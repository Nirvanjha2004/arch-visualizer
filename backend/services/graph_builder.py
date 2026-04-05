"""
Graph Builder — Steps 5 & 6 of the pipeline.

Responsibilities:
  - Receive a list of FileMetadata objects
  - Build a Directed Graph (DiGraph) using NetworkX
      Nodes  → files / modules
      Edges  → directed import/dependency relationships
  - Prune the graph:
      - Remove isolated nodes (no edges)
      - Run DFS to keep only nodes reachable from high-degree hubs
  - Summarise the graph topology into a clean JSON-serialisable dict
    that will be handed to the LangGraph agent

Graph JSON schema:
  {
    "node_count": int,
    "edge_count": int,
    "nodes": [
      {
        "id": "src/app.py",
        "label": "app",
        "type": "file|module",
        "language": "python",
        "classes": [...],
        "functions": [...],
        "has_external_apis": bool,
        "in_degree": int,
        "out_degree": int
      }, ...
    ],
    "edges": [
      { "source": "src/app.py", "target": "src/db.py", "relation": "imports" },
      ...
    ],
    "hubs": ["src/app.py", ...],   # top-5 nodes by in-degree (most depended-upon)
    "entry_points": [...],          # nodes with 0 in-degree (nothing imports them)
    "clusters": { "cluster_name": ["node_id", ...] }
  }
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

import networkx as nx

from services.ast_parser import FileMetadata


# ── Helpers ────────────────────────────────────────────────────────────────────

def _module_name_from_path(path: str) -> str:
    """Convert a file path to a dot-style module name."""
    name = path.replace("\\", "/")
    # Strip common source roots
    for prefix in ("src/", "lib/", "app/", "backend/", "frontend/src/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Drop extension
    name = os.path.splitext(name)[0]
    # Replace path separators with dots
    return name.replace("/", ".").replace("\\", ".")


def _label(path: str) -> str:
    """Short human-readable label — just the basename without extension."""
    base = os.path.basename(path)
    return os.path.splitext(base)[0]


def _resolve_import_to_node(
    import_str: str,
    node_ids: set[str],
    path_to_module: dict[str, str],
    module_to_path: dict[str, str],
) -> str | None:
    """
    Try to resolve an import string to one of our known file nodes.
    Returns the file path (node id) if found, else None.
    """
    # Direct path match
    if import_str in node_ids:
        return import_str

    # Exact module name match
    if import_str in module_to_path:
        return module_to_path[import_str]

    # Dotted import — try progressively shorter prefixes
    # e.g. "services.github_service" → try "services.github_service", then "services"
    parts = import_str.split(".")
    for length in range(len(parts), 0, -1):
        candidate = ".".join(parts[:length])
        if candidate in module_to_path:
            return module_to_path[candidate]

    # Partial module match — import basename matches module basename
    # e.g. import "github_service" matches module "services.github_service"
    import_base = parts[-1]
    for mod, p in module_to_path.items():
        mod_base = mod.split(".")[-1]
        if mod_base == import_base:
            return p

    # Relative-style JS import ("./ or ../" stripped), also strip extension
    stripped = import_str.lstrip("./").replace("/", ".")
    for candidate in (stripped, os.path.splitext(stripped)[0]):
        if candidate in module_to_path:
            return module_to_path[candidate]

    # Last resort: match on filename basename only
    import_file_base = os.path.splitext(import_str.split("/")[-1])[0]
    for mod, p in module_to_path.items():
        if mod.split(".")[-1] == import_file_base:
            return p

    return None


# ── Main builder ───────────────────────────────────────────────────────────────

def build_graph(file_metadata: list[FileMetadata]) -> dict[str, Any]:
    """
    Build, prune, and summarise the dependency graph.

    Returns a JSON-serialisable dictionary describing the graph topology.
    """
    G = nx.DiGraph()

    # ── Add nodes ──────────────────────────────────────────────────────────────
    path_to_module: dict[str, str] = {}
    module_to_path: dict[str, str] = {}

    for fm in file_metadata:
        G.add_node(
            fm.path,
            label=_label(fm.path),
            language=fm.language,
            imports=fm.imports,
            classes=fm.classes,
            functions=fm.functions,
            has_external_apis=bool(fm.external_apis),
            external_apis=fm.external_apis,
        )
        mod = _module_name_from_path(fm.path)
        path_to_module[fm.path] = mod
        module_to_path[mod] = fm.path

    node_ids = set(G.nodes)

    # ── Add edges (imports → dependency edges) ─────────────────────────────────
    for fm in file_metadata:
        for imp in fm.imports:
            target = _resolve_import_to_node(
                imp, node_ids, path_to_module, module_to_path
            )
            if target and target != fm.path:
                # Skip __init__.py as intermediate — connect directly to the package's files
                if target.endswith("__init__.py"):
                    pkg_dir = target.replace("\\", "/").rsplit("/", 1)[0]
                    for other_fm in file_metadata:
                        other_dir = other_fm.path.replace("\\", "/").rsplit("/", 1)[0]
                        if (other_dir == pkg_dir
                                and not other_fm.path.endswith("__init__.py")):
                            G.add_edge(fm.path, other_fm.path, relation="imports")
                else:
                    G.add_edge(fm.path, target, relation="imports")

    # ── Prune: remove isolated nodes ──────────────────────────────────────────
    isolated = list(nx.isolates(G))
    # Never prune entry-point files or service/agent files — they're architecturally important
    keep_keywords = ("main", "app", "index", "server", "manage", "wsgi", "asgi",
                     "service", "agent", "parser", "builder", "handler", "router")
    isolated = [
        n for n in isolated
        if not any(kw in os.path.basename(n).lower() for kw in keep_keywords)
    ]
    G.remove_nodes_from(isolated)

    # If graph is empty after pruning, re-add all nodes (small repo)
    if G.number_of_nodes() == 0:
        for fm in file_metadata:
            G.add_node(
                fm.path,
                label=_label(fm.path),
                language=fm.language,
                classes=fm.classes,
                functions=fm.functions,
                has_external_apis=bool(fm.external_apis),
                external_apis=fm.external_apis,
            )

    # ── Identify architectural clusters ───────────────────────────────────────
    clusters: dict[str, list[str]] = defaultdict(list)
    for node in G.nodes:
        path_lower = node.lower()
        if any(kw in path_lower for kw in ("route", "controller", "handler", "view")):
            clusters["Controllers / Routes"].append(node)
        elif any(kw in path_lower for kw in ("model", "schema", "entity")):
            clusters["Data Models"].append(node)
        elif any(kw in path_lower for kw in ("db", "database", "repo", "repository", "store", "mongo", "postgres", "mysql", "sqlite")):
            clusters["Database Layer"].append(node)
        elif any(kw in path_lower for kw in ("service", "usecase", "business", "domain")):
            clusters["Services"].append(node)
        elif any(kw in path_lower for kw in ("middleware", "auth", "guard", "interceptor")):
            clusters["Middleware / Auth"].append(node)
        elif any(kw in path_lower for kw in ("util", "helper", "common", "shared", "lib")):
            clusters["Utilities"].append(node)
        elif any(kw in path_lower for kw in ("config", "settings", "env", "constant")):
            clusters["Config"].append(node)
        elif any(kw in path_lower for kw in ("test", "spec", "__test__")):
            clusters["Tests"].append(node)
        else:
            clusters["Core"].append(node)

    # ── Compute summary statistics ─────────────────────────────────────────────
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())

    # Entry points: nodes nobody imports (root modules / app entrypoints)
    entry_points = [n for n, d in in_degrees.items() if d == 0]

    # Hubs: top-5 most-depended-upon nodes
    hubs = sorted(in_degrees, key=lambda n: in_degrees[n], reverse=True)[:5]

    # ── Build output JSON ──────────────────────────────────────────────────────
    nodes_out = []
    for node in G.nodes(data=True):
        n_id, attrs = node
        nodes_out.append(
            {
                "id": n_id,
                "label": attrs.get("label", n_id),
                "language": attrs.get("language", "unknown"),
                "type": "file",
                "imports": attrs.get("imports", [])[:15],
                "classes": attrs.get("classes", [])[:10],
                "functions": attrs.get("functions", [])[:10],
                "has_external_apis": attrs.get("has_external_apis", False),
                "external_api_calls": attrs.get("external_apis", [])[:10],
                "in_degree": in_degrees.get(n_id, 0),
                "out_degree": out_degrees.get(n_id, 0),
            }
        )

    edges_out = [
        {
            "source": u,
            "target": v,
            "relation": data.get("relation", "imports"),
        }
        for u, v, data in G.edges(data=True)
    ]

    return {
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "nodes": nodes_out,
        "edges": edges_out,
        "hubs": hubs,
        "entry_points": entry_points[:10],
        "clusters": {k: v for k, v in clusters.items() if v},
    }
