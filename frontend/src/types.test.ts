import { describe, it, expect } from "vitest";
import { isNoQueue } from "./types";

describe("isNoQueue", () => {
  it("treats raw 30000 as no queue", () => {
    expect(isNoQueue(30000, 0)).toBe(true);
  });
  it("treats q of 0 as no queue", () => {
    expect(isNoQueue(100, 0)).toBe(true);
  });
  it("treats a real queue as not no-queue", () => {
    expect(isNoQueue(210, 188)).toBe(false);
  });
});
