# Automated Codebase Architecture Visualizer

> Paste any GitHub repo URL → AI parses ASTs → builds dependency graph → generates a hosted Eraser.io architecture diagram.

---

## ── Free API Keys Setup (No Credit Card Required) ──────────────────────────

### 1. GitHub Personal Access Token (PAT)
1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Scopes needed: ✅ `public_repo` (read-only is fine)
4. Copy the `ghp_...` token → set as `GITHUB_PAT`

### 2. Groq API Key (Free, No CC)
1. Go to https://console.groq.com
2. Sign up with Google/GitHub (no credit card)
3. Dashboard → **API Keys** → **Create API Key**
4. Copy the `gsk_...` key → set as `GROQ_API_KEY`
> Model used: `llama3-70b-8192` (free tier: 30 req/min, 6000 tokens/min)

### 3. Google Gemini (Alternative, No CC)
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google → **Create API Key**
3. Set `GEMINI_API_KEY` and `LLM_PROVIDER=gemini`

### 4. Eraser.io API Key
1. Create a free account at https://app.eraser.io (free tier available)
2. Go to **Settings → API** → **Generate Key**
3. Copy it → set as `ERASER_API_KEY`

---

## ── Local Development ───────────────────────────────────────────────────────

### Backend (FastAPI)
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env template and fill in keys
cp .env.example .env
# Edit .env with your keys

# Run backend (port 8000)
uvicorn main:app --reload --port 8000
```

### Frontend (React + Vite)
```bash
cd frontend

# Install dependencies
npm install

# Copy env template
cp .env.example .env
# (Leave VITE_BACKEND_URL empty — Vite proxy handles it)

# Run dev server (port 5173)
npm run dev
```

Open http://localhost:5173

---

## ── Deployment ──────────────────────────────────────────────────────────────

### Backend → Koyeb (Free Tier, No CC)
1. Push `backend/` to a GitHub repo
2. Sign up at https://app.koyeb.com (free tier, no CC)
3. Create a new **Service** → **Docker** → point to your repo
4. Set environment variables in the Koyeb dashboard:
   - `GITHUB_PAT`, `GROQ_API_KEY`, `ERASER_API_KEY`, `LLM_PROVIDER`
   - `BACKEND_CORS_ORIGINS=["https://your-app.vercel.app"]`
5. Deploy — note the public URL, e.g. `https://xxx.koyeb.app`

> **Alternative:** Render.com free tier also works. Create a new Web Service,
> select Docker, set the same env vars.

### Frontend → Vercel (Free Tier, No CC)
1. Push `frontend/` to a GitHub repo
2. Sign up at https://vercel.com (free, no CC)
3. Import the repo → Vercel auto-detects Vite
4. Add environment variable:
   - `VITE_BACKEND_URL=https://your-koyeb-backend.koyeb.app`
5. Deploy → get your `https://your-app.vercel.app` URL

---

## ── Architecture ────────────────────────────────────────────────────────────

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend (Vite)                   │
│   Input URL → POST /api/analyze → Render diagram iframe     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend (Python)                     │
│                                                              │
│  1. GitHubService  ── fetch file tree + content             │
│  2. ast_parser     ── Tree-sitter ASTs → FileMetadata       │
│  3. graph_builder  ── NetworkX DiGraph → Graph JSON         │
│  4. LangGraph Agent                                         │
│     ├── Node 1: analyze_architecture (Groq/Gemini LLM)     │
│     │     → parses Graph JSON → generates Eraser DaC        │
│     └── Node 2: create_eraser_diagram (Eraser MCP Client)  │
│           → spawns @eraser-io/mcp via stdio                 │
│           → calls generateDiagram tool                      │
│           → returns hosted diagram URL                      │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Eraser.io MCP Server (Node.js)                  │
│    Runs as subprocess · communicates via stdio MCP          │
│    Takes Diagram-as-Code → returns hosted eraser.io URL     │
└─────────────────────────────────────────────────────────────┘
```

---

## ── Tech Stack ──────────────────────────────────────────────────────────────
| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite 5 |
| Backend | FastAPI + Uvicorn |
| Orchestration | LangGraph 0.1 |
| LLM | Groq Llama 3 70B (free) or Gemini 1.5 Flash (free) |
| AST Parsing | Tree-sitter (Python, JS, TS) |
| Graph Processing | NetworkX |
| Diagramming | Eraser.io via official MCP server |
| Frontend Hosting | Vercel (free tier) |
| Backend Hosting | Koyeb or Render (free tier) |
