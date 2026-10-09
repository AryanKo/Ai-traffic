export function queueFraction(lineMm: number, qMm: number): number {
  if (lineMm <= 0 || qMm <= 0) return 0;
  return Math.min(1, qMm / lineMm);
}

const SIGNAL_HEAD_OFFSET = 12;

export function signalHeadCenter(lane: "A" | "B", cx: number, cy: number): { x: number; y: number } {
  return lane === "A"
    ? { x: cx, y: cy + SIGNAL_HEAD_OFFSET }
    : { x: cx + SIGNAL_HEAD_OFFSET, y: cy };
}
