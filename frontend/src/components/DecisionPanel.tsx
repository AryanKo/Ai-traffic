import type { Config, Telemetry } from "../types";
import { evaluateRules } from "../ruleCheck";

const WHY_TEXT: Record<string, string> = {
  BOOT: "Startup default",
  GAP_OUT: "The green lane ran out of cars",
  PRESSURE: "The other lane had built up more demand",
  MAX_GREEN: "The green lane hit its time limit",
  EMERGENCY: "Emergency priority was requested",
};

function goText(g: Telemetry["g"]): string {
  if (g === "X") return "none (all red)";
  if (g === "AB") return "Lanes A and B";
  return `Lane ${g}`;
}

export function DecisionPanel({ telemetry, config }: { telemetry: Telemetry | null; config: Config | null }) {
  if (!telemetry || !config) {
    return <div className="rounded-2xl border border-border bg-panel p-4 text-gray-500">No device connected</div>;
  }
  const rules = evaluateRules(telemetry, config);
  const progressPct = Math.min(100, (telemetry.pt / config.maxG) * 100);
  const minGreenPct = (config.minG / config.maxG) * 100;

  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="font-semibold">Decision</div>
      <div className="mt-1 text-sm">GO: {goText(telemetry.g)} — green for {(telemetry.pt / 1000).toFixed(1)}s</div>
      <div className="relative mt-2 h-2 rounded bg-black/40">
        <div className="absolute h-2 rounded bg-accent" style={{ width: `${progressPct}%` }} />
        <div className="absolute top-0 h-2 w-px bg-white/60" style={{ left: `${minGreenPct}%` }} />
      </div>
      <div className="mt-2 text-sm text-gray-400">Last switch: {telemetry.why} — {WHY_TEXT[telemetry.why] ?? ""}</div>

      <div className="mt-3 text-xs uppercase text-gray-500">Live rule check, from latest readings</div>
      <ul className="mt-1 space-y-1 text-sm">
        {rules.map((r) => (
          <li key={r.id} className="flex justify-between">
            <span className={r.pass ? "text-go" : "text-gray-500"}>{r.pass ? "✓" : "✗"} {r.label}</span>
            <span className="font-mono text-xs text-gray-500">{r.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
