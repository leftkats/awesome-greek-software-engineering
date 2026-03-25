import yaml
from collections import Counter

# import random
from jinja2 import Environment, FileSystemLoader

# --- Configuration ---
YAML_PATH = "data/companies.yaml"
OUTPUT_PATH = "index.html"
ITEMS_PER_PAGE = 50
env = Environment(loader=FileSystemLoader("templates"))


# --- Helper Functions ---
def get_policy_style(policy):
    if not policy:
        return "hidden"
    p = str(policy).lower()
    if "remote" in p:
        return "bg-green-100 text-green-800"
    if "hybrid" in p:
        return "bg-yellow-100 text-yellow-800"
    return "bg-gray-100 text-gray-800"


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
    # Common canonicalizations
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


# --- Load and Prepare Data ---
try:
    with open(YAML_PATH, "r", encoding="utf-8") as f:
        companies_data = yaml.load(f, Loader=yaml.FullLoader)

    if not companies_data:
        # In case the company doesn't have jobs in Greece or YAML is empty
        print("No companies found in source.")
        companies_data = []

    all_sectors = set()
    all_locations = set()
    policy_counts = Counter()
    sector_counts = Counter()
    location_counts = Counter()

    for c in companies_data:
        # Assign random policy if missing as requested
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
    }

except FileNotFoundError:
    print(f"Error: {YAML_PATH} not found.")
    exit()

# --- HTML Template ---
template = env.get_template("index_template.html")

# --- Build Execution ---
final_html = template.render(
    companies=companies_data,
    sectors=sorted_sectors,
    locations=sorted_locations,
    items_per_page=ITEMS_PER_PAGE,
    get_style=get_policy_style,
    stats=stats,
)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(final_html)

print("Website updated with specified Nav, Header, and Search UI components.")
