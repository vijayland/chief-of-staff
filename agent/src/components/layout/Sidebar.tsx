"use client";

import {
  Brain,
  Calendar,
  Loader2,
  LogOut,
  Mail,
  MessageSquare,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/ui/Avatar";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { clearTokens } from "@/lib/auth";
import { useChatContext } from "@/lib/chat-context";
import type { Conversation, User } from "@/types";

const NAV = [
  { href: "/dashboard", icon: MessageSquare, label: "Chat" },
  { href: "/dashboard/email", icon: Mail, label: "Email" },
  { href: "/dashboard/calendar", icon: Calendar, label: "Calendar" },
  { href: "/dashboard/memory", icon: Brain, label: "Memory" },
];

const NEW_ID = "__new__";

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const { activeConvId, setActiveConvId, refreshTrigger } = useChatContext();
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConvs, setLoadingConvs] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const isChat = pathname === "/dashboard";

  useEffect(() => {
    api.auth
      .me()
      .then(setUser)
      .catch(() => null)
      .finally(() => setLoadingUser(false));
  }, []);

  useEffect(() => {
    if (!isChat) return;
    setLoadingConvs(true);
    api.chat
      .conversations()
      .then(setConversations)
      .catch(() => null)
      .finally(() => setLoadingConvs(false));
  }, [isChat, refreshTrigger]);

  function logout() {
    clearTokens();
    router.push("/");
  }
  function handleNavClick() {
    onClose?.();
  }

  function startNewChat() {
    if (activeConvId === NEW_ID) return;
    setConversations((prev) =>
      prev.some((c) => c.id === NEW_ID)
        ? prev
        : [
            {
              id: NEW_ID,
              title: "New chat",
              created_at: new Date().toISOString(),
            } as Conversation,
            ...prev,
          ],
    );
    setActiveConvId(NEW_ID);
    onClose?.();
  }

  async function deleteConv(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    if (id === NEW_ID) {
      setConversations((p) => p.filter((c) => c.id !== NEW_ID));
      setActiveConvId(undefined);
      return;
    }
    setDeletingId(id);
    try {
      await api.chat.deleteConversation(id);
      setConversations((p) => p.filter((c) => c.id !== id));
      if (activeConvId === id) setActiveConvId(undefined);
    } catch {
      /* noop */
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <aside className="w-64 lg:w-56 shrink-0 h-screen flex flex-col bg-surface-sidebar border-r border-border">
      {/* Brand */}
      <div className="px-4 pt-5 pb-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-text-primary flex items-center justify-center shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <p className="text-[13px] font-bold text-text-primary leading-tight">
              Chief of Staff
            </p>
            <p className="text-[10px] text-text-muted leading-tight">
              AI Assistant
            </p>
          </div>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="lg:hidden p-1 rounded-md text-text-muted hover:bg-surface-hover transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="px-3 pt-3 pb-1">
        <p className="px-2 mb-1.5 text-[10px] font-semibold text-text-muted uppercase tracking-widest">
          Workspace
        </p>
        <div className="space-y-0.5">
          {NAV.map(({ href, icon: Icon, label }) => {
            const active =
              pathname === href ||
              (href !== "/dashboard" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                onClick={handleNavClick}
                className={`flex items-center gap-2.5 px-2.5 py-1.75 rounded-md
                  text-[15px] font-medium leading-5 transition-all duration-100
                  ${
                    active
                      ? "bg-white text-text-primary shadow-sm border border-border"
                      : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                  }`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${active ? "text-text-primary" : "text-text-muted"}`}
                />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Conversation list — only on chat page */}
      {isChat && (
        <div className="flex-1 flex flex-col overflow-hidden px-3 pt-3">
          {/* New chat button */}
          <button
            type="button"
            onClick={startNewChat}
            className="flex items-center gap-2 w-full px-2.5 py-2 mb-2 text-xs font-semibold
              text-text-primary bg-white border border-border rounded-md shadow-sm
              hover:bg-surface-hover transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New chat
          </button>

          <p className="px-2 mb-1 text-[10px] font-semibold text-text-muted uppercase tracking-widest">
            Recents
          </p>

          <div className="flex-1 overflow-y-auto -mx-1">
            {loadingConvs ? (
              <div className="px-2 space-y-1 pt-1">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-2 px-2 py-2">
                    <Skeleton className="w-3.5 h-3.5 rounded shrink-0" />
                    <Skeleton
                      className={`h-3 ${i % 2 === 0 ? "w-24" : "w-20"}`}
                    />
                  </div>
                ))}
              </div>
            ) : conversations.length === 0 ? (
              <p className="text-center text-[11px] text-text-muted pt-4 px-3">
                No conversations yet
              </p>
            ) : (
              <div className="px-1">
                {conversations.map((conv) => {
                  const isActive =
                    activeConvId === conv.id ||
                    (activeConvId === NEW_ID && conv.id === NEW_ID);
                  const isPending = conv.id === NEW_ID;
                  return (
                    <div
                      key={conv.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => {
                        if (!isPending) {
                          setActiveConvId(conv.id);
                          onClose?.();
                        }
                      }}
                      onKeyDown={(e) =>
                        e.key === "Enter" &&
                        !isPending &&
                        setActiveConvId(conv.id)
                      }
                      className={`group flex items-center gap-2 px-2.5 py-2 mx-1 rounded-md cursor-pointer transition-all
                        ${
                          isActive
                            ? "bg-white text-text-primary shadow-sm border border-border"
                            : "hover:bg-surface-hover text-text-secondary hover:text-text-primary"
                        }`}
                    >
                      <MessageSquare
                        className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-text-primary" : "text-text-muted"}`}
                      />
                      <span
                        className={`flex-1 truncate text-xs font-medium ${isPending ? "text-text-muted italic" : ""}`}
                      >
                        {conv.title ?? "Untitled"}
                      </span>
                      <button
                        type="button"
                        disabled={deletingId === conv.id}
                        onClick={(e) => deleteConv(e, conv.id)}
                        className="opacity-0 group-hover:opacity-100 p-0.5 rounded
                          text-text-muted hover:text-danger transition-all disabled:opacity-50"
                      >
                        {deletingId === conv.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Trash2 className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Spacer for non-chat pages */}
      {!isChat && <div className="flex-1" />}

      {/* User footer */}
      <div className="px-3 pb-4 border-t border-border pt-3">
        {loadingUser ? (
          <div className="flex items-center gap-2.5 px-2 py-1.5">
            <Skeleton className="w-7 h-7 rounded-full" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-2.5 w-20" />
              <Skeleton className="h-2 w-28" />
            </div>
          </div>
        ) : user ? (
          <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-md">
            <Avatar name={user.full_name} size="sm" />
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-semibold text-text-primary truncate">
                {user.full_name}
              </p>
              <p className="text-[10px] text-text-muted truncate">
                {user.email}
              </p>
            </div>
          </div>
        ) : null}
        <button
          onClick={logout}
          className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[12px] font-medium
            text-text-secondary hover:bg-surface-hover hover:text-danger transition-colors w-full mt-1"
        >
          <LogOut className="w-3.5 h-3.5 shrink-0" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
