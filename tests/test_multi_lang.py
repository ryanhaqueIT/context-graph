"""Tests for multi-language tree-sitter parser (ingest/multi_lang_parser.py).

Covers:
  - Python file parsing (functions, classes, methods, calls, imports)
  - JavaScript file parsing (functions, classes, arrow functions, calls)
  - TypeScript file parsing (interfaces, type aliases, generics)
  - Symbol resolution (same-file preference, same-language, cross-language)
  - Directory scanning with mixed languages
  - Graceful handling of unsupported file extensions
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from context_graph.ingest.models import ParseResult, Reference, Symbol
from context_graph.ingest.multi_lang_parser import (
    LANGUAGE_CONFIG,
    MultiLanguageParser,
    SymbolResolver,
)


@pytest.fixture()
def parser():
    return MultiLanguageParser()


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        yield Path(d)


# ---------------------------------------------------------------------------
# Helper to write a temp file and parse it
# ---------------------------------------------------------------------------


def _write_and_parse(
    parser: MultiLanguageParser,
    tmp_dir: Path,
    filename: str,
    content: str,
) -> ParseResult:
    fpath = tmp_dir / filename
    fpath.write_text(content, encoding="utf-8")
    return parser.parse_file(fpath, repo_root=tmp_dir)


# ===================================================================
# Python parsing
# ===================================================================


class TestPythonParsing:
    def test_extract_functions(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "example.py", """\
def top_level():
    pass

async def async_top():
    pass
""")
        names = {s.name for s in result.symbols}
        assert "top_level" in names
        assert "async_top" in names
        kinds = {s.name: s.kind for s in result.symbols}
        assert kinds["top_level"] == "function"
        assert kinds["async_top"] == "function"

    def test_extract_classes_and_methods(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "classes.py", """\
class Animal:
    def speak(self):
        pass

    def move(self):
        pass

class Dog(Animal):
    def speak(self):
        return "woof"
""")
        names = {s.name for s in result.symbols}
        assert "Animal" in names
        assert "Dog" in names
        assert "speak" in names
        assert "move" in names

        methods = [s for s in result.symbols if s.kind == "method"]
        assert len(methods) >= 3
        for m in methods:
            assert m.parent in ("Animal", "Dog")

    def test_extract_calls(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "caller.py", """\
def caller():
    helper()
    obj.method()
""")
        call_refs = [r for r in result.references if r.kind == "calls"]
        call_targets = {r.target_name for r in call_refs}
        assert "helper" in call_targets
        assert "method" in call_targets

    def test_extract_imports(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "imports.py", """\
import os
from pathlib import Path
from . import sibling
""")
        import_refs = [r for r in result.references if r.kind == "imports"]
        import_names = {r.target_name for r in import_refs}
        assert "os" in import_names
        assert "pathlib" in import_names

    def test_language_is_python(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "lang.py", "def f(): pass")
        assert result.language == "python"
        assert all(s.language == "python" for s in result.symbols)

    def test_line_numbers(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "lines.py", """\
# line 1
def first():  # line 2
    pass       # line 3

def second():  # line 5
    pass
""")
        by_name = {s.name: s for s in result.symbols}
        assert by_name["first"].start_line == 2
        assert by_name["second"].start_line == 5


# ===================================================================
# JavaScript parsing
# ===================================================================


class TestJavaScriptParsing:
    def test_extract_functions(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "example.js", """\
function greet(name) {
    return "Hello " + name;
}

function helper() {}
""")
        names = {s.name for s in result.symbols}
        assert "greet" in names
        assert "helper" in names
        assert all(s.language == "javascript" for s in result.symbols)

    def test_extract_classes(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "cls.js", """\
class MyService {
    constructor(db) { this.db = db; }
    fetch() { return this.db.query(); }
}
""")
        names = {s.name for s in result.symbols}
        assert "MyService" in names
        assert "constructor" in names
        assert "fetch" in names

        cls = next(s for s in result.symbols if s.name == "MyService")
        assert cls.kind == "class"

        methods = [s for s in result.symbols if s.kind == "method"]
        assert all(m.parent == "MyService" for m in methods)

    def test_extract_arrow_functions(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "arrows.js", """\
