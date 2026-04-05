#!/usr/bin/env python3
"""
Universal Code Review Graph MCP Server
Works with ALL AI assistants: Kimi K2.5, Qwen, Gemini Pro, Claude, ChatGPT, etc.
"""

import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    LoggingLevel,
)

from code_graph import CodeGraph, GraphBuilder


@dataclass
class ServerState:
    """Server state management."""
    graph: Optional[CodeGraph] = None
    repo_path: Optional[str] = None
    db_path: str = field(default=".code_graph.db")


# Global state
state = ServerState()

# Create MCP server
app = Server("universal-code-review-graph")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="build_graph",
            description="Build or rebuild the code graph for a repository. Indexes all functions, classes, imports, and calls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Absolute path to the repository root"
                    },
                    "language": {
                        "type": "string",
                        "description": "Primary language (python, javascript, typescript, go, auto)",
                        "default": "auto"
                    },
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns to exclude (e.g., ['**/test_*.py', '**/node_modules/**'])",
                        "default": []
                    }
                },
                "required": ["repo_path"]
            }
        ),
        Tool(
            name="review_changes",
            description="Get impacted symbols for a set of changed files. Returns minimal context for code review.",
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
                        "description": "Include functions that call the changed functions",
                        "default": True
                    },
                    "include_downstream": {
                        "type": "boolean",
                        "description": "Include functions called by the changed functions",
                        "default": True
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth for dependency traversal",
                        "default": 3
                    }
                },
                "required": ["changed_files"]
            }
        ),
        Tool(
            name="get_impact",
            description="Find all upstream and downstream dependencies of a specific symbol.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name (e.g., 'parse_source', 'MyClass.method')"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth for dependency traversal",
                        "default": 5
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="find_paths",
            description="Find all call paths between two symbols in the codebase.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source symbol name"
                    },
                    "target": {
                        "type": "string",
                        "description": "Target symbol name"
                    },
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
            description="Search for symbols in the codebase by name or pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (supports wildcards)"
                    },
                    "symbol_type": {
                        "type": "string",
                        "description": "Filter by type (function, class, method, import, any)",
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
            description="Get detailed information about a specific symbol including its definition and dependencies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name"
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="get_file_symbols",
            description="Get all symbols defined in a specific file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File path (relative to repo root)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="export_graph",
            description="Export the code graph to various formats (JSON, DOT, or summary).",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Export format (json, dot, summary)",
                        "default": "summary"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_stats",
            description="Get statistics about the code graph.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> AsyncIterator[TextContent]:
    """Handle tool calls."""
    global state
    
    try:
        if name == "build_graph":
            repo_path = arguments["repo_path"]
            language = arguments.get("language", "auto")
            exclude_patterns = arguments.get("exclude_patterns", [])
            
            await app.request_context.session.send_log_message(
                level=LoggingLevel.INFO,
                data=f"Building graph for {repo_path}..."
            )
            
            builder = GraphBuilder(
                repo_path=repo_path,
                db_path=os.path.join(repo_path, ".code_graph.db"),
                exclude_patterns=exclude_patterns
            )
            
            stats = builder.build()
            state.graph = builder.graph
            state.repo_path = repo_path
            
            result = {
                "status": "success",
                "message": f"Graph built successfully",
                "stats": stats
            }
            yield TextContent(type="text", text=json.dumps(result, indent=2))
            
        elif name == "review_changes":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            changed_files = arguments["changed_files"]
            include_upstream = arguments.get("include_upstream", True)
            include_downstream = arguments.get("include_downstream", True)
            max_depth = arguments.get("max_depth", 3)
            
            impacted = state.graph.review_changes(
                changed_files=changed_files,
                include_upstream=include_upstream,
                include_downstream=include_downstream,
                max_depth=max_depth
            )
            
            result = {
                "changed_files": changed_files,
                "impacted_symbols": impacted["symbols"],
                "total_impacted": impacted["total"],
                "upstream_count": len(impacted["upstream"]),
                "downstream_count": len(impacted["downstream"]),
                "files_to_review": list(set(impacted["files"]))
            }
            yield TextContent(type="text", text=json.dumps(result, indent=2))
            
        elif name == "get_impact":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            symbol = arguments["symbol"]
            max_depth = arguments.get("max_depth", 5)
            
            impact = state.graph.get_impact(symbol, max_depth=max_depth)
            
            result = {
                "symbol": symbol,
                "upstream": impact["upstream"],
                "downstream": impact["downstream"],
                "upstream_count": len(impact["upstream"]),
                "downstream_count": len(impact["downstream"])
            }
            yield TextContent(type="text", text=json.dumps(result, indent=2))
            
        elif name == "find_paths":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            source = arguments["source"]
            target = arguments["target"]
            max_paths = arguments.get("max_paths", 5)
            
            paths = state.graph.find_paths(source, target, max_paths=max_paths)
            
            result = {
                "source": source,
                "target": target,
                "paths_found": len(paths),
                "paths": paths
            }
            yield TextContent(type="text", text=json.dumps(result, indent=2))
            
        elif name == "search_symbols":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            query = arguments["query"]
            symbol_type = arguments.get("symbol_type", "any")
            limit = arguments.get("limit", 20)
            
            symbols = state.graph.search_symbols(query, symbol_type=symbol_type, limit=limit)
            
            result = {
                "query": query,
                "matches_found": len(symbols),
                "symbols": symbols
            }
            yield TextContent(type="text", text=json.dumps(result, indent=2))
            
        elif name == "get_symbol_details":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            symbol = arguments["symbol"]
            details = state.graph.get_symbol_details(symbol)
            
            yield TextContent(type="text", text=json.dumps(details, indent=2))
            
        elif name == "get_file_symbols":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            file_path = arguments["file_path"]
            symbols = state.graph.get_file_symbols(file_path)
            
            result = {
                "file": file_path,
                "symbols_defined": symbols
            }
            yield TextContent(type="text", text=json.dumps(result, indent=2))
            
        elif name == "export_graph":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            format_type = arguments.get("format", "summary")
            export = state.graph.export(format_type)
            
            yield TextContent(type="text", text=json.dumps(export, indent=2))
            
        elif name == "get_stats":
            if not state.graph:
                yield TextContent(
                    type="text", 
                    text=json.dumps({"error": "No graph built. Call build_graph first."}, indent=2)
                )
                return
            
            stats = state.graph.get_stats()
            yield TextContent(type="text", text=json.dumps(stats, indent=2))
            
        else:
            yield TextContent(
                type="text", 
                text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2)
            )
            
    except Exception as e:
        yield TextContent(
            type="text", 
            text=json.dumps({"error": str(e)}, indent=2)
        )


async def main():
    """Main entry point."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="universal-code-review-graph",
                server_version="1.0.0",
                capabilities=app.get_capabilities()
            )
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
