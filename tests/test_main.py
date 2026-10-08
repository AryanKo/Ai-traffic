import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from fastapi.testclient import TestClient

from store import Store
from main import create_app


class FakeLink:
    def __init__(self):
        self.connected = False
        self.port_name = None
        self.parse_errors = 0
        self.last_packet_at = None
        self.boot_at = None
        self.sent = []

    def pps(self):
        return 0.0

    def send_command(self, cmd, timeout=2.0):
        self.sent.append(cmd)
        return {"ok": True, "ack": {"cmd": cmd}}


def make_app():
    db_path = os.path.join(tempfile.mkdtemp(), "t.db")
    store = Store(db_path)
    link = FakeLink()
    app = create_app(link, store)
    return app, link, store


def test_status_with_no_device_reports_disconnected():
    app, link, store = make_app()
    client = TestClient(app)
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["link"]["connected"] is False
    assert body["telemetry"] is None


def test_command_rejects_non_whitelisted_cmd():
    app, link, store = make_app()
    client = TestClient(app)
    r = client.post("/api/command", json={"cmd": "rm -rf /"})
    assert r.status_code == 400
    assert link.sent == []


def test_command_forwards_whitelisted_cmd_to_link():
    app, link, store = make_app()
    client = TestClient(app)
    r = client.post("/api/command", json={"cmd": "E:A"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert link.sent == ["E:A"]


def test_history_endpoint_returns_only_real_ring_buffer_entries():
    app, link, store = make_app()
    store.start_session("COM5", "{}")
    store.add_telemetry({
        "type": "tel", "ms": 1, "g": "A", "ph": "GREEN", "pt": 1, "mode": "AUTO", "why": "BOOT", "emg": "-",
        "a": {"raw": 1, "d": 1, "q": 0, "n": 0, "line": 1, "w": 0, "p": 0.0, "ok": 1},
        "b": {"raw": 1, "d": 1, "q": 0, "n": 0, "line": 1, "w": 0, "p": 0.0, "ok": 1},
    })
    client = TestClient(app)
    r = client.get("/api/history?seconds=60")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_stats_endpoint_404_before_any_session():
    app, link, store = make_app()
    client = TestClient(app)
    r = client.get("/api/stats")
    assert r.status_code == 404
