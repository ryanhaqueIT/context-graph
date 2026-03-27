"""Tests for the SQLite-backed graph storage engine.

Covers table creation, node/edge CRUD, indexing, BFS traversal,
pathfinding, trajectory lifecycle, co-occurrence stats, persistence,
counts, and concurrent reads via WAL mode.
All tests use temporary directories for full isolation.
"""

import tempfile
from collections import deque
from pathlib import Path

import pytest

from context_graph.engine.store import GraphStore
from context_graph.models.nodes import (
    DecisionTrace,
    DecisionType,
    Edge,
    EdgeType,
    Node,
    NodeType,
)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_initialize_creates_tables(tmp_dir):
    """Initializing a new store creates the database file and tables."""
    graph_path = tmp_dir / "graph"
    store = GraphStore(graph_path)
    store.initialize()

    # SQLite-backed store creates graph.db inside the directory
    assert graph_path.exists()
    db_file = graph_path / "graph.db"
    assert db_file.exists()
    assert store.is_initialized
    store.close()


def test_initialize_is_idempotent(tmp_dir):
    """Calling initialize twice must not corrupt existing data."""
    store = GraphStore(tmp_dir / "graph")
    store.initialize()
    store.add_node(Node(node_type=NodeType.CODE_UNIT, name="x.py"))
    assert store.node_count == 1

    # Re-initialize: data should still be present after reload
    store.initialize()
    assert store.node_count == 1
    store.close()


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def test_add_and_get_node(store):
    """A node can be stored and retrieved by its ID."""
    node = Node(node_type=NodeType.CODE_UNIT, name="src/main.py",
                properties={"file_path": "src/main.py", "language": "python"})
    store.add_node(node)

    retrieved = store.get_node(node.id)
    assert retrieved is not None
    assert retrieved.id == node.id
    assert retrieved.name == "src/main.py"
    assert retrieved.node_type == NodeType.CODE_UNIT
    assert retrieved.properties["language"] == "python"


def test_get_node_nonexistent(store):
    """Requesting a node that does not exist returns None."""
    assert store.get_node("does-not-exist") is None


def test_add_and_get_edge(store):
    """An edge can be stored and retrieved via its source node."""
    n1 = Node(node_type=NodeType.CODE_CHANGE, name="commit abc")
    n2 = Node(node_type=NodeType.CODE_UNIT, name="src/foo.py")
    store.add_node(n1)
    store.add_node(n2)

    edge = Edge(edge_type=EdgeType.MODIFIES, source_id=n1.id, target_id=n2.id,
                properties={"lines_changed": 42})
    store.add_edge(edge)

    edges_from = store.get_edges_from(n1.id)
    assert len(edges_from) == 1
    assert edges_from[0].target_id == n2.id
    assert edges_from[0].edge_type == EdgeType.MODIFIES

    edges_to = store.get_edges_to(n2.id)
    assert len(edges_to) == 1
    assert edges_to[0].source_id == n1.id


def test_get_edges_from_empty(store):
    """Querying edges from a node with no outgoing edges returns empty list."""
    n = Node(node_type=NodeType.CODE_UNIT, name="isolated.py")
    store.add_node(n)
    assert store.get_edges_from(n.id) == []


def test_get_edges_to_empty(store):
    """Querying edges to a node with no incoming edges returns empty list."""
    n = Node(node_type=NodeType.CODE_UNIT, name="lonely.py")
    store.add_node(n)
    assert store.get_edges_to(n.id) == []


# ---------------------------------------------------------------------------
# Index lookups
# ---------------------------------------------------------------------------


def test_get_nodes_by_type(store):
    """Nodes can be fetched by their NodeType."""
    store.add_node(Node(node_type=NodeType.CODE_UNIT, name="a.py"))
    store.add_node(Node(node_type=NodeType.CODE_UNIT, name="b.py"))
    store.add_node(Node(node_type=NodeType.CODE_CHANGE, name="commit"))

    code_units = store.get_nodes_by_type(NodeType.CODE_UNIT)
    assert len(code_units) == 2
    names = {n.name for n in code_units}
    assert names == {"a.py", "b.py"}

    changes = store.get_nodes_by_type(NodeType.CODE_CHANGE)
    assert len(changes) == 1

    incidents = store.get_nodes_by_type(NodeType.INCIDENT)
    assert len(incidents) == 0


