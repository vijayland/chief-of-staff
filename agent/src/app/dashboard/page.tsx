"use client";

import { useEffect, useState } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { useChatContext } from "@/lib/chat-context";
import { api } from "@/lib/api";
import type { User } from "@/types";

export default function ChatPage() {
  const { activeConvId, setActiveConvId, triggerRefresh } = useChatContext();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api.auth.me().then(setUser).catch(() => null);
  }, []);

  const isNew = activeConvId === "__new__";

  return (
    <ChatWindow
      conversationId={isNew ? undefined : activeConvId}
      userName={user?.full_name}
      onConversationCreated={(id) => {
        setActiveConvId(id);
        triggerRefresh();
      }}
    />
  );
}
