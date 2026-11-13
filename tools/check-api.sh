#!/usr/bin/env bash
# The API and plug-in checks in one command (DASH-281). Run it after every change, before a merge and before a
# release; a change that breaks one is fixed, or becomes a new API version with a deprecation note.
#
#   bash tools/check-api.sh
#
# 1. starboard/openapi.json is what tools/make_openapi.py writes from the route table (nothing undescribed).
# 2. docs/help/developers/api-reference.md is what tools/make_api_reference.py writes from that description.
# 3. The contract tests: every /api/v1 route against its description, with its scope, right and errors.
# 4. The plug-in tests: manifests, permissions and key scopes, cards, the life cycle and the tester.
# 5. The example plug-ins' smoke test, from the starboard-plugins repository, against this copy of Starboard.
#    It needs Docker and that repository (STARBOARD_PLUGINS, by default ../starboard-plugins or
#    ~/src/starboard-plugins). Without them it says it was not run; SMOKE=required makes that a failure.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
cd "$here"

step() { printf '\n== %s\n' "$1"; }

step "API description is up to date"
python3 tools/make_openapi.py --check
step "API reference page is up to date"
python3 tools/make_api_reference.py --check
step "API contract tests"
python3 -m unittest tests.test_api_v1
step "Plug-in tests"
python3 -m unittest tests.test_plugins tests.test_plugins_admin tests.test_plugin_cards tests.test_plugin_life \
  tests.test_plugin_custom tests.test_plugin_files tests.test_plugin_groups tests.test_plugin_catalogues

step "Example plug-ins smoke test"
plugins="${STARBOARD_PLUGINS:-}"
if [ -z "$plugins" ]; then
  for d in "$here/../starboard-plugins" "$HOME/src/starboard-plugins"; do
    if [ -f "$d/tools/smoke_test.py" ]; then plugins="$d"; break; fi
  done
fi
if [ -n "$plugins" ] && [ -f "$plugins/tools/smoke_test.py" ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  (cd "$plugins" && STARBOARD_SRC="$here" python3 tools/smoke_test.py)
elif [ "${SMOKE:-}" = "required" ]; then
  echo "The smoke test could not run: it needs Docker and the starboard-plugins repository (STARBOARD_PLUGINS)." >&2
  exit 1
else
  echo "Not run: it needs Docker and the starboard-plugins repository (set STARBOARD_PLUGINS). Run it before a release."
fi

printf '\nThe API and plug-in checks passed.\n'
