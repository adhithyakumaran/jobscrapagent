# Personal Job Finder

Local job-discovery tool — Phase 1 (mock) + Phase 2 (LinkedIn discovery).

## Setup

```bash
cd job-finder   # repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Edit `config/profile.yaml` for your locations, domains, roles, and exclusions (use `any` for broad coverage).

## Commands

```bash
# LinkedIn discovery (configure config/sources.yaml)
python -m jobfinder scan
python -m jobfinder scan --source linkedin --max-intents 12

# Mock data (offline)
python -m jobfinder scan --mock

python -m jobfinder stats
python -m jobfinder serve
```

LinkedIn settings: `config/sources.yaml` (rate limits, pages, provider order).

Optional: install Playwright for the browser provider: `pip install playwright && playwright install chromium`

Optional session cookies: set `linkedin.session_cookie_file` in `config/sources.yaml`.

Open http://127.0.0.1:8765

## Tests

```bash
pytest -q
```

Database file: `data/jobs.db` (created on first run).
