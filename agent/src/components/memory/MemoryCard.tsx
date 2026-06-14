"use client";

import { Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { MemoryNode } from "@/types";

interface MemoryCardProps {
  memory: MemoryNode;
  similarity?: number;
  onDelete: (id: string) => void;
}

const typeConfig = {
  semantic: { label: "Fact", variant: "blue" as const },
  procedural: { label: "Style", variant: "purple" as const },
  episodic: { label: "Episode", variant: "green" as const },
};

const sourceLabels: Record<string, string> = {
  chat: "from chat",
  email: "from email",
  calendar: "from calendar",
  action: "from action",
};

function importanceBar(importance: number) {
  const w = Math.round(importance * 100);
  const color =
    importance > 0.7 ? "#2383e2" : importance > 0.4 ? "#d97706" : "#9ca3af";
  return { w, color };
}

export function MemoryCard({ memory, similarity, onDelete }: MemoryCardProps) {
  const config = typeConfig[memory.memory_type];
  const { w, color } = importanceBar(memory.importance);

  return (
    <div
      className="group p-4 rounded-[8px] border border-[#e5e5e5] bg-white
      hover:border-[#d1d5db] hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <Badge variant={config.variant}>{config.label}</Badge>
          {memory.source && (
            <span className="text-[11px] text-[#9ca3af]">
              {sourceLabels[memory.source] ?? memory.source}
            </span>
          )}
          {similarity !== undefined && (
            <span className="text-[11px] text-[#16a34a]">
              {Math.round(similarity * 100)}% match
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDelete(memory.id)}
          className="opacity-0 group-hover:opacity-100 p-1 rounded
            hover:bg-[#fef2f2] text-[#9ca3af] hover:text-[#dc2626] transition-all"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <p className="text-sm text-[#1a1a1a] leading-relaxed">{memory.content}</p>

      <div className="mt-3 flex items-center gap-3">
        {/* Importance bar */}
        <div className="flex items-center gap-1.5 flex-1">
          <div className="flex-1 h-1 bg-[#f0f0ef] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${w}%`, backgroundColor: color }}
            />
          </div>
          <span className="text-[11px] text-[#9ca3af]">{w}%</span>
        </div>
        <span className="text-[11px] text-[#9ca3af]">
          {new Date(memory.created_at).toLocaleDateString([], {
            month: "short",
            day: "numeric",
          })}
        </span>
      </div>
    </div>
  );
}
