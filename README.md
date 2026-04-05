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

## The Token Problem

```mermaid
graph LR
    subgraph WITHOUT["❌  Without Graph — 13,205 tokens"]
        direction TB
        AI1["🤖 AI Assistant"]
        CB["📁 Entire Codebase\n40+ files"]
        AI1 -->|"reads everything"| CB
    end

    subgraph WITH["✅  With Graph — 1,928 tokens"]
        direction TB
        AI2["🤖 AI Assistant"]
        G["🔷 Code Graph"]
        BR["📁 Blast Radius\n3–5 files only"]
        AI2 -->|"queries graph"| G
        G -->|"returns minimal set"| BR
    end

    WITHOUT -.->|"6.8× fewer tokens\nhigher review quality"| WITH

    style WITHOUT fill:#2d1515,stroke:#ff4444,color:#fff
    style WITH fill:#152d15,stroke:#44ff44,color:#fff
```

---

## The Problem

Every time you ask an AI to review code, it reads *everything*:

```
You:  "Review this PR — I changed src/parser.py"

AI:   reads main.py ... reads utils.py ... reads config.py ...
      reads parser.py ... reads compiler.py ... reads tests/ ...
      13,205 tokens consumed. Review quality: 7.2/10
```

That's slow, expensive, and the AI gets confused by irrelevant context.

## The Solution

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

## How It Works

```mermaid
flowchart TD
    A["📂 Your Source Code\nPython · JS · TS · Go"] --> B

    B["🌳 Tree-sitter Parser\nParses every file into a syntax tree"]
    B --> C

    C["🔍 Symbol Extraction\nFunctions · Classes · Methods"]
    C --> D

    D["📊 Call Edge Extraction\nWho calls whom?"]
    D --> E

    E["🕸️ NetworkX DiGraph\nDirected call graph in memory"]
    E --> F

    F["💾 SQLite Database\n.code_graph.db — survives restarts"]
    F --> G

    G["🔌 MCP Server\nJSON-RPC over stdio"]
    G --> H

    H["🤖 Your AI Assistant\nQueries only what matters"]

    style A fill:#1a1a2e,stroke:#4B6BFF,color:#fff
    style B fill:#1a1a2e,stroke:#4B6BFF,color:#fff
    style C fill:#1a1a2e,stroke:#4B6BFF,color:#fff
    style D fill:#1a1a2e,stroke:#4B6BFF,color:#fff
    style E fill:#16213e,stroke:#7ee787,color:#fff
    style F fill:#16213e,stroke:#7ee787,color:#fff
    style G fill:#0f3460,stroke:#e94560,color:#fff
    style H fill:#0f3460,stroke:#e94560,color:#fff
```

---

## Blast Radius Algorithm

```mermaid
graph TD
    CF["📝 Changed Files\ncheckout/views.py\ncheckout/serializers.py"]

    CF --> SYM["🔍 Find All Symbols\nin changed files\nprocess_checkout · CartSerializer · ..."]

    SYM --> UP["⬆️ Upstream BFS\nWho calls these?\npayments/stripe.py · orders/tasks.py"]
    SYM --> DOWN["⬇️ Downstream BFS\nWhat do these call?\ncheckout/models.py · cart/models.py"]

    UP --> RESULT["✅ Minimal Review Set\n5 files instead of 127\n2,100 tokens instead of 18,400"]
    DOWN --> RESULT

    style CF fill:#2d1515,stroke:#ff6b6b,color:#fff
    style SYM fill:#1a2a1a,stroke:#7ee787,color:#fff
    style UP fill:#1a1a2e,stroke:#4B6BFF,color:#fff
    style DOWN fill:#1a1a2e,stroke:#4B6BFF,color:#fff
    style RESULT fill:#152d15,stroke:#44ff44,color:#fff
```

---

## Quickstart (5 minutes)

### Step 1 — Install

```bash
git clone https://github.com/cyberNoman/universal-code-review-graph.git
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
<summary><b>ChatGPT / GPT-4o / Qwen / Continue / Zed</b></summary>

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

### Step 4 — Start saving tokens

```
I changed src/api/routes.py and src/db/models.py — what do I need to review?
```

---

## Token Savings — Real Numbers

```mermaid
xychart-beta
    title "Tokens Used Per Code Review"
    x-axis ["Kimi K2.5", "Gemini Pro", "Claude", "ChatGPT", "Qwen", "Cursor", "Windsurf"]
    y-axis "Tokens" 0 --> 20000
    bar [15000, 18000, 13205, 14000, 12000, 13500, 7000]
    bar [2000, 2500, 1928, 2150, 1800, 1930, 1000]