def test_get_nodes_by_name(store):
    """Nodes can be found by exact or substring name match."""
    store.add_node(Node(node_type=NodeType.CODE_UNIT, name="engine/store.py"))
    store.add_node(Node(node_type=NodeType.CODE_UNIT, name="engine/cache.py"))
    store.add_node(Node(node_type=NodeType.CODE_UNIT, name="cli/main.py"))

    # Substring match
    engine_nodes = store.get_nodes_by_name("engine")
    assert len(engine_nodes) == 2

    # Exact match
    exact = store.get_nodes_by_name("cli/main.py")
    assert len(exact) == 1
    assert exact[0].name == "cli/main.py"

    # No match
    assert store.get_nodes_by_name("nonexistent") == []


def test_find_nodes_by_property(store):
    """Nodes can be found by a property key-value substring match."""
    store.add_node(Node(
        node_type=NodeType.CODE_UNIT, name="foo",
        properties={"file_path": "src/engine/store.py"},
    ))
    store.add_node(Node(
        node_type=NodeType.CODE_UNIT, name="bar",
        properties={"file_path": "src/cli/main.py"},
    ))

    # Substring match in property value
    found = store.find_nodes_by_property("file_path", "engine/store.py")
    assert len(found) == 1
    assert found[0].name == "foo"

    # Filtered by type
    found_typed = store.find_nodes_by_property(
        "file_path", "engine/store.py", NodeType.CODE_UNIT
    )
    assert len(found_typed) == 1

    # Wrong type yields nothing
    found_wrong = store.find_nodes_by_property(
        "file_path", "engine/store.py", NodeType.INCIDENT
    )
    assert len(found_wrong) == 0


def test_find_nodes_by_property_no_match(store):
    """Finding by a property that no node has returns an empty list."""
    store.add_node(Node(node_type=NodeType.CODE_UNIT, name="x", properties={"lang": "py"}))
    assert store.find_nodes_by_property("lang", "rust") == []


# ---------------------------------------------------------------------------
# Edge lookups
# ---------------------------------------------------------------------------


def test_get_edges_from_and_to(store):
    """Edges can be retrieved by source or target node."""
    a = Node(id="a", node_type=NodeType.CODE_CHANGE, name="commit a")
    b = Node(id="b", node_type=NodeType.CODE_UNIT, name="b.py")
    c = Node(id="c", node_type=NodeType.CODE_UNIT, name="c.py")
    store.add_node(a)
    store.add_node(b)
    store.add_node(c)

    store.add_edge(Edge(edge_type=EdgeType.MODIFIES, source_id="a", target_id="b"))
    store.add_edge(Edge(edge_type=EdgeType.MODIFIES, source_id="a", target_id="c"))

    from_a = store.get_edges_from("a")
    assert len(from_a) == 2
    targets = {e.target_id for e in from_a}
    assert targets == {"b", "c"}

    to_b = store.get_edges_to("b")
    assert len(to_b) == 1
    assert to_b[0].source_id == "a"


# ---------------------------------------------------------------------------
# Graph traversal
# ---------------------------------------------------------------------------


def test_connected_nodes(store):
    """get_connected_nodes returns all direct neighbors in either direction."""
    n1 = Node(id="n1", node_type=NodeType.CODE_CHANGE, name="commit")
    n2 = Node(id="n2", node_type=NodeType.CODE_UNIT, name="file.py")
    n3 = Node(id="n3", node_type=NodeType.INCIDENT, name="bug")
    n4 = Node(id="n4", node_type=NodeType.CODE_UNIT, name="other.py")
    store.add_node(n1)
    store.add_node(n2)
    store.add_node(n3)
    store.add_node(n4)

    # n1 -> n2, n1 -> n3 (outgoing)
    store.add_edge(Edge(edge_type=EdgeType.MODIFIES, source_id="n1", target_id="n2"))
    store.add_edge(Edge(edge_type=EdgeType.CAUSES, source_id="n1", target_id="n3"))
    # n4 -> n1 (incoming to n1)
    store.add_edge(Edge(edge_type=EdgeType.PRECEDED_BY, source_id="n4", target_id="n1"))

    connected = store.get_connected_nodes("n1")
    connected_ids = {n.id for n in connected}
    assert connected_ids == {"n2", "n3", "n4"}


def test_connected_nodes_isolated(store):
    """A node with no edges has no connected nodes."""
    n = Node(id="lonely", node_type=NodeType.CODE_UNIT, name="lonely.py")
    store.add_node(n)
    assert store.get_connected_nodes("lonely") == []


