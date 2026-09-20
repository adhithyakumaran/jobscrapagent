# Personal Job Finder

Local job-discovery tool (Phase 1: mock data, SQLite, CLI, minimal web UI).

## Setup

```bash
cd job-finder   # repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Edit `config/profile.yaml` for your locations, domains, roles, and exclusions (use `any` for broad coverage).

## Phase 1 commands

```bash
python -m jobfinder scan --mock
python -m jobfinder stats
python -m jobfinder serve
```

Open http://127.0.0.1:8765

## Tests

```bash
pytest -q
```

Database file: `data/jobs.db` (created on first run).
