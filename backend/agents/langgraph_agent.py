"""
LangGraph Agent — Triple-output pipeline (LLD + HLD + ERD).

State machine:
  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
  │ analyze_lld │──►│ analyze_hld │──►│ analyze_erd │──► END
  └─────────────┘   └─────────────┘   └─────────────┘

Node 1 (LLD): detailed module-level dependency graph → React Flow nodes/edges
Node 2 (HLD): abstract infrastructure block diagram → React Flow nodes/edges
              each HLD node carries data.systemType for icon rendering
Node 3 (ERD): entity-relationship diagram from ORM models → React Flow nodes/edges
              each ERD node carries data.modelName + data.fields[]
"""

from __future__ import annotations

import json
import re
import asyncio
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph


# ── LLM factory ───────────────────────────────────────────────────────────────

def _build_llm(provider: str, api_key: str):
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=api_key,
            temperature=0.2,
            max_tokens=4096,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_output_tokens=8192,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


# ── LLD Prompts ───────────────────────────────────────────────────────────────

LLD_SYSTEM_PROMPT = """You are an expert software architect specialising in codebase analysis.
Your task is to analyse a dependency graph JSON extracted from a GitHub repository and
produce a React Flow diagram JSON that visually represents the detailed module-level architecture.

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
- Use a maximum of 30 nodes — pick the most architecturally significant files/modules.
- Group nodes into logical COLUMNS by layer (left-to-right: entry → controllers → services → data):
    Column 0 (x=50):   Entry points / main files (e.g. main.py, App.jsx, index.js)
    Column 1 (x=300):  Routes / Controllers / Handlers / UI Components (e.g. routes.py, UserController, DiagramViewer, AnalyzerForm)
    Column 2 (x=550):  Services / Business logic (e.g. github_service.py, ast_parser.py, graph_builder.py)
    Column 3 (x=800):  Models / Schemas / Data classes (e.g. models.py, schema.py, types.ts)
    Column 4 (x=1050): Database / Cache / External integrations — ONLY if they exist
    Column 5 (x=1300): Utilities / Config / Shared (e.g. vite.config.js, settings.py, utils.py)
- Space nodes VERTICALLY: y = row_index * 120 within each column. Start at y=50.
- Node `id` must be a short, unique snake_case string (e.g., "app_main", "user_controller").
- Node `label` must be a concise human-readable name (e.g., "App Entry", "User Controller").
- CRITICAL: Frontend UI components (React components, Vue components) belong in Column 1 (x=300), NOT Column 4.

## Edge Rules:
- Only include edges between nodes that ARE in your node list.
- `source` and `target` must exactly match node `id` values.
- Set `animated: true` on every edge.

## CRITICAL:
- Return ONLY the raw JSON object — no explanation, no code fences, no extra text.
- Every node id referenced in edges MUST exist in the nodes array.
"""

LLD_USER_PROMPT = """Analyse the following dependency graph extracted from a GitHub repository.
Produce a React Flow diagram showing the detailed module-level architecture.

Graph JSON:
{graph_json}

## How to read this graph:
- "edges": import relationships between files — use these as your diagram edges
- "external_api_calls": HTTP calls or route decorators found in the file:
    - "ROUTE:@app.post(...)" → this file is an API server entry point
    - "fetch(...)" → this file calls a backend API
    - "self._client.get(...)" → this file calls an external service
- "imports": libraries used — tells you what layer this file belongs to

## Rules:
- Include ALL nodes from the graph — both frontend AND backend
- Use the "edges" array to draw connections between nodes
- For files with "ROUTE:" in external_api_calls → place in Column 0 (entry point)
- For files with fetch/axios in external_api_calls → they call the backend, show that edge too
- Backend entry (main.py with @app routes) connects to service files it imports

## Layout:
- Column 0 (x=50):   main.py, main.jsx, index.js — entry points
- Column 1 (x=300):  React components, API route handlers
- Column 2 (x=550):  Service files (github_service, ast_parser, graph_builder, langgraph_agent)
- Column 3 (x=800):  Models/schemas — only if they exist
- Column 5 (x=1300): Config/utilities (vite.config.js, .env files)

Assign clear labels. No two nodes at same x,y position.
"""


# ── HLD Prompts ───────────────────────────────────────────────────────────────

