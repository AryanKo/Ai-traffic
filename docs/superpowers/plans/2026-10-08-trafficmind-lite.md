# TrafficMind Lite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI + React dashboard that shows live, real telemetry from the TrafficMind Lite Arduino traffic controller over serial, logs it to SQLite, and lets the operator trigger emergency/calibrate/car-length commands — with zero fake data anywhere outside `tests/`.

**Architecture:** A Python backend (`backend/`) owns a background serial-reader thread, an in-memory ring buffer, and a SQLite log; FastAPI exposes REST + a WebSocket that pushes every real message to the browser. A Vite/React/TypeScript frontend renders the dashboard, built to static files and served by FastAPI so `python run.py` is the only command needed.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, pyserial, `sqlite3`; React + Vite + TypeScript + Tailwind CSS, uPlot, lucide-react.

**Spec:** `BUILD_SPEC_FOR_CLAUDE_CODE.md` and `WIRING_AND_SETUP.md` (repo root). `traffic_controller.ino` is the given, unmodified device firmware.

## Global Constraints

- No mock/fake/demo/random/simulated data anywhere outside `tests/`. Final task greps for `random|mock|fake|dummy|faker|sample|demo|simulate` (case-insensitive) outside `tests/` and must find nothing (spec rule 1.7, Done-when #8).
- If no Arduino is connected, the UI shows "No device connected"; numeric fields show a dash; charts show empty axes (spec rule 1.2).
- If no telemetry arrived for more than 1 s, the UI shows stale/grey state with "Signal lost, last data X s ago" — no interpolation or animation of values that didn't arrive (spec rule 1.3).
- The app never computes its own signal decision for actual lights — only an explicitly labelled "rule check" panel that re-derives pass/fail from the latest reported values and reported config (spec rule 1.4, section 6.4).
- All device settings (min green, max green, clearance, margins, car length, stop line distances) are read from `BOOT`/`CFG` events, never hardcoded in the UI (spec rule 1.5).
- Serial: 115200 baud, newline-terminated JSON lines in, whitelisted plain-text commands out (`PING`, `CFG`, `CAL`, `E:A`, `E:B`, `E:OFF`, `CAR:<10..500>`) — validated server-side (spec section 3.4).
- Backend binds to `127.0.0.1` only, no auth (spec section 4.4).
- Desktop layout target 1440x900 without scrolling, dark theme, Inter + JetBrains Mono, signal colors reserved for signals (spec section 5).
- `traffic_controller.ino` behavior must not change; the folder containing it must be named `traffic_controller` to match the `.ino` filename (spec section 7, `WIRING_AND_SETUP.md` section 5 step 3).
- **Deviation from spec section 4.2 wording:** the telemetry table column list in the spec includes `a_e`/`b_e`, but the serial protocol (section 3.1) has no `e` field per lane — the only lane field missing from the rest of the column list is `line` (calibrated stop-line distance). Task 3 stores this as `a_line`/`b_line` instead of `a_e`/`b_e`, since that is the only field consistent with the protocol.

## Review Focus

- **Arduino resets when the port opens:** the backend must wait for a fresh `BOOT` event before treating the device as usable (spec section 3) — covered in Task 6 (`main.py` session-start-on-BOOT test) and Task 5 (`SerialLink` boot-tracking test).
- **Non-JSON / partial lines on the wire:** a truncated line (power blip, buffer split) must be silently counted as a parse error, never crash the reader or reach the UI as telemetry — covered in Task 2 (`parse_line` malformed-input tests) and Task 5 (`_handle_line` parse-error-counter test).
- **Unknown or malformed command text:** anything not in the exact whitelist (including a near-miss like `CAR:9999` or `cal` lowercase) must be rejected by the backend before it reaches the serial port — covered in Task 4 (`is_allowed_command` boundary tests) and Task 6 (`/api/command` rejection test).
- **Device unplugged mid-session:** `/api/status` and the WebSocket `link` message must flip to disconnected and keep the last real numbers rather than freezing on stale "connected" state — covered in Task 5 (`SerialLink` reconnect-loop test) and Task 9 (frontend staleness-after-1s test).
- **Division-by-zero in stats with few/no events:** a session with zero switches or zero green time must not throw when computing averages or green-time share — covered in Task 4 (`compute_stats` empty-session test).

---

## Task 1: Project scaffold and firmware folder

**Files:**
- Create: `traffic_controller/traffic_controller.ino` (moved from repo root, unchanged content)
- Create: `backend/__init__.py` (empty)
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `data/.gitkeep`
- Create: `README.md`
- Modify: none (pure scaffold)

**Interfaces:**
- Produces: on-disk layout `trafficmind/traffic_controller/`, `backend/`, `frontend/` (created in Task 8), `tests/`, `data/`, `run.py` (Task 7), `requirements.txt` that every later backend task installs from.

- [ ] **Step 1: Move the firmware file into its matching folder**

```bash
mkdir -p traffic_controller
git mv traffic_controller.ino traffic_controller/traffic_controller.ino 2>/dev/null || mv traffic_controller.ino traffic_controller/traffic_controller.ino
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi>=0.110
uvicorn[standard]>=0.29
pyserial>=3.5
pytest>=8.0
httpx>=0.27
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
data/*.db
data/*.db-wal
data/*.db-shm
frontend/node_modules/
frontend/dist/
.pytest_cache/
```

- [ ] **Step 4: Create `data/.gitkeep` (empty file) and `backend/__init__.py` (empty file)**

- [ ] **Step 5: Create `README.md`**

```markdown
# TrafficMind Lite

Live dashboard for the two-lane TrafficMind Lite Arduino junction.

## Run

1. Flash `traffic_controller/traffic_controller.ino` to the Uno (Arduino IDE 2, install the "VL53L0X" library by Pololu). See `WIRING_AND_SETUP.md`.
2. Close the Arduino Serial Monitor (only one program can hold the port).
3. `pip install -r requirements.txt`
4. `cd frontend && npm install && cd ..`
5. `python run.py`

The dashboard opens at http://127.0.0.1:8000.

## Finding the COM port

The backend auto-detects the Uno by USB vendor ID. If it picks the wrong port, or you have more than one device plugged in, pass it explicitly:

```
python run.py --port COM5
```

or set `TRAFFIC_PORT=COM5`.
```

- [ ] **Step 6: Initialize git and commit the scaffold**

```bash
git init
git add traffic_controller requirements.txt .gitignore data/.gitkeep backend/__init__.py README.md BUILD_SPEC_FOR_CLAUDE_CODE.md WIRING_AND_SETUP.md
git commit -m "chore: project scaffold and firmware folder"
```

---

## Task 2: `protocol.py` — line parsing and command whitelist

**Files:**
- Create: `backend/protocol.py`
- Test: `tests/test_protocol.py`

**Interfaces:**
- Produces: `parse_line(line: str) -> dict | None`, `is_allowed_command(cmd: str) -> bool` — used by `serial_link.py` (Task 5) and `main.py` (Task 6).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_protocol.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from protocol import parse_line, is_allowed_command

TEL_LINE = (
    '{"type":"tel","ms":5123,"g":"A","next":"-","ph":"GREEN","pt":1100,'
    '"mode":"AUTO","why":"PRESSURE","emg":"-","emgLeft":0,'
    '"a":{"raw":30000,"d":503,"q":0,"n":0,"line":403,"w":0,"p":0.00,"ok":1},'
    '"b":{"raw":210,"d":212,"q":188,"n":3,"line":400,"w":3200,"p":4.60,"ok":1}}'
)
EVT_LINE = '{"type":"evt","ms":10,"ev":"BOOT","lineA":0,"lineB":0,"carMm":70}'
ACK_LINE = '{"type":"ack","ms":11,"cmd":"PING"}'


def test_parses_valid_telemetry():
    obj = parse_line(TEL_LINE)
    assert obj["type"] == "tel"
    assert obj["g"] == "A"
    assert obj["a"]["raw"] == 30000


def test_parses_valid_event():
    obj = parse_line(EVT_LINE)
    assert obj["type"] == "evt"
    assert obj["ev"] == "BOOT"


def test_parses_valid_ack():
    obj = parse_line(ACK_LINE)
    assert obj["type"] == "ack"


def test_rejects_empty_line():
    assert parse_line("") is None
    assert parse_line("\n") is None


def test_rejects_truncated_json():
    assert parse_line('{"type":"tel","ms":51') is None


def test_rejects_non_json_noise():
    assert parse_line("garbled startup text from the bootloader") is None


def test_rejects_json_without_recognized_type():
    assert parse_line('{"type":"debug","msg":"hi"}') is None


def test_rejects_json_array():
    assert parse_line("[1,2,3]") is None


def test_allows_exact_whitelisted_commands():
    for cmd in ("PING", "CFG", "CAL", "E:A", "E:B", "E:OFF"):
        assert is_allowed_command(cmd)


def test_allows_car_command_in_range():
    assert is_allowed_command("CAR:70")
    assert is_allowed_command("CAR:10")
    assert is_allowed_command("CAR:500")


def test_rejects_car_command_out_of_range():
    assert not is_allowed_command("CAR:9")
    assert not is_allowed_command("CAR:501")
    assert not is_allowed_command("CAR:9999")


def test_rejects_car_command_non_numeric():
    assert not is_allowed_command("CAR:abc")
    assert not is_allowed_command("CAR:")


def test_rejects_unknown_or_near_miss_commands():
    assert not is_allowed_command("cal")
    assert not is_allowed_command("E:C")
    assert not is_allowed_command("PING; rm -rf")
    assert not is_allowed_command("")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'protocol'`

- [ ] **Step 3: Write `backend/protocol.py`**

```python
"""Parsing and validation of lines exchanged with the Arduino."""
import json
from typing import Optional

_WHITELIST_EXACT = {"PING", "CFG", "CAL", "E:A", "E:B", "E:OFF"}
_RECOGNIZED_TYPES = {"tel", "evt", "ack"}


def parse_line(line: str) -> Optional[dict]:
    """Parse one line of serial output into a dict, or None if it is not
    a recognized, well-formed JSON message. Malformed or partial lines
    (power blips, a line split across two reads) must return None rather
    than raise, so the caller can count them as parse errors."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    if obj.get("type") not in _RECOGNIZED_TYPES:
        return None
    return obj


def is_allowed_command(cmd: str) -> bool:
    """Whitelist for commands the app may send to the device."""
    if cmd in _WHITELIST_EXACT:
        return True
    if cmd.startswith("CAR:"):
        value = cmd[4:]
        if not value.isdigit():
            return False
        n = int(value)
        return 10 <= n <= 500
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_protocol.py -v`
Expected: PASS (16 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/protocol.py tests/test_protocol.py
git commit -m "feat: serial line parser and command whitelist"
```

---

## Task 3: `store.py` — SQLite log and in-memory ring buffer

**Files:**
- Create: `backend/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `class Store(db_path: str)` with methods `start_session(port: str | None, boot_json: str) -> int`, `end_session() -> None`, `add_telemetry(tel: dict) -> None`, `add_event(evt: dict) -> None`, `add_command(cmd: str, result: str) -> None`, `flush() -> None`, `history(seconds: int) -> list[dict]`, `recent_events(limit: int) -> list[dict]`, and attributes `store.session_id: int | None`, `store.conn: sqlite3.Connection` — used by `stats.py` (Task 4) and `main.py` (Task 6).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_store.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'store'`

- [ ] **Step 3: Write `backend/store.py`**

```python
"""SQLite log and in-memory ring buffer of real telemetry/events."""
import json
import sqlite3
import threading
import time
from collections import deque
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    port TEXT,
    boot_json TEXT
);
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    host_ts REAL NOT NULL,
    dev_ms INTEGER,
    g TEXT, ph TEXT, pt INTEGER, mode TEXT, why TEXT, emg TEXT,
    a_raw INTEGER, a_d INTEGER, a_q INTEGER, a_n INTEGER, a_line INTEGER, a_w INTEGER, a_p REAL, a_ok INTEGER,
    b_raw INTEGER, b_d INTEGER, b_q INTEGER, b_n INTEGER, b_line INTEGER, b_w INTEGER, b_p REAL, b_ok INTEGER
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    host_ts REAL NOT NULL,
    dev_ms INTEGER,
    ev TEXT NOT NULL,
    json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    host_ts REAL NOT NULL,
    cmd TEXT NOT NULL,
    result TEXT
);
"""

FLUSH_INTERVAL_S = 0.5


class Store:
    def __init__(self, db_path: str, ring_seconds: int = 600):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._lock = threading.Lock()
        self.session_id: int | None = None
        self.ring_seconds = ring_seconds
        self.ring: deque[tuple[float, dict]] = deque()
        self._pending_tel: list[tuple] = []
        self._pending_evt: list[tuple] = []
        self._pending_cmd: list[tuple] = []
        self._last_flush = time.monotonic()

    def start_session(self, port: str | None, boot_json: str) -> int:
        now = time.time()
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO sessions (started_at, port, boot_json) VALUES (?,?,?)",
                (str(now), port, boot_json),
            )
            self.conn.commit()
            self.session_id = cur.lastrowid
        self.ring.clear()
        return self.session_id

    def end_session(self) -> None:
        if self.session_id is None:
            return
        self.flush()
        with self._lock:
            self.conn.execute(
                "UPDATE sessions SET ended_at=? WHERE id=?",
                (str(time.time()), self.session_id),
            )
            self.conn.commit()

    def add_telemetry(self, tel: dict) -> None:
        now = time.time()
        a, b = tel.get("a", {}), tel.get("b", {})
        row = (
            self.session_id, now, tel.get("ms"), tel.get("g"), tel.get("ph"),
            tel.get("pt"), tel.get("mode"), tel.get("why"), tel.get("emg"),
            a.get("raw"), a.get("d"), a.get("q"), a.get("n"), a.get("line"), a.get("w"), a.get("p"), a.get("ok"),
            b.get("raw"), b.get("d"), b.get("q"), b.get("n"), b.get("line"), b.get("w"), b.get("p"), b.get("ok"),
        )
        self._pending_tel.append(row)
        self.ring.append((now, tel))
        cutoff = now - self.ring_seconds
        while self.ring and self.ring[0][0] < cutoff:
            self.ring.popleft()
        self._maybe_flush()

    def add_event(self, evt: dict) -> None:
        now = time.time()
        row = (self.session_id, now, evt.get("ms"), evt.get("ev"), json.dumps(evt))
        self._pending_evt.append(row)
        self._maybe_flush(force=True)

    def add_command(self, cmd: str, result: str) -> None:
        row = (self.session_id, time.time(), cmd, result)
        self._pending_cmd.append(row)
        self._maybe_flush(force=True)

    def _maybe_flush(self, force: bool = False) -> None:
        if force or (time.monotonic() - self._last_flush) >= FLUSH_INTERVAL_S:
            self.flush()

    def flush(self) -> None:
        with self._lock:
            if self._pending_tel:
                self.conn.executemany(
                    "INSERT INTO telemetry (session_id, host_ts, dev_ms, g, ph, pt, mode, why, emg,"
                    " a_raw, a_d, a_q, a_n, a_line, a_w, a_p, a_ok,"
                    " b_raw, b_d, b_q, b_n, b_line, b_w, b_p, b_ok)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    self._pending_tel,
                )
                self._pending_tel = []
            if self._pending_evt:
                self.conn.executemany(
                    "INSERT INTO events (session_id, host_ts, dev_ms, ev, json) VALUES (?,?,?,?,?)",
                    self._pending_evt,
                )
                self._pending_evt = []
            if self._pending_cmd:
                self.conn.executemany(
                    "INSERT INTO commands (session_id, host_ts, cmd, result) VALUES (?,?,?,?)",
                    self._pending_cmd,
                )
                self._pending_cmd = []
            self.conn.commit()
            self._last_flush = time.monotonic()

    def history(self, seconds: int) -> list[dict]:
        cutoff = time.time() - seconds
        return [tel for ts, tel in self.ring if ts >= cutoff]

    def recent_events(self, limit: int) -> list[dict]:
        self.flush()
        with self._lock:
            rows = self.conn.execute(
                "SELECT host_ts, ev, json FROM events WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (self.session_id, limit),
            ).fetchall()
        out = []
        for host_ts, ev, raw in rows:
            d = json.loads(raw)
            d["host_ts"] = host_ts
            out.append(d)
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_store.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/store.py tests/test_store.py
git commit -m "feat: SQLite log and ring buffer for real telemetry"
```

---

## Task 4: `stats.py` — session stats from the DB

**Files:**
- Create: `backend/stats.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Consumes: `sqlite3.Connection` and `session_id` shaped like `Store.conn`/`Store.session_id` from Task 3 (same `events`/`telemetry`/`sessions` schema).
- Produces: `compute_stats(conn: sqlite3.Connection, session_id: int) -> dict` with keys `switches_total`, `switches_by_reason`, `avg_green_ms`, `longest_green_ms`, `avg_wait_ms`, `max_wait_ms`, `peak_queue_mm`, `peak_queue_cars`, `green_share`, `emergencies`, `faults`, `session_uptime_s` — used by `main.py` (Task 6).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_stats.py
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


