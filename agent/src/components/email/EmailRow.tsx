"use client";

import type { Email } from "@/types";

interface EmailRowProps {
  email: Email;
  onClick: () => void;
  selected: boolean;
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000)
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (diff < 604800000) return d.toLocaleDateString([], { weekday: "short" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

function fromName(from: string) {
  const match = from.match(/^(.+?)\s*</);
  return match ? match[1].replace(/"/g, "") : from.split("@")[0];
}

export function EmailRow({ email, onClick, selected }: EmailRowProps) {
  const isUnread = email.label_ids.includes("UNREAD");

  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        w-full text-left px-4 py-3.5 border-b border-surface-hover transition-colors relative
        ${selected ? "bg-surface-active" : "bg-white hover:bg-surface-sidebar"}
      `}
    >
      {/* Unread indicator */}
      {isUnread && !selected && (
        <span className="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-accent" />
      )}

      <div className="flex items-baseline justify-between gap-2 mb-1">
        <span
          className={`text-[13px] truncate ${isUnread ? "font-bold text-text-primary" : "font-medium text-text-secondary"}`}
        >
          {fromName(email.from)}
        </span>
        <span className="text-[10px] text-text-muted shrink-0 font-medium">
          {formatDate(email.date)}
        </span>
      </div>
      <p
        className={`text-xs truncate mb-0.5 ${isUnread ? "font-semibold text-text-primary" : "text-text-secondary"}`}
      >
        {email.subject}
      </p>
      <p className="text-[11px] text-text-muted truncate">{email.snippet}</p>
    </button>
  );
}
