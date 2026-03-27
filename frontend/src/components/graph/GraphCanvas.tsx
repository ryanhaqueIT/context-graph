"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import cytoscape from "cytoscape";
import type { Core, EventObject } from "cytoscape";
import { useGraphStore, type GraphNode, type GraphEdge } from "@/store/graph-store";
import { sampleNodes, sampleEdges } from "@/lib/sample-data";
import { fetchGraph, fetchNodeDetail } from "@/lib/api";
import { ZoomIn, ZoomOut, Maximize2, Loader2 } from "lucide-react";

const NODE_COLORS: Record<string, string> = {
  function: "#3b82f6",
  class: "#a855f7",
  file: "#22c55e",
  test: "#f59e0b",
};

const EDGE_COLORS: Record<string, string> = {
  calls: "#64748b",
  imports: "#6366f1",
  depends_on: "#f59e0b",
};

export function GraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const { filters, setSelectedNode, layoutMode, searchQuery } = useGraphStore();
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>(sampleNodes);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>(sampleEdges);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  // Fetch graph data from API on mount and when search/filters change
  useEffect(() => {
    let cancelled = false;
    async function loadGraph() {
      setLoading(true);
      // Build type filter for API
      const activeTypes = Object.entries(filters.nodeTypes)
        .filter(([, enabled]) => enabled)
        .map(([type]) => type);
      const typeParam = activeTypes.length < 4 ? activeTypes[0] : undefined;

      const result = await fetchGraph({
        type: typeParam,
        search: searchQuery || undefined,
        limit: 100,
      });

      if (cancelled) return;

      if (result && result.nodes.length > 0) {
        // Map API GraphNode to local GraphNode format
        const nodes: GraphNode[] = result.nodes.map((n) => ({
          id: n.data.id,
          label: n.data.label,
          type: n.data.type as GraphNode["type"],
          filePath: n.data.properties?.file_path,
          lineNumber: n.data.properties?.line_number,
          cluster: n.data.properties?.cluster,
          callers: n.data.properties?.callers || [],
          callees: n.data.properties?.callees || [],
          processes: n.data.properties?.processes || [],
          riskLevel: n.data.properties?.risk_level,
        }));
        const edges: GraphEdge[] = result.edges.map((e) => ({
          id: e.data.id,
          source: e.data.source,
          target: e.data.target,
          type: e.data.type as GraphEdge["type"],
        }));
        setGraphNodes(nodes);
        setGraphEdges(edges);
        setUsingFallback(false);
      } else {
        setGraphNodes(sampleNodes);
        setGraphEdges(sampleEdges);
        setUsingFallback(true);
      }
      setLoading(false);
    }
    loadGraph();
    return () => { cancelled = true; };
  }, [searchQuery, filters.nodeTypes]);

  const initGraph = useCallback(() => {
    if (!containerRef.current) return;

    // Filter nodes based on current filters
    const visibleNodes = graphNodes.filter(
      (n) => filters.nodeTypes[n.type] !== false
    );
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));

    const visibleEdges = graphEdges.filter(
      (e) =>
        filters.edgeTypes[e.type] !== false &&
        visibleNodeIds.has(e.source) &&
        visibleNodeIds.has(e.target)
    );

    // Build cytoscape elements
    const elements = [
      ...visibleNodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          cluster: n.cluster,
        },
      })),
      ...visibleEdges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
        },
      })),
    ];

    // Destroy existing instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const layoutConfig: Record<string, cytoscape.LayoutOptions> = {
      force: { name: "cose", animate: false, nodeOverlap: 40, idealEdgeLength: 80, gravity: 0.3 } as cytoscape.LayoutOptions,
      hierarchical: { name: "breadthfirst", animate: false, directed: true, spacingFactor: 1.2 } as cytoscape.LayoutOptions,
      concentric: { name: "concentric", animate: false, minNodeSpacing: 50 } as cytoscape.LayoutOptions,
      grid: { name: "grid", animate: false, rows: 4 } as cytoscape.LayoutOptions,
    };

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "bottom",
            "text-halign": "center",
            "font-size": "10px",
            color: "#94a3b8",
            "text-margin-y": 6,
            width: 28,
            height: 28,
            "background-color": (ele: any) =>
              NODE_COLORS[ele.data("type")] || "#64748b",
            "border-width": 2,
            "border-color": (ele: any) => {
              const c = NODE_COLORS[ele.data("type")] || "#64748b";
              return c;
            },
            "border-opacity": 0.3,
            "background-opacity": 0.85,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": (ele: any) =>
              EDGE_COLORS[ele.data("type")] || "#475569",
            "target-arrow-color": (ele: any) =>
              EDGE_COLORS[ele.data("type")] || "#475569",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.8,
            "curve-style": "bezier",
            opacity: 0.6,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#60a5fa",
            "border-opacity": 1,
            "background-opacity": 1,
            "overlay-color": "#60a5fa",
            "overlay-opacity": 0.1,
          },
        },
        {
          selector: "node.highlighted",
          style: {
            "border-width": 3,
            "border-color": "#60a5fa",
          },
        },
        {
          selector: "node.dimmed",
          style: {
            opacity: 0.2,
          },
        },
        {
          selector: "edge.dimmed",
          style: {
            opacity: 0.1,
          },
        },
      ],
      layout: layoutConfig[layoutMode] || layoutConfig.force,
      wheelSensitivity: 0.3,
      minZoom: 0.2,
      maxZoom: 3,
    });

    // Click handler — try API for detail, fall back to local data
    cyRef.current.on("tap", "node", async (evt: EventObject) => {
      const nodeId = evt.target.id();

      // Try API first for richer detail
      const apiDetail = await fetchNodeDetail(nodeId);
      if (apiDetail) {
        setSelectedNode({
          id: apiDetail.id,
          label: apiDetail.label,
          type: apiDetail.type as GraphNode["type"],
          filePath: apiDetail.file_path,
          lineNumber: apiDetail.line_number,
          cluster: apiDetail.cluster,
          callers: apiDetail.callers,
          callees: apiDetail.callees,
          processes: apiDetail.processes,
          riskLevel: apiDetail.risk_level as GraphNode["riskLevel"],
        });
      } else {
        // Fall back to local data
        const nodeData = graphNodes.find((n) => n.id === nodeId);
        if (nodeData) {
          setSelectedNode(nodeData);
        }
      }

      // Highlight connected nodes
      const cy = cyRef.current;
      if (cy) {
        cy.elements().removeClass("highlighted dimmed");
        const selected = cy.getElementById(nodeId);
        const neighborhood = selected.neighborhood().add(selected);
        cy.elements().not(neighborhood).addClass("dimmed");
        neighborhood.addClass("highlighted");
      }
    });

    // Click on background to deselect
    cyRef.current.on("tap", (evt: EventObject) => {
      if (evt.target === cyRef.current) {
        setSelectedNode(null);
        cyRef.current?.elements().removeClass("highlighted dimmed");
      }
    });
  }, [filters, layoutMode, setSelectedNode, graphNodes, graphEdges]);

  useEffect(() => {
    if (!loading) {
      initGraph();
    }
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [initGraph, loading]);

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.3);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() / 1.3);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 40);
    }
  };

  return (
    <div className="relative flex-1 bg-slate-950">
      {loading ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
            <p className="text-sm text-slate-500">Loading graph data...</p>
          </div>
        </div>
      ) : (
        <div ref={containerRef} className="w-full h-full" />
      )}

      {/* Fallback Banner */}
      {usingFallback && !loading && (
        <div className="absolute top-4 right-4 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400 backdrop-blur-sm">
          API unavailable — showing sample data
        </div>
      )}

      {/* Zoom Controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1">
        <button
          onClick={handleZoomIn}
          className="h-8 w-8 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-50 hover:bg-slate-700 transition-colors"
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="h-8 w-8 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-50 hover:bg-slate-700 transition-colors"
        >
          <ZoomOut className="h-4 w-4" />
        </button>
        <button
          onClick={handleFit}
          className="h-8 w-8 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-50 hover:bg-slate-700 transition-colors"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>

      {/* Layout Legend */}
      <div className="absolute top-4 left-4 flex items-center gap-4 px-3 py-2 rounded-md bg-slate-900/80 border border-slate-800 backdrop-blur-sm">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-[10px] text-slate-400 capitalize">
              {type}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
