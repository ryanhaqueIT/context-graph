"""Multi-language tree-sitter parser for code intelligence.

Replaces the Python-only ``ast`` approach with tree-sitter grammars so the
same pipeline works for Python, JavaScript, and TypeScript.  The old
``code_intel.py`` / ``_ast_helpers.py`` remain untouched as a fallback.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import tree_sitter as ts
import tree_sitter_javascript as tsjs
import tree_sitter_python as tsp
import tree_sitter_typescript as tsts

from context_graph.ingest.models import ParseResult, Reference, Symbol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language configuration
# ---------------------------------------------------------------------------

# Maps file extensions to (language_name, tree-sitter Language object).
# To add a new language:
#   1. pip install tree-sitter-<lang>
#   2. Add the extension(s) and Language() call here.

LANGUAGE_CONFIG: dict[str, tuple[str, Any]] = {
    ".py": ("python", ts.Language(tsp.language())),
    ".js": ("javascript", ts.Language(tsjs.language())),
    ".ts": ("typescript", ts.Language(tsts.language_typescript())),
    ".tsx": ("typescript", ts.Language(tsts.language_tsx())),
}

# Directories that are never traversed during a recursive scan.
SKIP_DIRS: set[str] = {
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def _supported_extensions() -> frozenset[str]:
    return frozenset(LANGUAGE_CONFIG)


# ---------------------------------------------------------------------------
# Tree-sitter query helpers (per-language)
# ---------------------------------------------------------------------------

# Node types that define a *symbol* in each language family.
_PYTHON_SYMBOL_TYPES = {"function_definition", "class_definition"}

_JS_TS_SYMBOL_TYPES = {
    "function_declaration",
    "class_declaration",
    "method_definition",
    "interface_declaration",
    "type_alias_declaration",
}

# Node types that represent a *call*.
_CALL_TYPES = {"call", "call_expression", "new_expression"}

# Node types for imports.
_PYTHON_IMPORT_TYPES = {"import_statement", "import_from_statement"}
_JS_TS_IMPORT_TYPES = {"import_statement"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _relpath(path: Path, root: Path) -> str:
    """Return repo-relative path with forward slashes."""
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _node_name(node: ts.Node) -> str:
    """Extract the identifier/name child from a definition node."""
    # Different tree-sitter grammars use different identifier types:
    #   Python: identifier (class Foo, def bar)
    #   JS/TS:  identifier (class Foo, function bar)
    #           property_identifier (method_definition names like constructor, fetch)
    #           type_identifier (interface Config, type UserId)
    _NAME_TYPES = ("identifier", "property_identifier", "type_identifier")
    for child in node.children:
        if child.type in _NAME_TYPES:
            return child.text.decode("utf-8")
    # For arrow_function assigned to a variable, the name lives in the parent.
    return ""


def _node_source(node: ts.Node) -> str:
    """Return the full source text of a node, capped at 2000 chars."""
    raw = node.text.decode("utf-8", errors="replace")
    return raw[:2000]


def _enclosing_class(node: ts.Node) -> str | None:
    """Walk up the tree to find an enclosing class."""
    cursor = node.parent
    while cursor is not None:
        if cursor.type in ("class_definition", "class_declaration"):
            return _node_name(cursor)
        cursor = cursor.parent
    return None


def _enclosing_symbol_qname(node: ts.Node, language: str) -> str:
    """Return the qualified_name of the innermost enclosing function/method/class.

    Falls back to ``<module>`` when the reference lives at module scope.
    """
    symbol_types = (
        _PYTHON_SYMBOL_TYPES if language == "python" else _JS_TS_SYMBOL_TYPES
    )
    cursor = node.parent
    while cursor is not None:
        if cursor.type in symbol_types:
            name = _node_name(cursor)
            parent_class = _enclosing_class(cursor)
            return f"{parent_class}.{name}" if parent_class else name
        # Arrow / variable declarator containing an arrow function
        if cursor.type == "arrow_function":
            # Climb to variable_declarator to get the name
            vd = cursor.parent
            if vd is not None and vd.type == "variable_declarator":
                vname = _node_name(vd)
                if vname:
                    parent_class = _enclosing_class(vd)
                    return f"{parent_class}.{vname}" if parent_class else vname
        cursor = cursor.parent
    return "<module>"


def _extract_call_target(node: ts.Node) -> str:
    """Extract the function/method name being called.

    Examples:
      ``foo()``          -> ``foo``
      ``bar.baz()``      -> ``baz``
      ``new MyClass()``  -> ``MyClass``
    """
    if node.type == "new_expression":
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode("utf-8")
        return ""

    # call / call_expression: first child is the callee
    callee = node.children[0] if node.children else None
    if callee is None:
        return ""

    if callee.type == "identifier":
        return callee.text.decode("utf-8")

    if callee.type in ("attribute", "member_expression"):
        # last identifier child is the method name
        for child in reversed(callee.children):
            if child.type in ("identifier", "property_identifier"):
                return child.text.decode("utf-8")
    return ""


def _extract_import_names_python(node: ts.Node) -> list[str]:
    """Return imported module names from a Python import node."""
    names: list[str] = []
    if node.type == "import_statement":
        for child in node.children:
            if child.type == "dotted_name":
                names.append(child.text.decode("utf-8"))
    elif node.type == "import_from_statement":
        # ``from X import Y`` -> we record module X
        for child in node.children:
            if child.type == "dotted_name":
                names.append(child.text.decode("utf-8"))
                break  # first dotted_name is the module
    return names


def _extract_import_names_js_ts(node: ts.Node) -> list[str]:
    """Return imported module specifiers from a JS/TS import node."""
    names: list[str] = []
    for child in node.children:
        if child.type == "string" or child.type == "string_fragment":
            val = child.text.decode("utf-8").strip("'\"")
            names.append(val)
    # Also handle: import X from 'Y' -- get named imports
    for child in node.children:
        if child.type == "import_clause":
            for gc in child.children:
                if gc.type == "identifier":
                    names.append(gc.text.decode("utf-8"))
                elif gc.type == "named_imports":
                    for spec in gc.children:
                        if spec.type == "import_specifier":
                            for s in spec.children:
                                if s.type == "identifier":
                                    names.append(s.text.decode("utf-8"))
                                    break
    return names


# ---------------------------------------------------------------------------
# Arrow-function symbols extracted from variable declarations
# ---------------------------------------------------------------------------


def _extract_arrow_symbols(
    node: ts.Node,
    language: str,
    file_path: str,
) -> list[Symbol]:
    """Find ``const name = (...) => { ... }`` patterns and emit symbols."""
    symbols: list[Symbol] = []
    if node.type not in ("lexical_declaration", "variable_declaration"):
        return symbols
    for child in node.children:
        if child.type != "variable_declarator":
            continue
        vname = _node_name(child)
        if not vname:
            continue
        # Check if the initializer is an arrow_function
        for gc in child.children:
            if gc.type == "arrow_function":
                parent_class = _enclosing_class(child)
                symbols.append(
                    Symbol(
                        name=vname,
                        kind="arrow_function",
                        language=language,
                        file_path=file_path,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        source=_node_source(child),
                        parent=parent_class,
                    )
                )
    return symbols


# ---------------------------------------------------------------------------
# Core walker
# ---------------------------------------------------------------------------


def _walk_tree(
    root: ts.Node,
    language: str,
    file_path: str,
) -> ParseResult:
    """Depth-first walk of the tree-sitter CST, collecting symbols and refs."""
    symbols: list[Symbol] = []
    references: list[Reference] = []

    is_python = language == "python"
    symbol_types = _PYTHON_SYMBOL_TYPES if is_python else _JS_TS_SYMBOL_TYPES
    import_types = _PYTHON_IMPORT_TYPES if is_python else _JS_TS_IMPORT_TYPES

    stack: list[ts.Node] = [root]
    while stack:
        node = stack.pop()

        # --- Symbols ----------------------------------------------------------
        if node.type in symbol_types:
            name = _node_name(node)
            if name:
                parent_class = _enclosing_class(node)
                kind = _kind_for(node.type, parent_class)
                symbols.append(
                    Symbol(
                        name=name,
                        kind=kind,
                        language=language,
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        source=_node_source(node),
                        parent=parent_class,
                    )
                )

        # Arrow function symbols (JS/TS only)
        if not is_python and node.type in (
            "lexical_declaration",
            "variable_declaration",
        ):
            symbols.extend(_extract_arrow_symbols(node, language, file_path))

        # --- References: calls ------------------------------------------------
        if node.type in _CALL_TYPES:
            target = _extract_call_target(node)
            if target:
                source_qname = _enclosing_symbol_qname(node, language)
                references.append(
                    Reference(
                        source_symbol=source_qname,
                        target_name=target,
                        kind="calls",
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                    )
                )

        # --- References: imports ----------------------------------------------
        if node.type in import_types:
            if is_python:
                import_names = _extract_import_names_python(node)
            else:
                import_names = _extract_import_names_js_ts(node)
            source_qname = _enclosing_symbol_qname(node, language)
            for imp in import_names:
                references.append(
                    Reference(
                        source_symbol=source_qname,
                        target_name=imp,
                        kind="imports",
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                    )
                )

        # Push children in reverse so leftmost is processed first.
        for i in range(node.child_count - 1, -1, -1):
            stack.append(node.children[i])

    return ParseResult(
        symbols=symbols,
        references=references,
        language=language,
        file_path=file_path,
    )


def _kind_for(node_type: str, parent_class: str | None) -> str:
    """Map a tree-sitter node type to a Symbol.kind string."""
    mapping: dict[str, str] = {
        "function_definition": "method" if parent_class else "function",
        "class_definition": "class",
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
        "interface_declaration": "interface",
        "type_alias_declaration": "type_alias",
    }
    kind = mapping.get(node_type, node_type)
    # Python methods inside a class
    if node_type == "function_definition" and parent_class:
        kind = "method"
    return kind


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class MultiLanguageParser:
    """Parse source files into Symbols and References using tree-sitter."""

    def __init__(self) -> None:
        self._parsers: dict[str, ts.Parser] = {}
        for ext, (lang_name, ts_lang) in LANGUAGE_CONFIG.items():
            if ext not in self._parsers:
                self._parsers[ext] = ts.Parser(ts_lang)

    # -- Single file --------------------------------------------------------

    def parse_file(self, file_path: Path, repo_root: Path | None = None) -> ParseResult:
        """Parse a single file and return its symbols and references.

        Parameters
        ----------
        file_path:
            Absolute or relative path to the source file.
        repo_root:
            If provided, ``file_path`` is stored as a repo-relative string.
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext not in LANGUAGE_CONFIG:
            return ParseResult()

        lang_name, _ts_lang = LANGUAGE_CONFIG[ext]
        parser = self._parsers[ext]

        try:
            source_bytes = path.read_bytes()
        except OSError:
            logger.warning("Could not read file: %s", file_path)
            return ParseResult()

        tree = parser.parse(source_bytes)
        rel = _relpath(path, repo_root) if repo_root else str(path).replace("\\", "/")

        return _walk_tree(tree.root_node, lang_name, rel)

    # -- Directory ----------------------------------------------------------

    def parse_directory(self, dir_path: Path, repo_root: Path | None = None) -> list[ParseResult]:
        """Recursively parse all supported files under *dir_path*.

        Skips directories listed in ``SKIP_DIRS``.
        """
        root = repo_root or dir_path
        results: list[ParseResult] = []
        exts = _supported_extensions()

        for child in sorted(dir_path.rglob("*")):
            if not child.is_file():
                continue
            if child.suffix.lower() not in exts:
                continue
            if any(part in SKIP_DIRS for part in child.parts):
                continue
            result = self.parse_file(child, repo_root=root)
            if result.symbols or result.references:
                results.append(result)

        return results

    # -- Convenience --------------------------------------------------------

    @staticmethod
    def supported_extensions() -> frozenset[str]:
        """Return the set of file extensions this parser can handle."""
        return _supported_extensions()


