"""
LangGraph Agent — Steps 7–12 of the pipeline.

State machine:
  ┌──────────────────────┐      ┌────────────────────────┐
  │  analyze_architecture│ ──►  │  create_eraser_diagram  │ ──► END
  └──────────────────────┘      └────────────────────────┘

Step 1 — analyze_architecture:
  The LLM receives the compressed Graph JSON and produces:
    a) A prose summary of the detected architectural patterns.
    b) A STRICTLY VALID Eraser.io Diagram-as-Code (DaC) string.

Step 2 — create_eraser_diagram:
  The agent acts as an MCP Client, spawning the official
  @eraser-io/mcp-server Node.js process via stdio and calling its
  tool to turn the DaC into a hosted diagram URL.

Returns the final diagram URL (or a fallback Eraser preview URL).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

# MCP client imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ── LLM factory ───────────────────────────────────────────────────────────────

def _build_llm(provider: str, api_key: str):
    """Return a LangChain chat model based on the chosen provider."""
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


# ── Eraser DaC prompt templates ───────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert software architect specialising in codebase analysis
and visual diagramming. Your task is to analyse a dependency graph JSON and produce:

1. A short prose summary (3-5 sentences) of the detected architectural patterns.
2. A STRICTLY VALID Eraser.io Diagram-as-Code (DaC) architecture diagram.

## Eraser.io DaC Syntax Rules (follow EXACTLY):
- Use `direction: right` or `direction: down` at the top.
- Declare nodes using:  NodeId [label: "Display Name", icon: icon-name]
  Valid icons: aws-lambda, aws-rds, aws-s3, aws-ec2, postgresql, mysql, mongodb,
  redis, docker, kubernetes, react, nextjs, nodejs, python, fastapi, django,
  flask, express, nginx, cloudflare, github, vercel, firebase, supabase,
  microservice, api, database, cache, queue, browser, server, cloud
- Declare edges using:  Source > Target : "label"  (label is optional)
- Group nodes in clusters using:  GroupName { ... }
- DO NOT use Mermaid syntax. DO NOT use arrows like -→ or ──►.
- Cluster names and node IDs must NOT contain spaces (use underscores).
- Max ~20 nodes to keep the diagram readable.

## Output format (return ONLY this JSON, no extra text):
{
  "summary": "...",
  "dac": "direction: right\\n\\n..."
}
"""

USER_PROMPT_TEMPLATE = """Analyse the following dependency graph extracted from a GitHub repository.
Identify the architectural patterns, layers, and key dependencies, then generate the Eraser DaC.

Graph JSON:
{graph_json}

Focus on:
- Entry points and main application files
- Database / persistence layer
- API / controller layer
- Service / business logic layer
- External API integrations
- Utility / shared modules

Group related files into logical clusters in the diagram.
"""


# ── Graph State ────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    graph_json: dict[str, Any]       # Input: compressed graph topology
    dac_syntax: str                  # Intermediate: Eraser DaC string
    arch_summary: str                # Intermediate: prose description
    diagram_url: str                 # Output: hosted Eraser URL
    error: str                       # Error message if any step fails


# ── Node 1: Analyse architecture & generate DaC ───────────────────────────────

def _compress_graph(graph_json: dict) -> str:
    """
    Compress graph JSON to stay within LLM context window.
    Keeps essential structural info, drops verbose call lists.
    """
    compressed = {
        "node_count": graph_json.get("node_count"),
        "edge_count": graph_json.get("edge_count"),
        "hubs": graph_json.get("hubs", []),
        "entry_points": graph_json.get("entry_points", []),
        "clusters": graph_json.get("clusters", {}),
        # Only top-20 nodes by in_degree
        "nodes": sorted(
            graph_json.get("nodes", []),
            key=lambda n: n.get("in_degree", 0),
            reverse=True,
        )[:20],
        # Only first 40 edges
        "edges": graph_json.get("edges", [])[:40],
    }
    return json.dumps(compressed, indent=2)


async def analyze_architecture(state: AgentState, llm) -> AgentState:
    """LLM step: analyse graph JSON → generate DaC + summary."""
    try:
        compressed = _compress_graph(state["graph_json"])
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=USER_PROMPT_TEMPLATE.format(graph_json=compressed)
            ),
        ]
        response = await llm.ainvoke(messages)
        raw_content: str = response.content

        # Extract JSON from the LLM response (may have markdown code fences)
        json_match = re.search(r"\{[\s\S]*\}", raw_content)
        if not json_match:
            raise ValueError("LLM did not return valid JSON")

        parsed = json.loads(json_match.group())
        return {
            **state,
            "dac_syntax": parsed.get("dac", ""),
            "arch_summary": parsed.get("summary", ""),
            "error": "",
        }
    except Exception as exc:
        return {**state, "error": f"LLM analysis failed: {exc}"}


# ── Node 2: Call Eraser MCP to generate diagram ───────────────────────────────

