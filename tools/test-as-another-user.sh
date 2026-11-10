#!/usr/bin/env bash
# The unit tests as GitHub runs them: a fresh copy of this checkout, as a user other than yours (uid 1001, like
# GitHub's runner), in a throwaway container. Run it before each release (suggestion of 10 November 2026: the
# ready-made image did not build for 0.15.2 to 0.15.4 because a test passed only as user 1000).
#   tools/test-as-another-user.sh
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="${TEST_IMAGE:-python:3.12-bookworm}"
docker run --rm -u 1001:1001 -e HOME=/tmp -e STARBOARD_WATCH=0 -e STARBOARD_JOBS=0 -v "$PWD:/src:ro" "$IMAGE" \
  sh -c 'cp -r /src /tmp/w && cd /tmp/w && rm -rf data && python3 -m unittest discover -s tests 2>&1 | tail -n 25'
