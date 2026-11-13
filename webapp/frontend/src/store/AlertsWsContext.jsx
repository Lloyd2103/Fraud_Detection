import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';

const AlertsWsContext = createContext(null);

export function AlertsWsProvider({ children }) {
  const { user } = useAuth();
  const [isLiveWs, setIsLiveWs] = useState(false);
  const [summary, setSummary] = useState(null);
  const [lastEvent, setLastEvent] = useState(null);
  const [alertsList, setAlertsList] = useState(null);
  const wsRef = useRef(null);

  const sendWs = useCallback((msgObj) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(msgObj));
      } catch (err) {
        console.error('Failed to send WS message:', err);
      }
    }
  }, []);

  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;
    let isMounted = true;

    const connect = () => {
      if (!isMounted) return;
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = window.location.host;
      const inspParam = user?.id ? String(user.id) : (user?.username || user?.email || '');
      const wsUrl = `${wsProtocol}//${wsHost}/ws/alerts${inspParam ? `?inspector_id=${encodeURIComponent(inspParam)}` : ''}`;

      try {
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;
      } catch (e) {
        setIsLiveWs(false);
        if (isMounted) reconnectTimer = setTimeout(connect, 3000);
        return;
      }

      ws.onopen = () => {
        if (!isMounted) {
          try { ws.close(); } catch (_) {}
          return;
        }
        setIsLiveWs(true);
        try {
          ws.send(JSON.stringify({ action: 'FETCH_ALERTS', status: 'PENDING' }));
        } catch (_) {}
      };

      ws.onmessage = (evt) => {
        if (!isMounted) return;
        try {
          const payload = JSON.parse(evt.data);
          setLastEvent(payload);

          if (payload.summary) {
            setSummary((prev) => ({ ...prev, ...payload.summary }));
          }
          if (payload.type === 'ALERT_LIST' || payload.type === 'HEARTBEAT') {
            if (Array.isArray(payload.alerts)) {
              setAlertsList(payload);
            }
          }
        } catch (_) {}
      };

      ws.onclose = () => {
        if (isMounted) {
          setIsLiveWs(false);
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        try { ws.close(); } catch (_) {}
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null;
        ws.onerror = null;
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.onopen = () => {
            try { ws.close(); } catch (_) {}
          };
        } else if (ws.readyState === WebSocket.OPEN) {
          try { ws.close(); } catch (_) {}
        }
      }
      wsRef.current = null;
    };
  }, [user?.id, user?.username, user?.email]);

  return (
    <AlertsWsContext.Provider value={{ isLiveWs, summary, setSummary, lastEvent, alertsList, sendWs }}>
      {children}
    </AlertsWsContext.Provider>
  );
}

export const useAlertsWs = () => {
  const ctx = useContext(AlertsWsContext);
  return ctx;
};

export default AlertsWsContext;

