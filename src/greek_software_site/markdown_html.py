"""Convert repository Markdown to HTML for the static site."""

from __future__ import annotations

import re
from pathlib import Path

import markdown

_MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "nl2br"]


def _site_page_hrefs(site_baseurl: str, *, local_flat: bool = False) -> dict[str, str]:
    """Map local ``*.md`` names to site paths (Jekyll URLs or sibling ``*.html`` when ``local_flat``)."""
    if local_flat:
        return {
            "readme.md": "index.html",
            "engineering-hubs.md": "job-search.html#employers",
            "search-queries-and-resources.md": "job-search.html",
            "greek-tech-podcasts.md": "podcasts.html",
            "remote-cafe-resources.md": "resources.html",
            "open-source-projects.md": "open-source.html",
        }
    b = (site_baseurl or "").rstrip("/")
    root = f"{b}/" if b else "/"
    eng = f"{b}/job-search/#employers" if b else "/job-search/#employers"
    jq = f"{b}/job-search/" if b else "/job-search/"
    pod = f"{b}/podcasts/" if b else "/podcasts/"
    res = f"{b}/resources/" if b else "/resources/"
    osp = f"{b}/open-source/" if b else "/open-source/"
    return {
        "readme.md": root,
        "engineering-hubs.md": eng,
        "search-queries-and-resources.md": jq,
        "greek-tech-podcasts.md": pod,
        "remote-cafe-resources.md": res,
        "open-source-projects.md": osp,
    }


def _rewrite_repo_markdown_hrefs(
    html: str,
    github_repo_url: str,
    site_baseurl: str = "",
    *,
    local_flat: bool = False,
) -> str:
    """Rewrite ``*.md`` hrefs to site pages or the GitHub repo (no blob ``.md``)."""
    gh = (github_repo_url or "").strip().rstrip("/")
    md_map = _site_page_hrefs(site_baseurl, local_flat=local_flat)
    b = (site_baseurl or "").rstrip("/")
    home = "index.html" if local_flat else (f"{b}/" if b else "/")

    def repl_double(m: re.Match[str]) -> str:
        href = m.group(1)
        if href.startswith(("#", "mailto:", "javascript:", "data:")):
            return m.group(0)
        if "://" not in href:
            base = href.split("/")[-1].strip().casefold()
            if base in md_map:
                return f'href="{md_map[base]}"'
            if base == "development.md":
                return f'href="{gh}"' if gh else f'href="{home}"'
            if base == "contributing.md":
                return f'href="{gh}/contribute"' if gh else f'href="{home}"'
        if gh and href.startswith("https://github.com/") and "/blob/" in href:
            lower = href.lower()
            if not lower.endswith(".md"):
                return m.group(0)
            if "contributing.md" in lower:
                return f'href="{gh}/contribute"'
            if lower.rstrip("/").endswith("/readme.md"):
                return f'href="{home}"'
            return f'href="{gh}"'
        return m.group(0)

    return re.sub(r'href="([^"]+)"', repl_double, html)


def markdown_to_html(
    raw: str,
    *,
    github_repo_url: str = "",
    site_baseurl: str = "",
    local_flat: bool = False,
) -> str:
    """Parse Markdown, then rewrite repo ``.md`` links for the static site."""
    html = markdown.markdown(raw, extensions=_MARKDOWN_EXTENSIONS)
    return _rewrite_repo_markdown_hrefs(
        html,
        github_repo_url,
        site_baseurl,
        local_flat=local_flat,
    )


def markdown_file_to_html(
    path: Path,
    *,
    github_repo_url: str = "",
    site_baseurl: str = "",
    local_flat: bool = False,
) -> str:
    """Load a Markdown file; return HTML for embedding in Jinja templates."""
    return markdown_to_html(
        path.read_text(encoding="utf-8"),
        github_repo_url=github_repo_url,
        site_baseurl=site_baseurl,
        local_flat=local_flat,
    )
