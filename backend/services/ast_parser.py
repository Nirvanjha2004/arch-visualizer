"""
AST Parser — Step 3 & 4 of the pipeline.

Uses Tree-sitter to generate Abstract Syntax Trees for each source file
and traverses them to extract structural metadata:

  - Import/require statements
  - Function definitions
  - Class definitions
  - Function call expressions (top-level and inside classes)
  - External API call patterns (fetch, axios, requests.get, etc.)

Returns a list of FileMetadata objects — one per parsed file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# tree-sitter >= 0.21 API
from tree_sitter import Language, Node, Parser

# Language grammar packages
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_go as tsgo
import tree_sitter_rust as tsrust
import tree_sitter_java as tsjava


# ── Language setup ─────────────────────────────────────────────────────────────

_PY_LANG  = Language(tspython.language())
_JS_LANG  = Language(tsjavascript.language())
_TS_LANG  = Language(tstypescript.language_typescript())
_TSX_LANG = Language(tstypescript.language_tsx())
_GO_LANG  = Language(tsgo.language())
_RS_LANG  = Language(tsrust.language())
_JV_LANG  = Language(tsjava.language())

_EXT_TO_LANG: dict[str, Language] = {
    ".py":   _PY_LANG,
    ".js":   _JS_LANG,
    ".jsx":  _JS_LANG,
    ".ts":   _TS_LANG,
    ".tsx":  _TSX_LANG,
    ".go":   _GO_LANG,
    ".rs":   _RS_LANG,
    ".java": _JV_LANG,
}


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class FileMetadata:
    """Structural metadata extracted from one source file."""

    path: str                                 # e.g. "src/controllers/user.py"
    language: str                             # "python" | "javascript" | "typescript"
    imports: list[str] = field(default_factory=list)    # imported module names
    classes: list[str] = field(default_factory=list)    # class names defined
    functions: list[str] = field(default_factory=list)  # top-level function names
    calls: list[str] = field(default_factory=list)      # function/method calls observed
    external_apis: list[str] = field(default_factory=list)  # HTTP client calls


# ── Node traversal helpers ─────────────────────────────────────────────────────

def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _children_of_type(node: Node, *types: str) -> list[Node]:
    return [c for c in node.children if c.type in types]


def _walk(node: Node):
    """Depth-first generator over all descendant nodes."""
    yield node
    for child in node.children:
        yield from _walk(child)


# ── Language-specific extractors ───────────────────────────────────────────────

def _extract_python(tree_root: Node, source: bytes) -> tuple[list, list, list, list, list]:
    imports, classes, functions, calls, ext_apis = [], [], [], [], []

    for node in _walk(tree_root):
        t = node.type

        # --- imports ---
        if t == "import_statement":
            for child in node.named_children:
                if child.type in ("dotted_name", "aliased_import"):
                    name = _node_text(child, source).split(" as ")[0].split(".")[0]
                    imports.append(name)

        elif t == "import_from_statement":
            mod_children = [c for c in node.named_children if c.type == "dotted_name"]
            if mod_children:
                imports.append(_node_text(mod_children[0], source).split(".")[0])

        # --- class definitions ---
        elif t == "class_definition":
            name_nodes = _children_of_type(node, "identifier")
            if name_nodes:
                classes.append(_node_text(name_nodes[0], source))

        # --- function definitions ---
        elif t == "function_definition":
            name_nodes = _children_of_type(node, "identifier")
            if name_nodes:
                fn_name = _node_text(name_nodes[0], source)
                functions.append(fn_name)

        # --- function calls ---
        elif t == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                call_text = _node_text(func_node, source)
                calls.append(call_text)
                # Detect HTTP client patterns
                if any(
                    pat in call_text
                    for pat in ("requests.get", "requests.post", "requests.put",
                                "requests.delete", "httpx.get", "httpx.post",
                                "aiohttp.", "urllib.request")
                ):
                    ext_apis.append(call_text)

        # --- decorators: extract HTTP route info (@app.get, @app.post etc.) ---
        elif t == "decorator":
            dec_text = _node_text(node, source)
            if any(m in dec_text for m in (".get(", ".post(", ".put(", ".delete(", ".patch(")):
                ext_apis.append(f"ROUTE:{dec_text.strip()}")

    return imports, classes, functions, calls, ext_apis


def _extract_js_ts(tree_root: Node, source: bytes) -> tuple[list, list, list, list, list]:
    imports, classes, functions, calls, ext_apis = [], [], [], [], []

    for node in _walk(tree_root):
        t = node.type

        # --- ES6 imports: import X from 'module' ---
        if t == "import_statement":
            # tree-sitter stores the module path in the "source" field
            src_node = node.child_by_field_name("source")
            if src_node:
                raw = _node_text(src_node, source).strip("'\"")
                imports.append(raw)
            else:
                # fallback: any string child
                for c in node.named_children:
                    if c.type == "string":
                        imports.append(_node_text(c, source).strip("'\""))

        # --- require() calls ---
        elif t == "call_expression":
            fn_node = node.child_by_field_name("function")
            if fn_node and _node_text(fn_node, source) == "require":
                args = node.child_by_field_name("arguments")
                if args:
                    for sn in args.named_children:
                        if sn.type == "string":
                            imports.append(_node_text(sn, source).strip("'\""))

        # --- class declarations ---
        elif t in ("class_declaration", "class"):
            name_nodes = [c for c in node.named_children if c.type == "identifier"]
            if name_nodes:
                classes.append(_node_text(name_nodes[0], source))

        # --- function declarations ---
        elif t in ("function_declaration", "function", "arrow_function",
                   "method_definition"):
            name_nodes = [c for c in node.named_children if c.type == "identifier"]
            if name_nodes:
                functions.append(_node_text(name_nodes[0], source))

        # --- call expressions ---
        elif t == "call_expression":
            fn_node = node.child_by_field_name("function")
            if fn_node:
                call_text = _node_text(fn_node, source)
                calls.append(call_text)
                if any(pat in call_text for pat in (
                    "fetch", "axios.", "http.", "https.", "request(", "got.", "superagent."
                )):
                    # Try to grab the URL argument too
                    args = node.child_by_field_name("arguments")
                    url_hint = ""
                    if args:
                        for c in args.named_children:
                            txt = _node_text(c, source)
                            if "/api/" in txt or "http" in txt or "${" in txt:
                                url_hint = txt[:80]
                                break
                    ext_apis.append(f"{call_text}({url_hint})" if url_hint else call_text)

    return imports, classes, functions, calls, ext_apis


def _extract_go(tree_root: Node, source: bytes) -> tuple[list, list, list, list, list]:
    imports, classes, functions, calls, ext_apis = [], [], [], [], []

    for node in _walk(tree_root):
        t = node.type

        # import "pkg" or import ( "pkg1" "pkg2" )
        if t == "import_spec":
            path_nodes = [c for c in node.named_children if c.type == "interpreted_string_literal"]
            for pn in path_nodes:
                raw = _node_text(pn, source).strip('"')
                imports.append(raw.split("/")[-1])  # last segment e.g. "fmt", "fiber"

        # struct types act as classes in Go
        elif t == "type_declaration":
            for child in _walk(node):
                if child.type == "type_spec":
                    name_nodes = [c for c in child.named_children if c.type == "type_identifier"]
                    if name_nodes:
                        classes.append(_node_text(name_nodes[0], source))

        # function / method declarations
        elif t in ("function_declaration", "method_declaration"):
            name_nodes = [c for c in node.named_children if c.type == "identifier"]
            if name_nodes:
                functions.append(_node_text(name_nodes[0], source))

        # call expressions
        elif t == "call_expression":
            fn_node = node.child_by_field_name("function")
            if fn_node:
                call_text = _node_text(fn_node, source)
                calls.append(call_text)
                if any(p in call_text for p in ("http.Get", "http.Post", "http.Do",
                                                  "client.Get", "client.Post")):
                    ext_apis.append(call_text)

    return imports, classes, functions, calls, ext_apis


def _extract_rust(tree_root: Node, source: bytes) -> tuple[list, list, list, list, list]:
    imports, classes, functions, calls, ext_apis = [], [], [], [], []

    for node in _walk(tree_root):
        t = node.type

        # use std::collections::HashMap  →  "use_declaration"
        if t == "use_declaration":
            imports.append(_node_text(node, source).replace("use ", "").split("::")[0].strip(";"))

        # struct / enum as classes
        elif t in ("struct_item", "enum_item"):
            name_nodes = [c for c in node.named_children if c.type == "type_identifier"]
            if name_nodes:
                classes.append(_node_text(name_nodes[0], source))

        # fn declarations
        elif t == "function_item":
            name_nodes = [c for c in node.named_children if c.type == "identifier"]
            if name_nodes:
                functions.append(_node_text(name_nodes[0], source))

        # call expressions
        elif t == "call_expression":
            fn_node = node.child_by_field_name("function")
            if fn_node:
                call_text = _node_text(fn_node, source)
                calls.append(call_text)
                if any(p in call_text for p in ("reqwest::", "ureq::", "hyper::")):
                    ext_apis.append(call_text)

    return imports, classes, functions, calls, ext_apis


def _extract_java(tree_root: Node, source: bytes) -> tuple[list, list, list, list, list]:
    imports, classes, functions, calls, ext_apis = [], [], [], [], []

    for node in _walk(tree_root):
        t = node.type

        if t == "import_declaration":
            raw = _node_text(node, source).replace("import ", "").strip(";").strip()
            imports.append(raw.split(".")[-1])  # simple class name

        elif t == "class_declaration":
            name_nodes = [c for c in node.named_children if c.type == "identifier"]
            if name_nodes:
                classes.append(_node_text(name_nodes[0], source))

        elif t == "method_declaration":
            name_nodes = [c for c in node.named_children if c.type == "identifier"]
            if name_nodes:
                functions.append(_node_text(name_nodes[0], source))

        elif t == "method_invocation":
            name_nodes = [c for c in node.named_children if c.type == "identifier"]
            if name_nodes:
                call_text = _node_text(name_nodes[0], source)
                calls.append(call_text)

    return imports, classes, functions, calls, ext_apis

def parse_files(file_contents: dict[str, str]) -> list[FileMetadata]:
    """
    Given a mapping of { file_path: source_code }, return a list of
    FileMetadata objects with extracted structural relationships.
    """
    results: list[FileMetadata] = []

    for path, source_str in file_contents.items():
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        lang = _EXT_TO_LANG.get(ext)
        if lang is None:
            continue

        lang_name = {
            ".py": "python", ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            ".go": "go", ".rs": "rust", ".java": "java",
        }.get(ext, "unknown")

        try:
            parser = Parser(lang)
            source_bytes = source_str.encode("utf-8", errors="replace")
            tree = parser.parse(source_bytes)

            if lang_name == "python":
                imports, classes, functions, calls, ext_apis = _extract_python(tree.root_node, source_bytes)
            elif lang_name in ("javascript", "typescript"):
                imports, classes, functions, calls, ext_apis = _extract_js_ts(tree.root_node, source_bytes)
            elif lang_name == "go":
                imports, classes, functions, calls, ext_apis = _extract_go(tree.root_node, source_bytes)
            elif lang_name == "rust":
                imports, classes, functions, calls, ext_apis = _extract_rust(tree.root_node, source_bytes)
            elif lang_name == "java":
                imports, classes, functions, calls, ext_apis = _extract_java(tree.root_node, source_bytes)
            else:
                imports, classes, functions, calls, ext_apis = [], [], [], [], []

            # ── DEBUG: log node types seen in the tree ──────────────────────
            import logging, os as _os
            if _os.getenv("AST_DEBUG"):
                _log = logging.getLogger("arch-visualizer")
                node_types = {n.type for n in _walk(tree.root_node)}
                _log.info("AST_DEBUG %s | node_types=%s | imports=%s",
                          path, sorted(node_types)[:30], imports[:10])

            def dedup(lst: list[str]) -> list[str]:
                seen: set[str] = set()
                return [x for x in lst if x not in seen and not seen.add(x)]  # type: ignore

            results.append(
                FileMetadata(
                    path=path,
                    language=lang_name,
                    imports=dedup(imports),
                    classes=dedup(classes),
                    functions=dedup(functions),
                    calls=dedup(calls[:50]),
                    external_apis=dedup(ext_apis),
                )
            )
        except Exception:
            results.append(FileMetadata(path=path, language=lang_name))

    return results
