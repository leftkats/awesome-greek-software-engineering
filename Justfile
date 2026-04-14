# Developer command interface for Greek Software Ecosystem (uv underneath).
# List targets: `just` or `just --list`. Install just: https://github.com/casey/just

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# Default: show available recipes
default:
	@just --list

# Install / refresh Python dependencies. CI: `just sync --frozen`
setup *ARGS:
	uv sync {{ARGS}}

# Same as `setup` (common muscle memory for uv users).
sync *ARGS:
	uv sync {{ARGS}}

# Fetch Workable open-role counts into _data/workable_counts.yaml (network).
fetch:
	uv run python -m greek_software_ecosystem.fetch_workable_counts

# Fetch GitHub stars/forks for _data/open_source_projects.yaml → _data/open_source_github_stats.yaml (network).
fetch-open-source-stats:
	uv run python -m greek_software_ecosystem.fetch_open_source_github_stats

# Regenerate docs/*.md (plus root README.md stub) from _data/readme.yaml, open_source_projects.yaml, and other YAML data.
readme:
	uv run python -m greek_software_ecosystem.generate_readme

# Regenerate static HTML (open-source stars/forks come from _data/open_source_github_stats.yaml).
# Default on dev: sibling *.html + assets/ (python -m http.server). CI=true: Jekyll-style paths.
index:
	uv run python -m greek_software_ecosystem.generate_index

# Refresh OSS GitHub stats YAML, then regenerate HTML (use in CI / before deploy).
index-all:
	just fetch-open-source-stats
	uv run python -m greek_software_ecosystem.generate_index

# Force local-style output (same as default on a dev machine; use if CI is set in your shell).
index-local:
	AGTJ_LOCAL=1 uv run python -m greek_software_ecosystem.generate_index

# Force GitHub Pages / Jekyll-style output locally (dry-run deploy layout).
index-gh-pages:
	AGTJ_GH_PAGES=1 uv run python -m greek_software_ecosystem.generate_index

# Regenerate generated markdown + index (no Workable fetch).
generate: readme index

# Refresh Workable snapshot, then regenerate readme, hubs, and index.
all:
	just fetch
	just generate

# Same checks as PR validation: regenerate readme then index (fast; no OSS GitHub fan-out).
check:
	just readme
	just index
