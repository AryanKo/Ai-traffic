import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from traffic_sim import TrafficSim


def dev(ms, la, lb, emg="-", emg_left=0):
    return {"type": "tel", "ms": ms, "mode": "DIRECT", "emg": emg, "emgLeft": emg_left, "la": la, "lb": lb}


def run(sim, start_ms, end_ms, la, lb):
    tel, events = None, []
    for ms in range(start_ms, end_ms, 100):
        tel, evs = sim.step(dev(ms, la, lb))
        events += evs
    return tel, events


def test_light_state_comes_from_the_device_leds():
    sim = TrafficSim(rng=random.Random(1))
    assert sim.step(dev(0, 0, 1))[0]["g"] == "A"   # LED A off = A goes
    assert sim.step(dev(100, 1, 0))[0]["g"] == "B"
    assert sim.step(dev(200, 1, 1))[0]["g"] == "X"
    assert sim.step(dev(300, 0, 0))[0]["g"] == "AB"


def test_telemetry_is_flagged_and_carries_led_state():
    sim = TrafficSim(rng=random.Random(1))
    tel, _ = sim.step(dev(0, 1, 0))
    assert tel["sim"] is True
    assert (tel["la"], tel["lb"]) == (1, 0)
    assert tel["mode"] == "SIM"
    for lane in ("a", "b"):
        assert set(tel[lane]) == {"raw", "d", "q", "n", "line", "w", "p", "ok"}


def test_red_lane_queues_up_and_waits_while_green_lane_drains():
    sim = TrafficSim(rng=random.Random(2))
    tel, _ = run(sim, 0, 60000, la=1, lb=0)  # A red, B go
    assert tel["a"]["n"] > 0
    assert tel["a"]["w"] > 0
    assert tel["a"]["p"] > tel["a"]["n"]
    assert tel["b"]["n"] <= 1
    assert tel["b"]["w"] == 0
    tel, _ = run(sim, 60000, 120000, la=0, lb=1)  # flip
    assert tel["a"]["n"] <= 1


def test_queue_never_exceeds_lane_length():
    sim = TrafficSim(rng=random.Random(3))
    tel, _ = run(sim, 0, 600000, la=1, lb=1)
    assert tel["a"]["q"] <= tel["a"]["line"]
    assert tel["a"]["n"] == sim.max_cars


def test_switching_leds_emits_switch_then_green_events():
    sim = TrafficSim(rng=random.Random(4))
    run(sim, 0, 5000, la=0, lb=1)  # A green for 5 s
    _, events = sim.step(dev(5000, 1, 0))
    assert [e["ev"] for e in events] == ["SWITCH", "GREEN"]
    sw, gr = events
    assert (sw["from"], sw["to"]) == ("A", "B")
    assert sw["greenMs"] == 5000
    assert gr["lane"] == "B"
    assert sw["why"] == gr["why"]
    assert all(e["type"] == "evt" for e in events)


def test_going_all_red_emits_switch_to_x_and_no_green():
    sim = TrafficSim(rng=random.Random(5))
    sim.step(dev(0, 0, 1))
    _, events = sim.step(dev(100, 1, 1))
    assert [e["ev"] for e in events] == ["SWITCH"]
    assert events[0]["to"] == "X"


def test_emergency_reason_when_device_reports_emergency():
    sim = TrafficSim(rng=random.Random(6))
    sim.step(dev(0, 0, 1))
    tel, events = sim.step(dev(100, 1, 0, emg="B", emg_left=29900))
    assert events[0]["why"] == "EMERGENCY"
    assert tel["mode"] == "EMERGENCY"
    assert (tel["emg"], tel["emgLeft"]) == ("B", 29900)


def test_no_events_when_leds_do_not_change():
    sim = TrafficSim(rng=random.Random(7))
    _, events = run(sim, 0, 3000, la=0, lb=1)
    assert events == []


def test_config_fills_in_stop_lines_and_takes_car_length():
    sim = TrafficSim()
    cfg = sim.config({"type": "evt", "ev": "BOOT", "lineA": 0, "lineB": 0, "carMm": 100, "direct": 1})
    assert cfg["lineA"] == sim.line_mm and cfg["lineB"] == sim.line_mm
    assert sim.car_mm == 100
    assert sim.max_cars == sim.line_mm // 100
