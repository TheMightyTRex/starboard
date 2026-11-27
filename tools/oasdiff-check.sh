#!/usr/bin/env bash
# Public API changes that break an outside tool fail here (DASH-603). The baseline is the last release: the starboard/openapi.json
# of the newest v* tag. oasdiff (https://github.com/oasdiff/oasdiff) lists what changed in a way that could break a caller: a
# removed route, a removed or retyped answer field, a new required input, a stricter scope. Adding is fine. A route that was
# deprecated with a sunset date, and whose notice has run out, may go (the policy in docs/help/developers/compatibility-promise.md).
#
#   bash tools/oasdiff-check.sh          # needs oasdiff on the path (CI installs a pinned copy); it is never installed for you
#   BASE=v0.31.0 bash tools/oasdiff-check.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v oasdiff >/dev/null 2>&1; then
  echo "Not run: oasdiff is not installed here. CI runs it on every change." >&2
  [ "${OASDIFF:-}" = "required" ] && exit 1
  exit 0
fi
base="${BASE:-$(git describe --tags --abbrev=0 --match 'v*' 2>/dev/null || true)}"
if [ -z "$base" ]; then echo "Not run: no release tag to compare with." >&2; [ "${OASDIFF:-}" = "required" ] && exit 1; exit 0; fi
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
git show "$base:starboard/openapi.json" > "$work/base.json"
echo "Comparing starboard/openapi.json with the one in $base"
oasdiff breaking "$work/base.json" starboard/openapi.json --fail-on ERR
echo "No breaking change to the public API since $base."