async def create_eraser_diagram(state: AgentState, eraser_api_key: str) -> AgentState:
    """
    MCP Client step: spawn the official @eraser-io/mcp-server via stdio,
    list its tools, call the diagram generation tool, and return the URL.
    """
    if state.get("error"):
        return state  # propagate error without attempting MCP call

    dac = state.get("dac_syntax", "")
    if not dac:
        return {**state, "error": "No DaC syntax generated by LLM"}

    try:
        # Spawn the Eraser MCP server as a subprocess via stdio transport
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@eraser-io/mcp@latest"],
            env={
                **os.environ,
                "ERASER_API_KEY": eraser_api_key,
            },
        )

        diagram_url = ""
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialise the MCP session
                await session.initialize()

                # List available tools to find the correct tool name
                tools_response = await session.list_tools()
                available_tools = [t.name for t in tools_response.tools]

                # Determine which tool to call
                # Eraser MCP exposes: "generate-diagram-as-code" or similar
                tool_name = None
                for candidate in (
                    "generateDiagram",
                    "generate-diagram",
                    "generate_diagram",
                    "createDiagram",
                    "create-diagram",
                    "renderDiagram",
                ):
                    if candidate in available_tools:
                        tool_name = candidate
                        break

                if tool_name is None and available_tools:
                    # Fallback: use the first available tool
                    tool_name = available_tools[0]

                if tool_name is None:
                    raise RuntimeError(
                        "No diagram generation tool found in Eraser MCP server. "
                        f"Available: {available_tools}"
                    )

                # Call the Eraser MCP tool
                result = await session.call_tool(
                    tool_name,
                    {
                        "text": dac,           # primary field Eraser uses
                        "diagramType": "cloud-architecture",
                    },
                )

                # Extract the URL from the result content
                if result.content:
                    for content_item in result.content:
                        text = getattr(content_item, "text", "") or str(content_item)
                        # Look for a URL in the response
                        url_match = re.search(
                            r"https?://[^\s\"'<>]+eraser[^\s\"'<>]+", text
                        )
                        if url_match:
                            diagram_url = url_match.group()
                            break
                        # Sometimes the whole text IS the URL
                        if text.startswith("http"):
                            diagram_url = text.strip()
                            break

        if not diagram_url:
            # Fallback: provide a direct Eraser preview link with encoded DaC
            import urllib.parse
            encoded = urllib.parse.quote(dac)
            diagram_url = f"https://app.eraser.io/workspace/new?content={encoded[:2000]}"

        return {**state, "diagram_url": diagram_url, "error": ""}

    except Exception as exc:
        # Return a graceful fallback instead of crashing
        import urllib.parse
        fallback = f"https://app.eraser.io/workspace/new"
        return {
            **state,
            "diagram_url": fallback,
            "error": f"Eraser MCP call failed: {exc}. Fallback URL provided.",
        }


# ── Graph assembly ─────────────────────────────────────────────────────────────

def build_agent(llm_provider: str, llm_api_key: str, eraser_api_key: str):
    """
    Construct and compile the LangGraph state machine.

    Returns a compiled graph (app) that can be invoked with:
        result = await app.ainvoke({"graph_json": {...}, "dac_syntax": "", ...})
    """
    llm = _build_llm(llm_provider, llm_api_key)

    workflow = StateGraph(AgentState)

    # Bind parameters into node functions
    async def _analyze(state: AgentState) -> AgentState:
        return await analyze_architecture(state, llm)

    async def _create_diagram(state: AgentState) -> AgentState:
        return await create_eraser_diagram(state, eraser_api_key)

    # Register nodes
    workflow.add_node("analyze_architecture", _analyze)
    workflow.add_node("create_eraser_diagram", _create_diagram)

    # Define edges
    workflow.set_entry_point("analyze_architecture")
    workflow.add_edge("analyze_architecture", "create_eraser_diagram")
    workflow.add_edge("create_eraser_diagram", END)

    return workflow.compile()


# ── Convenience runner ────────────────────────────────────────────────────────

async def run_agent(
    graph_json: dict[str, Any],
    llm_provider: str,
    llm_api_key: str,
    eraser_api_key: str,
) -> dict[str, Any]:
    """
    End-to-end entry point.

    Accepts the graph topology dict and returns:
      {
        "diagram_url": "https://...",
        "arch_summary": "...",
        "dac_syntax": "...",
        "error": ""
      }
    """
    app = build_agent(llm_provider, llm_api_key, eraser_api_key)

    initial_state: AgentState = {
        "graph_json": graph_json,
        "dac_syntax": "",
        "arch_summary": "",
        "diagram_url": "",
        "error": "",
    }

    result = await app.ainvoke(initial_state)
    return {
        "diagram_url": result.get("diagram_url", ""),
        "arch_summary": result.get("arch_summary", ""),
        "dac_syntax": result.get("dac_syntax", ""),
        "error": result.get("error", ""),
    }
