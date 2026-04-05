# Developer Guide

Everything you need to set up, run, test, and extend `universal-code-review-graph`.

---

## Local development setup

### Prerequisites

- Python 3.9+
- Node.js 18+ (for VS Code extension only)
- Git

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/universal-code-review-graph.git
cd universal-code-review-graph/universal-code-graph
pip install -r requirements.txt
```

### 2. Verify the install

```bash
python3 -c "import mcp, tree_sitter, networkx; print('All dependencies OK')"
```

### 3. Test against a real repo

```bash
# Index this repo itself
python3 - << 'EOF'
from code_graph import GraphBuilder
builder = GraphBuilder(repo_path=".")
stats = builder.build()
print(stats)
print("Stats:", builder.graph.get_stats())
EOF
```

Expected output:
```
{'files_processed': 2, 'symbols_found': 35+, 'edges_found': 40+, 'repo_path': '...'}
Stats: {'total_symbols': 35, 'total_edges': 40, ...}
```

---

## Running the MCP server manually

```bash
cd universal-code-graph
python3 server.py
```

The server starts and listens on stdin/stdout.
To test it interactively, you can send raw JSON-RPC:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 server.py
```

---

## Using with Claude Code (development)

```bash
# Add the local server to Claude Code
claude mcp add code-graph python3 $(pwd)/universal-code-graph/server.py

# Verify it's listed
claude mcp list

# Test it
claude
> Build the code graph for /path/to/any/repo
```

---

## Using with Cursor (development)

Edit `~/.cursor/mcp.json`:

```json
{
  "servers": {
    "code-graph-dev": {
      "command": "python3",
      "args": ["/path/to/universal-code-review-graph/universal-code-graph/server.py"],
      "type": "stdio"
    }
  }
}
```

Restart Cursor. The tools will appear in the AI's tool list.

---

## Testing

### Run the test suite

```bash
cd universal-code-graph
python3 -m pytest tests/ -v
```

### Test a specific language parser

```bash
python3 - << 'EOF'
from code_graph import GraphBuilder
from pathlib import Path

# Create a temp test file
Path("/tmp/test_parser.py").write_text("""
class MyClass:
    def method_a(self):
        self.method_b()

    def method_b(self):
        pass

def standalone():
    obj = MyClass()
    obj.method_a()
""")

builder = GraphBuilder(repo_path="/tmp")
stats = builder.build()

graph = builder.graph
print("Symbols:", list(graph.symbols.keys()))
print("Edges:", list(graph.graph.edges()))
print("Impact of method_b:", graph.get_impact("method_b"))
EOF
```

Expected output:
```
Symbols: ['test_parser.py::MyClass', 'test_parser.py::MyClass.method_a', ...]
Edges: [('test_parser.py::MyClass.method_a', 'test_parser.py::MyClass.method_b'), ...]
Impact of method_b: {'upstream': ['MyClass.method_a', 'standalone'], ...}
```

### Test the review_changes blast radius

```bash
python3 - << 'EOF'
from code_graph import GraphBuilder

builder = GraphBuilder(repo_path="/path/to/your/repo")
builder.build()

result = builder.graph.review_changes(
    changed_files=["src/parser.py"],
    max_depth=3
)
print(f"Changed: 1 file → Need to review: {len(result['files'])} files")
print(f"Impacted symbols: {result['total']}")
print(f"Files: {result['files']}")
EOF
```

---

## Common issues

### `ImportError: No module named 'tree_sitter_python'`

```bash
pip install tree-sitter-python tree-sitter-javascript tree-sitter-go
```

### `ImportError: No module named 'mcp'`

```bash
pip install mcp
```

### Graph builds but shows 0 edges for JS/TS

Make sure you're using tree-sitter >= 0.25.0:
```bash
pip install --upgrade tree-sitter
```

### Symbols from test files are included

Add test exclusions when calling `build_graph`:
```
Build the graph for /my/repo, excluding **/tests/**, **/__tests__/**, **/*.test.ts
```

Or set `exclude_patterns` in the tool call.

### MCP server not found by AI assistant

Make sure you're using the **absolute path** in your MCP config, not a relative path:
```json
"args": ["/home/me/universal-code-review-graph/universal-code-graph/server.py"]
```

---

## Building the VS Code extension

### Prerequisites

```bash
npm install -g @vscode/vsce
```

### Development build

```bash
cd vscode-code-graph
npm install
npm run compile
```

### Run in VS Code debug mode

1. Open `vscode-code-graph/` in VS Code
2. Press `F5` — this opens a new VS Code window with the extension loaded
3. Open any folder and press `Ctrl+Shift+G` to build the graph

### Package as .vsix

```bash
cd vscode-code-graph
npm run package
vsce package
# Creates: universal-code-graph-1.0.0.vsix
```

### Install locally

```bash
code --install-extension universal-code-graph-1.0.0.vsix
```

---

## Project conventions

### Python

- Type hints on all public methods
- Dataclasses for data transfer objects (`Symbol`, `CallEdge`)
- No global mutable state in `code_graph.py` (only in `server.py`)
- All file paths stored as strings (relative to repo root, forward slashes)

### TypeScript

- Strict mode enabled
- No `any` on public method signatures
- All Python subprocess calls go through `MCPServerManager.runTool()` — never raw `exec` with string interpolation

### Naming

- Symbol keys: `"src/file.py::ClassName.method_name"`
- Short names: `"ClassName.method_name"` or `"method_name"`
- Tool names: `snake_case` (MCP convention)
- VS Code commands: `codeGraph.camelCase` (VS Code convention)

---

## Release process

1. Bump version in `universal-code-graph/setup.py` and `vscode-code-graph/package.json`
2. Update `CHANGELOG.md`
3. Tag the release: `git tag v1.1.0 && git push --tags`
4. GitHub Actions will run tests automatically on push
5. To publish to PyPI: `python setup.py sdist bdist_wheel && twine upload dist/*`
6. To publish to VS Code Marketplace: `vsce publish`
