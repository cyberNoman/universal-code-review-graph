# Building the VS Code Extension

## Prerequisites

- Node.js 18+
- npm or yarn
- VS Code

## Build Steps

### 1. Install Dependencies

```bash
cd vscode-code-graph
npm install
```

### 2. Compile TypeScript

```bash
npm run compile
```

### 3. Package Extension

```bash
npm install -g vsce
vsce package
```

This creates a `.vsix` file that can be installed in VS Code.

### 4. Install in VS Code

```bash
code --install-extension universal-code-graph-1.0.0.vsix
```

Or drag the `.vsix` file into VS Code.

## Development

### Watch Mode

```bash
npm run watch
```

### Debug

Press F5 in VS Code to launch a new Extension Development Host.

## Publishing to Marketplace

1. Create a publisher account at https://marketplace.visualstudio.com/
2. Get a Personal Access Token
3. Login: `vsce login <publisher-name>`
4. Publish: `vsce publish`

## File Structure

```
vscode-code-graph/
├── src/
│   ├── extension.ts          # Main entry point
│   ├── codeGraphProvider.ts  # Tree view provider
│   ├── commands.ts           # Command handlers
│   └── mcpServer.ts          # MCP server wrapper
├── server/
│   ├── server.py             # MCP server
│   ├── code_graph.py         # Graph engine
│   └── requirements.txt      # Python deps
├── icons/
│   └── icon.png              # Extension icon
├── package.json              # Extension manifest
├── tsconfig.json             # TypeScript config
├── webpack.config.js         # Bundler config
└── README.md                 # Documentation
```

## Troubleshooting

### Build Errors

1. **TypeScript errors**: Run `npm run lint`
2. **Webpack errors**: Delete `dist/` and rebuild
3. **Missing dependencies**: Run `npm install`

### Runtime Errors

1. Check VS Code Developer Tools (Help > Toggle Developer Tools)
2. View Output panel > "Universal Code Graph"
3. Check Python is installed: `python3 --version`
