#!/bin/bash
# Universal Code Review Graph - Installation Script

set -e

echo "🚀 Installing Universal Code Review Graph..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📍 Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Make server executable
chmod +x server.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Configure your AI assistant:"
echo "   • Kimi: Add configs/kimi.json to your Kimi MCP settings"
echo "   • Claude: Run 'claude mcp add code-graph python3 $(pwd)/server.py'"
echo "   • Cursor: Add configs/cursor.json to ~/.cursor/mcp.json"
echo ""
echo "2. Start using it:"
echo "   'Build the code graph for /path/to/my/repo'"
echo ""
echo "📖 Full documentation: https://your-docs-url.com"
