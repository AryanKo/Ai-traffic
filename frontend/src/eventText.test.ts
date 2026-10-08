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
