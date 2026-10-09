import { useEffect, useState } from "react";
import { getStats } from "../api";

interface Stats {
  switches_total: number;
  switches_by_reason: Record<string, number>;
  avg_green_ms: Record<string, number>;
  avg_wait_ms: Record<string, number>;
  max_wait_ms: Record<string, number>;
  green_share: Record<string, number>;
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
        <div>avg green A/B: {stats.avg_green_ms.A.toFixed(0)} / {stats.avg_green_ms.B.toFixed(0)} ms</div>
        <div>green share A/B: {(stats.green_share.A * 100).toFixed(0)}% / {(stats.green_share.B * 100).toFixed(0)}%</div>
        <div>avg wait A/B: {stats.avg_wait_ms.A.toFixed(0)} / {stats.avg_wait_ms.B.toFixed(0)} ms</div>
        <div>max wait A/B: {stats.max_wait_ms.A.toFixed(0)} / {stats.max_wait_ms.B.toFixed(0)} ms</div>
      </div>
      <div className="mt-2 text-xs text-gray-400">
        switches by reason: {Object.entries(stats.switches_by_reason).map(([k, v]) => `${k}:${v}`).join(", ") || "none yet"}
      </div>
    </div>
  );
}
