import type { WSMessage } from "@/types";
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from "./auth";

function getWsBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace("http://", "ws://").replace(
      "https://",
      "wss://",
    );
  }
  // No env var: derive from current page origin (works behind CloudFront)
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}`;
  }
  return "ws://localhost:8000";
}

export type WSCallbacks = {
  onToken: (token: string) => void;
  onDone: (conversationId: string) => void;
  onError: (msg: string) => void;
  onStatusChange?: (connected: boolean) => void;
};

// Ping every 25s so ALB (60s idle timeout) never closes an idle connection.
const PING_INTERVAL_MS = 25_000;

async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "";
    const res = await fetch(`${base}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    saveTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export class ChatSocket {
  private ws: WebSocket | null = null;
  private destroyed = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private requestInFlight = false;
  private pingTimer: ReturnType<typeof setInterval> | null = null;

  constructor(private callbacks: WSCallbacks) {
    this.connect();
  }

  private connect() {
    if (this.destroyed) return;

    const token = getAccessToken();
    if (!token) return;

    try {
      this.ws = new WebSocket(`${getWsBase()}/ws/chat?token=${token}`);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectDelay = 1000; // reset backoff on success
      this.callbacks.onStatusChange?.(true);
      this.startPing();
    };

    this.ws.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        if (data.type === "token") this.callbacks.onToken(data.content);
        else if (data.type === "done") {
          this.requestInFlight = false;
          this.callbacks.onDone(data.conversation_id);
        } else if (data.type === "error") {
          this.requestInFlight = false;
          this.callbacks.onError(data.content);
        }
        // "pong" frames are silently ignored
      } catch {
        // malformed message — ignore
      }
    };

    this.ws.onerror = () => {
      // error is always followed by onclose — handle reconnect there
    };

    this.ws.onclose = (event) => {
      this.stopPing();
      this.callbacks.onStatusChange?.(false);
      if (this.requestInFlight) {
        this.requestInFlight = false;
        this.callbacks.onError("Connection lost. Please try again.");
      }
      // 4001 = auth failure — try refreshing the token once, then reconnect
      if (event.code === 4001) {
        refreshAccessToken().then((ok) => {
          if (ok) {
            this.scheduleReconnect();
          } else {
            // Refresh failed — force re-login
            clearTokens();
            if (typeof window !== "undefined") window.location.href = "/";
          }
        });
        return;
      }
      this.scheduleReconnect();
    };
  }

  private startPing() {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: "ping" }));
        } catch {
          // ignore — onclose will handle reconnect
        }
      }
    }, PING_INTERVAL_MS);
  }

  private stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect() {
    if (this.destroyed) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // cap at 30s
      this.connect();
    }, this.reconnectDelay);
  }

  send(message: string, conversationId?: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.requestInFlight = true;
      this.ws.send(
        JSON.stringify({ message, conversation_id: conversationId }),
      );
      return true;
    }
    return false;
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  destroy() {
    this.destroyed = true;
    this.stopPing();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}
