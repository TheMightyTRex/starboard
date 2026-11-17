#!/usr/bin/env bash
# Update Starboard to the newest release:  ./update.sh
#
#   --check          Only say whether an update is available
#   --to v0.2.0      Install a particular release (also how you go back to an older one)
#   --main           Follow the main branch instead of releases (for testing). An install made with
#                    ./install.sh --main follows it without this (STARBOARD_CHANNEL in .env, DASH-416)
#
# Before updating it backs up ./data to ./backups, except each plug-in's own data folder, which belongs to the
# plug-in's user and stays where it is. If the new version does not start, it goes back to the version you had and
# restores the backup. When going forward it hands over to the new version's own update.sh first (DASH-429), so a fix
# to this file takes effect in the update that brings it.
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
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
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
# DASH-416: an install made with ./install.sh --main follows main unless --to names a release.
if [ "$CHANNEL" = release ] && [ -z "$TARGET" ] && [ "$(sed -n 's/^STARBOARD_CHANNEL=//p' .env | tail -n 1)" = main ]; then CHANNEL=main; fi
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
  WANT_NAME="$(git tag -l 'v[0-9]*' --sort=-v:refname | { grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true; } | head -n 1)"  # never a test build
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

# DASH-429: the update runs with the new version's own update.sh, so a fix to this file takes effect in the update that
# brings it, not one update later. Only going forward: going back keeps this copy, as an older update.sh may lack a
# fix this one has (such as leaving the plug-ins' own data out of the backup). STARBOARD_UPDATE_HANDED stops a loop:
# the new copy never hands over again, even when it finds yet another version.
if [ -z "${STARBOARD_UPDATE_HANDED:-}" ] && git merge-base --is-ancestor "$CURRENT" "$WANT" 2>/dev/null; then
  newer_copy="$(mktemp)"
  if git show "$WANT:update.sh" > "$newer_copy" 2>/dev/null && [ -s "$newer_copy" ] && ! cmp -s "$newer_copy" "$0"; then
    say "Using the update steps from $WANT_NAME"
    # The same version, pinned: a release by its tag; the main branch is followed again, as asked.
    if [ "$CHANNEL" = main ] && [ -z "$TARGET" ]; then set -- --main; else set -- --to "$WANT_NAME"; fi
    rm -f "$0"  # this temporary copy: bash keeps it open while it runs, and exec leaves no trap to remove it
    STARBOARD_UPDATE_HANDED=1 STARBOARD_UPDATE_DIR="$STARBOARD_UPDATE_DIR" exec bash "$newer_copy" "$@"
  fi
  rm -f "$newer_copy"
fi

if git merge-base --is-ancestor "$CURRENT" "$WANT" 2>/dev/null; then
  say "What changed"
  # -n, not | head: head stops reading early, and with pipefail git's broken pipe would stop the update.
  git log --oneline --no-decorate -n 30 "$CURRENT..$WANT"
  more=$(( $(git rev-list --count "$CURRENT..$WANT") - 30 ))
  [ "$more" -le 0 ] || echo "... and $more more. The release notes list them in plain words."
fi

# Each step starts with a "== " line: Settings, Updates reads them to show the update's progress (DASH-417).
restart() {  # restart <version>
  if [ "$MODE" = docker ]; then
    say "Building $1"
    docker compose build
    say "Restarting Starboard"
    docker compose up -d
  else
    say "Restarting Starboard"
    systemctl --user restart starboard.service
  fi
}

answers() {  # one look at Starboard's health page; wget where there is no python3 (the page's updater, DASH-417)
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/healthz', timeout=2)" 2>/dev/null
  else
    wget -q -T 2 -O /dev/null "http://127.0.0.1:$PORT/healthz" 2>/dev/null
  fi
}

healthy() {
  say "Checking that Starboard answers"
  for _ in $(seq 1 30); do
    if answers; then
      return 0
    fi
    sleep 2
  done
  return 1
}

