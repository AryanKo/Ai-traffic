import { useState } from "react";
import { postCommand } from "../api";
import type { Config, LinkStatus } from "../types";

export function Controls({ link, config }: { link: LinkStatus | null; config: Config | null }) {
  const [calOpen, setCalOpen] = useState(false);
  const [calResult, setCalResult] = useState<string | null>(null);
  const [carLenInput, setCarLenInput] = useState<string>(config ? String(config.carMm) : "");
  const [lastAck, setLastAck] = useState<string | null>(null);
  const disabled = !link || !link.connected || !link.booted;

  async function sendEmergency(cmd: string, label: string) {
    if (!window.confirm(`Send "${label}"?`)) return;
    const res = await postCommand(cmd);
    setLastAck(res.ok ? `${label}: ok` : `${label}: failed (${res.error ?? "unknown"})`);
  }

  async function runCalibrate() {
    const res = await postCommand("CAL");
    if (res.ok && res.cal) {
      const cal = res.cal as Record<string, unknown>;
      setCalResult(`A: ${(Number(cal.lineA) / 10).toFixed(1)}cm (ok=${cal.okA}), B: ${(Number(cal.lineB) / 10).toFixed(1)}cm (ok=${cal.okB})`);
    } else {
      setCalResult("Calibration failed or timed out");
    }
  }

  async function submitCarLength() {
    const mm = parseInt(carLenInput, 10);
    if (Number.isNaN(mm) || mm < 10 || mm > 500) return;
    const res = await postCommand(`CAR:${mm}`);
    setLastAck(res.ok ? `Car length set to ${mm}mm` : "Car length update failed");
  }

  return (
    <div className="rounded-2xl border border-border bg-panel p-4 space-y-4">
      <div>
        <div className="font-semibold">Emergency</div>
        <div className="mt-2 flex gap-2">
          <button disabled={disabled} onClick={() => sendEmergency("E:A", "Priority to Lane A")} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Priority to Lane A</button>
          <button disabled={disabled} onClick={() => sendEmergency("E:B", "Priority to Lane B")} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Priority to Lane B</button>
          <button disabled={disabled} onClick={() => sendEmergency("E:OFF", "Cancel emergency")} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Cancel emergency</button>
        </div>
        {lastAck && <div className="mt-1 text-xs text-gray-400">{lastAck}</div>}
      </div>

      <div>
        <div className="font-semibold">Calibrate</div>
        <button disabled={disabled} onClick={() => setCalOpen(true)} className="mt-2 rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Calibrate…</button>
        {calOpen && (
          <div className="mt-2 rounded border border-border bg-black/30 p-3 text-sm">
            <p>Remove all cars. Stand a flat card upright on each stop line, facing its sensor. Then press Calibrate. Remove the cards afterwards.</p>
            <div className="mt-2 flex gap-2">
              <button onClick={async () => { await runCalibrate(); }} className="rounded bg-accent px-3 py-1 text-black">Calibrate</button>
              <button onClick={() => setCalOpen(false)} className="rounded bg-black/30 px-3 py-1">Close</button>
            </div>
            {calResult && <div className="mt-2 text-gray-300">{calResult}</div>}
          </div>
        )}
      </div>

      <div>
        <div className="font-semibold">Car length (mm)</div>
        <div className="mt-2 flex gap-2">
          <input
            type="number"
            min={10}
            max={500}
            value={carLenInput}
            onChange={(e) => setCarLenInput(e.target.value)}
            className="w-24 rounded bg-black/30 px-2 py-1 font-mono"
          />
          <button disabled={disabled} onClick={submitCarLength} className="rounded bg-black/30 px-3 py-1 text-sm disabled:opacity-40">Set</button>
        </div>
        <div className="mt-1 text-xs text-gray-500">Current: {config ? `${config.carMm} mm` : "—"}</div>
      </div>
    </div>
  );
}
