import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from store import Store

TEL = {
    "type": "tel", "ms": 5123, "g": "A", "ph": "GREEN", "pt": 1100,
    "mode": "AUTO", "why": "PRESSURE", "emg": "-",
    "a": {"raw": 30000, "d": 503, "q": 0, "n": 0, "line": 403, "w": 0, "p": 0.0, "ok": 1},
    "b": {"raw": 210, "d": 212, "q": 188, "n": 3, "line": 400, "w": 3200, "p": 4.6, "ok": 1},
}
EVT = {"type": "evt", "ms": 10, "ev": "BOOT", "lineA": 0, "lineB": 0}


def make_store():
    path = os.path.join(tempfile.mkdtemp(), "test.db")
    return Store(path)


def test_start_session_returns_increasing_ids():
    s = make_store()
    sid1 = s.start_session("COM5", "{}")
    assert isinstance(sid1, int)
    s.end_session()
    sid2 = s.start_session("COM5", "{}")
    assert sid2 != sid1


def test_add_telemetry_lands_in_ring_buffer_immediately():
    s = make_store()
    s.start_session("COM5", "{}")
    s.add_telemetry(TEL)
    hist = s.history(60)
    assert len(hist) == 1
    assert hist[0]["g"] == "A"


def test_add_telemetry_is_flushed_to_sqlite():
    s = make_store()
    s.start_session("COM5", "{}")
    s.add_telemetry(TEL)
    s.flush()
    row = s.conn.execute(
        "SELECT g, a_line, b_w FROM telemetry WHERE session_id=?", (s.session_id,)
    ).fetchone()
    assert row == ("A", 403, 3200)


def test_add_event_is_queryable_via_recent_events():
    s = make_store()
    s.start_session("COM5", "{}")
    s.add_event(EVT)
    events = s.recent_events(10)
    assert len(events) == 1
    assert events[0]["ev"] == "BOOT"


def test_history_excludes_entries_older_than_window():
    s = make_store()
    s.start_session("COM5", "{}")
    s.ring_seconds = 600
    old_ts = time.time() - 700
    s.ring.append((old_ts, TEL))
    s.add_telemetry(TEL)
    hist = s.history(600)
    assert len(hist) == 1


def test_add_command_is_persisted():
    s = make_store()
    s.start_session("COM5", "{}")
    s.add_command("E:A", '{"ok": true}')
    row = s.conn.execute(
        "SELECT cmd, result FROM commands WHERE session_id=?", (s.session_id,)
    ).fetchone()
    assert row == ("E:A", '{"ok": true}')
