import type { Telemetry } from "./types";

export function toUplotSeries(history: Telemetry[]): [number[], number[], number[]] {
  if (history.length === 0) return [[], [], []];
  const t0 = history[0].ms;
  const x = history.map((t) => (t.ms - t0) / 1000);
  const a = history.map((t) => t.a.n);
  const b = history.map((t) => t.b.n);
  return [x, a, b];
}
