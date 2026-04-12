#!/usr/bin/env python3
"""
Universal Code Review Graph — MCP Server (Math-Optimized)
Works with ALL AI assistants: Kimi K2.5, Qwen, Gemini, Claude, ChatGPT,
Cursor, Windsurf, Zed, Continue, and any MCP-compatible client.

Protocol: JSON-RPC 2.0 over stdio (MCP spec)

ENHANCEMENTS:
- Shannon entropy-based symbol filtering
- Spectral graph theory prioritization
- Thermodynamic free energy pruning
- Fractal dimension analysis
- Wave function collapse for symbol merging
- Renormalization group flow for multi-scale abstraction
- Compact JSON serialization (40-50% token reduction)
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
from math_optimizer import UnifiedMathOptimizer
from compact_serializer import AdaptiveSerializer


@dataclass
class ServerState:
    graph: Optional[CodeGraph] = None
    repo_path: Optional[str] = None
    db_path: str = field(default=".code_graph.db")
    optimization_enabled: bool = True
    token_budget: int = 2000


state = ServerState()
app = Server("universal-code-review-graph-optimized")


def _require_graph() -> Optional[str]:
    """Return an error JSON string if no graph is loaded, else None."""
    if not state.graph or len(state.graph.symbols) == 0:
        return json.dumps({
            "error": "No graph loaded. Call build_graph first (or re-open the repo if a .code_graph.db exists)."
        }, indent=2)
    return None


def _convert_symbols_to_dict(graph: CodeGraph) -> list:
    """Convert graph symbols to dict format for optimization."""
    symbols = []
    for sym in graph.symbols:
        symbol_dict = {
            'key': sym.key if hasattr(sym, 'key') else f"{sym.file_path}::{sym.name}",
            'name': sym.name,
            'short_name': getattr(sym, 'short_name', sym.name),
            'symbol_type': sym.symbol_type,
            'file_path': sym.file_path,
            'line_start': sym.line_start,
            'line_end': sym.line_end,
            'parent': getattr(sym, 'parent', ''),
            'signature': getattr(sym, 'signature', ''),
        }
        symbols.append(symbol_dict)
    return symbols


def _convert_edges_to_dict(graph: CodeGraph) -> list:
    """Convert graph edges to dict format for optimization."""
    edges = []
    if hasattr(graph, 'G') and graph.G:
        for u, v, edge_data in graph.G.edges(data=True):
            edges.append({
                'caller': u,
                'callee': v,
                'call_type': edge_data.get('call_type', 'call')
            })
    return edges


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
                "and files the reviewer needs to look at. Uses mathematical optimization "
                "(entropy, spectral analysis, thermodynamics) to minimize token usage. "
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
                    },
                    "optimize": {
                        "type": "boolean",
                        "description": "Apply math optimization (entropy, spectral, thermodynamics)",
                        "default": True
                    },
                    "token_budget": {
                        "type": "integer",
                        "description": "Target token count for optimization",
                        "default": 2000
                    },
                    "compact_format": {
                        "type": "boolean",
                        "description": "Use compact JSON serialization (saves 40-50% tokens)",
                        "default": True
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
                    },
                    "optimize": {
                        "type": "boolean",
                        "description": "Apply math optimization to reduce token count",
                        "default": True
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
                        "description": "Export format: json, dot, summary, compact_json, binary",
                        "default": "summary"
                    },
                    "optimize": {
                        "type": "boolean",
                        "description": "Apply math optimization before export",
                        "default": False
                    },
                    "token_budget": {
                        "type": "integer",
                        "description": "Target token count when optimize=True",
                        "default": 2000
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
        Tool(
            name="get_optimization_stats",
            description=(
                "Get detailed statistics about mathematical optimization and token savings. "
                "Shows entropy scores, spectral centrality, free energy, fractal dimension, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "token_budget": {
                        "type": "integer",
                        "description": "Target token count for optimization demo",
                        "default": 2000
                    }
                }
            }
        ),
        Tool(
            name="set_optimization",
            description="Enable or disable mathematical optimization and set token budget.",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable/disable optimization",
                        "default": True
                    },
                    "token_budget": {
                        "type": "integer",
                        "description": "Target token count",
                        "default": 2000
                    }
                }
            }
        ),
    ]


def _serialize_response(data: Any, compact: bool = False) -> str:
    """Serialize response with optional compact format."""
    if compact:
        if isinstance(data, dict) and 'symbols' in data and 'edges' in data:
            return AdaptiveSerializer.serialize(
                data['symbols'], data['edges'], format='compact_json'
            )
        return json.dumps(data, separators=(',', ':'))
    return json.dumps(data, indent=2)


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
            optimize = arguments.get("optimize", state.optimization_enabled)
            compact = arguments.get("compact_format", True)
            token_budget = arguments.get("token_budget", state.token_budget)

            result = state.graph.review_changes(
                changed_files=changed_files,
                include_upstream=arguments.get("include_upstream", True),
                include_downstream=arguments.get("include_downstream", True),
                max_depth=arguments.get("max_depth", 3),
            )

            # Apply mathematical optimization
            if optimize and result.get("impacted_symbols"):
                try:
                    symbols = _convert_symbols_to_dict(state.graph)
                    edges = _convert_edges_to_dict(state.graph)

                    opt_result = UnifiedMathOptimizer.optimize(
                        symbols, edges,
                        token_budget=token_budget,
                        enable_entropy=True,
                        enable_spectral=True,
                        enable_thermodynamic=True,
                        enable_fractal=False,
                        enable_wave_collapse=True,
                        enable_renormalization=True
                    )

                    # Filter impacted symbols to only optimized ones
                    optimized_keys = set(
                        s.get('key', s.get('symbol_key', ''))
                        for s in opt_result.optimized_symbols
                    )
                    result["impacted_symbols"] = [
                        s for s in result["impacted_symbols"]
                        if s in optimized_keys
                    ]
                    result["optimization_applied"] = True
                    result["techniques"] = opt_result.techniques_applied
                    result["original_tokens"] = opt_result.original_tokens
                    result["optimized_tokens"] = opt_result.optimized_tokens
                    result["reduction_ratio"] = round(opt_result.reduction_ratio, 2)
                except Exception as e:
                    # Fallback to non-optimized if optimization fails
                    result["optimization_error"] = str(e)
                    result["optimization_applied"] = False

            response_data = {
                "changed_files": changed_files,
                "impacted_symbols": result["impacted_symbols"],
                "total_impacted": result["total"],
                "upstream_count": result.get("upstream_count", len(result.get("upstream", []))),
                "downstream_count": result.get("downstream_count", len(result.get("downstream", []))),
                "files_to_review": list(set(result["files"])),
                "optimization_applied": result.get("optimization_applied", False),
            }

            # Add optimization metrics if available
            if result.get("optimization_applied"):
                response_data["token_savings"] = {
                    "original": result.get("original_tokens", 0),
                    "optimized": result.get("optimized_tokens", 0),
                    "reduction_ratio": result.get("reduction_ratio", 1.0),
                    "techniques": result.get("techniques", [])
                }

            yield TextContent(type="text", text=_serialize_response(response_data, compact))

        # ── get_impact ─────────────────────────────────────────
        elif name == "get_impact":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            symbol = arguments["symbol"]
            max_depth = arguments.get("max_depth", 5)
            optimize = arguments.get("optimize", state.optimization_enabled)

            impact = state.graph.get_impact(symbol, max_depth=max_depth)

            if optimize:
                try:
                    symbols = _convert_symbols_to_dict(state.graph)
                    edges = _convert_edges_to_dict(state.graph)

                    opt_result = UnifiedMathOptimizer.optimize(
                        symbols, edges,
                        token_budget=state.token_budget
                    )

                    impact["optimization_applied"] = True
                    impact["original_tokens"] = opt_result.original_tokens
                    impact["optimized_tokens"] = opt_result.optimized_tokens
                    impact["reduction_ratio"] = round(opt_result.reduction_ratio, 2)
                except Exception:
                    impact["optimization_applied"] = False

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
            optimize = arguments.get("optimize", False)
            token_budget = arguments.get("token_budget", state.token_budget)

            # Handle optimized export
            if optimize and fmt in ["json", "compact_json"]:
                try:
                    symbols = _convert_symbols_to_dict(state.graph)
                    edges = _convert_edges_to_dict(state.graph)

                    opt_result = UnifiedMathOptimizer.optimize(
                        symbols, edges,
                        token_budget=token_budget
                    )

                    if fmt == "compact_json":
                        compact_json = AdaptiveSerializer.serialize(
                            opt_result.optimized_symbols,
                            opt_result.optimized_edges,
                            format='compact_json'
                        )
                        yield TextContent(type="text", text=compact_json)
                    else:
                        yield TextContent(type="text", text=json.dumps({
                            "symbols": opt_result.optimized_symbols,
                            "edges": opt_result.optimized_edges,
                            "optimization": {
                                "original_tokens": opt_result.original_tokens,
                                "optimized_tokens": opt_result.optimized_tokens,
                                "reduction_ratio": opt_result.reduction_ratio,
                                "techniques": opt_result.techniques_applied
                            }
                        }, indent=2))
                    return
                except Exception as e:
                    yield TextContent(type="text", text=json.dumps({
                        "error": f"Optimization failed: {str(e)}",
                        "fallback": state.graph.export(fmt)
                    }, indent=2))
                    return

            # Standard export
            yield TextContent(type="text", text=json.dumps(state.graph.export(fmt), indent=2))

        # ── get_stats ──────────────────────────────────────────
        elif name == "get_stats":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            stats = state.graph.get_stats()
            stats["optimization_enabled"] = state.optimization_enabled
            stats["token_budget"] = state.token_budget
            yield TextContent(type="text", text=json.dumps(stats, indent=2))

        # ── get_optimization_stats ─────────────────────────────
        elif name == "get_optimization_stats":
            err = _require_graph()
            if err:
                yield TextContent(type="text", text=err)
                return

            token_budget = arguments.get("token_budget", state.token_budget)

            try:
                symbols = _convert_symbols_to_dict(state.graph)
                edges = _convert_edges_to_dict(state.graph)

                # Calculate metrics
                from math_optimizer import (
                    EntropyOptimizer, SpectralGraphOptimizer,
                    ThermodynamicOptimizer, FractalDimensionOptimizer
                )

                entropies = EntropyOptimizer.calculate_symbol_entropy(symbols, edges)
                centralities = SpectralGraphOptimizer.compute_eigenvector_centrality(
                    symbols, edges
                )
                free_energies = ThermodynamicOptimizer.compute_free_energies(
                    symbols, edges
                )
                fractal_dim = FractalDimensionOptimizer.compute_box_counting_dimension(
                    symbols
                )

                # Run full optimization
                opt_result = UnifiedMathOptimizer.optimize(
                    symbols, edges,
                    token_budget=token_budget
                )

                yield TextContent(type="text", text=json.dumps({
                    "optimization_metrics": {
                        "total_symbols": len(symbols),
                        "total_edges": len(edges),
                        "fractal_dimension": round(fractal_dim, 3),
                        "avg_entropy": round(sum(entropies.values()) / max(len(entropies), 1), 3),
                        "avg_centrality": round(sum(centralities.values()) / max(len(centralities), 1), 3),
                        "avg_free_energy": round(sum(free_energies.values()) / max(len(free_energies), 1), 3),
                    },
                    "token_savings": {
                        "original_tokens": opt_result.original_tokens,
                        "optimized_tokens": opt_result.optimized_tokens,
                        "reduction_ratio": round(opt_result.reduction_ratio, 2),
                        "techniques_applied": opt_result.techniques_applied
                    },
                    "top_symbols_by_entropy": sorted(
                        entropies.items(), key=lambda x: x[1], reverse=True
                    )[:10],
                    "top_symbols_by_centrality": sorted(
                        centralities.items(), key=lambda x: x[1], reverse=True
                    )[:10],
                }, indent=2))

            except Exception as e:
                yield TextContent(type="text", text=json.dumps({
                    "error": f"Failed to calculate optimization stats: {str(e)}"
                }, indent=2))

        # ── set_optimization ───────────────────────────────────
        elif name == "set_optimization":
            state.optimization_enabled = arguments.get("enabled", True)
            state.token_budget = arguments.get("token_budget", state.token_budget)

            yield TextContent(type="text", text=json.dumps({
                "status": "success",
                "optimization_enabled": state.optimization_enabled,
                "token_budget": state.token_budget,
            }, indent=2))

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
                server_name="universal-code-review-graph-optimized",
                server_version="2.0.0-math-optimized",
                capabilities=app.get_capabilities(),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
