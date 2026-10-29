import { useEffect, useRef } from 'react';
import { wsClient } from './ws';

/**
 * Re-runs `refresh` whenever the backend broadcasts a lifecycle event over the
 * WebSocket (debounced), and also polls every `pollMs` while `polling` is true so
 * screens stay current even if the socket drops.
 */
export function useLiveRefresh(refresh: () => void, polling = false, pollMs = 3000) {
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const unsub = wsClient.on('*', (msg) => {
      if (msg?.type === 'connection.established' || msg?.type === 'subscribed') return;
      clearTimeout(timer);
      timer = setTimeout(() => refreshRef.current(), 400);
    });
    return () => {
      clearTimeout(timer);
      unsub();
    };
  }, []);

  useEffect(() => {
    if (!polling) return;
    const id = setInterval(() => refreshRef.current(), pollMs);
    return () => clearInterval(id);
  }, [polling, pollMs]);
}
