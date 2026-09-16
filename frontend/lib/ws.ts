"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "./api";
import type { WSMessage } from "./types";

function wsUrl(): string {
  return API_BASE.replace(/^http/, "ws") + "/ws/events";
}

/**
 * Single WebSocket connection per hook instance (build spec §5.4). Pass an
 * onMessage callback to react to every message as it arrives — most pages
 * use this to append to local state rather than re-fetching on every event.
 */
export function useEventStream(onMessage: (msg: WSMessage) => void) {
  const [connected, setConnected] = useState(false);
  const callbackRef = useRef(onMessage);
  callbackRef.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    function connect() {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) retryTimer = setTimeout(connect, 2000);
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (evt) => {
        try {
          const msg: WSMessage = JSON.parse(evt.data);
          callbackRef.current(msg);
        } catch {
          /* ignore malformed frames */
        }
      };
    }

    connect();
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
      ws?.close();
    };
  }, []);

  return { connected };
}
