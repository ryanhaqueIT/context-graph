"""Code intelligence -- AST-based semantic analysis of a Python repo."""

from __future__ import annotations

import ast
import logging
from collections import deque
from pathlib import Path

from context_graph.engine.store import GraphStore
from context_graph.ingest._ast_helpers import (
    collect_py_files,
    count_ast_type,
    extract_args,
    extract_import_targets,
    module_summary,
    relpath,
    safe_parse,
)
from context_graph.models.nodes import Edge, EdgeType, Node, NodeType

logger = logging.getLogger(__name__)


class CodeIntelligence:
    """AST-powered code understanding for a Python repository."""

    def __init__(self, store: GraphStore, repo_root: Path) -> None:
        self._store = store
        self._repo_root = repo_root.resolve()
        self._py_files: list[Path] | None = None

    def scan_codebase(self) -> dict:
        """Walk all .py files and create CODE_UNIT nodes. Returns summary stats."""
        py_files = self._get_py_files()
        totals = {"lines": 0, "functions": 0, "classes": 0, "imports": 0}
        files_scanned = 0

        for path in py_files:
            rel = relpath(path, self._repo_root)
            source = self._read_source(path, rel)
            if source is None:
                continue

            tree = safe_parse(source, rel)
            line_count = self._line_count(source)
            func_count = count_ast_type(tree, ast.FunctionDef, ast.AsyncFunctionDef) if tree else 0
            class_count = count_ast_type(tree, ast.ClassDef) if tree else 0
            import_count = count_ast_type(tree, ast.Import, ast.ImportFrom) if tree else 0

            totals["lines"] += line_count
            totals["functions"] += func_count
            totals["classes"] += class_count
            totals["imports"] += import_count
            files_scanned += 1

            if self._store.find_nodes_by_property("file_path", rel, NodeType.CODE_UNIT):
                continue

            self._store.add_node(
                Node(
                    node_type=NodeType.CODE_UNIT,
                    name=rel,
                    properties={
                        "file_path": rel,
                        "language": "python",
                        "line_count": line_count,
                        "function_count": func_count,
                        "class_count": class_count,
                        "import_count": import_count,
                    },
                )
            )

        summary = {
            "files_scanned": files_scanned,
            "total_lines": totals["lines"],
            "total_functions": totals["functions"],
            "total_classes": totals["classes"],
            "total_imports": totals["imports"],
        }
        logger.info("Codebase scan complete", extra=summary)
        return summary

    def build_dependency_graph(self) -> int:
        """Create REFERENCES edges between CODE_UNIT nodes. Returns edge count."""
        edge_count = 0
        for path in self._get_py_files():
            rel = relpath(path, self._repo_root)
            source = self._read_source(path, rel)
            if source is None:
                continue
            tree = safe_parse(source, rel)
            if tree is None:
                continue

            src_node = self._node_for(rel)
            if src_node is None:
                continue

            imports = extract_import_targets(tree, path, self._repo_root)
            for target_rel in imports["internal"]:
                tgt_node = self._node_for(target_rel)
                if tgt_node is None or self._edge_exists(src_node.id, tgt_node.id):
                    continue
                self._store.add_edge(
                    Edge(
                        edge_type=EdgeType.REFERENCES,
                        source_id=src_node.id,
                        target_id=tgt_node.id,
                        properties={"relationship": "imports"},
                    )
                )
                edge_count += 1

        logger.info("Dependency graph built", extra={"edges_created": edge_count})
        return edge_count

    def extract_functions(self, file_path: str) -> list[dict]:
        """Extract all function/method signatures from *file_path*."""
        tree = self._parse_file(file_path)
        if tree is None:
            return []

        results: list[dict] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            parent_class = self._find_parent_class(tree, node)
            results.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": extract_args(node),
                    "return_type": ast.unparse(node.returns) if node.returns else None,
                    "decorators": [ast.unparse(d) for d in node.decorator_list],
                    "docstring": ast.get_docstring(node),
                    "is_method": parent_class is not None,
                    "parent_class": parent_class,
                }
            )
        return results

    def extract_classes(self, file_path: str) -> list[dict]:
        """Extract all class definitions from *file_path*."""
        tree = self._parse_file(file_path)
        if tree is None:
            return []

        results: list[dict] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods = [
                n.name
                for n in ast.iter_child_nodes(node)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
            results.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "bases": [ast.unparse(b) for b in node.bases],
                    "methods": methods,
                    "docstring": ast.get_docstring(node),
                }
            )
        return results

    def get_file_dependencies(self, file_path: str) -> list[str]:
        """Return internal file paths that *file_path* imports."""
        abs_path = self._repo_root / file_path
        source = self._read_source(abs_path, file_path)
        if source is None:
            return []
        tree = safe_parse(source, file_path)
        if tree is None:
            return []
        imports = extract_import_targets(tree, abs_path, self._repo_root)
        return sorted(set(imports["internal"]))

    def get_file_dependents(self, file_path: str) -> list[str]:
        """Return internal file paths that import *file_path*."""
        node = self._node_for(file_path)
        if node is None:
            return []
        dependents: list[str] = []
        for edge in self._store.get_edges_to(node.id):
            if edge.edge_type != EdgeType.REFERENCES:
                continue
            src = self._store.get_node(edge.source_id)
            if src and src.node_type == NodeType.CODE_UNIT:
                fp = str(src.properties.get("file_path", ""))
                if fp:
                    dependents.append(fp)
        return sorted(set(dependents))

    def compute_blast_radius(self, file_path: str) -> dict:
        """BFS through dependents to find all transitively affected files."""
        direct = self.get_file_dependents(file_path)
        visited: set[str] = {file_path}
        transitive: list[str] = []
        queue: deque[str] = deque(direct)

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current not in direct:
                transitive.append(current)
            for dep in self.get_file_dependents(current):
                if dep not in visited:
                    queue.append(dep)

        return {
            "direct_dependents": sorted(direct),
            "transitive_dependents": sorted(transitive),
            "total_affected": len(direct) + len(transitive),
        }

    def find_dead_code(self) -> list[str]:
        """Files that nothing imports (potential dead code)."""
        dead: list[str] = []
        for node in self._store.get_nodes_by_type(NodeType.CODE_UNIT):
            fp = str(node.properties.get("file_path", ""))
            if not fp.endswith(".py"):
                continue
            if Path(fp).name in ("__init__.py", "__main__.py"):
                continue
            has_importer = any(
                e.edge_type == EdgeType.REFERENCES for e in self._store.get_edges_to(node.id)
            )
            if not has_importer:
                dead.append(fp)
        return sorted(dead)

    def get_module_summary(self, module_path: str) -> dict:
        """Aggregate summary of a module directory."""
        return module_summary(module_path, self._repo_root)

    def _get_py_files(self) -> list[Path]:
        if self._py_files is None:
            self._py_files = collect_py_files(self._repo_root)
        return self._py_files

    @staticmethod
    def _read_source(path: Path, label: str) -> str | None:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.warning("Could not read file", extra={"path": label})
            return None

    @staticmethod
    def _line_count(source: str) -> int:
        return source.count("\n") + (1 if source and not source.endswith("\n") else 0)

    def _parse_file(self, file_path: str) -> ast.Module | None:
        source = self._read_source(self._repo_root / file_path, file_path)
        return safe_parse(source, file_path) if source else None

    def _node_for(self, rel_path: str) -> Node | None:
        hits = self._store.find_nodes_by_property(
            "file_path",
            rel_path,
            NodeType.CODE_UNIT,
        )
        return hits[0] if hits else None

    def _edge_exists(self, src_id: str, tgt_id: str) -> bool:
        return any(
            e.target_id == tgt_id and e.edge_type == EdgeType.REFERENCES
            for e in self._store.get_edges_from(src_id)
        )

    @staticmethod
    def _find_parent_class(
        tree: ast.Module,
        target: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str | None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.iter_child_nodes(node):
                    if child is target:
                        return node.name
        return None
