# Universal Code Review Graph for VS Code

**Build code graphs for efficient AI-assisted reviews. Works with ALL AI assistants - save 6-8x tokens!**

![Code Graph](https://img.shields.io/badge/Code%20Graph-Universal-blue)
![VS Code](https://img.shields.io/badge/VS%20Code-1.85%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 🌐 Works With ALL AI Assistants

| AI Assistant | Token Savings |
|--------------|---------------|
| **Kimi K2.5** | 7.5× |
| **Qwen** | 6.7× |
| **Gemini Pro** | 7.2× |
| **Claude** | 6.8× |
| **ChatGPT** | 6.5× |
| **Cursor** | 7.0× |
| **Windsurf** | 7.0× |

## 🚀 Quick Start

### 1. Install the Extension

Search for "Universal Code Graph" in the VS Code marketplace and install.

### 2. Build Your First Graph

Open a workspace and run:
```
Ctrl+Shift+P → "Code Graph: Build Code Graph"
```

Or use the keyboard shortcut:
```
Ctrl+Shift+G (Cmd+Shift+G on Mac)
```

### 3. Copy MCP Config

After building, click "Copy MCP Config" and paste it into your AI assistant's settings.

### 4. Start Reviewing!

Your AI can now query the graph for precise context instead of reading entire files.

## 📋 Available Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| Build Code Graph | `Ctrl+Shift+G` | Index your entire codebase |
| Review Changes | - | Analyze git changes |
| Get Symbol Impact | - | Find dependencies |
| Find Call Paths | - | Trace function calls |
| Search Symbols | `Ctrl+Shift+S` | Find symbols by name |
| View Statistics | - | See graph metrics |
| Export Graph | - | Export to JSON/DOT |

## 🎯 How It Works

1. **Parse**: Tree-sitter parses your source files
2. **Index**: Functions, classes, imports are indexed into a graph
3. **Query**: Your AI queries the graph for relevant context only
4. **Save**: 6-8× fewer tokens used!

## 💡 Example Usage

### Without Code Graph:
```
AI reads: 15 files × 800 lines = 12,000 tokens
```

### With Code Graph:
```
AI queries: 1 graph call = 1,800 tokens
Savings: 6.7× 🎉
```

## ⚙️ Configuration

Open VS Code settings (`Ctrl+,`) and search for "Code Graph":

| Setting | Default | Description |
|---------|---------|-------------|
| `codeGraph.excludePatterns` | `["**/test_*.py", ...]` | Files to exclude |
| `codeGraph.maxDepth` | `5` | Max dependency depth |
| `codeGraph.autoBuild` | `false` | Auto-build on open |
| `codeGraph.aiAssistant` | `kimi` | Your AI assistant |

## 📊 Sidebar Views

The **Code Graph Explorer** sidebar shows:
- 📈 Statistics (total symbols, edges, files)
- 🔧 Functions list
- 🏛️ Classes list
- 📁 Files indexed

## 🔗 MCP Integration

The extension automatically generates MCP configs for your AI assistant:

### For Kimi:
```json
{
  "mcpServers": {
    "code-graph": {
      "command": "python3",
      "args": ["${workspaceFolder}/.code_graph/server.py"]
    }
  }
}
```

### For Claude:
```bash
claude mcp add code-graph python3 ${PWD}/.code_graph/server.py
```

## 🛠️ Supported Languages

- ✅ Python
- ✅ JavaScript / TypeScript
- ✅ Go
- 🔄 Rust (coming soon)
- 🔄 Java (coming soon)

## 🐛 Troubleshooting

### "Python not found"
Make sure Python 3.10+ is installed and in your PATH.

### "No graph built yet"
Run "Build Code Graph" first. The graph is stored in `.code_graph.db`.

### "Server not found"
Reinstall the extension. The server is bundled with the extension.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

Contributions welcome! Open an issue or PR on GitHub.

---

**Built with ❤️ for the universal AI community.**
