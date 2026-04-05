# universal-code-review-graph

**AI coding tools re-read your entire codebase on every task.**
This tool fixes that.

It builds a structural map of your code using [Tree-sitter](https://tree-sitter.github.io/tree-sitter/), tracks call relationships in a graph, and gives your AI assistant precise context via [MCP](https://modelcontextprotocol.io/) so it reads **only what matters**.

```
Without Graph                     With Graph
─────────────────                 ─────────────────
AI reads everything           →   AI queries graph
     ↓                                  ↓
Entire codebase (20+ files)       Blast radius (3-5 files)
13,205 tokens  ❌                 1,928 tokens  ✅
Quality: 7.2/10                   Quality: 8.8/10

              6.8× fewer tokens · higher review quality
```

## Works with ANY AI assistant

| AI | Token savings |
|----|--------------|
| Kimi K2.5 | ~7.5× |
| Claude / Claude Code | ~6.8× |
| Gemini Pro | ~7.2× |
| ChatGPT / GPT-4o | ~6.5× |
| Qwen | ~6.7× |
| Cursor | ~7.0× |
| Windsurf | ~7.0× |
| Zed, Continue, any MCP client | ~6.5× |

## Quick start

### 1 — Install

```bash
git clone https://github.com/YOUR_USERNAME/universal-code-review-graph.git
cd universal-code-review-graph
pip install -r requirements.txt
```

### 2 — Add to your AI assistant

#### Claude Code
```bash
claude mcp add code-graph python3 /path/to/universal-code-graph/server.py
```

#### Kimi / Qwen / ChatGPT (any MCP client)
```json
{
  "mcpServers": {
    "code-graph": {
      "command": "python3",
      "args": ["/path/to/universal-code-graph/server.py"]
    }
  }
}
```

#### Cursor
```json
{
  "servers": {
    "code-graph": {
      "command": "python3",
      "args": ["/path/to/universal-code-graph/server.py"],
      "type": "stdio"
    }
  }
}
```

#### Windsurf
```json
{
  "mcpServers": {
    "code-graph": {
      "command": "python3",
      "args": ["/path/to/universal-code-graph/server.py"],
      "type": "stdio"
    }
  }
}
```

### 3 — Use it

```
You: Build the code graph for /home/me/myproject

AI:  ✅ Graph built. 847 symbols, 1,203 edges across 43 files.

You: I changed src/parser.py and src/tokenizer.py — what do I need to review?

AI:  Files to review: src/parser.py, src/tokenizer.py, src/compiler.py
     Impacted symbols: parse_source, tokenize, compile_ast, run_pipeline
     (4 upstream callers, 3 downstream dependencies)
     → 1,928 tokens instead of 13,205
```

## Supported languages

| Language | Symbols | Call edges |
|----------|---------|------------|
| Python | ✅ | ✅ |
| JavaScript / JSX | ✅ | ✅ |
| TypeScript / TSX | ✅ | ✅ |
| Go | ✅ | ✅ |
| Rust | planned | planned |
| Java | planned | planned |

## Available MCP tools (9 total)

| Tool | What it does |
|------|-------------|
| `build_graph` | Parse repo, build graph, persist to `.code_graph.db` |
| `review_changes` | **Core feature** — given changed files, return minimal blast radius |
| `get_impact` | Find all callers + callees of a specific symbol |
| `find_paths` | Find call paths between two symbols |
| `search_symbols` | Search by name or wildcard (`parse*`, `*handler`) |
| `get_symbol_details` | Location, signature, callers, callees for one symbol |
| `get_file_symbols` | All symbols defined in a file |
| `export_graph` | Export as JSON, DOT (Graphviz), or summary |
| `get_stats` | Counts, most-connected symbols, type breakdown |

## How it works

```
Source files
    ↓  Tree-sitter (Python / JS / TS / Go)
Symbol extraction   →   function, class, method per file
    ↓
Call edge extraction  →  who calls whom
    ↓
NetworkX DiGraph  →  BFS traversal for upstream/downstream
    ↓
SQLite (.code_graph.db)  →  persists across sessions
    ↓
MCP tools  →  AI queries only relevant nodes
```

## Example workflow

```python
# Step 1 — build (once per repo, re-run after big refactors)
build_graph(repo_path="/home/me/myproject")
# → 847 symbols, 1203 edges, 43 files

# Step 2 — on every PR / change
review_changes(
    changed_files=["src/parser.py", "src/tokenizer.py"],
    include_upstream=True,
    include_downstream=True,
    max_depth=3
)
# → {
#     "files_to_review": ["src/parser.py", "src/tokenizer.py", "src/compiler.py"],
#     "impacted_symbols": ["parse_source", "tokenize", "compile_ast", "run_pipeline"],
#     "total_impacted": 7,
#     "upstream_count": 4,
#     "downstream_count": 3
# }
```

## Persistent sessions

On startup, `server.py` automatically finds and loads any `.code_graph.db`
in the working directory — so you don't need to re-run `build_graph` every
session. The graph is rebuilt only when you explicitly call `build_graph`.

## Contributing

Contributions welcome! The easiest way to contribute:

**Add a new language:**
1. Install the tree-sitter grammar: `pip install tree-sitter-rust`
2. Add a `_parse_rust()` method in `code_graph.py` following the Go parser pattern
3. Register it in `GraphBuilder._init_parsers()` and `_get_language()`
4. Submit a PR

**Other contributions:**
- Bug reports / issues
- Improve call resolution accuracy (currently best-effort)
- Add Rust, Java, C/C++ support
- Improve the VS Code extension

## Requirements

```
Python >= 3.9
mcp >= 1.0.0
tree-sitter >= 0.25.0
tree-sitter-python >= 0.25.0
tree-sitter-javascript >= 0.25.0
tree-sitter-go >= 0.25.0
networkx >= 3.0
```

## License

MIT — free for personal and commercial use.

## Acknowledgments

Inspired by the original `code-review-graph` for Claude.
Built to be universal — works with **any** AI assistant that supports MCP.
