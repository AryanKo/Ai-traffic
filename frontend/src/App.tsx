import { useLiveState } from "./useLiveState";
import { TopBar } from "./components/TopBar";
import { JunctionView } from "./components/JunctionView";

export default function App() {
  const { telemetry, link, config, isStale } = useLiveState();

  return (
    <div className="min-h-screen bg-bg text-[#E6E9EE]">
      <TopBar
        link={link}
        mode={telemetry?.mode ?? null}
        deviceMs={telemetry?.ms ?? null}
        isStale={isStale}
      />
      <main className="grid grid-cols-[2fr_1fr] gap-4 p-6">
        <section className="rounded-2xl border border-border bg-panel p-4" style={{ height: 520 }}>
          <JunctionView telemetry={telemetry} config={config} />
        </section>
      </main>
    </div>
  );
}
