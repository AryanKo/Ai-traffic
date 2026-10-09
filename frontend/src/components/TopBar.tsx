import type { LinkStatus } from "../types";

function linkLabel(link: LinkStatus | null, isStale: boolean): string {
  if (!link || !link.connected) return "No device";
  if (!link.booted) return "Booting";
  if (isStale) return "Signal lost";
  return `Connected ${link.port ?? ""}`.trim();
}

export function TopBar({ link, mode, sim, deviceMs, isStale }: {
  link: LinkStatus | null;
  mode: string | null;
  sim: boolean;
  deviceMs: number | null;
  isStale: boolean;
}) {
  const label = linkLabel(link, isStale);
  const pillClass = label.startsWith("Connected")
    ? "bg-go/20 text-go"
    : label === "Signal lost"
      ? "bg-clear/20 text-clear"
      : "bg-stop/20 text-stop";

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-3">
      <div className="text-lg font-semibold">TrafficMind Lite</div>
      <div className="flex items-center gap-4 font-mono text-sm">
        <span className={`rounded-full px-3 py-1 ${pillClass}`}>{label}</span>
        <span>{link ? `${link.pps.toFixed(1)} pkt/s` : "—"}</span>
        <span>
          {link && link.last_packet_age !== null ? `last ${link.last_packet_age.toFixed(1)}s ago` : "—"}
        </span>
        {sim ? (
          // The one place the dashboard states how it is being driven right now.
          <span className="rounded-md border border-clear bg-clear/20 px-3 py-1 font-sans font-semibold text-clear">
            Smart Traffic System using LEDs to simulate traffic signals.
          </span>
        ) : (
          <span className="rounded px-2 py-1 bg-panel border border-border">{mode ?? "—"}</span>
        )}
        <span>{deviceMs !== null ? `up ${(deviceMs / 1000).toFixed(0)}s` : "—"}</span>
      </div>
    </header>
  );
}
