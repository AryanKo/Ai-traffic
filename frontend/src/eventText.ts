import type { EventMsg } from "./types";

export function describeEvent(ev: EventMsg): string {
  switch (ev.ev) {
    case "SWITCH": {
      const secs = (ev.greenMs as number) / 1000;
      return `Switched ${ev.from} to ${ev.to} after ${secs.toFixed(1)} s: ${ev.why} (A ${(ev.pA as number).toFixed(1)}, B ${(ev.pB as number).toFixed(1)})`;
    }
    case "GREEN":
      return `Lane ${ev.lane} got green: ${ev.why}`;
    case "EMG_ON":
      return `Emergency priority requested for lane ${ev.lane}`;
    case "EMG_OFF":
      return `Emergency priority ended for lane ${ev.lane} (${ev.why})`;
    case "FAULT":
      return `Lane ${ev.lane} sensor fault`;
    case "RECOVER":
      return `Lane ${ev.lane} sensor recovered`;
    case "CAL":
      return `Calibrated: A ${ev.lineA}mm (ok=${ev.okA}), B ${ev.lineB}mm (ok=${ev.okB})`;
    case "BOOT":
      return "Device booted";
    case "CFG":
      return "Config updated";
    case "ERR":
      return `Device error: ${ev.msg}`;
    default:
      return String(ev.ev);
  }
}

export function eventColor(ev: EventMsg): string {
  if (ev.ev === "FAULT" || ev.ev === "ERR") return "text-stop";
  if (ev.ev === "EMG_ON" || ev.ev === "EMG_OFF") return "text-clear";
  if (ev.ev === "SWITCH" || ev.ev === "GREEN") return "text-accent";
  return "text-gray-400";
}