HLD_SYSTEM_PROMPT = """You are an expert software architect creating a High-Level Design (HLD) diagram.
Your task is to abstract a detailed code dependency graph into a clean system-level block diagram
showing the major infrastructure components and how they interact.

## Output Requirements (STRICT — return ONLY valid JSON, no markdown fences):

{
  "nodes": [
    {
      "id": "unique_snake_case_id",
      "type": "custom",
      "data": {
        "label": "Human-Readable Component Name",
        "systemType": "<one of the types below>",
        "description": "One sentence describing this component's role."
      },
      "position": { "x": <integer>, "y": <integer> }
    }
  ],
  "edges": [
    {
      "id": "e_<source_id>_<target_id>",
      "source": "<source node id>",
      "target": "<target node id>",
      "label": "<short action label e.g. HTTP, SQL, gRPC, Pub/Sub>",
      "animated": true
    }
  ]
}

## systemType values (MUST use one of these exactly):
- "client"       → Browser / Mobile / Frontend UI
- "server"       → API Server / Backend / Web Server
- "service"      → Microservice / Worker / Background Job
- "database"     → SQL or NoSQL Database
- "cache"        → Cache (Redis, Memcached, in-memory)
- "queue"        → Message Queue / Event Bus (Kafka, RabbitMQ, SQS)
- "external_api" → Third-party API / External service
- "cdn"          → CDN / Static file storage

## Layout Rules:
- Use 5–8 nodes maximum — focus on major system components only, NOT individual files.
- Think in terms of: Who are the clients? What servers handle requests? What data stores exist?
  What external services are called? What background workers run?
- Layout left-to-right by data flow:
    x=100:  Clients / Entry (browsers, mobile apps)
    x=400:  API / Backend servers
    x=700:  Internal services / workers
    x=1000: Data stores (databases, caches, queues)
    x=1300: External APIs / CDN
- Space nodes vertically: y = row_index * 180, start at y=100.
- Make labels concise and infrastructure-level (e.g., "FastAPI Server", "PostgreSQL", "React App").

## Edge Rules:
- Show data flow in BOTH directions for request-response patterns.
- Use a single edge with label "HTTP req/res" for synchronous REST calls (request + response combined).
- Every call to an external API (GitHub API, LLM API) MUST have a corresponding response edge back.
- Use label "Internal" for in-process calls between services.

## CRITICAL:
- Return ONLY the raw JSON object — no explanation, no code fences, no extra text.
- Every node id referenced in edges MUST exist in the nodes array.
- Do NOT include individual source files as nodes — only system-level blocks.
"""

HLD_USER_PROMPT = """Analyse this dependency graph and produce a HIGH-LEVEL system architecture diagram.

Graph JSON:
{graph_json}

## How to read this graph:
- "imports": what libraries/modules this file uses → tells you the tech stack
- "external_api_calls": actual HTTP calls or route definitions found in this file:
    - "fetch(...)" or "axios.(...)" → this file makes HTTP requests to a backend
    - "ROUTE:@app.post(...)" → this file EXPOSES an HTTP endpoint (it IS the server)
    - "self._client.get(...)" → this file calls an external HTTP API
- "has_external_apis": true → this file makes outbound HTTP calls
- "all_file_paths": every file in the repo — use to infer languages/frameworks not parsed

## Rules for building the diagram:
1. Find the CLIENT: look for files with fetch() or axios calls → that's the frontend calling the backend
2. Find the SERVER: look for files with ROUTE: decorators (@app.post, @app.get) → that's the API server
3. Find EXTERNAL APIs: look for files named *github*, *stripe*, *twilio* etc with HTTP calls → external services
4. Find INTERNAL SERVICES: look for langgraph, celery, worker imports → background services
5. Find DATA STORES: only if sqlalchemy, prisma, mongoose, redis imports exist

## Edge rules — BIDIRECTIONAL flows:
- Every HTTP call has a response. Show BOTH directions:
  - client → server: label "HTTP POST /api/analyze"  
  - server → client: label "JSON response"
- Every external API call has a response:
  - server → github_api: label "GET /repos/{owner}/{repo}"
  - github_api → server: label "repo file tree"
  - langgraph → llm_api: label "prompt + graph JSON"
  - llm_api → langgraph: label "React Flow JSON"

## Infrastructure rules:
- NO database node unless sqlalchemy/prisma/mongoose/django.db imports exist
- NO cache node unless redis/memcached imports exist  
- NO queue node unless kafka/rabbitmq/celery imports exist
"""


# ── Agent State ────────────────────────────────────────────────────────────────

