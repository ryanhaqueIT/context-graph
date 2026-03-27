"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Inbox,
  Bug,
  Zap,
  GitPullRequest,
  Network,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/app-store";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip";

const navItems = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/chat", label: "AI Chat", icon: MessageSquare },
  { href: "/inbox", label: "Inbox", icon: Inbox },
  { href: "/debug", label: "Debug", icon: Bug },
  { href: "/simulations", label: "Simulations", icon: Zap },
  { href: "/reviews", label: "PR Reviews", icon: GitPullRequest },
  { href: "/graph", label: "Graph Explorer", icon: Network },
];

const bottomItems = [
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useAppStore();

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex flex-col h-full bg-slate-950 border-r border-slate-800 transition-all duration-300 ease-in-out",
          sidebarCollapsed ? "w-16" : "w-56"
        )}
      >
        {/* Nav items */}
        <nav className="flex-1 py-4 space-y-1 px-2">
          {navItems.map((item) => {
            const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                      isActive
                        ? "bg-slate-800 text-slate-50"
                        : "text-slate-400 hover:text-slate-50 hover:bg-slate-800/50"
                    )}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                    {!sidebarCollapsed && <span>{item.label}</span>}
                  </Link>
                </TooltipTrigger>
                {sidebarCollapsed && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}

          <Separator className="my-3 bg-slate-800" />

          {bottomItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            const Icon = item.icon;

            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                      isActive
                        ? "bg-slate-800 text-slate-50"
                        : "text-slate-400 hover:text-slate-50 hover:bg-slate-800/50"
                    )}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                    {!sidebarCollapsed && <span>{item.label}</span>}
                  </Link>
                </TooltipTrigger>
                {sidebarCollapsed && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}
        </nav>

        {/* Collapse toggle */}
        <div className="p-2 border-t border-slate-800">
          <button
            onClick={toggleSidebar}
            className="flex items-center justify-center w-full py-2 rounded-md text-slate-400 hover:text-slate-50 hover:bg-slate-800/50 transition-colors"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <ChevronLeft className="h-5 w-5" />
            )}
          </button>
        </div>
      </aside>
    </TooltipProvider>
  );
}
