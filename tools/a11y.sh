#!/usr/bin/env bash
# Accessibility check of every page against made-up data: tools/a11y.sh
# Starts tools/screenshots/example_server.py (nothing real is read) and runs tools/a11y/a11y.mjs in the Playwright
# image with axe-core. Writes tools/a11y/a11y.json. Needs Docker and network access the first time.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${A11Y_PORT:-18796}"
PLAYWRIGHT="1.63.0"
AXE_VERSION="4.14.0"
work="$(mktemp -d)"
trap 'kill "$server" 2>/dev/null || true; rm -rf "$work"' EXIT
EXAMPLE_CONTAINERS=1 python3 tools/screenshots/example_server.py "$work/data" "$PORT" > "$work/server.log" 2>&1 &
server=$!
for _ in $(seq 1 30); do grep -q READY "$work/server.log" 2>/dev/null && break; sleep 1; done
grep -q READY "$work/server.log" || { cat "$work/server.log"; echo "The example server did not start" >&2; exit 1; }
docker run --rm --network host -u "$(id -u):$(id -g)" -e HOME=/tmp -e BASE="http://127.0.0.1:$PORT" -e PASSWORD_FILE=/work/data/password \
  -e PAGES="${PAGES:-}" -e OUT=/work/a11y.json -v "$work:/work" -v "$PWD/tools/a11y/a11y.mjs:/j/a11y.mjs:ro" -v "$PWD/web:/web:ro" \
  "mcr.microsoft.com/playwright:v$PLAYWRIGHT-noble" \
  sh -c "mkdir -p /tmp/a && cp /j/a11y.mjs /tmp/a/ && cd /tmp/a && npm init -y >/dev/null && npm i --silent playwright@$PLAYWRIGHT axe-core@$AXE_VERSION >/dev/null && node a11y.mjs"
cp "$work/a11y.json" tools/a11y/a11y.json
