#!/usr/bin/env bash
# Update Starboard to the newest release:  ./update.sh
#
#   --check          Only say whether an update is available
#   --to v0.2.0      Install a particular release (also how you go back to an older one)
#   --main           Follow the main branch instead of releases (for testing)
#
# Before updating it backs up ./data to ./backups. If the new version does not start, it goes back to the
# version you had and restores the backup.
set -euo pipefail

umask 022  # files checked out below must be readable inside the container
# Run from a copy: git checkout replaces this file while it runs, and bash reads scripts as it goes.
if [ -z "${STARBOARD_UPDATE_DIR:-}" ]; then
  copy="$(mktemp)"
  cp "$0" "$copy"
  STARBOARD_UPDATE_DIR="$(dirname "$(readlink -f "$0")")" exec bash "$copy" "$@"
fi
trap 'rm -f "$0"' EXIT
cd "$STARBOARD_UPDATE_DIR"
TARGET=""
CHECK=0
CHANNEL=release

while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=1 ;;
    --to) TARGET="${2:?--to needs a version, for example v0.2.0}"; shift ;;
    --main) CHANNEL=main ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\n== %s\n' "$*"; }
fail() { printf 'Stopped: %s\n' "$*" >&2; exit 1; }

[ -d .git ] || fail "this folder is not a git clone of Starboard"
[ -f .env ] || fail "no .env here. Run ./install.sh first"
MODE="$(sed -n 's/^STARBOARD_MODE=//p' .env)"
PORT="$(sed -n 's/^STARBOARD_PORT=//p' .env)"
MODE="${MODE:-docker}"
PORT="${PORT:-8095}"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  fail "files in this folder have been changed. Keep your changes elsewhere, then run: git checkout -- ."
fi

say "Fetching releases"
git fetch --quiet --tags --prune origin
CURRENT="$(git rev-parse HEAD)"
CURRENT_NAME="$(git describe --tags --always)"

if [ -n "$TARGET" ]; then
  git rev-parse -q --verify "refs/tags/$TARGET" >/dev/null || fail "there is no release called $TARGET"
  WANT="$(git rev-parse "refs/tags/$TARGET^{commit}")"
  WANT_NAME="$TARGET"
elif [ "$CHANNEL" = main ]; then
  WANT="$(git rev-parse origin/main)"
  WANT_NAME="main ($(git rev-parse --short origin/main))"
else
  WANT_NAME="$(git tag -l 'v[0-9]*' --sort=-v:refname | head -n 1)"
  [ -n "$WANT_NAME" ] || fail "no releases yet. Use --main to follow the main branch"
  WANT="$(git rev-parse "refs/tags/$WANT_NAME^{commit}")"
fi

echo "You have:  $CURRENT_NAME"
echo "Available: $WANT_NAME"
if [ "$WANT" = "$CURRENT" ]; then
  echo "Already up to date."
  exit 0
fi
if [ "$CHECK" = 1 ]; then
  echo "Run ./update.sh to install it."
  exit 0
fi

if git merge-base --is-ancestor "$CURRENT" "$WANT" 2>/dev/null; then
  say "What changed"
  # -n, not | head: head stops reading early, and with pipefail git's broken pipe would stop the update.
  git log --oneline --no-decorate -n 30 "$CURRENT..$WANT"
  more=$(( $(git rev-list --count "$CURRENT..$WANT") - 30 ))
  [ "$more" -le 0 ] || echo "... and $more more. The release notes list them in plain words."
fi

restart() {
  if [ "$MODE" = docker ]; then
    docker compose up -d --build
  else
    systemctl --user restart starboard.service
  fi
}

healthy() {
  for _ in $(seq 1 30); do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/healthz', timeout=2)" 2>/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

say "Backing up your settings"
mkdir -p backups
chmod 700 backups
BACKUP="backups/starboard-data-$(date +%Y-%m-%d-%H%M%S)-$(git rev-parse --short HEAD).tar.gz"
(umask 077 && tar -czf "$BACKUP" data)  # private backup; the code files below must stay readable
echo "Saved $BACKUP"
# DASH-109: keep the copies of the last versions only (Settings, Updates, Restore: 5, 10 or 20; 5 if unset). These are
# update.sh's own rolling copies, one per update, so the older ones are removed rather than kept elsewhere.
KEEP_COPIES="$(python3 -I -c 'import json, sys
try:
    n = int(json.load(open(sys.argv[1])).get("backup_keep_versions", 5))
except Exception:
    n = 5
print(n if n in (5, 10, 20) else 5)' data/config.json 2>/dev/null || echo 5)"
{ ls -1t backups/starboard-data-*.tar.gz 2>/dev/null || true; } | tail -n +$((KEEP_COPIES + 1)) | while read -r old; do
  if [ "$old" != "$BACKUP" ]; then rm -f -- "$old"; echo "Removed the older copy $old"; fi
done

say "Installing $WANT_NAME"
git -c advice.detachedHead=false checkout --quiet "$WANT"
restart

if healthy; then
  # The set-up helper (DASH-299), from the version just installed: this copy of update.sh may be older.
  if [ -x tools/install-starter.sh ]; then tools/install-starter.sh || true; fi
  say "Updated to $WANT_NAME"
  exit 0
fi

say "The new version did not start. Going back to $CURRENT_NAME"
git -c advice.detachedHead=false checkout --quiet "$CURRENT"
rm -rf data.failed-update
mv data data.failed-update
tar -xzf "$BACKUP"
restart
if healthy; then
  echo "Back on $CURRENT_NAME with your settings restored. The failed version's data is in data.failed-update."
else
  echo "Starboard is still not starting. See: docker compose logs starboard (or journalctl --user -u starboard)"
fi
exit 1
