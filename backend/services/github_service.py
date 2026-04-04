"""
GitHub Service — Step 2 of the pipeline.

Responsibilities:
  - Parse a GitHub URL into owner/repo/ref
  - Recursively fetch the repo file tree via Git Trees API
  - Filter for supported source code files only
  - Fetch file content (base64-decoded) for each source file
"""

import base64
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# ── Supported file extensions for AST parsing ─────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".py":   "python",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".go":   "go",
    ".rs":   "rust",
    ".java": "java",
}

# Max file size to fetch (200 KB) — avoids giant generated/minified files
MAX_FILE_SIZE_BYTES = 200_000

# Maximum number of source files to analyse
MAX_FILES = 120


def parse_github_url(url: str) -> tuple[str, str, Optional[str]]:
    """
    Parse a GitHub URL and return (owner, repo, ref).
    Supports formats:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch
    """
    url = url.rstrip("/")
    # Normalise: strip .git suffix
    url = re.sub(r"\.git$", "", url)

    parsed = urlparse(url)
    if parsed.hostname not in ("github.com", "www.github.com"):
        raise ValueError(f"Not a GitHub URL: {url}")

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Could not parse owner/repo from URL: {url}")

    owner, repo = parts[0], parts[1]
    ref: Optional[str] = None

    # Path like /owner/repo/tree/branch-name
    if len(parts) >= 4 and parts[2] == "tree":
        ref = "/".join(parts[3:])  # handles slashes in branch names

    return owner, repo, ref


class GitHubService:
    """Async client for the GitHub REST API."""

    BASE = "https://api.github.com"

    def __init__(self, pat: Optional[str] = None):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if pat:
            headers["Authorization"] = f"Bearer {pat}"

        self._client = httpx.AsyncClient(
            base_url=self.BASE,
            headers=headers,
            timeout=30.0,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def _get(self, path: str, **params) -> dict | list:
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _get_default_branch(self, owner: str, repo: str) -> str:
        data = await self._get(f"/repos/{owner}/{repo}")
        return data.get("default_branch", "main")  # type: ignore[index]

    async def _resolve_tree_sha(
        self, owner: str, repo: str, ref: str
    ) -> str:
        """Return the SHA of the root tree for the given ref."""
        data = await self._get(f"/repos/{owner}/{repo}/git/ref/heads/{ref}")
        commit_sha = data["object"]["sha"]  # type: ignore[index]
        commit_data = await self._get(
            f"/repos/{owner}/{repo}/git/commits/{commit_sha}"
        )
        return commit_data["tree"]["sha"]  # type: ignore[index]

    # ── Public API ────────────────────────────────────────────────────────────

    async def fetch_repo_structure(
        self, github_url: str
    ) -> dict[str, str]:
        """
        Main entry point.

        Returns a mapping of  { file_path: source_code_string }
        for all supported source files found in the repository.
        """
        owner, repo, ref = parse_github_url(github_url)

        if ref is None:
            ref = await self._get_default_branch(owner, repo)

        tree_sha = await self._resolve_tree_sha(owner, repo, ref)

        # Fetch recursive tree in one request (works for repos < 100k files)
        tree_data = await self._get(
            f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            recursive=1,
        )

        source_files: list[dict] = []
        for item in tree_data.get("tree", []):  # type: ignore[union-attr]
            if item["type"] != "blob":
                continue
            path: str = item["path"]
            ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            size = item.get("size", 0)
            if size > MAX_FILE_SIZE_BYTES:
                continue
            source_files.append(item)

        # Trim to MAX_FILES — prefer files in shallower directories
        source_files.sort(key=lambda f: f["path"].count("/"))
        source_files = source_files[:MAX_FILES]

        # Fetch content concurrently (batched to avoid rate limits)
        result: dict[str, str] = {}
        for item in source_files:
            try:
                blob = await self._get(
                    f"/repos/{owner}/{repo}/git/blobs/{item['sha']}"
                )
                content_b64: str = blob.get("content", "")  # type: ignore[union-attr]
                # GitHub returns content with embedded newlines
                raw = base64.b64decode(
                    content_b64.replace("\n", "")
                ).decode("utf-8", errors="replace")
                result[item["path"]] = raw
            except Exception:
                # Skip files that can't be decoded
                continue

        return result

    async def close(self):
        await self._client.aclose()
