"""
LangGraph Agent — Steps 7-10 of the pipeline (React Flow edition).

State machine:
  ┌──────────────────────┐
  │  analyze_architecture│ ──► END
  └──────────────────────┘

The single LLM node receives the compressed NetworkX Graph JSON and outputs
a React Flow-compatible JSON payload:

  {
    "summary": "prose description of architectural patterns",
    "nodes": [
      { "id": "unique_id", "data": { "label": "Display Name" }, "position": { "x": 0, "y": 0 } },
      ...
    ],
    "edges": [
      { "id": "e_src_tgt", "source": "src_id", "target": "tgt_id", "animated": true },
      ...
    ]
  }

The FastAPI layer returns this directly to the React frontend, which renders
it 100% client-side using @xyflow/react — no external services required.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph


# ── LLM factory ───────────────────────────────────────────────────────────────

def _build_llm(provider: str, api_key: str):
    """Return a LangChain chat model based on the configured provider."""
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama3-70b-8192",
            api_key=api_key,
            temperature=0.2,
            max_tokens=4096,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=4096,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert software architect specialising in codebase analysis.
Your task is to analyse a dependency graph JSON extracted from a GitHub repository and
produce a React Flow diagram JSON that visually represents the architecture.

## Output Requirements (STRICT — return ONLY valid JSON, no markdown fences):

{
  "summary": "3-5 sentence prose description of the detected architectural patterns.",
  "nodes": [
    {
      "id": "unique_snake_case_id",
      "data": { "label": "Human-Readable Name" },
      "position": { "x": <integer>, "y": <integer> }
    }
  ],
  "edges": [
    {
      "id": "e_<source_id>_<target_id>",
      "source": "<source node id>",
      "target": "<target node id>",
      "animated": true
    }
  ]
}

## Node & Layout Rules:
- Use a maximum of 20 nodes — pick the most architecturally significant files/modules.
- Group nodes into logical COLUMNS by layer (left-to-right: entry → controllers → services → data):
    Column 0 (x=50):   Entry points / main files
    Column 1 (x=300):  Routes / Controllers / Handlers
    Column 2 (x=550):  Services / Business logic
    Column 3 (x=800):  Models / Schemas / Repositories
    Column 4 (x=1050): Database / Cache / External integrations
    Column 5 (x=1300): Utilities / Config / Shared
- Space nodes VERTICALLY: y = row_index * 120 within each column. Start at y=50.
- Node `id` must be a short, unique snake_case string (e.g., "app_main", "user_controller").
- Node `label` must be a concise human-readable name (e.g., "App Entry", "User Controller").

## Edge Rules:
- Only include edges between nodes that ARE in your node list.
- `source` and `target` must exactly match node `id` values.
- Set `animated: true` on every edge.

## CRITICAL:
- Return ONLY the raw JSON object — no explanation, no code fences, no extra text.
- Every node id referenced in edges MUST exist in the nodes array.
"""

USER_PROMPT_TEMPLATE = """Analyse the following dependency graph extracted from a GitHub repository.
Identify the architectural layers and key dependencies, then produce the React Flow JSON.

Graph JSON:
{graph_json}

Focus on:
- Entry points and main application files (leftmost column)
- API routes / controllers
- Service / business logic layer
- Data models and repositories
- Database / cache integrations (rightmost column)
- Utilities and config (rightmost column)

Assign clear, descriptive labels. Ensure no two nodes share the same x,y position.
"""


# ── Agent State ────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    graph_json: dict[str, Any]        # Input: NetworkX graph topology
    react_flow_nodes: list[dict]      # Output: React Flow nodes array
    react_flow_edges: list[dict]      # Output: React Flow edges array
    arch_summary: str                 # Output: prose architecture description
    error: str                        # Non-empty if anything went wrong


# ── Graph compression ─────────────────────────────────────────────────────────

def _compress_graph(graph_json: dict) -> str:
    """
    Trim the graph to stay within LLM context limits.
    Keeps top 20 nodes by in-degree and the first 40 edges.
    """
    compressed = {
        "node_count":   graph_json.get("node_count"),
        "edge_count":   graph_json.get("edge_count"),
        "hubs":         graph_json.get("hubs", []),
        "entry_points": graph_json.get("entry_points", []),
        "clusters":     graph_json.get("clusters", {}),
        "nodes": sorted(
            graph_json.get("nodes", []),
            key=lambda n: n.get("in_degree", 0),
            reverse=True,
        )[:20],
        "edges": graph_json.get("edges", [])[:40],
    }
    return json.dumps(compressed, indent=2)


