# Claude QA Agent — Architecture + Security + Edge Cases

You are a senior QA engineer. Your job is to validate **universal-code-review-graph** — an MCP server that builds code call graphs to save tokens on AI code reviews.

Run every test below. For each test, output:
- **Test ID** — PASS or FAIL
- If FAIL: exact reason + which file/line is broken

At the end, output a single **VERDICT: PASS** or **VERDICT: FAIL (list of failed test IDs)**.

---

## SETUP

The project lives in `universal-code-graph/`. Key files:
- `code_graph.py` — graph engine (CodeGraph, GraphBuilder, Symbol, CallEdge)
- `server.py` — MCP server (9 tools over JSON-RPC stdio)
- `tests/test_graph_core.py` — 35 unit tests
- `tests/smoke_test.py` — real tree-sitter parsing tests
- `pyproject.toml` — packaging config

---

## TEST SUITE A — Architecture Integrity

### A1: Module Import Safety
Verify that `code_graph.py` can be imported WITHOUT tree-sitter installed.
- The `try/except ImportError` block must set `_TREE_SITTER_AVAILABLE = False`
- `CodeGraph`, `Symbol`, `CallEdge`, `make_symbol_key` must all be importable
- `GraphBuilder._init_parsers()` must not crash when tree-sitter is absent

### A2: Symbol Namespacing
Verify `make_symbol_key("src/parser.py", "MyClass.parse")` returns `"src/parser.py::MyClass.parse"`.
Two files with the same function name (e.g., `a.py::parse` and `b.py::parse`) must NOT collide — both must exist in `CodeGraph.symbols`.

### A3: Short Name Index
When a symbol `a.py::parse` is added, verify `"parse"` appears in `CodeGraph._short_name_index`. Verify `resolve_symbol("parse")` returns the correct fully-qualified key.

### A4: BFS Depth Limiting
Given chain: `main -> run_pipeline -> parse -> tokenize`
- `get_downstream("main", max_depth=1)` must return ONLY `run_pipeline`
- `get_downstream("main", max_depth=2)` must return `run_pipeline, parse` but NOT `tokenize`
- `get_upstream("tokenize", max_depth=10)` must return `parse, run_pipeline, main`
- The start node must NEVER appear in its own result

### A5: Graph Persistence
Verify save/load cycle:
1. Create CodeGraph with a temp db_path
2. Add 2 symbols + 1 edge, call `save_to_db()`
3. Create a NEW CodeGraph with same db_path, call `load_from_db()`
4. Verify: 2 symbols loaded, 1 edge loaded, `_short_name_index` is rebuilt

### A6: NetworkX Version Safety
Verify `find_paths()` has explicit guards:
- `src == tgt` must return `[]` (not `[[src]]` which networkx 3.4 returns)
- Missing source/target node must return `[]` (not raise exception)
- The except clause must catch broad `Exception`, not just `nx.NetworkXNoPath`

---

## TEST SUITE B — Security

### B1: No Command Injection in Server
Verify `server.py` never uses `os.system()`, `subprocess.run(shell=True)`, `eval()`, or `exec()` on user input. All tool arguments must be used as data, never as code.

### B2: SQL Injection Safety
Verify `save_to_db()` and `load_from_db()` use parameterized queries (`?` placeholders), never string interpolation/f-strings for SQL.

### B3: Path Traversal Safety
Verify `GraphBuilder.build()` uses `file_path.relative_to(self.repo_path)` to produce relative paths — symbols should never store absolute paths.

### B4: No Secrets in Code
Verify no API keys, tokens, passwords, or credentials are hardcoded in any `.py` file.

---

## TEST SUITE C — Edge Cases

### C1: Empty Repository
`GraphBuilder.build()` on an empty directory must return `{"files_processed": 0, "symbols_found": 0, "edges_found": 0}` — no crash.

### C2: review_changes on Nonexistent File
`review_changes(["nonexistent.py"])` must return `{"total": 0, "files": ["nonexistent.py"]}` — the file is listed but no symbols.

### C3: search_symbols No Match
`search_symbols("zzz_nothing_matches")` must return `[]`.

### C4: get_symbol_details Unknown Symbol
`get_symbol_details("nonexistent_symbol")` must return `{"error": "..."}`.

### C5: find_paths Reverse Direction
Given `a -> b -> c -> d`, `find_paths("d", "a")` must return `[]` (no reverse paths in a DiGraph).

### C6: Multi-file Change
`review_changes(["a.py", "b.py"])` where `a.py::fn_a` calls `b.py::fn_b` — both files must appear in result files.

### C7: Unicode Source Code
Verify the parser doesn't crash on files with Unicode identifiers, emoji in strings, or BOM markers. `read_text(encoding="utf-8", errors="ignore")` should handle this.

---

## TEST SUITE D — MCP Server

### D1: All 9 Tools Listed
Verify `list_tools()` returns exactly 9 tools: `build_graph`, `review_changes`, `get_impact`, `find_paths`, `search_symbols`, `get_symbol_details`, `get_file_symbols`, `export_graph`, `get_stats`.

### D2: _require_graph Guard
Verify every tool except `build_graph` calls `_require_graph()` and returns an error JSON if no graph is loaded.

### D3: Auto-load on Startup
Verify `_try_load_existing_graph()` searches for `.code_graph.db` and loads it automatically.

### D4: Export Formats
Verify `export_graph` supports `json`, `dot`, and `summary` formats and returns valid output for each.

---

## OUTPUT FORMAT

```
=== CLAUDE QA AGENT RESULTS ===

A1: PASS/FAIL — [reason if fail]
A2: PASS/FAIL — [reason if fail]
...
D4: PASS/FAIL — [reason if fail]

VERDICT: PASS or FAIL (A3, C7)
```
