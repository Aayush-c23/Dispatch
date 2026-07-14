import { useEffect, useRef, useState } from 'react';

function operationsSocketUrl() {
  const configuredUrl = import.meta.env.VITE_OPS_WS_URL;
  if (configuredUrl) return configuredUrl;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.hostname}:8000/ws/ops`;
}

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const reconnectTimer = useRef(null);

  useEffect(() => {
    let disposed = false;
    let socket;

    function connect() {
      socket = new WebSocket(operationsSocketUrl());
      socket.onopen = () => setConnected(true);
      socket.onmessage = (event) => {
        try {
          setLastMessage(JSON.parse(event.data));
        } catch {
          // Ignore malformed messages so an unavailable backend cannot break the dashboard.
        }
      };
      socket.onclose = () => {
        setConnected(false);
        if (!disposed) reconnectTimer.current = window.setTimeout(connect, 1_000);
      };
      socket.onerror = () => socket.close();
    }

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(reconnectTimer.current);
      socket?.close();
    };
  }, []);

  return { connected, lastMessage };
}
