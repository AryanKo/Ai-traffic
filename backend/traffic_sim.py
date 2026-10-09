"""Simulated traffic for direct LED mode.

In direct mode the device does not read its sensors; it only reports which
LEDs are lit (la/lb, 1 = on = red). This module turns each device packet into
a telemetry packet of the usual shape: the light state is the device's real
LED state, and the queues on both lanes are simulated around it. Every packet
it produces carries "sim": true and mode "SIM".
"""
import math
import random

LINE_MM = 600            # simulated distance from sensor to stop line
DEFAULT_CAR_MM = 70
ARRIVALS_PER_S = {"A": 0.30, "B": 0.24}
DISCHARGE_S = 1.1        # one car crosses the stop line this often on green
WAIT_WEIGHT = 0.5        # same pressure formula as the firmware
MAX_GREEN_MS = 20000
NO_TARGET_MM = 30000
_LANES = ("A", "B")


class TrafficSim:
    def __init__(self, rng: random.Random | None = None, line_mm: int = LINE_MM):
        self.rng = rng or random.Random()
        self.line_mm = line_mm
        self.car_mm = DEFAULT_CAR_MM
        self.reset()

    @property
    def max_cars(self) -> int:
        return self.line_mm // self.car_mm

    def reset(self) -> None:
        self.cars = {"A": 0, "B": 0}
        self.discharge_s = {"A": 0.0, "B": 0.0}
        self.wait_start: dict[str, int | None] = {"A": None, "B": None}
        self.green_start: dict[str, int | None] = {"A": None, "B": None}
        self.go: dict[str, bool] | None = None
        self.phase_start = 0
        self.why = "BOOT"
        self.last_ms: int | None = None

    def config(self, cfg: dict) -> dict:
        """Fill in the simulated stop lines and pick up the device car length."""
        out = dict(cfg)
        if cfg.get("carMm"):
            self.car_mm = int(cfg["carMm"])
        out["lineA"] = self.line_mm
        out["lineB"] = self.line_mm
        return out

    def step(self, dev: dict) -> tuple[dict, list[dict]]:
        ms = int(dev["ms"])
        if self.last_ms is not None and ms < self.last_ms:
            self.reset()  # device restarted
        dt = 0.0 if self.last_ms is None else min(1.0, (ms - self.last_ms) / 1000)
        self.last_ms = ms
        emg = dev.get("emg", "-")
        go = {"A": dev.get("la", 1) == 0, "B": dev.get("lb", 1) == 0}

        events: list[dict] = []
        if self.go is None:
            for lane in _LANES:
                if go[lane]:
                    self.green_start[lane] = ms
            self.phase_start = ms
        elif go != self.go:
            events = self._light_change(ms, go, emg)
            self.phase_start = ms
        self.go = go

        for lane in _LANES:
            self._move_traffic(lane, ms, dt, go[lane])

        return self._telemetry(ms, dev, emg), events

    def _light_change(self, ms: int, go: dict, emg: str) -> list[dict]:
        lost = [l for l in _LANES if self.go[l] and not go[l]]
        gained = [l for l in _LANES if not self.go[l] and go[l]]
        why = self._reason(ms, lost, emg)
        self.why = why
        events = []
        for lane in lost:
            other = "B" if lane == "A" else "A"
            to = other if go[other] else "X"
            pressures = {l: self._pressure(l, ms) for l in _LANES}
            events.append({
                "type": "evt", "ms": ms, "ev": "SWITCH", "from": lane, "to": to, "why": why,
                "greenMs": self._green_for(lane, ms),
                "nA": self.cars["A"], "nB": self.cars["B"],
                "pA": round(pressures["A"], 2), "pB": round(pressures["B"], 2),
            })
            self.green_start[lane] = None
        for lane in gained:
            self.green_start[lane] = ms
            events.append({"type": "evt", "ms": ms, "ev": "GREEN", "lane": lane, "why": why})
        return events

    def _reason(self, ms: int, lost: list[str], emg: str) -> str:
        if emg != "-":
            return "EMERGENCY"
        for lane in lost:
            if self.cars[lane] == 0:
                return "GAP_OUT"
            if self._green_for(lane, ms) >= MAX_GREEN_MS:
                return "MAX_GREEN"
        return "PRESSURE"

    def _green_for(self, lane: str, ms: int) -> int:
        start = self.green_start[lane]
        return ms - start if start is not None else 0

    def _move_traffic(self, lane: str, ms: int, dt: float, go: bool) -> None:
        # Arrival rate drifts slowly so the two lanes don't look metronomic.
        drift = 1 + 0.5 * math.sin(2 * math.pi * ms / 90000 + (0 if lane == "A" else 2.1))
        if self.cars[lane] < self.max_cars and self.rng.random() < ARRIVALS_PER_S[lane] * drift * dt:
            self.cars[lane] += 1

        if go and self.cars[lane] > 0:
            self.discharge_s[lane] += dt
            if self.discharge_s[lane] >= DISCHARGE_S:
                self.cars[lane] -= 1
                self.discharge_s[lane] = 0.0
        else:
            self.discharge_s[lane] = 0.0

        if not go and self.cars[lane] > 0:
            if self.wait_start[lane] is None:
                self.wait_start[lane] = ms
        else:
            self.wait_start[lane] = None

    def _pressure(self, lane: str, ms: int) -> float:
        start = self.wait_start[lane]
        wait_s = (ms - start) / 1000 if start is not None else 0.0
        return self.cars[lane] + wait_s * WAIT_WEIGHT

    def _lane(self, lane: str, ms: int) -> dict:
        n = self.cars[lane]
        q = min(self.line_mm, n * self.car_mm)
        start = self.wait_start[lane]
        return {
            "raw": self.line_mm - q if n else NO_TARGET_MM,
            "d": self.line_mm - q if n else self.line_mm + 100,
            "q": q,
            "n": n,
            "line": self.line_mm,
            "w": ms - start if start is not None else 0,
            "p": round(self._pressure(lane, ms), 2),
            "ok": 1,
        }

    def _telemetry(self, ms: int, dev: dict, emg: str) -> dict:
        go = self.go
        g = "AB" if go["A"] and go["B"] else "A" if go["A"] else "B" if go["B"] else "X"
        return {
            "type": "tel",
            "ms": ms,
            "g": g,
            "next": "-",
            "ph": "CLEAR" if g == "X" else "GREEN",
            "pt": ms - self.phase_start,
            "mode": "EMERGENCY" if emg != "-" else "SIM",
            "why": self.why,
            "emg": emg,
            "emgLeft": dev.get("emgLeft", 0),
            "la": dev.get("la", 1),
            "lb": dev.get("lb", 1),
            "sim": True,
            "a": self._lane("A", ms),
            "b": self._lane("B", ms),
        }
