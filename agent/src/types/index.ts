export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  google_connected: boolean;
  timezone: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  messages: Message[];
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "tool" | "error";
  content: string;
  created_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  reply: string;
}

export interface Email {
  id: string;
  subject: string;
  from: string;
  to: string;
  date: string;
  snippet: string;
  body: string;
  body_html: string;
  label_ids: string[];
}

export interface CalendarEvent {
  id: string;
  title: string;
  description: string;
  start: string;
  end: string;
  attendees: string[];
  location: string;
  html_link: string;
  status: string | null;
}

export interface MemoryNode {
  id: string;
  memory_type: "semantic" | "procedural" | "episodic";
  content: string;
  source: string | null;
  importance: number;
  access_count: number;
  created_at: string;
}

export interface MemorySearchResult {
  memory: MemoryNode;
  similarity: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type WSMessage =
  | { type: "token"; content: string }
  | { type: "thinking"; content: string }
  | { type: "done"; conversation_id: string }
  | { type: "error"; content: string };
