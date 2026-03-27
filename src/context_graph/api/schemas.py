"""Pydantic models for API request/response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────


class HealthResponse(BaseModel):
    total_nodes: int
    total_edges: int
    code_units: int
    decision_traces: int
    code_changes: int
    files_with_traces: int
    files_without_traces: int
    coverage_ratio: float
    uncovered_files: list[str]


class StatsResponse(BaseModel):
    node_count: int
    edge_count: int
    decision_traces: int
    code_changes: int
    coverage_ratio: float


# ── Graph / Cytoscape models ────────────────────────────────


class CytoscapeNodeData(BaseModel):
    id: str
    label: str
    type: str
    properties: dict = Field(default_factory=dict)


class CytoscapeNode(BaseModel):
    data: CytoscapeNodeData


class CytoscapeEdgeData(BaseModel):
    id: str
    source: str
    target: str
    type: str


class CytoscapeEdge(BaseModel):
    data: CytoscapeEdgeData


class GraphResponse(BaseModel):
    nodes: list[CytoscapeNode]
    edges: list[CytoscapeEdge]


class NodeDetailResponse(BaseModel):
    node: CytoscapeNode
    edges_from: list[CytoscapeEdge]
    edges_to: list[CytoscapeEdge]


# ── Decision trace models ───────────────────────────────────


class DecisionTraceRequest(BaseModel):
    type: str = Field(..., description="Decision type: fix, review, architecture, etc.")
    summary: str
    rationale: str = ""
    files: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    actor: str = "agent"
    outcome: str = "resolved"


class DecisionTraceResponse(BaseModel):
    id: str
    decision_type: str
    summary: str
    rationale: str
    evidence: list[str]
    files_affected: list[str]
    categories: list[str]
    actor: str
    outcome: str
    created_at: str


# ── Trajectory models ───────────────────────────────────────


class TrajectoryStartRequest(BaseModel):
    agent_id: str = "agent"
    description: str = ""


class TrajectoryStartResponse(BaseModel):
    trajectory_id: str


class TrajectoryStepRequest(BaseModel):
    trajectory_id: str
    node_id: str
    action: str = "step"


class TrajectoryStepResponse(BaseModel):
    status: str = "recorded"


class TrajectoryEndRequest(BaseModel):
    trajectory_id: str


class TrajectoryEndResponse(BaseModel):
    status: str = "ended"