ERD_SYSTEM_PROMPT = """You are an expert database architect analyzing a codebase.
Your task is to identify all data models, ORM entities, schemas, or data classes
and produce a React Flow Entity-Relationship Diagram (ERD).

## Output Requirements (STRICT — return ONLY valid JSON, no markdown fences):

{
  "nodes": [
    {
      "id": "snake_case_model_id",
      "type": "erd",
      "position": { "x": <integer>, "y": <integer> },
      "data": {
        "modelName": "ModelName",
        "fields": [
          { "name": "field_name", "type": "DataType", "isPrimaryKey": true },
          { "name": "other_field", "type": "String", "isPrimaryKey": false }
        ]
      }
    }
  ],
  "edges": [
    {
      "id": "e_users_posts",
      "source": "users",
      "target": "posts",
      "label": "1:N",
      "animated": false
    }
  ]
}

## Node Rules:
- Each node represents ONE data model / ORM class / schema / data class.
- Use up to 15 models maximum — pick the most important ones.
- `modelName` must be PascalCase (e.g., "User", "BlogPost", "OrderItem").
- `fields` array: include 3–8 fields per model. Always include primary keys.
- Common field types: UUID, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON, Enum.
- Always mark the primary key field with `isPrimaryKey: true`.
- For foreign key fields, use type "ForeignKey(ModelName)".

## Layout Rules:
- Place related models close together.
- Use a grid layout: x = column * 320 + 50, y = row * 400 + 50.
- Spread columns across x=50, x=370, x=690, x=1010, etc.
- Start y at 50, increment by 400 per row.

## Edge Rules:
- Show relationships between models (foreign keys, many-to-many).
- Use clear relationship labels: "1:1", "1:N", "N:M".
- Only draw edges between models that ARE in your nodes list.
- Do NOT animate ERD edges (animated: false).

## CRITICAL:
- Return ONLY the raw JSON object — no explanation, no code fences, no extra text.
- If NO data models exist in the codebase, return exactly: {"nodes": [], "edges": [], "no_models": true}
- Do NOT invent or infer models. Only include models that are explicitly defined in the source files.
- Every source/target in edges MUST match a node id exactly.
"""

ERD_USER_PROMPT = """Analyse the following dependency graph from a GitHub repository and produce an ERD.

Graph JSON:
{graph_json}

STRICT RULES:
- Only include models that are EXPLICITLY defined in the source files shown in the graph.
- Look for ORM models (SQLAlchemy, Django ORM, Mongoose, Prisma, TypeORM, Pydantic BaseModel used as DB schema, dataclasses used as DB entities, etc.).
- If you see NO ORM imports (sqlalchemy, django.db, mongoose, prisma, typeorm, sequelize, etc.) in the graph, return {"nodes": [], "edges": [], "no_models": true} immediately.
- Do NOT infer or invent models based on the application's purpose or domain.
- Pydantic models used only for API request/response validation are NOT data models — do not include them unless they map to a database table.
- Only show relationships via edges if foreign key fields are explicitly present in the model definitions.
"""


# ── Agent State ────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    graph_json: dict[str, Any]
    # LLD outputs
    lld_nodes: list[dict]
    lld_edges: list[dict]
    arch_summary: str
    # HLD outputs
    hld_nodes: list[dict]
    hld_edges: list[dict]
    # ERD outputs
    erd_nodes: list[dict]
    erd_edges: list[dict]
    error: str


# ── Graph compression ─────────────────────────────────────────────────────────

def _compress_graph(graph_json: dict, include_file_paths: bool = False) -> str:
    def _trim_node(n: dict) -> dict:
        return {
            "id":                  n.get("id"),
            "label":               n.get("label"),
            "language":            n.get("language"),
            "imports":             n.get("imports", [])[:15],
            "classes":             n.get("classes", [])[:10],
            "functions":           n.get("functions", [])[:10],
            "has_external_apis":   n.get("has_external_apis", False),
            "external_api_calls":  n.get("external_api_calls", [])[:8],  # HTTP calls + routes
            "in_degree":           n.get("in_degree", 0),
            "out_degree":          n.get("out_degree", 0),
        }

    compressed = {
        "node_count":   graph_json.get("node_count"),
        "edge_count":   graph_json.get("edge_count"),
        "hubs":         graph_json.get("hubs", []),
        "entry_points": graph_json.get("entry_points", []),
        "clusters":     graph_json.get("clusters", {}),
        "nodes": [
            _trim_node(n)
            for n in sorted(
                graph_json.get("nodes", []),
                key=lambda n: n.get("in_degree", 0),
                reverse=True,
            )
        ],
        "edges": graph_json.get("edges", []),
    }
    if include_file_paths:
        compressed["all_file_paths"] = graph_json.get("all_file_paths", [])[:80]

    return json.dumps(compressed, indent=2)


