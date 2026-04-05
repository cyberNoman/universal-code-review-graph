# Architecture

This document explains how `universal-code-review-graph` is built internally.

---

## Overview

The system has three layers:

```
┌──────────────────────────────────┐
│   AI Assistant (any MCP client)  │
│   Kimi / Claude / Cursor / etc.  │
└──────────────┬───────────────────┘
               │ JSON-RPC over stdio (MCP protocol)
               ▼
┌──────────────────────────────────┐
│   MCP Server  (server.py)        │
│   9 tools, stateful              │
└──────────────┬───────────────────┘
               │ Python API calls
               ▼
┌──────────────────────────────────┐
│   Graph Engine (code_graph.py)   │
│   CodeGraph + GraphBuilder       │
└──────────────┬───────────────────┘
               │ SQLite read/write
               ▼
┌──────────────────────────────────┐
│   .code_graph.db                 │
│   symbols + calls tables         │
└──────────────────────────────────┘
```

---

## Core classes

### `Symbol` (dataclass)

Every indexed code entity — function, class, method — becomes a `Symbol`:

```python
@dataclass
class Symbol:
    name: str        # Unique key: "src/parser.py::MyClass.parse"
    short_name: str  # Human-readable: "MyClass.parse"
    symbol_type: str # function | class | method | import
    file_path: str   # "src/parser.py" (relative to repo root)
    line_start: int
    line_end: int
    parent: str      # Parent class name, if any
```

**Key design:** `name` is namespaced as `file_path::qualified_name`.
This prevents collisions between two files that both define a function called `parse()`.

---

### `CallEdge` (dataclass)

A directed relationship between two symbols:

```python
@dataclass
class CallEdge:
    caller: str    # "src/compiler.py::compile_ast"
    callee: str    # "src/parser.py::MyClass.parse"
    call_type: str # direct_call | import | inheritance
    file_path: str
    line: int
```

---

### `CodeGraph`

The in-memory graph. Wraps a `networkx.DiGraph`:

```
Nodes = Symbols
Edges = CallEdges (directed: caller → callee)
```

Key methods:

| Method | Algorithm | Complexity |
|--------|-----------|-----------|
| `get_upstream(sym, depth)` | BFS on predecessors | O(V + E) |
| `get_downstream(sym, depth)` | BFS on successors | O(V + E) |
| `find_paths(src, tgt)` | `nx.all_simple_paths` | O(V! / (V-k)!) worst case |
| `review_changes(files)` | Union of upstream+downstream for all file symbols | O(n × (V+E)) |
| `search_symbols(query)` | Regex scan | O(V) |

Short-name index (`_short_name_index`) maps `"parse"` → `["src/parser.py::parse", "src/lexer.py::parse"]`
for best-effort call resolution across files.

---

### `GraphBuilder`

Walks the repo, parses every source file with Tree-sitter, builds the graph.

**Build pipeline for one file:**

```
file.py
  ↓  open + read bytes
Tree-sitter parser (language-specific)
  ↓  parse() → CST (concrete syntax tree)
_parse_python() / _parse_js() / _parse_go()
  ↓  walk CST nodes
List[Symbol] + List[CallEdge]
  ↓  graph.add_symbol() / graph.add_call()
CodeGraph (in-memory)
  ↓  save_to_db()
.code_graph.db
```

---

## Language parsers

Each language has two methods:
- `_parse_<lang>()` — walks the CST to extract symbols
- `_collect_<lang>_calls()` — recursively finds call nodes within a function body

### Python

Tree-sitter node types used:
- `function_definition` → `Symbol(type=function|method)`
- `class_definition` → `Symbol(type=class)`
- `call` → `CallEdge`

Class body is visited separately from the top-level to avoid double-registering symbols.

### JavaScript / TypeScript

Tree-sitter node types used:
- `function_declaration` → `Symbol(type=function)`
- `method_definition` → `Symbol(type=method)`
- `class_declaration` / `class` → `Symbol(type=class)`
- `variable_declarator` with `arrow_function` or `function` value → `Symbol(type=function)`
- `call_expression` → `CallEdge`

### Go

Tree-sitter node types used:
- `function_declaration` → `Symbol(type=function)`
- `method_declaration` → `Symbol(type=method)` with receiver type extracted
- `type_declaration` → `Symbol(type=class)` (structs/interfaces)
- `call_expression` → `CallEdge`

---

## Call resolution

When `compile_ast()` calls `parse()`, the edge is recorded as:
```
caller = "src/compiler.py::compile_ast"
callee = "src/parser.py::MyClass.parse"   ← resolved via short_name_index
```

Resolution is best-effort:
1. If `parse` resolves to exactly one symbol in the index → use its full key
2. If multiple matches → use the first match (same-file preference is a planned improvement)
3. If no match → store the bare name as the callee node (still useful for path finding)

---

## Persistence

Graph is saved to SQLite after every `build_graph` call:

```sql
CREATE TABLE symbols (
    name TEXT PRIMARY KEY,   -- "src/parser.py::MyClass.parse"
    short_name TEXT,
    symbol_type TEXT,
    file_path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    column_start INTEGER,
    column_end INTEGER,
    parent TEXT
);

CREATE TABLE calls (
    caller TEXT,
    callee TEXT,
    call_type TEXT,
    file_path TEXT,
    line INTEGER,
    PRIMARY KEY (caller, callee, line)
);
```

On MCP server startup, `_try_load_existing_graph()` searches for `.code_graph.db`
in the working directory and loads it automatically — no re-indexing needed.

---

## MCP protocol

The server speaks [Model Context Protocol](https://modelcontextprotocol.io/) over stdin/stdout.
This is JSON-RPC 2.0:

```json
// AI sends:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "review_changes",
    "arguments": {
      "changed_files": ["src/parser.py"],
      "max_depth": 3
    }
  }
}

// Server responds:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{
      "type": "text",
      "text": "{ \"files_to_review\": [...], \"total_impacted\": 7 }"
    }]
  }
}
```

Any AI that implements the MCP client spec can use this server without modification.

---

## Security model

**No shell injection.** The VS Code extension does NOT construct Python code as strings.
Instead it uses:

```
python3 run_tool.py --tool build_graph --args-json '{"repo_path": "..."}'
```

Arguments are array elements passed to `spawn()` — they cannot break out into shell commands
regardless of what the repo path or symbol name contains.

---

## Performance characteristics

| Repo size | Index time | DB size | Query time |
|---|---|---|---|
| ~100 files | < 5 sec | ~200 KB | < 50 ms |
| ~500 files | ~20 sec | ~1 MB | < 100 ms |
| ~2000 files | ~90 sec | ~4 MB | < 300 ms |

Memory: approximately 50 bytes per symbol + 30 bytes per edge.
A 2000-file Python codebase with ~10,000 symbols uses ~1-2 MB of RAM.
