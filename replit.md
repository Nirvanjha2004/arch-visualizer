# Automated Codebase Architecture Visualizer

## Overview

A full-stack web app that analyzes any public GitHub repository and generates an interactive architecture diagram using AI. It fetches source files, parses them with Tree-sitter, builds a dependency graph with NetworkX, and uses an LLM (via LangGraph) to generate a React Flow visualization.

## Architecture

- **Frontend**: React 18 + Vite 5, using `@xyflow/react` for interactive diagrams. Runs on port 5000.
- **Backend**: FastAPI (Python 3.12) + Uvicorn, runs on port 8000. The frontend proxies `/api/*` requests to the backend via Vite's proxy config.

## Project Structure

```
.
├── backend/
│   ├── main.py               # FastAPI app, API routes (/api/health, /api/analyze)
│   ├── requirements.txt      # Python dependencies
│   ├── agents/
│   │   └── langgraph_agent.py  # LangGraph AI agent for graph → React Flow conversion
│   └── services/
│       ├── ast_parser.py      # Tree-sitter AST parsing (Python, JS, TS)
│       ├── github_service.py  # GitHub API fetching
│       └── graph_builder.py   # NetworkX dependency graph builder
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── main.jsx           # React entry point
│   │   └── components/        # UI components (AnalyzerForm, DiagramViewer, etc.)
│   ├── vite.config.js         # Vite config (port 5000, proxy to :8000, allowedHosts: true)
│   └── package.json
└── replit.md
```

## Required Secrets

- `GITHUB_PAT` — GitHub Personal Access Token (free, needs `public_repo` scope)
- `GROQ_API_KEY` — Groq API key (free tier available at https://console.groq.com)

## Optional Secrets

- `GEMINI_API_KEY` — Google Gemini API key (alternative to Groq)

## Environment Variables

- `LLM_PROVIDER` — `"groq"` (default) or `"gemini"`
- `LOG_LEVEL` — `"INFO"` (default)
- `BACKEND_CORS_ORIGINS` — JSON array of allowed origins

## Workflows

- **Start application** — Runs the React/Vite frontend on port 5000 (`cd frontend && npm run dev`)
- **Backend** — Runs FastAPI backend on port 8000 (`cd backend && uvicorn main:app --host localhost --port 8000 --reload`)

## Key API Endpoints

- `GET /api/health` — Health check, shows LLM provider and GitHub PAT status
- `POST /api/analyze` — Main pipeline: accepts `{ repo_url: "https://github.com/..." }`, returns React Flow nodes/edges + architecture summary

## LLM Pipeline

1. GitHub API fetches repo file tree and contents
2. Tree-sitter parses Python/JS/TS files into ASTs
3. NetworkX builds a directed dependency graph
4. Graph is compressed (top 20 nodes by in-degree, first 40 edges)
5. LangGraph agent sends the graph to Groq (llama3-70b-8192) or Gemini (gemini-1.5-flash)
6. LLM returns React Flow JSON (nodes + edges + summary)
7. Frontend renders the interactive diagram

## Dependency Notes

- `langchain-core` was pinned to `0.2.38` (bumped from `0.2.10`) to satisfy `langgraph==0.1.19`'s `>=0.2.22` requirement
- `langchain` was bumped to `0.2.16` accordingly
- Log directory changed from a hardcoded EFS path to a local `logs/` directory
