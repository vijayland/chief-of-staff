import { AlertCircle, Bot, RotateCcw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Avatar } from "@/components/ui/Avatar";
import type { Message } from "@/types";

interface MessageBubbleProps {
  message: Message;
  userName?: string;
  onRetry?: () => void;
}

export function MessageBubble({
  message,
  userName = "You",
  onRetry,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.role === "error";

  if (isError) {
    return (
      <div className="flex justify-center">
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm
          bg-red-50 border border-red-200 text-red-600 max-w-[80%]"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{message.content}</span>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="ml-1 flex items-center gap-1 text-red-500 hover:text-red-700
                font-medium whitespace-nowrap hover:underline"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div className="shrink-0 mt-0.5">
        {isUser ? (
          <Avatar name={userName} size="sm" />
        ) : (
          <div className="w-6 h-6 rounded-full bg-text-primary flex items-center justify-center">
            <Bot className="w-3.5 h-3.5 text-white" />
          </div>
        )}
      </div>

      <div
        className={`flex flex-col gap-0.5 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}
      >
        <span className="text-[11px] text-text-muted px-1">
          {isUser ? userName : "Assistant"}
        </span>
        <div
          className={`
            px-3 py-2 rounded-lg text-sm leading-relaxed
            ${
              isUser
                ? "bg-text-primary text-white rounded-tr-sm whitespace-pre-wrap"
                : "bg-surface-sidebar text-text-primary border border-border rounded-tl-sm prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0"
            }
          `}
        >
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}

export function StreamingBubble({ content, thinking }: { content: string; thinking?: string }) {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 mt-0.5">
        <div className="w-6 h-6 rounded-full bg-text-primary flex items-center justify-center">
          <Bot className="w-3.5 h-3.5 text-white" />
        </div>
      </div>
      <div className="flex flex-col gap-0.5 max-w-[85%] items-start">
        <span className="text-[11px] text-text-muted px-1">Assistant</span>
        <div
          className="px-3 py-2 rounded-lg rounded-tl-sm text-sm leading-relaxed
          bg-surface-sidebar text-text-primary border border-border
          prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0"
        >
          {content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          ) : thinking ? (
            <ThinkingIndicator label={thinking} />
          ) : (
            <ThinkingIndicator />
          )}
        </div>
      </div>
    </div>
  );
}

function ThinkingIndicator({ label }: { label?: string }) {
  return (
    <span className="flex items-center gap-2 py-0.5">
      <span className="flex gap-1 items-center">
        <span className="w-1.5 h-1.5 rounded-full bg-text-muted"
          style={{ animation: "claudePulse 1.4s ease-in-out infinite", animationDelay: "0ms" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-text-muted"
          style={{ animation: "claudePulse 1.4s ease-in-out infinite", animationDelay: "200ms" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-text-muted"
          style={{ animation: "claudePulse 1.4s ease-in-out infinite", animationDelay: "400ms" }} />
      </span>
      {label && (
        <span className="text-[11px] text-text-muted italic">{label}</span>
      )}
    </span>
  );
}
