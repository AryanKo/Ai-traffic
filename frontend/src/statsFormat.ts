export function fmtMs(v: number | null): string {
  return v === null ? "—" : `${v.toFixed(0)} ms`;
}

export function fmtPct(v: number | null): string {
  return v === null ? "—" : `${(v * 100).toFixed(0)}%`;
}
