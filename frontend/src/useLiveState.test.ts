import { describe, it, expect } from "vitest";
import { computeIsStale } from "./useLiveState";

describe("computeIsStale", () => {
  it("is not stale right after a packet arrives", () => {
    expect(computeIsStale(1000, 1000)).toBe(false);
  });
  it("is not stale at exactly 999ms", () => {
    expect(computeIsStale(1000, 1999)).toBe(false);
  });
  it("is stale past 1000ms with no new packet", () => {
    expect(computeIsStale(1000, 2001)).toBe(true);
  });
  it("is stale when there has never been a packet", () => {
    expect(computeIsStale(null, 2001)).toBe(true);
  });
});
