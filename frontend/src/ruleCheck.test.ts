import { describe, it, expect } from "vitest";
import { evaluateRules } from "./ruleCheck";
import type { Config, Telemetry } from "./types";

const config: Config = {
  lineA: 400, lineB: 400, carMm: 70, minG: 4000, maxG: 20000, clr: 1500,
  emgT: 30000, queueMin: 20, waitW: 0.5, margin: 1.5, faultDemand: 3, tof: 1,
};

function tel(overrides: Partial<Telemetry> = {}): Telemetry {
  return {
    type: "tel", ms: 0, g: "A", next: "-", ph: "GREEN", pt: 5000, mode: "AUTO", why: "BOOT", emg: "-", emgLeft: 0,
    a: { raw: 1, d: 1, q: 0, n: 0, line: 400, w: 0, p: 0, ok: 1 },
    b: { raw: 1, d: 1, q: 200, n: 3, line: 400, w: 2000, p: 4.0, ok: 1 },
    ...overrides,
  };
}

describe("evaluateRules", () => {
  it("min green reached passes when pt >= minG", () => {
    const rules = evaluateRules(tel({ pt: 5000 }), config);
    expect(rules.find((r) => r.id === "min_green")!.pass).toBe(true);
  });
  it("min green reached fails when pt < minG", () => {
    const rules = evaluateRules(tel({ pt: 1000 }), config);
    expect(rules.find((r) => r.id === "min_green")!.pass).toBe(false);
  });
  it("gap out passes when green lane has no cars", () => {
    const rules = evaluateRules(tel({ a: { raw: 1, d: 1, q: 0, n: 0, line: 400, w: 0, p: 0, ok: 1 } }), config);
    expect(rules.find((r) => r.id === "gap_out")!.pass).toBe(true);
  });
  it("pressure rule compares other vs green plus margin", () => {
    const rules = evaluateRules(
      tel({
        a: { raw: 1, d: 1, q: 0, n: 1, line: 400, w: 0, p: 1.0, ok: 1 },
        b: { raw: 1, d: 1, q: 200, n: 3, line: 400, w: 2000, p: 4.0, ok: 1 },
      }),
      config,
    );
    const r = rules.find((x) => x.id === "pressure")!;
    expect(r.pass).toBe(true);
    expect(r.detail).toContain("4");
    expect(r.detail).toContain("1");
  });
  it("max green reached compares pt to maxG", () => {
    const rules = evaluateRules(tel({ pt: 21000 }), config);
    expect(rules.find((r) => r.id === "max_green")!.pass).toBe(true);
  });
  it("reports both lanes moving when both have green", () => {
    const rules = evaluateRules(tel({ g: "AB" }), config);
    expect(rules).toHaveLength(1);
    expect(rules[0].id).toBe("both_go");
  });
});