# update-data-functions-begin (tests/test_update_backup.py runs these two on their own)
# Each plug-in's own data folder (data/plugins/<id>/data) belongs to the plug-in's own user, so Starboard's user cannot
# read it and tar would stop the update. Those folders are left out of this backup; the plug-ins' settings and
# manifests are in it. An update does not touch them, and going back leaves them with their plug-in.
# The page's update log (data/self-update.log, written as self-update.log.new and renamed after every line) changes
# while this runs, so tar could list the .new file and find it gone a moment later ("No such file or directory", exit
# 2), which stopped the update from the page on 16 November 2026. The log is this update's own record, not a setting,
# so it is left out, and so is every half-written .tmp or .new file (Starboard keeps running during the backup and
# writes its settings the same way: a .tmp file, then a rename).
# Starboard's files can still change while GNU tar reads the folder ("file changed as we read it"); GNU tar then ends
# with 1, which means the archive is whole and some file changed, so that one is accepted. The page's updater (DASH-417)
# has BusyBox tar, which knows no --warning options and ends with 1 for any error, so there only 0 is accepted. Either
# way the backup must exist and read back whole before anything is changed: a missing backup left going back with
# nothing to restore (found by the update test, 16 November 2026).
backup_data() {  # backup_data <file>
  local code=0 gnu=0
  local opts=(--exclude='data/plugins/*/data' --exclude='data/self-update.log' --exclude='*.tmp' --exclude='*.new')
  if tar --version 2>/dev/null | grep -q 'GNU tar'; then
    gnu=1
    opts=(--warning=no-file-changed --warning=no-file-removed "${opts[@]}")
  fi
  local tries=1
  while :; do
    code=0
    (umask 077 && tar -czf "$1" "${opts[@]}" data) || code=$?  # private backup
    if [ "$gnu" = 1 ]; then [ "$code" -le 1 ] && break; else [ "$code" -eq 0 ] && break; fi
    # BusyBox tar (in the page's update helper) looks each file up before its --exclude list, so a file renamed away
    # while it reads the folder stops it even when it is left out. Such a race passes on the next try (17 November
    # 2026: Update now to 0.20.1 stopped on data/self-update.log.new).
    [ "$tries" -lt 3 ] || return 1
    echo "A file changed while it was backed up; trying again ($tries of 3)." >&2
    tries=$((tries + 1))
    sleep 1
  done
  [ -s "$1" ] && tar -tzf "$1" >/dev/null || { echo "The backup $1 could not be read back."; return 1; }
}

restore_data() {  # restore_data <file>: data goes to data.failed-update, the backup comes back, plug-ins keep their data
  rm -rf data.failed-update
  mv data data.failed-update
  tar -xzf "$1"
  local old id
  for old in data.failed-update/plugins/*/data; do
    [ -d "$old" ] || continue
    id="$(basename "$(dirname "$old")")"
    mkdir -p data/plugins
    # The data folder cannot be moved on its own (its owner is the plug-in's user), so its plug-in's folder, which is
    # Starboard's, moves back whole, and the backup's copies of the plug-in's own files go over it.
    if [ -d "data/plugins/$id" ]; then
      rm -rf "data/.restore-$id"
      mv "data/plugins/$id" "data/.restore-$id"
      mv "data.failed-update/plugins/$id" "data/plugins/$id"
      cp -a "data/.restore-$id/." "data/plugins/$id/"
      rm -rf "data/.restore-$id"
    else
      mv "data.failed-update/plugins/$id" "data/plugins/$id"
    fi
  done
}
# update-data-functions-end

say "Backing up your settings"
mkdir -p backups
chmod 700 backups
BACKUP="backups/starboard-data-$(date +%Y-%m-%d-%H%M%S)-$(git rev-parse --short HEAD).tar.gz"
if ! backup_err="$(backup_data "$BACKUP" 2>&1)"; then
  rm -f -- "$BACKUP"
  printf '%s\n' "$backup_err"
  echo "Stopped: your settings could not be backed up, so nothing was changed. $(printf '%s\n' "$backup_err" | grep -m1 -v 'error exit delayed' || true)"
  exit 1
fi
echo "Saved $BACKUP (the plug-ins' own data folders are not in it: they stay where they are)"
# DASH-109: keep the copies of the last versions only (Settings, Updates, Restore: 5, 10 or 20; 5 if unset). These are
# update.sh's own rolling copies, one per update, so the older ones are removed rather than kept elsewhere.
if command -v python3 >/dev/null 2>&1; then
  KEEP_COPIES="$(python3 -I -c 'import json, sys
try:
    n = int(json.load(open(sys.argv[1])).get("backup_keep_versions", 5))
except Exception:
    n = 5
print(n if n in (5, 10, 20) else 5)' data/config.json 2>/dev/null || echo 5)"
else  # the page's updater has no python3 (DASH-417): the same number, read with sed
  KEEP_COPIES="$(sed -n 's/.*"backup_keep_versions": *\([0-9]*\).*/\1/p' data/config.json 2>/dev/null || true)"
  KEEP_COPIES="${KEEP_COPIES%%$'\n'*}"
  case "$KEEP_COPIES" in 5|10|20) ;; *) KEEP_COPIES=5 ;; esac
fi
{ ls -1t backups/starboard-data-*.tar.gz 2>/dev/null || true; } | tail -n +$((KEEP_COPIES + 1)) | while read -r old; do
  if [ "$old" != "$BACKUP" ]; then rm -f -- "$old"; echo "Removed the older copy $old"; fi
done

say "Installing $WANT_NAME"
git -c advice.detachedHead=false checkout --quiet "$WANT"
restart "$WANT_NAME"

if healthy; then
  # The set-up helper (DASH-299), from the version just installed: this copy of update.sh may be older.
  if [ -x tools/install-starter.sh ]; then tools/install-starter.sh || true; fi
  say "Updated to $WANT_NAME"
  exit 0
fi

say "The new version did not start. Going back to $CURRENT_NAME"
git -c advice.detachedHead=false checkout --quiet "$CURRENT"
restore_data "$BACKUP"
restart "$CURRENT_NAME"
if healthy; then
  echo "Back on $CURRENT_NAME with your settings restored. The failed version's data is in data.failed-update."
else
  echo "Starboard is still not starting. For the reason, run: docker compose logs starboard (or journalctl --user -u starboard)"
fi
exit 1
