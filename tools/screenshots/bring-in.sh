#!/usr/bin/env bash
# Pictures of Bring in media (DASH-455) from made-up data: tools/screenshots/bring-in.sh [OUT folder]. ONLY=regex takes
# just the matching pictures. Starts the example server (nothing real is read) and runs bring-in.mjs in the Playwright
# image, under the heavy-job lock, with memory and processor caps. Look at every picture.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT="${1:-docs/screenshots/bring-in}"
PORT="${SHOTS_PORT:-18892}"
cache="${PLAYWRIGHT_NPM_CACHE:-/mnt/pool/build-cache/npm-playwright-1.63}"
[ -d "$cache/node_modules/playwright" ] || cache=""
work="$(mktemp -d)"
trap 'kill "$server" 2>/dev/null || true' EXIT
python3 tools/screenshots/example_server.py "$work/data" "$PORT" > "$work/server.log" 2>&1 &
server=$!
for _ in $(seq 1 40); do grep -q READY "$work/server.log" 2>/dev/null && break; sleep 1; done
grep -q READY "$work/server.log" || { cat "$work/server.log"; echo "The example server did not start" >&2; exit 1; }
mkdir -p "$work/out" "$OUT"
python3 tools/screenshots/bring-in-terminal.py "$work/term" >/dev/null  # the terminal set-up's screens, as pages
docker run --rm --memory 3g --memory-swap 3g --cpus 4 --network host -u "$(id -u):$(id -g)" -e HOME=/tmp -e ONLY="${ONLY:-}" \
  -e BASE="http://127.0.0.1:$PORT" -e PASSWORD_FILE=/work/data/password -e OUT=/work/out -e DATA=/work/data \
  -v "$work:/work" -v "$PWD/tools/screenshots/bring-in.mjs:/shots/bring-in.mjs:ro" -v "$PWD/web:/web:ro" \
  ${cache:+-v "$cache:/cache:ro"} "mcr.microsoft.com/playwright:v1.63.0-noble" \
  sh -c "for f in /web/js/*.js; do node --check \"\$f\" || exit 2; done && mkdir -p /tmp/s && cp /shots/bring-in.mjs /tmp/s/ && cd /tmp/s && ln -s /cache/node_modules node_modules && node bring-in.mjs" || status=$?
cp "$work"/out/*.png "$OUT"/ 2>/dev/null || true
grep -iE "error|traceback" "$work/server.log" | tail -20 || true
echo "Written to $OUT (server log: $work/server.log)"
exit "${status:-0}"
