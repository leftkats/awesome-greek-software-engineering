"""Build static ``index.html`` from YAML, Workable snapshot, and Jinja2.

Data flow
---------
1. ``data/companies.yaml`` — companies, sectors, locations, careers URLs, policies.
2. This module normalises rows and sets ``workable_slug`` for apply.workable.com URLs
   (see ``scripts.workable_apply_slug``).
3. ``data/workable_counts.yaml`` — Greece ``incountry`` counts per slug, from
   ``python -m scripts.fetch_workable_counts`` (server-side; avoids browser CORS).
   Embedded in the page for badges, header totals, sort, and hiring-only filter.
4. ``templates/index_template.html`` → ``index.html``.

Run
---
* ``uv run python -m scripts.generate_index`` — render (use existing snapshot YAML if any).
* ``uv run python -m scripts.generate_index --fetch-workable`` — fetch then render.

CI: ``.github/workflows/sync-on-main-merge.yaml`` runs fetch + generate on push to
``main`` and weekly (Monday 05:00 UTC); commits ``data/workable_counts.yaml`` and
``index.html``. Paths align with ``scripts.fetch_workable_counts``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from collections import Counter

from jinja2 import Environment, FileSystemLoader

from scripts.workable_apply_slug import extract_workable_apply_slug

# --- Configuration (aligned with scripts/fetch_workable_counts.py) ---
YAML_PATH = "data/companies.yaml"
OUTPUT_PATH = "index.html"
SITEMAP_PATH = "sitemap.xml"
ROBOTS_PATH = "robots.txt"
ITEMS_PER_PAGE = 50
WORKABLE_SNAPSHOT_PATH = Path("data/workable_counts.yaml")

env = Environment(loader=FileSystemLoader("templates"))

_README_YAML = Path("readme.yaml")


def load_site_meta() -> dict:
    """SEO, Open Graph / Twitter, canonical URL (aligned with readme.yaml)."""
    origin = "https://leftkats.github.io/awesome-greek-tech-jobs"
    title = "Awesome Greek Tech Jobs"
    desc = (
        "Curated directory of tech companies hiring in Greece — sectors, "
        "work policies, career links, and hiring insights."
    )
    repo_slug = "leftkats/awesome-greek-tech-jobs"
    if _README_YAML.is_file():
        try:
            with _README_YAML.open(encoding="utf-8") as f:
                rd = yaml.safe_load(f) or {}
        except (yaml.YAMLError, OSError):
            rd = {}
        else:
            live = rd.get("live_url")
            if isinstance(live, str) and live.strip():
                origin = live.strip().rstrip("/")
            long_desc = rd.get("description")
            if isinstance(long_desc, str) and long_desc.strip():
                desc = " ".join(long_desc.split())
            rs = rd.get("repo")
            if isinstance(rs, str) and rs.strip():
                repo_slug = rs.strip()
    if len(desc) > 200:
        desc = desc[:197].rstrip() + "…"
    og_image_url = f"{origin}/assets/og-image.png"
    canonical_url = f"{origin}/"
    github_repo_url = f"https://github.com/{repo_slug}"
    document_title = f"{title} | Greece tech companies, jobs & careers"
    if len(document_title) > 60:
        document_title = f"{title} | Greece tech jobs & careers"
    seo_keywords = (
        "Greece tech jobs, software engineer Greece, IT careers Athens, "
        "remote work Greece, tech startups Greece, developer jobs Greece, "
        "engineering jobs Thessaloniki, tech hiring Greece"
    )
    return {
        "canonical_url": canonical_url,
        "site_origin": origin,
        "document_title": document_title,
        "og_description": desc,
        "og_image_url": og_image_url,
        "og_image_alt": f"{title} — preview image",
        "og_site_name": title,
        "github_repo_url": github_repo_url,
        "seo_keywords": seo_keywords,
    }


def build_schema_json_ld(
    *,
    canonical_url: str,
    origin: str,
    name: str,
    description: str,
    document_title: str,
    total_companies: int,
    github_repo_url: str,
) -> str:
    """JSON-LD graph: WebSite, Organization, WebPage, CollectionPage."""
    website_id = f"{origin}/#website"
    org_id = f"{origin}/#organization"
    graph: list[dict] = [
        {
            "@type": "WebSite",
            "@id": website_id,
            "url": canonical_url,
            "name": name,
            "description": description,
            "inLanguage": "en-GB",
            "publisher": {"@id": org_id},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"{origin}/?q={{search_term_string}}",
                },
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@type": "Organization",
            "@id": org_id,
            "name": name,
            "url": canonical_url,
            "sameAs": [github_repo_url],
        },
        {
            "@type": "WebPage",
            "@id": canonical_url,
            "url": canonical_url,
            "name": document_title,
            "description": description,
            "isPartOf": {"@id": website_id},
            "about": {
                "@type": "Thing",
                "name": "Technology employment and hiring in Greece",
            },
        },
        {
            "@type": "CollectionPage",
            "@id": f"{origin}/#directory",
            "name": "Tech companies hiring in Greece",
            "isPartOf": {"@id": canonical_url},
            "numberOfItems": total_companies,
        },
    ]
    payload = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(payload, ensure_ascii=False)


# --- Helper Functions ---
def get_policy_style(policy):
    if not policy:
        return "hidden"
    p = str(policy).lower()
    if "remote" in p:
        return " ".join(
            [
                "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-200",
                "dark:bg-emerald-500/10 dark:text-emerald-300",
                "dark:ring-emerald-400/30",
            ]
        )
    if "hybrid" in p:
        return " ".join(
            [
                "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-200",
                "dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/30",
            ]
        )
    return " ".join(
        [
            "bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-200",
            "dark:bg-slate-500/10 dark:text-slate-300 dark:ring-slate-400/30",
        ]
    )


def normalize_url(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() == "none":
        return None
    return s


def normalize_sector(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return " ".join(s.split())


def normalize_location(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = " ".join(s.split())
    if s.casefold() in {"athina"}:
        return "Athens"
    if s.casefold() in {"thessaloniki", "thessaloníki"}:
        return "Thessaloniki"
    return s


def normalize_policy(value):
    raw = (value or "").strip().lower()
    if not raw:
        return "n/a"
    if raw in {"n/a", "na", "none"}:
        return "n/a"
    if raw == "remote":
        return "remote"
    if raw == "hybrid":
        return "hybrid"
    if raw in {"on-site", "onsite", "on site"}:
        return "on-site"
    return raw


def load_workable_snapshot():
    """Load ``data/workable_counts.yaml`` for embedding in the HTML output."""
    if not WORKABLE_SNAPSHOT_PATH.is_file():
        return {"generated_at": None, "accounts": {}, "total_open": 0}
    try:
        with WORKABLE_SNAPSHOT_PATH.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return {"generated_at": None, "accounts": {}, "total_open": 0}
    if not isinstance(data, dict):
        return {"generated_at": None, "accounts": {}, "total_open": 0}
    accounts = data.get("accounts")
    if not isinstance(accounts, dict):
        accounts = {}
    total = data.get("total_open")
    if not isinstance(total, int):
        total = sum(n for n in accounts.values() if isinstance(n, int))
    return {
        "generated_at": data.get("generated_at"),
        "accounts": accounts,
        "total_open": total,
        "metric": data.get("metric") or "incountry_greece",
    }


def run_generate_index() -> None:
    """Load YAML, snapshot, render template, write ``index.html``."""
    try:
        with open(YAML_PATH, "r", encoding="utf-8") as f:
            companies_data = yaml.load(f, Loader=yaml.FullLoader)

        if not companies_data:
            print("No companies found in source.")
            companies_data = []

        all_sectors = set()
        all_locations = set()
        policy_counts = Counter()
        sector_counts = Counter()
        location_counts = Counter()

        for c in companies_data:
            if not c.get("work_policy"):
                c["work_policy"] = "N/A"
            else:
                c["work_policy"] = str(c["work_policy"]).strip()

            careers_url = normalize_url(c.get("careers_url"))
            company_url = normalize_url(c.get("url"))
            c["careers_url"] = careers_url
            c["url"] = company_url
            c["site_url"] = company_url or "#"
            c["career_url"] = careers_url or company_url or "#"
            c["workable_slug"] = extract_workable_apply_slug(careers_url)

            raw_sectors = c.get("sectors", []) or []
            normalized = []
            for s in raw_sectors:
                ns = normalize_sector(s)
                if ns:
                    normalized.append(ns)

            seen = set()
            deduped = []
            for s in normalized:
                k = s.casefold()
                if k in seen:
                    continue
                seen.add(k)
                deduped.append(s)
            deduped.sort(key=lambda x: x.casefold())
            c["sectors"] = deduped

            raw_locations = c.get("locations", []) or []
            loc_normalized = []
            for loc in raw_locations:
                nl = normalize_location(loc)
                if nl:
                    loc_normalized.append(nl)
            seen = set()
            loc_deduped = []
            for loc in loc_normalized:
                k = loc.casefold()
                if k in seen:
                    continue
                seen.add(k)
                loc_deduped.append(loc)
            loc_deduped.sort(key=lambda x: x.casefold())
            c["locations"] = loc_deduped

            for s in c.get("sectors", []):
                all_sectors.add(s)
                sector_counts[s] += 1
            for loc in c.get("locations", []):
                all_locations.add(loc)
                location_counts[loc] += 1

            policy_counts[normalize_policy(c.get("work_policy"))] += 1

        sorted_sectors = sorted(list(all_sectors))
        sorted_locations = sorted(list(all_locations))

        stats = {
            "total_companies": len(companies_data),
            "policy_counts": dict(policy_counts),
            "top_sectors": sector_counts.most_common(10),
            "top_locations": location_counts.most_common(10),
            "workable_companies_count": sum(
                1 for c in companies_data if c.get("workable_slug")
            ),
        }

    except FileNotFoundError:
        print(f"Error: {YAML_PATH} not found.", file=sys.stderr)
        raise SystemExit(1)

    template = env.get_template("index_template.html")

    _workable_snapshot = load_workable_snapshot()
    _meta = load_site_meta()
    _schema = build_schema_json_ld(
        canonical_url=_meta["canonical_url"],
        origin=_meta["site_origin"],
        name=_meta["og_site_name"],
        description=_meta["og_description"],
        document_title=_meta["document_title"],
        total_companies=stats["total_companies"],
        github_repo_url=_meta["github_repo_url"],
    )
    final_html = template.render(
        companies=companies_data,
        sectors=sorted_sectors,
        locations=sorted_locations,
        items_per_page=ITEMS_PER_PAGE,
        get_style=get_policy_style,
        stats=stats,
        workable_snapshot=_workable_snapshot,
        workable_snapshot_json=json.dumps(_workable_snapshot, ensure_ascii=False),
        schema_json_ld=_schema,
        **_meta,
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(final_html)

    lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{_meta['canonical_url']}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        "    <changefreq>daily</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    robots_body = (
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {_meta['site_origin']}/sitemap.xml\n"
    )
    with open(ROBOTS_PATH, "w", encoding="utf-8") as f:
        f.write(robots_body)

    print("Website updated with modernized UI template and refreshed styles.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate index.html from data/companies.yaml and templates.",
    )
    parser.add_argument(
        "--fetch-workable",
        action="store_true",
        help=(
            "Run fetch_workable_counts first (writes data/workable_counts.yaml "
            "over the network)."
        ),
    )
    args = parser.parse_args(argv)

    if args.fetch_workable:
        from scripts.fetch_workable_counts import main as fetch_workable_main

        rc = fetch_workable_main()
        if rc != 0:
            return rc

    run_generate_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
