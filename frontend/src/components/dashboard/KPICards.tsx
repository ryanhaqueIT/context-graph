"use client";

import { useEffect, useState } from "react";
import { Network, GitBranch, Brain, Shield, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { kpiData } from "@/lib/sample-data";
import { fetchStats } from "@/lib/api";
import type { StatsResponse } from "@/lib/types";

interface KPIItem {
  label: string;
  value: string;
  icon: typeof Network;
  color: string;
  bgColor: string;
}

function buildKPIs(data: StatsResponse): KPIItem[] {
  return [
    {
      label: "Total Nodes",
      value: data.total_nodes.toLocaleString(),
      icon: Network,
      color: "text-blue-400",
      bgColor: "bg-blue-500/10",
    },
    {
      label: "Total Edges",
      value: data.total_edges.toLocaleString(),
      icon: GitBranch,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
    },
    {
      label: "Decision Traces",
      value: data.decision_traces.toString(),
      icon: Brain,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
    },
    {
      label: "Coverage",
      value: `${data.coverage_percent}%`,
      icon: Shield,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
    },
  ];
}

const fallbackKPIs = buildKPIs({
  total_nodes: kpiData.totalNodes,
  total_edges: kpiData.totalEdges,
  decision_traces: kpiData.decisionTraces,
  coverage_percent: kpiData.coveragePercent,
});

export function KPICards() {
  const [kpis, setKpis] = useState<KPIItem[]>(fallbackKPIs);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const stats = await fetchStats();
      if (cancelled) return;
      if (stats) {
        setKpis(buildKPIs(stats));
        setUsingFallback(false);
      } else {
        setKpis(fallbackKPIs);
        setUsingFallback(true);
      }
      setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      {usingFallback && !loading && (
        <div className="mb-3 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400">
          API unavailable — showing sample data
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label} className="bg-slate-900 border-slate-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                      {kpi.label}
                    </p>
                    {loading ? (
                      <div className="mt-2">
                        <Loader2 className="h-5 w-5 text-slate-600 animate-spin" />
                      </div>
                    ) : (
                      <p className="mt-1 text-2xl font-bold text-slate-50">
                        {kpi.value}
                      </p>
                    )}
                  </div>
                  <div className={`h-10 w-10 rounded-lg ${kpi.bgColor} flex items-center justify-center`}>
                    <Icon className={`h-5 w-5 ${kpi.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
