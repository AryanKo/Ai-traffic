export function queueFraction(lineMm: number, qMm: number): number {
  if (lineMm <= 0 || qMm <= 0) return 0;
  return Math.min(1, qMm / lineMm);
}
