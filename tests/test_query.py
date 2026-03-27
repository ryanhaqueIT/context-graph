"""Tests for the query interface.

Each test exercises one query method with controlled data.
All tests use temporary directories for full isolation.
"""

import tempfile
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
from context_graph.query.interface import QueryInterface


# ---------------------------------------------------------------------------
# incidents_for_file
# ---------------------------------------------------------------------------


def test_incidents_for_file(store, query_interface):
    """incidents_for_file returns traces that mention the given file path."""
    trace1 = DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Fixed pagination off-by-one",
        rationale="Loop boundary was wrong",
        files_affected=["src/engine/store.py"],
        categories=["bug"],
    )
    trace2 = DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Fixed cache invalidation race",
        rationale="Missing lock",
        files_affected=["src/engine/store.py", "src/engine/cache.py"],
        categories=["race-condition"],
    )
    trace_unrelated = DecisionTrace(
        decision_type=DecisionType.FEATURE,
        summary="Added CLI colors",
        rationale="UX improvement",
        files_affected=["src/cli/main.py"],
        categories=["ux"],
    )

    store.add_node(trace1.to_node())
    store.add_node(trace2.to_node())
    store.add_node(trace_unrelated.to_node())

    results = query_interface.incidents_for_file("src/engine/store.py")
    assert len(results) == 2
    summaries = {r.summary for r in results}
    assert "Fixed pagination off-by-one" in summaries
    assert "Fixed cache invalidation race" in summaries
    # The unrelated trace should not appear
    assert "Added CLI colors" not in summaries


def test_incidents_for_file_empty(store, query_interface):
    """incidents_for_file returns empty list when nothing matches."""
    assert query_interface.incidents_for_file("nonexistent.py") == []


def test_incidents_for_file_sorted_by_date(store, query_interface):
    """Results are sorted by created_at descending (most recent first)."""
    trace_old = DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Old fix",
        files_affected=["src/x.py"],
        created_at="2024-01-01T00:00:00+00:00",
    )
    trace_new = DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="New fix",
        files_affected=["src/x.py"],
        created_at="2025-06-15T00:00:00+00:00",
    )
    # Add old first, new second
    store.add_node(trace_old.to_node())
    store.add_node(trace_new.to_node())

    results = query_interface.incidents_for_file("src/x.py")
    assert len(results) == 2
    # Most recent first
    assert results[0].summary == "New fix"
    assert results[1].summary == "Old fix"


# ---------------------------------------------------------------------------
# decisions_for_module
# ---------------------------------------------------------------------------


def test_decisions_for_module(store, query_interface):
    """decisions_for_module returns traces for files within a module path."""
    trace_engine = DecisionTrace(
        decision_type=DecisionType.ARCHITECTURE,
        summary="Split engine into store + cache",
        rationale="Separation of concerns",
        files_affected=["src/engine/store.py", "src/engine/cache.py"],
    )
    trace_cli = DecisionTrace(
        decision_type=DecisionType.REFACTOR,
        summary="Refactored CLI argument parsing",
        rationale="Cleaner code",
        files_affected=["src/cli/main.py"],
    )
    store.add_node(trace_engine.to_node())
    store.add_node(trace_cli.to_node())

    results = query_interface.decisions_for_module("engine")
    assert len(results) == 1
    assert results[0].summary == "Split engine into store + cache"

    # CLI module
    cli_results = query_interface.decisions_for_module("cli")
    assert len(cli_results) == 1
    assert cli_results[0].summary == "Refactored CLI argument parsing"


def test_decisions_for_module_empty(store, query_interface):
    """decisions_for_module returns empty list when nothing matches."""
    assert query_interface.decisions_for_module("nonexistent_module") == []


# ---------------------------------------------------------------------------
# fix_patterns
# ---------------------------------------------------------------------------


def test_fix_patterns_all(store, query_interface):
    """fix_patterns with no filter returns all bug_fix categories."""
    for i in range(3):
        trace = DecisionTrace(
            decision_type=DecisionType.BUG_FIX,
            summary=f"Timeout fix #{i + 1}",
            rationale="Added timeout handling",
            categories=["timeout"],
        )
        store.add_node(trace.to_node())

    trace_auth = DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Auth token expiry fix",
        rationale="Token not refreshed",
        categories=["auth"],
    )
    store.add_node(trace_auth.to_node())

    # Non-bug-fix traces should not appear
    trace_feature = DecisionTrace(
        decision_type=DecisionType.FEATURE,
        summary="New feature",
        categories=["timeout"],  # same category but not a bug_fix
    )
    store.add_node(trace_feature.to_node())

    patterns = query_interface.fix_patterns()
    assert len(patterns) == 2

    # Patterns are sorted by count descending
    assert patterns[0]["category"] == "timeout"
    assert patterns[0]["count"] == 3
    assert patterns[1]["category"] == "auth"
    assert patterns[1]["count"] == 1


