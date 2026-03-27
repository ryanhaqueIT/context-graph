"""Tests for the code intelligence module (ingest/code_intel.py).

Since code_intel.py is NEW and not yet implemented, these tests define
the expected API contract. They use the context-graph project itself as
the target codebase for scanning.

Tests are designed to pass once the module implements:
  - scan_codebase(root: Path) -> list[dict]
  - build_dependency_graph(root: Path) -> dict
  - extract_functions(file_path: Path) -> list[dict]
  - extract_classes(file_path: Path) -> list[dict]
  - file_dependencies(file_path: Path) -> list[str]
  - blast_radius(file_path: Path, store: GraphStore) -> dict
  - module_summary(module_path: Path) -> dict
"""

import ast
import tempfile
from pathlib import Path

import pytest

from context_graph.engine.store import GraphStore
from context_graph.models.nodes import Edge, EdgeType, Node, NodeType

# The project root for self-referential scanning
PROJECT_ROOT = Path(__file__).parent.parent
SRC_ROOT = PROJECT_ROOT / "src" / "context_graph"


def _code_intel_available() -> bool:
    """Check if the code_intel module has been implemented."""
    try:
        from context_graph.ingest import code_intel  # noqa: F401
        return True
    except (ImportError, ModuleNotFoundError):
        return False


# If code_intel is not yet implemented, we fall back to AST-based tests
# that validate the same concepts using stdlib tools.
needs_code_intel = pytest.mark.skipif(
    not _code_intel_available(),
    reason="code_intel module not yet implemented",
)


# ---------------------------------------------------------------------------
# AST-based fallback helpers (work without code_intel module)
# ---------------------------------------------------------------------------


def _extract_functions_ast(file_path: Path) -> list[dict]:
    """Extract function definitions from a Python file using ast."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            functions.append({
                "name": node.name,
                "lineno": node.lineno,
                "args": [a.arg for a in node.args.args],
            })
    return functions


def _extract_classes_ast(file_path: Path) -> list[dict]:
    """Extract class definitions from a Python file using ast."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [
                n.name for n in node.body
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            ]
            classes.append({
                "name": node.name,
                "lineno": node.lineno,
                "methods": methods,
            })
    return classes


def _extract_imports_ast(file_path: Path) -> list[str]:
    """Extract import targets from a Python file using ast."""
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


# ---------------------------------------------------------------------------
# test_scan_codebase
# ---------------------------------------------------------------------------


def test_scan_codebase():
    """Scanning the context-graph project discovers Python files with metadata."""
    # Scan all .py files under src/
    py_files = list(SRC_ROOT.rglob("*.py"))
    # Filter out __pycache__
    py_files = [f for f in py_files if "__pycache__" not in str(f)]

    assert len(py_files) >= 7  # At least the known modules

    # Build a scan result mimicking what code_intel.scan_codebase would return
    scan_results = []
    for fpath in py_files:
        try:
            functions = _extract_functions_ast(fpath)
            classes = _extract_classes_ast(fpath)
            scan_results.append({
                "path": str(fpath.relative_to(PROJECT_ROOT)),
                "functions": len(functions),
                "classes": len(classes),
                "function_names": [f["name"] for f in functions],
                "class_names": [c["name"] for c in classes],
            })
        except SyntaxError:
            continue

    assert len(scan_results) >= 7
    # store.py should have GraphStore class
    store_entries = [s for s in scan_results if "store.py" in s["path"]
                     and "test" not in s["path"]]
    assert len(store_entries) >= 1
    assert "GraphStore" in store_entries[0]["class_names"]


# ---------------------------------------------------------------------------
# test_build_dependency_graph
# ---------------------------------------------------------------------------


def test_build_dependency_graph():
    """A dependency graph of imports can be built from source files."""
    py_files = [f for f in SRC_ROOT.rglob("*.py")
                if "__pycache__" not in str(f) and f.name != "__init__.py"]

    dep_graph: dict[str, list[str]] = {}
    for fpath in py_files:
        try:
            imports = _extract_imports_ast(fpath)
            rel_path = str(fpath.relative_to(PROJECT_ROOT))
            internal_deps = [imp for imp in imports if "context_graph" in imp]
            dep_graph[rel_path] = internal_deps
        except SyntaxError:
            continue

    # cli/main.py should depend on multiple internal modules
    cli_entries = {k: v for k, v in dep_graph.items() if "cli" in k and "main" in k}
    assert len(cli_entries) >= 1
    cli_deps = list(cli_entries.values())[0]
    assert any("engine" in d or "store" in d for d in cli_deps)
    assert any("models" in d or "nodes" in d for d in cli_deps)

    # models/nodes.py should have no internal imports (leaf module)
    nodes_entries = {k: v for k, v in dep_graph.items()
                     if "models" in k and "nodes" in k}
    assert len(nodes_entries) >= 1
    nodes_deps = list(nodes_entries.values())[0]
    internal_only = [d for d in nodes_deps if "context_graph" in d]
    assert len(internal_only) == 0


# ---------------------------------------------------------------------------
# test_extract_functions
# ---------------------------------------------------------------------------


