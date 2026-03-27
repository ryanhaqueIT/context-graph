"use client";

import { Search } from "lucide-react";
import { useGraphStore } from "@/store/graph-store";
import { clusters } from "@/lib/sample-data";

export function FilterPanel() {
  const {
    filters,
    searchQuery,
    toggleNodeType,
    toggleEdgeType,
    toggleCluster,
    setDepth,
    setSearchQuery,
  } = useGraphStore();

  return (
    <div className="w-56 border-r border-slate-800 bg-slate-950 p-4 space-y-6 overflow-y-auto">
      {/* Search */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Search
        </h3>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter nodes..."
            className="w-full h-8 pl-8 pr-3 rounded-md border border-slate-800 bg-slate-900 text-slate-50 text-xs placeholder:text-slate-600 outline-none focus:border-blue-500/50 transition-colors"
          />
        </div>
      </div>

      {/* Node Types */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Node Types
        </h3>
        <div className="space-y-2">
          {(["function", "class", "file", "test"] as const).map((type) => (
            <label
              key={type}
              className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer hover:text-slate-50"
            >
              <input
                type="checkbox"
                checked={filters.nodeTypes[type] ?? false}
                onChange={() => toggleNodeType(type)}
                className="rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="capitalize">{type}s</span>
              <span
                className={`ml-auto h-2 w-2 rounded-full ${
                  type === "function"
                    ? "bg-blue-500"
                    : type === "class"
                    ? "bg-purple-500"
                    : type === "file"
                    ? "bg-emerald-500"
                    : "bg-amber-500"
                }`}
              />
            </label>
          ))}
        </div>
      </div>

      {/* Edge Types */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Edge Types
        </h3>
        <div className="space-y-2">
          {(["calls", "imports", "depends_on"] as const).map((type) => (
            <label
              key={type}
              className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer hover:text-slate-50"
            >
              <input
                type="checkbox"
                checked={filters.edgeTypes[type] ?? false}
                onChange={() => toggleEdgeType(type)}
                className="rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span className="capitalize">{type.replace("_", " ")}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Depth Slider */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Depth
        </h3>
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              onClick={() => setDepth(d)}
              className={`flex-1 h-8 rounded-md text-sm font-medium transition-colors ${
                filters.depth === d
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : "bg-slate-800 text-slate-400 border border-slate-700 hover:border-slate-600"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Clusters */}
      <div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Clusters
        </h3>
        <div className="space-y-2">
          {clusters.map((cluster) => (
            <label
              key={cluster.id}
              className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer hover:text-slate-50"
            >
              <input
                type="checkbox"
                checked={filters.clusters[cluster.id] ?? true}
                onChange={() => toggleCluster(cluster.id)}
                className="rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-blue-500 focus:ring-offset-0"
              />
              <span>{cluster.name}</span>
              <span className="ml-auto text-xs text-slate-600">
                {cluster.nodeCount}
              </span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