const add = (a, b) => a + b;
const multiply = (a, b) => {
    return a * b;
};
""")
        names = {s.name for s in result.symbols}
        assert "add" in names
        assert "multiply" in names

        for s in result.symbols:
            if s.name in ("add", "multiply"):
                assert s.kind == "arrow_function"

    def test_extract_calls(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "calls.js", """\
function main() {
    console.log("hi");
    fetch("/api");
    const x = new MyClass();
}
""")
        call_targets = {r.target_name for r in result.references if r.kind == "calls"}
        assert "log" in call_targets
        assert "fetch" in call_targets
        assert "MyClass" in call_targets


# ===================================================================
# TypeScript parsing
# ===================================================================


class TestTypeScriptParsing:
    def test_extract_functions_and_interfaces(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "service.ts", """\
interface Config {
    port: number;
    host: string;
}

function createServer(cfg: Config): void {
    console.log(cfg.port);
}

type UserId = string;
""")
        names = {s.name for s in result.symbols}
        assert "Config" in names
        assert "createServer" in names
        assert "UserId" in names

        kinds = {s.name: s.kind for s in result.symbols}
        assert kinds["Config"] == "interface"
        assert kinds["createServer"] == "function"
        assert kinds["UserId"] == "type_alias"
        assert all(s.language == "typescript" for s in result.symbols)

    def test_tsx_extension(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "component.tsx", """\
function App() {
    return null;
}
""")
        assert result.language == "typescript"
        names = {s.name for s in result.symbols}
        assert "App" in names

    def test_extract_calls_typescript(self, parser, tmp_dir):
        result = _write_and_parse(parser, tmp_dir, "app.ts", """\
