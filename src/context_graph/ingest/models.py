"""Data models for multi-language code intelligence.

Symbol and Reference are the atomic units produced by tree-sitter parsing.
They are deliberately decoupled from the graph store's Node/Edge types so
the parser layer stays independent and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Symbol:
    """A named code entity extracted from source (function, class, method, etc.)."""

    name: str
    kind: str  # "function", "class", "method", "interface", "type_alias", "arrow_function"
    language: str  # "python", "javascript", "typescript"
    file_path: str  # repo-relative, forward slashes
    start_line: int
    end_line: int
    source: str = ""  # raw source text of the symbol
    parent: str | None = None  # enclosing class name (for methods)

    @property
    def qualified_name(self) -> str:
        """Return ``Parent.name`` for methods, plain ``name`` otherwise."""
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name


@dataclass(frozen=True)
class Reference:
    """A reference from one symbol to another name (call, import, etc.)."""

    source_symbol: str  # qualified_name of the symbol making the reference
    target_name: str  # unresolved name being referenced
    kind: str  # "calls", "imports"
    file_path: str  # repo-relative path where the reference occurs
    line: int


@dataclass
class ParseResult:
    """Aggregated output from parsing a single file."""

    symbols: list[Symbol] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    language: str = ""
    file_path: str = ""
