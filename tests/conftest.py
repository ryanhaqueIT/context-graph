"""Shared fixtures and path setup for the test suite."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from context_graph.engine.store import GraphStore  # noqa: E402
from context_graph.models.nodes import (  # noqa: E402
    DecisionTrace,
    DecisionType,
    Edge,
    EdgeType,
    Node,
    NodeType,
)
from context_graph.query.interface import QueryInterface  # noqa: E402


@pytest.fixture()
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        yield Path(d)


@pytest.fixture()
def store(tmp_dir):
    """Provide an initialized GraphStore in a temp directory."""
    s = GraphStore(tmp_dir / "graph")
    s.initialize()
    yield s
    s.close()


@pytest.fixture()
def query_interface(store):
    """Provide a QueryInterface backed by an empty store."""
    return QueryInterface(store)


@pytest.fixture()
def populated_store(store):
    """Provide a store pre-loaded with a small graph for traversal tests.

    Graph topology:
        file_a  <--MODIFIES--  commit_1  --MODIFIES-->  file_b
        file_b  <--MODIFIES--  commit_2  --CAUSES-->    bug_1
        bug_1   <--FIXES--     trace_1
    """
    file_a = Node(id="file_a", node_type=NodeType.CODE_UNIT, name="a.py",
                  properties={"file_path": "src/a.py"})
    file_b = Node(id="file_b", node_type=NodeType.CODE_UNIT, name="b.py",
                  properties={"file_path": "src/b.py"})
    commit_1 = Node(id="commit_1", node_type=NodeType.CODE_CHANGE, name="initial commit",
                    properties={"commit_hash": "aaa111", "author": "alice", "date": "2025-01-01"})
    commit_2 = Node(id="commit_2", node_type=NodeType.CODE_CHANGE, name="refactor b",
                    properties={"commit_hash": "bbb222", "author": "bob", "date": "2025-01-02"})
    bug_1 = Node(id="bug_1", node_type=NodeType.INCIDENT, name="null pointer in b.py")
    trace_1 = DecisionTrace(
        id="trace_1",
        decision_type=DecisionType.BUG_FIX,
        summary="Fixed null pointer in b.py",
        rationale="Added null check before dereference",
        files_affected=["src/b.py"],
        categories=["null-pointer"],
    )

    for n in [file_a, file_b, commit_1, commit_2, bug_1]:
        store.add_node(n)
    store.add_node(trace_1.to_node())

    store.add_edge(Edge(id="e1", edge_type=EdgeType.MODIFIES,
                        source_id="commit_1", target_id="file_a"))
    store.add_edge(Edge(id="e2", edge_type=EdgeType.MODIFIES,
                        source_id="commit_1", target_id="file_b"))
    store.add_edge(Edge(id="e3", edge_type=EdgeType.MODIFIES,
                        source_id="commit_2", target_id="file_b"))
    store.add_edge(Edge(id="e4", edge_type=EdgeType.CAUSES,
                        source_id="commit_2", target_id="bug_1"))
    store.add_edge(Edge(id="e5", edge_type=EdgeType.FIXES,
                        source_id="trace_1", target_id="bug_1"))

    return store
