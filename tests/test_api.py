"""Tests for the FastAPI API server.

Uses FastAPI's TestClient for synchronous HTTP testing.
Each test gets an isolated temporary store via fixture override.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from context_graph.api.deps import get_store, override_store, reset_store
from context_graph.api.server import create_app
from context_graph.engine.store import GraphStore
from context_graph.models.nodes import (
    DecisionTrace,
    DecisionType,
    Edge,
    EdgeType,
    Node,
    NodeType,
)


@pytest.fixture()
def api_store():
    """Provide an initialized GraphStore in a temp directory for API tests.

    Uses check_same_thread=False because TestClient runs handlers in a separate thread.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        store = GraphStore(Path(d) / "graph", check_same_thread=False)
        store.initialize()
        yield store
        store.close()


@pytest.fixture()
def client(api_store):
    """Provide a TestClient with the store dependency overridden."""
    override_store(api_store)
    app = create_app()
    with TestClient(app) as c:
        yield c
    reset_store()


# ---------------------------------------------------------------------------
# Health & Stats
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_valid_structure(self, client):
        """GET /api/health returns all expected keys with correct types."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_nodes" in data
        assert "total_edges" in data
        assert "code_units" in data
        assert "decision_traces" in data
        assert "code_changes" in data
        assert "coverage_ratio" in data
        assert "uncovered_files" in data
        assert isinstance(data["total_nodes"], int)
        assert isinstance(data["coverage_ratio"], float)
        assert isinstance(data["uncovered_files"], list)

    def test_health_empty_store(self, client):
        """An empty store returns zeroes."""
        resp = client.get("/api/health")
        data = resp.json()
        assert data["total_nodes"] == 0
        assert data["total_edges"] == 0
        assert data["coverage_ratio"] == 0.0


class TestStats:
    def test_stats_returns_counts(self, client):
        """GET /api/stats returns the expected summary keys."""
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "node_count" in data
        assert "edge_count" in data
        assert "decision_traces" in data
        assert "code_changes" in data
        assert "coverage_ratio" in data

    def test_stats_reflects_data(self, client, api_store):
        """Stats should reflect data added to the store."""
        api_store.add_node(Node(node_type=NodeType.CODE_UNIT, name="x.py",
                                properties={"file_path": "src/x.py"}))
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX,
            summary="Fix x",
            files_affected=["src/x.py"],
        ).to_node())

        resp = client.get("/api/stats")
        data = resp.json()
        assert data["node_count"] == 2
        assert data["decision_traces"] == 1


# ---------------------------------------------------------------------------
# Graph Data
# ---------------------------------------------------------------------------


class TestGraph:
    def test_graph_returns_nodes_and_edges(self, client, api_store):
        """GET /api/graph returns nodes and edges arrays."""
        api_store.add_node(Node(id="n1", node_type=NodeType.CODE_UNIT, name="a.py"))
        api_store.add_node(Node(id="n2", node_type=NodeType.CODE_UNIT, name="b.py"))
        api_store.add_edge(Edge(id="e1", edge_type=EdgeType.DEPENDS_ON,
                                source_id="n1", target_id="n2"))

        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        # Check Cytoscape format
        node_data = data["nodes"][0]["data"]
        assert "id" in node_data
        assert "label" in node_data
        assert "type" in node_data

    def test_graph_filter_by_type(self, client, api_store):
        """GET /api/graph?type=code_unit filters by node type."""
        api_store.add_node(Node(node_type=NodeType.CODE_UNIT, name="a.py"))
        api_store.add_node(Node(node_type=NodeType.CODE_CHANGE, name="commit 1"))

        resp = client.get("/api/graph?type=code_unit")
        data = resp.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["data"]["type"] == "code_unit"

    def test_graph_filter_by_search(self, client, api_store):
        """GET /api/graph?search=keyword filters nodes by name."""
        api_store.add_node(Node(node_type=NodeType.CODE_UNIT, name="auth_handler.py"))
        api_store.add_node(Node(node_type=NodeType.CODE_UNIT, name="cache.py"))

        resp = client.get("/api/graph?search=auth")
        data = resp.json()
        assert len(data["nodes"]) == 1
        assert "auth" in data["nodes"][0]["data"]["label"]

    def test_graph_invalid_type(self, client):
        """GET /api/graph?type=invalid returns 422."""
        resp = client.get("/api/graph?type=invalid_type")
        assert resp.status_code == 422

    def test_graph_empty(self, client):
        """GET /api/graph on empty store returns empty arrays."""
        resp = client.get("/api/graph")
        data = resp.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_graph_limit(self, client, api_store):
        """GET /api/graph?limit=N respects the limit."""
        for i in range(10):
            api_store.add_node(Node(node_type=NodeType.CODE_UNIT, name=f"file_{i}.py"))

        resp = client.get("/api/graph?limit=3")
        data = resp.json()
        assert len(data["nodes"]) == 3


class TestNodeDetail:
    def test_get_node_valid(self, client, api_store):
        """GET /api/graph/node/{id} returns the node with its edges."""
        api_store.add_node(Node(id="n1", node_type=NodeType.CODE_UNIT, name="a.py"))
        api_store.add_node(Node(id="n2", node_type=NodeType.CODE_UNIT, name="b.py"))
        api_store.add_edge(Edge(id="e1", edge_type=EdgeType.DEPENDS_ON,
                                source_id="n1", target_id="n2"))

        resp = client.get("/api/graph/node/n1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["node"]["data"]["id"] == "n1"
        assert len(data["edges_from"]) == 1
        assert data["edges_from"][0]["data"]["target"] == "n2"

    def test_get_node_not_found(self, client):
        """GET /api/graph/node/{id} returns 404 for missing nodes."""
        resp = client.get("/api/graph/node/nonexistent")
        assert resp.status_code == 404

    def test_get_node_with_incoming_edges(self, client, api_store):
        """GET /api/graph/node/{id} includes edges_to (incoming)."""
        api_store.add_node(Node(id="n1", node_type=NodeType.CODE_UNIT, name="a.py"))
        api_store.add_node(Node(id="n2", node_type=NodeType.CODE_UNIT, name="b.py"))
        api_store.add_edge(Edge(id="e1", edge_type=EdgeType.DEPENDS_ON,
                                source_id="n2", target_id="n1"))

        resp = client.get("/api/graph/node/n1")
        data = resp.json()
        assert len(data["edges_to"]) == 1
        assert data["edges_to"][0]["data"]["source"] == "n2"


class TestNeighbors:
    def test_neighbors_returns_graph(self, client, api_store):
        """GET /api/graph/neighbors/{id} returns BFS neighbors."""
        api_store.add_node(Node(id="a", node_type=NodeType.CODE_UNIT, name="a.py"))
        api_store.add_node(Node(id="b", node_type=NodeType.CODE_UNIT, name="b.py"))
        api_store.add_node(Node(id="c", node_type=NodeType.CODE_UNIT, name="c.py"))
        api_store.add_edge(Edge(edge_type=EdgeType.DEPENDS_ON, source_id="a", target_id="b"))
        api_store.add_edge(Edge(edge_type=EdgeType.DEPENDS_ON, source_id="b", target_id="c"))

        resp = client.get("/api/graph/neighbors/a?depth=2")
        assert resp.status_code == 200
        data = resp.json()
        ids = {n["data"]["id"] for n in data["nodes"]}
        assert "a" in ids
        assert "b" in ids
        assert "c" in ids

    def test_neighbors_not_found(self, client):
        """GET /api/graph/neighbors/{id} returns 404 for missing nodes."""
        resp = client.get("/api/graph/neighbors/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Query Endpoints
# ---------------------------------------------------------------------------


class TestQueryIncidents:
    def test_incidents_with_file(self, client, api_store):
        """GET /api/query/incidents?file=path returns matching traces."""
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX,
            summary="Fix store bug",
            files_affected=["src/store.py"],
            categories=["bug"],
        ).to_node())

        resp = client.get("/api/query/incidents?file=src/store.py")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["summary"] == "Fix store bug"

    def test_incidents_empty(self, client):
        """GET /api/query/incidents?file=path returns empty list when no match."""
        resp = client.get("/api/query/incidents?file=nonexistent.py")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_incidents_requires_file(self, client):
        """GET /api/query/incidents without file param returns 422."""
        resp = client.get("/api/query/incidents")
        assert resp.status_code == 422


class TestQueryDecisions:
    def test_decisions_for_module(self, client, api_store):
        """GET /api/query/decisions?module=path returns matching traces."""
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.ARCHITECTURE,
            summary="Split engine",
            files_affected=["src/engine/store.py"],
        ).to_node())

        resp = client.get("/api/query/decisions?module=engine")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["summary"] == "Split engine"


class TestQueryPatterns:
    def test_patterns_returns_list(self, client, api_store):
        """GET /api/query/patterns returns fix pattern list."""
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX,
            summary="Timeout fix",
            categories=["timeout"],
        ).to_node())

        resp = client.get("/api/query/patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["category"] == "timeout"

    def test_patterns_with_category(self, client, api_store):
        """GET /api/query/patterns?category=X filters correctly."""
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX, summary="t1", categories=["timeout"],
        ).to_node())
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX, summary="a1", categories=["auth"],
        ).to_node())

        resp = client.get("/api/query/patterns?category=timeout")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["category"] == "timeout"


class TestQueryChanges:
    def test_changes_returns_list(self, client, api_store):
        """GET /api/query/changes returns recent code changes."""
        api_store.add_node(Node(
            node_type=NodeType.CODE_CHANGE, name="commit 1",
            properties={"commit_hash": "abc123"},
        ))

        resp = client.get("/api/query/changes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


class TestQueryOwners:
    def test_owners_returns_list(self, client, api_store):
        """GET /api/query/owners?file=path returns knowledge owners."""
        resp = client.get("/api/query/owners?file=src/store.py")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestQueryBlastRadius:
    def test_blast_radius_returns_dict(self, client, api_store):
        """GET /api/query/blast-radius?file=path returns blast radius dict."""
        resp = client.get("/api/query/blast-radius?file=src/store.py")
        assert resp.status_code == 200
        data = resp.json()
        assert "file" in data
        assert "dependents" in data
        assert "risk_score" in data


class TestQueryWhatIf:
    def test_what_if_returns_dict(self, client, api_store):
        """GET /api/query/what-if?file=path returns what-if analysis."""
        resp = client.get("/api/query/what-if?file=src/store.py")
        assert resp.status_code == 200
        data = resp.json()
        assert "file" in data
        assert "risk_level" in data


class TestQueryTimeline:
    def test_timeline_returns_nodes(self, client, api_store):
        """GET /api/query/timeline returns events in time range."""
        api_store.add_node(Node(
            node_type=NodeType.CODE_CHANGE, name="commit 1",
            created_at="2025-01-15T00:00:00+00:00",
        ))

        resp = client.get("/api/query/timeline?start=2025-01-01T00:00:00%2B00:00&end=2025-01-31T23:59:59%2B00:00")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


class TestQuerySimilar:
    def test_similar_returns_matches(self, client, api_store):
        """GET /api/query/similar?q=description returns similar incidents."""
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX,
            summary="Timeout in auth service",
            rationale="Connection pool exhausted",
        ).to_node())

        resp = client.get("/api/query/similar?q=timeout")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert "Timeout" in data[0]["summary"]


# ---------------------------------------------------------------------------
# Decision Traces
# ---------------------------------------------------------------------------


class TestTraces:
    def test_create_trace(self, client):
        """POST /api/traces creates a decision trace and returns 201."""
        body = {
            "type": "fix",
            "summary": "Fixed null pointer",
            "rationale": "Added null check",
            "files": ["src/store.py"],
            "categories": ["null-pointer"],
            "actor": "agent",
            "outcome": "resolved",
        }
        resp = client.post("/api/traces", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["summary"] == "Fixed null pointer"
        assert data["decision_type"] == "bug_fix"
        assert "id" in data
        assert data["files_affected"] == ["src/store.py"]

    def test_create_trace_invalid_type(self, client):
        """POST /api/traces with invalid type returns 422."""
        body = {"type": "invalid_type", "summary": "test"}
        resp = client.post("/api/traces", json=body)
        assert resp.status_code == 422

    def test_list_traces(self, client, api_store):
        """GET /api/traces returns all traces."""
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX, summary="Fix 1",
        ).to_node())
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.FEATURE, summary="Feature 1",
        ).to_node())

        resp = client.get("/api/traces")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_traces_with_file_filter(self, client, api_store):
        """GET /api/traces?file=path filters traces by file."""
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX, summary="Fix store",
            files_affected=["src/store.py"],
        ).to_node())
        api_store.add_node(DecisionTrace(
            decision_type=DecisionType.FEATURE, summary="Feature cli",
            files_affected=["src/cli.py"],
        ).to_node())

        resp = client.get("/api/traces?file=src/store.py")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["summary"] == "Fix store"

    def test_create_then_list(self, client):
        """POST + GET roundtrip: created trace appears in list."""
        body = {"type": "fix", "summary": "Roundtrip test", "files": ["x.py"]}
        create_resp = client.post("/api/traces", json=body)
        assert create_resp.status_code == 201
        trace_id = create_resp.json()["id"]

        list_resp = client.get("/api/traces")
        ids = {t["id"] for t in list_resp.json()}
        assert trace_id in ids


# ---------------------------------------------------------------------------
# Trajectory
# ---------------------------------------------------------------------------


class TestTrajectory:
    def test_start_trajectory(self, client):
        """POST /api/trajectory/start creates a trajectory."""
        resp = client.post("/api/trajectory/start", json={
            "agent_id": "test-agent",
            "description": "Testing trajectory",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "trajectory_id" in data
        assert len(data["trajectory_id"]) > 0

    def test_trajectory_lifecycle(self, client, api_store):
        """Full lifecycle: start -> step -> step -> end."""
        # Need a node to reference in steps
        api_store.add_node(Node(id="test-node", node_type=NodeType.CODE_UNIT, name="x.py"))

        # Start
        start_resp = client.post("/api/trajectory/start", json={
            "agent_id": "agent-1",
            "description": "Investigating bug",
        })
        assert start_resp.status_code == 201
        tid = start_resp.json()["trajectory_id"]

        # Step 1
        step1_resp = client.post("/api/trajectory/step", json={
            "trajectory_id": tid,
            "node_id": "test-node",
            "action": "read_file",
        })
        assert step1_resp.status_code == 200
        assert step1_resp.json()["status"] == "recorded"

        # Step 2
        step2_resp = client.post("/api/trajectory/step", json={
            "trajectory_id": tid,
            "node_id": "test-node",
            "action": "analyze",
        })
        assert step2_resp.status_code == 200

        # End
        end_resp = client.post("/api/trajectory/end", json={
            "trajectory_id": tid,
        })
        assert end_resp.status_code == 200
        assert end_resp.json()["status"] == "ended"

        # Verify the trajectory is recorded
        traj = api_store.get_trajectory(tid)
        assert traj["id"] == tid
        assert len(traj["steps"]) == 2
        assert traj["ended_at"] is not None

    def test_step_nonexistent_trajectory(self, client):
        """POST /api/trajectory/step with invalid trajectory returns 404."""
        resp = client.post("/api/trajectory/step", json={
            "trajectory_id": "nonexistent",
            "node_id": "n1",
            "action": "test",
        })
        assert resp.status_code == 404

    def test_end_nonexistent_trajectory(self, client):
        """POST /api/trajectory/end with invalid trajectory returns 404."""
        resp = client.post("/api/trajectory/end", json={
            "trajectory_id": "nonexistent",
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORS:
    def test_cors_headers_present(self, client):
        """Preflight CORS request returns correct headers for localhost:3000."""
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_disallowed_origin(self, client):
        """CORS should not allow arbitrary origins."""
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # The header should either be absent or not match the evil origin
        origin = resp.headers.get("access-control-allow-origin")
        assert origin != "http://evil.example.com"

    def test_cors_127_allowed(self, client):
        """CORS allows 127.0.0.1:3000 as well."""
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
