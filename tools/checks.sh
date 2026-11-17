#!/usr/bin/env bash
# The code and writing checks, run in one small image (tools/checks/Dockerfile) so they are the same here and on GitHub.
#
#   tools/checks.sh               every quick check, in seconds: Ruff, Biome, Vale, typos, actionlint and zizmor
#   tools/checks.sh --file PATH   only the checks that fit one file (the Claude Code hooks use this after each edit)
#   tools/checks.sh --coverage    the unit tests under coverage.py; fails below the floor in .coveragerc
#
# What each one checks:
#   Ruff        likely bugs in the Python (ruff.toml): unused names, undefined names, mistakes in loops and tests
#   Biome       likely bugs in the JavaScript and CSS (biome.jsonc)
#   Vale        the writing rules (tools/checks/vale): no em dashes, no contractions, British spelling, no Title Case
#   typos       misspellings in code and text (_typos.toml)
#   actionlint  mistakes in the GitHub workflows
#   zizmor      security in the GitHub workflows: pinned actions, no stored credentials
#
# The image is built the first time, and again when its Dockerfile changes. Each run has no network, reads the
# checkout without changing it, and is capped like every other container here (3 GB, 4 processors).
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

IMAGE="starboard-checks:$(sha256sum tools/checks/Dockerfile | cut -c1-12)"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building the checks image (once, about a minute)."
  docker build -q -t "$IMAGE" tools/checks >/dev/null || { echo "The checks image did not build."; exit 1; }
fi

run() {  # run <command...>: one command in the checks image, with the checkout read only
  docker run --rm --network none --memory 3g --memory-swap 3g --cpus 4 -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$PWD:/src:ro" -w /src "$IMAGE" "$@"
}

WORDS=(CHANGELOG.md docs web)  # where Vale reads: the release notes, the help, the other docs and the pages
VALE=(vale --config tools/checks/vale/vale.ini --output line)

case "${1:-}" in
  --file)
    f="${2:-}"
    f="${f#"$PWD"/}"
    [ -n "$f" ] && [ -f "$f" ] || exit 0  # gone, or outside this checkout: nothing to check
    case "$f" in
      *.py) run sh -c 'ruff check --no-cache --quiet "$1" && typos --format brief "$1"' - "$f" ;;
      *.js | *.css) run sh -c 'biome lint --error-on-warnings --no-errors-on-unmatched --log-level=none "$1" && typos --format brief "$1"' - "$f" ;;
      *.md | *.html)
        case "$f" in
          CHANGELOG.md | docs/* | web/*) run sh -c 'vale --config tools/checks/vale/vale.ini --output line "$1" && typos --format brief "$1"' - "$f" ;;
          *) run typos --format brief "$f" ;;
        esac ;;
      .github/workflows/*.yml | .github/dependabot.yml)
        run sh -c 'actionlint && zizmor --offline --quiet --format plain .github' ;;
      *) run typos --format brief "$f" ;;
    esac
    exit $?
    ;;
  --coverage)
    # The unit tests run on this computer's own Python, as they always do (some need its tar, apt or dnf). coverage.py
    # comes from its pure-Python wheel, fetched once through the checks image into a cache folder.
    COV="${XDG_CACHE_HOME:-$HOME/.cache}/starboard-checks/coverage-7.17.3"
    if [ ! -d "$COV/coverage" ]; then
      mkdir -p "$COV"
      docker run --rm --memory 1g -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$COV:/out" "$IMAGE" \
        pip install --quiet --no-deps --no-compile --target /out --implementation py --only-binary=:all: coverage==7.17.3 \
        || { echo "coverage.py could not be fetched."; exit 1; }
    fi
    export PYTHONPATH="$COV${PYTHONPATH:+:$PYTHONPATH}" COVERAGE_FILE="${TMPDIR:-/tmp}/starboard-coverage-$$"
    python3 -m coverage run -m unittest discover -s tests && python3 -m coverage report
    code=$?
    rm -f "$COVERAGE_FILE"
    exit $code
    ;;
  "" ) ;;
  *) sed -n '2,6p' "$0"; exit 2 ;;
esac

failed=()
check() {  # check <name> <command...>
  local name="$1"; shift
  if out=$(run "$@" 2>&1); then
    echo "PASS $name"
  else
    echo "FAIL $name"
    printf '%s\n' "$out" | sed 's/^/     /'
    failed+=("$name")
  fi
}
check "Ruff (Python)" ruff check --no-cache .
check "Biome (JavaScript and CSS)" biome lint --error-on-warnings .
check "Vale (writing rules)" "${VALE[@]}" "${WORDS[@]}"
check "typos (spelling)" typos --format brief
check "actionlint (workflows)" actionlint
check "zizmor (workflow security)" zizmor --offline --format plain .github

if [ ${#failed[@]} -gt 0 ]; then
  echo "${#failed[@]} failed: ${failed[*]}"
  exit 1
fi
echo "Every code and writing check passed."