function boot() {
    const server = createServer({ port: 3000 });
    server.listen();
}
""")
        call_targets = {r.target_name for r in result.references if r.kind == "calls"}
        assert "createServer" in call_targets
        assert "listen" in call_targets


# ===================================================================
# Symbol resolution
# ===================================================================


class TestSymbolResolution:
    def test_same_file_preference(self):
        sym_a = Symbol(
            name="helper", kind="function", language="python",
            file_path="a.py", start_line=1, end_line=3,
        )
        sym_b = Symbol(
            name="helper", kind="function", language="python",
            file_path="b.py", start_line=1, end_line=3,
        )
        resolver = SymbolResolver([sym_a, sym_b])

        ref = Reference(
            source_symbol="caller",
            target_name="helper",
            kind="calls",
            file_path="a.py",
            line=10,
        )
        resolved = resolver.resolve(ref)
        assert resolved is not None
        assert resolved.file_path == "a.py"

    def test_same_language_preference(self):
        sym_py = Symbol(
            name="Config", kind="class", language="python",
            file_path="config.py", start_line=1, end_line=5,
        )
        sym_ts = Symbol(
            name="Config", kind="interface", language="typescript",
            file_path="config.ts", start_line=1, end_line=5,
        )
        resolver = SymbolResolver([sym_py, sym_ts])

        ref = Reference(
            source_symbol="app",
            target_name="Config",
            kind="calls",
            file_path="main.ts",
            line=1,
        )
        resolved = resolver.resolve(ref)
        assert resolved is not None
        assert resolved.language == "typescript"

    def test_unresolvable_returns_none(self):
        sym = Symbol(
            name="existing", kind="function", language="python",
            file_path="a.py", start_line=1, end_line=3,
        )
        resolver = SymbolResolver([sym])
        ref = Reference(
            source_symbol="caller",
            target_name="nonexistent",
            kind="calls",
            file_path="a.py",
            line=10,
        )
        assert resolver.resolve(ref) is None

    def test_resolve_all_batch(self):
        sym = Symbol(
            name="target", kind="function", language="python",
            file_path="a.py", start_line=1, end_line=3,
        )
        resolver = SymbolResolver([sym])
        refs = [
            Reference("caller", "target", "calls", "a.py", 10),
            Reference("caller", "missing", "calls", "a.py", 11),
        ]
        pairs = resolver.resolve_all(refs)
        assert len(pairs) == 2
        assert pairs[0][1] is not None
        assert pairs[0][1].name == "target"
        assert pairs[1][1] is None


# ===================================================================
# Directory scanning (mixed languages)
# ===================================================================


class TestDirectoryScanning:
    def test_mixed_language_directory(self, parser, tmp_dir):
        (tmp_dir / "app.py").write_text("def main(): pass", encoding="utf-8")
        (tmp_dir / "utils.js").write_text("function helper() {}", encoding="utf-8")
        (tmp_dir / "types.ts").write_text("interface Foo { x: number; }", encoding="utf-8")

        results = parser.parse_directory(tmp_dir, repo_root=tmp_dir)
        languages = {r.language for r in results}
        assert "python" in languages
        assert "javascript" in languages
        assert "typescript" in languages

    def test_skips_node_modules(self, parser, tmp_dir):
        nm = tmp_dir / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("function x() {}", encoding="utf-8")
        (tmp_dir / "app.js").write_text("function main() {}", encoding="utf-8")

        results = parser.parse_directory(tmp_dir, repo_root=tmp_dir)
        all_files = {r.file_path for r in results}
        assert not any("node_modules" in f for f in all_files)
        assert any("app.js" in f for f in all_files)

    def test_skips_pycache(self, parser, tmp_dir):
        pc = tmp_dir / "__pycache__"
        pc.mkdir()
        (pc / "cached.py").write_text("def x(): pass", encoding="utf-8")
        (tmp_dir / "real.py").write_text("def y(): pass", encoding="utf-8")

        results = parser.parse_directory(tmp_dir, repo_root=tmp_dir)
        all_files = {r.file_path for r in results}
        assert not any("__pycache__" in f for f in all_files)

    def test_counts_by_language(self, parser, tmp_dir):
        (tmp_dir / "a.py").write_text("class A: pass", encoding="utf-8")
        (tmp_dir / "b.py").write_text("def b(): pass", encoding="utf-8")
        (tmp_dir / "c.js").write_text("function c() {}", encoding="utf-8")

        results = parser.parse_directory(tmp_dir, repo_root=tmp_dir)
        lang_count = {}
        for r in results:
            lang_count[r.language] = lang_count.get(r.language, 0) + 1
        assert lang_count.get("python", 0) == 2
        assert lang_count.get("javascript", 0) == 1


# ===================================================================
# Unsupported extensions
# ===================================================================


class TestUnsupportedExtensions:
    def test_unsupported_extension_returns_empty(self, parser, tmp_dir):
        (tmp_dir / "data.json").write_text('{"key": "value"}', encoding="utf-8")
        result = parser.parse_file(tmp_dir / "data.json", repo_root=tmp_dir)
        assert result.symbols == []
        assert result.references == []

    def test_supported_extensions_method(self, parser):
        exts = parser.supported_extensions()
        assert ".py" in exts
        assert ".js" in exts
        assert ".ts" in exts
        assert ".tsx" in exts
        assert ".json" not in exts
        assert ".md" not in exts

    def test_missing_file_returns_empty(self, parser, tmp_dir):
        result = parser.parse_file(tmp_dir / "does_not_exist.py", repo_root=tmp_dir)
        assert result.symbols == []
        assert result.references == []


# ===================================================================
# Model dataclass tests
# ===================================================================


class TestModels:
    def test_symbol_qualified_name_plain(self):
        s = Symbol("foo", "function", "python", "a.py", 1, 3)
        assert s.qualified_name == "foo"

    def test_symbol_qualified_name_with_parent(self):
        s = Symbol("bar", "method", "python", "a.py", 1, 3, parent="MyClass")
        assert s.qualified_name == "MyClass.bar"

    def test_symbol_is_frozen(self):
        s = Symbol("foo", "function", "python", "a.py", 1, 3)
        with pytest.raises(AttributeError):
            s.name = "changed"  # type: ignore[misc]

    def test_reference_is_frozen(self):
        r = Reference("caller", "target", "calls", "a.py", 10)
        with pytest.raises(AttributeError):
            r.kind = "imports"  # type: ignore[misc]

    def test_parse_result_defaults(self):
        pr = ParseResult()
        assert pr.symbols == []
        assert pr.references == []
        assert pr.language == ""
        assert pr.file_path == ""
