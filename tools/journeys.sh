#!/usr/bin/env bash
# Browser journeys against made-up data: tools/journeys.sh
# Starts tools/screenshots/example_server.py (nothing real is read) and runs tools/journeys/journeys.mjs in the
# Playwright image: Manage apps, text that looks like code, the content policy, a saved key that must never come
# back, phone width on every page, and that every page script parses (TEST-PLAN USE-01, USE-02, SEC-07, SEC-12, SEC-13, APP-01). Run it before each
# release. Needs Docker and network access (the first run downloads the Playwright image).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${JOURNEYS_PORT:-18794}"
PLAYWRIGHT="1.63.0"
work="$(mktemp -d)"
trap 'kill "$server" 2>/dev/null || true; rm -rf "$work"' EXIT

EXAMPLE_CONTAINERS=1 python3 tools/screenshots/example_server.py "$work/data" "$PORT" > "$work/server.log" 2>&1 &
server=$!
for _ in $(seq 1 30); do grep -q READY "$work/server.log" 2>/dev/null && break; sleep 1; done
grep -q READY "$work/server.log" || { cat "$work/server.log"; echo "The example server did not start" >&2; exit 1; }

docker run --rm --network host -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e BASE="http://127.0.0.1:$PORT" -e PASSWORD_FILE=/work/data/password \
  -v "$work:/work" -v "$PWD/tools/journeys/journeys.mjs:/j/journeys.mjs:ro" -v "$PWD/web/js:/web-js:ro" \
  "mcr.microsoft.com/playwright:v$PLAYWRIGHT-noble" \
  sh -c "for f in /web-js/*.js; do node --check \$f || exit 1; done && echo 'PASS every page script parses' && mkdir -p /tmp/j && cp /j/journeys.mjs /tmp/j/ && cd /tmp/j && npm init -y >/dev/null && npm i --silent playwright@$PLAYWRIGHT >/dev/null && node journeys.mjs"
