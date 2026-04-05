#!/usr/bin/env python3
"""
Safe CLI wrapper for code_graph operations.
Called by the VS Code extension with --tool and --args-json flags.
Never uses string interpolation — all arguments come through JSON via stdin or --args-json.

Usage:
  python3 run_tool.py --tool build_graph --args-json '{"repo_path":"/some/path"}'
"""

import argparse
import json
import sys
import os

# Allow running from the bundled server/ directory
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

from code_graph import CodeGraph, GraphBuilder, Symbol, CallEdge


def load_graph_from_db(db_path: str) -> CodeGraph:
    graph = CodeGraph(db_path)
    graph.load_from_db()
    return graph


def tool_build_graph(args: dict) -> dict:
    repo_path = args["repo_path"]
    exclude_patterns = args.get("exclude_patterns", [])
    db_path = os.path.join(repo_path, ".code_graph.db")

    builder = GraphBuilder(
        repo_path=repo_path,
        db_path=db_path,
        exclude_patterns=exclude_patterns,
    )
    stats = builder.build()

    # Return top symbols for sidebar display
    graph = builder.graph
    symbols = [s.to_dict() for s in list(graph.symbols.values())[:100]]
    graph_stats = graph.get_stats()

    return {
        "status": "success",
        "stats": stats,
        "symbols": symbols,
        "graph_stats": graph_stats,
    }


def tool_review_changes(args: dict) -> dict:
    repo_path = args["repo_path"]
    db_path = os.path.join(repo_path, ".code_graph.db")
    graph = load_graph_from_db(db_path)

    result = graph.review_changes(
        changed_files=args["changed_files"],
        include_upstream=args.get("include_upstream", True),
        include_downstream=args.get("include_downstream", True),
        max_depth=args.get("max_depth", 3),
    )
    return {
        "changed_files": args["changed_files"],
        "impacted_symbols": result["symbols"],
        "total_impacted": result["total"],
        "upstream_count": len(result["upstream"]),
        "downstream_count": len(result["downstream"]),
        "files_to_review": list(set(result["files"])),
    }


def tool_get_impact(args: dict) -> dict:
    repo_path = args["repo_path"]
    db_path = os.path.join(repo_path, ".code_graph.db")
    graph = load_graph_from_db(db_path)
    return graph.get_impact(args["symbol"], max_depth=args.get("max_depth", 5))


def tool_search_symbols(args: dict) -> dict:
    repo_path = args["repo_path"]
    db_path = os.path.join(repo_path, ".code_graph.db")
    graph = load_graph_from_db(db_path)
    symbols = graph.search_symbols(
        query=args["query"],
        symbol_type=args.get("symbol_type", "any"),
        limit=args.get("limit", 20),
    )
    return {"query": args["query"], "matches_found": len(symbols), "symbols": symbols}


def tool_get_stats(args: dict) -> dict:
    repo_path = args["repo_path"]
    db_path = os.path.join(repo_path, ".code_graph.db")
    graph = load_graph_from_db(db_path)
    return graph.get_stats()


TOOLS = {
    "build_graph": tool_build_graph,
    "review_changes": tool_review_changes,
    "get_impact": tool_get_impact,
    "search_symbols": tool_search_symbols,
    "get_stats": tool_get_stats,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", required=True, help="Tool name")
    parser.add_argument("--args-json", required=True, help="JSON-encoded arguments")
    parsed = parser.parse_args()

    tool_fn = TOOLS.get(parsed.tool)
    if not tool_fn:
        print(json.dumps({"error": f"Unknown tool: {parsed.tool}"}))
        sys.exit(1)

    try:
        args = json.loads(parsed.args_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON args: {e}"}))
        sys.exit(1)

    try:
        result = tool_fn(args)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
