# Contributing to universal-code-review-graph

Thanks for wanting to contribute! This project is open source and community-driven.

## Adding a new language

This is the most impactful contribution. Here's exactly how to do it:

### 1. Install the tree-sitter grammar

```bash
pip install tree-sitter-rust       # Rust
pip install tree-sitter-java       # Java
pip install tree-sitter-cpp        # C / C++
```

### 2. Register the parser in `GraphBuilder._init_parsers()`

```python
# In code_graph.py, inside GraphBuilder._init_parsers():
try:
    from tree_sitter_rust import language as rust_language
    self.parsers["rust"] = Parser(Language(rust_language))
except ImportError:
    pass
```

### 3. Add the file extension mapping

```python
# In GraphBuilder._get_language():
".rs": "rust",
```

### 4. Write the parser method

```python
def _parse_rust(self, tree, source: str, file_path: str) -> Tuple[List[Symbol], List[CallEdge]]:
    symbols = []
    calls = []

    def text(node): return source[node.start_byte:node.end_byte]

    def visit(node, parent_name=None):
        if node.type == "function_item":
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
                    self._collect_rust_calls(body, key, file_path, source, calls)
        for child in node.children:
            visit(child, parent_name)

    visit(tree.root_node)
    return symbols, calls

def _collect_rust_calls(self, node, caller_key, file_path, source, calls):
    def text(n): return source[n.start_byte:n.end_byte]
    if node.type == "call_expression":
        func_node = node.child_by_field_name("function")
        if func_node:
            raw = text(func_node)
            if "(" not in raw:
                callee_short = raw.split("::")[-1]
                resolved = self.graph._short_name_index.get(callee_short)
                callee_key = resolved[0] if resolved else callee_short
                calls.append(CallEdge(
                    caller=caller_key, callee=callee_key,
                    call_type="direct_call", file_path=file_path,
                    line=node.start_point[0] + 1,
                ))
    for child in node.children:
        self._collect_rust_calls(child, caller_key, file_path, source, calls)
```

### 5. Wire it up in `_parse_file()`

```python
elif language == "rust":
    return self._parse_rust(tree, source, relative_path)
```

### 6. Add to requirements.txt

```
tree-sitter-rust>=0.25.0
```

### 7. Submit a PR

That's it! You've added full symbol + call-graph support for a new language.

## Bug reports

Please include:
- OS and Python version
- The language of the repo you were indexing
- Output of `get_stats` if the graph built but gave wrong results
- Minimal reproduction case if possible

## Code style

- Python: follow PEP 8, type hints on all public methods
- TypeScript: strict mode, no `any` on public API surfaces
- No new dependencies without discussion
