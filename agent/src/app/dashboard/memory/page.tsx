"use client";

import { Brain, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Header } from "@/components/layout/Header";
import { MemoryCard } from "@/components/memory/MemoryCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import type { MemoryNode, MemorySearchResult } from "@/types";

type FilterType = "all" | "semantic" | "procedural" | "episodic";

const FILTERS: FilterType[] = ["all", "semantic", "procedural", "episodic"];

function MemorySkeleton() {
  return (
    <div className="p-4 rounded-lg border border-border bg-white space-y-2.5">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-20 rounded-full" />
        <Skeleton className="h-3 w-12" />
      </div>
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryNode[]>([]);
  const [searchResults, setSearchResults] = useState<
    MemorySearchResult[] | null
  >(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);

  async function loadMemories(f: FilterType) {
    setLoading(true);
    setSearchResults(null);
    try {
      const data = await api.memory.list(f === "all" ? undefined : f);
      setMemories(data);
    } catch {
      setMemories([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMemories(filter);
  }, [filter]);

  async function handleSearch() {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    try {
      const results = await api.memory.search(query, 20);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }

  function clearSearch() {
    setQuery("");
    setSearchResults(null);
  }

  async function handleDelete(id: string) {
    try {
      await api.memory.delete(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
      if (searchResults) {
        setSearchResults(
          (prev) => prev?.filter((r) => r.memory.id !== id) ?? null,
        );
      }
    } catch {
      /* noop */
    }
  }

  const displayItems = searchResults
    ? searchResults.map((r) => ({ node: r.memory, similarity: r.similarity }))
    : memories.map((m) => ({ node: m, similarity: undefined }));

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="Memory"
        description="Everything your assistant has learned about you"
      />

      {/* Controls bar */}
      <div className="px-6 py-3 border-b border-border flex items-center gap-3 shrink-0 bg-white">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted pointer-events-none" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Semantic search…"
              className="w-full h-8 pl-8 pr-2.5 text-xs rounded-md border border-border
                bg-surface-sidebar placeholder:text-text-muted focus:outline-none
                focus:border-accent focus:ring-1 focus:ring-accent/20 transition-colors"
            />
          </div>
          <button
            type="button"
            onClick={handleSearch}
            disabled={searching || !query.trim()}
            className="px-3 h-8 text-xs font-medium rounded-md bg-text-primary text-white
              hover:bg-[#333] transition-colors disabled:opacity-40"
          >
            {searching ? "…" : "Search"}
          </button>
          {searchResults !== null && (
            <button
              type="button"
              onClick={clearSearch}
              className="text-xs text-text-secondary hover:text-text-primary transition-colors font-medium"
            >
              Clear
            </button>
          )}
        </div>

        {searchResults === null && (
          <div className="flex items-center gap-1 ml-auto">
            {FILTERS.map((f) => (
              <button
                type="button"
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full capitalize transition-all
                  ${
                    filter === f
                      ? "bg-text-primary text-white shadow-sm"
                      : "text-text-secondary hover:bg-surface-hover"
                  }`}
              >
                {f}
              </button>
            ))}
          </div>
        )}

        {searchResults !== null && (
          <span className="ml-auto text-xs text-text-muted font-medium">
            {searchResults.length} result{searchResults.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Memory grid */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <MemorySkeleton key={i} />
            ))}
          </div>
        ) : displayItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center pt-24 gap-3">
            <div className="w-12 h-12 rounded-2xl bg-surface-sidebar flex items-center justify-center">
              <Brain className="w-6 h-6 text-text-muted" />
            </div>
            <p className="text-sm font-medium text-text-primary">
              {searchResults !== null ? "No matches found" : "No memories yet"}
            </p>
            <p className="text-xs text-text-muted">
              {searchResults !== null
                ? "Try a different search term"
                : "Start chatting to build your assistant's memory"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {displayItems.map(({ node, similarity }) => (
              <MemoryCard
                key={node.id}
                memory={node}
                similarity={similarity}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
