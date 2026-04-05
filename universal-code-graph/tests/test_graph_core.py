"""Unit tests for the core CodeGraph engine."""

import pytest
from code_graph import CodeGraph, Symbol, CallEdge, make_symbol_key


def make_sym(file_path, name, sym_type="function", parent=None):
    key = make_symbol_key(file_path, name)
    return Symbol(
        name=key, short_name=name, symbol_type=sym_type,
        file_path=file_path, line_start=1, line_end=10,
        parent=parent,
    )


def make_edge(file_path, caller_short, callee_short):
    return CallEdge(
        caller=make_symbol_key(file_path, caller_short),
        callee=make_symbol_key(file_path, callee_short),
        call_type="direct_call",
        file_path=file_path,
        line=5,
    )


class TestSymbolNamespacing:
    def test_same_name_different_files_no_collision(self):
        g = CodeGraph()
        s1 = make_sym("a.py", "parse")
        s2 = make_sym("b.py", "parse")
        g.add_symbol(s1)
        g.add_symbol(s2)
        assert len(g.symbols) == 2

    def test_symbol_key_format(self):
        key = make_symbol_key("src/parser.py", "MyClass.parse")
        assert key == "src/parser.py::MyClass.parse"


class TestUpstreamDownstream:
    def setup_method(self):
        self.g = CodeGraph()
        for name in ["main", "run_pipeline", "parse", "tokenize"]:
            self.g.add_symbol(make_sym("app.py", name))
        # main → run_pipeline → parse → tokenize
        self.g.add_call(make_edge("app.py", "main", "run_pipeline"))
        self.g.add_call(make_edge("app.py", "run_pipeline", "parse"))
        self.g.add_call(make_edge("app.py", "parse", "tokenize"))

    def test_downstream(self):
        down = self.g.get_downstream("main", max_depth=5)
        short_names = [self.g.symbols[k].short_name for k in down if k in self.g.symbols]
        assert "run_pipeline" in short_names
        assert "parse" in short_names
        assert "tokenize" in short_names

    def test_upstream(self):
        up = self.g.get_upstream("tokenize", max_depth=5)
        short_names = [self.g.symbols[k].short_name for k in up if k in self.g.symbols]
        assert "parse" in short_names
        assert "run_pipeline" in short_names
        assert "main" in short_names

    def test_depth_limit(self):
        down = self.g.get_downstream("main", max_depth=1)
        short_names = [self.g.symbols[k].short_name for k in down if k in self.g.symbols]
        assert "run_pipeline" in short_names
        assert "tokenize" not in short_names


class TestReviewChanges:
    def setup_method(self):
        self.g = CodeGraph()
        for name in ["main", "api_handler", "parse", "tokenize", "utils"]:
            self.g.add_symbol(make_sym("app.py", name))
        self.g.add_call(make_edge("app.py", "main", "api_handler"))
        self.g.add_call(make_edge("app.py", "api_handler", "parse"))
        self.g.add_call(make_edge("app.py", "parse", "tokenize"))

    def test_review_returns_blast_radius(self):
        result = self.g.review_changes(
            changed_files=["app.py"],
            include_upstream=True,
            include_downstream=True,
            max_depth=3,
        )
        assert result["total"] > 0
        assert "app.py" in result["files"]

    def test_review_changed_files_always_in_result(self):
        result = self.g.review_changes(changed_files=["app.py"])
        assert "app.py" in result["files"]


class TestSearchSymbols:
    def setup_method(self):
        self.g = CodeGraph()
        for name in ["parse_source", "parse_json", "compile_ast", "ParserClass"]:
            self.g.add_symbol(make_sym("app.py", name))

    def test_wildcard_prefix(self):
        results = self.g.search_symbols("parse*")
        names = [r["short_name"] for r in results]
        assert "parse_source" in names
        assert "parse_json" in names
        assert "compile_ast" not in names

    def test_wildcard_suffix(self):
        results = self.g.search_symbols("*ast")
        names = [r["short_name"] for r in results]
        assert "compile_ast" in names

    def test_case_insensitive(self):
        results = self.g.search_symbols("parser*")
        names = [r["short_name"] for r in results]
        assert "ParserClass" in names


class TestFindPaths:
    def setup_method(self):
        self.g = CodeGraph()
        for name in ["a", "b", "c", "d"]:
            self.g.add_symbol(make_sym("app.py", name))
        self.g.add_call(make_edge("app.py", "a", "b"))
        self.g.add_call(make_edge("app.py", "b", "c"))
        self.g.add_call(make_edge("app.py", "a", "c"))  # direct shortcut
        self.g.add_call(make_edge("app.py", "c", "d"))

    def test_finds_path(self):
        paths = self.g.find_paths("a", "d")
        assert len(paths) > 0

    def test_no_path_returns_empty(self):
        paths = self.g.find_paths("d", "a")  # reverse direction
        assert paths == []
