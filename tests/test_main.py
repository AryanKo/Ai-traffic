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
        self._on_message = None

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


def test_boot_event_starts_session_before_being_stored():
    app, link, store = make_app()
    boot = {"type": "evt", "ms": 1, "ev": "BOOT", "lineA": 0, "lineB": 0}
    link._on_message(boot)
    assert store.session_id is not None
    store.flush()
    row = store.conn.execute(
        "SELECT session_id FROM events WHERE ev='BOOT'"
    ).fetchone()
    assert row == (store.session_id,)


def test_event_before_boot_does_not_crash():
    app, link, store = make_app()
    err = {"type": "evt", "ms": 1, "ev": "ERR", "msg": "TOF_INIT_FAILED"}
    link._on_message(err)
    store.flush()
    assert store.session_id is None


def direct_tel(ms, la, lb):
    return {"type": "tel", "ms": ms, "g": "A", "next": "-", "ph": "GREEN", "pt": 0, "mode": "DIRECT",
            "why": "BOOT", "emg": "-", "emgLeft": 0, "la": la, "lb": lb,
            "a": {"raw": -1, "d": -1, "q": -1, "n": -1, "line": 0, "w": 0, "p": 0.0, "ok": 1},
            "b": {"raw": -1, "d": -1, "q": -1, "n": -1, "line": 0, "w": 0, "p": 0.0, "ok": 1}}


def test_direct_mode_telemetry_is_replaced_by_simulated_view_of_real_leds():
    app, link, store = make_app()
    link._on_message({"type": "evt", "ms": 1, "ev": "BOOT", "lineA": 0, "lineB": 0, "carMm": 70, "direct": 1})
    link._on_message(direct_tel(100, 0, 1))
    body = TestClient(app).get("/api/status").json()
    assert body["telemetry"]["sim"] is True
    assert body["telemetry"]["g"] == "A"
    assert (body["telemetry"]["la"], body["telemetry"]["lb"]) == (0, 1)
    assert body["config"]["lineA"] > 0


def test_direct_mode_led_change_logs_switch_events():
    app, link, store = make_app()
    link._on_message({"type": "evt", "ms": 1, "ev": "BOOT", "lineA": 0, "lineB": 0, "carMm": 70, "direct": 1})
    link._on_message(direct_tel(100, 0, 1))
    link._on_message(direct_tel(200, 1, 0))
    store.flush()
    evs = [r[0] for r in store.conn.execute("SELECT ev FROM events ORDER BY id")]
    assert evs == ["BOOT", "SWITCH", "GREEN"]


def test_non_direct_telemetry_passes_through_unchanged():
    app, link, store = make_app()
    tel = direct_tel(100, 1, 1)
    tel["mode"] = "AUTO"
    link._on_message(tel)
    body = TestClient(app).get("/api/status").json()
    assert "sim" not in body["telemetry"]


def test_board_reset_restores_last_reported_led_state():
    import time
    app, link, store = make_app()
    boot = {"type": "evt", "ms": 1, "ev": "BOOT", "lineA": 0, "lineB": 0, "carMm": 70, "direct": 1}
    link._on_message(boot)
    assert link.sent == []  # nothing reported yet, nothing to restore
    link._on_message(direct_tel(100, 0, 1))
    link._on_message(dict(boot))
    for _ in range(100):
        if link.sent:
            break
        time.sleep(0.01)
    assert link.sent == ["L:01"]


def test_remote_page_is_served():
    app, link, store = make_app()
    r = TestClient(app).get("/remote")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
