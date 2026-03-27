"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

const stages = [
  { name: "All Stages", count: 47 },
  { name: "Intake", count: 12 },
  { name: "RCA", count: 8 },
  { name: "Fix", count: 15 },
  { name: "Test", count: 7 },
  { name: "Close", count: 5 },
];

const items = [
  { title: "Billing bug #427", stage: "Fix", status: "needs_approval" as const, time: "2h ago" },
  { title: "Auth investigation", stage: "RCA", status: "in_progress" as const, time: "30m ago" },
  { title: "Missing env config", stage: "Intake", status: "needs_input" as const, time: "4h ago" },
  { title: "Rate limiter fix", stage: "Test", status: "done" as const, time: "1d ago" },
  { title: "Checkout permissions", stage: "Close", status: "done" as const, time: "2d ago" },
];

const statusConfig = {
  needs_approval: { label: "Needs Approval", variant: "warning" as const },
  in_progress: { label: "In Progress", variant: "info" as const },
  needs_input: { label: "Needs Input", variant: "error" as const },
  done: { label: "Done", variant: "success" as const },
};

export default function InboxPage() {
  return (
    <div className="flex h-full">
      {/* Stage sidebar */}
      <div className="w-52 border-r border-slate-800 p-4 space-y-1">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Stages
        </h2>
        {stages.map((stage) => (
          <button
            key={stage.name}
            className="flex items-center justify-between w-full px-3 py-2 text-sm text-slate-300 rounded-md hover:bg-slate-800/50 transition-colors"
          >
            <span>{stage.name}</span>
            <span className="text-xs text-slate-600">{stage.count}</span>
          </button>
        ))}
      </div>

      {/* Item list */}
      <div className="flex-1 border-r border-slate-800 p-4 space-y-2 overflow-y-auto">
        <h2 className="text-sm font-semibold text-slate-50 mb-4">Workflow Inbox</h2>
        {items.map((item) => {
          const { label, variant } = statusConfig[item.status];
          return (
            <Card
              key={item.title}
              className="bg-slate-900 border-slate-800 p-4 cursor-pointer hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-200">{item.title}</p>
                  <p className="text-xs text-slate-500 mt-1">{item.stage} stage</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={variant}>{label}</Badge>
                  <span className="text-xs text-slate-600">{item.time}</span>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Detail panel */}
      <div className="w-80 p-4 flex items-center justify-center">
        <p className="text-sm text-slate-500">Select an item to view details</p>
      </div>
    </div>
  );
}
