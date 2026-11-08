#!/usr/bin/env bash
# Takes the help centre's screenshots from made-up data, marked up with annotate.js, into docs/help/images:
#   tools/help-screenshots.sh [topic,topic...]     (all of tools/screenshots/help_shots.json when none is given)
# Look at every picture before committing (docs/help/HOW-THIS-HELP-IS-WRITTEN.md, Screenshots).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${SHOTS_PORT:-18792}"
PLAYWRIGHT="1.63.0"
work="$(mktemp -d)"
trap 'kill "$server" 2>/dev/null || true; rm -rf "$work"' EXIT
EXAMPLE_CONTAINERS=1 python3 tools/screenshots/example_server.py "$work/data" "$PORT" > "$work/server.log" 2>&1 &
server=$!
for _ in $(seq 1 30); do grep -q READY "$work/server.log" 2>/dev/null && break; sleep 1; done
grep -q READY "$work/server.log" || { cat "$work/server.log"; echo "The example server did not start" >&2; exit 1; }
mkdir -p "$work/out"
status=0
docker run --rm --network host -u "$(id -u):$(id -g)" -e HOME=/tmp -e ONLY="${1:-}" \
  -e BASE="http://127.0.0.1:$PORT" -e PASSWORD_FILE=/work/data/password -e OUT=/work/out \
  -v "$work:/work" -v "$PWD/tools/screenshots:/shots:ro" \
  "mcr.microsoft.com/playwright:v$PLAYWRIGHT-noble" \
  sh -c "mkdir -p /tmp/s && cp -r /shots/help_shoot.mjs /shots/help_shots.json /shots/annotate.js /shots/terminal /tmp/s/ && cd /tmp/s && npm init -y >/dev/null && npm i --silent playwright@$PLAYWRIGHT >/dev/null && node help_shoot.mjs" || status=$?
mkdir -p docs/help/images
cp "$work"/out/*.png docs/help/images/ 2>/dev/null || true
command -v pngquant >/dev/null && pngquant --force --ext .png --quality 70-90 docs/help/images/*.png 2>/dev/null || true
echo "Written to docs/help/images. Look at each one before committing."
exit $status
