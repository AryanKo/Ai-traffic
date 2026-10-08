import { useEffect, useState } from "react";
import { useLiveState } from "./useLiveState";
import { getHistory } from "./api";
import { TopBar } from "./components/TopBar";
import { JunctionView } from "./components/JunctionView";
import { LaneCard } from "./components/LaneCard";
import { DecisionPanel } from "./components/DecisionPanel";
import type { Telemetry } from "./types";

export default function App() {
  const { telemetry, link, config, isStale } = useLiveState();
  const [history, setHistory] = useState<Telemetry[]>([]);

  useEffect(() => {
    const id = setInterval(() => { getHistory(60).then(setHistory); }, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen bg-bg text-[#E6E9EE]">
      <TopBar
        link={link}
        mode={telemetry?.mode ?? null}
        deviceMs={telemetry?.ms ?? null}
        isStale={isStale}
      />
      <main className="grid grid-cols-[2fr_1fr] gap-4 p-6">
        <div className="space-y-4">
          <section className="rounded-2xl border border-border bg-panel p-4" style={{ height: 420 }}>
            <JunctionView telemetry={telemetry} config={config} />
          </section>
          <div className="grid grid-cols-2 gap-4">
            <LaneCard name="Lane A" direction="from bottom" sensorType="HC-SR04" lane={telemetry?.a ?? null} history={history} nowMs={telemetry?.ms ?? 0} />
            <LaneCard name="Lane B" direction="from right" sensorType="VL53L0X" lane={telemetry?.b ?? null} history={history} nowMs={telemetry?.ms ?? 0} />
          </div>
        </div>
        <div className="space-y-4">
          <DecisionPanel telemetry={telemetry} config={config} />
        </div>
      </main>
    </div>
  );
}
