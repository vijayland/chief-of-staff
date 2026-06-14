import type {
  CalendarEvent,
  ChatResponse,
  Conversation,
  Email,
  MemoryNode,
  MemorySearchResult,
  TokenResponse,
  User,
} from "@/types";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data: TokenResponse = await res.json();
    saveTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const token = getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...init.headers,
  };

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request<T>(path, init, false);
    clearTokens();
    window.location.href = "/";
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ────────────────────────────────────────────────────────────────────
export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    register: (
      email: string,
      full_name: string,
      password: string,
      tenant_slug: string,
    ) =>
      request<TokenResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, full_name, password, tenant_slug }),
      }),

    me: () => request<User>("/api/v1/auth/me"),

    googleUrl: () =>
      request<{ url: string; state: string }>("/api/v1/auth/google"),
  },

  // ── Chat ──────────────────────────────────────────────────────────────────
  chat: {
    send: (message: string, conversation_id?: string) =>
      request<ChatResponse>("/api/v1/chat", {
        method: "POST",
        body: JSON.stringify({ message, conversation_id }),
      }),

    conversations: () => request<Conversation[]>("/api/v1/chat/conversations"),

    conversation: (id: string) =>
      request<Conversation>(`/api/v1/chat/conversations/${id}`),

    deleteConversation: (id: string) =>
      request<void>(`/api/v1/chat/conversations/${id}`, { method: "DELETE" }),
  },

  // ── Email ─────────────────────────────────────────────────────────────────
  email: {
    list: (query = "", max_results = 20, page_token?: string) => {
      const params = new URLSearchParams({
        query,
        max_results: String(max_results),
      });
      if (page_token) params.set("page_token", page_token);
      return request<{ emails: Email[]; next_page_token: string | null }>(
        `/api/v1/email?${params}`,
      );
    },

    get: (id: string) => request<Email>(`/api/v1/email/${id}`),

    send: (to: string, subject: string, body: string) =>
      request<unknown>("/api/v1/email/send", {
        method: "POST",
        body: JSON.stringify({ to, subject, body }),
      }),

    draft: (to: string, subject: string, body: string) =>
      request<unknown>("/api/v1/email/draft", {
        method: "POST",
        body: JSON.stringify({ to, subject, body }),
      }),

    trash: (id: string) =>
      request<void>(`/api/v1/email/${id}`, { method: "DELETE" }),
  },

  // ── Calendar ──────────────────────────────────────────────────────────────
  calendar: {
    events: (days_ahead = 7) =>
      request<CalendarEvent[]>(
        `/api/v1/calendar/events?days_ahead=${days_ahead}`,
      ),

    create: (
      title: string,
      start: string,
      end: string,
      description = "",
      attendees: string[] = [],
    ) =>
      request<CalendarEvent>("/api/v1/calendar/events", {
        method: "POST",
        body: JSON.stringify({ title, start, end, description, attendees }),
      }),

    delete: (id: string) =>
      request<void>(`/api/v1/calendar/events/${id}`, { method: "DELETE" }),
  },

  // ── Memory ────────────────────────────────────────────────────────────────
  memory: {
    list: (memory_type?: string) =>
      request<MemoryNode[]>(
        `/api/v1/memory${memory_type ? `?memory_type=${memory_type}` : ""}`,
      ),

    search: (query: string, top_k = 10) =>
      request<MemorySearchResult[]>("/api/v1/memory/search", {
        method: "POST",
        body: JSON.stringify({ query, top_k }),
      }),

    delete: (id: string) =>
      request<void>(`/api/v1/memory/${id}`, { method: "DELETE" }),
  },
};
