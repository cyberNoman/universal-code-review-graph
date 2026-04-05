# Universal Code Review Graph - Usage Examples

## Example 1: Basic Code Review

```
User: Build the code graph for my repository at /home/user/myproject

AI: [Calls build_graph with repo_path="/home/user/myproject"]

Result: {
  "status": "success",
  "message": "Graph built successfully",
  "stats": {
    "files_processed": 42,
    "symbols_found": 156,
    "edges_found": 289,
    "repo_path": "/home/user/myproject"
  }
}
```

## Example 2: Review Pull Request Changes

```
User: Review these changed files: src/parser.py, src/graph.py

AI: [Calls review_changes with changed_files]

Result: {
  "changed_files": ["src/parser.py", "src/graph.py"],
  "impacted_symbols": [
    "parse_source",
    "build_call_graph", 
    "resolve_imports",
    "get_neighbors",
    "to_json",
    "export_dot",
    "validate_graph"
  ],
  "total_impacted": 7,
  "upstream_count": 3,
  "downstream_count": 4,
  "files_to_review": [
    "src/parser.py",
    "src/graph.py",
    "src/api/routes.py"
  ]
}

AI: Based on the graph analysis, your changes to `src/parser.py` and 
`src/graph.py` impact 7 functions total. Here are the key areas to review:

1. **parse_source()** - Modified parsing logic affects 3 upstream callers
2. **build_call_graph()** - Changes propagate to 4 downstream functions
3. **validate_graph()** - Validation now covers new edge cases

I recommend checking `src/api/routes.py` as it uses the modified graph functions.
```

## Example 3: Impact Analysis

```
User: What functions depend on parse_source()?

AI: [Calls get_impact with symbol="parse_source"]

Result: {
  "symbol": "parse_source",
  "upstream": ["main", "cli_main", "test_parser"],
  "downstream": [
    "build_call_graph",
    "resolve_imports",
    "get_neighbors"
  ],
  "upstream_count": 3,
  "downstream_count": 3
}

AI: The function `parse_source()` has:
- **3 upstream callers**: main, cli_main, test_parser
- **3 downstream dependencies**: build_call_graph, resolve_imports, get_neighbors

If you modify `parse_source()`, you'll need to verify these 6 related functions.
```

## Example 4: Find Code Paths

```
User: Show me how main() calls validate_graph()

AI: [Calls find_paths with source="main", target="validate_graph"]

Result: {
  "source": "main",
  "target": "validate_graph",
  "paths_found": 2,
  "paths": [
    ["main", "parse_source", "build_call_graph", "validate_graph"],
    ["main", "cli_main", "build_call_graph", "validate_graph"]
  ]
}

AI: There are 2 call paths from `main()` to `validate_graph()`:

**Path 1:**
main → parse_source → build_call_graph → validate_graph

**Path 2:**
main → cli_main → build_call_graph → validate_graph
```

## Example 5: Search Symbols

```
User: Find all functions related to "parse"

AI: [Calls search_symbols with query="parse*"]

Result: {
  "query": "parse*",
  "matches_found": 5,
  "symbols": [
    {"name": "parse_source", "symbol_type": "function", ...},
    {"name": "parse_imports", "symbol_type": "function", ...},
    {"name": "parse_class", "symbol_type": "function", ...},
    {"name": "Parser", "symbol_type": "class", ...},
    {"name": "test_parse", "symbol_type": "function", ...}
  ]
}
```

## Token Savings Comparison

### Without Code Graph:
```
Changed files: 2 files
Files read by AI: 15 files (entire codebase context)
Tokens used: ~12,000
```

### With Code Graph:
```
Changed files: 2 files
Graph query: 1 call
Impacted symbols: 7 functions
Tokens used: ~1,800
Savings: 6.7×
```
