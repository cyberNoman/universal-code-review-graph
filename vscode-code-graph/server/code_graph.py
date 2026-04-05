"""
Core Code Graph implementation for Universal Code Review Graph.
Builds and queries a call graph of functions, classes, and imports.
"""

import os
import re
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

import networkx as nx

# Tree-sitter imports
from tree_sitter import Language, Parser, Tree, Node


@dataclass
class Symbol:
    """Represents a code symbol (function, class, method, etc.)."""
    name: str
    symbol_type: str  # function, class, method, import
    file_path: str
    line_start: int
    line_end: int
    column_start: int = 0
    column_end: int = 0
    parent: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CallEdge:
    """Represents a call relationship between symbols."""
    caller: str
    callee: str
    call_type: str  # direct_call, import, inheritance
    file_path: str
    line: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


class CodeGraph:
    """In-memory code graph with NetworkX backend."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self.symbols: Dict[str, Symbol] = {}
        self.file_symbols: Dict[str, List[str]] = defaultdict(list)
        
    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to the graph."""
        self.symbols[symbol.name] = symbol
        self.file_symbols[symbol.file_path].append(symbol.name)
        
        self.graph.add_node(
            symbol.name,
            **symbol.to_dict()
        )
        
    def add_call(self, edge: CallEdge) -> None:
        """Add a call edge to the graph."""
        self.graph.add_edge(
            edge.caller,
            edge.callee,
            **edge.to_dict()
        )
        
    def get_symbol(self, name: str) -> Optional[Symbol]:
        """Get a symbol by name."""
        if name in self.symbols:
            return self.symbols[name]
        return None
        
    def get_upstream(self, symbol: str, max_depth: int = 5) -> List[str]:
        """Get all symbols that call this symbol (upstream dependencies)."""
        if symbol not in self.graph:
            return []
        
        upstream = set()
        visited = {symbol}
        queue = [(symbol, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
                
            for predecessor in self.graph.predecessors(current):
                if predecessor not in visited:
                    visited.add(predecessor)
                    upstream.add(predecessor)
                    queue.append((predecessor, depth + 1))
                    
        return list(upstream)
        
    def get_downstream(self, symbol: str, max_depth: int = 5) -> List[str]:
        """Get all symbols called by this symbol (downstream dependencies)."""
        if symbol not in self.graph:
            return []
        
        downstream = set()
        visited = {symbol}
        queue = [(symbol, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
                
            for successor in self.graph.successors(current):
                if successor not in visited:
                    visited.add(successor)
                    downstream.add(successor)
                    queue.append((successor, depth + 1))
                    
        return list(downstream)
        
    def find_paths(self, source: str, target: str, max_paths: int = 5) -> List[List[str]]:
        """Find all paths from source to target symbol."""
        try:
            paths = list(nx.all_simple_paths(
                self.graph, 
                source=source, 
                target=target,
                cutoff=10
            ))
            return paths[:max_paths]
        except nx.NetworkXNoPath:
            return []
        except nx.NodeNotFound:
            return []
            
    def search_symbols(
        self, 
        query: str, 
        symbol_type: str = "any",
        limit: int = 20
    ) -> List[Dict]:
        """Search for symbols by name pattern."""
        results = []
        pattern = query.replace("*", ".*").replace("?", ".")
        regex = re.compile(pattern, re.IGNORECASE)
        
        for name, symbol in self.symbols.items():
            if regex.search(name):
                if symbol_type == "any" or symbol.symbol_type == symbol_type:
                    results.append(symbol.to_dict())
                    if len(results) >= limit:
                        break
                        
        return results
        
    def review_changes(
        self,
        changed_files: List[str],
        include_upstream: bool = True,
        include_downstream: bool = True,
        max_depth: int = 3
    ) -> Dict:
        """Get impacted symbols for a set of changed files."""
        impacted_symbols = set()
        upstream_symbols = set()
        downstream_symbols = set()
        impacted_files = set(changed_files)
        
        # Get symbols defined in changed files
        for file_path in changed_files:
            symbols = self.file_symbols.get(file_path, [])
            impacted_symbols.update(symbols)
            
            for symbol in symbols:
                if include_upstream:
                    upstream = self.get_upstream(symbol, max_depth=max_depth)
                    upstream_symbols.update(upstream)
                    impacted_symbols.update(upstream)
                    
                if include_downstream:
                    downstream = self.get_downstream(symbol, max_depth=max_depth)
                    downstream_symbols.update(downstream)
                    impacted_symbols.update(downstream)
                    
        # Get files containing impacted symbols
        for symbol_name in impacted_symbols:
            symbol = self.symbols.get(symbol_name)
            if symbol:
                impacted_files.add(symbol.file_path)
                
        return {
            "symbols": list(impacted_symbols),
            "upstream": list(upstream_symbols),
            "downstream": list(downstream_symbols),
            "total": len(impacted_symbols),
            "files": list(impacted_files)
        }
        
    def get_impact(self, symbol: str, max_depth: int = 5) -> Dict:
        """Get full impact analysis for a symbol."""
        upstream = self.get_upstream(symbol, max_depth=max_depth)
        downstream = self.get_downstream(symbol, max_depth=max_depth)
        
        return {
            "symbol": symbol,
            "upstream": upstream,
            "downstream": downstream,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream)
        }
        
    def get_symbol_details(self, symbol_name: str) -> Dict:
        """Get detailed information about a symbol."""
        symbol = self.symbols.get(symbol_name)
        if not symbol:
            return {"error": f"Symbol '{symbol_name}' not found"}
            
        upstream = list(self.graph.predecessors(symbol_name))
        downstream = list(self.graph.successors(symbol_name))
        
        return {
            "symbol": symbol.to_dict(),
            "called_by": upstream,
            "calls": downstream,
            "called_by_count": len(upstream),
            "calls_count": len(downstream)
        }
        
    def get_file_symbols(self, file_path: str) -> List[Dict]:
        """Get all symbols defined in a file."""
        symbols = []
        for symbol_name in self.file_symbols.get(file_path, []):
            symbol = self.symbols.get(symbol_name)
            if symbol:
                symbols.append(symbol.to_dict())
        return symbols
        
    def export(self, format_type: str = "summary") -> Dict:
        """Export the graph in various formats."""
        if format_type == "json":
            return {
                "nodes": [self.graph.nodes[n] for n in self.graph.nodes()],
                "edges": [
                    {
                        "source": u,
                        "target": v,
                        **self.graph.edges[u, v]
                    }
                    for u, v in self.graph.edges()
                ]
            }
        elif format_type == "dot":
            lines = ["digraph CodeGraph {"]
            for node in self.graph.nodes():
                lines.append(f'    "{node}";')
            for u, v in self.graph.edges():
                lines.append(f'    "{u}" -> "{v}";')
            lines.append("}")
            return {"dot": "\n".join(lines)}
        else:  # summary
            return {
                "total_symbols": len(self.symbols),
                "total_edges": self.graph.number_of_edges(),
                "files_indexed": len(self.file_symbols),
                "symbol_types": self._get_symbol_type_counts()
            }
            
    def _get_symbol_type_counts(self) -> Dict[str, int]:
        """Get counts of each symbol type."""
        counts = defaultdict(int)
        for symbol in self.symbols.values():
            counts[symbol.symbol_type] += 1
        return dict(counts)
        
    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "total_symbols": len(self.symbols),
            "total_edges": self.graph.number_of_edges(),
            "files_indexed": len(self.file_symbols),
            "symbol_types": self._get_symbol_type_counts(),
            "most_connected": self._get_most_connected(10)
        }
        
    def _get_most_connected(self, n: int) -> List[Dict]:
        """Get the most connected symbols."""
        degrees = [
            (node, self.graph.in_degree(node) + self.graph.out_degree(node))
            for node in self.graph.nodes()
        ]
        degrees.sort(key=lambda x: x[1], reverse=True)
        
        result = []
        for node, degree in degrees[:n]:
            symbol = self.symbols.get(node)
            if symbol:
                result.append({
                    "name": node,
                    "type": symbol.symbol_type,
                    "total_connections": degree,
                    "incoming": self.graph.in_degree(node),
                    "outgoing": self.graph.out_degree(node)
                })
        return result


class GraphBuilder:
    """Builds a CodeGraph from source files."""
    
    def __init__(
        self,
        repo_path: str,
        db_path: str = ".code_graph.db",
        exclude_patterns: Optional[List[str]] = None
    ):
        self.repo_path = Path(repo_path).resolve()
        self.db_path = db_path
        self.exclude_patterns = exclude_patterns or [
            "**/test_*.py",
            "**/tests/**",
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/*.min.js",
            "**/dist/**",
            "**/build/**",
            "**/venv/**",
            "**/.venv/**",
        ]
        self.graph = CodeGraph(db_path)
        self.parsers: Dict[str, Parser] = {}
        self._init_parsers()
        
    def _init_parsers(self) -> None:
        """Initialize tree-sitter parsers for supported languages."""
        try:
            from tree_sitter_python import language as python_language
            self.parsers["python"] = Parser(Language(python_language))
        except ImportError:
            pass
            
        try:
            from tree_sitter_javascript import language as js_language
            self.parsers["javascript"] = Parser(Language(js_language))
            self.parsers["typescript"] = Parser(Language(js_language))
        except ImportError:
            pass
            
        try:
            from tree_sitter_go import language as go_language
            self.parsers["go"] = Parser(Language(go_language))
        except ImportError:
            pass
            
    def _should_exclude(self, path: Path) -> bool:
        """Check if a file should be excluded."""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            regex = pattern.replace("**", ".*").replace("*", "[^/]*").replace("?", ".")
            if re.search(regex, path_str):
                return True
        return False
        
    def _get_language(self, file_path: Path) -> Optional[str]:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
        }
        return mapping.get(ext)
        
    def build(self) -> Dict:
        """Build the code graph from all source files."""
        files_processed = 0
        symbols_found = 0
        edges_found = 0
        
        # Find all source files
        for ext in ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go"]:
            for file_path in self.repo_path.rglob(ext):
                if self._should_exclude(file_path):
                    continue
                    
                language = self._get_language(file_path)
                if not language or language not in self.parsers:
                    continue
                    
                try:
                    symbols, calls = self._parse_file(file_path, language)
                    
                    for symbol in symbols:
                        self.graph.add_symbol(symbol)
                        symbols_found += 1
                        
                    for call in calls:
                        self.graph.add_call(call)
                        edges_found += 1
                        
                    files_processed += 1
                    
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")
                    
        # Save to database
        self._save_to_db()
        
        return {
            "files_processed": files_processed,
            "symbols_found": symbols_found,
            "edges_found": edges_found,
            "repo_path": str(self.repo_path)
        }
        
    def _parse_file(
        self, 
        file_path: Path, 
        language: str
    ) -> Tuple[List[Symbol], List[CallEdge]]:
        """Parse a single file and extract symbols and calls."""
        symbols = []
        calls = []
        
        relative_path = str(file_path.relative_to(self.repo_path))
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except Exception:
            return symbols, calls
            
        parser = self.parsers.get(language)
        if not parser:
            return symbols, calls
            
        tree = parser.parse(source.encode())
        
        if language == "python":
            symbols, calls = self._parse_python_tree(tree, source, relative_path)
        elif language in ["javascript", "typescript"]:
            symbols, calls = self._parse_js_tree(tree, source, relative_path)
        elif language == "go":
            symbols, calls = self._parse_go_tree(tree, source, relative_path)
            
        return symbols, calls
        
    def _parse_python_tree(
        self, 
        tree, 
        source: str, 
        file_path: str
    ) -> Tuple[List[Symbol], List[CallEdge]]:
        """Parse Python AST."""
        symbols = []
        calls = []
        
        root = tree.root_node
        
        def get_text(node: Node) -> str:
            return source[node.start_byte:node.end_byte]
            
        def visit_node(node: Node, parent_name: Optional[str] = None) -> None:
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    if parent_name:
                        full_name = f"{parent_name}.{name}"
                    else:
                        full_name = name
                        
                    symbol = Symbol(
                        name=full_name,
                        symbol_type="method" if parent_name else "function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                        parent=parent_name
                    )
                    symbols.append(symbol)
                    
                    # Find calls within this function
                    for child in node.children:
                        if child.type == "block":
                            self._find_python_calls(
                                child, full_name, file_path, source, calls
                            )
                            
            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    symbol = Symbol(
                        name=name,
                        symbol_type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1]
                    )
                    symbols.append(symbol)
                    
                    # Visit methods within class
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            visit_node(child, name)
                            
            # Continue visiting children
            for child in node.children:
                visit_node(child, parent_name)
                
        visit_node(root)
        return symbols, calls
        
    def _find_python_calls(
        self,
        node: Node,
        caller: str,
        file_path: str,
        source: str,
        calls: List[CallEdge]
    ) -> None:
        """Find function calls in Python code."""
        def get_text(n: Node) -> str:
            return source[n.start_byte:n.end_byte]
            
        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                callee = get_text(func_node)
                # Simple name resolution
                if "." not in callee and "(" not in callee:
                    calls.append(CallEdge(
                        caller=caller,
                        callee=callee,
                        call_type="direct_call",
                        file_path=file_path,
                        line=node.start_point[0] + 1
                    ))
                    
        for child in node.children:
            self._find_python_calls(child, caller, file_path, source, calls)
            
    def _parse_js_tree(
        self, 
        tree, 
        source: str, 
        file_path: str
    ) -> Tuple[List[Symbol], List[CallEdge]]:
        """Parse JavaScript/TypeScript AST."""
        symbols = []
        calls = []
        
        root = tree.root_node
        
        def get_text(node: Node) -> str:
            return source[node.start_byte:node.end_byte]
            
        def visit_node(node: Node, parent_name: Optional[str] = None) -> None:
            # Function declarations
            if node.type in ["function_declaration", "function"]:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    symbol = Symbol(
                        name=name,
                        symbol_type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1]
                    )
                    symbols.append(symbol)
                    
            # Arrow functions and methods
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    full_name = f"{parent_name}.{name}" if parent_name else name
                    symbol = Symbol(
                        name=full_name,
                        symbol_type="method",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                        parent=parent_name
                    )
                    symbols.append(symbol)
                    
            # Class declarations
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    symbol = Symbol(
                        name=name,
                        symbol_type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1]
                    )
                    symbols.append(symbol)
                    
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            visit_node(child, name)
                            
            # Continue visiting
            for child in node.children:
                visit_node(child, parent_name)
                
        visit_node(root)
        return symbols, calls
        
    def _parse_go_tree(
        self, 
        tree, 
        source: str, 
        file_path: str
    ) -> Tuple[List[Symbol], List[CallEdge]]:
        """Parse Go AST."""
        symbols = []
        calls = []
        
        root = tree.root_node
        
        def get_text(node: Node) -> str:
            return source[node.start_byte:node.end_byte]
            
        def visit_node(node: Node, parent_name: Optional[str] = None) -> None:
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    symbol = Symbol(
                        name=name,
                        symbol_type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1]
                    )
                    symbols.append(symbol)
                    
            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    full_name = f"{parent_name}.{name}" if parent_name else name
                    symbol = Symbol(
                        name=full_name,
                        symbol_type="method",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                        parent=parent_name
                    )
                    symbols.append(symbol)
                    
            elif node.type == "type_declaration":
                # Extract type names
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            name = get_text(name_node)
                            symbol = Symbol(
                                name=name,
                                symbol_type="class",
                                file_path=file_path,
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                                column_start=node.start_point[1],
                                column_end=node.end_point[1]
                            )
                            symbols.append(symbol)
                            
            for child in node.children:
                visit_node(child, parent_name)
                
        visit_node(root)
        return symbols, calls
        
    def _save_to_db(self) -> None:
        """Save the graph to SQLite database."""
        if not self.db_path:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                name TEXT PRIMARY KEY,
                symbol_type TEXT,
                file_path TEXT,
                line_start INTEGER,
                line_end INTEGER,
                parent TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                caller TEXT,
                callee TEXT,
                call_type TEXT,
                file_path TEXT,
                line INTEGER,
                PRIMARY KEY (caller, callee, line)
            )
        """)
        
        # Clear existing data
        cursor.execute("DELETE FROM symbols")
        cursor.execute("DELETE FROM calls")
        
        # Insert symbols
        for symbol in self.graph.symbols.values():
            cursor.execute("""
                INSERT INTO symbols (name, symbol_type, file_path, line_start, line_end, parent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol.name,
                symbol.symbol_type,
                symbol.file_path,
                symbol.line_start,
                symbol.line_end,
                symbol.parent
            ))
            
        # Insert calls
        for u, v, data in self.graph.graph.edges(data=True):
            cursor.execute("""
                INSERT INTO calls (caller, callee, call_type, file_path, line)
                VALUES (?, ?, ?, ?, ?)
            """, (
                u,
                v,
                data.get("call_type", "direct_call"),
                data.get("file_path", ""),
                data.get("line", 0)
            ))
            
        conn.commit()
        conn.close()
