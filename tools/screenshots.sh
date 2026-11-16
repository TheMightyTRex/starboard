#!/usr/bin/env bash
# Retakes the README screenshots from made-up data: tools/screenshots.sh
# Starts tools/screenshots/example_server.py (nothing real is read), takes every shot listed in
# tools/screenshots/shoot.mjs in the Playwright image, and writes them to docs/screenshots. Run it before each
# release and look at every picture: check that the screens still match and that no real names, addresses
# or titles appear. Needs Docker and network access (the first run downloads the Playwright image).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${SHOTS_PORT:-18792}"
PLAYWRIGHT="1.63.0"
# Playwright's node modules from a cache folder when there is one (PLAYWRIGHT_NPM_CACHE), so a run needs no download.
cache="${PLAYWRIGHT_NPM_CACHE:-/mnt/pool/build-cache/npm-playwright-1.63}"
[ -d "$cache/node_modules/playwright" ] || cache=""
work="$(mktemp -d)"
trap 'kill "$server" 2>/dev/null || true; rm -rf "$work"' EXIT

EXAMPLE_CONTAINERS=1 python3 tools/screenshots/example_server.py "$work/data" "$PORT" > "$work/server.log" 2>&1 &
server=$!
for _ in $(seq 1 30); do grep -q READY "$work/server.log" 2>/dev/null && break; sleep 1; done
grep -q READY "$work/server.log" || { cat "$work/server.log"; echo "The example server did not start" >&2; exit 1; }

mkdir -p "$work/out"
docker run --rm --memory 3g --memory-swap 3g --cpus 4 --network host -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e BASE="http://127.0.0.1:$PORT" -e PASSWORD_FILE=/work/data/password -e OUT=/work/out \
  -v "$work:/work" -v "$PWD/tools/screenshots/shoot.mjs:/shots/shoot.mjs:ro" \
  ${cache:+-v "$cache:/cache:ro"} "mcr.microsoft.com/playwright:v$PLAYWRIGHT-noble" \
  sh -c "mkdir -p /tmp/s && cp /shots/shoot.mjs /tmp/s/ && cd /tmp/s && if [ -d /cache/node_modules/playwright ]; then ln -s /cache/node_modules node_modules; else npm init -y >/dev/null && npm i --silent playwright@$PLAYWRIGHT >/dev/null; fi && node shoot.mjs"

mkdir -p docs/screenshots
command -v pngquant >/dev/null && pngquant --force --ext .png --quality 70-90 "$work"/out/*.png || true
cp "$work"/out/*.png docs/screenshots/
echo "Written to docs/screenshots. Look at each one before committing."
