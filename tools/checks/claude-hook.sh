#!/usr/bin/env bash
# The Claude Code hook for this repository (.claude/settings.json): after Claude edits or writes a file, the checks
# that fit that one file (tools/checks.sh --file), in about 2 seconds. A failure exits with 2, which Claude Code shows
# to Claude, so it fixes the file straight away. The full checks run weekly on GitHub instead (quality.yml).
set -uo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
input="$(cat)"

case "${1:-}" in
  edited)
    file="$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); i=d.get("tool_input") or {}; print(i.get("file_path") or "")' 2>/dev/null)"
    case "$file" in
      "$root"/*) ;;
      *) exit 0 ;;  # a file outside this checkout
    esac
    out="$(bash "$root/tools/checks.sh" --file "$file" 2>&1)" && exit 0
    printf 'The code and writing checks found problems in %s. Fix them:\n%s\n' "${file#"$root"/}" "$out" >&2
    exit 2
    ;;
  *)
    echo "Use: claude-hook.sh edited (reads the hook input on stdin)" >&2
    exit 1
    ;;
esac
