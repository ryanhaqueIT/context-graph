"use client";

import { FileText, Search, AlertCircle } from "lucide-react";
import { useChatStore } from "@/store/chat-store";

export function ContextPanel() {
  const { context } = useChatStore();

  const hasContent =
    context.files.length > 0 ||
    context.patterns.length > 0 ||
    context.problems.length > 0;

  return (
    <div className="w-64 border-r border-slate-800 bg-slate-950 p-4 space-y-5 overflow-y-auto">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Context Workspace
      </h3>

      {!hasContent && (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <FileText className="h-6 w-6 text-slate-700" />
          <p className="text-xs text-slate-600 text-center">
            Context will build up as you chat. Ask a question to get started.
          </p>
        </div>
      )}

      {/* Files Viewed */}
      {context.files.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <FileText className="h-3.5 w-3.5 text-slate-500" />
            <span className="text-xs font-medium text-slate-400">
              Files Viewed ({context.files.length})
            </span>
          </div>
          <div className="space-y-1">
            {context.files.map((file) => (
              <div
                key={file}
                className="text-xs text-slate-500 font-mono px-2 py-1 rounded bg-slate-800/30 hover:bg-slate-800/50 cursor-pointer truncate"
              >
                {file}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Patterns Found */}
      {context.patterns.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Search className="h-3.5 w-3.5 text-slate-500" />
            <span className="text-xs font-medium text-slate-400">
              Patterns Found ({context.patterns.length})
            </span>
          </div>
          <div className="space-y-1">
            {context.patterns.map((pattern) => (
              <div
                key={pattern}
                className="text-xs text-slate-500 px-2 py-1 rounded bg-slate-800/30"
              >
                {pattern}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Problems */}
      {context.problems.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <AlertCircle className="h-3.5 w-3.5 text-rose-500" />
            <span className="text-xs font-medium text-slate-400">
              Problems ({context.problems.length})
            </span>
          </div>
          <div className="space-y-1">
            {context.problems.map((problem) => (
              <div
                key={problem}
                className="text-xs text-rose-400/80 px-2 py-1 rounded bg-rose-500/5 border border-rose-500/10"
              >
                {problem}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