# ── LLM validation helpers ────────────────────────────────────────────────────

def _validate_and_fix(parsed: dict) -> dict:
    """
    Ensure nodes and edges are structurally valid.
    Removes edges whose source/target don't exist in the node list.
    """
    nodes = parsed.get("nodes", [])
    edges = parsed.get("edges", [])

    valid_ids = {n["id"] for n in nodes if "id" in n}

    # Fix missing position fields
    for i, node in enumerate(nodes):
        if "position" not in node:
            node["position"] = {"x": (i % 6) * 250 + 50, "y": (i // 6) * 120 + 50}
        if "data" not in node:
            node["data"] = {"label": node.get("id", f"node_{i}")}

    # Drop edges referencing unknown node IDs; ensure animated=true
    clean_edges = []
    for edge in edges:
        if edge.get("source") in valid_ids and edge.get("target") in valid_ids:
            edge["animated"] = True
            if "id" not in edge:
                edge["id"] = f"e_{edge['source']}_{edge['target']}"
            clean_edges.append(edge)

    parsed["nodes"] = nodes
    parsed["edges"] = clean_edges
    return parsed


# ── Node: analyse architecture ────────────────────────────────────────────────

async def analyze_architecture(state: AgentState, llm) -> AgentState:
    """
    Single LLM step: compress graph JSON → call LLM → parse React Flow JSON.
    """
    try:
        compressed = _compress_graph(state["graph_json"])
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=USER_PROMPT_TEMPLATE.format(graph_json=compressed)
            ),
        ]
        response = await llm.ainvoke(messages)
        raw: str = response.content

        # Strip markdown code fences if the LLM wraps output
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"```\s*$", "", raw.strip(), flags=re.MULTILINE)

        # Extract the outermost JSON object
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if not json_match:
            raise ValueError("LLM response did not contain a JSON object")

        parsed = json.loads(json_match.group())
        parsed = _validate_and_fix(parsed)

        return {
            **state,
            "react_flow_nodes": parsed.get("nodes", []),
            "react_flow_edges": parsed.get("edges", []),
            "arch_summary":     parsed.get("summary", ""),
            "error":            "",
        }
    except Exception as exc:
        return {
            **state,
            "react_flow_nodes": [],
            "react_flow_edges": [],
            "error": f"LLM analysis failed: {exc}",
        }


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_agent(llm_provider: str, llm_api_key: str):
    """
    Compile the single-node LangGraph state machine.

    Usage:
        app = build_agent("groq", "gsk_...")
        result = await app.ainvoke(initial_state)
    """
    llm = _build_llm(llm_provider, llm_api_key)

    workflow = StateGraph(AgentState)

    async def _analyze(state: AgentState) -> AgentState:
        return await analyze_architecture(state, llm)

    workflow.add_node("analyze_architecture", _analyze)
    workflow.set_entry_point("analyze_architecture")
    workflow.add_edge("analyze_architecture", END)

    return workflow.compile()


# ── Convenience runner ────────────────────────────────────────────────────────

async def run_agent(
    graph_json: dict[str, Any],
    llm_provider: str,
    llm_api_key: str,
) -> dict[str, Any]:
    """
    End-to-end entry point — call from FastAPI.

    Returns:
      {
        "react_flow_nodes": [...],
        "react_flow_edges": [...],
        "arch_summary": "...",
        "error": ""
      }
    """
    app = build_agent(llm_provider, llm_api_key)

    initial_state: AgentState = {
        "graph_json":       graph_json,
        "react_flow_nodes": [],
        "react_flow_edges": [],
        "arch_summary":     "",
        "error":            "",
    }

    result = await app.ainvoke(initial_state)
    return {
        "react_flow_nodes": result.get("react_flow_nodes", []),
        "react_flow_edges": result.get("react_flow_edges", []),
        "arch_summary":     result.get("arch_summary", ""),
        "error":            result.get("error", ""),
    }
