# Personal Job Finder

Local job-discovery tool — Phase 1 (mock) + Phase 2 (LinkedIn discovery).

## Setup

Requires **Python 3.10+** (`python --version`).

```bash
git clone https://github.com/adhithyakumaran/jobscrapagent.git
cd jobscrapagent          # repository root (not the parent folder)
python -m venv .venv
# Windows (Git Bash):  source .venv/Scripts/activate
# Linux/macOS:         source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then edit .env with your Telegram token and chat id
```

Until you run `pip install -e .` inside the repo, `python -m jobfinder` will fail with **No module named jobfinder**.

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

# Telegram (after .env is configured)
python -m jobfinder telegram-chat-id   # message your bot first, then run this
python -m jobfinder telegram-test
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
