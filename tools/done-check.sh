#!/usr/bin/env bash
# The done gate (DASH-617): one command that runs every check a change needs before anyone says it is done.
#
#   /mnt/pool/build-cache/heavy-run-wt2 tools/done-check.sh
#
# Run it once, on the final tip of the branch, through heavy-run-wt2 (the shared slots: it starts a browser, a
# journeys run and the unit suite). It prints a table of each step, its result, its seconds and its log, and ends with
# DONE-CHECK PASSED or DONE-CHECK FAILED: <steps>. The same table is written to done-check-out/summary.md: paste it
# into the pull request. Failures already on main are listed in tools/done-check-baseline.json and do not fail it.
# The steps, the environment variables (ONLY, SKIP, FAIL_FAST, CHANGED_ONLY, FULL) and the rules are in
# tools/done_check.py.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
exec python3 tools/done_check.py "$@"
