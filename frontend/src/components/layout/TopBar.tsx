"use client";

import { Search, ChevronDown, User } from "lucide-react";
import { useAppStore } from "@/store/app-store";
import { Button } from "@/components/ui/button";

interface TopBarProps {
  onOpenCommandPalette: () => void;
}

export function TopBar({ onOpenCommandPalette }: TopBarProps) {
  const { activeProject } = useAppStore();

  return (
    <header className="h-14 border-b border-slate-800 bg-slate-950 flex items-center justify-between px-4">
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center">
            <span className="text-white text-xs font-bold">CG</span>
          </div>
          <span className="text-slate-50 font-semibold text-sm">Context Graph</span>
        </div>
      </div>

      {/* Center: Search trigger */}
      <button
        onClick={onOpenCommandPalette}
        className="flex items-center gap-2 h-9 w-80 px-3 rounded-md border border-slate-800 bg-slate-900 text-slate-400 text-sm hover:border-slate-700 transition-colors"
      >
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border border-slate-700 bg-slate-800 px-1.5 font-mono text-[10px] font-medium text-slate-400">
          <span className="text-xs">Ctrl</span>K
        </kbd>
      </button>

      {/* Right: Project selector + User */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="text-slate-400 hover:text-slate-50 gap-1">
          <span className="font-mono text-xs">{activeProject}</span>
          <ChevronDown className="h-3 w-3" />
        </Button>

        <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center">
          <User className="h-4 w-4 text-slate-400" />
        </div>
      </div>
    </header>
  );
}
