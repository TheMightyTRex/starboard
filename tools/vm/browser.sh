#!/usr/bin/env bash
# The browser route on a test machine: reads the address the stand-in browser was given (~/opened-urls in the
# machine), then runs tools/vm/browser_drive.mjs in the Playwright image against the machine's forwarded port.
#   tools/vm/browser.sh OUT_DIR [ALL_APPS=1] [WIDTH=1280]
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT="$(realpath -m "$1")"; mkdir -p "$OUT"
DIR="${STARBOARD_VM_DIR:-/mnt/pool/build-cache/starboard-vm}"
SSH_PORT="${VM_SSH_PORT:-2222}"; WEB_PORT="${VM_WEB_PORT:-18095}"
PLAYWRIGHT="1.63.0"
url="$(ssh -q -i "$DIR/id_ed25519" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null tester@127.0.0.1 'tail -n 1 ~/opened-urls 2>/dev/null' || true)"
[ -n "$url" ] || { echo "The stand-in browser was not given an address" >&2; exit 1; }
start="/${url#*://*/}"
echo "The browser was asked to open: ${url%%#*}#… (the code is not printed)"
docker run --rm --network host -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e BASE="http://127.0.0.1:$WEB_PORT" -e START="$start" -e OUT=/out -e ALL_APPS="${ALL_APPS:-1}" -e WIDTH="${WIDTH:-1280}" \
  -v "$OUT:/out" -v "$PWD/tools/vm/browser_drive.mjs:/j/browser_drive.mjs:ro" \
  "mcr.microsoft.com/playwright:v$PLAYWRIGHT-noble" \
  sh -c "mkdir -p /tmp/j && cp /j/browser_drive.mjs /tmp/j/ && cd /tmp/j && npm init -y >/dev/null && npm i --silent playwright@$PLAYWRIGHT >/dev/null && node browser_drive.mjs"
