"""API route handlers for the context graph engine.

All routes are mounted under /api and return JSON responses.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from context_graph.api.deps import get_store
from context_graph.api.schemas import (
    CytoscapeEdge,
    CytoscapeEdgeData,
    CytoscapeNode,
    CytoscapeNodeData,
    DecisionTraceRequest,
    DecisionTraceResponse,
    GraphResponse,
    HealthResponse,
    NodeDetailResponse,
    StatsResponse,
    TrajectoryEndRequest,
    TrajectoryEndResponse,
    TrajectoryStartRequest,
    TrajectoryStartResponse,
    TrajectoryStepRequest,
    TrajectoryStepResponse,
)
from context_graph.models.nodes import (
    DecisionTrace,
    DecisionType,
    Edge,
    EdgeType,
    Node,
    NodeType,
)
from context_graph.query.interface import QueryInterface

router = APIRouter(prefix="/api")

DECISION_TYPE_MAP: dict[str, DecisionType] = {
    "fix": DecisionType.BUG_FIX,
    "review": DecisionType.REVIEW,
    "architecture": DecisionType.ARCHITECTURE,
    "validation": DecisionType.VALIDATION_FIX,
    "refactor": DecisionType.REFACTOR,
    "feature": DecisionType.FEATURE,
    "incident": DecisionType.INCIDENT_RESPONSE,
}


# ── Helpers ──────────────────────────────────────────────────


def _node_to_cytoscape(node: Node) -> CytoscapeNode:
    """Convert an internal Node to Cytoscape.js format."""
    return CytoscapeNode(
        data=CytoscapeNodeData(
            id=node.id,
            label=node.name,
            type=node.node_type.value,
            properties=node.properties,
        )
    )


def _edge_to_cytoscape(edge: Edge) -> CytoscapeEdge:
    """Convert an internal Edge to Cytoscape.js format."""
    return CytoscapeEdge(
        data=CytoscapeEdgeData(
            id=edge.id,
            source=edge.source_id,
            target=edge.target_id,
            type=edge.edge_type.value,
        )
    )


def _trace_to_response(trace: DecisionTrace) -> DecisionTraceResponse:
    """Convert a DecisionTrace dataclass to its API response model."""
    return DecisionTraceResponse(
        id=trace.id,
        decision_type=trace.decision_type.value,
        summary=trace.summary,
        rationale=trace.rationale,
        evidence=trace.evidence,
        files_affected=trace.files_affected,
        categories=trace.categories,
        actor=trace.actor,
        outcome=trace.outcome,
        created_at=trace.created_at,
    )


# ── Health & Stats ───────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Return graph health report (node counts, edge counts, coverage ratio)."""
    store = get_store()
    qi = QueryInterface(store)
    report = qi.health_report()
    return HealthResponse(**report)


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Return summary statistics for the graph."""
    store = get_store()
    qi = QueryInterface(store)
    report = qi.health_report()
    return StatsResponse(
        node_count=report["total_nodes"],
        edge_count=report["total_edges"],
        decision_traces=report["decision_traces"],
        code_changes=report["code_changes"],
        coverage_ratio=report["coverage_ratio"],
    )


# ── Graph Data (Cytoscape.js) ───────────────────────────────


@router.get("/graph", response_model=GraphResponse)
def get_graph(
    type: str | None = Query(None, description="Filter by node type (e.g. code_unit)"),
    limit: int = Query(100, ge=1, le=10000, description="Maximum nodes to return"),
    search: str | None = Query(None, description="Search nodes by name keyword"),
):
    """Return nodes and edges in Cytoscape.js format."""
    store = get_store()

    # Collect nodes
    if type:
        try:
            node_type = NodeType(type)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid node type: {type}")
        nodes = store.get_nodes_by_type(node_type)
    elif search:
        nodes = store.get_nodes_by_name(search)
    else:
        # Get all node types
        nodes = []
        for nt in NodeType:
            nodes.extend(store.get_nodes_by_type(nt))

    # Apply limit
    nodes = nodes[:limit]

    # Collect node ids for edge filtering
    node_ids = {n.id for n in nodes}

    # Build Cytoscape nodes
    cyto_nodes = [_node_to_cytoscape(n) for n in nodes]

    # Collect edges between the returned nodes
    cyto_edges: list[CytoscapeEdge] = []
    seen_edges: set[str] = set()
    for node in nodes:
        for edge in store.get_edges_from(node.id):
            if edge.id not in seen_edges and edge.target_id in node_ids:
                cyto_edges.append(_edge_to_cytoscape(edge))
                seen_edges.add(edge.id)
        for edge in store.get_edges_to(node.id):
            if edge.id not in seen_edges and edge.source_id in node_ids:
                cyto_edges.append(_edge_to_cytoscape(edge))
                seen_edges.add(edge.id)

    return GraphResponse(nodes=cyto_nodes, edges=cyto_edges)


@router.get("/graph/node/{node_id}", response_model=NodeDetailResponse)
def get_node(node_id: str):
    """Return a single node with its incoming and outgoing edges."""
    store = get_store()
    node = store.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    edges_from = [_edge_to_cytoscape(e) for e in store.get_edges_from(node_id)]
    edges_to = [_edge_to_cytoscape(e) for e in store.get_edges_to(node_id)]

    return NodeDetailResponse(
        node=_node_to_cytoscape(node),
        edges_from=edges_from,
        edges_to=edges_to,
    )


@router.get("/graph/neighbors/{node_id}", response_model=GraphResponse)
def get_neighbors(
    node_id: str,
    depth: int = Query(2, ge=1, le=5, description="BFS traversal depth"),
):
    """Return BFS neighbors of a node up to the given depth."""
    store = get_store()
    root = store.get_node(node_id)
    if not root:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    neighbors = store.traverse(node_id, max_depth=depth)
    all_nodes = [root, *neighbors]
    node_ids = {n.id for n in all_nodes}

    cyto_nodes = [_node_to_cytoscape(n) for n in all_nodes]

    cyto_edges: list[CytoscapeEdge] = []
    seen_edges: set[str] = set()
    for node in all_nodes:
        for edge in store.get_edges_from(node.id):
            if edge.id not in seen_edges and edge.target_id in node_ids:
                cyto_edges.append(_edge_to_cytoscape(edge))
                seen_edges.add(edge.id)
        for edge in store.get_edges_to(node.id):
            if edge.id not in seen_edges and edge.source_id in node_ids:
                cyto_edges.append(_edge_to_cytoscape(edge))
                seen_edges.add(edge.id)

    return GraphResponse(nodes=cyto_nodes, edges=cyto_edges)


# ── Query Endpoints ──────────────────────────────────────────


@router.get("/query/incidents")
def query_incidents(file: str = Query(..., description="File path to query")):
    """Return incidents (decision traces) for a file."""
    store = get_store()
    qi = QueryInterface(store)
    traces = qi.incidents_for_file(file)
    return [_trace_to_response(t) for t in traces]


@router.get("/query/decisions")
def query_decisions(module: str = Query(..., description="Module path to query")):
    """Return decisions for a module."""
    store = get_store()
    qi = QueryInterface(store)
    traces = qi.decisions_for_module(module)
    return [_trace_to_response(t) for t in traces]


@router.get("/query/patterns")
def query_patterns(category: str | None = Query(None, description="Category filter")):
    """Return fix patterns, optionally filtered by category."""
    store = get_store()
    qi = QueryInterface(store)
    return qi.fix_patterns(category=category)


@router.get("/query/changes")
def query_changes(
    file: str | None = Query(None, description="File path filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
):
    """Return recent code changes, optionally filtered by file."""
    store = get_store()
    qi = QueryInterface(store)
    changes = qi.recent_changes(file_path=file, limit=limit)
    return [n.to_dict() for n in changes]


@router.get("/query/owners")
def query_owners(file: str = Query(..., description="File path to query")):
    """Return knowledge owners for a file."""
    store = get_store()
    qi = QueryInterface(store)
    return qi.knowledge_owners(file)


@router.get("/query/blast-radius")
def query_blast_radius(file: str = Query(..., description="File path to query")):
    """Return blast radius analysis for a file."""
    store = get_store()
    qi = QueryInterface(store)
    return qi.blast_radius(file)


@router.get("/query/what-if")
def query_what_if(file: str = Query(..., description="File path to simulate")):
    """Return what-if analysis for a file change."""
    store = get_store()
    qi = QueryInterface(store)
    return qi.what_if_change(file)


@router.get("/query/timeline")
def query_timeline(
    start: str = Query(..., description="Start date (ISO format)"),
    end: str = Query(..., description="End date (ISO format)"),
):
    """Return graph events within a time range."""
    store = get_store()
    qi = QueryInterface(store)
    try:
        nodes = qi.timeline(start, end)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {e}")
    return [n.to_dict() for n in nodes]


@router.get("/query/similar")
def query_similar(q: str = Query(..., description="Description to search for")):
    """Return incidents similar to the given description."""
    store = get_store()
    qi = QueryInterface(store)
    traces = qi.similar_incidents(q)
    return [_trace_to_response(t) for t in traces]


# ── Decision Traces ──────────────────────────────────────────


@router.post("/traces", response_model=DecisionTraceResponse, status_code=201)
def create_trace(body: DecisionTraceRequest):
    """Record a new decision trace."""
    store = get_store()
    dt = DECISION_TYPE_MAP.get(body.type)
    if dt is None:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid decision type: {body.type}. "
            f"Valid types: {', '.join(DECISION_TYPE_MAP.keys())}",
        )
    trace = DecisionTrace(
        decision_type=dt,
        summary=body.summary,
        rationale=body.rationale,
        evidence=body.evidence,
        files_affected=body.files,
        categories=body.categories,
        actor=body.actor,
        outcome=body.outcome,
    )
    store.add_node(trace.to_node())
    return _trace_to_response(trace)


@router.get("/traces")
def list_traces(file: str | None = Query(None, description="Filter by file path")):
    """List all decision traces, optionally filtered by file."""
    store = get_store()
    qi = QueryInterface(store)
    if file:
        traces = qi.incidents_for_file(file)
    else:
        nodes = store.get_nodes_by_type(NodeType.DECISION_TRACE)
        traces = [DecisionTrace.from_node(n) for n in nodes]
    return [_trace_to_response(t) for t in traces]


# ── Trajectory ───────────────────────────────────────────────


@router.post("/trajectory/start", response_model=TrajectoryStartResponse, status_code=201)
def trajectory_start(body: TrajectoryStartRequest):
    """Start a new agent trajectory."""
    store = get_store()
    tid = store.start_trajectory(agent_id=body.agent_id, description=body.description)
    return TrajectoryStartResponse(trajectory_id=tid)


@router.post("/trajectory/step", response_model=TrajectoryStepResponse)
def trajectory_step(body: TrajectoryStepRequest):
    """Record a step in an agent trajectory."""
    store = get_store()
    traj = store.get_trajectory(body.trajectory_id)
    if not traj:
        raise HTTPException(status_code=404, detail=f"Trajectory not found: {body.trajectory_id}")
    store.record_step(
        trajectory_id=body.trajectory_id,
        node_id=body.node_id,
        action=body.action,
    )
    return TrajectoryStepResponse(status="recorded")


@router.post("/trajectory/end", response_model=TrajectoryEndResponse)
def trajectory_end(body: TrajectoryEndRequest):
    """End an agent trajectory."""
    store = get_store()
    traj = store.get_trajectory(body.trajectory_id)
    if not traj:
        raise HTTPException(status_code=404, detail=f"Trajectory not found: {body.trajectory_id}")
    store.end_trajectory(body.trajectory_id)
    return TrajectoryEndResponse(status="ended")
