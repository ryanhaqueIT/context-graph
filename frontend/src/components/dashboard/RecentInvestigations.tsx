"use client";

import { useEffect, useState } from "react";
import { FileSearch, Clock, AlertCircle, Loader2, Pause } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { recentInvestigations } from "@/lib/sample-data";
import { fetchChanges } from "@/lib/api";
import type { Investigation } from "@/lib/sample-data";
import type { Change } from "@/lib/types";

function changeToInvestigation(change: Change, index: number): Investigation {
  const statusMap: Record<string, Investigation["status"]> = {
    add: "completed",
    modify: "running",
    delete: "failed",
  };
  return {
    id: change.id || `inv-api-${index}`,
    title: change.description || `Change in ${change.file}`,
    status: statusMap[change.type] || "completed",
    agent: change.author || "Code Explorer",
    timestamp: change.timestamp || "recently",
    duration: `${change.lines_changed || 0} lines`,
    filesExplored: 1,
    findings: change.lines_changed || 0,
  };
}

function StatusBadge({ status }: { status: Investigation["status"] }) {
  const config = {
    completed: { variant: "success" as const, label: "Completed" },
    running: { variant: "info" as const, label: "Running" },
    failed: { variant: "error" as const, label: "Failed" },
    paused: { variant: "warning" as const, label: "Paused" },
  };
  const { variant, label } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}

function StatusIcon({ status }: { status: Investigation["status"] }) {
  const config = {
    completed: <FileSearch className="h-4 w-4 text-emerald-400" />,
    running: <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />,
    failed: <AlertCircle className="h-4 w-4 text-rose-400" />,
    paused: <Pause className="h-4 w-4 text-amber-400" />,
  };
  return config[status];
}

export function RecentInvestigations() {
  const [investigations, setInvestigations] = useState<Investigation[]>(recentInvestigations);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const changes = await fetchChanges(undefined, 6);
      if (cancelled) return;
      if (changes.length > 0) {
        setInvestigations(changes.map(changeToInvestigation));
      }
      // else keep sample data
      setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold text-slate-50">
          Recent Investigations
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 p-0 px-2 pb-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 text-slate-600 animate-spin" />
          </div>
        ) : (
          investigations.map((inv) => (
            <div
              key={inv.id}
              className="flex items-center gap-3 px-4 py-3 rounded-md hover:bg-slate-800/50 cursor-pointer transition-colors group"
            >
              <StatusIcon status={inv.status} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate group-hover:text-slate-50">
                  {inv.title}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-slate-500">{inv.agent}</span>
                  <span className="text-xs text-slate-600">|</span>
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {inv.duration}
                  </span>
                  <span className="text-xs text-slate-600">|</span>
                  <span className="text-xs text-slate-500">
                    {inv.filesExplored} files, {inv.findings} findings
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={inv.status} />
                <span className="text-xs text-slate-600">{inv.timestamp}</span>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
