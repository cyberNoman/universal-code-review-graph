"""
Unit tests for CodeGraph engine.
These tests do NOT import tree-sitter at all — they test the graph
logic (BFS, search, review_changes, find_paths) directly using
hand-crafted Symbol and CallEdge objects.
CI always passes regardless of tree-sitter version.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from code_graph import CodeGraph, Symbol, CallEdge, make_symbol_key


# ── Helpers ───────────────────────────────────────────────────────────────────

def sym(file_path: str, name: str, sym_type: str = "function", parent: str = None) -> Symbol:
    key = make_symbol_key(file_path, name)
    return Symbol(
        name=key, short_name=name, symbol_type=sym_type,
        file_path=file_path, line_start=1, line_end=10,
        parent=parent,
    )


def edge(file_path: str, caller: str, callee: str) -> CallEdge:
    return CallEdge(
        caller=make_symbol_key(file_path, caller),
        callee=make_symbol_key(file_path, callee),
        call_type="direct_call", file_path=file_path, line=5,
    )


def build_chain_graph() -> CodeGraph:
    """main → run_pipeline → parse → tokenize"""
    g = CodeGraph()
    for name in ["main", "run_pipeline", "parse", "tokenize"]:
        g.add_symbol(sym("app.py", name))
    g.add_call(edge("app.py", "main", "run_pipeline"))
    g.add_call(edge("app.py", "run_pipeline", "parse"))
    g.add_call(edge("app.py", "parse", "tokenize"))
    return g


# ── Symbol namespacing ────────────────────────────────────────────────────────

class TestNamespacing:
    def test_two_files_same_name_no_collision(self):
        g = CodeGraph()
        g.add_symbol(sym("a.py", "parse"))
        g.add_symbol(sym("b.py", "parse"))
        assert len(g.symbols) == 2

    def test_key_format(self):
        assert make_symbol_key("src/parser.py", "MyClass.parse") == "src/parser.py::MyClass.parse"

    def test_short_name_index_populated(self):
        g = CodeGraph()
        g.add_symbol(sym("a.py", "parse"))
        assert "parse" in g._short_name_index

    def test_resolve_unambiguous(self):
        g = CodeGraph()
        g.add_symbol(sym("a.py", "unique_fn"))
        resolved = g.resolve_symbol("unique_fn")
        assert resolved == "a.py::unique_fn"

    def test_resolve_fully_qualified(self):
        g = CodeGraph()
        g.add_symbol(sym("a.py", "parse"))
        assert g.resolve_symbol("a.py::parse") == "a.py::parse"


# ── BFS traversal ─────────────────────────────────────────────────────────────

class TestBFS:
    def setup_method(self):
        self.g = build_chain_graph()

    def test_downstream_full_chain(self):
        down = self.g.get_downstream("main", max_depth=10)
        names = {self.g.symbols[k].short_name for k in down if k in self.g.symbols}
        assert names == {"run_pipeline", "parse", "tokenize"}

    def test_upstream_full_chain(self):
        up = self.g.get_upstream("tokenize", max_depth=10)
        names = {self.g.symbols[k].short_name for k in up if k in self.g.symbols}
        assert names == {"parse", "run_pipeline", "main"}

    def test_depth_1_downstream(self):
        down = self.g.get_downstream("main", max_depth=1)
        names = {self.g.symbols[k].short_name for k in down if k in self.g.symbols}
        assert "run_pipeline" in names
        assert "parse" not in names
        assert "tokenize" not in names

    def test_depth_2_downstream(self):
        down = self.g.get_downstream("main", max_depth=2)
        names = {self.g.symbols[k].short_name for k in down if k in self.g.symbols}
        assert "parse" in names
        assert "tokenize" not in names

    def test_no_self_in_result(self):
        down = self.g.get_downstream("main", max_depth=10)
        assert "app.py::main" not in down

    def test_unknown_symbol_returns_empty(self):
        assert self.g.get_downstream("nonexistent", max_depth=5) == []
        assert self.g.get_upstream("nonexistent", max_depth=5) == []


# ── review_changes ─────────────────────────────────────────────────────────────

class TestReviewChanges:
    def setup_method(self):
        self.g = build_chain_graph()

    def test_changed_file_always_in_result(self):
        result = self.g.review_changes(["app.py"])
        assert "app.py" in result["files"]

    def test_returns_impacted_symbols(self):
        result = self.g.review_changes(["app.py"], max_depth=5)
        assert result["total"] > 0

    def test_upstream_only(self):
        result = self.g.review_changes(
            ["app.py"], include_upstream=True, include_downstream=False, max_depth=5
        )
        assert len(result["upstream"]) > 0
        assert len(result["downstream"]) == 0

    def test_downstream_only(self):
        result = self.g.review_changes(
            ["app.py"], include_upstream=False, include_downstream=True, max_depth=5
        )
        assert len(result["downstream"]) > 0
        assert len(result["upstream"]) == 0

    def test_empty_file_returns_minimal(self):
        result = self.g.review_changes(["nonexistent.py"])
        assert result["total"] == 0
        assert "nonexistent.py" in result["files"]

    def test_multifile_change(self):
        g = CodeGraph()
        for f, n in [("a.py", "fn_a"), ("b.py", "fn_b"), ("c.py", "fn_c")]:
            g.add_symbol(sym(f, n))
        g.add_call(CallEdge(
            caller="a.py::fn_a", callee="b.py::fn_b",
            call_type="direct_call", file_path="a.py", line=1
        ))
        result = g.review_changes(["a.py", "b.py"])
        assert "a.py" in result["files"]
        assert "b.py" in result["files"]


# ── search_symbols ─────────────────────────────────────────────────────────────

class TestSearch:
    def setup_method(self):
        self.g = CodeGraph()
        for name in ["parse_source", "parse_json", "compile_ast", "ParserClass", "run_pipeline"]:
            self.g.add_symbol(sym("app.py", name))

    def test_prefix_wildcard(self):
        results = self.g.search_symbols("parse*")
        names = {r["short_name"] for r in results}
        assert "parse_source" in names
        assert "parse_json" in names
        assert "compile_ast" not in names

    def test_suffix_wildcard(self):
        results = self.g.search_symbols("*ast")
        names = {r["short_name"] for r in results}
        assert "compile_ast" in names

    def test_case_insensitive(self):
        results = self.g.search_symbols("parserclass")
        names = {r["short_name"] for r in results}
        assert "ParserClass" in names

    def test_exact_match(self):
        results = self.g.search_symbols("run_pipeline")
        assert len(results) == 1
        assert results[0]["short_name"] == "run_pipeline"

    def test_no_match_returns_empty(self):
        assert self.g.search_symbols("zzz_nothing") == []

    def test_type_filter(self):
        g = CodeGraph()
        g.add_symbol(sym("f.py", "MyClass", "class"))
        g.add_symbol(sym("f.py", "my_func", "function"))
        classes = g.search_symbols("*", symbol_type="class")
        funcs = g.search_symbols("*", symbol_type="function")
        assert all(r["symbol_type"] == "class" for r in classes)
        assert all(r["symbol_type"] == "function" for r in funcs)

    def test_limit(self):
        results = self.g.search_symbols("*", limit=2)
        assert len(results) <= 2


# ── find_paths ────────────────────────────────────────────────────────────────

class TestFindPaths:
    def setup_method(self):
        self.g = CodeGraph()
        for name in ["a", "b", "c", "d"]:
            self.g.add_symbol(sym("app.py", name))
        # a→b→c→d  and  a→c (shortcut)
        self.g.add_call(edge("app.py", "a", "b"))
        self.g.add_call(edge("app.py", "b", "c"))
        self.g.add_call(edge("app.py", "a", "c"))
        self.g.add_call(edge("app.py", "c", "d"))

    def test_finds_path(self):
        paths = self.g.find_paths("a", "d")
        assert len(paths) > 0

    def test_finds_multiple_paths(self):
        paths = self.g.find_paths("a", "d", max_paths=10)
        assert len(paths) >= 2

    def test_reverse_no_path(self):
        assert self.g.find_paths("d", "a") == []

    def test_same_node_no_path(self):
        assert self.g.find_paths("a", "a") == []

    def test_unknown_node(self):
        assert self.g.find_paths("a", "zzz") == []


# ── get_symbol_details ────────────────────────────────────────────────────────

class TestSymbolDetails:
    def setup_method(self):
        self.g = build_chain_graph()

    def test_known_symbol(self):
        d = self.g.get_symbol_details("parse")
        assert "symbol" in d
        assert d["symbol"]["short_name"] == "parse"
        assert "called_by" in d
        assert "calls" in d

    def test_unknown_symbol_returns_error(self):
        d = self.g.get_symbol_details("zzz_missing")
        assert "error" in d

    def test_callers_populated(self):
        d = self.g.get_symbol_details("parse")
        callers = d["called_by"]
        assert any("run_pipeline" in c for c in callers)

    def test_calls_populated(self):
        d = self.g.get_symbol_details("parse")
        calls = d["calls"]
        assert any("tokenize" in c for c in calls)


# ── get_stats ─────────────────────────────────────────────────────────────────

class TestStats:
    def test_counts_correct(self):
        g = build_chain_graph()
        stats = g.get_stats()
        assert stats["total_symbols"] == 4
        assert stats["total_edges"] == 3
        assert stats["files_indexed"] == 1

    def test_most_connected_present(self):
        g = build_chain_graph()
        stats = g.get_stats()
        assert isinstance(stats["most_connected"], list)

    def test_symbol_types_counted(self):
        g = CodeGraph()
        g.add_symbol(sym("f.py", "MyClass", "class"))
        g.add_symbol(sym("f.py", "my_func", "function"))
        g.add_symbol(sym("f.py", "my_method", "method"))
        stats = g.get_stats()
        assert stats["symbol_types"]["class"] == 1
        assert stats["symbol_types"]["function"] == 1
        assert stats["symbol_types"]["method"] == 1


# ── SQLite persistence ────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_and_reload(self, tmp_path):
        db = str(tmp_path / "test.db")
        g1 = CodeGraph(db_path=db)
        g1.add_symbol(sym("f.py", "hello"))
        g1.add_symbol(sym("f.py", "world"))
        g1.add_call(edge("f.py", "hello", "world"))
        g1.save_to_db()

        g2 = CodeGraph(db_path=db)
        loaded = g2.load_from_db()
        assert loaded is True
        assert len(g2.symbols) == 2
        assert g2.graph.number_of_edges() == 1

    def test_load_nonexistent_db_returns_false(self, tmp_path):
        g = CodeGraph(db_path=str(tmp_path / "missing.db"))
        assert g.load_from_db() is False

    def test_reload_preserves_short_name_index(self, tmp_path):
        db = str(tmp_path / "test.db")
        g1 = CodeGraph(db_path=db)
        g1.add_symbol(sym("f.py", "my_func"))
        g1.save_to_db()

        g2 = CodeGraph(db_path=db)
        g2.load_from_db()
        assert "my_func" in g2._short_name_index
