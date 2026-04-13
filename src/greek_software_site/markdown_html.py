"""Convert repository Markdown to HTML for the static site."""

from __future__ import annotations

import re
from pathlib import Path

import markdown

_MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "nl2br"]

# Local repo markdown → static HTML (site navigation; keep in sync with pages).
_MD_FILENAME_TO_PAGE: dict[str, str] = {
    "readme.md": "index.html",
    "engineering-hubs.md": "job-search.html#employers",
    "search-queries-and-resources.md": "job-search.html",
    "greek-tech-podcasts.md": "podcasts.html",
    "remote-cafe-resources.md": "resources.html",
}


def _rewrite_repo_markdown_hrefs(html: str, github_repo_url: str) -> str:
    """Rewrite ``*.md`` hrefs to static pages or the GitHub repo (no blob ``.md``)."""
    gh = (github_repo_url or "").strip().rstrip("/")

    def repl_double(m: re.Match[str]) -> str:
        href = m.group(1)
        if href.startswith(("#", "mailto:", "javascript:", "data:")):
            return m.group(0)
        if "://" not in href:
            base = href.split("/")[-1].strip().casefold()
            if base in _MD_FILENAME_TO_PAGE:
                return f'href="{_MD_FILENAME_TO_PAGE[base]}"'
            if base == "development.md":
                return f'href="{gh}"' if gh else 'href="index.html"'
            if base == "contributing.md":
                return f'href="{gh}/contribute"' if gh else 'href="index.html"'
        if gh and href.startswith("https://github.com/") and "/blob/" in href:
            lower = href.lower()
            if not lower.endswith(".md"):
                return m.group(0)
            if "contributing.md" in lower:
                return f'href="{gh}/contribute"'
            if lower.rstrip("/").endswith("/readme.md"):
                return 'href="index.html"'
            return f'href="{gh}"'
        return m.group(0)

    return re.sub(r'href="([^"]+)"', repl_double, html)


def markdown_to_html(raw: str, *, github_repo_url: str = "") -> str:
    """Parse Markdown, then rewrite repo ``.md`` links for the static site."""
    html = markdown.markdown(raw, extensions=_MARKDOWN_EXTENSIONS)
    return _rewrite_repo_markdown_hrefs(html, github_repo_url)


def markdown_file_to_html(path: Path, *, github_repo_url: str = "") -> str:
    """Load a Markdown file; return HTML for embedding in Jinja templates."""
    return markdown_to_html(path.read_text(encoding="utf-8"), github_repo_url=github_repo_url)
