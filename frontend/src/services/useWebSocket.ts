import { useCallback, useEffect, useRef, useState } from 'react';

function resolveWebSocketUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws`;
}

const RECONNECT_INTERVAL_MS = 1500;
const MAX_RECONNECT_ATTEMPTS = 10;

export function useWebSocket(onMessage: (data: any) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const onMessageRef = useRef(onMessage);
  const aliveRef = useRef(true);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (!aliveRef.current) return;

    try {
      const ws = new WebSocket(resolveWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data));
        } catch (parseError) {
          console.warn('[Sugio WS] Ignored non-JSON event', parseError);
        }
      };

      ws.onerror = () => setIsConnected(false);

      ws.onclose = () => {
        setIsConnected(false);
        if (!aliveRef.current) return;

        if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
          setError(new Error('Live events are offline. REST features remain available.'));
          return;
        }

        const attempt = reconnectAttemptsRef.current++;
        const delay = Math.min(RECONNECT_INTERVAL_MS * Math.pow(1.45, attempt), 10000);
        reconnectTimerRef.current = window.setTimeout(connect, delay);
      };
    } catch (connectError) {
      setError(connectError instanceof Error ? connectError : new Error('WebSocket connection failed.'));
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    aliveRef.current = true;
    connect();

    return () => {
      aliveRef.current = false;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { isConnected, error, sendMessage };
}
