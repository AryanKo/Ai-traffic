import { useEffect, useRef, useState } from "react";

export interface WsMessage<T = unknown> {
  kind: "tel" | "evt" | "ack" | "link";
  data: T;
}

export function useWebSocket(url: string, onMessage: (msg: WsMessage) => void) {
  const [open, setOpen] = useState(false);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closedByUs = false;
    let retryTimer: number | undefined;

    function connect() {
      ws = new WebSocket(url);
      ws.onopen = () => setOpen(true);
      ws.onclose = () => {
        setOpen(false);
        if (!closedByUs) retryTimer = window.setTimeout(connect, 2000);
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (evt) => {
        try {
          handlerRef.current(JSON.parse(evt.data) as WsMessage);
        } catch {
          // ignore malformed frames; never show them as data
        }
      };
    }

    connect();
    return () => {
      closedByUs = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      ws?.close();
    };
  }, [url]);

  return { open };
}
