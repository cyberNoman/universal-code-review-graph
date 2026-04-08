"""
Core Code Graph implementation for Universal Code Review Graph.
Builds and queries a call graph of functions, classes, and imports.

Supports: Python, JavaScript, TypeScript, Go
Works with: Claude, Kimi, Qwen, Gemini, ChatGPT, Cursor, Windsurf, Zed, Continue
"""

import hashlib
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

import networkx as nx

# Tree-sitter — optional at module level so CodeGraph / Symbol / CallEdge
# remain importable even when tree-sitter is not installed.
# GraphBuilder will fail gracefully per-language if grammars are missing.
try:
    from tree_sitter import Language, Parser, Node
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _TREE_SITTER_AVAILABLE = False
    Language = None  # type: ignore
    Parser = None    # type: ignore
    Node = None      # type: ignore


@dataclass
class Symbol:
    """Represents a code symbol (function, class, method, etc.)."""
    name: str           # fully-qualified: "file_path::ClassName.method_name"
    short_name: str     # just the bare symbol name: "method_name"
    symbol_type: str    # function, class, method, import
    file_path: str
    line_start: int
    line_end: int
    column_start: int = 0
    column_end: int = 0
    parent: Optional[str] = None      # parent class short name
    signature: Optional[str] = None
    docstring: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CallEdge:
    """Represents a call relationship between symbols."""
    caller: str    # fully-qualified name
    callee: str    # fully-qualified name (best-effort resolution)
    call_type: str  # direct_call, import, inheritance
    file_path: str
    line: int

    def to_dict(self) -> Dict:
        return asdict(self)


def make_symbol_key(file_path: str, name: str) -> str:
    """Create a unique symbol key: 'relative/path.py::SymbolName'."""
    return f"{file_path}::{name}"


# ══════════════════════════════════════════════════════════════
# Diagnostics — loud failures, never silent
# ══════════════════════════════════════════════════════════════

class BuildDiagnostics:
    """Collects warnings, errors, and stats during a build."""

    def __init__(self) -> None:
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.files_parsed: int = 0
        self.files_skipped: int = 0
        self.files_failed: int = 0

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "files_parsed": self.files_parsed,
            "files_skipped": self.files_skipped,
            "files_failed": self.files_failed,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _stderr(msg: str) -> None:
    """Print to stderr so it's visible even when stdout is captured."""
    print(msg, file=sys.stderr, flush=True)


# ══════════════════════════════════════════════════════════════
# CodeGraph — in-memory graph with NetworkX backend
# ══════════════════════════════════════════════════════════════