# ---------------------------------------------------------------------------
# Symbol resolution
# ---------------------------------------------------------------------------


class SymbolResolver:
    """Resolve unqualified reference target names to concrete Symbols.

    Resolution strategy:
      1. Same-file match (strongest signal).
      2. Same-language match.
      3. Any-language match.
    """

    def __init__(self, symbols: list[Symbol]) -> None:
        # Index by name for fast lookup.
        self._by_name: dict[str, list[Symbol]] = {}
        for sym in symbols:
            self._by_name.setdefault(sym.name, []).append(sym)

    def resolve(self, ref: Reference) -> Symbol | None:
        """Return the best-matching Symbol for *ref*, or None."""
        candidates = self._by_name.get(ref.target_name)
        if not candidates:
            return None

        # 1. Same file
        same_file = [s for s in candidates if s.file_path == ref.file_path]
        if same_file:
            return same_file[0]

        # 2. Same language (infer from the reference's file extension)
        ref_ext = Path(ref.file_path).suffix.lower()
        ref_lang = LANGUAGE_CONFIG.get(ref_ext, (None,))[0]
        if ref_lang:
            same_lang = [s for s in candidates if s.language == ref_lang]
            if same_lang:
                return same_lang[0]

        # 3. Any match
        return candidates[0]

    def resolve_all(
        self,
        references: list[Reference],
    ) -> list[tuple[Reference, Symbol | None]]:
        """Resolve a batch of references and return (ref, symbol|None) pairs."""
        return [(ref, self.resolve(ref)) for ref in references]
