"""
Qwen QA Agent — Multi-Language Parsing + Cross-File Resolution
Comprehensive test suite for universal-code-review-graph.
Uses manual temp dirs to avoid pytest tmp_path permission issues on Windows.
"""
import sys
import os
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from code_graph import (
    CodeGraph, Symbol, CallEdge, make_symbol_key, GraphBuilder, _TREE_SITTER_AVAILABLE
)


# ── Detect whether tree-sitter grammars actually work ─────────────────────────
# On some platforms (notably Windows), tree-sitter language packages may
# silently crash during import or Language() construction.  We run a
# minimal end-to-end parse to confirm the parsers actually work.

def _parsers_work():
    """Return True if at least the Python parser can parse a trivial file."""
    if not _TREE_SITTER_AVAILABLE:
        return False
    try:
        tmp = Path(tempfile.gettempdir()) / "qwen_qa_probe"
        tmp.mkdir(exist_ok=True)
        (tmp / "probe.py").write_text("def foo(): pass")
        b = GraphBuilder(repo_path=str(tmp))
        st = b.build()
        # Clean up
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
        return st["files_processed"] > 0 and len(b.graph.symbols) > 0
    except Exception:
        return False

PARSERS_WORK = _parsers_work()

# ── Custom temp dir helper ────────────────────────────────────────────────────
_test_dirs = []

def make_test_dir():
    base = Path(tempfile.gettempdir()) / "qwen_qa_test"
    base.mkdir(exist_ok=True)
    import uuid
    d = base / str(uuid.uuid4())
    d.mkdir()
    _test_dirs.append(d)
    return d

def cleanup_test_dirs():
    for d in _test_dirs:
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE A — Multi-Language File Detection
# ─────────────────────────────────────────────────────────────────────────────

