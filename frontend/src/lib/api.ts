import type {
  StatsResponse,
  HealthReport,
  GraphData,
  NodeDetailResponse,
  NeighborsResponse,
  Incident,
  DecisionTrace,
  Pattern,
  Change,
  Owner,
  BlastRadius,
  WhatIfResult,
  TimelineEvent,
  SimilarIncident,
  TraceCreate,
  ChatRequest,
  ChatResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Helpers ─────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      console.warn(`API ${path} returned ${res.status}`);
      return null;
    }
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`API ${path} unreachable:`, err);
    return null;
  }
}

async function apiFetchArray<T>(
  path: string,
  options?: RequestInit
): Promise<T[]> {
  const result = await apiFetch<T[]>(path, options);
  return result ?? [];
}

// ─── Health & Stats ──────────────────────────────────────────

export async function fetchHealth(): Promise<HealthReport | null> {
  return apiFetch<HealthReport>("/api/health");
}

export async function fetchStats(): Promise<StatsResponse | null> {
  return apiFetch<StatsResponse>("/api/stats");
}

// ─── Graph ───────────────────────────────────────────────────

export async function fetchGraph(params?: {
  type?: string;
  limit?: number;
  search?: string;
}): Promise<GraphData | null> {
  const query = new URLSearchParams();
  if (params?.type) query.set("type", params.type);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.search) query.set("search", params.search);
  const qs = query.toString();
  return apiFetch<GraphData>(`/api/graph${qs ? `?${qs}` : ""}`);
}

export async function fetchNodeDetail(
  nodeId: string
): Promise<NodeDetailResponse | null> {
  return apiFetch<NodeDetailResponse>(`/api/graph/nodes/${encodeURIComponent(nodeId)}`);
}

export async function fetchNeighbors(
  nodeId: string,
  depth?: number
): Promise<NeighborsResponse | null> {
  const qs = depth ? `?depth=${depth}` : "";
  return apiFetch<NeighborsResponse>(
    `/api/graph/nodes/${encodeURIComponent(nodeId)}/neighbors${qs}`
  );
}

// ─── Incidents ───────────────────────────────────────────────

export async function fetchIncidents(file: string): Promise<Incident[]> {
  return apiFetchArray<Incident>(
    `/api/incidents?file=${encodeURIComponent(file)}`
  );
}

// ─── Decisions ───────────────────────────────────────────────

export async function fetchDecisions(module: string): Promise<DecisionTrace[]> {
  return apiFetchArray<DecisionTrace>(
    `/api/decisions?module=${encodeURIComponent(module)}`
  );
}

// ─── Patterns ────────────────────────────────────────────────

export async function fetchPatterns(category?: string): Promise<Pattern[]> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiFetchArray<Pattern>(`/api/patterns${qs}`);
}

// ─── Changes ─────────────────────────────────────────────────

export async function fetchChanges(
  file?: string,
  limit?: number
): Promise<Change[]> {
  const query = new URLSearchParams();
  if (file) query.set("file", file);
  if (limit) query.set("limit", String(limit));
  const qs = query.toString();
  return apiFetchArray<Change>(`/api/changes${qs ? `?${qs}` : ""}`);
}

// ─── Ownership ───────────────────────────────────────────────

export async function fetchOwners(file: string): Promise<Owner[]> {
  return apiFetchArray<Owner>(
    `/api/owners?file=${encodeURIComponent(file)}`
  );
}

// ─── Blast Radius & What-If ─────────────────────────────────

export async function fetchBlastRadius(
  file: string
): Promise<BlastRadius | null> {
  return apiFetch<BlastRadius>(
    `/api/blast-radius?file=${encodeURIComponent(file)}`
  );
}

export async function fetchWhatIf(file: string): Promise<WhatIfResult | null> {
  return apiFetch<WhatIfResult>(
    `/api/what-if?file=${encodeURIComponent(file)}`
  );
}

// ─── Timeline ────────────────────────────────────────────────

export async function fetchTimeline(
  start: string,
  end: string
): Promise<TimelineEvent[]> {
  return apiFetchArray<TimelineEvent>(
    `/api/timeline?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
  );
}

// ─── Similar Incidents ───────────────────────────────────────

export async function fetchSimilarIncidents(
  query: string
): Promise<SimilarIncident[]> {
  return apiFetchArray<SimilarIncident>(
    `/api/similar-incidents?query=${encodeURIComponent(query)}`
  );
}

// ─── Traces ──────────────────────────────────────────────────

export async function createTrace(
  trace: TraceCreate
): Promise<DecisionTrace | null> {
  return apiFetch<DecisionTrace>("/api/traces", {
    method: "POST",
    body: JSON.stringify(trace),
  });
}

// ─── Chat ────────────────────────────────────────────────────

export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse | null> {
  return apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
