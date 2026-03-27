"use client";

import { Search } from "lucide-react";
import { KPICards } from "@/components/dashboard/KPICards";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { RecentInvestigations } from "@/components/dashboard/RecentInvestigations";
import { CodeHealth } from "@/components/dashboard/CodeHealth";

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* AI Prompt Input */}
      <div className="relative">
        <div className="flex items-center gap-3 p-4 rounded-lg border border-slate-800 bg-slate-900/50 hover:border-slate-700 transition-colors">
          <Search className="h-5 w-5 text-slate-500" />
          <input
            type="text"
            placeholder="Ask anything about your codebase..."
            className="flex-1 bg-transparent text-slate-50 text-sm placeholder:text-slate-500 outline-none"
          />
          <kbd className="hidden sm:inline-flex h-6 select-none items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2 font-mono text-[10px] font-medium text-slate-400">
            Enter
          </kbd>
        </div>
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* KPI Cards */}
      <KPICards />

      {/* Two column layout: Investigations + Code Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentInvestigations />
        </div>
        <div>
          <CodeHealth />
        </div>
      </div>
    </div>
  );
}
