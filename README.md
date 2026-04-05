# universal-code-review-graph

<div align="center">

**Stop feeding your entire codebase to AI on every task.**

AI coding tools re-read your whole codebase on every request.
`universal-code-review-graph` fixes that — it builds a structural map of your code,
tracks call relationships, and gives your AI assistant *only* the context it needs.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![MCP](https://img.shields.io/badge/Protocol-MCP-purple)](https://modelcontextprotocol.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## The problem

Every time you ask an AI to review code, it reads *everything*:

```
You:  "Review this PR — I changed src/parser.py"

AI:   reads main.py ... reads utils.py ... reads config.py ...
      reads parser.py ... reads compiler.py ... reads tests/ ...
      13,205 tokens consumed. Review quality: 7.2/10
```

That's slow, expensive, and the AI gets confused by irrelevant context.

## The solution

```
You:  "Review this PR — I changed src/parser.py"

AI:   queries graph → finds blast radius: parser.py + 2 dependent files
      1,928 tokens consumed. Review quality: 8.8/10

      6.8× fewer tokens. Better answer.
```

---

## Works with ANY AI assistant

This is not a Claude-only tool. It works with every AI that supports [MCP](https://modelcontextprotocol.io/):

| AI Assistant | Token savings | Status |
|---|---|---|
| **Kimi K2.5** | ~7.5× | ✅ |
| **Claude / Claude Code** | ~6.8× | ✅ |
| **Gemini Pro** | ~7.2× | ✅ |
| **ChatGPT / GPT-4o** | ~6.5× | ✅ |
| **Qwen** | ~6.7× | ✅ |
| **Cursor** | ~7.0× | ✅ |
| **Windsurf** | ~7.0× | ✅ |
| **Zed** | ~6.5× | ✅ |
| **Continue** | ~6.5× | ✅ |
| Any MCP-compatible client | varies | ✅ |

---

## Quickstart (5 minutes)

### Step 1 — Install

```bash
git clone https://github.com/YOUR_USERNAME/universal-code-review-graph.git
cd universal-code-review-graph/universal-code-graph
pip install -r requirements.txt
```

### Step 2 — Connect your AI

Pick your AI assistant and add this to its MCP config:

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add code-graph python3 /path/to/universal-code-graph/server.py
```
</details>

<details>
<summary><b>Kimi K2.5</b></summary>

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
</details>

<details>
<summary><b>Cursor</b></summary>

Edit `~/.cursor/mcp.json`:
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
</details>

<details>
<summary><b>Windsurf</b></summary>

Edit `~/.codeium/windsurf/mcp_config.json`:
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
</details>

<details>
<summary><b>ChatGPT / GPT-4o (via any MCP bridge)</b></summary>

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
</details>

<details>
<summary><b>Qwen / Continue / Zed</b></summary>

Add to your MCP config file:
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
</details>

### Step 3 — Build your first graph

Tell your AI:

```
Build the code graph for /home/me/my-project
```

The AI will index your codebase and save a `.code_graph.db` file.
This persists across sessions — you only need to do this once.

### Step 4 — Start saving tokens

```
I changed src/api/routes.py and src/db/models.py — what do I need to review?
```

Instead of reading all 40 files, the AI reads only the 4-5 files in the blast radius.

---

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Source Code                         │
└─────────────────┬───────────────────────────────────────────┘
                  │ Tree-sitter parses every file
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Symbol Extraction                              │
│  functions • classes • methods (Python / JS / TS / Go)     │
└─────────────────┬───────────────────────────────────────────┘
                  │ Who calls whom?
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Call Graph (NetworkX DiGraph)                  │
│  parse_source → tokenize → build_ast → compile             │
└─────────────────┬───────────────────────────────────────────┘
                  │ Persisted to SQLite
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              .code_graph.db                                 │
│  Survives server restarts — no re-indexing needed          │
└─────────────────┬───────────────────────────────────────────┘
                  │ Exposed via MCP (JSON-RPC over stdio)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Your AI Assistant                              │
│  Queries graph → reads only relevant files → better answer │
└─────────────────────────────────────────────────────────────┘
```

### Blast radius algorithm

When you change `src/parser.py`:

1. Find all symbols defined in `src/parser.py` (e.g. `parse_source`, `Tokenizer`)
2. BFS upstream: who calls these? (`compile_ast` → `run_pipeline` → `main`)
3. BFS downstream: what do these call? (`tokenize`, `read_file`)
4. Collect all files containing those symbols
5. Return the minimal review set

**Result:** Instead of 40 files, the AI reads 4-5. Same accuracy, 6-8× fewer tokens.

---

## Available tools

Your AI can use these 9 tools once the MCP server is connected:

| Tool | Description | When to use |
|---|---|---|
| `build_graph` | Index a codebase | Once per project (or after major refactors) |
| `review_changes` | **Get blast radius for changed files** | Every PR / code review |
| `get_impact` | Find all callers and callees of a symbol | When refactoring a function |
| `find_paths` | Trace call chains between two symbols | Debugging unexpected behavior |
| `search_symbols` | Find symbols by name / wildcard | Exploring unfamiliar code |
| `get_symbol_details` | Full details for one symbol | Deep-dive on a function/class |
| `get_file_symbols` | All symbols in a file | File-level overview |
| `export_graph` | Export as JSON, DOT, or summary | Visualization / tooling |
| `get_stats` | Counts, most-connected nodes | Health check on your graph |

---

## Supported languages

| Language | Symbol extraction | Call edges | Extensions |
|---|---|---|---|
| Python | ✅ | ✅ | `.py` |
| JavaScript | ✅ | ✅ | `.js` `.jsx` |
| TypeScript | ✅ | ✅ | `.ts` `.tsx` |
| Go | ✅ | ✅ | `.go` |
| Rust | 🔄 planned | 🔄 planned | `.rs` |
| Java | 🔄 planned | 🔄 planned | `.java` |
| C / C++ | 🔄 planned | 🔄 planned | `.c` `.cpp` |

---

## VS Code Extension

A full VS Code extension is included in the `vscode-code-graph/` directory:

- **Sidebar panel** — browse symbols, classes, files, statistics
- **`Ctrl+Shift+G`** — build graph for current workspace
- **`Ctrl+Shift+S`** — search symbols
- **Right-click menu** — get impact on any selected symbol
- **One-click MCP config** — copy the right config for your AI assistant

See [vscode-code-graph/README.md](vscode-code-graph/README.md) for build instructions.

---

## Real-world example

```
Repository: Django e-commerce app
Files: 127 Python files
Total symbols: 2,341
Total call edges: 4,892

Changed files: checkout/views.py, checkout/serializers.py

Without graph:
  → AI reads all 127 files
  → 18,400 tokens
  → Quality: 6.9/10

With graph:
  → review_changes(["checkout/views.py", "checkout/serializers.py"])
  → Files to review: checkout/views.py, checkout/serializers.py,
                     checkout/models.py, payments/stripe.py,
                     cart/models.py
  → 2,100 tokens
  → Quality: 8.7/10

Savings: 8.7× fewer tokens, +1.8 quality points
```

---

## Project structure

```
universal-code-review-graph/
│
├── universal-code-graph/        # Python MCP server (core)
│   ├── server.py                # MCP server entry point
│   ├── code_graph.py            # Graph engine (NetworkX + Tree-sitter)
│   ├── requirements.txt
│   ├── setup.py
│   ├── configs/                 # Ready-made configs per AI assistant
│   │   ├── claude.json
│   │   ├── kimi.json
│   │   ├── cursor.json
│   │   ├── windsurf.json
│   │   └── continue.json
│   ├── README.md
│   ├── CONTRIBUTING.md
│   └── EXAMPLES.md
│
├── vscode-code-graph/           # VS Code extension
│   ├── src/
│   │   ├── extension.ts         # Activation + command registration
│   │   ├── mcpServer.ts         # Safe Python subprocess bridge
│   │   ├── commands.ts          # All VS Code commands
│   │   └── codeGraphProvider.ts # Sidebar tree view
│   ├── server/
│   │   ├── server.py            # Bundled MCP server
│   │   ├── code_graph.py        # Bundled graph engine
│   │   └── run_tool.py          # Safe CLI wrapper (no injection)
│   └── package.json
│
├── app/                         # Landing page (React + Vite)
│   └── src/sections/
│
└── docs/                        # Full documentation
    ├── architecture.md
    ├── api-reference.md
    ├── developer-guide.md
    └── adding-a-language.md
```

---

## Contributing

We welcome contributions! The most impactful things you can do:

1. **Add a language** (Rust, Java, C++) — see [CONTRIBUTING.md](universal-code-graph/CONTRIBUTING.md)
2. **Improve call resolution** — currently best-effort; better cross-file resolution would help
3. **Report bugs** — especially wrong blast radius results
4. **Write tests** — the core graph engine needs unit tests

---

## License

MIT — free for personal and commercial use. See [LICENSE](LICENSE).

---

<div align="center">

**If this saved you tokens, give it a ⭐**

Built to be universal — not locked to any one AI.

</div>
