"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Cpu, FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/store/chat-store";
import type { ChatMessage } from "@/lib/types";

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "system") {
    return (
      <div className="flex justify-center py-2">
        <span className="text-xs text-slate-500 bg-slate-800/50 px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? "bg-blue-500/20" : "bg-slate-800"
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-blue-400" />
        ) : (
          <Bot className="h-4 w-4 text-emerald-400" />
        )}
      </div>
      <div
        className={`max-w-[70%] ${
          isUser
            ? "bg-blue-500/10 border-blue-500/20"
            : "bg-slate-800/80 border-slate-700"
        } border rounded-lg px-4 py-3`}
      >
        {message.agent && (
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="outline" className="text-[10px] border-slate-700">
              <Cpu className="h-3 w-3 mr-1" />
              {message.agent}
            </Badge>
          </div>
        )}
        <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
          {message.content}
        </p>
        {message.files && message.files.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.files.map((file) => (
              <span
                key={file}
                className="inline-flex items-center gap-1 text-[10px] text-slate-400 bg-slate-900/60 px-2 py-0.5 rounded font-mono"
              >
                <FileText className="h-3 w-3" />
                {file}
              </span>
            ))}
          </div>
        )}
        <span className="text-[10px] text-slate-600 mt-2 block">
          {message.timestamp}
        </span>
      </div>
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="h-8 w-8 rounded-full flex items-center justify-center shrink-0 bg-slate-800">
        <Bot className="h-4 w-4 text-emerald-400" />
      </div>
      <div className="bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-3">
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
          <span className="text-sm text-slate-400">Thinking...</span>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  const { sendMessage } = useChatStore();

  const suggestions = [
    "Why are users getting 500 errors on checkout?",
    "What if I modify src/auth/validate.ts?",
    "Who owns the checkout module?",
    "Explain the execution path from apiGateway to processPayment",
    "What is the blast radius of src/checkout/handler.ts?",
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
      <div className="flex flex-col items-center gap-2">
        <div className="h-14 w-14 rounded-full bg-blue-500/10 flex items-center justify-center">
          <Bot className="h-7 w-7 text-blue-400" />
        </div>
        <h2 className="text-lg font-semibold text-slate-50">
          Context Graph AI
        </h2>
        <p className="text-sm text-slate-500 text-center max-w-md">
          Ask questions about your codebase. I can trace execution paths,
          analyze blast radius, find code owners, and investigate bugs.
        </p>
      </div>
      <div className="grid gap-2 w-full max-w-lg">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => sendMessage(suggestion)}
            className="text-left text-sm text-slate-400 px-4 py-2.5 rounded-lg border border-slate-800 bg-slate-900/50 hover:bg-slate-800/50 hover:text-slate-300 hover:border-slate-700 transition-colors"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ChatInterface() {
  const { messages, isLoading, sendMessage } = useChatStore();
  const [inputValue, setInputValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isLoading) return;
    setInputValue("");
    await sendMessage(trimmed);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {messages.length === 0 ? (
        <EmptyState />
      ) : (
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="space-y-4 max-w-3xl mx-auto pb-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <ThinkingIndicator />}
          </div>
        </ScrollArea>
      )}

      {/* Input */}
      <div className="border-t border-slate-800 p-4">
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your codebase..."
              disabled={isLoading}
              className="w-full h-10 px-4 pr-10 rounded-lg border border-slate-800 bg-slate-900 text-slate-50 text-sm placeholder:text-slate-500 outline-none focus:border-blue-500/50 transition-colors disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !inputValue.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 h-6 w-6 rounded-md bg-blue-500 flex items-center justify-center hover:bg-blue-400 transition-colors disabled:opacity-40 disabled:hover:bg-blue-500"
            >
              {isLoading ? (
                <Loader2 className="h-3 w-3 text-white animate-spin" />
              ) : (
                <Send className="h-3 w-3 text-white" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
