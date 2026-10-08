import { useLiveState } from "./useLiveState";
import { TopBar } from "./components/TopBar";

export default function App() {
  const { telemetry, link, isStale } = useLiveState();

  return (
    <div className="min-h-screen bg-bg text-[#E6E9EE]">
      <TopBar
        link={link}
        mode={telemetry?.mode ?? null}
        deviceMs={telemetry?.ms ?? null}
        isStale={isStale}
      />
      <main className="p-6 text-sm text-gray-400">
        Dashboard panels are added in later tasks.
      </main>
    </div>
  );
}
