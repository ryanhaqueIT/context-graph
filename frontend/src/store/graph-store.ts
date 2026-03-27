import { create } from "zustand";

export interface GraphNode {
  id: string;
  label: string;
  type: "function" | "class" | "file" | "test";
  filePath?: string;
  lineNumber?: number;
  cluster?: string;
  callers?: string[];
  callees?: string[];
  processes?: string[];
  riskLevel?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: "calls" | "imports" | "depends_on";
}

interface GraphFilters {
  nodeTypes: Record<string, boolean>;
  edgeTypes: Record<string, boolean>;
  clusters: Record<string, boolean>;
  depth: number;
}

interface GraphState {
  selectedNode: GraphNode | null;
  filters: GraphFilters;
  layoutMode: "force" | "hierarchical" | "concentric" | "grid";
  searchQuery: string;
  setSelectedNode: (node: GraphNode | null) => void;
  setFilters: (filters: Partial<GraphFilters>) => void;
  setLayoutMode: (mode: GraphState["layoutMode"]) => void;
  setSearchQuery: (query: string) => void;
  toggleNodeType: (type: string) => void;
  toggleEdgeType: (type: string) => void;
  toggleCluster: (cluster: string) => void;
  setDepth: (depth: number) => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  selectedNode: null,
  filters: {
    nodeTypes: { function: true, class: true, file: true, test: false },
    edgeTypes: { calls: true, imports: true, depends_on: false },
    clusters: {},
    depth: 2,
  },
  layoutMode: "force",
  searchQuery: "",
  setSelectedNode: (node) => set({ selectedNode: node }),
  setFilters: (filters) =>
    set((state) => ({ filters: { ...state.filters, ...filters } })),
  setLayoutMode: (mode) => set({ layoutMode: mode }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  toggleNodeType: (type) =>
    set((state) => ({
      filters: {
        ...state.filters,
        nodeTypes: {
          ...state.filters.nodeTypes,
          [type]: !state.filters.nodeTypes[type],
        },
      },
    })),
  toggleEdgeType: (type) =>
    set((state) => ({
      filters: {
        ...state.filters,
        edgeTypes: {
          ...state.filters.edgeTypes,
          [type]: !state.filters.edgeTypes[type],
        },
      },
    })),
  toggleCluster: (cluster) =>
    set((state) => ({
      filters: {
        ...state.filters,
        clusters: {
          ...state.filters.clusters,
          [cluster]: !state.filters.clusters[cluster],
        },
      },
    })),
  setDepth: (depth) =>
    set((state) => ({
      filters: { ...state.filters, depth },
    })),
}));
