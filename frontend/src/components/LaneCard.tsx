import { isNoQueue } from "../types";
import type { LaneTelemetry, Telemetry } from "../types";
import { buildSparklinePoints } from "../sparkline";

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return <div className="h-8 text-xs text-gray-500">—</div>;
  const max = Math.max(1, ...points);
  const w = 120;
  const h = 32;
  const step = w / (points.length - 1);
  const d = points.map((v, i) => `${i === 0 ? "M" : "L"} ${i * step} ${h - (v / max) * h}`).join(" ");
  return (
    <svg width={w} height={h}>
      <path d={d} stroke="#38BDF8" fill="none" strokeWidth={1.5} />
    </svg>
  );
}

export function LaneCard({
  name, direction, sensorType, lane, history, nowMs,
}: {
  name: string;
  direction: string;
  sensorType: string;
  lane: LaneTelemetry | null;
  history: Telemetry[];
  nowMs: number;
}) {
  const points = lane ? buildSparklinePoints(history, name === "Lane A" ? "a" : "b", nowMs, 60000) : [];
  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="flex items-baseline justify-between">
        <div className="font-semibold">{name}</div>
        <div className="text-xs text-gray-500">{direction} · {sensorType}</div>
      </div>
      {!lane ? (
        <div className="mt-2 text-sm text-gray-500">—</div>
      ) : (
        <div className="mt-2 grid grid-cols-2 gap-1 font-mono text-sm">
          <div>raw: {lane.raw === 30000 ? "nothing in range" : `${lane.raw} mm`}</div>
          <div>filtered: {lane.d < 0 ? "—" : `${lane.d} mm`}</div>
          <div>queue: {isNoQueue(lane.raw, lane.q) ? "no queue" : `${(lane.q / 10).toFixed(1)} cm`}</div>
          <div>cars: {lane.n < 0 ? "—" : lane.n}</div>
          <div>waiting: {(lane.w / 1000).toFixed(1)} s</div>
          <div>pressure: {lane.p.toFixed(2)}</div>
          <div>stop line: {lane.line === 0 ? "not calibrated" : `${(lane.line / 10).toFixed(1)} cm`}</div>
          <div className={lane.ok ? "text-go" : "text-stop"}>{lane.ok ? "sensor OK" : "SENSOR FAULT"}</div>
        </div>
      )}
      <div className="mt-2"><Sparkline points={points} /></div>
    </div>
  );
}
