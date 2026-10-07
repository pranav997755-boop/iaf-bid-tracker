#!/usr/bin/env bash
# Run the whole pipeline on your own computer (use this if GitHub's servers are blocked by GeM).
# Schedule it daily with cron (Mac/Linux) or Task Scheduler (Windows, via Git Bash/WSL).
set -euo pipefail
cd "$(dirname "$0")"
pip install -q -r requirements.txt && python -m playwright install chromium
python collector/scrape.py && python collector/build.py
git add data/state.json docs/data.json && (git diff --cached --quiet || git commit -qm "Daily refresh $(date +%F)") && git push
python collector/notify.py || true
