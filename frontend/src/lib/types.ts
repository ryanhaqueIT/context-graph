// ─── Graph Types ─────────────────────────────────────────────

export interface GraphNode {
  data: {
    id: string;
    label: string;
    type: string;
    properties: Record<string, any>;
  };
}

export interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    type: string;
  };
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ─── Health & Stats ──────────────────────────────────────────

export interface HealthReport {
  total_nodes: number;
  total_edges: number;
  total_processes: number;
  coverage_percent: number;
  status: string;
}

export interface StatsResponse {
  total_nodes: number;
  total_edges: number;
  decision_traces: number;
  coverage_percent: number;
}

// ─── Node Detail ─────────────────────────────────────────────

export interface NodeDetailResponse {
  id: string;
  label: string;
  type: string;
  file_path?: string;
  line_number?: number;
  cluster?: string;
  callers: string[];
  callees: string[];
  processes: string[];
  risk_level: string;
  properties: Record<string, any>;
}

export interface NeighborsResponse {
  center: string;
  depth: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ─── Incidents & Decisions ───────────────────────────────────

export interface Incident {
  id: string;
  file: string;
  type: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  timestamp: string;
  resolved: boolean;
}

export interface DecisionTrace {
  id: string;
  decision_type: string;
  summary: string;
  module: string;
  timestamp: string;
  rationale: string;
  alternatives_considered: string[];
  impact: string;
}

// ─── Patterns ────────────────────────────────────────────────

export interface Pattern {
  id: string;
  name: string;
  category: string;
  description: string;
  files: string[];
  occurrences: number;
  severity: string;
}

// ─── Changes & Ownership ────────────────────────────────────

export interface Change {
  id: string;
  file: string;
  type: string;
  description: string;
  author: string;
  timestamp: string;
  lines_changed: number;
}

export interface Owner {
  name: string;
  email: string;
  ownership_percent: number;
  last_modified: string;
  commits: number;
}

// ─── Blast Radius & What-If ─────────────────────────────────

export interface BlastRadius {
  file: string;
  dependents: string[];
  total_affected: number;
  risk_level: string;
  affected_processes: string[];
  affected_tests: string[];
}

export interface WhatIfResult {
  file: string;
  blast_radius: BlastRadius;
  risk_level: string;
  confidence: number;
  recommendations: string[];
  estimated_impact: string;
}

// ─── Timeline ────────────────────────────────────────────────

export interface TimelineEvent {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  file?: string;
  author?: string;
}

// ─── Similar Incidents ───────────────────────────────────────

export interface SimilarIncident {
  id: string;
  description: string;
  similarity: number;
  file: string;
  timestamp: string;
  resolution?: string;
}

// ─── Chat ────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  agent?: string;
  status?: "thinking" | "reading" | "complete";
  files?: string[];
}

export interface ChatRequest {
  message: string;
  context?: {
    files?: string[];
    mode?: "agent" | "hive";
  };
}

export interface ChatResponse {
  message: ChatMessage;
  context?: {
    files: string[];
    patterns: string[];
    problems: string[];
  };
}

// ─── Agent (Hive Mode) ──────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  objective: string;
  result?: string;
}

// ─── Trace ───────────────────────────────────────────────────

export interface TraceCreate {
  decision_type: string;
  summary: string;
  module: string;
  rationale: string;
  alternatives_considered: string[];
  impact: string;
}
