# ── Backend Dockerfile (for Koyeb / Render / Railway) ─────────────────────
FROM python:3.11-slim

# Install Node.js (needed for the Eraser MCP server spawned via npx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install the Eraser MCP package to avoid npx network calls at runtime
RUN npm install -g @eraser-io/mcp@latest

# Copy source code
COPY . .

# Create log directory
RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
