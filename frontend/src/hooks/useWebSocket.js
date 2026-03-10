import { useEffect, useRef, useState, useCallback } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export function useWebSocket(restaurantId, token, onMessage) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const pingTimerRef = useRef(null);
  const onMessageRef = useRef(onMessage);

  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);

  const connect = useCallback(() => {
    if (!restaurantId || !token || wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = BACKEND_URL.replace(/^http/, 'ws') + `/api/ws/${restaurantId}?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Ping every 30s to keep alive
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type !== 'pong' && onMessageRef.current) {
          onMessageRef.current(msg);
        }
      } catch { /* ignore */ }
    };

    ws.onclose = () => {
      setConnected(false);
      clearInterval(pingTimerRef.current);
      // Reconnect after 3s
      reconnectTimerRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [restaurantId, token]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      clearInterval(pingTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { connected };
}
