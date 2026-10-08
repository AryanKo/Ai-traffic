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
