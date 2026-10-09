import { useEffect, useState } from "react";
import { getStats } from "../api";
import { fmtMs, fmtPct } from "../statsFormat";

interface Stats {
  switches_total: number;
  switches_by_reason: Record<string, number>;
  avg_green_ms: Record<string, number | null>;
  avg_wait_ms: Record<string, number | null>;
  max_wait_ms: Record<string, number | null>;
  green_share: Record<string, number | null>;
  emergencies: number;
  faults: number;
  session_uptime_s: number;
}

export function StatsPanel() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [noSession, setNoSession] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const s = (await getStats()) as unknown as Stats;
        if (!cancelled) { setStats(s); setNoSession(false); }
      } catch {
        if (!cancelled) setNoSession(true);
      }
    }
    poll();
    const id = setInterval(poll, 5000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  if (noSession || !stats) {
    return <div className="rounded-2xl border border-border bg-panel p-4 text-gray-500">No session data yet</div>;
  }

  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="font-semibold">Session stats</div>
      <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-sm">
        <div>switches: {stats.switches_total}</div>
        <div>emergencies: {stats.emergencies}</div>
        <div>faults: {stats.faults}</div>
        <div>uptime: {stats.session_uptime_s.toFixed(0)}s</div>
        <div>avg green A/B: {fmtMs(stats.avg_green_ms.A)} / {fmtMs(stats.avg_green_ms.B)}</div>
        <div>green share A/B: {fmtPct(stats.green_share.A)} / {fmtPct(stats.green_share.B)}</div>
        <div>avg wait A/B: {fmtMs(stats.avg_wait_ms.A)} / {fmtMs(stats.avg_wait_ms.B)}</div>
        <div>max wait A/B: {fmtMs(stats.max_wait_ms.A)} / {fmtMs(stats.max_wait_ms.B)}</div>
      </div>
      <div className="mt-2 text-xs text-gray-400">
        switches by reason: {Object.entries(stats.switches_by_reason).map(([k, v]) => `${k}:${v}`).join(", ") || "none yet"}
      </div>
    </div>
  );
}
