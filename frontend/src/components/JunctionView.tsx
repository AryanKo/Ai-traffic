import { isNoQueue } from "../types";
import type { Config, Telemetry } from "../types";
import { queueFraction } from "../junctionGeometry";

const W = 480;
const H = 480;

function SignalHead({ go, cx, cy }: { go: boolean; cx: number; cy: number }) {
  return <circle cx={cx} cy={cy} r={10} fill={go ? "#22C55E" : "#EF4444"} />;
}

export function JunctionView({ telemetry, config }: { telemetry: Telemetry | null; config: Config | null }) {
  if (!telemetry) {
    return (
      <div className="flex h-full items-center justify-center text-gray-500">
        No device connected — no junction data
      </div>
    );
  }

  const a = telemetry.a;
  const b = telemetry.b;
  const laneLenPx = 180;
  const fracA = queueFraction(a.line, a.q);
  const fracB = queueFraction(b.line, b.q);
  const goA = telemetry.g === "A";
  const goB = telemetry.g === "B";
  const allRed = telemetry.g === "X";
  const emergency = telemetry.mode === "EMERGENCY";

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={`h-full w-full ${emergency ? "outline outline-2 outline-clear" : ""}`}>
      {/* Lane A: from bottom, heading up */}
      <rect x={W / 2 - 24} y={H / 2} width={48} height={laneLenPx} fill="#161A20" />
      {a.line === 0 ? (
        <text x={W / 2} y={H / 2 + laneLenPx / 2} fill="#9CA3AF" fontSize="12" textAnchor="middle">Not calibrated</text>
      ) : (
        <rect
          x={W / 2 - 24}
          y={H / 2 + laneLenPx * (1 - fracA)}
          width={48}
          height={laneLenPx * fracA}
          fill="#38BDF822"
        />
      )}
      {a.ok === 0 && <rect x={W / 2 - 24} y={H / 2} width={48} height={laneLenPx} fill="url(#hatch)" />}
      <SignalHead go={goA} cx={W / 2} cy={H / 2} />
      <text x={W / 2} y={H / 2 - 16} fontSize="11" fill="#9CA3AF" textAnchor="middle">
        {isNoQueue(a.raw, a.q) ? "No queue" : `${(a.q / 10).toFixed(0)} cm`}
      </text>

      {/* Lane B: from right, heading left */}
      <rect x={W / 2} y={H / 2 - 24} width={laneLenPx} height={48} fill="#161A20" />
      {b.line === 0 ? (
        <text x={W / 2 + laneLenPx / 2} y={H / 2 - 30} fill="#9CA3AF" fontSize="12" textAnchor="middle">Not calibrated</text>
      ) : (
        <rect
          x={W / 2}
          y={H / 2 - 24}
          width={laneLenPx * fracB}
          height={48}
          fill="#38BDF822"
        />
      )}
      {b.ok === 0 && <rect x={W / 2} y={H / 2 - 24} width={laneLenPx} height={48} fill="url(#hatch)" />}
      <SignalHead go={goB} cx={W / 2} cy={H / 2} />
      <text x={W / 2 + laneLenPx / 2} y={H / 2 - 32} fontSize="11" fill="#9CA3AF" textAnchor="middle">
        {isNoQueue(b.raw, b.q) ? "No queue" : `${(b.q / 10).toFixed(0)} cm`}
      </text>

      {allRed && (
        <text x={W / 2} y={30} fill="#F59E0B" fontSize="14" textAnchor="middle">
          ALL RED — clearing
        </text>
      )}
      {emergency && (
        <text x={W / 2} y={50} fill="#F59E0B" fontSize="13" textAnchor="middle">
          Emergency priority: Lane {telemetry.emg}, {(telemetry.emgLeft / 1000).toFixed(0)}s left
        </text>
      )}

      <defs>
        <pattern id="hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <rect width="8" height="8" fill="transparent" />
          <line x1="0" y1="0" x2="0" y2="8" stroke="#EF4444" strokeWidth="2" />
        </pattern>
      </defs>
    </svg>
  );
}