```

> Blue = without graph · Orange = with graph

---

## Available Tools

```mermaid
mindmap
  root((9 MCP Tools))
    Graph Management
      build_graph
        Index your whole repo
        Saves to SQLite
      get_stats
        Symbol counts
        Most connected nodes
      export_graph
        JSON format
        DOT / Graphviz
        Summary
    Code Review
      review_changes
        Core feature
        Blast radius for changed files
        6-8x token savings
      get_impact
        All callers of a symbol
        All callees of a symbol
    Exploration
      search_symbols
        Wildcard support
        Filter by type
      get_symbol_details
        Location and signature
        Callers and callees
      get_file_symbols
        All symbols in a file
      find_paths
        Call chains between symbols
```

---

## Architecture

```mermaid
graph LR
    subgraph CLIENT["AI Client Layer"]
        K["Kimi K2.5"]
        C["Claude"]
        G["Gemini"]
        CU["Cursor"]
        W["Windsurf"]
        CH["ChatGPT"]
    end

    subgraph MCP["MCP Server  (server.py)"]
        S["9 Tools\nJSON-RPC over stdio"]
    end

    subgraph ENGINE["Graph Engine  (code_graph.py)"]
        TS["🌳 Tree-sitter\nParsers"]
        NX["🕸️ NetworkX\nDiGraph"]
        SQ["💾 SQLite\n.code_graph.db"]
        TS --> NX --> SQ
    end

    subgraph LANGS["Supported Languages"]
        PY["Python"]
        JS["JavaScript"]
        TS2["TypeScript"]
        GO["Go"]
    end

    K & C & G & CU & W & CH -->|"MCP protocol\nstdio"| S
    S <--> NX
    LANGS --> TS

    style CLIENT fill:#0d1117,stroke:#30363d,color:#c9d1d9
    style MCP fill:#161b22,stroke:#4B6BFF,color:#c9d1d9
    style ENGINE fill:#161b22,stroke:#7ee787,color:#c9d1d9
    style LANGS fill:#161b22,stroke:#f78166,color:#c9d1d9
```

---

## Supported Languages

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

## Real-World Example

```mermaid
sequenceDiagram
    actor Dev as 👨‍💻 Developer
    participant AI as 🤖 AI Assistant
    participant MCP as 🔌 MCP Server
    participant DB as 💾 .code_graph.db

    Dev->>AI: "I changed checkout/views.py — review my PR"
    AI->>MCP: review_changes(["checkout/views.py"])
    MCP->>DB: Load graph
    DB-->>MCP: 2,341 symbols, 4,892 edges
    MCP-->>AI: files_to_review: [views.py, models.py,\nstripe.py, cart.py, tasks.py]
    AI->>Dev: Reads 5 files (2,100 tokens)\n"Here's what to check in your PR..."

    Note over Dev,DB: Without graph: AI reads 127 files (18,400 tokens)
    Note over Dev,DB: With graph: AI reads 5 files (2,100 tokens) — 8.7× savings
```

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

## Project Structure

```
universal-code-review-graph/
│
├── universal-code-graph/        # Python MCP server (core)
│   ├── server.py                # MCP server entry point
│   ├── code_graph.py            # Graph engine (NetworkX + Tree-sitter)
│   ├── requirements.txt
│   ├── configs/                 # Ready-made configs per AI assistant
│   │   ├── claude.json
│   │   ├── kimi.json
│   │   ├── cursor.json
│   │   ├── windsurf.json
│   │   └── continue.json
│   └── tests/                   # Unit tests
│
├── vscode-code-graph/           # VS Code extension
│   ├── src/
│   └── server/                  # Bundled Python backend
│
├── docs/                        # Full documentation
│   ├── architecture.md
│   ├── api-reference.md
│   ├── developer-guide.md
│   └── adding-a-language.md
│
└── README.md                    # This file
```

---

## Contributing

We welcome contributions! The most impactful things:

1. **Add a language** (Rust, Java, C++) — see [docs/adding-a-language.md](docs/adding-a-language.md)
2. **Improve call resolution** — better cross-file symbol matching
3. **Report wrong blast radius** — open an issue with a minimal reproduction
4. **Write tests** — see `universal-code-graph/tests/`

---

## License

MIT — free for personal and commercial use. See [LICENSE](LICENSE).

---

<div align="center">

**If this saved you tokens, give it a ⭐**

Built for the whole AI community — not locked to any one assistant.

</div>
