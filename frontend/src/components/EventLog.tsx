import type { EventMsg } from "../types";
import { describeEvent, eventColor } from "../eventText";

export function EventLog({ events }: { events: EventMsg[] }) {
  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="font-semibold">Event log</div>
      <ul className="mt-2 max-h-64 overflow-y-auto space-y-1 text-sm font-mono">
        {events.length === 0 && <li className="text-gray-500">No events yet</li>}
        {events.map((ev, i) => (
          <li key={i} className={eventColor(ev)}>
            [{new Date(((ev.host_ts as number) ?? Date.now() / 1000) * 1000).toLocaleTimeString()}] {describeEvent(ev)}
          </li>
        ))}
      </ul>
    </div>
  );
}