def test_traverse_bfs(populated_store):
    """The native store.traverse BFS reaches all reachable nodes from file_a."""
    store = populated_store

    reachable = store.traverse("file_a", max_depth=10)
    reachable_ids = {n.id for n in reachable}

    # file_a connects to commit_1, which connects to file_b, commit_2, etc.
    assert "commit_1" in reachable_ids
    assert "file_b" in reachable_ids
    assert "commit_2" in reachable_ids
    assert "bug_1" in reachable_ids
    assert "trace_1" in reachable_ids
    # file_a itself is the start node and not included in results
    assert "file_a" not in reachable_ids


def test_traverse_bfs_with_depth_limit(populated_store):
    """BFS respects the max_depth parameter."""
    store = populated_store

    # Depth 1: only immediate neighbors of file_a
    depth1 = store.traverse("file_a", max_depth=1)
    depth1_ids = {n.id for n in depth1}
    assert "commit_1" in depth1_ids
    # Nodes further away should not appear
    assert "bug_1" not in depth1_ids


def test_traverse_bfs_with_edge_type_filter(populated_store):
    """BFS can be filtered by edge type."""
    store = populated_store

    # Only follow MODIFIES edges
    reachable = store.traverse("commit_1", edge_types=[EdgeType.MODIFIES], max_depth=5)
    reachable_ids = {n.id for n in reachable}
    assert "file_a" in reachable_ids
    assert "file_b" in reachable_ids
    # bug_1 is linked via CAUSES, should not appear
    assert "bug_1" not in reachable_ids


def test_find_paths(populated_store):
    """The native store.find_paths discovers paths between nodes."""
    store = populated_store

    paths = store.find_paths("file_a", "bug_1")
    assert len(paths) >= 1

    for path in paths:
        assert path[0] == "file_a"
        assert path[-1] == "bug_1"
        assert len(path) >= 3


def test_find_paths_no_connection(store):
    """find_paths returns empty when nodes are not connected."""
    a = Node(id="island_a", node_type=NodeType.CODE_UNIT, name="a.py")
    b = Node(id="island_b", node_type=NodeType.CODE_UNIT, name="b.py")
    store.add_node(a)
    store.add_node(b)

    paths = store.find_paths("island_a", "island_b")
    assert paths == []


# ---------------------------------------------------------------------------
# Trajectory lifecycle (native SQLite trajectory tables)
# ---------------------------------------------------------------------------


def test_trajectory_lifecycle(store):
    """A trajectory can be started, steps recorded, ended, and retrieved."""
    # Create step target nodes
    for i in range(4):
        store.add_node(Node(
            id=f"target_{i}", node_type=NodeType.CODE_UNIT, name=f"file_{i}.py",
        ))

    # Start trajectory
    tid = store.start_trajectory(agent_id="agent-42", description="Fix auth bug")
    assert tid  # non-empty UUID string

    # Record steps
    actions = ["read auth.py", "analyze logs", "edit auth.py", "run tests"]
    for i, action in enumerate(actions):
        store.record_step(tid, node_id=f"target_{i}", action=action)

    # End trajectory
    store.end_trajectory(tid)

    # Retrieve and verify
    traj = store.get_trajectory(tid)
    assert traj["id"] == tid
    assert traj["agent_id"] == "agent-42"
    assert traj["description"] == "Fix auth bug"
    assert traj["ended_at"] is not None

    steps = traj["steps"]
    assert len(steps) == 4
    for i, step in enumerate(steps):
        assert step["step_order"] == i
        assert step["action"] == actions[i]
        assert step["node_id"] == f"target_{i}"


def test_trajectory_get_nonexistent(store):
    """get_trajectory returns empty dict for unknown trajectory."""
    result = store.get_trajectory("nonexistent-id")
    assert result == {}


def test_trajectory_step_ordering(store):
    """Steps are auto-numbered in insertion order."""
    node = Node(id="n1", node_type=NodeType.CODE_UNIT, name="f.py")
    store.add_node(node)

    tid = store.start_trajectory("agent-1", "test ordering")
    store.record_step(tid, "n1", "step A")
    store.record_step(tid, "n1", "step B")
    store.record_step(tid, "n1", "step C")

    traj = store.get_trajectory(tid)
    orders = [s["step_order"] for s in traj["steps"]]
    assert orders == [0, 1, 2]


# ---------------------------------------------------------------------------
# Co-occurrence statistics
# ---------------------------------------------------------------------------


