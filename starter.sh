#!/usr/bin/env bash
# Starboard's set-up helper (owner, 10 November 2026: nothing to configure outside Starboard). A small background
# service, installed by ./install.sh (deploy/starboard-starter.service), that runs as your user, never as root. It does
# for the browser what the Run first window used to do while it stayed open:
#   - Start the apps: Starboard leaves data/stack/start-request; this runs ./install.sh --start-apps and leaves
#     data/stack/start-result.json.
#   - Make the change now: Starboard leaves data/stack/host-request (after the Starboard password); this applies the
#     set-up's answers in data/setup-host.json with ./install.sh, writing each step to data/stack/host-progress.json
#     and the output to data/stack/host.log, which the browser shows.
# It touches data/starter every few seconds, so Starboard knows it is there. It runs only the installer, with only the
# set-up's fixed answers (each folder checked first), and cannot use sudo: a change that needs the server's password
# (disk health) is left for the command the browser shows.
set -uo pipefail
cd "$(dirname "$0")" || exit 1
# Started before this user joined the docker group (the installer had just added Docker): carry on within it.
if command -v docker >/dev/null && ! docker info >/dev/null 2>&1 && [ -z "${STARBOARD_REGROUPED:-}" ] \
   && id -nG "$(id -un)" | tr ' ' '\n' | grep -qx docker && command -v sg >/dev/null; then
  export STARBOARD_REGROUPED=1
  exec sg docker -c "$(printf '%q' "$PWD/starter.sh")"
fi
mkdir -p data/stack
umask 077