# ── LLM response parser ────────────────────────────────────────────────────────

def _parse_llm_json(raw: str) -> dict:
    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw.strip(), flags=re.MULTILINE)
    # Extract outermost JSON object
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        raise ValueError("LLM response did not contain a JSON object")
    candidate = json_match.group()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Fix common LLM mistakes: single quotes, extra wrapping quotes on keys
        candidate = candidate.replace("'", '"')
        # Remove extra quotes around keys like '"nodes"': → "nodes":
        candidate = re.sub(r'"\"(\w+)\""', r'"\1"', candidate)
        return json.loads(candidate)


# ── Validate & fix nodes/edges ────────────────────────────────────────────────

def _validate_and_fix(parsed: dict, default_type: str | None = None) -> dict:
    nodes = parsed.get("nodes", [])
    edges = parsed.get("edges", [])
    valid_ids = {n["id"] for n in nodes if "id" in n}

    # Build a fuzzy lookup: lowercase label/id → actual id
    # so edges referencing "main" can match node id "app_main"
    fuzzy: dict[str, str] = {}
    for n in nodes:
        nid = n.get("id", "")
        fuzzy[nid.lower()] = nid
        label = n.get("data", {}).get("label", "")
        if label:
            fuzzy[label.lower()] = nid
            fuzzy[label.lower().replace(" ", "_")] = nid

    def _resolve(ref: str) -> str | None:
        if ref in valid_ids:
            return ref
        return fuzzy.get(ref.lower()) or fuzzy.get(ref.lower().replace(" ", "_"))

    for i, node in enumerate(nodes):
        if "position" not in node:
            node["position"] = {"x": (i % 6) * 250 + 50, "y": (i // 6) * 150 + 100}
        if "data" not in node:
            node["data"] = {"label": node.get("id", f"node_{i}")}
        if default_type and node.get("type") != default_type:
            node["type"] = default_type

    clean_edges = []
    for edge in edges:
        src = _resolve(edge.get("source", ""))
        tgt = _resolve(edge.get("target", ""))
        if src and tgt and src != tgt:
            edge["source"] = src
            edge["target"] = tgt
            edge["animated"] = True
            if "id" not in edge:
                edge["id"] = f"e_{src}_{tgt}"
            clean_edges.append(edge)

    parsed["nodes"] = nodes
    parsed["edges"] = clean_edges
    return parsed


# ── Retry wrapper for rate limits ─────────────────────────────────────────────

async def _invoke_with_retry(llm, messages: list, max_retries: int = 4) -> Any:
    """Retry LLM calls on 429 rate limit errors with exponential backoff."""
    import logging
    log = logging.getLogger("arch-visualizer")

    for i, msg in enumerate(messages):
        content = msg.content if hasattr(msg, "content") else str(msg)
        log.info("LLM_INPUT [msg %d/%d] type=%s length=%d chars:\n%s",
                 i + 1, len(messages),
                 type(msg).__name__,
                 len(content),
                 content[:3000])   # cap at 3000 chars so logs don't explode

    for attempt in range(max_retries):
        try:
            return await llm.ainvoke(messages)
        except Exception as exc:
            err = str(exc)
            is_rate_limit = "429" in err or "TooManyRequests" in err or "rate" in err.lower()
            if is_rate_limit and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)
                continue
            raise


# ── LLD node ──────────────────────────────────────────────────────────────────

async def analyze_lld(state: AgentState, llm) -> AgentState:
    try:
        compressed = _compress_graph(state["graph_json"])  # lean — no file paths
        messages = [
            SystemMessage(content=LLD_SYSTEM_PROMPT),
            HumanMessage(content=LLD_USER_PROMPT.format(graph_json=compressed)),
        ]
        response = await _invoke_with_retry(llm, messages)
        parsed = _parse_llm_json(response.content)
        parsed = _validate_and_fix(parsed)
        return {
            **state,
            "lld_nodes":   parsed.get("nodes", []),
            "lld_edges":   parsed.get("edges", []),
            "arch_summary": parsed.get("summary", ""),
            "error": "",
        }
    except Exception as exc:
        return {
            **state,
            "lld_nodes": [],
            "lld_edges": [],
            "error": f"LLD analysis failed: {exc}",
        }


# ── HLD node ──────────────────────────────────────────────────────────────────

async def analyze_hld(state: AgentState, llm) -> AgentState:
    try:
        compressed = _compress_graph(state["graph_json"], include_file_paths=True)
        messages = [
            SystemMessage(content=HLD_SYSTEM_PROMPT),
            HumanMessage(content=HLD_USER_PROMPT.format(graph_json=compressed)),
        ]
        response = await _invoke_with_retry(llm, messages)
        parsed = _parse_llm_json(response.content)
        parsed = _validate_and_fix(parsed, default_type="custom")
        return {
            **state,
            "hld_nodes": parsed.get("nodes", []),
            "hld_edges": parsed.get("edges", []),
        }
    except Exception as exc:
        return {
            **state,
            "hld_nodes": [],
            "hld_edges": [],
            "error": state.get("error", "") + f" | HLD analysis failed: {exc}",
        }


# ── ERD node ──────────────────────────────────────────────────────────────────

async def analyze_erd(state: AgentState, llm) -> AgentState:
    try:
        compressed = _compress_graph(state["graph_json"])  # lean — no file paths needed
        messages = [
            SystemMessage(content=ERD_SYSTEM_PROMPT),
            HumanMessage(content=ERD_USER_PROMPT.format(graph_json=compressed)),
        ]
        response = await _invoke_with_retry(llm, messages)
        parsed = _parse_llm_json(response.content)

        # LLM signalled no models exist — return empty ERD, not an error
        if parsed.get("no_models") or (not parsed.get("nodes") and not parsed.get("edges")):
            return {
                **state,
                "erd_nodes": [],
                "erd_edges": [],
            }

        parsed = _validate_and_fix(parsed, default_type="erd")
        # ERD edges should NOT be animated
        for edge in parsed.get("edges", []):
            edge["animated"] = False
        return {
            **state,
            "erd_nodes": parsed.get("nodes", []),
            "erd_edges": parsed.get("edges", []),
        }
    except Exception as exc:
        return {
            **state,
            "erd_nodes": [],
            "erd_edges": [],
            "error": state.get("error", "") + f" | ERD analysis failed: {exc}",
        }


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_agent(llm_provider: str, llm_api_key: str):
    llm = _build_llm(llm_provider, llm_api_key)

    workflow = StateGraph(AgentState)

    async def _lld(state: AgentState) -> AgentState:
        return await analyze_lld(state, llm)

    async def _hld(state: AgentState) -> AgentState:
        await asyncio.sleep(8)   # longer gap — Groq TPM limit needs more breathing room
        return await analyze_hld(state, llm)

    async def _erd(state: AgentState) -> AgentState:
        await asyncio.sleep(8)
        return await analyze_erd(state, llm)

    workflow.add_node("analyze_lld", _lld)
    workflow.add_node("analyze_hld", _hld)
    workflow.add_node("analyze_erd", _erd)
    workflow.set_entry_point("analyze_lld")
    workflow.add_edge("analyze_lld", "analyze_hld")
    workflow.add_edge("analyze_hld", "analyze_erd")
    workflow.add_edge("analyze_erd", END)

    return workflow.compile()


# ── Convenience runner ────────────────────────────────────────────────────────

async def run_agent(
    graph_json: dict[str, Any],
    llm_provider: str,
    llm_api_key: str,
) -> dict[str, Any]:
    app = build_agent(llm_provider, llm_api_key)

    initial_state: AgentState = {
        "graph_json":   graph_json,
        "lld_nodes":    [],
        "lld_edges":    [],
        "arch_summary": "",
        "hld_nodes":    [],
        "hld_edges":    [],
        "erd_nodes":    [],
        "erd_edges":    [],
        "error":        "",
    }

    result = await app.ainvoke(initial_state)
    return {
        "lld_nodes":    result.get("lld_nodes", []),
        "lld_edges":    result.get("lld_edges", []),
        "hld_nodes":    result.get("hld_nodes", []),
        "hld_edges":    result.get("hld_edges", []),
        "erd_nodes":    result.get("erd_nodes", []),
        "erd_edges":    result.get("erd_edges", []),
        "arch_summary": result.get("arch_summary", ""),
        "error":        result.get("error", ""),
    }
