#!/usr/bin/env bash
# End-to-end self-test: mock GeM -> scraper -> build -> phone UI. No internet needed.
set -euo pipefail; cd "$(dirname "$0")/.."
PY=${PYTHON:-$(command -v python3 || command -v python)}
export NO_PROXY=127.0.0.1 no_proxy=127.0.0.1
CHROME=${CHROMIUM_PATH:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}
$PY tests/mock_gem.py & MOCK=$!; trap "kill $MOCK" EXIT; sleep 1
GEM_BASE=http://127.0.0.1:8765 CHROMIUM_PATH=$CHROME GEM_OUT=data/raw.json $PY collector/scrape.py
rm -f data/state.json; $PY collector/build.py; $PY tests/ui_test.py