def test_co_occurrence_stats(store):
    """Nodes visited in the same trajectory produce co-occurrence counts."""
    for nid in ["alpha", "beta", "gamma"]:
        store.add_node(Node(id=nid, node_type=NodeType.CODE_UNIT, name=nid))

    # Trajectory 1: visits alpha, beta, gamma
    t1 = store.start_trajectory("agent-1", "traj 1")
    store.record_step(t1, "alpha", "read")
    store.record_step(t1, "beta", "read")
    store.record_step(t1, "gamma", "read")

    # Trajectory 2: visits alpha, beta only
    t2 = store.start_trajectory("agent-2", "traj 2")
    store.record_step(t2, "alpha", "read")
    store.record_step(t2, "beta", "edit")

    stats = store.get_co_occurrence_stats()

    # alpha-beta co-occurs in both trajectories
    assert stats.get("alpha|beta", 0) == 2
    # alpha-gamma and beta-gamma only in trajectory 1
    assert stats.get("alpha|gamma", 0) == 1
    assert stats.get("beta|gamma", 0) == 1


def test_co_occurrence_stats_empty(store):
    """Empty store has no co-occurrence stats."""
    assert store.get_co_occurrence_stats() == {}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_persistence(tmp_dir):
    """Data survives closing and reopening the store."""
    graph_path = tmp_dir / "graph"

    # Session 1: write data
    store1 = GraphStore(graph_path)
    store1.initialize()
    store1.add_node(Node(id="persist_node", node_type=NodeType.CODE_UNIT, name="persistent.py"))
    store1.add_edge(Edge(
        id="persist_edge",
        edge_type=EdgeType.REFERENCES,
        source_id="persist_node",
        target_id="persist_node",
    ))
    assert store1.node_count == 1
    assert store1.edge_count == 1

    store1.close()

    # Session 2: fresh instance, same directory
    store2 = GraphStore(graph_path)
    store2.initialize()
    assert store2.node_count == 1
    assert store2.edge_count == 1

    retrieved = store2.get_node("persist_node")
    assert retrieved is not None
    assert retrieved.name == "persistent.py"

    edges = store2.get_edges_from("persist_node")
    assert len(edges) == 1
    store2.close()


def test_persistence_accumulates(tmp_dir):
    """Data from multiple sessions accumulates."""
    graph_path = tmp_dir / "graph"

    store1 = GraphStore(graph_path)
    store1.initialize()
    store1.add_node(Node(node_type=NodeType.CODE_UNIT, name="first.py"))
    store1.close()

    store2 = GraphStore(graph_path)
    store2.initialize()
    store2.add_node(Node(node_type=NodeType.CODE_UNIT, name="second.py"))
    store2.close()

    store3 = GraphStore(graph_path)
    store3.initialize()
    assert store3.node_count == 2
    store3.close()


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------


def test_node_and_edge_counts(store):
    """node_count and edge_count reflect stored data."""
    assert store.node_count == 0
    assert store.edge_count == 0

    n1 = Node(node_type=NodeType.CODE_UNIT, name="a")
    n2 = Node(node_type=NodeType.CODE_UNIT, name="b")
    store.add_node(n1)
    store.add_node(n2)

    assert store.node_count == 2
    assert store.edge_count == 0

    store.add_edge(Edge(edge_type=EdgeType.REFERENCES, source_id=n1.id, target_id=n2.id))
    assert store.edge_count == 1


def test_node_and_edge_counts_populated(populated_store):
    """The populated fixture has 6 nodes and 5 edges."""
    assert populated_store.node_count == 6
    assert populated_store.edge_count == 5


# ---------------------------------------------------------------------------
# Concurrent reads (WAL mode readiness)
# ---------------------------------------------------------------------------


def test_concurrent_reads(tmp_dir):
    """Two store instances reading the same directory do not conflict.

    This verifies the JSONL store can handle concurrent read access
    (both load the same files independently).
    """
    graph_path = tmp_dir / "graph"

    # Set up data
    writer = GraphStore(graph_path)
    writer.initialize()
    for i in range(10):
        writer.add_node(Node(
            node_type=NodeType.CODE_UNIT,
            name=f"file_{i}.py",
            properties={"index": i},
        ))

    # Two independent readers
    reader_a = GraphStore(graph_path)
    reader_a.initialize()

    reader_b = GraphStore(graph_path)
    reader_b.initialize()

    assert reader_a.node_count == 10
    assert reader_b.node_count == 10

    # Both should see the same nodes
    nodes_a = {n.name for n in reader_a.get_nodes_by_type(NodeType.CODE_UNIT)}
    nodes_b = {n.name for n in reader_b.get_nodes_by_type(NodeType.CODE_UNIT)}
    assert nodes_a == nodes_b
    assert len(nodes_a) == 10

    writer.close()
    reader_a.close()
    reader_b.close()
