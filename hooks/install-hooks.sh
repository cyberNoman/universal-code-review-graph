#!/bin/bash
# Install pre-commit hooks for this repository

echo "🔗 Installing pre-commit hooks..."

HOOKS_DIR=".git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "❌ Not a git repository or .git/hooks not found"
    exit 1
fi

# Copy pre-commit hook
cp hooks/pre-commit "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ Pre-commit hook installed!"
echo ""
echo "The hook will:"
echo "  - Check if code-graph is installed"
echo "  - Run impact analysis on staged files"
echo "  - Warn about affected dependencies"
echo ""
echo "To bypass: git commit --no-verify"
