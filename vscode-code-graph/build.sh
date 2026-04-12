#!/bin/bash
# Build VS Code extension .vsix for manual installation
# Usage: ./build.sh

echo "📦 Building Universal Code Graph VS Code Extension..."

# Install dependencies
echo "📥 Installing dependencies..."
npm install

# Compile TypeScript
echo "🔨 Compiling TypeScript..."
npm run compile

# Install vsce if not present
if ! command -v vsce &> /dev/null; then
    echo "📥 Installing vsce..."
    npm install -g @vscode/vsce
fi

# Build .vsix package
echo "📦 Building .vsix package..."
vsce package --no-dependencies

echo ""
echo "✅ Build complete! Install with:"
echo "   code --install-extension universal-code-graph-*.vsix"
echo ""