class CodeGraph:
    """In-memory code graph with NetworkX backend."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self.symbols: Dict[str, Symbol] = {}          # key → Symbol
        self.file_symbols: Dict[str, List[str]] = defaultdict(list)
        # short_name index for cross-file call resolution
        self._short_name_index: Dict[str, List[str]] = defaultdict(list)
        # file hash cache for incremental rebuilds
        self._file_hashes: Dict[str, str] = {}

    # ──────────────────────────────────────────────────────────
    # Mutation
    # ──────────────────────────────────────────────────────────

    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to the graph (key = symbol.name which is fully qualified)."""
        self.symbols[symbol.name] = symbol
        self.file_symbols[symbol.file_path].append(symbol.name)
        self._short_name_index[symbol.short_name].append(symbol.name)
        self.graph.add_node(symbol.name, **symbol.to_dict())

    def remove_file(self, file_path: str) -> None:
        """Remove all symbols and edges for a given file (for incremental rebuilds)."""
        for sym_key in list(self.file_symbols.get(file_path, [])):
            sym = self.symbols.pop(sym_key, None)
            if sym:
                self.graph.remove_node(sym_key)
        self.file_symbols.pop(file_path, None)
        # Rebuild short_name index from scratch (cheap for small repos)
        self._rebuild_short_name_index()
        # Remove from hash cache
        self._file_hashes.pop(file_path, None)

    def _rebuild_short_name_index(self) -> None:
        self._short_name_index.clear()
        for sym in self.symbols.values():
            self._short_name_index[sym.short_name].append(sym.name)

    def add_call(self, edge: CallEdge) -> None:
        """Add a call edge. Both nodes are auto-created if missing."""
        if edge.caller not in self.graph:
            self.graph.add_node(edge.caller)
        if edge.callee not in self.graph:
            self.graph.add_node(edge.callee)
        self.graph.add_edge(edge.caller, edge.callee, **edge.to_dict())

    def add_calls_batch(self, edges: List[CallEdge]) -> int:
        """Add many edges at once. Returns count added."""
        added = 0
        for edge in edges:
            self.add_call(edge)
            added += 1
        return added

    # ──────────────────────────────────────────────────────────
    # Queries
    # ──────────────────────────────────────────────────────────

    def resolve_symbol(self, name: str) -> Optional[str]:
        """
        Given a bare short name OR a fully-qualified key, return the
        canonical key in the graph.  Returns None if not found.
        """
        if name in self.symbols:
            return name
        matches = self._short_name_index.get(name, [])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return matches[0]  # best-effort: first match
        return None

    def get_symbol(self, name: str) -> Optional[Symbol]:
        key = self.resolve_symbol(name)
        return self.symbols.get(key) if key else None

    def get_upstream(self, symbol: str, max_depth: int = 5) -> List[str]:
        """All symbols that (transitively) call this symbol."""
        key = self.resolve_symbol(symbol) or symbol
        if key not in self.graph:
            return []

        upstream: Set[str] = set()
        visited = {key}
        queue: List[Tuple[str, int]] = [(key, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for pred in self.graph.predecessors(current):
                if pred not in visited:
                    visited.add(pred)
                    upstream.add(pred)
                    queue.append((pred, depth + 1))

        return list(upstream)

    def get_downstream(self, symbol: str, max_depth: int = 5) -> List[str]:
        """All symbols (transitively) called by this symbol."""
        key = self.resolve_symbol(symbol) or symbol
        if key not in self.graph:
            return []

        downstream: Set[str] = set()
        visited = {key}
        queue: List[Tuple[str, int]] = [(key, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            for succ in self.graph.successors(current):
                if succ not in visited:
                    visited.add(succ)
                    downstream.add(succ)
                    queue.append((succ, depth + 1))

        return list(downstream)

    def find_paths(self, source: str, target: str, max_paths: int = 5) -> List[List[str]]:
        """Find call paths between two symbols."""
        src = self.resolve_symbol(source) or source
        tgt = self.resolve_symbol(target) or target
        if src not in self.graph or tgt not in self.graph or src == tgt:
            return []
        try:
            paths = list(nx.all_simple_paths(self.graph, source=src, target=tgt, cutoff=10))
            return paths[:max_paths]
        except Exception:
            return []

    def search_symbols(self, query: str, symbol_type: str = "any", limit: int = 20) -> List[Dict]:
        """Search symbols by name pattern (wildcards supported)."""
        pattern = query.replace("*", ".*").replace("?", ".")
        regex = re.compile(pattern, re.IGNORECASE)
        results: List[Dict] = []
        for symbol in self.symbols.values():
            if regex.search(symbol.short_name) or regex.search(symbol.name):
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
        max_depth: int = 3,
        max_files: int = 30,
    ) -> Dict:
        """Core feature: get the minimal set of symbols impacted by changed files."""
        impacted: Set[str] = set()
        upstream_set: Set[str] = set()
        downstream_set: Set[str] = set()
        impacted_files: Set[str] = set(changed_files)

        for file_path in changed_files:
            for sym_key in self.file_symbols.get(file_path, []):
                impacted.add(sym_key)
                if include_upstream:
                    up = self.get_upstream(sym_key, max_depth=max_depth)
                    upstream_set.update(up)
                    impacted.update(up)
                if include_downstream:
                    down = self.get_downstream(sym_key, max_depth=max_depth)
                    downstream_set.update(down)
                    impacted.update(down)

        for sym_key in impacted:
            sym = self.symbols.get(sym_key)
            if sym:
                impacted_files.add(sym.file_path)

        impacted_files_list = list(impacted_files)
        if len(impacted_files_list) > max_files:
            impacted_files_list = impacted_files_list[:max_files]

        return {
            "symbols": list(impacted),
            "upstream": list(upstream_set),
            "downstream": list(downstream_set),
            "total": len(impacted),
            "files": impacted_files_list,
        }

    def get_impact(self, symbol: str, max_depth: int = 5) -> Dict:
        upstream = self.get_upstream(symbol, max_depth=max_depth)
        downstream = self.get_downstream(symbol, max_depth=max_depth)
        return {
            "symbol": symbol,
            "upstream": upstream,
            "downstream": downstream,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
        }

    def get_symbol_details(self, symbol_name: str) -> Dict:
        sym = self.get_symbol(symbol_name)
        if not sym:
            return {"error": f"Symbol '{symbol_name}' not found"}
        key = sym.name
        return {
            "symbol": sym.to_dict(),
            "called_by": list(self.graph.predecessors(key)),
            "calls": list(self.graph.successors(key)),
            "called_by_count": self.graph.in_degree(key),
            "calls_count": self.graph.out_degree(key),
        }

    def get_file_symbols(self, file_path: str) -> List[Dict]:
        return [
            self.symbols[k].to_dict()
            for k in self.file_symbols.get(file_path, [])
            if k in self.symbols
        ]

    def export(self, format_type: str = "summary") -> Dict:
        if format_type == "json":
            return {
                "nodes": [dict(self.graph.nodes[n]) for n in self.graph.nodes()],
                "edges": [
                    {"source": u, "target": v, **dict(self.graph.edges[u, v])}
                    for u, v in self.graph.edges()
                ],
            }
        elif format_type == "dot":
            lines = ["digraph CodeGraph {"]
            for node in self.graph.nodes():
                lines.append(f'    "{node}";')
            for u, v in self.graph.edges():
                lines.append(f'    "{u}" -> "{v}";')
            lines.append("}")
            return {"dot": "\n".join(lines)}
        else:
            return {
                "total_symbols": len(self.symbols),
                "total_edges": self.graph.number_of_edges(),
                "files_indexed": len(self.file_symbols),
                "symbol_types": self._get_symbol_type_counts(),
            }

    def get_stats(self) -> Dict:
        return {
            "total_symbols": len(self.symbols),
            "total_edges": self.graph.number_of_edges(),
            "files_indexed": len(self.file_symbols),
            "symbol_types": self._get_symbol_type_counts(),
            "most_connected": self._get_most_connected(10),
        }

    def _get_symbol_type_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for sym in self.symbols.values():
            counts[sym.symbol_type] += 1
        return dict(counts)

    def _get_most_connected(self, n: int) -> List[Dict]:
        degrees = [
            (node, self.graph.in_degree(node) + self.graph.out_degree(node))
            for node in self.graph.nodes()
            if node in self.symbols
        ]
        degrees.sort(key=lambda x: x[1], reverse=True)
        result: List[Dict] = []
        for node, degree in degrees[:n]:
            sym = self.symbols[node]
            result.append({
                "name": node,
                "short_name": sym.short_name,
                "type": sym.symbol_type,
                "total_connections": degree,
                "incoming": self.graph.in_degree(node),
                "outgoing": self.graph.out_degree(node),
            })
        return result

    # ──────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────

    def load_from_db(self) -> bool:
        """Load graph from SQLite. Returns True if data was found."""
        if not self.db_path or not Path(self.db_path).exists():
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='symbols'")
            if not cursor.fetchone():
                return False

            cursor.execute("SELECT name, short_name, symbol_type, file_path, line_start, line_end, column_start, column_end, parent FROM symbols")
            for row in cursor.fetchall():
                sym = Symbol(
                    name=row[0],
                    short_name=row[1],
                    symbol_type=row[2],
                    file_path=row[3],
                    line_start=row[4],
                    line_end=row[5],
                    column_start=row[6] or 0,
                    column_end=row[7] or 0,
                    parent=row[8],
                )
                self.add_symbol(sym)

            cursor.execute("SELECT caller, callee, call_type, file_path, line FROM calls")
            for row in cursor.fetchall():
                edge = CallEdge(
                    caller=row[0],
                    callee=row[1],
                    call_type=row[2],
                    file_path=row[3],
                    line=row[4],
                )
                self.add_call(edge)

            return len(self.symbols) > 0
        except Exception:
            return False
        finally:
            conn.close()

    def save_to_db(self) -> None:
        """Save graph to SQLite."""
        if not self.db_path:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                name TEXT PRIMARY KEY,
                short_name TEXT,
                symbol_type TEXT,
                file_path TEXT,
                line_start INTEGER,
                line_end INTEGER,
                column_start INTEGER,
                column_end INTEGER,
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

        cursor.execute("DELETE FROM symbols")
        cursor.execute("DELETE FROM calls")

        for sym in self.symbols.values():
            cursor.execute(
                "INSERT INTO symbols VALUES (?,?,?,?,?,?,?,?,?)",
                (sym.name, sym.short_name, sym.symbol_type, sym.file_path,
                 sym.line_start, sym.line_end, sym.column_start, sym.column_end, sym.parent),
            )

        for u, v, data in self.graph.edges(data=True):
            cursor.execute(
                "INSERT OR IGNORE INTO calls VALUES (?,?,?,?,?)",
                (u, v, data.get("call_type", "direct_call"),
                 data.get("file_path", ""), data.get("line", 0)),
            )

        conn.commit()
        conn.close()


# ══════════════════════════════════════════════════════════════
# GraphBuilder — parse source files into CodeGraph
# ══════════════════════════════════════════════════════════════

class GraphBuilder:
    """Builds a CodeGraph from source files using Tree-sitter."""

    DEFAULT_EXCLUDES = [
        "**/test_*.py", "**/tests/**", "**/node_modules/**",
        "**/.git/**", "**/__pycache__/**", "**/*.min.js",
        "**/dist/**", "**/build/**", "**/venv/**", "**/.venv/**",
    ]

    # File extensions handled per language
    EXT_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
    }

    def __init__(
        self,
        repo_path: str,
        db_path: str = ".code_graph.db",
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.db_path = db_path
        self.exclude_patterns = exclude_patterns or self.DEFAULT_EXCLUDES
        self.graph = CodeGraph(db_path)
        self.parsers: Dict[str, Parser] = {}
        self.diagnostics = BuildDiagnostics()
        self._init_parsers()

    # ──────────────────────────────────────────────────────────
    # Parser initialisation — LOUD on failure
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _make_parser(lang_capsule_or_fn) -> "Optional[Parser]":
        """
        Build a tree-sitter Parser handling all API styles:
          - tree-sitter >= 0.24: language may already be a Language object
          - tree-sitter >= 0.22: Parser(Language(capsule))
          - tree-sitter <  0.22: parser.set_language(Language(capsule))
        Also handles grammars that export language as a callable vs a capsule.
        """
        if not _TREE_SITTER_AVAILABLE:
            return None
        try:
            obj = lang_capsule_or_fn() if callable(lang_capsule_or_fn) else lang_capsule_or_fn
            if isinstance(obj, Language):
                lang = obj
            else:
                lang = Language(obj)
            try:
                return Parser(lang)
            except TypeError:
                p = Parser()
                p.set_language(lang)
                return p
        except Exception as exc:
            # LOUD: never fail silently — report which grammar broke
            _stderr(f"  [WARN] tree-sitter parser init failed: {exc}")
            return None

    def _init_parsers(self) -> None:
        if not _TREE_SITTER_AVAILABLE:
            _stderr("[WARN] tree-sitter package not installed — parsing disabled")
            _stderr("        Install with:  pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-go")
            return

        lang_map: Dict[str, Callable] = {}

        try:
            from tree_sitter_python import language as python_language
            lang_map["python"] = python_language
        except ImportError:
            _stderr("[WARN] tree-sitter-python not installed — Python files will be skipped")
            self.diagnostics.warn("tree-sitter-python not installed")
        except Exception as exc:
            _stderr(f"[ERROR] tree-sitter-python crashed during import: {exc}")
            self.diagnostics.error(f"tree-sitter-python import crash: {exc}")

        try:
            from tree_sitter_javascript import language as js_language
            lang_map["javascript"] = js_language
            lang_map["typescript"] = js_language  # shared parser
        except ImportError:
            _stderr("[WARN] tree-sitter-javascript not installed — JS/TS files will be skipped")
            self.diagnostics.warn("tree-sitter-javascript not installed")
        except Exception as exc:
            _stderr(f"[ERROR] tree-sitter-javascript crashed during import: {exc}")
            self.diagnostics.error(f"tree-sitter-javascript import crash: {exc}")

        try:
            from tree_sitter_go import language as go_language
            lang_map["go"] = go_language
        except ImportError:
            _stderr("[WARN] tree-sitter-go not installed — Go files will be skipped")
            self.diagnostics.warn("tree-sitter-go not installed")
        except Exception as exc:
            _stderr(f"[ERROR] tree-sitter-go crashed during import: {exc}")
            self.diagnostics.error(f"tree-sitter-go import crash: {exc}")

        for lang_name, lang_fn in lang_map.items():
            p = self._make_parser(lang_fn)
            if p:
                self.parsers[lang_name] = _stderr(f"[INFO] parser loaded: {lang_name}") or p
            else:
                _stderr(f"[WARN] could not create parser for {lang_name}")
                self.diagnostics.warn(f"parser for {lang_name} failed to initialise")

        if not self.parsers:
            _stderr("[ERROR] No tree-sitter parsers loaded. Graph building will produce 0 symbols.")

    # ──────────────────────────────────────────────────────────
    # File discovery
    # ──────────────────────────────────────────────────────────

    def _should_exclude(self, path: Path) -> bool:
        path_str = str(path).replace("\\", "/")
        for pattern in self.exclude_patterns:
            regex = pattern.replace("**", ".*").replace("*", "[^/]*").replace("?", ".")
            if re.search(regex, path_str):
                return True
        return False

    def _get_language(self, file_path: Path) -> Optional[str]:
        return self.EXT_MAP.get(file_path.suffix.lower())

    # ──────────────────────────────────────────────────────────
    # File hashing — for incremental rebuilds
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _file_hash(path: Path) -> str:
        """SHA-256 of file contents."""
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            return ""

    # ──────────────────────────────────────────────────────────
    # Public: detect changed files via git diff
    # ──────────────────────────────────────────────────────────

    def get_changed_files(self, base: str = "HEAD") -> List[str]:
        """
        Return list of relative file paths (forward-slash normalised)
        that are tracked by git and have been modified/added/deleted
        compared to *base* (default HEAD).
        Falls back to all indexed files if git is unavailable.
        """
        try:
            import subprocess
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=AM", base],
                capture_output=True, text=True, cwd=str(self.repo_path), timeout=10,
            )
            if result.returncode == 0:
                return [p.replace("\\", "/") for p in result.stdout.strip().splitlines() if p]
        except Exception:
            pass
        # Fallback: return all currently-indexed files
        return list(self.graph.file_symbols.keys())

    # ──────────────────────────────────────────────────────────
    # Public: incremental rebuild
    # ──────────────────────────────────────────────────────────

    def build_incremental(self, changed_files: Optional[List[str]] = None) -> Dict:
        """
        Re-parse only the files whose contents have changed.
        If *changed_files* is None, auto-detect via git diff.
        Falls back to full build if no prior hash data exists.
        """
        t0 = time.time()

        # Auto-detect if not provided
        if changed_files is None:
            changed_files = self.get_changed_files()

        if not changed_files:
            # Nothing changed — try loading from DB
            if self.graph.load_from_db():
                elapsed = time.time() - t0
                return {
                    "files_processed": 0,
                    "symbols_found": len(self.graph.symbols),
                    "edges_found": self.graph.number_of_edges(),
                    "repo_path": str(self.repo_path),
                    "incremental": True,
                    "unchanged": True,
                    "elapsed_s": round(elapsed, 2),
                    "diagnostics": self.diagnostics.to_summary(),
                }

        # Build the full graph from scratch (safe but we only re-parse changed)
        return self.build(changed_files_only=changed_files)

    # ──────────────────────────────────────────────────────────
    # Public: full / partial build
    # ──────────────────────────────────────────────────────────

    def build(self, changed_files_only: Optional[List[str]] = None) -> Dict:
        """
        Build the code graph.
        If *changed_files_only* is provided, only those files are parsed
        and the old data for them is removed first (incremental update).
        """
        t0 = time.time()
        incremental = changed_files_only is not None and len(changed_files_only) > 0

        # If incremental, remove old data for changed files first
        if incremental:
            for fp in changed_files_only:
                self.graph.remove_file(fp)

        # Phase 1: parse all files and collect raw symbols + raw calls
        all_symbols: List[Symbol] = []
        all_raw_calls: List[CallEdge] = []
        files_processed = 0

        if incremental:
            # Only parse the changed files
            for rel_path in changed_files_only:
                full = self.repo_path / rel_path.replace("/", os.sep)
                if not full.exists():
                    self.diagnostics.warn(f"File not found (deleted?): {rel_path}")
                    continue
                language = self._get_language(full)
                if not language or language not in self.parsers:
                    self.diagnostics.files_skipped += 1
                    continue
                try:
                    symbols, calls = self._parse_file(full, language)
                    all_symbols.extend(symbols)
                    all_raw_calls.extend(calls)
                    files_processed += 1
                    self.diagnostics.files_parsed += 1
                except Exception as e:
                    _stderr(f"[ERROR] could not parse {full}: {e}")
                    self.diagnostics.files_failed += 1
        else:
            # Full rebuild: scan the repo
            for ext in ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go"]:
                for file_path in self.repo_path.rglob(ext):
                    if self._should_exclude(file_path):
                        self.diagnostics.files_skipped += 1
                        continue
                    language = self._get_language(file_path)
                    if not language or language not in self.parsers:
                        self.diagnostics.files_skipped += 1
                        continue
                    try:
                        symbols, calls = self._parse_file(file_path, language)
                        all_symbols.extend(symbols)
                        all_raw_calls.extend(calls)
                        files_processed += 1
                        self.diagnostics.files_parsed += 1
                    except Exception as e:
                        _stderr(f"[ERROR] could not parse {file_path}: {e}")
                        self.diagnostics.files_failed += 1

        # Phase 2: add all symbols to the graph (populates _short_name_index)
        symbols_found = 0
        for sym in all_symbols:
            self.graph.add_symbol(sym)
            symbols_found += 1

        # Phase 3: resolve call edges now that the index is fully populated
        edges_found = 0
        resolved_count = 0
        unresolved_count = 0
        for call in all_raw_calls:
            short_name = call.callee
            if short_name in self.graph.symbols:
                pass  # already fully-qualified
            else:
                resolved = self.graph._short_name_index.get(short_name)
                if resolved and len(resolved) == 1:
                    call.callee = resolved[0]
                    resolved_count += 1
                elif resolved and len(resolved) > 1:
                    call.callee = resolved[0]  # best-effort: first match
                    resolved_count += 1
                else:
                    unresolved_count += 1
                # else: leave as bare short name
            self.graph.add_call(call)
            edges_found += 1

        # Store file hashes for future incremental builds
        if not incremental:
            for sym in all_symbols:
                full_path = self.repo_path / sym.file_path.replace("/", os.sep)
                if full_path.exists():
                    self.graph._file_hashes[sym.file_path] = self._file_hash(full_path)

        # Persist
        self.graph.save_to_db()

        elapsed = time.time() - t0
        result = {
            "files_processed": files_processed,
            "symbols_found": symbols_found,
            "edges_found": edges_found,
            "repo_path": str(self.repo_path),
            "incremental": incremental,
            "elapsed_s": round(elapsed, 2),
            "call_resolution": {
                "resolved": resolved_count,
                "unresolved": unresolved_count,
            },
            "diagnostics": self.diagnostics.to_summary(),
        }

        # Print summary to stderr (visible, doesn't pollute MCP stdout)
        if incremental:
            _stderr(f"[INFO] Incremental build: {files_processed} files, {symbols_found} new symbols, {edges_found} edges ({elapsed:.1f}s)")
        else:
            _stderr(f"[INFO] Full build: {files_processed} files, {symbols_found} symbols, {edges_found} edges ({elapsed:.1f}s)")

        if self.diagnostics.warnings:
            _stderr(f"[WARN] {len(self.diagnostics.warnings)} warning(s) during build")
            for w in self.diagnostics.warnings[:5]:
                _stderr(f"        - {w}")
        if self.diagnostics.errors:
            _stderr(f"[ERROR] {len(self.diagnostics.errors)} error(s) during build")
            for e in self.diagnostics.errors[:5]:
                _stderr(f"        - {e}")

        return result

    # ──────────────────────────────────────────────────────────
    # Parsing
    # ──────────────────────────────────────────────────────────

    def _parse_file(self, file_path: Path, language: str) -> Tuple[List[Symbol], List[CallEdge]]:
        relative_path = str(file_path.relative_to(self.repo_path)).replace("\\", "/")
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return [], []

        parser = self.parsers.get(language)
        if not parser:
            return [], []

        tree = parser.parse(source.encode())

        if language == "python":
            return self._parse_python(tree, source, relative_path)
        elif language in ("javascript", "typescript"):
            return self._parse_js(tree, source, relative_path)
        elif language == "go":
            return self._parse_go(tree, source, relative_path)
        return [], []

    # ──────────────────────────────────────────────────────────
    # Python parser
    # ──────────────────────────────────────────────────────────

    def _parse_python(self, tree, source: str, file_path: str) -> Tuple[List[Symbol], List[CallEdge]]:
        symbols: List[Symbol] = []
        calls: List[CallEdge] = []

        def text(node: Node) -> str:
            return source[node.start_byte:node.end_byte]

        def visit(node: Node, class_name: Optional[str] = None) -> None:
            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    cname = text(name_node)
                    key = make_symbol_key(file_path, cname)
                    symbols.append(Symbol(
                        name=key, short_name=cname, symbol_type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                    ))
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            visit(child, cname)
                return

            elif node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    fname = text(name_node)
                    if class_name:
                        qualified = f"{class_name}.{fname}"
                        sym_type = "method"
                    else:
                        qualified = fname
                        sym_type = "function"
                    key = make_symbol_key(file_path, qualified)
                    symbols.append(Symbol(
                        name=key, short_name=qualified, symbol_type=sym_type,
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                        parent=class_name,
                    ))
                    body = node.child_by_field_name("body")
                    if body:
                        self._collect_python_calls(body, key, file_path, source, calls)
                    body2 = node.child_by_field_name("body")
                    if body2:
                        for child in body2.children:
                            visit(child, class_name)
                return

            for child in node.children:
                visit(child, class_name)

        visit(tree.root_node)
        return symbols, calls

    def _collect_python_calls(self, node: Node, caller_key: str, file_path: str, source: str, calls: List[CallEdge]) -> None:
        def text(n: Node) -> str:
            return source[n.start_byte:n.end_byte]

        if node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                raw = text(func_node)
                if "(" not in raw:
                    callee_short = raw.split(".")[-1] if "." in raw else raw
                    # NOTE: resolution happens in build() Phase 3,
                    # after _short_name_index is fully populated.
                    calls.append(CallEdge(
                        caller=caller_key,
                        callee=callee_short,
                        call_type="direct_call",
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                    ))

        for child in node.children:
            self._collect_python_calls(child, caller_key, file_path, source, calls)

    # ──────────────────────────────────────────────────────────
    # JavaScript / TypeScript parser
    # ──────────────────────────────────────────────────────────

    def _parse_js(self, tree, source: str, file_path: str) -> Tuple[List[Symbol], List[CallEdge]]:
        symbols: List[Symbol] = []
        calls: List[CallEdge] = []

        def text(node: Node) -> str:
            return source[node.start_byte:node.end_byte]

        def visit(node: Node, class_name: Optional[str] = None, current_func_key: Optional[str] = None) -> None:
            if node.type in ("class_declaration", "class"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    cname = text(name_node)
                    key = make_symbol_key(file_path, cname)
                    symbols.append(Symbol(
                        name=key, short_name=cname, symbol_type="class",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                    ))
                    body = node.child_by_field_name("body")
                    if body:
                        for child in body.children:
                            visit(child, cname, current_func_key)
                return

            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    mname = text(name_node)
                    qualified = f"{class_name}.{mname}" if class_name else mname
                    key = make_symbol_key(file_path, qualified)
                    symbols.append(Symbol(
                        name=key, short_name=qualified, symbol_type="method",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                        parent=class_name,
                    ))
                    body = node.child_by_field_name("body")
                    if body:
                        self._collect_js_calls(body, key, file_path, source, calls)
                        for child in body.children:
                            visit(child, class_name, key)
                return

            elif node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    fname = text(name_node)
                    key = make_symbol_key(file_path, fname)
                    symbols.append(Symbol(
                        name=key, short_name=fname, symbol_type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                    ))
                    body = node.child_by_field_name("body")
                    if body:
                        self._collect_js_calls(body, key, file_path, source, calls)
                        for child in body.children:
                            visit(child, class_name, key)
                return

            elif node.type == "variable_declarator":
                name_node = node.child_by_field_name("name")
                value_node = node.child_by_field_name("value")
                if name_node and value_node and value_node.type in ("arrow_function", "function"):
                    fname = text(name_node)
                    key = make_symbol_key(file_path, fname)
                    symbols.append(Symbol(
                        name=key, short_name=fname, symbol_type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                    ))
                    body = value_node.child_by_field_name("body")
                    if body:
                        self._collect_js_calls(body, key, file_path, source, calls)
                        for child in body.children:
                            visit(child, class_name, key)
                    return

            for child in node.children:
                visit(child, class_name, current_func_key)

        visit(tree.root_node)
        return symbols, calls

    def _collect_js_calls(self, node: Node, caller_key: str, file_path: str, source: str, calls: List[CallEdge]) -> None:
        def text(n: Node) -> str:
            return source[n.start_byte:n.end_byte]

        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                raw = text(func_node)
                if "(" not in raw:
                    callee_short = raw.split(".")[-1]
                    calls.append(CallEdge(
                        caller=caller_key,
                        callee=callee_short,
                        call_type="direct_call",
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                    ))

        for child in node.children:
            self._collect_js_calls(child, caller_key, file_path, source, calls)

    # ──────────────────────────────────────────────────────────
    # Go parser
    # ──────────────────────────────────────────────────────────

    def _parse_go(self, tree, source: str, file_path: str) -> Tuple[List[Symbol], List[CallEdge]]:
        symbols: List[Symbol] = []
        calls: List[CallEdge] = []

        def text(node: Node) -> str:
            return source[node.start_byte:node.end_byte]

        def visit(node: Node) -> None:
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    fname = text(name_node)
                    key = make_symbol_key(file_path, fname)
                    symbols.append(Symbol(
                        name=key, short_name=fname, symbol_type="function",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                    ))
                    body = node.child_by_field_name("body")
                    if body:
                        self._collect_go_calls(body, key, file_path, source, calls)

            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                recv_node = node.child_by_field_name("receiver")
                receiver_type = ""
                if recv_node:
                    recv_text = text(recv_node)
                    m = re.search(r"\*?(\w+)\s*\)", recv_text)
                    if m:
                        receiver_type = m.group(1)
                if name_node:
                    mname = text(name_node)
                    qualified = f"{receiver_type}.{mname}" if receiver_type else mname
                    key = make_symbol_key(file_path, qualified)
                    symbols.append(Symbol(
                        name=key, short_name=qualified, symbol_type="method",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        column_start=node.start_point[1],
                        column_end=node.end_point[1],
                        parent=receiver_type or None,
                    ))
                    body = node.child_by_field_name("body")
                    if body:
                        self._collect_go_calls(body, key, file_path, source, calls)

            elif node.type == "type_declaration":
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            tname = text(name_node)
                            key = make_symbol_key(file_path, tname)
                            symbols.append(Symbol(
                                name=key, short_name=tname, symbol_type="class",
                                file_path=file_path,
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                                column_start=node.start_point[1],
                                column_end=node.end_point[1],
                            ))

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return symbols, calls

    def _collect_go_calls(self, node: Node, caller_key: str, file_path: str, source: str, calls: List[CallEdge]) -> None:
        def text(n: Node) -> str:
            return source[n.start_byte:n.end_byte]

        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                raw = text(func_node)
                if "(" not in raw:
                    callee_short = raw.split(".")[-1]
                    calls.append(CallEdge(
                        caller=caller_key,
                        callee=callee_short,
                        call_type="direct_call",
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                    ))

        for child in node.children:
            self._collect_go_calls(child, caller_key, file_path, source, calls)
