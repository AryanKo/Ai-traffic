"""Computes session stats purely from logged real telemetry/events."""
import json
import sqlite3
import time

_LANES = ("A", "B")


def compute_stats(conn: sqlite3.Connection, session_id: int) -> dict:
    rows = conn.execute(
        "SELECT host_ts, ev, json FROM events WHERE session_id=? ORDER BY id",
        (session_id,),
    ).fetchall()
    events = [(ts, ev, json.loads(raw)) for ts, ev, raw in rows]

    switches = [(ts, d) for ts, ev, d in events if ev == "SWITCH"]
    greens = [(ts, d) for ts, ev, d in events if ev == "GREEN"]
    emergencies = sum(1 for _, ev, _ in events if ev == "EMG_ON")
    faults = sum(1 for _, ev, _ in events if ev == "FAULT")

    switches_by_reason: dict[str, int] = {}
    green_ms_by_lane: dict[str, list[int]] = {"A": [], "B": []}
    for _, d in switches:
        switches_by_reason[d["why"]] = switches_by_reason.get(d["why"], 0) + 1
        green_ms_by_lane[d["from"]].append(d["greenMs"])

    avg_green_ms = {lane: _avg(v) for lane, v in green_ms_by_lane.items()}
    longest_green_ms = {lane: (max(v) if v else None) for lane, v in green_ms_by_lane.items()}
    total_green = sum(sum(v) for v in green_ms_by_lane.values())
    green_share = {
        lane: (sum(v) / total_green if total_green else None)
        for lane, v in green_ms_by_lane.items()
    }

    wait_by_lane: dict[str, list[int]] = {"A": [], "B": []}
    for ts, d in greens:
        lane = d["lane"]
        col = "a_w" if lane == "A" else "b_w"
        row = conn.execute(
            f"SELECT {col} FROM telemetry WHERE session_id=? AND host_ts < ? ORDER BY host_ts DESC LIMIT 1",
            (session_id, ts),
        ).fetchone()
        if row and row[0] is not None:
            wait_by_lane[lane].append(row[0])
    avg_wait_ms = {lane: _avg(v) for lane, v in wait_by_lane.items()}
    max_wait_ms = {lane: (max(v) if v else None) for lane, v in wait_by_lane.items()}

    peak_queue_mm, peak_queue_cars = {}, {}
    for lane, qcol, ncol in (("A", "a_q", "a_n"), ("B", "b_q", "b_n")):
        row = conn.execute(
            f"SELECT MAX({qcol}), MAX({ncol}) FROM telemetry WHERE session_id=?",
            (session_id,),
        ).fetchone()
        peak_queue_mm[lane] = row[0] or 0
        peak_queue_cars[lane] = row[1] or 0

    started_row = conn.execute(
        "SELECT started_at FROM sessions WHERE id=?", (session_id,)
    ).fetchone()
    session_uptime_s = (time.time() - float(started_row[0])) if started_row else 0

    return {
        "switches_total": len(switches),
        "switches_by_reason": switches_by_reason,
        "avg_green_ms": avg_green_ms,
        "longest_green_ms": longest_green_ms,
        "avg_wait_ms": avg_wait_ms,
        "max_wait_ms": max_wait_ms,
        "peak_queue_mm": peak_queue_mm,
        "peak_queue_cars": peak_queue_cars,
        "green_share": green_share,
        "emergencies": emergencies,
        "faults": faults,
        "session_uptime_s": session_uptime_s,
    }


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