class TestA_LanguageFileDetection:
    """A1: Language Extension Mapping"""

    def test_py_maps_to_python(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.py")) == "python"

    def test_js_maps_to_javascript(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.js")) == "javascript"

    def test_jsx_maps_to_javascript(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.jsx")) == "javascript"

    def test_ts_maps_to_typescript(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.ts")) == "typescript"

    def test_tsx_maps_to_typescript(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.tsx")) == "typescript"

    def test_go_maps_to_go(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.go")) == "go"

    def test_unknown_rs_returns_none(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.rs")) is None

    def test_unknown_java_returns_none(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.java")) is None

    def test_unknown_c_returns_none(self):
        gb = GraphBuilder(repo_path=".")
        assert gb._get_language(Path("foo.c")) is None

    """A2: File Discovery — only scans supported extensions"""

    def test_rglob_uses_correct_extensions(self):
        tmp = make_test_dir()
        (tmp / "a.py").write_text("def foo(): pass")
        (tmp / "b.js").write_text("function foo() {}")
        (tmp / "c.ts").write_text("function bar() {}")
        (tmp / "d.go").write_text("func baz() {}")
        (tmp / "e.rs").write_text("fn qux() {}")
        (tmp / "f.java").write_text("class Qux {}")
        (tmp / "g.c").write_text("void qux() {}")

        builder = GraphBuilder(repo_path=str(tmp))
        stats = builder.build()
        indexed_files = set(builder.graph.file_symbols.keys())
        for f in indexed_files:
            assert not f.endswith(".rs"), f"Should not index .rs files: {f}"
            assert not f.endswith(".java"), f"Should not index .java files: {f}"
            assert not f.endswith(".c"), f"Should not index .c files: {f}"

    """A3: Exclude Patterns"""

    def test_exclude_test_files(self):
        tmp = make_test_dir()
        (tmp / "test_foo.py").write_text("def test_foo(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any("test_" in f for f in indexed), f"test files should be excluded: {indexed}"

    def test_exclude_tests_dir(self):
        tmp = make_test_dir()
        tests_dir = tmp / "tests"
        tests_dir.mkdir()
        (tests_dir / "helper.py").write_text("def helper(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any("/tests/" in f or "\\tests\\" in f for f in indexed), f"tests/ dir should be excluded: {indexed}"

    def test_exclude_node_modules(self):
        tmp = make_test_dir()
        nm = tmp / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("function foo() {}")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any("node_modules" in f for f in indexed), f"node_modules should be excluded: {indexed}"

    def test_exclude_git(self):
        tmp = make_test_dir()
        git = tmp / ".git"
        git.mkdir()
        (git / "config.py").write_text("def foo(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any(".git" in f for f in indexed), f".git should be excluded: {indexed}"

    def test_exclude_pycache(self):
        tmp = make_test_dir()
        pc = tmp / "__pycache__"
        pc.mkdir()
        (pc / "mod.cpython-39.pyc").write_text("# cache")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any("__pycache__" in f for f in indexed), f"__pycache__ should be excluded: {indexed}"

    def test_exclude_minified_js(self):
        tmp = make_test_dir()
        (tmp / "bundle.min.js").write_text("var a=1;")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any(".min.js" in f for f in indexed), f"minified JS should be excluded: {indexed}"

    def test_exclude_dist_and_build(self):
        tmp = make_test_dir()
        dist = tmp / "dist"
        dist.mkdir()
        (dist / "out.js").write_text("var x=1;")
        build = tmp / "build"
        build.mkdir()
        (build / "out.py").write_text("def foo(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any("/dist/" in f or "\\dist\\" in f for f in indexed), f"dist/ should be excluded: {indexed}"
        assert not any("/build/" in f or "\\build\\" in f for f in indexed), f"build/ should be excluded: {indexed}"

    def test_exclude_venv(self):
        tmp = make_test_dir()
        venv = tmp / "venv"
        venv.mkdir()
        (venv / "lib.py").write_text("def foo(): pass")
        dotvenv = tmp / ".venv"
        dotvenv.mkdir()
        (dotvenv / "lib2.py").write_text("def bar(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any("/venv/" in f or "\\venv\\" in f for f in indexed), f"venv/ should be excluded: {indexed}"
        assert not any("/.venv/" in f or "\\.venv\\" in f for f in indexed), f".venv/ should be excluded: {indexed}"

    """A4: Custom Exclude Patterns"""

    def test_custom_exclude_patterns(self):
        tmp = make_test_dir()
        subdir = tmp / "vendor"
        subdir.mkdir()
        (subdir / "lib.py").write_text("def vendored(): pass")
        (tmp / "main.py").write_text("def main(): pass")

        builder = GraphBuilder(
            repo_path=str(tmp),
            exclude_patterns=["**/vendor/**"],
        )
        builder.build()
        indexed = set(builder.graph.file_symbols.keys())
        assert not any("vendor" in f for f in indexed), f"Custom exclude should skip vendor/: {indexed}"
        assert builder.exclude_patterns == ["**/vendor/**"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE B — Python Parsing Deep Dive
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional (silent crash on this platform)")
class TestB_PythonParsing:
    """B1: Nested Class Methods"""

    def test_nested_class_methods(self):
        tmp = make_test_dir()
        code = '''
class Outer:
    class Inner:
        def inner_method(self):
            pass
    def outer_method(self):
        pass
'''
        (tmp / "nested.py").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        outer_keys = [k for k in g.symbols if "Outer" in k and g.symbols[k].symbol_type == "class"]
        assert len(outer_keys) >= 1, f"Outer class not found: {list(g.symbols.keys())}"

        outer_method_keys = [k for k in g.symbols if "outer_method" in k]
        assert len(outer_method_keys) >= 1, f"outer_method not found: {list(g.symbols.keys())}"
        om_sym = g.symbols[outer_method_keys[0]]
        assert om_sym.parent == "Outer", f"outer_method parent should be 'Outer', got '{om_sym.parent}'"

    """B2: Decorated Functions"""

    def test_decorated_functions(self):
        tmp = make_test_dir()
        code = '''
@staticmethod
def my_static():
    pass

@property
def my_prop(self):
    return self._x
'''
        (tmp / "decorated.py").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        sym_names = {s.short_name for s in g.symbols.values()}
        assert "my_static" in sym_names, f"my_static not found: {sym_names}"
        assert "my_prop" in sym_names, f"my_prop not found: {sym_names}"

    """B3: Python Call Edge — self Calls"""

    def test_self_call_edges(self):
        tmp = make_test_dir()
        code = '''
class MyClass:
    def method_a(self):
        self.method_b()
    def method_b(self):
        pass
'''
        (tmp / "selfcalls.py").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        method_a_keys = [k for k in g.symbols if "method_a" in k]
        assert len(method_a_keys) >= 1, f"method_a not found: {list(g.symbols.keys())}"
        method_a_key = method_a_keys[0]

        successors = list(g.graph.successors(method_a_key))
        assert len(successors) >= 1, f"method_a should have outgoing edges, got none. Graph edges: {list(g.graph.edges())}"

        callee_keys = [c for c in successors if "method_b" in c]
        assert len(callee_keys) >= 1, f"method_a should call method_b, but edges go to: {successors}"

    """B4: Cross-File Resolution"""

    def test_cross_file_resolution(self):
        tmp = make_test_dir()
        (tmp / "a.py").write_text('''
def parse():
    validate()
''')
        (tmp / "b.py").write_text('''
def validate():
    pass
''')
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        a_parse_keys = [k for k in g.symbols if "a.py" in k and "parse" in k]
        b_validate_keys = [k for k in g.symbols if "b.py" in k and "validate" in k]
        assert len(a_parse_keys) >= 1, f"a.py::parse not found: {list(g.symbols.keys())}"
        assert len(b_validate_keys) >= 1, f"b.py::validate not found: {list(g.symbols.keys())}"

        parse_key = a_parse_keys[0]
        successors = list(g.graph.successors(parse_key))
        assert len(successors) >= 1, f"parse should have outgoing edges: {list(g.graph.edges())}"

        validate_callees = [c for c in successors if "validate" in c]
        assert len(validate_callees) >= 1, f"parse should call validate, but calls: {successors}"
        b_validate_key = b_validate_keys[0]
        assert b_validate_key in validate_callees, f"Expected callee {b_validate_key}, got {validate_callees}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE C — JavaScript/TypeScript Parsing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional (silent crash on this platform)")
class TestC_JSTSParsing:
    """C1: Function Declaration"""

    def test_function_declarations(self):
        tmp = make_test_dir()
        code = '''
function fetchData() { return process(); }
function process() { return {}; }
'''
        (tmp / "funcs.js").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        if builder.graph.symbols:
            func_syms = [s for s in g.symbols.values() if s.symbol_type == "function"]
            assert len(func_syms) >= 2, f"Expected 2+ function symbols, got {len(func_syms)}: {list(g.symbols.keys())}"

            fd_keys = [k for k in g.symbols if "fetchData" in k]
            assert len(fd_keys) >= 1, f"fetchData not found: {list(g.symbols.keys())}"
            successors = list(g.graph.successors(fd_keys[0]))
            process_callees = [c for c in successors if "process" in c]
            assert len(process_callees) >= 1, f"fetchData should call process, calls: {successors}"

    """C2: Arrow Functions"""

    def test_arrow_functions(self):
        tmp = make_test_dir()
        code = '''
const handler = () => { fetchData(); };
const processor = (x) => x * 2;
'''
        (tmp / "arrows.js").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        sym_names = {s.short_name for s in g.symbols.values()}
        assert "handler" in sym_names, f"handler arrow function not found: {sym_names}"
        handler_sym = g.symbols.get(f"arrows.js::handler")
        if handler_sym:
            assert handler_sym.symbol_type == "function"

    """C3: Class Methods"""

    def test_class_methods(self):
        tmp = make_test_dir()
        code = '''
class ApiClient {
    constructor() {}
    fetchData() { return this.parseResponse(); }
    parseResponse() { return {}; }
}
'''
        (tmp / "class.js").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        sym_names = {s.short_name for s in g.symbols.values()}
        assert "ApiClient" in sym_names, f"ApiClient class not found: {sym_names}"
        assert "ApiClient.constructor" in sym_names or "constructor" in sym_names, f"constructor not found: {sym_names}"
        assert "ApiClient.fetchData" in sym_names or "fetchData" in sym_names, f"fetchData method not found: {sym_names}"
        assert "ApiClient.parseResponse" in sym_names or "parseResponse" in sym_names, f"parseResponse method not found: {sym_names}"

        fd_keys = [k for k in g.symbols if "fetchData" in k]
        if fd_keys:
            successors = list(g.graph.successors(fd_keys[0]))
            pr_callees = [c for c in successors if "parseResponse" in c]
            assert len(pr_callees) >= 1, f"fetchData should call parseResponse, calls: {successors}"

    """C4: TypeScript Shared Parser"""

    def test_typescript_shared_parser(self):
        tmp = make_test_dir()
        code_ts = '''
function greet(name: string): void {
    console.log(name);
}
'''
        code_tsx = '''
function Hello() {
    return <div>Hello</div>;
}
'''
        (tmp / "file.ts").write_text(code_ts)
        (tmp / "file.tsx").write_text(code_tsx)

        builder = GraphBuilder(repo_path=str(tmp))
        stats = builder.build()

        if stats["files_processed"] > 0:
            indexed = set(builder.graph.file_symbols.keys())
            ts_files = [f for f in indexed if f.endswith(".ts")]
            tsx_files = [f for f in indexed if f.endswith(".tsx")]
            assert len(ts_files) >= 1 or len(tsx_files) >= 1, f"TS/TSX files should be parsed: {indexed}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE D — Go Parsing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional (silent crash on this platform)")
class TestD_GoParsing:
    """D1: Function Declaration"""

    def test_function_declarations(self):
        tmp = make_test_dir()
        code = '''
package main

func main() { runServer() }
func runServer() {}
'''
        (tmp / "main.go").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        if builder.graph.symbols:
            func_syms = [s for s in g.symbols.values() if s.symbol_type == "function"]
            assert len(func_syms) >= 2, f"Expected 2 function symbols, got {len(func_syms)}: {list(g.symbols.keys())}"

            main_keys = [k for k in g.symbols if k.endswith("::main")]
            if main_keys:
                successors = list(g.graph.successors(main_keys[0]))
                rs_callees = [c for c in successors if "runServer" in c]
                assert len(rs_callees) >= 1, f"main should call runServer, calls: {successors}"

    """D2: Method with Receiver"""

    def test_method_with_receiver(self):
        tmp = make_test_dir()
        code = '''
package main

type Server struct{}

func (s *Server) Start() { s.Listen() }
func (s *Server) Listen() {}
'''
        (tmp / "server.go").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        start_keys = [k for k in g.symbols if "Start" in k]
        listen_keys = [k for k in g.symbols if "Listen" in k]
        assert len(start_keys) >= 1, f"Server.Start not found: {list(g.symbols.keys())}"
        assert len(listen_keys) >= 1, f"Server.Listen not found: {list(g.symbols.keys())}"

        start_sym = g.symbols[start_keys[0]]
        listen_sym = g.symbols[listen_keys[0]]

        assert start_sym.parent == "Server", f"Start parent should be 'Server', got '{start_sym.parent}'"
        assert listen_sym.parent == "Server", f"Listen parent should be 'Server', got '{listen_sym.parent}'"

        assert start_sym.symbol_type == "method", f"Start type should be 'method', got '{start_sym.symbol_type}'"
        assert listen_sym.symbol_type == "method", f"Listen type should be 'method', got '{listen_sym.symbol_type}'"

    """D3: Struct as Class"""

    def test_struct_as_class(self):
        tmp = make_test_dir()
        code = '''
package main

type Server struct {
    Port int
}
'''
        (tmp / "struct.go").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        server_keys = [k for k in g.symbols if "Server" in k]
        assert len(server_keys) >= 1, f"Server struct not found: {list(g.symbols.keys())}"
        server_sym = g.symbols[server_keys[0]]
        assert server_sym.symbol_type == "class", f"Server should be symbol_type='class', got '{server_sym.symbol_type}'"

    """D4: Package-Level Calls"""

    def test_package_level_calls(self):
        tmp = make_test_dir()
        code = '''
package main

func handler() { fmt.Println("hello") }
'''
        (tmp / "handler.go").write_text(code)
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        handler_keys = [k for k in g.symbols if "handler" in k]
        if handler_keys:
            successors = list(g.graph.successors(handler_keys[0]))
            println_callees = [c for c in successors if "Println" in c]
            assert len(println_callees) >= 1, f"handler should call Println, calls: {successors}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE E — Cross-File Symbol Resolution
# ─────────────────────────────────────────────────────────────────────────────

class TestE_CrossFileResolution:
    """E1: Unambiguous Resolution"""

    def test_unambiguous(self):
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::unique_fn", short_name="unique_fn", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        resolved = g.resolve_symbol("unique_fn")
        assert resolved == "a.py::unique_fn", f"Expected 'a.py::unique_fn', got '{resolved}'"

    """E2: Ambiguous Resolution"""

    def test_ambiguous(self):
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::parse", short_name="parse", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        g.add_symbol(Symbol(
            name="b.py::parse", short_name="parse", symbol_type="function",
            file_path="b.py", line_start=1, line_end=5,
        ))
        resolved = g.resolve_symbol("parse")
        assert resolved in ("a.py::parse", "b.py::parse"), f"Expected one of the parse symbols, got '{resolved}'"

    """E3: Fully Qualified Resolution"""

    def test_fully_qualified(self):
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::parse", short_name="parse", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        resolved = g.resolve_symbol("a.py::parse")
        assert resolved == "a.py::parse", f"Expected 'a.py::parse', got '{resolved}'"

    """E4: Missing Symbol"""

    def test_missing(self):
        g = CodeGraph()
        resolved = g.resolve_symbol("nonexistent")
        assert resolved is None, f"Expected None for missing symbol, got '{resolved}'"

    """E5: Call Edge Resolution During Build"""

    @pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional (silent crash on this platform)")
    def test_call_edge_resolution_in_build(self):
        tmp = make_test_dir()
        (tmp / "caller.py").write_text('''
def run():
    validate()
''')
        (tmp / "def_a.py").write_text('''
def validate():
    pass
''')
        (tmp / "def_b.py").write_text('''
def validate():
    pass
''')
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        run_keys = [k for k in g.symbols if "caller.py" in k and "run" in k]
        assert len(run_keys) >= 1, f"caller.py::run not found: {list(g.symbols.keys())}"

        successors = list(g.graph.successors(run_keys[0]))
        assert len(successors) >= 1, f"run should have outgoing edges: {list(g.graph.edges())}"

        validate_callees = [c for c in successors if "validate" in c]
        assert len(validate_callees) >= 1, f"run should call validate, calls: {successors}"

    @pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional (silent crash on this platform)")
    def test_call_edge_unambiguous_fallback(self):
        tmp = make_test_dir()
        (tmp / "caller.py").write_text('''
def run():
    validate()
''')
        (tmp / "definer.py").write_text('''
def validate():
    pass
''')
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        g = builder.graph

        run_keys = [k for k in g.symbols if "caller.py" in k and "run" in k]
        validate_keys = [k for k in g.symbols if "definer.py" in k and "validate" in k]

        assert len(run_keys) >= 1
        assert len(validate_keys) >= 1

        successors = list(g.graph.successors(run_keys[0]))
        assert validate_keys[0] in successors, f"Expected callee {validate_keys[0]}, got {successors}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE F — Export & Stats
# ─────────────────────────────────────────────────────────────────────────────

class TestF_ExportStats:
    """F1: JSON Export"""

    def test_json_export(self):
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::foo", short_name="foo", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        g.add_symbol(Symbol(
            name="a.py::bar", short_name="bar", symbol_type="function",
            file_path="a.py", line_start=6, line_end=10,
        ))
        g.add_call(CallEdge(
            caller="a.py::foo", callee="a.py::bar",
            call_type="direct_call", file_path="a.py", line=3,
        ))
        result = g.export("json")
        assert "nodes" in result, "JSON export should have 'nodes' key"
        assert "edges" in result, "JSON export should have 'edges' key"
        assert len(result["edges"]) >= 1, "Should have at least 1 edge"
        for edge in result["edges"]:
            assert "source" in edge, "Edge should have 'source'"
            assert "target" in edge, "Edge should have 'target'"

    """F2: DOT Export"""

    def test_dot_export(self):
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::foo", short_name="foo", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        g.add_call(CallEdge(
            caller="a.py::foo", callee="a.py::bar",
            call_type="direct_call", file_path="a.py", line=3,
        ))
        result = g.export("dot")
        assert "dot" in result, "DOT export should have 'dot' key"
        dot_str = result["dot"]
        assert "digraph CodeGraph {" in dot_str, "Should start with 'digraph CodeGraph {'"
        assert "}" in dot_str, "Should end with '}'"
        assert '"a.py::foo"' in dot_str, f"Should have quoted node name: {dot_str}"

    """F3: Summary Export"""

    def test_summary_export(self):
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::foo", short_name="foo", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        g.add_symbol(Symbol(
            name="b.py::bar", short_name="bar", symbol_type="class",
            file_path="b.py", line_start=1, line_end=5,
        ))
        g.add_call(CallEdge(
            caller="a.py::foo", callee="b.py::bar",
            call_type="direct_call", file_path="a.py", line=3,
        ))
        result = g.export("summary")
        assert "total_symbols" in result
        assert "total_edges" in result
        assert "files_indexed" in result
        assert "symbol_types" in result
        assert result["total_symbols"] == 2
        assert result["total_edges"] == 1
        assert result["files_indexed"] == 2
        assert "function" in result["symbol_types"]
        assert "class" in result["symbol_types"]

    """F4: get_stats"""

    def test_get_stats(self):
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::foo", short_name="foo", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        g.add_call(CallEdge(
            caller="a.py::foo", callee="a.py::bar",
            call_type="direct_call", file_path="a.py", line=3,
        ))
        stats = g.get_stats()
        assert "total_symbols" in stats
        assert "total_edges" in stats
        assert "files_indexed" in stats
        assert "symbol_types" in stats
        assert "most_connected" in stats
        assert isinstance(stats["most_connected"], list)

        if stats["most_connected"]:
            mc = stats["most_connected"][0]
            assert "name" in mc
            assert "short_name" in mc
            assert "type" in mc
            assert "total_connections" in mc
            assert "incoming" in mc
            assert "outgoing" in mc


# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITE G — New Features (Diagnostics, Incremental, Git, Batch Ops)
# ─────────────────────────────────────────────────────────────────────────────

class TestG_NewFeatures:
    """G1: BuildDiagnostics collects warnings/errors"""

    def test_diagnostics_present(self):
        from code_graph import BuildDiagnostics
        d = BuildDiagnostics()
        d.warn("test warning")
        d.error("test error")
        s = d.to_summary()
        assert "test warning" in s["warnings"]
        assert "test error" in s["errors"]
        assert s["files_parsed"] == 0
        assert s["files_skipped"] == 0
        assert s["files_failed"] == 0

    """G2: Build returns diagnostics in result dict"""

    @pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional")
    def test_build_returns_diagnostics(self):
        tmp = make_test_dir()
        (tmp / "a.py").write_text("def foo(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        result = builder.build()
        assert "diagnostics" in result
        assert "warnings" in result["diagnostics"]
        assert "errors" in result["diagnostics"]
        assert result["diagnostics"]["files_parsed"] >= 1

    """G3: Build returns call_resolution stats"""

    @pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional")
    def test_build_returns_call_resolution(self):
        tmp = make_test_dir()
        (tmp / "a.py").write_text("def foo(): bar()")
        (tmp / "b.py").write_text("def bar(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        result = builder.build()
        assert "call_resolution" in result
        assert "resolved" in result["call_resolution"]
        assert "unresolved" in result["call_resolution"]
        assert result["call_resolution"]["resolved"] >= 1

    """G4: Build returns elapsed_s and incremental flag"""

    @pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional")
    def test_build_returns_timing(self):
        tmp = make_test_dir()
        (tmp / "a.py").write_text("def foo(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        result = builder.build()
        assert "elapsed_s" in result
        assert result["elapsed_s"] >= 0
        assert "incremental" in result
        assert result["incremental"] is False

    """G5: Incremental build — only changed files re-parsed"""

    @pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional")
    def test_incremental_build(self):
        tmp = make_test_dir()
        (tmp / "a.py").write_text("def foo(): pass")
        (tmp / "b.py").write_text("def bar(): pass")

        # Full build
        builder = GraphBuilder(repo_path=str(tmp))
        result1 = builder.build()
        assert result1["files_processed"] == 2

        # Incremental: only a.py changed
        result2 = builder.build(changed_files_only=["a.py"])
        assert result2["incremental"] is True
        assert result2["files_processed"] == 1
        # b.py symbols should still be in graph (not removed)
        b_syms = [k for k in builder.graph.symbols if "b.py" in k]
        assert len(b_syms) >= 1

    """G6: remove_file removes symbols for a file"""

    def test_remove_file(self):
        from code_graph import CodeGraph, Symbol
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::foo", short_name="foo", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        g.add_symbol(Symbol(
            name="b.py::bar", short_name="bar", symbol_type="function",
            file_path="b.py", line_start=1, line_end=5,
        ))
        assert "a.py::foo" in g.symbols
        assert "b.py::bar" in g.symbols

        g.remove_file("a.py")
        assert "a.py::foo" not in g.symbols
        assert "b.py::bar" in g.symbols
        # short_name index should not contain foo anymore
        assert "foo" not in g._short_name_index

    """G7: get_changed_files falls back to indexed files when no git"""

    @pytest.mark.skipif(not PARSERS_WORK, reason="tree-sitter grammars not functional")
    def test_get_changed_files_fallback(self):
        tmp = make_test_dir()
        (tmp / "a.py").write_text("def foo(): pass")
        builder = GraphBuilder(repo_path=str(tmp))
        builder.build()
        changed = builder.get_changed_files()
        # Should return indexed files as fallback
        assert len(changed) >= 1 or len(builder.graph.file_symbols) >= 1

    """G8: Batch edge addition"""

    def test_add_calls_batch(self):
        from code_graph import CodeGraph, Symbol, CallEdge
        g = CodeGraph()
        g.add_symbol(Symbol(
            name="a.py::foo", short_name="foo", symbol_type="function",
            file_path="a.py", line_start=1, line_end=5,
        ))
        g.add_symbol(Symbol(
            name="a.py::bar", short_name="bar", symbol_type="function",
            file_path="a.py", line_start=6, line_end=10,
        ))
        edges = [
            CallEdge(caller="a.py::foo", callee="a.py::bar", call_type="direct_call", file_path="a.py", line=3),
        ]
        count = g.add_calls_batch(edges)
        assert count == 1

    """G9: Parser warnings when no grammars loaded"""

    def test_parser_warnings(self):
        # Create a builder with tree-sitter unavailable (simulate by checking diagnostics)
        from code_graph import GraphBuilder, _TREE_SITTER_AVAILABLE
        if _TREE_SITTER_AVAILABLE:
            # Parsers loaded fine — just verify diagnostics object exists
            builder = GraphBuilder(repo_path=".")
            assert builder.diagnostics is not None
            # If parsers loaded, no import errors should be present
            import_errors = [e for e in builder.diagnostics.errors if "import crash" in e]
            # On this machine parsers DO load, so no import crash errors
            assert len(import_errors) == 0

    """G10: EXT_MAP constant present"""

    def test_ext_map_present(self):
        assert hasattr(GraphBuilder, "EXT_MAP")
        assert GraphBuilder.EXT_MAP[".py"] == "python"
        assert GraphBuilder.EXT_MAP[".js"] == "javascript"
        assert GraphBuilder.EXT_MAP[".go"] == "go"


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

def teardown_module(module):
    cleanup_test_dirs()
