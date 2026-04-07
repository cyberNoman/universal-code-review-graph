# Gemini QA Agent — Documentation + API Consistency + User Experience

You are a senior QA engineer specializing in developer experience and documentation quality. Your job is to validate **universal-code-review-graph** — an MCP server that builds code call graphs to save 6-8x tokens on AI code reviews. This product is about to launch publicly.

Run every test below. For each test, output:
- **Test ID** — PASS or FAIL
- If FAIL: exact reason + what needs to change

At the end, output a single **VERDICT: PASS** or **VERDICT: FAIL (list of failed test IDs)**.

---

## SETUP

Key files to review:
- `README.md` (root) — GitHub landing page
- `docs/architecture.md` — system architecture
- `docs/api-reference.md` — all 9 tool docs
- `docs/developer-guide.md` — dev setup + testing + release
- `docs/adding-a-language.md` — how to add a new language
- `universal-code-graph/CONTRIBUTING.md` — contribution guidelines
- `universal-code-graph/pyproject.toml` — package metadata
- `universal-code-graph/server.py` — the actual MCP server
- `universal-code-graph/code_graph.py` — the graph engine

---

## TEST SUITE A — README Quality (First Impression)

### A1: Value Proposition Clear in 5 Seconds
Does the README communicate what the tool does within the first 3 lines? It should say: (1) what it is (MCP server for code graphs), (2) what it does (reduces tokens on code reviews), (3) how much (6-8x savings).

### A2: Install Instructions Complete
Verify the README has:
- pip install command: `pip install "universal-code-review-graph[all]"`
- From-source install: `git clone` + `pip install -e ".[all]"`
- Language-specific installs: `[python]`, `[javascript]`, `[go]`

### A3: AI Integration Configs
Verify README shows how to configure for:
- Claude Code (`claude mcp add`)
- Cursor (`~/.cursor/mcp.json`)
- Kimi / Qwen / ChatGPT / Windsurf / Zed / Continue (generic MCP config)
Each config must be a valid, copy-pasteable JSON or shell command.

