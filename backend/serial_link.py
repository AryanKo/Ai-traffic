"""Port detection, background reader thread, and command writer for the Uno."""
import threading
import time
from typing import Callable, Optional

import serial
from serial.tools import list_ports

from protocol import parse_line

# USB vendor IDs of Uno boards and the USB-serial chips clones use:
# Arduino LLC, Arduino SRL, WCH CH340, Silicon Labs CP210x, FTDI.
ALLOWED_VIDS = {0x2341, 0x2A03, 0x1A86, 0x10C4, 0x0403}
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

    def _mark_disconnected(self) -> None:
        self.connected = False
        self.boot_at = None

    def _run(self) -> None:
        while not self._stop.is_set():
            port = self._port_override or find_port()
            if not port:
                self._mark_disconnected()
                time.sleep(RECONNECT_DELAY_S)
                continue
            try:
                self._ser = serial.Serial(port, self._baud, timeout=1)
                self.port_name = port
                self.connected = True
                self.boot_at = None
                self._read_loop()
            except (serial.SerialException, OSError):
                self._mark_disconnected()
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
        self._mark_disconnected()
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

        try:
            self._on_message(obj)
        except Exception:
            pass

    def pps(self) -> float:
        cutoff = time.time() - ARRIVAL_WINDOW_S
        return sum(1 for a in self._arrivals if a >= cutoff) / ARRIVAL_WINDOW_S

    def send_command(self, cmd: str, timeout: float = 2.0) -> dict:
        if not self.connected or not self._ser:
            return {"ok": False, "error": "not_connected"}
        if self.boot_at is None:
            return {"ok": False, "error": "not_booted"}
        # The firmware acks CAR:<mm> and L:<a><b> with the bare command name
        # ("CAR", "L"), so the waiter must be keyed on that, not the full text.
        ack_key = cmd.split(":", 1)[0] if cmd.startswith(("CAR:", "L:")) else cmd
        with self._write_lock:
            ack_event = threading.Event()
            self._ack_waiters[ack_key] = ack_event
            cal_event = None
            if cmd == "CAL":
                cal_event = threading.Event()
                self._cal_waiter = cal_event
                self._cal_result = None
            try:
                self._ser.write((cmd + "\n").encode("ascii"))
            except (serial.SerialException, OSError):
                self._ack_waiters.pop(ack_key, None)
                return {"ok": False, "error": "write_failed"}
            got_ack = ack_event.wait(timeout)
            self._ack_waiters.pop(ack_key, None)
            if not got_ack:
                return {"ok": False, "error": "timeout"}
            result = {"ok": True, "ack": self._ack_results.pop(ack_key, None)}
            if cmd == "CAL" and cal_event is not None:
                cal_event.wait(4.0)
                self._cal_waiter = None
                result["cal"] = self._cal_result
            return result
