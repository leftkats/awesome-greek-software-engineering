#!/usr/bin/env python3
"""Discover top GitHub repos for committers.top Greece users.

Uses ``GET /users/{login}/repos`` (paginated) to pick candidates, then **always**
``GET /repos/{owner}/{repo}`` for each chosen repo so the YAML **description** matches
GitHub’s public repository description field (not the list payload).

A ``GITHUB_TOKEN`` or ``GH_TOKEN`` is **strongly recommended** (5k req/hr vs 60 for unauthenticated).

By default adds up to **2** public, non-fork repos per user, sorted by stars, that are not
already listed in ``_data/open_source_projects.yaml``. Repos must have **at least 1 star
or 1 fork** (``--min-engagement``).

Environment:
  COMMITTERS_GREECE_JSON  Override JSON list URL (default: committers.top ``rank_only/greece.json``)
  COMMITTERS_ONLY         Comma-separated logins (override built-in list)
  GITHUB_TOKEN / GH_TOKEN

Examples:
  GITHUB_TOKEN=ghp_… uv run python scripts/_committers_top_repos.py --batch greece-all
  GITHUB_TOKEN=ghp_… uv run python scripts/_committers_top_repos.py --batch missing-and-61-120
  COMMITTERS_ONLY=sgoudelis,ggozad uv run python scripts/_committers_top_repos.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

SESSION = requests.Session()
SESSION.headers.update(
    {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "greek-software-ecosystem-committers-import",
    }
)
_token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
if _token:
    SESSION.headers["Authorization"] = f"Bearer {_token}"

# Core REST: stay polite even with a token.
_REQUEST_DELAY_S = 0.35


def norm_repo(url: str) -> str | None:
    try:
        p = urlparse(url.strip())
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
    return f"{parts[0].lower()}/{parts[1].lower()}"


def load_existing_repos(yaml_path: str) -> set[str]:
    text = open(yaml_path, encoding="utf-8").read()
    out: set[str] = set()
    for m in re.finditer(r"https://github\.com/[^/\s]+/[^/\s)]+", text):
        n = norm_repo(m.group(0).rstrip("/"))
        if n:
            out.add(n)
    return out


def fetch_user_repos_all(login: str) -> list[dict]:
    """All public owner repos (paginated)."""
    repos: list[dict] = []
    page = 1
    while page <= 15:
        time.sleep(_REQUEST_DELAY_S)
        r = SESSION.get(
            f"https://api.github.com/users/{login}/repos",
            params={
                "type": "owner",
                "per_page": 100,
                "page": page,
                "sort": "pushed",
            },
            timeout=45,
        )
        if r.status_code == 404:
            return []
        if r.status_code == 403:
            raise requests.HTTPError(f"{r.status_code} {r.text[:200]}", response=r)
        r.raise_for_status()
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def yaml_escape_desc(s: str) -> str:
    s = " ".join((s or "").split())
    return s.replace("|", "\\|")


def fetch_public_description_from_github(full_name: str) -> str:
    """``GET /repos/{owner}/{repo}`` → public ``description`` (empty if GitHub has none)."""
    parts = [p for p in full_name.split("/") if p]
    if len(parts) != 2:
        return ""
    owner, repo = parts[0], parts[1]
    time.sleep(_REQUEST_DELAY_S)
    r = SESSION.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        params={},
        timeout=45,
    )
    if r.status_code != 200:
        return ""
    try:
        data = r.json()
    except (TypeError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    d = data.get("description")
    if d is None:
        return ""
    return str(d).strip()


# First 60 ranks: users that previously failed Search API (still worth filling).
MISSING_FROM_TOP60 = [
    "sgoudelis",
    "ggozad",
    "a8anassis",
    "matentzn",
    "Basilakis",
    "skorokithakis",
    "dzervas",
    "mandarini",
    "annakrystalli",
    "chrisK824",
    "OverloadedOrama",
    "kargig",
    "glogiotatidis",
    "Geoxor",
    "bill88t",
    "Kapendev",
    "dgrammatiko",
    "AlexandrosPanag",
    "PavlosIsaris",
]

# committers.top/greece ranks 61–120 (see site table).
RANKS_61_120 = [
    "KaloudasDev",
    "akatsoulas",
    "nikosdouvlis",
    "ppapadeas",
    "ArjixWasTaken",
    "WindowsNT",
    "statlink",
    "arisgk",
    "christosporios",
    "dspinellis",
    "paulkokos",
    "cerebrux",
    "birbilis",
    "OFFTKP",
    "purpl3F0x",
    "Acherontas",
    "greekfetacheese",
    "kvantas",
    "geooo109",
    "nikosdion",
    "jimmykarily",
    "MarieGutiz",
    "keybraker",
    "grgalex",
    "kostis",
    "evangelosmeklis",
    "iosifidis",
    "XhmikosR",
    "thgreasi",
    "nkast",
    "ntsekouras",
    "Zapotek",
    "ParaskP7",
    "themicp",
    "APZelos",
    "ObserverOfTime",
    "pyscripter",
    "vagman",
    "iani",
    "DRgreenT",
    "theodorosploumis",
    "GeopJr",
    "m-Peter",
    "VelocityRa",
    "AmmarkoV",
    "solisoft",
    "g-laliotis",
    "Trinityyi",
    "VaggelisD",
    "operatorequals",
    "PanagiotisKotsorgios",
    "chrismitsdev",
    "ftylitak",
    "menmaa",
    "ChrsMark",
    "MFDGaming",
    "stefaniamak",
    "frizchar",
    "ankostis",
    "Cranot",
]

COMMITTERS_GREECE_JSON = os.environ.get(
    "COMMITTERS_GREECE_JSON",
    "https://committers.top/rank_only/greece.json",
)


def fetch_committers_greece_usernames() -> list[str]:
    """Load ranked GitHub logins from committers.top machine-readable JSON."""
    time.sleep(_REQUEST_DELAY_S)
    r = SESSION.get(COMMITTERS_GREECE_JSON, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        return []
    users = data.get("user")
    if not isinstance(users, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for u in users:
        if not isinstance(u, str) or not u.strip():
            continue
        login = u.strip()
        if login.lower() in seen:
            continue
        seen.add(login.lower())
        out.append(login)
    return out


def pick_top_repos(
    login: str,
    *,
    existing: set[str],
    seen_new: set[str],
    limit: int,
    min_stars_or_forks: bool,
) -> list[tuple[str, str, str]]:
    """Return up to ``limit`` tuples (full_name, html_url, description)."""
    try:
        raw = fetch_user_repos_all(login)
    except requests.HTTPError as e:
        print(f"# skip {login}: {e}", file=sys.stderr)
        return []

    owned: list[dict] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        if r.get("fork") or r.get("private"):
            continue
        owner = (r.get("owner") or {}).get("login") or ""
        if owner.lower() != login.lower():
            continue
        stars = int(r.get("stargazers_count") or 0)
        forks = int(r.get("forks") or 0)
        if min_stars_or_forks and stars < 1 and forks < 1:
            continue
        owned.append(r)

    owned.sort(
        key=lambda x: (
            int(x.get("stargazers_count") or 0),
            int(x.get("forks") or 0),
        ),
        reverse=True,
    )

    candidates: list[dict] = []
    for r in owned:
        fn = (r.get("full_name") or "").strip()
        if not fn:
            continue
        key = fn.lower()
        if key in existing or key in seen_new:
            continue
        url = (r.get("html_url") or "").strip() or f"https://github.com/{fn}"
        candidates.append({"full_name": fn, "html_url": url})
        if len(candidates) >= limit:
            break

    out: list[tuple[str, str, str]] = []
    for c in candidates:
        fn = c["full_name"]
        url = c["html_url"]
        # Canonical public description from GitHub (not the list payload).
        gh_desc = fetch_public_description_from_github(fn)
        if not gh_desc:
            gh_desc = "No description on GitHub—see the repository README."
        desc = yaml_escape_desc(gh_desc)
        out.append((fn, url, desc))
        seen_new.add(fn.lower())
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--batch",
        choices=("greece-all", "missing-and-61-120", "61-120", "missing-60"),
        default="missing-and-61-120",
        help=(
            "greece-all = fetch ranked list from committers.top/greece.html (256 users); "
            "other presets use bundled username lists."
        ),
    )
    ap.add_argument("--per-user", type=int, default=2, help="Max repos per user (default: 2).")
    ap.add_argument(
        "--min-engagement",
        action="store_true",
        default=True,
        help="Require at least 1 star or 1 fork (default: on).",
    )
    ap.add_argument(
        "--no-min-engagement",
        action="store_false",
        dest="min_engagement",
        help="Allow 0 stars and 0 forks.",
    )
    args = ap.parse_args()

    if args.batch == "greece-all":
        try:
            users = fetch_committers_greece_usernames()
        except (OSError, json.JSONDecodeError, requests.RequestException, requests.HTTPError) as e:
            print(f"# failed to fetch {COMMITTERS_GREECE_JSON}: {e}", file=sys.stderr)
            sys.exit(1)
        if not users:
            print("# no usernames in committers JSON", file=sys.stderr)
            sys.exit(1)
        print(f"# loaded {len(users)} users from {COMMITTERS_GREECE_JSON}", file=sys.stderr)
    elif args.batch == "61-120":
        users = list(RANKS_61_120)
    elif args.batch == "missing-60":
        users = list(MISSING_FROM_TOP60)
    else:
        users = list(dict.fromkeys(MISSING_FROM_TOP60 + RANKS_61_120))

    _only = (os.environ.get("COMMITTERS_ONLY") or "").strip()
    if _only:
        users = [x.strip() for x in _only.split(",") if x.strip()]

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    yaml_path = os.path.join(root, "_data", "open_source_projects.yaml")
    existing = load_existing_repos(yaml_path)
    seen_new: set[str] = set()

    if not _token:
        print(
            "# Warning: no GITHUB_TOKEN/GH_TOKEN — you may hit rate limits quickly.",
            file=sys.stderr,
        )

    for login in users:
        picked = pick_top_repos(
            login,
            existing=existing,
            seen_new=seen_new,
            limit=args.per_user,
            min_stars_or_forks=args.min_engagement,
        )
        for fn, url, desc in picked:
            title = fn.split("/")[-1].replace("_", " ")
            print(f"  - title: {title}")
            print(f"    url: {url}")
            print(f"    description: >")
            print(
                f"      {desc} · From [committers.top Greece](https://committers.top/greece.html) "
                f"(maintainer **{fn.split('/')[0]}**)."
            )
            print()


if __name__ == "__main__":
    main()
