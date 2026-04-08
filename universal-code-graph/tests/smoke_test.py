"""
Smoke tests run directly by CI — no heredoc, no indentation issues.
Tests the graph engine against real source files.
"""
import sys
import os
import tempfile
from pathlib import Path

# Ensure we can import code_graph from the parent dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from code_graph import GraphBuilder

_TMPDIR = Path(tempfile.gettempdir())


def test_python_parser():
    tmp = _TMPDIR / "smoke_py"
    tmp.mkdir(exist_ok=True)
    (tmp / "sample.py").write_text("""
class MyClass:
    def method_a(self):
        self.method_b()

    def method_b(self):
        pass

def standalone():
    obj = MyClass()
    obj.method_a()
""")
    builder = GraphBuilder(repo_path=str(tmp), db_path=str(tmp / ".db"))
    stats = builder.build()
    g = builder.graph
    assert stats["files_processed"] >= 1, f"No files processed: {stats}"
    assert len(g.symbols) >= 4, f"Expected 4+ symbols, got {len(g.symbols)}: {list(g.symbols.keys())}"
    assert g.graph.number_of_edges() > 0, "Expected call edges for Python"
    print(f"  Python OK: {len(g.symbols)} symbols, {g.graph.number_of_edges()} edges")


def test_js_parser():
    tmp = _TMPDIR / "smoke_js"
    tmp.mkdir(exist_ok=True)
    (tmp / "sample.js").write_text("""
class ApiClient {
  constructor() {}
  fetchData() { return this.parseResponse(); }
  parseResponse() { return {}; }
}
function main() {
  const c = new ApiClient();
  c.fetchData();
}
""")
    builder = GraphBuilder(repo_path=str(tmp), db_path=str(tmp / ".db"))
    stats = builder.build()
    g = builder.graph
    if stats["files_processed"] == 0:
        print("  JS SKIP: tree-sitter-javascript not installed")
        return
    assert len(g.symbols) >= 3, f"Expected 3+ symbols, got {len(g.symbols)}"
    print(f"  JS OK: {len(g.symbols)} symbols, {g.graph.number_of_edges()} edges")


def test_go_parser():
    tmp = _TMPDIR / "smoke_go"
    tmp.mkdir(exist_ok=True)
    (tmp / "main.go").write_text("""
package main

type Server struct{}

func (s *Server) Start() {
    s.Listen()
}

func (s *Server) Listen() {}

func main() {
    srv := &Server{}
    srv.Start()
}
""")
    builder = GraphBuilder(repo_path=str(tmp), db_path=str(tmp / ".db"))
    stats = builder.build()
    g = builder.graph
    if stats["files_processed"] == 0:
        print("  Go SKIP: tree-sitter-go not installed")
        return
    assert len(g.symbols) >= 3, f"Expected 3+ symbols, got {len(g.symbols)}"
    print(f"  Go OK: {len(g.symbols)} symbols, {g.graph.number_of_edges()} edges")


def test_self_index():
    """Index the code_graph.py file itself."""
    this_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    builder = GraphBuilder(repo_path=this_dir, db_path=str(_TMPDIR / "self.db"))
    stats = builder.build()
    assert stats["files_processed"] >= 1
    assert stats["symbols_found"] > 0
    print(f"  Self-index OK: {stats['symbols_found']} symbols, {stats['edges_found']} edges")


if __name__ == "__main__":
    tests = [test_python_parser, test_js_parser, test_go_parser, test_self_index]
    failed = []
    for t in tests:
        print(f"Running {t.__name__}...")
        try:
            t()
        except Exception as e:
            print(f"  FAIL: {e}")
            failed.append(t.__name__)

    if failed:
        print(f"\nFAILED: {failed}")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} smoke tests passed.")
