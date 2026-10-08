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
