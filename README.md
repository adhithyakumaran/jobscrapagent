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

### Windows (Git Bash) troubleshooting

1. **Update the repo** (fixes `requires Python 3.11` on older clones):
   ```bash
   git pull origin main
   ```
2. **Remove a broken venv** if `activate` is missing (e.g. you interrupted `python -m venv`):
   ```bash
   rm -rf .venv
   python -m venv .venv
   ```
   Wait until venv finishes; do not press Ctrl+C during `ensurepip`.
3. **Activate** (Git Bash — use forward slashes, `source`, not a bare `C:\...` path):
   ```bash
   source .venv/Scripts/activate
   ```
4. **No venv** (works if venv keeps failing): from the repo root,
   ```bash
   pip install -e ".[dev]"
   ```
   Use the same `python` you will run for `python -m jobfinder`.

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
