"use client";

import { createContext, useCallback, useContext, useState } from "react";

interface ChatContextValue {
  activeConvId: string | undefined;
  setActiveConvId: (id: string | undefined) => void;
  refreshTrigger: number;
  triggerRefresh: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [activeConvId, setActiveConvId] = useState<string | undefined>();
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const triggerRefresh = useCallback(() => setRefreshTrigger((n) => n + 1), []);

  return (
    <ChatContext.Provider
      value={{ activeConvId, setActiveConvId, triggerRefresh, refreshTrigger }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used within ChatProvider");
  return ctx;
}