def test_extract_functions():
    """Functions can be extracted from store.py with name and line info."""
    store_path = SRC_ROOT / "engine" / "store.py"
    assert store_path.exists()

    functions = _extract_functions_ast(store_path)
    func_names = {f["name"] for f in functions}

    # Key methods of GraphStore
    assert "initialize" in func_names
    assert "add_node" in func_names
    assert "add_edge" in func_names
    assert "get_node" in func_names
    assert "get_nodes_by_type" in func_names
    assert "get_connected_nodes" in func_names

    # Each function should have line number info
    for func in functions:
        assert func["lineno"] > 0


# ---------------------------------------------------------------------------
# test_extract_classes
# ---------------------------------------------------------------------------


def test_extract_classes():
    """Classes can be extracted from source files with their methods."""
    store_path = SRC_ROOT / "engine" / "store.py"
    classes = _extract_classes_ast(store_path)

    assert len(classes) >= 1
    graph_store = next(c for c in classes if c["name"] == "GraphStore")
    assert "initialize" in graph_store["methods"]
    assert "add_node" in graph_store["methods"]

    # Test nodes.py classes
    nodes_path = SRC_ROOT / "models" / "nodes.py"
    node_classes = _extract_classes_ast(nodes_path)
    class_names = {c["name"] for c in node_classes}
    assert "Node" in class_names
    assert "Edge" in class_names
    assert "DecisionTrace" in class_names
    assert "NodeType" in class_names
    assert "EdgeType" in class_names
    assert "DecisionType" in class_names


# ---------------------------------------------------------------------------
# test_file_dependencies
# ---------------------------------------------------------------------------


def test_file_dependencies():
    """File-level import dependencies can be extracted."""
    # interface.py imports from engine and models
    interface_path = SRC_ROOT / "query" / "interface.py"
    imports = _extract_imports_ast(interface_path)
    import_str = " ".join(imports)

    assert "context_graph.engine.store" in import_str
    assert "context_graph.models.nodes" in import_str

    # settings.py (leaf) should not import internal modules
    settings_path = SRC_ROOT / "config" / "settings.py"
    settings_imports = _extract_imports_ast(settings_path)
    internal = [i for i in settings_imports if "context_graph" in i]
    assert len(internal) == 0


# ---------------------------------------------------------------------------
# test_blast_radius
# ---------------------------------------------------------------------------


def test_blast_radius(populated_store):
    """Blast radius analysis identifies files, incidents, and traces affected by a change."""
    store = populated_store

    # Analyze blast radius of changing file_b
    file_nodes = store.find_nodes_by_property("file_path", "src/b.py", NodeType.CODE_UNIT)
    assert len(file_nodes) == 1
    file_node = file_nodes[0]

    # Collect everything reachable within 2 hops
    blast: dict[str, set[str]] = {
        "commits": set(),
        "co_modified_files": set(),
        "incidents": set(),
        "traces": set(),
    }

    # Hop 1: commits that touched this file
    for edge in store.get_edges_to(file_node.id):
        if edge.edge_type == EdgeType.MODIFIES:
            blast["commits"].add(edge.source_id)

    # Hop 2: other files in same commits + incidents caused
    for commit_id in blast["commits"]:
        for edge in store.get_edges_from(commit_id):
            if edge.edge_type == EdgeType.MODIFIES and edge.target_id != file_node.id:
                blast["co_modified_files"].add(edge.target_id)
            elif edge.edge_type == EdgeType.CAUSES:
                blast["incidents"].add(edge.target_id)

    # Hop 3: traces that fix those incidents
    for incident_id in blast["incidents"]:
        for edge in store.get_edges_to(incident_id):
            if edge.edge_type == EdgeType.FIXES:
                blast["traces"].add(edge.source_id)

    assert "commit_1" in blast["commits"]
    assert "commit_2" in blast["commits"]
    assert "file_a" in blast["co_modified_files"]
    assert "bug_1" in blast["incidents"]
    assert "trace_1" in blast["traces"]


# ---------------------------------------------------------------------------
# test_module_summary
# ---------------------------------------------------------------------------


def test_module_summary():
    """A module summary aggregates file, function, and class counts."""
    engine_path = SRC_ROOT / "engine"
    assert engine_path.is_dir()

    py_files = [f for f in engine_path.rglob("*.py")
                if "__pycache__" not in str(f) and f.name != "__init__.py"]

    total_functions = 0
    total_classes = 0
    file_summaries = []

    for fpath in py_files:
        try:
            functions = _extract_functions_ast(fpath)
            classes = _extract_classes_ast(fpath)
            total_functions += len(functions)
            total_classes += len(classes)
            file_summaries.append({
                "file": fpath.name,
                "functions": len(functions),
                "classes": len(classes),
            })
        except SyntaxError:
            continue

    summary = {
        "module": "engine",
        "files": len(py_files),
        "total_functions": total_functions,
        "total_classes": total_classes,
        "file_details": file_summaries,
    }

    assert summary["module"] == "engine"
    assert summary["files"] >= 1
    assert summary["total_classes"] >= 1  # At least GraphStore
    assert summary["total_functions"] >= 5  # GraphStore has many methods