# The same folder check as Run first's: a folder Starboard may use for media or Live TV, never a system folder.
safe_folder() {
  local f="${1%/}"
  [[ "$f" =~ ^/[A-Za-z0-9._/-]{1,250}$ ]] || return 1
  case "$f/" in */../*|*//*) return 1 ;; esac
  case "$f" in /home|/var|/var/lib|/opt|/srv|/mnt|/media|/tmp) return 1 ;; esac
  [[ "$f" =~ ^/home/[^/]+$ ]] && return 1
  case "$f/" in /bin/*|/boot/*|/dev/*|/etc/*|/lib/*|/proc/*|/root/*|/run/*|/sbin/*|/sys/*|/usr/*|/var/spool/*) return 1 ;; esac
  return 0
}

# progress "state" "name" [n] [of]: one line for the browser's pop-up, written whole.
progress() {
  printf '{"state": "%s", "n": %s, "of": %s, "name": "%s"}\n' "$1" "${3:-1}" "${4:-1}" "${2//\"/}" > data/stack/host-progress.json.new \
    && mv -f data/stack/host-progress.json.new data/stack/host-progress.json
}

start_apps() {
  local req status=0
  req="$(head -c 40 data/stack/start-request | tr -cd '0-9.')"
  rm -f data/stack/start-request
  STARBOARD_FROM_HELPER=1 STARTER_RUN=1 ./install.sh --start-apps > data/stack/start.log 2>&1 < /dev/null &
  local job=$!
  while kill -0 "$job" 2>/dev/null; do : > data/starter; sleep 3; done
  wait "$job" || status=$?
  python3 -I -c 'import json, sys
log = open(sys.argv[3], errors="replace").read()[-6000:]
json.dump({"request": sys.argv[1], "ok": sys.argv[2] == "0", "log": log}, open(sys.argv[4] + ".new", "w"))' \
    "$req" "$status" data/stack/start.log data/stack/start-result.json && mv -f data/stack/start-result.json.new data/stack/start-result.json
}

host_change() {
  local args=() apply=() later=() i value folder status=0
  rm -f data/stack/host-request
  : > data/stack/host.log
  progress running "Checking the set-up's answers" 0 1
  if [ ! -s data/setup-host.json ] || [ -L data/setup-host.json ]; then
    progress finished "Nothing to change"; return 0
  fi
  mapfile -t args < <(python3 -I -c 'import json,sys; [print(a) for a in json.load(open(sys.argv[1]))["args"] if isinstance(a, str) and "\n" not in a]' data/setup-host.json 2>/dev/null)
  for (( i = 0; i < ${#args[@]}; i++ )); do
    value="${args[$((i + 1))]:-}"
    case "${args[$i]}" in
      --disk-health)
        if sudo -n true 2>/dev/null; then apply+=(--disk-health); else later+=(--disk-health); fi ;;
      --disk|--livetv-folder)
        folder="$value"; [ "${args[$i]}" = --disk ] && folder="${value#Media=}"
        if [ "${args[$i]}" = --disk ] && [ "${value:0:6}" != "Media=" ]; then folder=""; fi
        if safe_folder "$folder" && [ -d "$folder" ]; then apply+=("${args[$i]}" "$value")
        else echo "Left out: ${args[$i]} $value (not a folder Starboard uses yet)" >> data/stack/host.log; fi
        i=$(( i + 1 )) ;;
      *) echo "Left out: ${args[$i]}, which the set-up never asks for." >> data/stack/host.log; apply=(); later=(); break ;;
    esac
  done
  if [ ${#apply[@]} -gt 0 ]; then
    echo "Applying the set-up's answers: ./install.sh ${apply[*]}" >> data/stack/host.log
    STARBOARD_FROM_HELPER=1 STARBOARD_PROGRESS="$PWD/data/stack/host-progress.json" ./install.sh --yes --plain "${apply[@]}" >> data/stack/host.log 2>&1 < /dev/null &
    local job=$!
    while kill -0 "$job" 2>/dev/null; do : > data/starter; sleep 2; done
    wait "$job" || status=$?
  fi
  if [ "$status" != 0 ]; then
    progress failed "Stopped"
  elif [ ${#later[@]} -gt 0 ]; then
    # Saved for the command the browser shows: the part that needs the server's password.
    python3 -I -c 'import json,sys; json.dump({"args": sys.argv[1:]}, open("data/setup-host.json", "w"))' "${later[@]}"
    echo "Needs the server's password: ./install.sh ${later[*]}" >> data/stack/host.log
    progress needs-password "Disk health needs the server's password"
  else
    rm -f data/setup-host.json
    progress finished "Done"
  fi
}

# Keys: Starboard asks for the API keys of apps it found (data/stack/keys-request); this reads each from the app's own
# files through Docker, with Starboard's own reader, and answers in data/stack/keys-found.json, which Starboard
# deletes once it has saved them.
read_keys() {
  local request=data/stack/keys-request
  mv -f "$request" "$request.reading" 2>/dev/null || return 0
  python3 -c 'import json, sys
sys.path.insert(0, ".")
from starboard import discovery
asked = json.load(open(sys.argv[1]))
keys = {}
for app in asked.get("apps", [])[:40]:
    key, name = str(app.get("key", "")), str(app.get("container", ""))
    value = discovery.read_key(key, name)
    if value:
        keys[f"{key}|{name}"] = value
json.dump({"request": asked.get("request"), "keys": keys}, open(sys.argv[2] + ".new", "w"))' "$request.reading" data/stack/keys-found.json 2>> data/stack/keys.log \
    && mv -f data/stack/keys-found.json.new data/stack/keys-found.json
  rm -f "$request.reading"
}

# Started again while a change was running (a restart, a reboot): that change did not finish, so say so rather than
# leave the browser waiting for good (VM test N1).
if grep -q '"state": "running"' data/stack/host-progress.json 2>/dev/null; then
  progress failed "Stopped part-way: select Make the change now again"
fi

while :; do
  : > data/starter
  if [ -f data/stack/keys-request ] && [ ! -L data/stack/keys-request ]; then read_keys; fi
  if [ -f data/stack/start-request ] && [ ! -L data/stack/start-request ]; then start_apps; fi
  if [ -f data/stack/host-request ] && [ ! -L data/stack/host-request ]; then host_change; fi
  sleep 3
done
