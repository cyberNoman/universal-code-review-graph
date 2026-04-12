#!/usr/bin/env python3
"""
Universal Code Review Graph - Command Line Interface
Makes it easy to use without MCP server
"""

import argparse
import json
import sys
from pathlib import Path

from code_graph import CodeGraph, GraphBuilder


def cmd_build(args):
    """Build the code graph for a repository."""
    repo_path = Path(args.repo).resolve()
    
    if not repo_path.exists():
        print(f"❌ Error: Repository path does not exist: {repo_path}")
        return 1
    
    db_path = repo_path / ".code_graph.db"
    
    print(f"📊 Building code graph for: {repo_path}")
    print(f"   Database: {db_path}")
    print()
    
    builder = GraphBuilder(
        repo_path=str(repo_path),
        db_path=str(db_path),
        exclude_patterns=args.exclude or []
    )
    
    stats = builder.build()
    
    print(f"✅ Graph built successfully!")
    print(f"   Files indexed: {stats.get('files', 0)}")
    print(f"   Symbols: {stats.get('symbols', 0)}")
    print(f"   Call edges: {stats.get('calls', 0)}")
    
    return 0


def cmd_review(args):
    """Review changes and show impacted files."""
    repo_path = Path(args.repo).resolve()
    db_path = repo_path / ".code_graph.db"
    
    if not db_path.exists():
        print(f"❌ Error: No code graph found. Run 'code-graph build' first.")
        return 1
    
    graph = CodeGraph(str(db_path))
    if not graph.load_from_db():
        print(f"❌ Error: Failed to load code graph from {db_path}")
        return 1
    
    changed_files = args.files
    
    print(f"🔍 Analyzing impact of {len(changed_files)} changed file(s)...")
    print()
    
    result = graph.review_changes(
        changed_files=changed_files,
        include_upstream=args.upstream,
        include_downstream=args.downstream,
        max_depth=args.depth
    )
    
    print(f"📋 Results:")
    print(f"   Changed files: {len(changed_files)}")
    print(f"   Impacted symbols: {result['total']}")
    print(f"   Upstream dependencies: {len(result['upstream'])}")
    print(f"   Downstream dependencies: {len(result['downstream'])}")
    print()
    
    print(f"📁 Files to review ({len(result['files'])}):")
    for f in sorted(result['files']):
        prefix = "→ " if f in changed_files else "   "
        print(f"{prefix}{f}")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                'changed_files': changed_files,
                'impacted_symbols': result['symbols'],
                'files_to_review': list(result['files']),
                'upstream': result['upstream'],
                'downstream': result['downstream'],
                'total_impacted': result['total']
            }, f, indent=2)
        print()
        print(f"💾 Results saved to: {args.output}")
    
    return 0


def cmd_stats(args):
    """Show graph statistics."""
    repo_path = Path(args.repo).resolve()
    db_path = repo_path / ".code_graph.db"
    
    if not db_path.exists():
        print(f"❌ Error: No code graph found at {db_path}")
        print(f"   Run 'code-graph build' first.")
        return 1
    
    graph = CodeGraph(str(db_path))
    if not graph.load_from_db():
        print(f"❌ Error: Failed to load code graph")
        return 1
    
    stats = graph.get_stats()
    
    print(f"📊 Code Graph Statistics")
    print(f"   Repository: {repo_path}")
    print()
    print(f"   Total symbols: {stats.get('total_symbols', 0)}")
    print(f"   Total calls: {stats.get('total_calls', 0)}")
    print()
    print(f"   Symbol types:")
    for type_name, count in stats.get('by_type', {}).items():
        print(f"      {type_name}: {count}")
    
    if stats.get('most_connected'):
        print()
        print(f"   Most connected symbols:")
        for sym in stats['most_connected'][:5]:
            print(f"      {sym['name']} ({sym['connections']} connections)")
    
    return 0


def cmd_search(args):
    """Search for symbols."""
    repo_path = Path(args.repo).resolve()
    db_path = repo_path / ".code_graph.db"
    
    if not db_path.exists():
        print(f"❌ Error: No code graph found. Run 'code-graph build' first.")
        return 1
    
    graph = CodeGraph(str(db_path))
    graph.load_from_db()
    
    results = graph.search_symbols(
        query=args.query,
        symbol_type=args.type or 'any',
        limit=args.limit
    )
    
    print(f"🔍 Search results for '{args.query}':")
    print(f"   Found {len(results)} match(es)")
    print()
    
    for sym in results:
        print(f"   {sym['name']} ({sym['symbol_type']})")
        print(f"      File: {sym['file_path']}:{sym.get('line_start', '?')}")
        print()
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog='code-graph',
        description='Universal Code Review Graph - Analyze your codebase'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build code graph for repository')
    build_parser.add_argument('repo', nargs='?', default='.', help='Repository path (default: current directory)')
    build_parser.add_argument('--exclude', '-e', action='append', help='Patterns to exclude')
    
    # Review command
    review_parser = subparsers.add_parser('review', help='Review changes and show impact')
    review_parser.add_argument('files', nargs='+', help='Changed files to analyze')
    review_parser.add_argument('--repo', '-r', default='.', help='Repository path')
    review_parser.add_argument('--depth', '-d', type=int, default=3, help='Maximum traversal depth')
    review_parser.add_argument('--upstream', '-u', action='store_true', default=True, help='Include upstream')
    review_parser.add_argument('--no-upstream', dest='upstream', action='store_false', help='Exclude upstream')
    review_parser.add_argument('--downstream', action='store_true', default=True, help='Include downstream')
    review_parser.add_argument('--no-downstream', dest='downstream', action='store_false', help='Exclude downstream')
    review_parser.add_argument('--output', '-o', help='Output file (JSON)')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show graph statistics')
    stats_parser.add_argument('repo', nargs='?', default='.', help='Repository path')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for symbols')
    search_parser.add_argument('query', help='Search query (supports wildcards)')
    search_parser.add_argument('--repo', '-r', default='.', help='Repository path')
    search_parser.add_argument('--type', '-t', choices=['function', 'class', 'method', 'import', 'any'], default='any', help='Symbol type filter')
    search_parser.add_argument('--limit', '-l', type=int, default=20, help='Maximum results')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        'build': cmd_build,
        'review': cmd_review,
        'stats': cmd_stats,
        'search': cmd_search,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
