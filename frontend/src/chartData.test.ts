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
