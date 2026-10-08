import type { Config, EventMsg, LinkStatus, Telemetry } from "./types";

export interface StatusResponse {
  link: LinkStatus;
  telemetry: Telemetry | null;
  config: Config | null;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export const getStatus = () => getJSON<StatusResponse>("/api/status");
export const getHistory = (seconds: number) => getJSON<Telemetry[]>(`/api/history?seconds=${seconds}`);
export const getEvents = (limit: number) => getJSON<EventMsg[]>(`/api/events?limit=${limit}`);
export const getStats = () => getJSON<Record<string, unknown>>("/api/stats");

export async function postCommand(cmd: string): Promise<{ ok: boolean; [key: string]: unknown }> {
  const res = await fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cmd }),
  });
  return await res.json();
}