def test_empty_session_has_zeroed_stats_no_crash():
    s = make_store()
    s.start_session("COM5", "{}")
    stats = compute_stats(s.conn, s.session_id)
    assert stats["switches_total"] == 0
    assert stats["avg_green_ms"] == {"A": 0, "B": 0}
    assert stats["green_share"] == {"A": 0, "B": 0}
    assert stats["avg_wait_ms"] == {"A": 0, "B": 0}


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_stats.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'stats'`

- [ ] **Step 3: Write `backend/stats.py`**

```python
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
    longest_green_ms = {lane: (max(v) if v else 0) for lane, v in green_ms_by_lane.items()}
    total_green = sum(sum(v) for v in green_ms_by_lane.values())
    green_share = {
        lane: (sum(v) / total_green if total_green else 0)
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
    max_wait_ms = {lane: (max(v) if v else 0) for lane, v in wait_by_lane.items()}

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


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stats.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/stats.py tests/test_stats.py
git commit -m "feat: compute session stats from logged events and telemetry"
```

---

## Task 5: `serial_link.py` — port detection, reader thread, command writer

**Files:**
- Create: `backend/serial_link.py`
- Test: `tests/test_serial_link.py`

**Interfaces:**
- Consumes: `parse_line` from `backend/protocol.py` (Task 2).
- Produces: `find_port() -> str | None`, `class SerialLink(on_message: Callable[[dict], None], port: str | None = None, baud: int = 115200)` with `.start()`, `.stop()`, `.send_command(cmd: str, timeout: float = 2.0) -> dict`, `.pps() -> float`, and attributes `.connected: bool`, `.port_name: str | None`, `.parse_errors: int`, `.last_packet_at: float | None`, `.boot_at: float | None` — used by `main.py` (Task 6). `_handle_line(line: str)` is intentionally testable without opening a real port.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_serial_link.py
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from serial_link import SerialLink, find_port, ALLOWED_VIDS

TEL_LINE = (
    '{"type":"tel","ms":1,"g":"A","ph":"GREEN","pt":1,"mode":"AUTO","why":"BOOT","emg":"-",'
    '"a":{"raw":1,"d":1,"q":0,"n":0,"line":1,"w":0,"p":0.0,"ok":1},'
    '"b":{"raw":1,"d":1,"q":0,"n":0,"line":1,"w":0,"p":0.0,"ok":1}}'
)
BOOT_LINE = '{"type":"evt","ms":1,"ev":"BOOT","lineA":0,"lineB":0}'


class FakePort:
    vid = 0x2341
    device = "COM9"


class WrongVidPort:
    vid = 0x9999
    device = "COM3"


def test_find_port_accepts_known_vids(monkeypatch):
    import serial_link
    monkeypatch.setattr(serial_link.list_ports, "comports", lambda: [WrongVidPort(), FakePort()])
    assert find_port() == "COM9"


def test_find_port_returns_none_when_nothing_matches(monkeypatch):
    import serial_link
    monkeypatch.setattr(serial_link.list_ports, "comports", lambda: [WrongVidPort()])
    assert find_port() is None


def test_handle_line_delivers_parsed_message_to_callback():
    received = []
    link = SerialLink(on_message=received.append)
    link._handle_line(TEL_LINE)
    assert len(received) == 1
    assert received[0]["type"] == "tel"
    assert link.last_packet_at is not None


def test_handle_line_counts_parse_errors_without_crashing():
    received = []
    link = SerialLink(on_message=received.append)
    link._handle_line("not json at all")
    link._handle_line("")
    assert link.parse_errors == 2
    assert received == []


def test_handle_line_tracks_boot_time():
    link = SerialLink(on_message=lambda obj: None)
    assert link.boot_at is None
    link._handle_line(BOOT_LINE)
    assert link.boot_at is not None


def test_pps_counts_only_last_5_seconds():
    link = SerialLink(on_message=lambda obj: None)
    now = time.time()
    link._arrivals = [now - 10, now - 1, now]
    assert link.pps() == 2 / 5.0


def test_send_command_without_connection_returns_not_connected():
    link = SerialLink(on_message=lambda obj: None)
    result = link.send_command("PING")
    assert result == {"ok": False, "error": "not_connected"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_serial_link.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'serial_link'`

- [ ] **Step 3: Write `backend/serial_link.py`**

```python
"""Port detection, background reader thread, and command writer for the Uno."""
import threading
import time
from typing import Callable, Optional

import serial
from serial.tools import list_ports

from protocol import parse_line

ALLOWED_VIDS = {0x2341, 0x2A03, 0x1A86}
RECONNECT_DELAY_S = 2.0
ARRIVAL_WINDOW_S = 5.0


def find_port() -> Optional[str]:
    for p in list_ports.comports():
        if p.vid in ALLOWED_VIDS:
            return p.device
    return None


class SerialLink:
    def __init__(self, on_message: Callable[[dict], None], port: Optional[str] = None, baud: int = 115200):
        self._on_message = on_message
        self._port_override = port
        self._baud = baud
        self._ser: Optional[serial.Serial] = None
        self._stop = threading.Event()
        self._write_lock = threading.Lock()
        self._ack_waiters: dict[str, threading.Event] = {}
        self._ack_results: dict[str, dict] = {}
        self._cal_waiter: Optional[threading.Event] = None
        self._cal_result: Optional[dict] = None
        self._arrivals: list[float] = []
        self.connected = False
        self.port_name: Optional[str] = None
        self.parse_errors = 0
        self.last_packet_at: Optional[float] = None
        self.boot_at: Optional[float] = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            port = self._port_override or find_port()
            if not port:
                self.connected = False
                time.sleep(RECONNECT_DELAY_S)
                continue
            try:
                self._ser = serial.Serial(port, self._baud, timeout=1)
                self.port_name = port
                self.connected = True
                self.boot_at = None
                self._read_loop()
            except (serial.SerialException, OSError):
                self.connected = False
                time.sleep(RECONNECT_DELAY_S)

    def _read_loop(self) -> None:
        buf = b""
        while not self._stop.is_set():
            try:
                chunk = self._ser.read(1)
            except (serial.SerialException, OSError):
                break
            if not chunk:
                continue
            if chunk == b"\n":
                self._handle_line(buf.decode("utf-8", errors="replace"))
                buf = b""
            else:
                buf += chunk
        self.connected = False
        try:
            self._ser.close()
        except Exception:
            pass

    def _handle_line(self, line: str) -> None:
        obj = parse_line(line)
        now = time.time()
        if obj is None:
            self.parse_errors += 1
            return
        self.last_packet_at = now
        self._arrivals.append(now)
        cutoff = now - ARRIVAL_WINDOW_S
        self._arrivals = [a for a in self._arrivals if a >= cutoff]

        if obj["type"] == "evt" and obj.get("ev") == "BOOT":
            self.boot_at = now
        if obj["type"] == "ack":
            cmd = obj.get("cmd")
            ev = self._ack_waiters.get(cmd)
            if ev:
                self._ack_results[cmd] = obj
                ev.set()
        if obj["type"] == "evt" and obj.get("ev") == "CAL" and self._cal_waiter:
            self._cal_result = obj
            self._cal_waiter.set()

        self._on_message(obj)

    def pps(self) -> float:
        return len(self._arrivals) / ARRIVAL_WINDOW_S

    def send_command(self, cmd: str, timeout: float = 2.0) -> dict:
        if not self.connected or not self._ser:
            return {"ok": False, "error": "not_connected"}
        ack_event = threading.Event()
        cal_event = None
        with self._write_lock:
            self._ack_waiters[cmd] = ack_event
            if cmd == "CAL":
                cal_event = threading.Event()
                self._cal_waiter = cal_event
                self._cal_result = None
            try:
                self._ser.write((cmd + "\n").encode("ascii"))
            except (serial.SerialException, OSError):
                self._ack_waiters.pop(cmd, None)
                return {"ok": False, "error": "write_failed"}
        got_ack = ack_event.wait(timeout)
        self._ack_waiters.pop(cmd, None)
        if not got_ack:
            return {"ok": False, "error": "timeout"}
        result = {"ok": True, "ack": self._ack_results.pop(cmd, None)}
        if cmd == "CAL" and cal_event is not None:
            cal_event.wait(4.0)
            self._cal_waiter = None
            result["cal"] = self._cal_result
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_serial_link.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/serial_link.py tests/test_serial_link.py
git commit -m "feat: serial port detection, reader thread, and command writer"
```

---

## Task 6: `main.py` — FastAPI app, routes, WebSocket

**Files:**
- Create: `backend/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `is_allowed_command` (Task 2), `SerialLink` (Task 5), `Store` (Task 3), `compute_stats` (Task 4).
- Produces: `app: FastAPI` with `GET /api/status`, `GET /api/history`, `GET /api/events`, `GET /api/stats`, `POST /api/command`, `WS /ws` — used by `run.py` (Task 7). Exposes `create_app(link: SerialLink, store: Store) -> FastAPI` so tests can inject fakes instead of touching real hardware.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_main.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Write `backend/main.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_main.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/main.py tests/test_main.py
git commit -m "feat: FastAPI routes, websocket broadcast, and link/store wiring"
```

---

## Task 7: `run.py` — single entry point

**Files:**
- Create: `run.py`

**Interfaces:**
- Consumes: `backend.main.app` (Task 6), `frontend/dist` (produced by Task 8's `npm run build`).
- Produces: the one command (`python run.py`) the spec's Done-when #9 requires.

- [ ] **Step 1: Write `run.py`**

```python
"""Single entry point: builds the frontend if needed, starts the server, opens the browser."""
import argparse
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ensure_frontend_built() -> None:
    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        return
    print("frontend/dist not found, running npm run build ...")
    subprocess.run(["npm", "run", "build"], cwd=str(ROOT / "frontend"), check=True, shell=(os.name == "nt"))


def open_browser_later(url: str) -> None:
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", dest="port", default=None, help="Arduino COM port override, e.g. COM5")
    args = parser.parse_args()
    if args.port:
        os.environ["TRAFFIC_PORT"] = args.port

    ensure_frontend_built()

    sys.path.insert(0, str(ROOT / "backend"))
    import uvicorn

    url = "http://127.0.0.1:8000"
    open_browser_later(url)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, app_dir=str(ROOT / "backend"))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test without a device attached**

