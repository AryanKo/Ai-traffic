import { describe, it, expect } from "vitest";
import { queueFraction, signalHeadCenter } from "./junctionGeometry";

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

describe("signalHeadCenter", () => {
  it("places lane A's and lane B's heads at different points", () => {
    const a = signalHeadCenter("A", 0, 0);
    const b = signalHeadCenter("B", 0, 0);
    expect(a).not.toEqual(b);
  });
  it("offsets lane A's head along the vertical approach", () => {
    expect(signalHeadCenter("A", 100, 100)).toEqual({ x: 100, y: 112 });
  });
  it("offsets lane B's head along the horizontal approach", () => {
    expect(signalHeadCenter("B", 100, 100)).toEqual({ x: 112, y: 100 });
  });
});
