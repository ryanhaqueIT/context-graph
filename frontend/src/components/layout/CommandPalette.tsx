"use client";

import { useEffect } from "react";
import { Command } from "cmdk";
import {
  LayoutDashboard,
  MessageSquare,
  Inbox,
  Bug,
  Zap,
  GitPullRequest,
  Network,
  Settings,
} from "lucide-react";
import { useRouter } from "next/navigation";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const pages = [
  { name: "Home", href: "/", icon: LayoutDashboard },
  { name: "AI Chat", href: "/chat", icon: MessageSquare },
  { name: "Inbox", href: "/inbox", icon: Inbox },
  { name: "Debug", href: "/debug", icon: Bug },
  { name: "Simulations", href: "/simulations", icon: Zap },
  { name: "PR Reviews", href: "/reviews", icon: GitPullRequest },
  { name: "Graph Explorer", href: "/graph", icon: Network },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg">
        <Command
          className="rounded-lg border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden"
          onKeyDown={(e: React.KeyboardEvent) => {
            if (e.key === "Escape") onOpenChange(false);
          }}
        >
          <Command.Input
            placeholder="Search pages, symbols, files..."
            className="w-full h-12 px-4 bg-transparent text-slate-50 text-sm placeholder:text-slate-500 outline-none border-b border-slate-800"
            autoFocus
          />
          <Command.List className="max-h-72 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-slate-500">
              No results found.
            </Command.Empty>

            <Command.Group heading="Pages" className="text-xs text-slate-500 px-2 py-1.5">
              {pages.map((page) => {
                const Icon = page.icon;
                return (
                  <Command.Item
                    key={page.href}
                    value={page.name}
                    onSelect={() => {
                      router.push(page.href);
                      onOpenChange(false);
                    }}
                    className="flex items-center gap-3 px-3 py-2 text-sm text-slate-300 rounded-md cursor-pointer data-[selected=true]:bg-slate-800 data-[selected=true]:text-slate-50"
                  >
                    <Icon className="h-4 w-4 text-slate-500" />
                    {page.name}
                  </Command.Item>
                );
              })}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