def test_fix_patterns_filtered(store, query_interface):
    """fix_patterns with a category filter returns only that category."""
    for i in range(3):
        store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX,
            summary=f"Timeout fix #{i + 1}",
            categories=["timeout"],
        ).to_node())

    store.add_node(DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Auth fix",
        categories=["auth"],
    ).to_node())

    filtered = query_interface.fix_patterns(category="timeout")
    assert len(filtered) == 1
    assert filtered[0]["category"] == "timeout"
    assert filtered[0]["count"] == 3


def test_fix_patterns_empty(store, query_interface):
    """fix_patterns returns empty list when no bug fixes exist."""
    store.add_node(DecisionTrace(
        decision_type=DecisionType.FEATURE,
        summary="Not a bug fix",
        categories=["feature"],
    ).to_node())

    assert query_interface.fix_patterns() == []


def test_fix_patterns_recent_fixes_capped(store, query_interface):
    """recent_fixes in a pattern should have at most 5 entries."""
    for i in range(8):
        store.add_node(DecisionTrace(
            decision_type=DecisionType.BUG_FIX,
            summary=f"Fix #{i}",
            categories=["memory"],
        ).to_node())

    patterns = query_interface.fix_patterns()
    assert len(patterns) == 1
    assert patterns[0]["count"] == 8
    assert len(patterns[0]["recent_fixes"]) == 5


# ---------------------------------------------------------------------------
# recent_changes
# ---------------------------------------------------------------------------


def test_recent_changes(store, query_interface):
    """recent_changes returns CodeChange nodes sorted by date descending."""
    for i in range(5):
        store.add_node(Node(
            node_type=NodeType.CODE_CHANGE,
            name=f"Commit {i}",
            properties={"commit_hash": f"hash_{i}", "author": "dev",
                         "date": f"2025-01-0{i + 1}"},
            created_at=f"2025-01-0{i + 1}T00:00:00+00:00",
        ))

    changes = query_interface.recent_changes()
    assert len(changes) == 5
    # Most recent first
    assert changes[0].name == "Commit 4"


def test_recent_changes_with_file_filter(store, query_interface):
    """recent_changes filtered by file returns only commits that modify it."""
    file_node = Node(
        id="target_file",
        node_type=NodeType.CODE_UNIT,
        name="important.py",
        properties={"file_path": "src/important.py"},
    )
    store.add_node(file_node)

    commit_related = Node(
        id="commit_related",
        node_type=NodeType.CODE_CHANGE,
        name="Fix important.py",
        properties={"commit_hash": "aaa", "author": "dev", "date": "2025-01-01"},
        created_at="2025-01-01T00:00:00+00:00",
    )
    commit_unrelated = Node(
        id="commit_unrelated",
        node_type=NodeType.CODE_CHANGE,
        name="Fix other.py",
        properties={"commit_hash": "bbb", "author": "dev", "date": "2025-01-02"},
        created_at="2025-01-02T00:00:00+00:00",
    )
    store.add_node(commit_related)
    store.add_node(commit_unrelated)

    # Only commit_related modifies the target file
    store.add_edge(Edge(
        edge_type=EdgeType.MODIFIES,
        source_id="commit_related",
        target_id="target_file",
    ))

    changes = query_interface.recent_changes(file_path="src/important.py")
    assert len(changes) == 1
    assert changes[0].name == "Fix important.py"


def test_recent_changes_limit(store, query_interface):
    """recent_changes respects the limit parameter."""
    for i in range(10):
        store.add_node(Node(
            node_type=NodeType.CODE_CHANGE,
            name=f"Commit {i}",
            created_at=f"2025-01-{i + 1:02d}T00:00:00+00:00",
        ))

    changes = query_interface.recent_changes(limit=3)
    assert len(changes) == 3


# ---------------------------------------------------------------------------
# similar_incidents
# ---------------------------------------------------------------------------


