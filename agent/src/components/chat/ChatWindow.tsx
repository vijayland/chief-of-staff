"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { ChatSocket } from "@/lib/ws";
import type { Message } from "@/types";
import { ChatInput } from "./ChatInput";
import { MessageBubble, StreamingBubble } from "./MessageBubble";

interface ChatWindowProps {
  conversationId?: string;
  userName?: string;
  onConversationCreated?: (id: string) => void;
}

export function ChatWindow({
  conversationId,
  userName,
  onConversationCreated,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [activeConvId, setActiveConvId] = useState(conversationId);
  const wsRef = useRef<ChatSocket | null>(null);
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [_wsConnected, setWsConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const hasSentRef = useRef(false);
  // Tracks whether the next conversationId change is from a freshly created conversation
  // (so we skip reloading history we already have from streaming)
  const skipNextHistoryLoadRef = useRef(false);
  // Stable refs so WS callbacks always see latest values without recreating the socket
  const onConversationCreatedRef = useRef(onConversationCreated);
  const conversationIdRef = useRef(conversationId);
  const streamingRef = useRef("");

  useEffect(() => {
    onConversationCreatedRef.current = onConversationCreated;
  });
  useEffect(() => {
    conversationIdRef.current = conversationId;
  }, [conversationId]);

  // Load history when the selected conversation changes
  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      setActiveConvId(undefined);
      return;
    }
    if (skipNextHistoryLoadRef.current) {
      skipNextHistoryLoadRef.current = false;
      setActiveConvId(conversationId);
      return;
    }
    // Clear immediately so old messages don't flash while loading
    setMessages([]);
    setIsHistoryLoading(true);
    api.chat
      .conversation(conversationId)
      .then((conv) => setMessages(conv.messages ?? []))
      .catch(() =>
        setMessages([
          errorMessage(
            "Failed to load conversation history. Please try again.",
          ),
        ]),
      )
      .finally(() => setIsHistoryLoading(false));
    setActiveConvId(conversationId);
  }, [conversationId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Init WebSocket once — auto-reconnects on drop, destroyed on unmount
  useEffect(() => {
    const socket = new ChatSocket({
      onToken: (token) => {
        streamingRef.current += token;
        setStreaming((prev) => prev + token);
      },
      onDone: (convId) => {
        if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
        const content = streamingRef.current;
        streamingRef.current = "";
        setStreaming("");
        if (content) {
          setMessages((msgs) => [
            ...msgs,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content,
              created_at: new Date().toISOString(),
            },
          ]);
        }
        setIsLoading(false);
        setActiveConvId(convId);
        if (!conversationIdRef.current) {
          skipNextHistoryLoadRef.current = true;
          onConversationCreatedRef.current?.(convId);
        }
      },
      onError: (msg: string) => {
        if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
        streamingRef.current = "";
        setStreaming("");
        setIsLoading(false);
        if (hasSentRef.current) {
          setMessages((prev) => [
            ...prev,
            errorMessage(msg || "Something went wrong. Please try again."),
          ]);
        }
      },
      onStatusChange: (connected) => setWsConnected(connected),
    });
    wsRef.current = socket;
    return () => {
      if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
      socket.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSend(message: string) {
    hasSentRef.current = true;
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        created_at: new Date().toISOString(),
      },
    ]);
    setIsLoading(true);
    setStreaming("");
    streamingRef.current = "";

    // Safety net: if no response in 45s, surface an error instead of infinite dots.
    if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
    loadingTimeoutRef.current = setTimeout(() => {
      streamingRef.current = "";
      setStreaming("");
      setIsLoading(false);
      setMessages((prev) => [
        ...prev,
        errorMessage("No response received. Please try again."),
      ]);
    }, 45_000);

    if (wsRef.current?.send(message, activeConvId)) {
      // sent via WebSocket
    } else {
      // Fallback to REST if WS not connected
      api.chat
        .send(message, activeConvId)
        .then((res) => {
          setMessages((prev) => [
            ...prev,
            {
              id: res.message_id || crypto.randomUUID(),
              role: "assistant",
              content: res.reply,
              created_at: new Date().toISOString(),
            },
          ]);
          if (!activeConvId) {
            setActiveConvId(res.conversation_id);
            onConversationCreated?.(res.conversation_id);
          }
        })
        .catch(() => {
          setMessages((prev) => [
            ...prev,
            errorMessage(
              "Failed to send message. Please check your connection and try again.",
            ),
          ]);
        })
        .finally(() => setIsLoading(false));
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
          {isHistoryLoading ? (
            <HistorySkeleton />
          ) : messages.length === 0 && !streaming ? (
            <EmptyState />
          ) : (
            <>
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} userName={userName} />
              ))}
              {(isLoading || streaming) && (
                <StreamingBubble content={streaming} />
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="max-w-3xl mx-auto w-full px-4 sm:px-6 pb-4">
        <ChatInput
          onSend={handleSend}
          disabled={isLoading || isHistoryLoading}
        />
      </div>
    </div>
  );
}

function HistorySkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* User bubble — right aligned */}
      <div className="flex justify-end">
        <div className="h-9 w-48 rounded-2xl bg-surface-hover" />
      </div>
      {/* Assistant bubble — left aligned, 3 lines */}
      <div className="flex gap-3">
        <div className="w-7 h-7 rounded-full bg-surface-hover shrink-0 mt-0.5" />
        <div className="space-y-2 flex-1 max-w-lg">
          <div className="h-3.5 w-full rounded-full bg-surface-hover" />
          <div className="h-3.5 w-5/6 rounded-full bg-surface-hover" />
          <div className="h-3.5 w-2/3 rounded-full bg-surface-hover" />
        </div>
      </div>
      {/* User bubble */}
      <div className="flex justify-end">
        <div className="h-9 w-64 rounded-2xl bg-surface-hover" />
      </div>
      {/* Assistant bubble — 4 lines */}
      <div className="flex gap-3">
        <div className="w-7 h-7 rounded-full bg-surface-hover shrink-0 mt-0.5" />
        <div className="space-y-2 flex-1 max-w-xl">
          <div className="h-3.5 w-full rounded-full bg-surface-hover" />
          <div className="h-3.5 w-4/5 rounded-full bg-surface-hover" />
          <div className="h-3.5 w-full rounded-full bg-surface-hover" />
          <div className="h-3.5 w-1/2 rounded-full bg-surface-hover" />
        </div>
      </div>
      {/* User bubble */}
      <div className="flex justify-end">
        <div className="h-9 w-36 rounded-2xl bg-surface-hover" />
      </div>
      {/* Assistant bubble — 2 lines */}
      <div className="flex gap-3">
        <div className="w-7 h-7 rounded-full bg-surface-hover shrink-0 mt-0.5" />
        <div className="space-y-2 flex-1 max-w-sm">
          <div className="h-3.5 w-full rounded-full bg-surface-hover" />
          <div className="h-3.5 w-3/4 rounded-full bg-surface-hover" />
        </div>
      </div>
    </div>
  );
}

function errorMessage(content: string) {
  return {
    id: crypto.randomUUID(),
    role: "error" as const,
    content,
    created_at: new Date().toISOString(),
  };
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center pt-16">
      <div className="w-10 h-10 rounded-[10px] bg-surface-hover flex items-center justify-center">
        <span className="text-xl">✦</span>
      </div>
      <div>
        <p className="text-sm font-medium text-text-primary">
          How can I help you today?
        </p>
        <p className="text-xs text-text-muted mt-1">
          Ask me to read emails, check your calendar, or remember something
          important.
        </p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center mt-2">
        {[
          "What's on my calendar today?",
          "Summarise my unread emails",
          "What do you remember about me?",
        ].map((hint) => (
          <span
            key={hint}
            className="px-3 py-1.5 text-xs text-text-secondary border border-border
              rounded-full bg-white hover:bg-surface-sidebar cursor-default"
          >
            {hint}
          </span>
        ))}
      </div>
    </div>
  );
}
