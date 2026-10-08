import { useEffect, useRef, useState } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { Telemetry } from "../types";
import { toUplotSeries } from "../chartData";

export function LiveChart({ history }: { history: Telemetry[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const plotRef = useRef<uPlot | null>(null);
  const [windowSeconds, setWindowSeconds] = useState(120);

  useEffect(() => {
    if (!ref.current) return;
    const opts: uPlot.Options = {
      width: 640,
      height: 220,
      scales: { x: { time: false } },
      series: [
        {},
        { label: "Lane A cars", stroke: "#38BDF8" },
        { label: "Lane B cars", stroke: "#F59E0B" },
      ],
    };
    plotRef.current = new uPlot(opts, [[], [], []], ref.current);
    return () => plotRef.current?.destroy();
  }, []);

  useEffect(() => {
    if (!plotRef.current) return;
    const cutoffMs = history.length ? history[history.length - 1].ms - windowSeconds * 1000 : 0;
    const windowed = history.filter((t) => t.ms >= cutoffMs);
    plotRef.current.setData(toUplotSeries(windowed));
  }, [history, windowSeconds]);

  return (
    <div className="rounded-2xl border border-border bg-panel p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="font-semibold">Cars over time</div>
        <div className="flex gap-1 text-xs">
          {[60, 120, 300].map((s) => (
            <button
              key={s}
              onClick={() => setWindowSeconds(s)}
              className={`rounded px-2 py-1 ${windowSeconds === s ? "bg-accent text-black" : "bg-black/30 text-gray-400"}`}
            >
              {s}s
            </button>
          ))}
        </div>
      </div>
      {history.length === 0 ? (
        <div className="flex h-[220px] items-center justify-center text-gray-500">No telemetry yet</div>
      ) : (
        <div ref={ref} />
      )}
    </div>
  );
}
