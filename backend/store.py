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
    session_id INTEGER,
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
