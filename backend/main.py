"""FastAPI app: routes, WebSocket broadcast, and wiring of link + store."""
import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from protocol import is_allowed_command
from serial_link import SerialLink
from stats import compute_stats
from store import Store


def create_app(link, store: Store) -> FastAPI:
    app = FastAPI()
    ws_clients: set[WebSocket] = set()
    state = {"latest_tel": None, "latest_cfg": None, "loop": None}

    def status_payload() -> dict:
        age = None
        if link.last_packet_at is not None:
            age = time.time() - link.last_packet_at
        return {
            "connected": link.connected,
            "port": link.port_name,
            "pps": link.pps(),
            "last_packet_age": age,
            "parse_errors": link.parse_errors,
            "booted": link.boot_at is not None,
        }

    def broadcast(kind: str, data: dict) -> None:
        loop = state["loop"]
        if loop is None:
            return
        for ws in list(ws_clients):
            asyncio.run_coroutine_threadsafe(_safe_send(ws, kind, data, ws_clients), loop)

    def on_message(obj: dict) -> None:
        if obj["type"] == "tel":
            state["latest_tel"] = obj
            store.add_telemetry(obj)
            broadcast("tel", obj)
        elif obj["type"] == "evt":
            store.add_event(obj)
            if obj.get("ev") == "BOOT":
                state["latest_cfg"] = obj
                store.start_session(link.port_name, json.dumps(obj))
            elif obj.get("ev") == "CFG":
                state["latest_cfg"] = obj
            broadcast("evt", obj)
        elif obj["type"] == "ack":
            broadcast("ack", obj)

    if hasattr(link, "_on_message"):
        link._on_message = on_message

    @app.on_event("startup")
    async def startup() -> None:
        state["loop"] = asyncio.get_event_loop()
        if hasattr(link, "start"):
            link.start()
        asyncio.create_task(_link_status_loop(status_payload, broadcast))

    @app.get("/api/status")
    def api_status():
        return {
            "link": status_payload(),
            "telemetry": state["latest_tel"],
            "config": state["latest_cfg"],
        }

    @app.get("/api/history")
    def api_history(seconds: int = 120):
        return store.history(seconds)

    @app.get("/api/events")
    def api_events(limit: int = 100):
        return store.recent_events(limit)

    @app.get("/api/stats")
    def api_stats():
        if store.session_id is None:
            return JSONResponse({"error": "no_session"}, status_code=404)
        store.flush()
        return compute_stats(store.conn, store.session_id)

    @app.post("/api/command")
    async def api_command(request: Request):
        body = await request.json()
        cmd = body.get("cmd", "")
        if not is_allowed_command(cmd):
            return JSONResponse({"ok": False, "error": "not_allowed"}, status_code=400)
        result = link.send_command(cmd)
        store.add_command(cmd, json.dumps(result))
        return result

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        ws_clients.add(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            ws_clients.discard(ws)

    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

    return app


async def _safe_send(ws: WebSocket, kind: str, data: dict, ws_clients: set) -> None:
    try:
        await ws.send_json({"kind": kind, "data": data})
    except Exception:
        ws_clients.discard(ws)


async def _link_status_loop(status_payload, broadcast) -> None:
    last_sent = None
    while True:
        status = status_payload()
        if status != last_sent:
            broadcast("link", status)
            last_sent = status
        await asyncio.sleep(1)


DB_PATH = os.environ.get("TRAFFIC_DB", "data/trafficmind.db")
_store = Store(DB_PATH)
_link = SerialLink(lambda obj: None, port=os.environ.get("TRAFFIC_PORT"))
app = create_app(_link, _store)
