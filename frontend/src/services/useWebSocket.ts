import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws';
const RECONNECT_INTERVAL_MS = 2000;
const MAX_RECONNECT_ATTEMPTS = 10;

export function useWebSocket(onMessage: (data: any) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onMessageRef = useRef(onMessage);

  // Keep the latest callback ref to avoid re-triggering effects
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        console.log('[WebSocket] Connected to backend');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current(data);
        } catch (e) {
          console.error('[WebSocket] Error parsing message', e);
        }
      };

      ws.onerror = (e) => {
        console.error('[WebSocket] Error', e);
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('[WebSocket] Disconnected');
        
        // Automatic Reconnection
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_INTERVAL_MS * Math.pow(1.5, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current += 1;
          console.log(`[WebSocket] Reconnecting in ${Math.round(delay)}ms... (Attempt ${reconnectAttemptsRef.current})`);
          setTimeout(connect, delay);
        } else {
          setError(new Error('Max WebSocket reconnect attempts reached. Please check the backend server.'));
        }
      };
    } catch (e: any) {
      setError(e);
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        // Prevent onclose logic when unmounting
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      console.warn('[WebSocket] Cannot send message, not connected');
    }
  }, []);

  return { isConnected, error, sendMessage };
}