Run: `python run.py` (with no Arduino plugged in)
Expected: server starts on `http://127.0.0.1:8000`, browser opens, `/api/status` returns `{"link": {"connected": false, ...}, "telemetry": null, "config": null}`. Stop with Ctrl+C.

- [ ] **Step 3: Commit**

```bash
git add run.py
git commit -m "feat: single-command entry point"
```

---

## Task 8: Frontend scaffold — Vite + React + TS + Tailwind

**Files:**
- Create: `frontend/` (Vite-generated project: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/index.css`, etc.)
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/useWebSocket.ts`
- Test: `frontend/src/types.test.ts` (Vitest)

**Interfaces:**
- Produces: shared TypeScript types `Telemetry`, `LaneTelemetry`, `Event`, `LinkStatus`, `Config` (mirroring spec sections 3.1–3.2), `api.ts` fetch helpers (`getStatus`, `getHistory`, `getEvents`, `getStats`, `postCommand`), and `useWebSocket(url)` hook delivering `{kind, data}` messages — consumed by every component task (9–16).

- [ ] **Step 1: Scaffold the Vite project**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer vitest @vitest/ui jsdom
npm install uplot lucide-react
cd ..
```

- [ ] **Step 2: Configure Tailwind (`frontend/tailwind.config.ts`)**

```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0D10",
        panel: "#12151A",
        border: "#20242B",
        accent: "#38BDF8",
        go: "#22C55E",
        stop: "#EF4444",
        clear: "#F59E0B",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
```

`frontend/postcss.config.js`:

```javascript
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

`frontend/src/index.css` (replace generated content):

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #0B0D10;
  color: #E6E9EE;
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 3: Write failing test for shared types/formatting helper**

```typescript
// frontend/src/types.test.ts
import { describe, it, expect } from "vitest";
import { isNoQueue } from "./types";

describe("isNoQueue", () => {
  it("treats raw 30000 as no queue", () => {
    expect(isNoQueue(30000, 0)).toBe(true);
  });
  it("treats q of 0 as no queue", () => {
    expect(isNoQueue(100, 0)).toBe(true);
  });
  it("treats a real queue as not no-queue", () => {
    expect(isNoQueue(210, 188)).toBe(false);
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/types.test.ts`
Expected: FAIL — `isNoQueue` is not exported yet.

- [ ] **Step 5: Write `frontend/src/types.ts`**

```typescript
export interface LaneTelemetry {
  raw: number;
  d: number;
  q: number;
  n: number;
  line: number;
  w: number;
  p: number;
  ok: 0 | 1;
}

export interface Telemetry {
  type: "tel";
  ms: number;
  g: "A" | "B" | "X";
  next: "A" | "B" | "-";
  ph: "GREEN" | "CLEAR";
  pt: number;
  mode: "AUTO" | "EMERGENCY" | "DEGRADED";
  why: "BOOT" | "GAP_OUT" | "PRESSURE" | "MAX_GREEN" | "EMERGENCY";
  emg: "A" | "B" | "-";
  emgLeft: number;
  a: LaneTelemetry;
  b: LaneTelemetry;
}

export interface EventMsg {
  type: "evt";
  ms: number;
  ev: "BOOT" | "CFG" | "CAL" | "SWITCH" | "GREEN" | "EMG_ON" | "EMG_OFF" | "FAULT" | "RECOVER" | "ERR";
  host_ts?: number;
  [key: string]: unknown;
}

export interface AckMsg {
  type: "ack";
  ms: number;
  cmd: string;
}

export interface LinkStatus {
  connected: boolean;
  port: string | null;
  pps: number;
  last_packet_age: number | null;
  parse_errors: number;
  booted: boolean;
}

export interface Config {
  lineA: number;
  lineB: number;
  carMm: number;
  minG: number;
  maxG: number;
  clr: number;
  emgT: number;
  queueMin: number;
  waitW: number;
  margin: number;
  faultDemand: number;
  tof: number;
  cal?: "EEPROM" | "NONE";
}

export const NO_TARGET_RAW = 30000;

export function isNoQueue(raw: number, q: number): boolean {
  return raw === NO_TARGET_RAW || q === 0;
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/types.test.ts`
Expected: PASS

- [ ] **Step 7: Write `frontend/src/api.ts`**

```typescript
import type { Config, EventMsg, LinkStatus, Telemetry } from "./types";

export interface StatusResponse {
  link: LinkStatus;
  telemetry: Telemetry | null;
  config: Config | null;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export const getStatus = () => getJSON<StatusResponse>("/api/status");
export const getHistory = (seconds: number) => getJSON<Telemetry[]>(`/api/history?seconds=${seconds}`);
export const getEvents = (limit: number) => getJSON<EventMsg[]>(`/api/events?limit=${limit}`);
export const getStats = () => getJSON<Record<string, unknown>>("/api/stats");

export async function postCommand(cmd: string): Promise<{ ok: boolean; [key: string]: unknown }> {
  const res = await fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cmd }),
  });
  return await res.json();
}
```

- [ ] **Step 8: Write `frontend/src/useWebSocket.ts`**

```typescript
import { useEffect, useRef, useState } from "react";

export interface WsMessage<T = unknown> {
  kind: "tel" | "evt" | "ack" | "link";
  data: T;
}

export function useWebSocket(url: string, onMessage: (msg: WsMessage) => void) {
  const [open, setOpen] = useState(false);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closedByUs = false;
    let retryTimer: number | undefined;

    function connect() {
      ws = new WebSocket(url);
      ws.onopen = () => setOpen(true);
      ws.onclose = () => {
        setOpen(false);
        if (!closedByUs) retryTimer = window.setTimeout(connect, 2000);
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (evt) => {
        try {
          handlerRef.current(JSON.parse(evt.data) as WsMessage);
        } catch {
          // ignore malformed frames; never show them as data
        }
      };
    }

    connect();
    return () => {
      closedByUs = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      ws?.close();
    };
  }, [url]);

  return { open };
}
```

- [ ] **Step 9: Commit**

```bash
git add frontend package-lock.json 2>/dev/null
git add -A frontend
git commit -m "feat: frontend scaffold with Tailwind, shared types, api client, websocket hook"
```

---

## Task 9: Top bar and app shell with connection/staleness state

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/TopBar.tsx`
- Create: `frontend/src/useLiveState.ts`
- Test: `frontend/src/useLiveState.test.ts`

**Interfaces:**
- Consumes: `useWebSocket` (Task 8), `getStatus`/`getHistory`/`getEvents` (Task 8), `Telemetry`/`LinkStatus`/`Config`/`EventMsg` types (Task 8).
- Produces: `useLiveState()` hook returning `{ telemetry, link, config, events, isStale }` — consumed by every remaining frontend task. `isStale` is a pure function of "now" and `telemetry`'s arrival time, exported separately so it is unit-testable without a clock mock on the whole hook.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/useLiveState.test.ts
import { describe, it, expect } from "vitest";
import { computeIsStale } from "./useLiveState";

describe("computeIsStale", () => {
  it("is not stale right after a packet arrives", () => {
    expect(computeIsStale(1000, 1000)).toBe(false);
  });
  it("is not stale at exactly 999ms", () => {
    expect(computeIsStale(1000, 1999)).toBe(false);
  });
  it("is stale past 1000ms with no new packet", () => {
    expect(computeIsStale(1000, 2001)).toBe(true);
  });
  it("is stale when there has never been a packet", () => {
    expect(computeIsStale(null, 2001)).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/useLiveState.test.ts`
Expected: FAIL — `computeIsStale` not exported.

- [ ] **Step 3: Write `frontend/src/useLiveState.ts`**

```typescript
import { useEffect, useRef, useState } from "react";
import { getEvents, getStatus } from "./api";
import { useWebSocket, type WsMessage } from "./useWebSocket";
import type { Config, EventMsg, LinkStatus, Telemetry } from "./types";

const STALE_AFTER_MS = 1000;

export function computeIsStale(lastPacketAtMs: number | null, nowMs: number): boolean {
  if (lastPacketAtMs === null) return true;
  return nowMs - lastPacketAtMs >= STALE_AFTER_MS;
}

export function useLiveState() {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [link, setLink] = useState<LinkStatus | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [events, setEvents] = useState<EventMsg[]>([]);
  const [now, setNow] = useState<number>(Date.now());
  const lastPacketAtRef = useRef<number | null>(null);

  useEffect(() => {
    getStatus().then((s) => {
      setLink(s.link);
      setTelemetry(s.telemetry);
      setConfig(s.config);
      if (s.telemetry) lastPacketAtRef.current = Date.now();
    });
    getEvents(100).then(setEvents);
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, []);

  useWebSocket("/ws".replace("/ws", (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws"), (msg: WsMessage) => {
    if (msg.kind === "tel") {
      setTelemetry(msg.data as Telemetry);
      lastPacketAtRef.current = Date.now();
    } else if (msg.kind === "evt") {
      setEvents((prev) => [msg.data as EventMsg, ...prev].slice(0, 200));
      const ev = msg.data as EventMsg;
      if (ev.ev === "BOOT" || ev.ev === "CFG") setConfig(ev as unknown as Config);
    } else if (msg.kind === "link") {
      setLink(msg.data as LinkStatus);
    }
  });

  const isStale = computeIsStale(lastPacketAtRef.current, now);

  return { telemetry, link, config, events, isStale };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/useLiveState.test.ts`
Expected: PASS

- [ ] **Step 5: Write `frontend/src/components/TopBar.tsx`**

```tsx
import type { LinkStatus } from "../types";

function linkLabel(link: LinkStatus | null, isStale: boolean): string {
  if (!link || !link.connected) return "No device";
  if (!link.booted) return "Booting";
  if (isStale) return "Signal lost";
  return `Connected ${link.port ?? ""}`.trim();
}

export function TopBar({ link, mode, deviceMs, isStale }: {
  link: LinkStatus | null;
  mode: string | null;
  deviceMs: number | null;
  isStale: boolean;
}) {
  const label = linkLabel(link, isStale);
  const pillClass = label.startsWith("Connected")
    ? "bg-go/20 text-go"
    : label === "Signal lost"
      ? "bg-clear/20 text-clear"
      : "bg-stop/20 text-stop";

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-3">
      <div className="text-lg font-semibold">TrafficMind Lite</div>
      <div className="flex items-center gap-4 font-mono text-sm">
        <span className={`rounded-full px-3 py-1 ${pillClass}`}>{label}</span>
        <span>{link ? `${link.pps.toFixed(1)} pkt/s` : "—"}</span>
        <span>
          {link && link.last_packet_age !== null ? `last ${link.last_packet_age.toFixed(1)}s ago` : "—"}
        </span>
        <span className="rounded px-2 py-1 bg-panel border border-border">{mode ?? "—"}</span>
        <span>{deviceMs !== null ? `up ${(deviceMs / 1000).toFixed(0)}s` : "—"}</span>
      </div>
    </header>
  );
}
```

- [ ] **Step 6: Write `frontend/src/App.tsx`**

```tsx
import { useLiveState } from "./useLiveState";
import { TopBar } from "./components/TopBar";

export default function App() {
  const { telemetry, link, isStale } = useLiveState();

  return (
    <div className="min-h-screen bg-bg text-[#E6E9EE]">
      <TopBar
        link={link}
        mode={telemetry?.mode ?? null}
        deviceMs={telemetry?.ms ?? null}
        isStale={isStale}
      />
      <main className="p-6 text-sm text-gray-400">
        Dashboard panels are added in later tasks.
      </main>
    </div>
  );
}
```

- [ ] **Step 7: Verify in the browser**

Run: `cd frontend && npm run dev` (with backend running via `python run.py` in another terminal, or point Vite's dev proxy at `127.0.0.1:8000` for `/api` and `/ws`)
Expected: with no Arduino attached, top bar shows "No device", dash values, no crash.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/TopBar.tsx frontend/src/useLiveState.ts frontend/src/useLiveState.test.ts
git commit -m "feat: app shell, top bar, and live/staleness state hook"
```

---

## Task 10: Junction SVG view

**Files:**
- Create: `frontend/src/components/JunctionView.tsx`
- Create: `frontend/src/junctionGeometry.ts`
- Test: `frontend/src/junctionGeometry.test.ts`

**Interfaces:**
- Consumes: `Telemetry`, `Config` types (Task 8).
- Produces: pure `queueFraction(line: number, q: number): number` and `laneLabel(...)` helpers in `junctionGeometry.ts`; `<JunctionView telemetry config />` component — consumed by `App.tsx`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/junctionGeometry.test.ts
import { describe, it, expect } from "vitest";
import { queueFraction } from "./junctionGeometry";

describe("queueFraction", () => {
  it("is 0 when not calibrated (line = 0)", () => {
    expect(queueFraction(0, 50)).toBe(0);
  });
  it("is 0 when there is no queue", () => {
    expect(queueFraction(400, 0)).toBe(0);
  });
  it("is q/line when calibrated and queued", () => {
    expect(queueFraction(400, 200)).toBe(0.5);
  });
  it("clamps to 1 if q exceeds line (sensor noise)", () => {
    expect(queueFraction(400, 500)).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/junctionGeometry.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `frontend/src/junctionGeometry.ts`**

```typescript
export function queueFraction(lineMm: number, qMm: number): number {
  if (lineMm <= 0 || qMm <= 0) return 0;
  return Math.min(1, qMm / lineMm);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/junctionGeometry.test.ts`
Expected: PASS

- [ ] **Step 5: Write `frontend/src/components/JunctionView.tsx`**

```tsx
import { isNoQueue } from "../types";
import type { Config, Telemetry } from "../types";
import { queueFraction } from "../junctionGeometry";

const W = 480;
const H = 480;

function SignalHead({ go, cx, cy }: { go: boolean; cx: number; cy: number }) {
  return <circle cx={cx} cy={cy} r={10} fill={go ? "#22C55E" : "#EF4444"} />;
}

export function JunctionView({ telemetry, config }: { telemetry: Telemetry | null; config: Config | null }) {
  if (!telemetry) {
    return (
      <div className="flex h-full items-center justify-center text-gray-500">
        No device connected — no junction data
      </div>
    );
  }

  const a = telemetry.a;
  const b = telemetry.b;
  const laneLenPx = 180;
  const fracA = queueFraction(a.line, a.q);
  const fracB = queueFraction(b.line, b.q);
  const goA = telemetry.g === "A";
  const goB = telemetry.g === "B";
  const allRed = telemetry.g === "X";
  const emergency = telemetry.mode === "EMERGENCY";

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={`h-full w-full ${emergency ? "outline outline-2 outline-clear" : ""}`}>
      {/* Lane A: from bottom, heading up */}
      <rect x={W / 2 - 24} y={H / 2} width={48} height={laneLenPx} fill="#161A20" />
      {a.line === 0 ? (
        <text x={W / 2} y={H / 2 + laneLenPx / 2} fill="#9CA3AF" fontSize="12" textAnchor="middle">Not calibrated</text>
      ) : (
        <rect
          x={W / 2 - 24}
          y={H / 2 + laneLenPx * (1 - fracA)}
          width={48}
          height={laneLenPx * fracA}
          fill="#38BDF822"
        />
      )}
      {a.ok === 0 && <rect x={W / 2 - 24} y={H / 2} width={48} height={laneLenPx} fill="url(#hatch)" />}
      <SignalHead go={goA} cx={W / 2} cy={H / 2} />
      <text x={W / 2} y={H / 2 - 16} fontSize="11" fill="#9CA3AF" textAnchor="middle">
        {isNoQueue(a.raw, a.q) ? "No queue" : `${(a.q / 10).toFixed(0)} cm`}
      </text>

      {/* Lane B: from right, heading left */}
      <rect x={W / 2} y={H / 2 - 24} width={laneLenPx} height={48} fill="#161A20" />
      {b.line === 0 ? (
        <text x={W / 2 + laneLenPx / 2} y={H / 2 - 30} fill="#9CA3AF" fontSize="12" textAnchor="middle">Not calibrated</text>
      ) : (
        <rect
          x={W / 2}
          y={H / 2 - 24}
          width={laneLenPx * fracB}
          height={48}
          fill="#38BDF822"
        />
      )}
      {b.ok === 0 && <rect x={W / 2} y={H / 2 - 24} width={laneLenPx} height={48} fill="url(#hatch)" />}
      <SignalHead go={goB} cx={W / 2} cy={H / 2} />
      <text x={W / 2 + laneLenPx / 2} y={H / 2 - 32} fontSize="11" fill="#9CA3AF" textAnchor="middle">
        {isNoQueue(b.raw, b.q) ? "No queue" : `${(b.q / 10).toFixed(0)} cm`}
      </text>

      {allRed && (
        <text x={W / 2} y={30} fill="#F59E0B" fontSize="14" textAnchor="middle">
          ALL RED — clearing
        </text>
      )}
      {emergency && (
        <text x={W / 2} y={50} fill="#F59E0B" fontSize="13" textAnchor="middle">
          Emergency priority: Lane {telemetry.emg}, {(telemetry.emgLeft / 1000).toFixed(0)}s left
        </text>
      )}

      <defs>
        <pattern id="hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="transparent" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#EF4444" strokeWidth="2" />
        </pattern>
      </defs>
    </svg>
  );
}
```

- [ ] **Step 6: Wire into `App.tsx`**

```tsx
// in App.tsx, replace the <main> placeholder with:
import { JunctionView } from "./components/JunctionView";
// ...
<main className="grid grid-cols-[2fr_1fr] gap-4 p-6">
  <section className="rounded-2xl border border-border bg-panel p-4" style={{ height: 520 }}>
    <JunctionView telemetry={telemetry} config={config} />
  </section>
</main>
```

- [ ] **Step 7: Verify in the browser**

Run: `cd frontend && npm run dev`
Expected: with no device, junction panel shows "No device connected"; with telemetry flowing (or captured via `/api/history` once hardware is attached), lanes fill proportionally to real `q`/`line` values with no animation of unreceived data.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/JunctionView.tsx frontend/src/junctionGeometry.ts frontend/src/junctionGeometry.test.ts frontend/src/App.tsx
git commit -m "feat: top-down junction SVG view driven only by real telemetry"
```

---

## Task 11: Lane cards with sparkline

**Files:**
- Create: `frontend/src/components/LaneCard.tsx`
- Create: `frontend/src/sparkline.ts`
- Test: `frontend/src/sparkline.test.ts`

**Interfaces:**
- Consumes: `Telemetry`/`LaneTelemetry` types (Task 8); `getHistory` (Task 8) for the 60 s car-count series.
- Produces: `buildSparklinePoints(history: Telemetry[], lane: "a" | "b", nowMs: number, windowMs: number): number[]` and `<LaneCard lane="A" telemetry=... history=... />` — consumed by `App.tsx`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/sparkline.test.ts
import { describe, it, expect } from "vitest";
import { buildSparklinePoints } from "./sparkline";
import type { Telemetry } from "./types";

function tel(ms: number, nA: number): Telemetry {
  return {
    type: "tel", ms, g: "A", next: "-", ph: "GREEN", pt: 0, mode: "AUTO", why: "BOOT", emg: "-", emgLeft: 0,
    a: { raw: 1, d: 1, q: 1, n: nA, line: 1, w: 0, p: 0, ok: 1 },
    b: { raw: 1, d: 1, q: 1, n: 0, line: 1, w: 0, p: 0, ok: 1 },
  };
}

describe("buildSparklinePoints", () => {
  it("returns only points inside the window, in order", () => {
    const history = [tel(1000, 1), tel(2000, 2), tel(3000, 3)];
    const points = buildSparklinePoints(history, "a", 3000, 2000);
    expect(points).toEqual([2, 3]);
  });
  it("returns an empty array for empty history", () => {
    expect(buildSparklinePoints([], "a", 1000, 60000)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/sparkline.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `frontend/src/sparkline.ts`**

```typescript
import type { Telemetry } from "./types";

export function buildSparklinePoints(
  history: Telemetry[],
  lane: "a" | "b",
  nowMs: number,
  windowMs: number,
): number[] {
  const cutoff = nowMs - windowMs;
  return history.filter((t) => t.ms >= cutoff).map((t) => t[lane].n);
}
```

Note: `history` here is the host-timestamped history served by `/api/history` (device `ms` is monotonic within a session), so filtering on `t.ms` against a window expressed in the same device-ms timeline is correct as long as the window and `nowMs` both come from the latest telemetry's `ms`, not `Date.now()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/sparkline.test.ts`
Expected: PASS

- [ ] **Step 5: Write `frontend/src/components/LaneCard.tsx`**

```tsx
import { isNoQueue } from "../types";
import type { LaneTelemetry, Telemetry } from "../types";
import { buildSparklinePoints } from "../sparkline";

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return <div className="h-8 text-xs text-gray-500">—</div>;
  const max = Math.max(1, ...points);
  const w = 120;
  const h = 32;
  const step = w / (points.length - 1);
  const d = points.map((v, i) => `${i === 0 ? "M" : "L"} ${i * step} ${h - (v / max) * h}`).join(" ");
  return (
    <svg width={w} height={h}>
      <path d={d} stroke="#38BDF8" fill="none" strokeWidth={1.5} />
    </svg>
  );
}

export function LaneCard({
  name, direction, sensorType, lane, history, nowMs,
}: {
  name: string;
  direction: string;
  sensorType: string;
  lane: LaneTelemetry | null;
  history: Telemetry[];
  nowMs: number;
}) {
  const points = lane ? buildSparklinePoints(history, name === "Lane A" ? "a" : "b", nowMs, 60000) : [];
  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="flex items-baseline justify-between">
        <div className="font-semibold">{name}</div>
        <div className="text-xs text-gray-500">{direction} · {sensorType}</div>
      </div>
      {!lane ? (
        <div className="mt-2 text-sm text-gray-500">—</div>
      ) : (
        <div className="mt-2 grid grid-cols-2 gap-1 font-mono text-sm">
          <div>raw: {lane.raw === 30000 ? "nothing in range" : `${lane.raw} mm`}</div>
          <div>filtered: {lane.d < 0 ? "—" : `${lane.d} mm`}</div>
          <div>queue: {isNoQueue(lane.raw, lane.q) ? "no queue" : `${(lane.q / 10).toFixed(1)} cm`}</div>
          <div>cars: {lane.n < 0 ? "—" : lane.n}</div>
          <div>waiting: {(lane.w / 1000).toFixed(1)} s</div>
          <div>pressure: {lane.p.toFixed(2)}</div>
          <div>stop line: {lane.line === 0 ? "not calibrated" : `${(lane.line / 10).toFixed(1)} cm`}</div>
          <div className={lane.ok ? "text-go" : "text-stop"}>{lane.ok ? "sensor OK" : "SENSOR FAULT"}</div>
        </div>
      )}
      <div className="mt-2"><Sparkline points={points} /></div>
    </div>
  );
}
```

- [ ] **Step 6: Wire into `App.tsx`** (add history fetch + lane card row)

```tsx
// App.tsx additions
import { useEffect, useState } from "react";
import { getHistory } from "./api";
import { LaneCard } from "./components/LaneCard";
// inside App():
const [history, setHistory] = useState<Telemetry[]>([]);
useEffect(() => {
  const id = setInterval(() => { getHistory(60).then(setHistory); }, 1000);
  return () => clearInterval(id);
}, []);
// ... in the grid, add a second row:
<div className="grid grid-cols-2 gap-4">
  <LaneCard name="Lane A" direction="from bottom" sensorType="HC-SR04" lane={telemetry?.a ?? null} history={history} nowMs={telemetry?.ms ?? 0} />
  <LaneCard name="Lane B" direction="from right" sensorType="VL53L0X" lane={telemetry?.b ?? null} history={history} nowMs={telemetry?.ms ?? 0} />
</div>
```

- [ ] **Step 7: Verify in the browser, then commit**

```bash
git add frontend/src/components/LaneCard.tsx frontend/src/sparkline.ts frontend/src/sparkline.test.ts frontend/src/App.tsx
git commit -m "feat: lane cards with real-data sparklines"
```

---

## Task 12: Decision panel with live rule check

**Files:**
- Create: `frontend/src/components/DecisionPanel.tsx`
- Create: `frontend/src/ruleCheck.ts`
- Test: `frontend/src/ruleCheck.test.ts`

**Interfaces:**
- Consumes: `Telemetry`, `Config` types (Task 8).
- Produces: `evaluateRules(tel: Telemetry, config: Config): RuleResult[]` (pure, testable) and `<DecisionPanel telemetry config />` — consumed by `App.tsx`. This is the explicitly-labelled re-derivation from spec rule 1.4 / section 6.4 — it never drives the lights.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/ruleCheck.test.ts
import { describe, it, expect } from "vitest";
import { evaluateRules } from "./ruleCheck";
import type { Config, Telemetry } from "./types";

const config: Config = {
  lineA: 400, lineB: 400, carMm: 70, minG: 4000, maxG: 20000, clr: 1500,
  emgT: 30000, queueMin: 20, waitW: 0.5, margin: 1.5, faultDemand: 3, tof: 1,
};

function tel(overrides: Partial<Telemetry> = {}): Telemetry {
  return {
    type: "tel", ms: 0, g: "A", next: "-", ph: "GREEN", pt: 5000, mode: "AUTO", why: "BOOT", emg: "-", emgLeft: 0,
    a: { raw: 1, d: 1, q: 0, n: 0, line: 400, w: 0, p: 0, ok: 1 },
    b: { raw: 1, d: 1, q: 200, n: 3, line: 400, w: 2000, p: 4.0, ok: 1 },
    ...overrides,
  };
}

describe("evaluateRules", () => {
  it("min green reached passes when pt >= minG", () => {
    const rules = evaluateRules(tel({ pt: 5000 }), config);
    expect(rules.find((r) => r.id === "min_green")!.pass).toBe(true);
  });
  it("min green reached fails when pt < minG", () => {
    const rules = evaluateRules(tel({ pt: 1000 }), config);
    expect(rules.find((r) => r.id === "min_green")!.pass).toBe(false);
  });
  it("gap out passes when green lane has no cars", () => {
    const rules = evaluateRules(tel({ a: { raw: 1, d: 1, q: 0, n: 0, line: 400, w: 0, p: 0, ok: 1 } }), config);
    expect(rules.find((r) => r.id === "gap_out")!.pass).toBe(true);
  });
  it("pressure rule compares other vs green plus margin", () => {
    const rules = evaluateRules(
      tel({
        a: { raw: 1, d: 1, q: 0, n: 1, line: 400, w: 0, p: 1.0, ok: 1 },
        b: { raw: 1, d: 1, q: 200, n: 3, line: 400, w: 2000, p: 4.0, ok: 1 },
      }),
      config,
    );
    const r = rules.find((x) => x.id === "pressure")!;
    expect(r.pass).toBe(true);
    expect(r.detail).toContain("4");
    expect(r.detail).toContain("1");
  });
  it("max green reached compares pt to maxG", () => {
    const rules = evaluateRules(tel({ pt: 21000 }), config);
    expect(rules.find((r) => r.id === "max_green")!.pass).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/ruleCheck.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `frontend/src/ruleCheck.ts`**

```typescript
import type { Config, LaneTelemetry, Telemetry } from "./types";

export interface RuleResult {
  id: string;
  label: string;
  pass: boolean;
  detail: string;
}

function other(tel: Telemetry): LaneTelemetry {
  return tel.g === "A" ? tel.b : tel.a;
}
function green(tel: Telemetry): LaneTelemetry {
  return tel.g === "A" ? tel.a : tel.b;
}

export function evaluateRules(tel: Telemetry, config: Config): RuleResult[] {
  if (tel.g === "X") {
    return [{ id: "all_red", label: "All red clearance in progress", pass: true, detail: "Rules apply once a lane has green" }];
  }
  const g = green(tel);
  const o = other(tel);
  const minGreenOk = tel.pt >= config.minG;
  const otherHasCars = o.n > 0;
  const gapOut = g.n === 0;
  const pressureMargin = o.p > g.p + config.margin;
  const maxGreenOk = tel.pt >= config.maxG;

  return [
    { id: "min_green", label: "Min green reached", pass: minGreenOk, detail: `${tel.pt}ms / ${config.minG}ms` },
    { id: "other_has_cars", label: "Other lane has cars", pass: otherHasCars, detail: `${o.n} cars` },
    { id: "gap_out", label: "Green lane has no cars (GAP_OUT)", pass: minGreenOk && otherHasCars && gapOut, detail: `green lane cars: ${g.n}` },
    { id: "pressure", label: "Pressure: other > green + margin", pass: minGreenOk && otherHasCars && pressureMargin, detail: `${o.p.toFixed(2)} vs ${g.p.toFixed(2)} + ${config.margin}` },
    { id: "max_green", label: "Max green reached", pass: maxGreenOk, detail: `${tel.pt}ms / ${config.maxG}ms` },
  ];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/ruleCheck.test.ts`
Expected: PASS

- [ ] **Step 5: Write `frontend/src/components/DecisionPanel.tsx`**

```tsx
import type { Config, Telemetry } from "../types";
import { evaluateRules } from "../ruleCheck";

const WHY_TEXT: Record<string, string> = {
  BOOT: "Startup default",
  GAP_OUT: "The green lane ran out of cars",
  PRESSURE: "The other lane had built up more demand",
  MAX_GREEN: "The green lane hit its time limit",
  EMERGENCY: "Emergency priority was requested",
};

export function DecisionPanel({ telemetry, config }: { telemetry: Telemetry | null; config: Config | null }) {
  if (!telemetry || !config) {
    return <div className="rounded-2xl border border-border bg-panel p-4 text-gray-500">No device connected</div>;
  }
  const rules = evaluateRules(telemetry, config);
  const progressPct = Math.min(100, (telemetry.pt / config.maxG) * 100);
  const minGreenPct = (config.minG / config.maxG) * 100;

  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="font-semibold">Decision</div>
      <div className="mt-1 text-sm">GO: Lane {telemetry.g === "X" ? "none (all red)" : telemetry.g} — green for {(telemetry.pt / 1000).toFixed(1)}s</div>
      <div className="relative mt-2 h-2 rounded bg-black/40">
        <div className="absolute h-2 rounded bg-accent" style={{ width: `${progressPct}%` }} />
        <div className="absolute top-0 h-2 w-px bg-white/60" style={{ left: `${minGreenPct}%` }} />
      </div>
      <div className="mt-2 text-sm text-gray-400">Last switch: {telemetry.why} — {WHY_TEXT[telemetry.why] ?? ""}</div>

      <div className="mt-3 text-xs uppercase text-gray-500">Live rule check, from latest readings</div>
      <ul className="mt-1 space-y-1 text-sm">
        {rules.map((r) => (
          <li key={r.id} className="flex justify-between">
            <span className={r.pass ? "text-go" : "text-gray-500"}>{r.pass ? "✓" : "✗"} {r.label}</span>
            <span className="font-mono text-xs text-gray-500">{r.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 6: Wire into `App.tsx`** — add `<DecisionPanel telemetry={telemetry} config={config} />` into the right-hand column of the grid.

- [ ] **Step 7: Verify in the browser, then commit**

```bash
git add frontend/src/components/DecisionPanel.tsx frontend/src/ruleCheck.ts frontend/src/ruleCheck.test.ts frontend/src/App.tsx
git commit -m "feat: decision panel with labelled live rule check"
```

---

## Task 13: Live chart (uPlot)

**Files:**
- Create: `frontend/src/components/LiveChart.tsx`
- Create: `frontend/src/chartData.ts`
- Test: `frontend/src/chartData.test.ts`

**Interfaces:**
- Consumes: `Telemetry[]` history (from `getHistory`, Task 8/11).
- Produces: `toUplotSeries(history: Telemetry[]): [number[], number[], number[]]` (x = seconds-from-first, series A cars, series B cars) and `<LiveChart history={...} windowSeconds={120} />` — consumed by `App.tsx`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/chartData.test.ts
import { describe, it, expect } from "vitest";
import { toUplotSeries } from "./chartData";
import type { Telemetry } from "./types";

function tel(ms: number, nA: number, nB: number): Telemetry {
  return {
    type: "tel", ms, g: "A", next: "-", ph: "GREEN", pt: 0, mode: "AUTO", why: "BOOT", emg: "-", emgLeft: 0,
    a: { raw: 1, d: 1, q: 1, n: nA, line: 1, w: 0, p: 0, ok: 1 },
    b: { raw: 1, d: 1, q: 1, n: nB, line: 1, w: 0, p: 0, ok: 1 },
  };
}

describe("toUplotSeries", () => {
  it("converts ms to seconds-from-first and extracts both lanes' car counts", () => {
    const [x, a, b] = toUplotSeries([tel(1000, 1, 2), tel(3000, 4, 5)]);
    expect(x).toEqual([0, 2]);
    expect(a).toEqual([1, 4]);
    expect(b).toEqual([2, 5]);
  });
  it("returns empty series for empty history", () => {
    const [x, a, b] = toUplotSeries([]);
    expect(x).toEqual([]);
    expect(a).toEqual([]);
    expect(b).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/chartData.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `frontend/src/chartData.ts`**

```typescript
import type { Telemetry } from "./types";

export function toUplotSeries(history: Telemetry[]): [number[], number[], number[]] {
  if (history.length === 0) return [[], [], []];
  const t0 = history[0].ms;
  const x = history.map((t) => (t.ms - t0) / 1000);
  const a = history.map((t) => t.a.n);
  const b = history.map((t) => t.b.n);
  return [x, a, b];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/chartData.test.ts`
Expected: PASS

- [ ] **Step 5: Write `frontend/src/components/LiveChart.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { Telemetry } from "../types";
import { toUplotSeries } from "../chartData";

export function LiveChart({ history }: { history: Telemetry[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const plotRef = useRef<uPlot | null>(null);
  const [windowSeconds, setWindowSeconds] = useState(120);

  useEffect(() => {
    if (!ref.current) return;
    const opts: uPlot.Options = {
      width: 640,
      height: 220,
      scales: { x: { time: false } },
      series: [
        {},
        { label: "Lane A cars", stroke: "#38BDF8" },
        { label: "Lane B cars", stroke: "#F59E0B" },
      ],
    };
    plotRef.current = new uPlot(opts, [[], [], []], ref.current);
    return () => plotRef.current?.destroy();
  }, []);

  useEffect(() => {
    if (!plotRef.current) return;
    const cutoffMs = history.length ? history[history.length - 1].ms - windowSeconds * 1000 : 0;
    const windowed = history.filter((t) => t.ms >= cutoffMs);
    plotRef.current.setData(toUplotSeries(windowed));
  }, [history, windowSeconds]);

  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="font-semibold">Cars over time</div>
        <div className="flex gap-1 text-xs">
          {[60, 120, 300].map((s) => (
            <button
              key={s}
              onClick={() => setWindowSeconds(s)}
              className={`rounded px-2 py-1 ${windowSeconds === s ? "bg-accent text-black" : "bg-black/30 text-gray-400"}`}
            >
              {s}s
            </button>
          ))}
        </div>
      </div>
      {history.length === 0 ? (
        <div className="flex h-[220px] items-center justify-center text-gray-500">No telemetry yet</div>
      ) : (
        <div ref={ref} />
      )}
    </div>
  );
}
```

- [ ] **Step 6: Wire into `App.tsx`** — track a longer rolling history (e.g. `getHistory(300)` every second) and render `<LiveChart history={longHistory} />`.

- [ ] **Step 7: Verify in the browser, then commit**

```bash
git add frontend/src/components/LiveChart.tsx frontend/src/chartData.ts frontend/src/chartData.test.ts frontend/src/App.tsx
git commit -m "feat: uPlot live chart of real car counts, 60/120/300s toggle"
```

---

## Task 14: Event log

**Files:**
- Create: `frontend/src/components/EventLog.tsx`
- Create: `frontend/src/eventText.ts`
- Test: `frontend/src/eventText.test.ts`

**Interfaces:**
- Consumes: `EventMsg` type (Task 8).
- Produces: `describeEvent(ev: EventMsg): string` (plain-words description per spec section 6.6) and `<EventLog events={...} />` — consumed by `App.tsx`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/eventText.test.ts
import { describe, it, expect } from "vitest";
import { describeEvent } from "./eventText";

describe("describeEvent", () => {
  it("describes a SWITCH event in plain words", () => {
    const text = describeEvent({ type: "evt", ms: 0, ev: "SWITCH", from: "A", to: "B", why: "PRESSURE", greenMs: 9200, nA: 1, nB: 4, pA: 1.0, pB: 4.6 });
    expect(text).toBe("Switched A to B after 9.2 s: PRESSURE (A 1.0, B 4.6)");
  });
  it("describes an EMG_ON event", () => {
    expect(describeEvent({ type: "evt", ms: 0, ev: "EMG_ON", lane: "A" })).toBe("Emergency priority requested for lane A");
  });
  it("describes a FAULT event", () => {
    expect(describeEvent({ type: "evt", ms: 0, ev: "FAULT", lane: "B" })).toBe("Lane B sensor fault");
  });
  it("falls back to the raw event name for unmapped events", () => {
    expect(describeEvent({ type: "evt", ms: 0, ev: "RECOVER", lane: "A" })).toBe("Lane A sensor recovered");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/eventText.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write `frontend/src/eventText.ts`**

```typescript
import type { EventMsg } from "./types";

export function describeEvent(ev: EventMsg): string {
  switch (ev.ev) {
    case "SWITCH": {
      const secs = (ev.greenMs as number) / 1000;
      return `Switched ${ev.from} to ${ev.to} after ${secs.toFixed(1)} s: ${ev.why} (A ${(ev.pA as number).toFixed(1)}, B ${(ev.pB as number).toFixed(1)})`;
    }
    case "GREEN":
      return `Lane ${ev.lane} got green: ${ev.why}`;
    case "EMG_ON":
      return `Emergency priority requested for lane ${ev.lane}`;
    case "EMG_OFF":
      return `Emergency priority ended for lane ${ev.lane} (${ev.why})`;
    case "FAULT":
      return `Lane ${ev.lane} sensor fault`;
    case "RECOVER":
      return `Lane ${ev.lane} sensor recovered`;
    case "CAL":
      return `Calibrated: A ${ev.lineA}mm (ok=${ev.okA}), B ${ev.lineB}mm (ok=${ev.okB})`;
    case "BOOT":
      return "Device booted";
    case "CFG":
      return "Config updated";
    case "ERR":
      return `Device error: ${ev.msg}`;
    default:
      return String(ev.ev);
  }
}

export function eventColor(ev: EventMsg): string {
  if (ev.ev === "FAULT" || ev.ev === "ERR") return "text-stop";
  if (ev.ev === "EMG_ON" || ev.ev === "EMG_OFF") return "text-clear";
  if (ev.ev === "SWITCH" || ev.ev === "GREEN") return "text-accent";
  return "text-gray-400";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/eventText.test.ts`
Expected: PASS

- [ ] **Step 5: Write `frontend/src/components/EventLog.tsx`**

```tsx
import type { EventMsg } from "../types";
import { describeEvent, eventColor } from "../eventText";

export function EventLog({ events }: { events: EventMsg[] }) {
  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="font-semibold">Event log</div>
      <ul className="mt-2 max-h-64 overflow-y-auto space-y-1 text-sm font-mono">
        {events.length === 0 && <li className="text-gray-500">No events yet</li>}
        {events.map((ev, i) => (
          <li key={i} className={eventColor(ev)}>
            [{new Date((ev.host_ts as number ?? Date.now() / 1000) * 1000).toLocaleTimeString()}] {describeEvent(ev)}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 6: Wire into `App.tsx`** — add `<EventLog events={events} />`.

- [ ] **Step 7: Verify in the browser, then commit**

```bash
git add frontend/src/components/EventLog.tsx frontend/src/eventText.ts frontend/src/eventText.test.ts frontend/src/App.tsx
git commit -m "feat: plain-words event log with per-type color"
```

---

## Task 15: Controls — emergency, calibrate, car length

**Files:**
- Create: `frontend/src/components/Controls.tsx`

**Interfaces:**
- Consumes: `postCommand` (Task 8), `LinkStatus`/`Config` types (Task 8).
- Produces: `<Controls link={...} config={...} onCalibrated={(evt) => void} />` — consumed by `App.tsx`. No new pure logic to unit test here (it is thin I/O wiring); verification is manual/browser per the project-wide UI-testing rule.

- [ ] **Step 1: Write `frontend/src/components/Controls.tsx`**

```tsx
import { useState } from "react";
import { postCommand } from "../api";
import type { Config, LinkStatus } from "../types";

export function Controls({ link, config }: { link: LinkStatus | null; config: Config | null }) {
  const [calOpen, setCalOpen] = useState(false);
  const [calResult, setCalResult] = useState<string | null>(null);
  const [carLenInput, setCarLenInput] = useState<string>(config ? String(config.carMm) : "");
  const [lastAck, setLastAck] = useState<string | null>(null);
  const disabled = !link || !link.connected;

  async function sendEmergency(cmd: string, label: string) {
    if (!window.confirm(`Send "${label}"?`)) return;
    const res = await postCommand(cmd);
    setLastAck(res.ok ? `${label}: ok` : `${label}: failed (${res.error ?? "unknown"})`);
  }

  async function runCalibrate() {
    const res = await postCommand("CAL");
    if (res.ok && res.cal) {
      const cal = res.cal as Record<string, unknown>;
      setCalResult(`A: ${(Number(cal.lineA) / 10).toFixed(1)}cm (ok=${cal.okA}), B: ${(Number(cal.lineB) / 10).toFixed(1)}cm (ok=${cal.okB})`);
    } else {
      setCalResult("Calibration failed or timed out");
    }
  }

  async function submitCarLength() {
    const mm = parseInt(carLenInput, 10);
    if (Number.isNaN(mm) || mm < 10 || mm > 500) return;
    const res = await postCommand(`CAR:${mm}`);
    setLastAck(res.ok ? `Car length set to ${mm}mm` : "Car length update failed");
  }

  return (
    <div className="rounded-2xl border border-border bg-panel p-4 space-y-4">
      <div>
        <div className="font-semibold">Emergency</div>
        <div className="mt-2 flex gap-2">
          <button disabled={disabled} onClick={() => sendEmergency("E:A", "Priority to Lane A")} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Priority to Lane A</button>
          <button disabled={disabled} onClick={() => sendEmergency("E:B", "Priority to Lane B")} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Priority to Lane B</button>
          <button disabled={disabled} onClick={() => sendEmergency("E:OFF", "Cancel emergency")} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Cancel emergency</button>
        </div>
        {lastAck && <div className="mt-1 text-xs text-gray-400">{lastAck}</div>}
      </div>

      <div>
        <div className="font-semibold">Calibrate</div>
        <button disabled={disabled} onClick={() => setCalOpen(true)} className="mt-2 rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Calibrate…</button>
        {calOpen && (
          <div className="mt-2 rounded border border-border bg-black/30 p-3 text-sm">
            <p>Remove all cars. Stand a flat card upright on each stop line, facing its sensor. Then press Calibrate. Remove the cards afterwards.</p>
            <div className="mt-2 flex gap-2">
              <button onClick={async () => { await runCalibrate(); }} className="rounded bg-accent px-3 py-1 text-black">Calibrate</button>
              <button onClick={() => setCalOpen(false)} className="rounded bg-black/30 px-3 py-1">Close</button>
            </div>
            {calResult && <div className="mt-2 text-gray-300">{calResult}</div>}
          </div>
        )}
      </div>

      <div>
        <div className="font-semibold">Car length (mm)</div>
        <div className="mt-2 flex gap-2">
          <input
            type="number"
            min={10}
            max={500}
            value={carLenInput}
            onChange={(e) => setCarLenInput(e.target.value)}
            className="w-24 rounded bg-black/30 px-2 py-1 font-mono"
          />
          <button disabled={disabled} onClick={submitCarLength} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Set</button>
        </div>
        <div className="mt-1 text-xs text-gray-500">Current: {config ? `${config.carMm} mm` : "—"}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire into `App.tsx`** — add `<Controls link={link} config={config} />`.

- [ ] **Step 3: Verify in the browser**

With no device: all buttons disabled. With a device attached: confirm dialog appears before sending emergency commands; calibrate dialog shows the real `CAL` result; car length shows the real `CFG` echo after submit.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Controls.tsx frontend/src/App.tsx
git commit -m "feat: emergency, calibrate, and car-length controls"
```

---

## Task 16: Session stats panel and final layout assembly

**Files:**
- Create: `frontend/src/components/StatsPanel.tsx`
- Modify: `frontend/src/App.tsx` (final grid layout per spec section 6)

**Interfaces:**
- Consumes: `getStats` (Task 8).
- Produces: `<StatsPanel />` (self-polling every 5 s) — completes the dashboard composition described in spec section 6.

- [ ] **Step 1: Write `frontend/src/components/StatsPanel.tsx`**

```tsx
import { useEffect, useState } from "react";
import { getStats } from "../api";

interface Stats {
  switches_total: number;
  switches_by_reason: Record<string, number>;
  avg_green_ms: Record<string, number>;
  avg_wait_ms: Record<string, number>;
  max_wait_ms: Record<string, number>;
  green_share: Record<string, number>;
  emergencies: number;
  faults: number;
  session_uptime_s: number;
}

export function StatsPanel() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [noSession, setNoSession] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const s = (await getStats()) as unknown as Stats;
        if (!cancelled) { setStats(s); setNoSession(false); }
      } catch {
        if (!cancelled) setNoSession(true);
      }
    }
    poll();
    const id = setInterval(poll, 5000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  if (noSession || !stats) {
    return <div className="rounded-2xl border border-border bg-panel p-4 text-gray-500">No session data yet</div>;
  }

  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="font-semibold">Session stats</div>
      <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-sm">
        <div>switches: {stats.switches_total}</div>
        <div>emergencies: {stats.emergencies}</div>
        <div>faults: {stats.faults}</div>
        <div>uptime: {stats.session_uptime_s.toFixed(0)}s</div>
        <div>avg green A/B: {stats.avg_green_ms.A.toFixed(0)} / {stats.avg_green_ms.B.toFixed(0)} ms</div>
        <div>green share A/B: {(stats.green_share.A * 100).toFixed(0)}% / {(stats.green_share.B * 100).toFixed(0)}%</div>
        <div>avg wait A/B: {stats.avg_wait_ms.A.toFixed(0)} / {stats.avg_wait_ms.B.toFixed(0)} ms</div>
        <div>max wait A/B: {stats.max_wait_ms.A.toFixed(0)} / {stats.max_wait_ms.B.toFixed(0)} ms</div>
      </div>
      <div className="mt-2 text-xs text-gray-400">
        switches by reason: {Object.entries(stats.switches_by_reason).map(([k, v]) => `${k}:${v}`).join(", ") || "none yet"}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Assemble the final `frontend/src/App.tsx` layout**

```tsx
import { useEffect, useState } from "react";
import { useLiveState } from "./useLiveState";
import { getHistory } from "./api";
import { TopBar } from "./components/TopBar";
import { JunctionView } from "./components/JunctionView";
import { LaneCard } from "./components/LaneCard";
import { DecisionPanel } from "./components/DecisionPanel";
import { LiveChart } from "./components/LiveChart";
import { EventLog } from "./components/EventLog";
import { Controls } from "./components/Controls";
import { StatsPanel } from "./components/StatsPanel";
import type { Telemetry } from "./types";

export default function App() {
  const { telemetry, link, config, events, isStale } = useLiveState();
  const [history, setHistory] = useState<Telemetry[]>([]);

  useEffect(() => {
    const id = setInterval(() => { getHistory(300).then(setHistory); }, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen bg-bg text-[#E6E9EE]">
      <TopBar link={link} mode={telemetry?.mode ?? null} deviceMs={telemetry?.ms ?? null} isStale={isStale} />
      <main className="grid grid-cols-[2fr_1fr] gap-4 p-6">
        <div className="space-y-4">
          <section className="rounded-2xl border border-border bg-panel p-4" style={{ height: 420 }}>
            <JunctionView telemetry={isStale ? telemetry : telemetry} config={config} />
          </section>
          <div className="grid grid-cols-2 gap-4">
            <LaneCard name="Lane A" direction="from bottom" sensorType="HC-SR04" lane={telemetry?.a ?? null} history={history} nowMs={telemetry?.ms ?? 0} />
            <LaneCard name="Lane B" direction="from right" sensorType="VL53L0X" lane={telemetry?.b ?? null} history={history} nowMs={telemetry?.ms ?? 0} />
          </div>
          <LiveChart history={history} />
          <EventLog events={events} />
        </div>
        <div className="space-y-4">
          <DecisionPanel telemetry={telemetry} config={config} />
          <Controls link={link} config={config} />
          <StatsPanel />
        </div>
      </main>
    </div>
  );
}
```

Note: `isStale` greys values via the TopBar pill and is passed to `JunctionView` as-is (same `telemetry` either way) because the spec requires freezing — not blanking — values while stale; `JunctionView`/`LaneCard` already show "—"/"No device" only when `telemetry` is `null`, which satisfies rule 1.2 (no device → dash) distinctly from rule 1.3 (stale → frozen, greyed).

- [ ] **Step 3: Add the grey-out-when-stale styling**

```tsx
// wrap the two inner <div className="space-y-4"> content areas that show live numbers
// with a conditional class, e.g. on JunctionView's wrapping <section>:
<section className={`rounded-2xl border border-border bg-panel p-4 ${isStale ? "opacity-50" : ""}`} style={{ height: 420 }}>
```
Apply the same `isStale ? "opacity-50" : ""` treatment to the lane-card grid wrapper.

- [ ] **Step 4: Build and verify**

Run: `cd frontend && npm run build`
Expected: build succeeds, `frontend/dist/` is created.

Run: `python run.py` (repo root)
Expected: dashboard loads at `http://127.0.0.1:8000` showing all panels; with no Arduino, every panel shows "No device"/dash/"No telemetry yet" and nothing animates.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/StatsPanel.tsx frontend/src/App.tsx
git commit -m "feat: session stats panel and final dashboard layout"
```

---

## Task 17: Forbidden-pattern sweep and done-when checklist

**Files:**
- Modify: none expected (remediation only if the sweep finds something)

**Interfaces:**
- Consumes: the whole tree from Tasks 1–16.
- Produces: a verified, clean tree satisfying spec rule 1.7 and the Done-when checklist (spec section 8).

- [ ] **Step 1: Run the forbidden-pattern sweep outside `tests/`**

```bash
grep -RinE "random|mock|fake|dummy|faker|sample|demo|simulate" \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=tests --exclude-dir=dist \
  backend frontend/src run.py
```

Expected: no output. If anything matches, remove or rename it (e.g. a stray comment using the word "sample" meaning "measurement sample" is fine only if it's prose in a comment, not a code path that fabricates data — read every hit and fix the ones that are actual fake-data code paths).

- [ ] **Step 2: Run the full backend test suite**

```bash
pytest tests/ -v
```

Expected: all tests from Tasks 2–6 pass (38 tests total).

- [ ] **Step 3: Run the full frontend test suite**

```bash
cd frontend && npx vitest run
```

Expected: all tests from Tasks 8–14 pass.

- [ ] **Step 4: Manually verify the hardware-dependent done-when items**

Using the physical rig from `WIRING_AND_SETUP.md`:
1. Unplug the Arduino, start `python run.py` — confirm "No device connected", no numbers, no chart points (spec Done-when #1).
2. Plug it in — confirm detection within 3 s and a `BOOT` line in the event log, no restart needed (#2).
3. Put 2 cars in a lane — confirm queue/car count update within ~0.3 s (#3).
4. Let a real switch happen — confirm the event log reason matches the device and the junction lights match the physical LEDs (#4).
5. Press an emergency button — confirm the physical LED changes and the UI countdown matches `emgLeft` (#5).
6. Unplug USB mid-run — confirm "Signal lost" within 1 s and greyed, frozen values (#6).
7. Confirm `/api/stats` only reflects the current session (restart the backend, confirm stats reset to a fresh session) (#7).

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: forbidden-pattern sweep and done-when verification"
```
