"use client";

import { ArrowUp, Loader2 } from "lucide-react";
import { type KeyboardEvent, useRef, useState } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled,
  placeholder = "Message your assistant…",
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const msg = value.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setValue("");
    if (ref.current) ref.current.style.height = "auto";
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function onInput() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  const hasText = value.trim().length > 0;

  return (
    <div className="pt-2">
      <div className="relative">
        <div
          className={`
          flex flex-col bg-white rounded-2xl border transition-all duration-150
          shadow-[0_2px_12px_rgba(0,0,0,0.06)] hover:shadow-[0_4px_16px_rgba(0,0,0,0.10)]
          ${disabled ? "border-border opacity-80" : "border-border-strong focus-within:border-[#c0c0c0] focus-within:shadow-[0_4px_16px_rgba(0,0,0,0.10)]"}
        `}
        >
          {/* Textarea */}
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKeyDown}
            onInput={onInput}
            disabled={disabled}
            placeholder={placeholder}
            rows={1}
            style={{ outline: "none", boxShadow: "none" }}
            className="w-full bg-transparent resize-none text-[15px] text-text-primary
              placeholder:text-text-muted leading-relaxed
              disabled:cursor-not-allowed min-h-13 max-h-50
              px-4 pt-3.5 pb-2"
          />

          {/* Bottom bar — actions */}
          <div className="flex items-center justify-between px-3 pb-2.5">
            <span className="text-[11px] text-text-muted select-none">
              <kbd className="px-1.5 py-0.5 bg-surface-hover rounded text-[10px] border border-border font-sans">
                ↵
              </kbd>{" "}
              send &nbsp;·&nbsp;{" "}
              <kbd className="px-1.5 py-0.5 bg-surface-hover rounded text-[10px] border border-border font-sans">
                ⇧↵
              </kbd>{" "}
              new line
            </span>

            {/* Send button */}
            <button
              type="button"
              onClick={submit}
              disabled={!hasText || disabled}
              className={`
                w-8 h-8 rounded-full flex items-center justify-center transition-all duration-150
                ${
                  hasText && !disabled
                    ? "bg-text-primary text-white hover:bg-[#333] shadow-sm hover:scale-105 active:scale-95"
                    : "bg-[#e8e8e8] text-[#b0b0b0] cursor-not-allowed"
                }
              `}
            >
              {disabled ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ArrowUp className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