### A4: Mermaid Diagrams Render
Verify the README contains Mermaid diagram blocks (```mermaid) for:
- Before/After token comparison
- How it works (pipeline flow)
- 9 tools mindmap
- Blast radius algorithm
All must use valid Mermaid syntax that GitHub renders natively.

### A5: Token Savings Table
Verify there's a table showing per-AI token savings (Kimi, Claude, Gemini, ChatGPT, Qwen, Cursor, Windsurf, Zed). Numbers should be in the 6-8x range.

### A6: Supported Languages Table
Verify there's a table showing Python, JavaScript/JSX, TypeScript/TSX, Go as supported. Rust and Java should show "planned".

### A7: Real Example
Verify the README has a concrete example with actual numbers (e.g., "127 Python files, changed 2 files, without graph: 18,400 tokens, with graph: 2,100 tokens").

---

## TEST SUITE B — API Documentation Accuracy

### B1: All 9 Tools Documented
Verify `docs/api-reference.md` documents all 9 tools: `build_graph`, `review_changes`, `get_impact`, `find_paths`, `search_symbols`, `get_symbol_details`, `get_file_symbols`, `export_graph`, `get_stats`.

### B2: Parameter Docs Match Code
For each tool in `docs/api-reference.md`, verify the documented parameters (name, type, required/optional, default) match the `inputSchema` in `server.py`. Flag any mismatch.

### B3: Response Examples Valid
Verify each tool's documented response example is valid JSON and matches what the code actually produces. Check field names match.

### B4: build_graph Response
Verify docs show: `status`, `message`, `stats` (with `files_processed`, `symbols_found`, `edges_found`, `repo_path`).

### B5: review_changes Response
Verify docs show: `changed_files`, `impacted_symbols`, `total_impacted`, `upstream_count`, `downstream_count`, `files_to_review`.

---

## TEST SUITE C — Developer Documentation

### C1: Architecture Doc Complete
Verify `docs/architecture.md` explains:
- Overall system design (Tree-sitter -> NetworkX -> SQLite -> MCP)
- Class responsibilities (CodeGraph, GraphBuilder, Symbol, CallEdge)
- Data flow from source code to MCP response

### C2: Developer Guide Setup
Verify `docs/developer-guide.md` has:
- Clone + install instructions
- How to run unit tests (`pytest tests/test_graph_core.py`)
- How to run smoke tests
- How to build the package

### C3: Adding a Language Guide
Verify `docs/adding-a-language.md` has:
- Step-by-step instructions for adding a new language
- Example (Rust or similar) showing the parser function pattern
- How to discover node types using tree-sitter

### C4: CONTRIBUTING.md
Verify `universal-code-graph/CONTRIBUTING.md` exists and includes:
- How to report bugs
- How to submit PRs
- Code style expectations
- Most-wanted contributions list

---

## TEST SUITE D — Package Metadata & Distribution

### D1: pyproject.toml Metadata
Verify:
- `name = "universal-code-review-graph"` (PyPI name)
- `version = "1.0.0"`
- `description` is a clear one-liner
- `license = "MIT"`
- `requires-python = ">=3.9"`
- `authors` field present
- `keywords` include: mcp, ai, code-review, graph, tree-sitter

### D2: Classifiers Appropriate
Verify classifiers include:
- Development Status :: 4 - Beta
- Python 3.9, 3.10, 3.11, 3.12
- Topic :: Software Development
- Topic :: Scientific/Engineering :: Artificial Intelligence

### D3: URLs Valid
Verify `[project.urls]` has Homepage, Repository, Documentation, and Bug Tracker — all pointing to the GitHub repo.

### D4: Entry Point Works
Verify `[project.scripts]` defines `code-graph-server` that points to a valid module path.

---

## TEST SUITE E — User Experience Consistency

### E1: Error Messages Helpful
Verify when no graph is loaded, all tools return: `"No graph loaded. Call build_graph first (or re-open the repo if a .code_graph.db exists)."` — this is actionable, not cryptic.

### E2: Tool Names Consistent
Verify tool names use snake_case consistently: `build_graph`, `review_changes`, `get_impact`, `find_paths`, `search_symbols`, `get_symbol_details`, `get_file_symbols`, `export_graph`, `get_stats`. No camelCase, no hyphens.

### E3: Tool Descriptions Self-Contained
Verify each tool's `description` in `server.py` explains what it does without requiring the user to read docs. An AI seeing only the tool list should understand when to use each.

### E4: JSON Response Consistency
Verify all tool responses use consistent patterns:
- Success: JSON with relevant data fields
- Error: `{"error": "message"}` 
- No mixed formats (sometimes JSON, sometimes plain text)

### E5: README and Docs Agree
Verify the tool count (9), language count (4), and token savings claim (6-8x) are consistent between README, docs, and code. No contradictions.

---

## TEST SUITE F — Launch Blockers

### F1: No TODO/FIXME/HACK in Production Code
Search `code_graph.py` and `server.py` for `TODO`, `FIXME`, `HACK`, `XXX`. Any found in production code is a launch blocker.

### F2: No Debug Print Statements
Verify `code_graph.py` has no stray `print()` calls except in `build()` where it prints warnings for unparseable files. Verify `server.py` only prints during auto-load (startup message).

### F3: LICENSE File Present
Verify `LICENSE` exists at the repo root with MIT license text.

### F4: .gitignore Covers Common Artifacts
Verify `.gitignore` (if exists) covers: `__pycache__/`, `*.egg-info/`, `dist/`, `build/`, `.code_graph.db`, `node_modules/`, `.venv/`.

### F5: No Large Binary Files
Verify no `.db`, `.sqlite`, `.whl`, `.tar.gz`, or other binary files are committed to the repo (check git tracked files).

---

## OUTPUT FORMAT

```
=== GEMINI QA AGENT RESULTS ===

A1: PASS/FAIL — [reason if fail]
A2: PASS/FAIL — [reason if fail]
...
F5: PASS/FAIL — [reason if fail]

VERDICT: PASS or FAIL (A4, E3)
```
