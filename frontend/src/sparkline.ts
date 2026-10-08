import type { Telemetry } from "./types";

export function buildSparklinePoints(
  history: Telemetry[],
  lane: "a" | "b",
  nowMs: number,
  windowMs: number,
): number[] {
  const cutoff = nowMs - windowMs;
  return history.filter((t) => t.ms > cutoff).map((t) => t[lane].n);
}
