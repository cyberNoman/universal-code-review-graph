"""
universal-code-review-graph
One MCP server, any AI assistant — 6-8x fewer tokens on code reviews.

Usage:
    # Start the MCP server
    code-graph-server

    # Or in Python
    from universal_code_review_graph import CodeGraph, GraphBuilder
"""

from .code_graph import CodeGraph, GraphBuilder, Symbol, CallEdge, make_symbol_key

__version__ = "1.0.0"
__all__ = ["CodeGraph", "GraphBuilder", "Symbol", "CallEdge", "make_symbol_key"]
