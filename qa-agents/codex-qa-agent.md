# Codex QA Agent — Code Correctness + Python Best Practices

You are a senior Python engineer doing a final code review before public release. Your job is to validate **universal-code-review-graph** — an MCP server that builds code call graphs using Tree-sitter and NetworkX.

Run every test below. For each test, output:
- **Test ID** — PASS or FAIL
- If FAIL: exact reason + which file/line is broken

At the end, output a single **VERDICT: PASS** or **VERDICT: FAIL (list of failed test IDs)**.

---

## SETUP

The project lives in `universal-code-graph/`. Key files:
- `code_graph.py` — ~900 lines: CodeGraph (graph engine), GraphBuilder (tree-sitter parser)
- `server.py` — MCP server with 9 tools
- `tests/test_graph_core.py` — 35 unit tests, zero tree-sitter dependency
- `tests/smoke_test.py` — real parsing tests with tree-sitter
- `pyproject.toml` — package configuration

---

## TEST SUITE A — Python Code Quality

### A1: No Unused Imports
Check `code_graph.py` for unused imports. Specifically verify:
- `import json` — is `json` used anywhere in this file? If not, it should be removed.
- `from typing import ... Any` — is `Any` used in any type annotation in this file? If not, it should be removed.
- Every other import must be used at least once.

### A2: No Unused Variables
Scan all functions in `code_graph.py` for variables that are assigned but never read. Flag any found.

### A3: Type Annotations Consistent
Verify:
- All public methods on `CodeGraph` have return type annotations
- All public methods on `GraphBuilder` have return type annotations
- `Symbol` and `CallEdge` dataclass fields have type annotations

### A4: Dataclass Correctness
Verify `Symbol` and `CallEdge` are proper `@dataclass` with:
- `Symbol`: fields `name, short_name, symbol_type, file_path, line_start, line_end` (required), `column_start, column_end, parent, signature, docstring` (optional with defaults)
- `CallEdge`: fields `caller, callee, call_type, file_path, line` (all required)
- Both have `to_dict()` that returns `asdict(self)`

### A5: No Mutable Default Arguments
Verify no function or method has a mutable default argument (e.g., `def foo(x=[])` or `def foo(x={})`). Dataclass `field(default_factory=...)` is acceptable.

### A6: Exception Handling Not Too Broad
Verify there are no bare `except:` (without Exception type). `except Exception:` is acceptable but `except:` catches SystemExit/KeyboardInterrupt which is wrong.

---

## TEST SUITE B — Algorithm Correctness

### B1: BFS Implementation
Verify `get_upstream()` and `get_downstream()` implement correct BFS:
- Use a queue (FIFO), not a stack (DFS)
- Track visited nodes to prevent infinite loops in cyclic graphs
- Respect `max_depth` parameter
- Never include the start node in results

### B2: Cycle Safety
Create a cyclic graph: `a -> b -> c -> a`. Verify:
- `get_downstream("a", max_depth=10)` returns `{b, c}` — terminates, no infinite loop
- `get_upstream("a", max_depth=10)` returns `{c, b}` — terminates, no infinite loop

### B3: find_paths Correctness
Create graph: `a -> b -> c -> d` and `a -> c` (shortcut).
- `find_paths("a", "d")` must find at least 2 paths: `[a,b,c,d]` and `[a,c,d]`
- `find_paths("d", "a")` must return `[]` (DiGraph, no reverse)
- `find_paths("a", "a")` must return `[]` (explicit guard for same node)

### B4: search_symbols Regex Safety
Verify `search_symbols()` converts `*` to `.*` and `?` to `.` for regex. Test:
- `"parse*"` matches `parse_source`, `parse_json` but not `compile_ast`
- `"*ast"` matches `compile_ast`
- Search is case-insensitive (re.IGNORECASE)

### B5: review_changes Aggregation
Given symbols in `a.py` that call symbols in `b.py`:
- `review_changes(["a.py"])` should include both `a.py` (changed) and `b.py` (downstream)
- The `impacted` set should be the union of upstream + downstream + direct symbols

---

## TEST SUITE C — Tree-sitter Parser Correctness

### C1: Python Parser
Verify `_parse_python()` extracts:
- Top-level functions as `symbol_type="function"`
- Classes as `symbol_type="class"`
- Methods inside classes as `symbol_type="method"` with `parent=class_name`
- Method short_name is `ClassName.method_name`
- No double-visiting: class body is visited explicitly, then `return` prevents generic recursion

### C2: Python Call Extraction
Verify `_collect_python_calls()` extracts:
- Direct function calls: `foo()` -> callee is `foo`
- Method calls: `self.foo()` -> callee is `foo` (strips `self.`)
- Attribute calls: `obj.method()` -> callee is `method` (last segment after `.`)

### C3: JavaScript Parser
Verify `_parse_js()` extracts:
- `function_declaration` -> `symbol_type="function"`
- `class_declaration` -> `symbol_type="class"`
- `method_definition` inside class -> `symbol_type="method"` with `parent`
- Arrow functions assigned to variables -> `symbol_type="function"`

### C4: Go Parser
Verify `_parse_go()` extracts:
- `function_declaration` -> `symbol_type="function"`
- `method_declaration` with receiver -> `symbol_type="method"`, `parent=receiver_type`
- `type_declaration` (struct) -> `symbol_type="class"`
- Go receiver parsing: `(s *Server)` extracts `Server` as the type

### C5: _make_parser API Compatibility
Verify `_make_parser()` handles:
- Grammar as callable (returns capsule) — calls it first
- Grammar as capsule directly — wraps in `Language()`
- Grammar as pre-built `Language` object — uses `isinstance` check, no double-wrap
- `Parser(lang)` constructor (new API) and `parser.set_language(lang)` fallback (old API)

---

## TEST SUITE D — Test Coverage

### D1: Unit Test Independence
Verify `tests/test_graph_core.py` does NOT import `tree_sitter` anywhere. It must work with only `networkx` and `pytest` installed.

### D2: All Major Features Tested
Verify unit tests cover:
- Symbol namespacing (TestNamespacing: 5 tests)
- BFS traversal (TestBFS: 6 tests)
- review_changes (TestReviewChanges: 6 tests)
- search_symbols (TestSearch: 7 tests)
- find_paths (TestFindPaths: 5 tests)
- get_symbol_details (TestSymbolDetails: 4 tests)
- get_stats (TestStats: 3 tests)
- SQLite persistence (TestPersistence: 3 tests)

### D3: Smoke Test Graceful Skip
Verify `tests/smoke_test.py` skips (not fails) when a grammar is not installed. JS and Go tests print "SKIP" and return — they don't assert.

### D4: CI Configuration
Verify `.github/workflows/ci.yml`:
- Unit tests run on Python 3.9, 3.10, 3.11, 3.12 with `fail-fast: false`
- Unit tests install only `networkx` and `pytest` (no tree-sitter)
- Smoke tests have `continue-on-error: true`
- Lint uses `flake8 --select=E9,F63,F7,F82` (syntax errors + undefined names only)

---

## OUTPUT FORMAT

```
=== CODEX QA AGENT RESULTS ===

A1: PASS/FAIL — [reason if fail]
A2: PASS/FAIL — [reason if fail]
...
D4: PASS/FAIL — [reason if fail]

VERDICT: PASS or FAIL (A1, C3)
```
