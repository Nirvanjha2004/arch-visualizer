"""
FastAPI Backend — Codebase Architecture Visualizer

Endpoints:
  POST /api/analyze   — main pipeline entry point
  GET  /api/health    — health check

Full 12-step pipeline:
  1.  Receive GitHub URL from client
  2.  Fetch repo tree via GitHub API (PAT-authenticated)
  3.  Parse each source file with Tree-sitter → ASTs
  4.  Extract structural metadata (imports, classes, functions, calls)
  5.  Build Directed Graph in NetworkX
  6.  Prune graph & generate topology summary JSON
  7–12. Hand JSON to LangGraph agent →
          LLM generates Eraser DaC →
          Agent calls Eraser MCP →
          Returns hosted diagram URL
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator

# ── Load environment variables ─────────────────────────────────────────────────
load_dotenv()

GITHUB_PAT       = os.getenv("GITHUB_PAT", "")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
ERASER_API_KEY   = os.getenv("ERASER_API_KEY", "")
LLM_PROVIDER     = os.getenv("LLM_PROVIDER", "groq").lower()
LOG_LEVEL        = os.getenv("LOG_LEVEL", "INFO").upper()

# Determine LLM API key based on provider
LLM_API_KEY = GROQ_API_KEY if LLM_PROVIDER == "groq" else GEMINI_API_KEY

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_DIR = Path("/mnt/efs/spaces/ca014c33-7622-4744-9932-2fe631ca359d/"
               "13310a0d-4c83-4d77-997b-8cec4d6ad9b4/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "backend.log"),
    ],
)
logger = logging.getLogger("arch-visualizer")

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Codebase Architecture Visualizer",
    description="Analyse any GitHub repo and generate a visual architecture diagram.",
    version="1.0.0",
)

# Parse CORS origins
_cors_raw = os.getenv(
    "BACKEND_CORS_ORIGINS",
    '["http://localhost:5173","http://localhost:3000"]',
)
try:
    CORS_ORIGINS: list[str] = json.loads(_cors_raw)
except Exception:
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ──────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def must_be_github(cls, v: str) -> str:
        if "github.com" not in v:
            raise ValueError("Only GitHub repository URLs are supported.")
        return v.strip()


class AnalyzeResponse(BaseModel):
    diagram_url: str
    arch_summary: str
    dac_syntax: str
    graph_stats: dict
    processing_time_seconds: float
    warning: str = ""


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "llm_provider": LLM_PROVIDER,
        "eraser_configured": bool(ERASER_API_KEY),
        "github_pat_configured": bool(GITHUB_PAT),
    }


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_repo(req: AnalyzeRequest):
    """
    Main pipeline endpoint. Accepts a GitHub URL and returns a
    hosted Eraser.io architecture diagram URL.
    """
    t_start = time.monotonic()
    repo_url = req.repo_url

    logger.info("Starting analysis for: %s", repo_url)

    # ── Step 1-2: Fetch repo source files ──────────────────────────────────────
    from services.github_service import GitHubService

    github = GitHubService(pat=GITHUB_PAT or None)
    try:
        file_contents = await github.fetch_repo_structure(repo_url)
    except Exception as exc:
        logger.error("GitHub fetch error: %s", exc)
        raise HTTPException(
            status_code=422,
            detail=f"Failed to fetch repository: {exc}",
        )
    finally:
        await github.close()

    if not file_contents:
        raise HTTPException(
            status_code=422,
            detail="No supported source files found in the repository "
                   "(supported: .py, .js, .jsx, .ts, .tsx).",
        )

    logger.info("Fetched %d source files", len(file_contents))

    # ── Steps 3-4: AST parsing ─────────────────────────────────────────────────
    from services.ast_parser import parse_files

    file_metadata = parse_files(file_contents)
    logger.info("Parsed %d files with Tree-sitter", len(file_metadata))

    # ── Steps 5-6: Graph construction & pruning ────────────────────────────────
    from services.graph_builder import build_graph

    graph_json = build_graph(file_metadata)
    logger.info(
        "Graph built: %d nodes, %d edges",
        graph_json["node_count"],
        graph_json["edge_count"],
    )

    # ── Steps 7-12: LangGraph agent + Eraser MCP ──────────────────────────────
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail=f"No API key configured for LLM provider '{LLM_PROVIDER}'. "
                   "Set GROQ_API_KEY or GEMINI_API_KEY in your .env file.",
        )

    from agents.langgraph_agent import run_agent

    agent_result = await run_agent(
        graph_json=graph_json,
        llm_provider=LLM_PROVIDER,
        llm_api_key=LLM_API_KEY,
        eraser_api_key=ERASER_API_KEY,
    )

    elapsed = round(time.monotonic() - t_start, 2)
    logger.info(
        "Analysis complete in %.2fs — diagram_url=%s error=%s",
        elapsed,
        agent_result.get("diagram_url"),
        agent_result.get("error"),
    )

    # Log result to JSON log file
    log_entry = {
        "repo_url": repo_url,
        "files_analysed": len(file_contents),
        "graph_nodes": graph_json["node_count"],
        "graph_edges": graph_json["edge_count"],
        "diagram_url": agent_result.get("diagram_url"),
        "error": agent_result.get("error"),
        "processing_time_seconds": elapsed,
    }
    try:
        with open(LOG_DIR / "analysis_log.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # Don't fail the request due to logging errors

    return AnalyzeResponse(
        diagram_url=agent_result.get("diagram_url", ""),
        arch_summary=agent_result.get("arch_summary", ""),
        dac_syntax=agent_result.get("dac_syntax", ""),
        graph_stats={
            "files_analysed": len(file_contents),
            "nodes": graph_json["node_count"],
            "edges": graph_json["edge_count"],
            "hubs": graph_json.get("hubs", []),
            "clusters": list(graph_json.get("clusters", {}).keys()),
        },
        processing_time_seconds=elapsed,
        warning=agent_result.get("error", ""),
    )
