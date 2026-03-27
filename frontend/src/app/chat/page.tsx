"use client";

import { Trash2 } from "lucide-react";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { ContextPanel } from "@/components/chat/ContextPanel";
import { HivePanel } from "@/components/chat/HivePanel";
import { useChatStore } from "@/store/chat-store";

export default function ChatPage() {
  const { messages, clearMessages } = useChatStore();

  // Derive title from the first user message, or show default
  const firstUserMsg = messages.find((m) => m.role === "user");
  const title = firstUserMsg
    ? `AI Investigation: ${firstUserMsg.content.slice(0, 50)}${firstUserMsg.content.length > 50 ? "..." : ""}`
    : "AI Investigation";

  return (
    <div className="flex h-full">
      <ContextPanel />
      <div className="flex-1 flex flex-col">
        <div className="h-12 border-b border-slate-800 flex items-center justify-between px-4">
          <h1 className="text-sm font-semibold text-slate-50 truncate">
            {title}
          </h1>
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
        </div>
        <ChatInterface />
      </div>
      <HivePanel />
    </div>
  );
}
