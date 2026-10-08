import { useEffect, useRef, useState } from "react";
import { getEvents, getStatus } from "./api";
import { useWebSocket, type WsMessage } from "./useWebSocket";
import type { Config, EventMsg, LinkStatus, Telemetry } from "./types";

const STALE_AFTER_MS = 1000;

export function computeIsStale(lastPacketAtMs: number | null, nowMs: number): boolean {
  if (lastPacketAtMs === null) return true;
  return nowMs - lastPacketAtMs >= STALE_AFTER_MS;
}

export function useLiveState() {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [link, setLink] = useState<LinkStatus | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [events, setEvents] = useState<EventMsg[]>([]);
  const [now, setNow] = useState<number>(Date.now());
  const lastPacketAtRef = useRef<number | null>(null);

  useEffect(() => {
    getStatus().then((s) => {
      setLink(s.link);
      setTelemetry(s.telemetry);
      setConfig(s.config);
      if (s.telemetry) lastPacketAtRef.current = Date.now();
    });
    getEvents(100).then(setEvents);
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, []);

  const wsUrl = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
  useWebSocket(wsUrl, (msg: WsMessage) => {
    if (msg.kind === "tel") {
      setTelemetry(msg.data as Telemetry);
      lastPacketAtRef.current = Date.now();
    } else if (msg.kind === "evt") {
      setEvents((prev) => [msg.data as EventMsg, ...prev].slice(0, 200));
      const ev = msg.data as EventMsg;
      if (ev.ev === "BOOT" || ev.ev === "CFG") setConfig(ev as unknown as Config);
    } else if (msg.kind === "link") {
      setLink(msg.data as LinkStatus);
    }
  });

  const isStale = computeIsStale(lastPacketAtRef.current, now);

  return { telemetry, link, config, events, isStale };
}
