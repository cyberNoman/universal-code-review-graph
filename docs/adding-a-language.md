# Adding a New Language

This is a step-by-step walkthrough for adding full symbol + call-graph support
for a new language (Rust, Java, C++, Ruby, etc.).

You'll need about 60-80 lines of Python. Here's the complete recipe.

---

## Example: Adding Rust support

### Step 1 — Install the tree-sitter grammar

```bash
pip install tree-sitter-rust
```

Verify it works:
```python
from tree_sitter_rust import language as rust_language
from tree_sitter import Language, Parser
p = Parser(Language(rust_language))
print("Rust parser ready")
```

### Step 2 — Add to requirements.txt

In `universal-code-graph/requirements.txt`, add:
```
tree-sitter-rust>=0.25.0
```

### Step 3 — Register in `_init_parsers()`

In `code_graph.py`, inside `GraphBuilder._init_parsers()`:

```python
try:
    from tree_sitter_rust import language as rust_language
    self.parsers["rust"] = Parser(Language(rust_language))
except ImportError:
    pass
```

### Step 4 — Add the file extension

In `GraphBuilder._get_language()`:

```python
".rs": "rust",
```

### Step 5 — Write the symbol parser

Add this method to `GraphBuilder`:

```python
def _parse_rust(
    self, tree, source: str, file_path: str
) -> Tuple[List[Symbol], List[CallEdge]]:
    """Parse Rust AST for functions, structs, and call edges."""
    symbols: List[Symbol] = []
    calls: List[CallEdge] = []

    def text(node: Node) -> str:
        return source[node.start_byte:node.end_byte]

    def visit(node: Node, impl_type: Optional[str] = None) -> None:
        # ── Free function ──────────────────────────────────
        if node.type == "function_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                fname = text(name_node)
                qualified = f"{impl_type}.{fname}" if impl_type else fname
                key = make_symbol_key(file_path, qualified)
                symbols.append(Symbol(
                    name=key, short_name=qualified,
                    symbol_type="method" if impl_type else "function",
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    column_start=node.start_point[1],
                    column_end=node.end_point[1],
                    parent=impl_type,
                ))
                body = node.child_by_field_name("body")
                if body:
                    self._collect_rust_calls(body, key, file_path, source, calls)
                return

        # ── Struct / enum ──────────────────────────────────
        elif node.type in ("struct_item", "enum_item"):
            name_node = node.child_by_field_name("name")
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

        # ── impl block — visit methods with receiver type ──
        elif node.type == "impl_item":
            type_node = node.child_by_field_name("type")
            impl_name = text(type_node) if type_node else None
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    visit(child, impl_name)
            return

        # Generic recursion
        for child in node.children:
            visit(child, impl_type)

    visit(tree.root_node)
    return symbols, calls


def _collect_rust_calls(
    self, node: Node, caller_key: str,
    file_path: str, source: str, calls: List[CallEdge]
) -> None:
    """Find function calls within a Rust function body."""
    def text(n: Node) -> str:
        return source[n.start_byte:n.end_byte]

    if node.type == "call_expression":
        func_node = node.child_by_field_name("function")
        if func_node:
            raw = text(func_node)
            if "(" not in raw:
                # Strip module paths: std::fs::read → read
                callee_short = raw.split("::")[-1]
                resolved = self.graph._short_name_index.get(callee_short)
                callee_key = resolved[0] if resolved else callee_short
                calls.append(CallEdge(
                    caller=caller_key, callee=callee_key,
                    call_type="direct_call",
                    file_path=file_path,
                    line=node.start_point[0] + 1,
                ))

    for child in node.children:
        self._collect_rust_calls(child, caller_key, file_path, source, calls)
```

### Step 6 — Wire into `_parse_file()`

In `GraphBuilder._parse_file()`, add:

```python
elif language == "rust":
    return self._parse_rust(tree, source, relative_path)
```

### Step 7 — Test it

```python
from pathlib import Path
from code_graph import GraphBuilder

# Write a test file
Path("/tmp/test.rs").write_text("""
struct Parser {
    input: String,
}

impl Parser {
    fn new(input: String) -> Self {
        Parser { input }
    }

    fn parse(&self) -> Vec<Token> {
        self.tokenize()
    }

    fn tokenize(&self) -> Vec<Token> {
        vec![]
    }
}

fn main() {
    let p = Parser::new("hello".to_string());
    p.parse();
}
""")

builder = GraphBuilder(repo_path="/tmp")
stats = builder.build()
print("Symbols:", list(builder.graph.symbols.keys()))
print("Edges:", list(builder.graph.graph.edges()))
print("Impact of tokenize:", builder.graph.get_impact("tokenize"))
```

Expected:
```
Symbols: ['/tmp/test.rs::Parser', '/tmp/test.rs::Parser.new', '/tmp/test.rs::Parser.parse', ...]
Edges: [('test.rs::Parser.parse', 'test.rs::Parser.tokenize'), ...]
Impact of tokenize: {'upstream': ['Parser.parse', 'main'], ...}
```

### Step 8 — Submit a PR

That's it! Open a pull request with:
- The changes to `code_graph.py`
- The updated `requirements.txt`
- A test file in `tests/test_rust_parser.py`

---

## Language grammar discovery

To find the correct tree-sitter node type names for a language:

```python
from tree_sitter_rust import language as rust_language
from tree_sitter import Language, Parser

p = Parser(Language(rust_language))
code = b"fn hello() { world(); }"
tree = p.parse(code)

def print_tree(node, indent=0):
    print("  " * indent + f"{node.type}: '{code[node.start_byte:node.end_byte].decode()[:30]}'")
    for child in node.children:
        print_tree(child, indent + 1)

print_tree(tree.root_node)
```

This prints the full CST — you'll see exactly which node types to match.

---

## Language-specific notes

### Java

Key node types:
- `method_declaration` → methods
- `class_declaration` → classes
- `interface_declaration` → interfaces
- `method_invocation` → calls

```bash
pip install tree-sitter-java
```

### C / C++

Key node types:
- `function_definition` → functions
- `struct_specifier` / `class_specifier` → types
- `call_expression` → calls

```bash
pip install tree-sitter-cpp
```

### Ruby

Key node types:
- `method` → methods
- `class` → classes
- `call` → calls

```bash
pip install tree-sitter-ruby
```

### Swift

Key node types:
- `function_declaration` → functions
- `class_declaration` / `struct_declaration` → types
- `call_expression` → calls

```bash
pip install tree-sitter-swift
```
