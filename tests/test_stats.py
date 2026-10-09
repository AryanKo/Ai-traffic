import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from store import Store
from stats import compute_stats


def make_store():
    path = os.path.join(tempfile.mkdtemp(), "test.db")
    return Store(path)


def add_evt(store, ev, **fields):
    store.add_event({"type": "evt", "ms": 0, "ev": ev, **fields})
    store.flush()


def add_tel(store, lane_w_a=0, lane_w_b=0, q_a=0, q_b=0, n_a=0, n_b=0):
    store.add_telemetry({
        "type": "tel", "ms": 0, "g": "A", "ph": "GREEN", "pt": 0, "mode": "AUTO", "why": "BOOT", "emg": "-",
        "a": {"raw": 1, "d": 1, "q": q_a, "n": n_a, "line": 400, "w": lane_w_a, "p": 0.0, "ok": 1},
        "b": {"raw": 1, "d": 1, "q": q_b, "n": n_b, "line": 400, "w": lane_w_b, "p": 0.0, "ok": 1},
    })
    store.flush()


def test_empty_session_has_no_fabricated_averages_and_does_not_crash():
    s = make_store()
    s.start_session("COM5", "{}")
    stats = compute_stats(s.conn, s.session_id)
    assert stats["switches_total"] == 0
    assert stats["avg_green_ms"] == {"A": None, "B": None}
    assert stats["longest_green_ms"] == {"A": None, "B": None}
    assert stats["green_share"] == {"A": None, "B": None}
    assert stats["avg_wait_ms"] == {"A": None, "B": None}
    assert stats["max_wait_ms"] == {"A": None, "B": None}


def test_counts_switches_by_reason():
    s = make_store()
    s.start_session("COM5", "{}")
    add_evt(s, "SWITCH", **{"from": "A", "to": "B", "why": "PRESSURE", "greenMs": 5000, "nA": 0, "nB": 3, "pA": 0, "pB": 4})
    add_evt(s, "SWITCH", **{"from": "B", "to": "A", "why": "GAP_OUT", "greenMs": 3000, "nA": 2, "nB": 0, "pA": 2, "pB": 0})
    stats = compute_stats(s.conn, s.session_id)
    assert stats["switches_total"] == 2
    assert stats["switches_by_reason"] == {"PRESSURE": 1, "GAP_OUT": 1}
    assert stats["avg_green_ms"]["A"] == 5000
    assert stats["avg_green_ms"]["B"] == 3000
    assert stats["longest_green_ms"]["A"] == 5000
    assert stats["green_share"]["A"] == 5000 / 8000
    assert stats["green_share"]["B"] == 3000 / 8000


def test_peak_queue_and_fault_and_emergency_counts():
    s = make_store()
    s.start_session("COM5", "{}")
    add_tel(s, q_a=100, n_a=1, q_b=300, n_b=4)
    add_tel(s, q_a=50, n_a=0, q_b=600, n_b=5)
    add_evt(s, "EMG_ON", lane="A")
    add_evt(s, "FAULT", lane="B")
    stats = compute_stats(s.conn, s.session_id)
    assert stats["peak_queue_mm"] == {"A": 100, "B": 600}
    assert stats["peak_queue_cars"] == {"A": 1, "B": 5}
    assert stats["emergencies"] == 1
    assert stats["faults"] == 1


def test_wait_uses_lane_w_from_latest_telemetry_before_green():
    s = make_store()
    s.start_session("COM5", "{}")
    add_tel(s, lane_w_b=3200)
    add_evt(s, "GREEN", lane="B", why="PRESSURE")
    stats = compute_stats(s.conn, s.session_id)
    assert stats["avg_wait_ms"]["B"] == 3200
    assert stats["max_wait_ms"]["B"] == 3200
