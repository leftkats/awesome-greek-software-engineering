"""Map ``_data/podcasts.yaml`` URL fields to UI chips and Markdown tables."""

from __future__ import annotations

from html import escape
from urllib.parse import urlparse

# CSV order: YAML key, short label for summary-table columns, HTML chip label, icon ``kind``.
_PODCAST_URL_SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("website_url", "Web", "Website", "site"),
    ("spotify_url", "Spotify", "Spotify", "spotify"),
    ("youtube_url", "YouTube", "YouTube", "youtube"),
    ("apple_podcasts_url", "Apple", "Apple Podcasts", "apple"),
    ("google_podcasts_url", "Google", "Google Podcasts", "google_podcasts"),
    ("simplecast_url", "Simplecast", "Simplecast", "other"),
    ("podlist_url", "Podlist", "Podlist", "other"),
)


def _anchor_for_chip(yaml_key: str, chip_label: str, url: str) -> str:
    if yaml_key == "website_url":
        parsed = urlparse(url.strip())
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host or chip_label
    return chip_label


def podcast_links_from_entry(pod: dict) -> list[dict]:
    """
    Build ``links`` for ``page_podcasts.html`` — ``label``, ``url``, ``anchor``, ``kind``.
    """
    out: list[dict] = []
    for yaml_key, _short, chip_label, kind in _PODCAST_URL_SPECS:
        url = (pod.get(yaml_key) or "").strip()
        if not url:
            continue
        anchor = _anchor_for_chip(yaml_key, chip_label, url)
        out.append(
            {
                "label": chip_label,
                "url": url,
                "anchor": anchor,
                "kind": kind,
            }
        )
    return out


def podcast_summary_table_columns() -> list[tuple[str, str]]:
    """(YAML key, column header) for the wide **availability** table."""
    return [(spec[0], spec[1]) for spec in _PODCAST_URL_SPECS]


def podcast_summary_markdown_cell(pod: dict, yaml_key: str) -> str:
    """One table cell: ``[●](url)`` if present, else ``—``."""
    url = (pod.get(yaml_key) or "").strip()
    if not url:
        return "—"
    return f"[●]({url})"


def podcast_summary_matrix_markdown_lines(podcasts: list[dict]) -> list[str]:
    """GitHub-flavored Markdown rows for the all-shows × platforms table."""
    cols = podcast_summary_table_columns()
    lines: list[str] = [
        "| Podcast | " + " | ".join(h for _, h in cols) + " |",
        "| :--- | " + " | ".join(":---:" for _ in cols) + " |",
    ]
    for pod in podcasts:
        if not isinstance(pod, dict):
            continue
        title = (pod.get("title") or "").strip()
        if not title:
            continue
        cells = [podcast_summary_markdown_cell(pod, k) for k, _ in cols]
        safe = title.replace("|", "\\|")
        lines.append(f"| **{safe}** | " + " | ".join(cells) + " |")
    return lines


def podcast_summary_table_html(podcasts: list[dict]) -> str:
    """Semantic HTML table for the podcasts page (platform availability)."""
    cols = podcast_summary_table_columns()
    parts: list[str] = [
        '<div class="overflow-x-auto -mx-1 px-1" role="region" aria-label="Podcasts by platform">',
        '<table class="w-full min-w-[40rem] text-sm border border-slate-200/90 dark:border-slate-700/90 rounded-xl overflow-hidden">',
        "<thead><tr>",
        '<th scope="col" class="text-left font-semibold px-3 py-2.5 bg-slate-50/90 dark:bg-slate-800/60 text-slate-900 dark:text-slate-100">Podcast</th>',
    ]
    for _, h in cols:
        parts.append(
            f'<th scope="col" class="text-center font-semibold px-2 py-2.5 whitespace-nowrap '
            f'bg-slate-50/90 dark:bg-slate-800/60 text-slate-900 dark:text-slate-100">{escape(h)}</th>'
        )
    parts.append("</tr></thead>")
    parts.append("<tbody>")
    for pod in podcasts:
        if not isinstance(pod, dict):
            continue
        title = (pod.get("title") or "").strip()
        if not title:
            continue
        parts.append(
            '<tr class="border-t border-slate-200/80 dark:border-slate-700/60 '
            'bg-white/80 dark:bg-slate-900/40">'
            f'<th scope="row" class="text-left font-medium px-3 py-2.5 align-middle max-w-[16rem] '
            f'text-slate-900 dark:text-slate-100">{escape(title)}</th>'
        )
        for key, h in cols:
            url = (pod.get(key) or "").strip()
            if url:
                aria = f"{title} — {h}"
                parts.append(
                    f'<td class="text-center px-2 py-2.5 align-middle">'
                    f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer" '
                    f'class="inline-flex h-8 min-w-[2rem] px-1.5 items-center justify-center rounded-lg '
                    f"bg-cyan-50 dark:bg-cyan-950/50 text-cyan-800 dark:text-cyan-200 "
                    f'hover:bg-cyan-100 dark:hover:bg-cyan-900/40 font-bold leading-none" '
                    f'title="{escape(aria)}" aria-label="{escape(aria)}">●</a></td>'
                )
            else:
                parts.append(
                    '<td class="text-center px-2 py-2.5 text-slate-400 dark:text-slate-600 '
                    'align-middle">—</td>'
                )
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)
