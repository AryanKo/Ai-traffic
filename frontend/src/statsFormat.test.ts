import { describe, it, expect } from "vitest";
import { fmtMs, fmtPct } from "./statsFormat";

describe("fmtMs", () => {
  it("shows an em dash for null (no real data yet)", () => {
    expect(fmtMs(null)).toBe("—");
  });
  it("formats a real number in ms", () => {
    expect(fmtMs(1234)).toBe("1234 ms");
  });
});

describe("fmtPct", () => {
  it("shows an em dash for null (no real data yet)", () => {
    expect(fmtPct(null)).toBe("—");
  });
  it("formats a fraction as a percentage", () => {
    expect(fmtPct(0.5)).toBe("50%");
  });
});
