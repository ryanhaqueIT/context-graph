"use client";

import { X, ExternalLink, AlertTriangle } from "lucide-react";
import { useGraphStore } from "@/store/graph-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

function RiskBadge({ level }: { level: string }) {
  const config: Record<string, { variant: "success" | "warning" | "error" | "info"; label: string }> = {
    LOW: { variant: "success", label: "LOW" },
    MEDIUM: { variant: "info", label: "MEDIUM" },
    HIGH: { variant: "warning", label: "HIGH" },
    CRITICAL: { variant: "error", label: "CRITICAL" },
  };
  const { variant, label } = config[level] || config.MEDIUM;
  return <Badge variant={variant}>{label}</Badge>;
}

export function NodeDetail() {
  const { selectedNode, setSelectedNode } = useGraphStore();

  if (!selectedNode) {
    return (
      <div className="w-72 border-l border-slate-800 bg-slate-950 flex items-center justify-center">
        <p className="text-sm text-slate-500">Click a node to view details</p>
      </div>
    );
  }

  const typeColor =
    selectedNode.type === "function"
      ? "text-blue-400"
      : selectedNode.type === "class"
      ? "text-purple-400"
      : selectedNode.type === "file"
      ? "text-emerald-400"
      : "text-amber-400";

  return (
    <div className="w-72 border-l border-slate-800 bg-slate-950 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-slate-50 truncate font-mono">
              {selectedNode.label}
            </h3>
            <p className={`text-xs mt-1 capitalize ${typeColor}`}>
              {selectedNode.type}
            </p>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {selectedNode.filePath && (
          <p className="text-xs text-slate-500 mt-2 font-mono truncate">
            {selectedNode.filePath}
            {selectedNode.lineNumber ? `:${selectedNode.lineNumber}` : ""}
          </p>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Risk Level */}
          {selectedNode.riskLevel && (
            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Impact Risk
              </h4>
              <RiskBadge level={selectedNode.riskLevel} />
            </div>
          )}

          <Separator className="bg-slate-800" />

          {/* Callers */}
          {selectedNode.callers && selectedNode.callers.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Callers ({selectedNode.callers.length})
              </h4>
              <div className="space-y-1">
                {selectedNode.callers.map((caller) => (
                  <div
                    key={caller}
                    className="text-xs text-slate-300 font-mono px-2 py-1.5 rounded bg-slate-800/50 hover:bg-slate-800 cursor-pointer"
                  >
                    {caller}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Callees */}
          {selectedNode.callees && selectedNode.callees.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Callees ({selectedNode.callees.length})
              </h4>
              <div className="space-y-1">
                {selectedNode.callees.map((callee) => (
                  <div
                    key={callee}
                    className="text-xs text-slate-300 font-mono px-2 py-1.5 rounded bg-slate-800/50 hover:bg-slate-800 cursor-pointer"
                  >
                    {callee}
                  </div>
                ))}
              </div>
            </div>
          )}

          <Separator className="bg-slate-800" />

          {/* Processes */}
          {selectedNode.processes && selectedNode.processes.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Processes
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {selectedNode.processes.map((process) => (
                  <Badge key={process} variant="outline" className="text-xs border-slate-700">
                    {process}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* View Source Button */}
          <Button variant="outline" size="sm" className="w-full mt-4 border-slate-700 text-slate-300">
            <ExternalLink className="h-3 w-3 mr-2" />
            View Source
          </Button>
        </div>
      </ScrollArea>
    </div>
  );
}
