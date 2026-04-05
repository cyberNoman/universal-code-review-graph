#!/usr/bin/env python3
"""
Universal Code Review Graph — MCP Server
Works with ALL AI assistants: Kimi K2.5, Qwen, Gemini, Claude, ChatGPT,
Cursor, Windsurf, Zed, Continue, and any MCP-compatible client.

Protocol: JSON-RPC 2.0 over stdio (MCP spec)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, LoggingLevel

from code_graph import CodeGraph, GraphBuilder


@dataclass
class ServerState:
    graph: Optional[CodeGraph] = None
    repo_path: Optional[str] = None
    db_path: str = field(default=".code_graph.db")


state = ServerState()
app = Server("universal-code-review-graph")


def _require_graph() -> Optional[str]:
    """Return an error JSON string if no graph is loaded, else None."""
    if not state.graph or len(state.graph.symbols) == 0:
        return json.dumps({
            "error": "No graph loaded. Call build_graph first (or re-open the repo if a .code_graph.db exists)."
        }, indent=2)
    return None


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="build_graph",
            description=(
                "Build or rebuild the code graph for a repository. "
                "Indexes all functions, classes, methods, and call relationships. "
                "Supports Python, JavaScript, TypeScript, and Go."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Absolute path to the repository root"
                    },
                    "language": {
                        "type": "string",
                        "description": "Primary language hint (python, javascript, typescript, go, auto)",
                        "default": "auto"
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Glob patterns to exclude (e.g. ['**/tests/**', '**/node_modules/**'])",
                        "default": []
                    }
                },
                "required": ["repo_path"]
            }
        ),
        Tool(
            name="review_changes",
            description=(
                "Given a list of changed files, return the minimal set of symbols "
                "and files the reviewer needs to look at. "
                "This is the core token-saving feature — instead of reading the whole codebase, "
                "your AI reads only the impacted blast radius."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of changed file paths (relative to repo root)"
                    },
                    "include_upstream": {
                        "type": "boolean",
                        "description": "Include callers of the changed functions",
                        "default": True
                    },
                    "include_downstream": {
                        "type": "boolean",
                        "description": "Include functions called by the changed functions",
                        "default": True
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "How many hops to traverse in each direction",
                        "default": 3
                    }
                },
                "required": ["changed_files"]
            }
        ),
        Tool(
            name="get_impact",
            description="Find all upstream callers and downstream callees of a specific symbol.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g. 'parse_source' or 'MyClass.method')"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum traversal depth",
                        "default": 5
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="find_paths",
            description="Find all call paths from one symbol to another.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source symbol name"},
                    "target": {"type": "string", "description": "Target symbol name"},
                    "max_paths": {
                        "type": "integer",
                        "description": "Maximum number of paths to return",
                        "default": 5
                    }
                },
                "required": ["source", "target"]
            }
        ),
        Tool(
            name="search_symbols",
            description="Search for symbols by name or wildcard pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Name or wildcard pattern (e.g. 'parse*', '*handler')"
                    },
                    "symbol_type": {
                        "type": "string",
                        "description": "Filter by type: function, class, method, import, any",
                        "default": "any"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_symbol_details",
            description="Get full details for a symbol: location, callers, callees.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Symbol name"}
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="get_file_symbols",
            description="List all symbols defined in a specific file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File path relative to repo root"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="export_graph",
            description="Export the code graph (json, dot, or summary).",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Export format: json, dot, summary",
                        "default": "summary"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_stats",
            description="Get statistics about the indexed code graph.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> AsyncIterator[TextContent]:
    global state

    try:
        # ── build_graph ────────────────────────────────────────
        if name == "build_graph":
            repo_path = arguments["repo_path"]
            exclude_patterns = arguments.get("exclude_patterns", [])

            try:
                await app.request_context.session.send_log_message(
                    level=LoggingLevel.INFO,
                    data=f"Building graph for {repo_path}..."
                )
            except Exception:
                pass

            db_path = os.path.join(repo_path, ".code_graph.db")
            builder = GraphBuilder(
                repo_path=repo_path,
                db_path=db_path,
                exclude_patterns=exclude_patterns,
            )
            stats = builder.build()
            state.graph = builder.graph
            state.repo_path = repo_path
            state.db_path = db_path

            yield TextContent(type="text", text=json.dumps({
                "status": "success",
                "message": "Graph built and persisted to .code_graph.db",
                "stats": stats,
            }, indent=2))

        # ── review_changes ─────────────────────────────────────
        elif name == "review_changes":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            changed_files = arguments["changed_files"]
            result = state.graph.review_changes(
                changed_files=changed_files,
                include_upstream=arguments.get("include_upstream", True),
                include_downstream=arguments.get("include_downstream", True),
                max_depth=arguments.get("max_depth", 3),
            )
            yield TextContent(type="text", text=json.dumps({
                "changed_files": changed_files,
                "impacted_symbols": result["symbols"],
                "total_impacted": result["total"],
                "upstream_count": len(result["upstream"]),
                "downstream_count": len(result["downstream"]),
                "files_to_review": list(set(result["files"])),
            }, indent=2))

        # ── get_impact ─────────────────────────────────────────
        elif name == "get_impact":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            symbol = arguments["symbol"]
            max_depth = arguments.get("max_depth", 5)
            impact = state.graph.get_impact(symbol, max_depth=max_depth)
            yield TextContent(type="text", text=json.dumps(impact, indent=2))

        # ── find_paths ─────────────────────────────────────────
        elif name == "find_paths":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            source = arguments["source"]
            target = arguments["target"]
            max_paths = arguments.get("max_paths", 5)
            paths = state.graph.find_paths(source, target, max_paths=max_paths)
            yield TextContent(type="text", text=json.dumps({
                "source": source,
                "target": target,
                "paths_found": len(paths),
                "paths": paths,
            }, indent=2))

        # ── search_symbols ─────────────────────────────────────
        elif name == "search_symbols":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            symbols = state.graph.search_symbols(
                query=arguments["query"],
                symbol_type=arguments.get("symbol_type", "any"),
                limit=arguments.get("limit", 20),
            )
            yield TextContent(type="text", text=json.dumps({
                "query": arguments["query"],
                "matches_found": len(symbols),
                "symbols": symbols,
            }, indent=2))

        # ── get_symbol_details ─────────────────────────────────
        elif name == "get_symbol_details":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            details = state.graph.get_symbol_details(arguments["symbol"])
            yield TextContent(type="text", text=json.dumps(details, indent=2))

        # ── get_file_symbols ───────────────────────────────────
        elif name == "get_file_symbols":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            file_path = arguments["file_path"]
            symbols = state.graph.get_file_symbols(file_path)
            yield TextContent(type="text", text=json.dumps({
                "file": file_path,
                "symbols_defined": symbols,
            }, indent=2))

        # ── export_graph ───────────────────────────────────────
        elif name == "export_graph":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            fmt = arguments.get("format", "summary")
            yield TextContent(type="text", text=json.dumps(state.graph.export(fmt), indent=2))

        # ── get_stats ──────────────────────────────────────────
        elif name == "get_stats":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            yield TextContent(type="text", text=json.dumps(state.graph.get_stats(), indent=2))

        else:
            yield TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2))

    except Exception as e:
        yield TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))


async def _try_load_existing_graph() -> None:
    """On startup, look for a .code_graph.db in the working directory and load it."""
    db_candidates = [
        Path(".code_graph.db"),
        *Path(".").glob("**/.code_graph.db"),
    ]
    for db_path in db_candidates:
        if db_path.exists():
            graph = CodeGraph(str(db_path))
            loaded = graph.load_from_db()
            if loaded:
                state.graph = graph
                state.db_path = str(db_path)
                state.repo_path = str(db_path.parent.resolve())
                print(
                    f"[code-graph] Auto-loaded {len(graph.symbols)} symbols "
                    f"from {db_path}",
                    flush=True,
                )
                return


async def main():
    await _try_load_existing_graph()

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="universal-code-review-graph",
                server_version="1.0.0",
                capabilities=app.get_capabilities(),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
