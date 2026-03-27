"""Tests for the CLI entry point.

Uses subprocess.run to invoke the CLI as a child process,
ensuring the full command-line interface works end-to-end.
All tests use temporary directories for isolation.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"


def _run_cli(*args: str, graph_dir: str | None = None) -> subprocess.CompletedProcess:
    """Run the context-graph CLI as a subprocess.

    Uses ``python -m context_graph`` so PYTHONPATH is all we need.
    """
    cmd = [sys.executable, "-m", "context_graph"]
    if graph_dir:
        cmd.extend(["--dir", graph_dir])
    cmd.extend(args)

    env = {"PYTHONPATH": str(SRC_DIR), "PATH": ""}
    # Merge with minimal env to allow python to find itself
    import os
    env["PATH"] = os.environ.get("PATH", "")
    env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "")

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


def test_init_command():
    """'context-graph init' creates the graph store directory and schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "graph")
        result = _run_cli("init", graph_dir=graph_dir)

        assert result.returncode == 0
        assert "initialized" in result.stdout.lower()
        assert Path(graph_dir).exists()
        assert (Path(graph_dir) / "graph.db").exists()


def test_init_command_idempotent():
    """Running init twice does not error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "graph")
        result1 = _run_cli("init", graph_dir=graph_dir)
        assert result1.returncode == 0

        result2 = _run_cli("init", graph_dir=graph_dir)
        assert result2.returncode == 0


# ---------------------------------------------------------------------------
# health command
# ---------------------------------------------------------------------------


def test_health_command():
    """'context-graph health' prints a report for an initialized store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "graph")
        _run_cli("init", graph_dir=graph_dir)

        result = _run_cli("health", graph_dir=graph_dir)
        assert result.returncode == 0
        assert "total nodes" in result.stdout.lower() or "Total nodes" in result.stdout


def test_health_command_uninitialized():
    """'context-graph health' on uninitialized store exits with error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "empty_graph")
        result = _run_cli("health", graph_dir=graph_dir)
        assert result.returncode != 0
        assert "not initialized" in result.stderr.lower() or "init" in result.stderr.lower()


# ---------------------------------------------------------------------------
# record + query roundtrip
# ---------------------------------------------------------------------------


def test_record_and_query_roundtrip():
    """A recorded DecisionTrace can be queried back."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "graph")

        # Step 1: Initialize
        init_result = _run_cli("init", graph_dir=graph_dir)
        assert init_result.returncode == 0

        # Step 2: Record a decision trace
        record_result = _run_cli(
            "record",
            "--type", "fix",
            "--file", "src/engine/store.py",
            "--summary", "Fixed null pointer in store",
            "--rationale", "Added null check before dereference",
            "--category", "null-pointer,defensive-coding",
            "--evidence", "commit:abc123,ticket:BUG-42",
            graph_dir=graph_dir,
        )
        assert record_result.returncode == 0
        assert "DecisionTrace recorded" in record_result.stdout

        # Step 3: Query incidents for that file
        query_result = _run_cli(
            "query", "incidents",
            "--file", "src/engine/store.py",
            graph_dir=graph_dir,
        )
        assert query_result.returncode == 0
        assert "Fixed null pointer in store" in query_result.stdout

        # Step 4: Query decisions for the module
        module_result = _run_cli(
            "query", "decisions",
            "--module", "engine",
            graph_dir=graph_dir,
        )
        assert module_result.returncode == 0
        assert "Fixed null pointer in store" in module_result.stdout

        # Step 5: Query fix patterns
        pattern_result = _run_cli(
            "query", "patterns",
            graph_dir=graph_dir,
        )
        assert pattern_result.returncode == 0
        assert "null-pointer" in pattern_result.stdout


def test_record_multiple_files():
    """Recording a trace with multiple --file flags works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "graph")
        _run_cli("init", graph_dir=graph_dir)

        result = _run_cli(
            "record",
            "--type", "fix",
            "--file", "src/a.py",
            "--file", "src/b.py",
            "--summary", "Multi-file fix",
            graph_dir=graph_dir,
        )
        assert result.returncode == 0

        # Both files should be queryable
        query_a = _run_cli("query", "incidents", "--file", "src/a.py",
                           graph_dir=graph_dir)
        assert "Multi-file fix" in query_a.stdout

        query_b = _run_cli("query", "incidents", "--file", "src/b.py",
                           graph_dir=graph_dir)
        assert "Multi-file fix" in query_b.stdout


def test_record_without_init():
    """Recording to an uninitialized store fails with a helpful error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "nograph")
        result = _run_cli(
            "record",
            "--type", "fix",
            "--file", "x.py",
            "--summary", "Should fail",
            graph_dir=graph_dir,
        )
        assert result.returncode != 0
        assert "not initialized" in result.stderr.lower() or "init" in result.stderr.lower()


def test_query_no_results():
    """Querying a file with no incidents succeeds without error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "graph")
        _run_cli("init", graph_dir=graph_dir)

        result = _run_cli(
            "query", "incidents",
            "--file", "nonexistent.py",
            graph_dir=graph_dir,
        )
        assert result.returncode == 0
        # Should not contain any actual trace summaries (no bracketed dates)
        # The CLI may print a "no incidents" message or just empty output
        assert "[" not in result.stdout or "no incidents" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_no_command_shows_help():
    """Running with no subcommand shows usage/help."""
    result = _run_cli()
    # argparse exits with code 1 when no command given (per the main() logic)
    assert result.returncode != 0 or "usage" in result.stdout.lower()


def test_record_all_decision_types():
    """All decision types can be recorded via the CLI."""
    decision_types = ["fix", "review", "architecture", "validation",
                      "refactor", "feature", "incident"]

    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = str(Path(tmpdir) / "graph")
        _run_cli("init", graph_dir=graph_dir)

        for dt in decision_types:
            result = _run_cli(
                "record",
                "--type", dt,
                "--file", f"src/{dt}_test.py",
                "--summary", f"Test {dt} decision",
                graph_dir=graph_dir,
            )
            assert result.returncode == 0, f"Failed to record type '{dt}': {result.stderr}"
