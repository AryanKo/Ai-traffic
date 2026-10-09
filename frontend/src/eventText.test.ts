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
  it("describes a SWITCH to all red", () => {
    const text = describeEvent({ type: "evt", ms: 0, ev: "SWITCH", from: "A", to: "X", why: "GAP_OUT", greenMs: 4000, nA: 0, nB: 0, pA: 0, pB: 0 });
    expect(text).toBe("Switched A to all red after 4.0 s: GAP_OUT (A 0.0, B 0.0)");
  });
  it("describes EMG_OFF reasons in plain words", () => {
    expect(describeEvent({ type: "evt", ms: 0, ev: "EMG_OFF", lane: "A", why: "MANUAL" })).toBe("Emergency priority ended for lane A (cancelled from the dashboard)");
    expect(describeEvent({ type: "evt", ms: 0, ev: "EMG_OFF", lane: "B", why: "TIMEOUT" })).toBe("Emergency priority ended for lane B (timed out)");
  });
});
