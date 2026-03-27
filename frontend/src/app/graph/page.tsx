"use client";

import { FilterPanel } from "@/components/graph/FilterPanel";
import { GraphCanvas } from "@/components/graph/GraphCanvas";
import { NodeDetail } from "@/components/graph/NodeDetail";
import { useGraphStore } from "@/store/graph-store";

export default function GraphExplorerPage() {
  const { layoutMode, setLayoutMode } = useGraphStore();

  return (
    <div className="flex h-full flex-col">
      {/* Top bar */}
      <div className="h-12 border-b border-slate-800 flex items-center justify-between px-4">
        <h1 className="text-sm font-semibold text-slate-50">Context Graph Explorer</h1>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Layout:</span>
          <div className="flex rounded-md border border-slate-800 p-0.5">
            {(["force", "hierarchical", "concentric", "grid"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setLayoutMode(mode)}
                className={`px-2.5 py-1 text-xs rounded-sm transition-colors capitalize ${
                  layoutMode === mode
                    ? "bg-slate-800 text-slate-50"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Three-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        <FilterPanel />
        <GraphCanvas />
        <NodeDetail />
      </div>
    </div>
  );
}
