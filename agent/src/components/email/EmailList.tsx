"use client";

import {
  ChevronLeft,
  ChevronRight,
  Inbox,
  Loader2,
  Reply,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import type { Email } from "@/types";
import { EmailRow } from "./EmailRow";

const PAGE_SIZE = 20;

function linkifyText(text: string) {
  const parts = text.split(/(<https?:\/\/[^>]+>|https?:\/\/\S+)/g);
  return parts.map((part, i) => {
    const angleMatch = part.match(/^<(https?:\/\/.+)>$/);
    const url = angleMatch
      ? angleMatch[1]
      : part.match(/^https?:\/\//)
        ? part
        : null;
    if (url) {
      return (
        <a
          key={i}
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-accent underline break-all"
        >
          {url}
        </a>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function HtmlEmailFrame({ html }: { html: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    const doc = iframe.contentDocument;
    if (!doc) return;
    doc.open();
    doc.write(`<!DOCTYPE html><html><head><style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
             font-size: 13px; color: #1a1a1a; margin: 0; padding: 0; word-break: break-word; }
      a { color: #4f46e5; }
      img { max-width: 100%; height: auto; }
    </style></head><body>${html}</body></html>`);
    doc.close();
    const resize = () => {
      if (iframe.contentDocument?.body) {
        iframe.style.height = `${iframe.contentDocument.body.scrollHeight + 32}px`;
      }
    };
    iframe.onload = resize;
    setTimeout(resize, 200);
  }, [html]);

  return (
    <iframe
      ref={iframeRef}
      sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
      className="w-full border-0 min-h-40"
      title="Email content"
    />
  );
}

function EmailBody({ email }: { email: Email }) {
  if (email.body_html) {
    return <HtmlEmailFrame html={email.body_html} />;
  }
  const text = email.body || email.snippet;
  return (
    <div className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap wrap-break-word">
      {linkifyText(text)}
    </div>
  );
}

function EmailSkeleton() {
  return (
    <div className="px-4 py-3 border-b border-surface-hover">
      <div className="flex items-center justify-between mb-1.5">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-2.5 w-10" />
      </div>
      <Skeleton className="h-2.5 w-3/4 mb-1.5" />
      <Skeleton className="h-2 w-full" />
    </div>
  );
}

export function EmailList() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [selected, setSelected] = useState<Email | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  // Stack of page tokens: index 0 = page 1 token (undefined = first page)
  const [tokenStack, setTokenStack] = useState<(string | null)[]>([null]);
  const [nextToken, setNextToken] = useState<string | null>(null);

  async function load(q: string, pageToken: string | null, isAppend = false) {
    if (isAppend) setLoadingMore(true);
    else setLoading(true);
    try {
      const data = await api.email.list(q, PAGE_SIZE, pageToken ?? undefined);
      if (isAppend) {
        setEmails((prev) => [...prev, ...data.emails]);
      } else {
        setEmails(data.emails);
      }
      setNextToken(data.next_page_token);
    } catch {
      if (!isAppend) setEmails([]);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    load("", null);
  }, [load]);

  function handleSearch() {
    setPage(1);
    setTokenStack([null]);
    setNextToken(null);
    load(query, null);
  }

  function goNext() {
    if (!nextToken) return;
    const newPage = page + 1;
    const newStack = [...tokenStack, nextToken];
    setPage(newPage);
    setTokenStack(newStack);
    setSelected(null);
    load(query, nextToken);
  }

  function goPrev() {
    if (page <= 1) return;
    const newPage = page - 1;
    const newStack = tokenStack.slice(0, -1);
    const token = newStack[newStack.length - 1] ?? null;
    setPage(newPage);
    setTokenStack(newStack);
    setSelected(null);
    load(query, token);
  }

  async function trash(id: string) {
    await api.email.trash(id);
    setEmails((prev) => prev.filter((e) => e.id !== id));
    if (selected?.id === id) setSelected(null);
  }

  return (
    <div className="flex h-full">
      {/* List panel */}
      <div className="w-80 shrink-0 flex flex-col border-r border-border">
        {/* Search */}
        <div className="px-3 py-2.5 border-b border-border bg-white">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search emails…"
              className="w-full h-8 pl-8 pr-3 text-xs rounded-md border border-border
                bg-surface-sidebar placeholder:text-text-muted focus:outline-none
                focus:border-accent focus:ring-1 focus:ring-accent/20 transition-colors"
            />
          </div>
        </div>

        {/* Email rows */}
        <div className="flex-1 overflow-y-auto bg-white">
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => <EmailSkeleton key={i} />)
          ) : emails.length === 0 ? (
            <div className="flex flex-col items-center justify-center pt-16 gap-2">
              <Inbox className="w-8 h-8 text-border-strong" />
              <p className="text-xs text-text-muted">No emails found</p>
            </div>
          ) : (
            emails.map((email) => (
              <EmailRow
                key={email.id}
                email={email}
                selected={selected?.id === email.id}
                onClick={() => setSelected(email)}
              />
            ))
          )}
        </div>

        {/* Pagination footer */}
        {!loading && emails.length > 0 && (
          <div className="px-3 py-2 border-t border-border bg-white flex items-center justify-between shrink-0">
            <button
              type="button"
              onClick={goPrev}
              disabled={page <= 1}
              className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium rounded-md
                text-text-secondary hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Prev
            </button>

            <span className="text-[11px] font-semibold text-text-muted">
              Page {page}
            </span>

            <button
              type="button"
              onClick={goNext}
              disabled={!nextToken || loadingMore}
              className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium rounded-md
                text-text-secondary hover:bg-surface-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              {loadingMore ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <>
                  Next <ChevronRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Detail panel */}
      <div className="flex-1 overflow-y-auto bg-white">
        {selected ? (
          <div className="p-6 max-w-2xl">
            <div className="flex items-start justify-between mb-4 gap-4">
              <h2 className="text-base font-bold text-text-primary leading-snug">
                {selected.subject}
              </h2>
              <button
                onClick={() => setSelected(null)}
                className="shrink-0 p-1.5 rounded-md hover:bg-surface-hover text-text-muted hover:text-text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 mb-5 pb-5 border-b border-border text-xs">
              <span className="text-text-muted font-medium">From</span>
              <span className="text-text-secondary">{selected.from}</span>
              <span className="text-text-muted font-medium">To</span>
              <span className="text-text-secondary">{selected.to}</span>
              <span className="text-text-muted font-medium">Date</span>
              <span className="text-text-secondary">
                {new Date(selected.date).toLocaleString()}
              </span>
            </div>

            <EmailBody email={selected} />

            <div className="flex gap-2 mt-6 pt-4 border-t border-border">
              <Button size="sm" variant="secondary">
                <Reply className="w-3.5 h-3.5" /> Reply
              </Button>
              <Button
                size="sm"
                variant="danger"
                onClick={() => trash(selected.id)}
              >
                <Trash2 className="w-3.5 h-3.5" /> Trash
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
            <div className="w-10 h-10 rounded-xl bg-surface-sidebar flex items-center justify-center">
              <Inbox className="w-5 h-5 text-text-muted" />
            </div>
            <p className="text-sm font-medium text-text-primary">
              Select an email
            </p>
            <p className="text-xs text-text-muted">
              Click any email on the left to read it
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