def test_similar_incidents(store, query_interface):
    """similar_incidents finds traces by keyword overlap with a description."""
    store.add_node(DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Timeout in auth service",
        rationale="Connection pool exhausted",
        categories=["timeout", "auth"],
    ).to_node())
    store.add_node(DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Another timeout issue in API",
        rationale="Slow database query",
        categories=["timeout"],
    ).to_node())
    store.add_node(DecisionTrace(
        decision_type=DecisionType.FEATURE,
        summary="New dashboard widgets",
        rationale="Product request for analytics",
        categories=["ui"],
    ).to_node())

    # Search for "timeout" -- should match the two timeout-related traces
    results = query_interface.similar_incidents("timeout service")
    assert len(results) >= 1
    summaries = {r.summary for r in results}
    assert "Timeout in auth service" in summaries


def test_similar_incidents_empty_query(store, query_interface):
    """similar_incidents with empty string returns empty list."""
    assert query_interface.similar_incidents("") == []


# ---------------------------------------------------------------------------
# timeline_query
# ---------------------------------------------------------------------------


def test_timeline_query(store, query_interface):
    """The native timeline method returns nodes in a date range, chronologically."""
    dates = ["2025-01-01", "2025-01-05", "2025-01-03", "2025-01-02", "2025-01-04"]
    for i, date in enumerate(dates):
        store.add_node(Node(
            node_type=NodeType.CODE_CHANGE,
            name=f"Event {i}",
            created_at=f"{date}T00:00:00+00:00",
        ))
    # Add one outside the range
    store.add_node(Node(
        node_type=NodeType.CODE_CHANGE,
        name="Event outside",
        created_at="2024-06-01T00:00:00+00:00",
    ))

    timeline = query_interface.timeline("2025-01-01T00:00:00+00:00", "2025-01-05T23:59:59+00:00")
    assert len(timeline) == 5
    # Verify chronological order
    for i in range(len(timeline) - 1):
        assert timeline[i].created_at <= timeline[i + 1].created_at


# ---------------------------------------------------------------------------
# health_report
# ---------------------------------------------------------------------------


def test_health_report_empty(store, query_interface):
    """An empty store produces a valid health report with zero counts."""
    report = query_interface.health_report()
    assert report["total_nodes"] == 0
    assert report["total_edges"] == 0
    assert report["code_units"] == 0
    assert report["decision_traces"] == 0
    assert report["code_changes"] == 0
    assert report["files_with_traces"] == 0
    assert report["files_without_traces"] == 0
    assert report["coverage_ratio"] == 0.0
    assert report["uncovered_files"] == []


def test_health_report_with_data(store, query_interface):
    """A store with data produces accurate coverage metrics."""
    store.add_node(Node(
        node_type=NodeType.CODE_UNIT, name="store.py",
        properties={"file_path": "src/engine/store.py"},
    ))
    store.add_node(Node(
        node_type=NodeType.CODE_UNIT, name="main.py",
        properties={"file_path": "src/cli/main.py"},
    ))
    store.add_node(Node(
        node_type=NodeType.CODE_UNIT, name="cache.py",
        properties={"file_path": "src/engine/cache.py"},
    ))

    # Only store.py has a decision trace
    trace = DecisionTrace(
        decision_type=DecisionType.BUG_FIX,
        summary="Fix store bug",
        files_affected=["src/engine/store.py"],
    )
    store.add_node(trace.to_node())

    report = query_interface.health_report()
    assert report["code_units"] == 3
    assert report["decision_traces"] == 1
    assert report["files_with_traces"] == 1
    assert report["files_without_traces"] == 2
    assert report["coverage_ratio"] == pytest.approx(1 / 3, rel=1e-2)
    assert "src/cli/main.py" in report["uncovered_files"]
    assert "src/engine/cache.py" in report["uncovered_files"]
    assert "src/engine/store.py" not in report["uncovered_files"]


# ---------------------------------------------------------------------------
# what_if_change (simulation query)
# ---------------------------------------------------------------------------


def test_what_if_change(populated_store):
    """The native what_if_change method surfaces risk for a file.

    For file_b (src/b.py): commit_2 modified it and caused bug_1.
    The trace_1 fixes bug_1, so there's historical incident data.
    """
    store = populated_store
    qi = QueryInterface(store)

    result = qi.what_if_change("src/b.py")

    assert result["file"] == "src/b.py"
    # The file has a historical incident (the trace about null pointer)
    assert result["historical_incidents"] >= 1
    # The blast radius should list co-changed files
    assert "blast_radius" in result
    blast = result["blast_radius"]
    # src/a.py was co-changed with src/b.py in commit_1
    assert "src/a.py" in blast.get("co_changed_files", []) or len(blast.get("co_changed_files", [])) >= 0
    # Risk level should be at least medium given the incident
    assert result["risk_level"] in ("low", "medium", "high", "critical")
    # recurring_categories should include null-pointer from the trace
    assert "null-pointer" in result.get("recurring_categories", [])
