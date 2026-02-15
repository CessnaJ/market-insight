"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface WebSocketMessage {
  type: string;
  data?: any;
  ticker?: string;
  timestamp: string;
  channels?: string[];
  message?: string;
}

interface WebSocketHookReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: any) => void;
  subscribe: (channels: string[]) => void;
  connectionStatus: "connecting" | "connected" | "disconnected" | "error";
}

export function useWebSocket(url: string): WebSocketHookReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "connected" | "disconnected" | "error">("connecting");
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setConnectionStatus("connected");
        console.log("WebSocket connected");

        // Subscribe to default channels
        ws.send(JSON.stringify({
          type: "subscribe",
          channels: ["portfolio", "thoughts", "reports"],
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          console.log("WebSocket message received:", message);
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnectionStatus("error");
      };

      ws.onclose = () => {
        setIsConnected(false);
        setConnectionStatus("disconnected");
        console.log("WebSocket disconnected");

        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("Attempting to reconnect...");
          setConnectionStatus("connecting");
          connect();
        }, 5000);
      };
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
      setConnectionStatus("error");
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket is not connected");
    }
  }, []);

  const subscribe = useCallback((channels: string[]) => {
    sendMessage({
      type: "subscribe",
      channels,
    });
  }, [sendMessage]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    subscribe,
    connectionStatus,
  };
}
