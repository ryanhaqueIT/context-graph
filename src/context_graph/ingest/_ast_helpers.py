"""AST parsing and import resolution helpers for code_intel.

Private module -- not part of the public API.  Extracted to keep
individual files under the 300-line limit.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Directories to skip when walking the codebase.
SKIP_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".git",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}


def safe_parse(source: str, label: str) -> ast.Module | None:
    """Parse source code; return None on SyntaxError."""
    try:
        return ast.parse(source, filename=label)
    except SyntaxError:
        logger.debug("Syntax error in file", extra={"path": label})
        return None


def count_ast_type(tree: ast.Module, *types: type) -> int:
    """Count AST nodes matching any of *types*."""
    return sum(1 for node in ast.walk(tree) if isinstance(node, types))


def extract_args(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return a list of argument names with optional annotations."""
    args: list[str] = []
    for arg in func.args.args:
        annotation = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
        args.append(f"{arg.arg}{annotation}")
    return args


def relpath(path: Path, repo_root: Path) -> str:
    """Return the path relative to repo root, with forward slashes."""
    try:
        return str(path.resolve().relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        return str(path)


def collect_py_files(repo_root: Path) -> list[Path]:
    """Walk the repo and return all .py file paths, sorted."""
    results: list[Path] = []
    for child in sorted(repo_root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in child.parts):
            continue
        results.append(child)
    logger.debug("Collected Python files", extra={"count": len(results)})
    return results


# ------------------------------------------------------------------
# Import resolution
# ------------------------------------------------------------------


def extract_import_targets(
    tree: ast.Module,
    source_path: Path,
    repo_root: Path,
) -> dict[str, list[str]]:
    """Classify every import in *tree* as internal or external.

    Returns ``{"internal": [...], "external": [...]}``.
    """
    internal: list[str] = []
    external: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = resolve_absolute_import(alias.name, repo_root)
                if resolved:
                    internal.append(resolved)
                else:
                    external.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0

            if level > 0:
                resolved = resolve_relative_import(
                    module,
                    level,
                    source_path,
                    repo_root,
                )
            else:
                resolved = resolve_absolute_import(module, repo_root)

            if resolved:
                internal.append(resolved)
            else:
                external.append(module if module else "<unknown>")

    return {"internal": internal, "external": external}


def resolve_absolute_import(module: str, repo_root: Path) -> str | None:
    """Map ``context_graph.engine.store`` to ``src/context_graph/engine/store.py``.

    Returns the repo-relative path string if the file exists, else None.
    """
    parts = module.split(".")
    # Try as a direct file, then under src/, then as a package.
    for prefix in [repo_root, repo_root / "src"]:
        candidate = prefix / Path(*parts).with_suffix(".py")
        if candidate.exists():
            return relpath(candidate, repo_root)
        pkg_init = prefix / Path(*parts) / "__init__.py"
        if pkg_init.exists():
            return relpath(pkg_init, repo_root)
    return None


def resolve_relative_import(
    module: str,
    level: int,
    source_path: Path,
    repo_root: Path,
) -> str | None:
    """Resolve ``from .models import Node`` relative to *source_path*."""
    base = source_path.resolve().parent
    for _ in range(level - 1):
        base = base.parent

    if module:
        parts = module.split(".")
        candidate = base / Path(*parts).with_suffix(".py")
        if candidate.exists():
            return relpath(candidate, repo_root)
        pkg_init = base / Path(*parts) / "__init__.py"
        if pkg_init.exists():
            return relpath(pkg_init, repo_root)
    else:
        init = base / "__init__.py"
        if init.exists():
            return relpath(init, repo_root)
    return None


# ------------------------------------------------------------------
# Module summary
# ------------------------------------------------------------------


def module_summary(module_path: str, repo_root: Path) -> dict:
    """Aggregate summary of a module directory (relative to repo root)."""
    abs_dir = repo_root / module_path
    if not abs_dir.is_dir():
        return {"error": f"Not a directory: {module_path}"}

    files: list[str] = []
    total_lines = 0
    functions: list[str] = []
    classes: list[str] = []
    ext_deps: set[str] = set()
    int_deps: set[str] = set()

    for py in sorted(abs_dir.rglob("*.py")):
        if any(part in SKIP_DIRS for part in py.parts):
            continue
        rel = relpath(py, repo_root)
        files.append(rel)
        try:
            source = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total_lines += source.count("\n") + (1 if source and not source.endswith("\n") else 0)
        tree = safe_parse(source, rel)
        if tree is None:
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(f"{rel}::{n.name}")
            elif isinstance(n, ast.ClassDef):
                classes.append(f"{rel}::{n.name}")
        imports = extract_import_targets(tree, py, repo_root)
        ext_deps.update(imports["external"])
        int_deps.update(imports["internal"])

    return {
        "files": files,
        "total_lines": total_lines,
        "functions": functions,
        "classes": classes,
        "external_deps": sorted(ext_deps),
        "internal_deps": sorted(int_deps),
    }
