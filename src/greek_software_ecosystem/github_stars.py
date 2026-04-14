"""GitHub API helpers for public repository metadata (stars, forks)."""

from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml


def parse_github_repo_url(url: str) -> tuple[str, str] | None:
    """Parse ``https://github.com/owner/repo/...`` into ``(owner, repo)``, else ``None``."""
    try:
        p = urlparse((url or "").strip())
    except Exception:
        return None
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "github.com":
        return None
    parts = [x for x in p.path.split("/") if x]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def format_compact_github_count(n: int | None) -> str:
    """Format star/fork counts for README + HTML tables: ``127_000`` → ``127K``; under 1k unchanged."""
    if n is None:
        return "—"
    if n < 0:
        return str(n)
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        k = n / 1000.0
        if k >= 100:
            return f"{int(round(k))}K"
        rounded = round(k, 1)
        if rounded == int(rounded):
            return f"{int(rounded)}K"
        return f"{rounded:.1f}K"
    m = n / 1_000_000.0
    rounded = round(m, 1)
    if rounded == int(rounded):
        return f"{int(rounded)}M"
    return f"{rounded:.1f}M"


def load_open_source_github_stats_yaml(
    path: Path | None = None,
) -> dict[str, tuple[int | None, int | None]]:
    """Load ``owner/repo`` → ``(stars, forks)`` from ``_data/open_source_github_stats.yaml``."""
    if path is None:
        path = Path("_data/open_source_github_stats.yaml")
    if not path.is_file():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    repos = raw.get("repos")
    if not isinstance(repos, dict):
        return {}
    out: dict[str, tuple[int | None, int | None]] = {}
    for k, v in repos.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            continue
        s, fk = v.get("stars"), v.get("forks")
        si = int(s) if isinstance(s, int) else None
        fi = int(fk) if isinstance(fk, int) else None
        out[k] = (si, fi)
    return out


def fetch_github_repo_stats(owner: str, repo: str) -> tuple[int | None, int | None]:
    """GET ``/repos/{owner}/{repo}`` → ``(stargazers_count, forks_count)``; ``None`` per field on failure."""
    api = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "greek-software-ecosystem",
    }
    token = (
        os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    ).strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    max_attempts = 3
    backoff_s = 0.75
    for attempt in range(max_attempts):
        try:
            r = requests.get(api, headers=headers, timeout=15)
        except (OSError, requests.RequestException):
            if attempt + 1 < max_attempts:
                time.sleep(backoff_s)
                backoff_s *= 2
                continue
            return None, None

        if r.status_code == 200:
            try:
                data = r.json()
            except (TypeError, ValueError):
                return None, None
            s = data.get("stargazers_count")
            f = data.get("forks")
            stars = int(s) if isinstance(s, int) else None
            forks = int(f) if isinstance(f, int) else None
            return stars, forks

        if r.status_code == 404:
            return None, None

        retryable = r.status_code in (403, 429, 502, 503)
        if retryable and attempt + 1 < max_attempts:
            ra = (r.headers.get("Retry-After") or "").strip()
            if ra.isdigit():
                time.sleep(min(int(ra), 120))
            else:
                time.sleep(backoff_s)
                backoff_s *= 2
            continue

        return None, None

    return None, None


def fetch_github_stargazers(owner: str, repo: str) -> int | None:
    """GET ``/repos/{owner}/{repo}`` → ``stargazers_count``, or ``None`` on failure."""
    stars, _ = fetch_github_repo_stats(owner, repo)
    return stars
