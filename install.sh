#!/usr/bin/env bash
# Install Starboard, or change what it can access. Run from the folder you cloned:  ./install.sh
#
# It says what it is going to do before each step, and asks before giving Starboard any access to this
# computer. Run it again at any time to change your answers; your settings and password stay.
#
#   --native              Run with this computer's Python as a systemd user service, without Docker
#   --port 8095           Port to listen on
#   --local-only          Only this computer can open it (default: your home network too; change it in Settings)
#   --docker              Let Starboard check and install app updates (full control of Docker)
#   --no-docker           Take that away
#   --disk Name=/path     Show free space for a folder on System, Storage (read-only; repeat for more)
#   --no-disks            Show no folders
#   --app-use             Show processor and memory use for each app on System, Monitor (read-only)
#   --no-app-use          Take that away
#   --livetv-folder PATH  Live TV: the folder Jellyfin reads its Live TV playlists and guides from (read-write)
#   --no-livetv           Take that away
#   --disk-health         Set up Disk health reports (installs a timer with sudo; asks for your password)
#   --no-disk-health      Stop reading Disk health reports (and say how to remove the timer)
#   --pool                Set up Drive pools: the pool helper, which joins drives into one folder and looks after
#                         backup drives (installs it with sudo; asks for your password)
#   --no-pool             Stop using the pool helper (and say how to remove it)
#   --yes                 Do not ask: use the options above, and your last answers (or No) for the rest
#   --start-apps          Download and start the apps the set-up wrote in data/stack, then stop
#   --terminal            Finish set-up here in the terminal (password, apps, download hours), with no browser:
#                         for a server with no desktop. Run it again later with: python3 -m starboard.terminal_setup
#   --plain               Plain lines with no boxes, colour or redrawing in the terminal set-up, for software that
#                         reads text aloud (the same as STARBOARD_PLAIN=1)
#
# Your settings go in ./data and .env, which git ignores.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
MODE=docker
PORT=8095
NETWORK=1
ASK=1
DOCKER=""
HEALTH=""
POOL=""
APPUSE=""
LIVETV="-"
TERMINAL=0
DISKS_GIVEN=0
DISKS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --native) MODE=native ;;
    --port) PORT="${2:?--port needs a number}"; shift ;;
    --local-only) NETWORK=0 ;;
    --docker) DOCKER=1 ;;
    --no-docker) DOCKER=0 ;;
    --disk) DISKS+=("${2:?--disk needs Name=/path}"); DISKS_GIVEN=1; shift ;;
    --no-disks) DISKS=(); DISKS_GIVEN=1 ;;
    --livetv-folder) LIVETV="${2:?--livetv-folder needs a folder}"; shift ;;
    --no-livetv) LIVETV="" ;;
    --app-use) APPUSE=1 ;;
    --no-app-use) APPUSE=0 ;;
    --disk-health) HEALTH=1 ;;
    --no-disk-health) HEALTH=0 ;;
    --pool) POOL=1 ;;
    --no-pool) POOL=0 ;;
    --yes) ASK=0 ;;
    --terminal) TERMINAL=1 ;;
    --start-apps) START_APPS=1 ;;
    --plain) export STARBOARD_PLAIN=1 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -t 0 ] || ASK=0
[ "$TERMINAL" = 0 ] || [ -t 0 ] || { echo "Stopped: --terminal needs a terminal to type in" >&2; exit 2; }

# Text is written for a wide window. In a narrower one, wrap it at spaces before the edge, so no word is cut in two.
WRAP=$(( $( { tput cols || printf 80; } 2>/dev/null) - 1 )); [ "$WRAP" -ge 39 ] || WRAP=79
echo() { if [ -t 1 ] && [ "$#" = 1 ]; then printf '%s\n' "$1" | fold -s -w "$WRAP"; else builtin echo "$@"; fi; }
say() { printf '\n== %s\n' "$*"; }
fail() { if [ -t 2 ]; then printf 'Stopped: %s\n' "$*" | fold -s -w "$WRAP" >&2; else printf 'Stopped: %s\n' "$*" >&2; fi; exit 1; }
# Runs a command with its output kept out of the window (package managers write a lot). If it fails, the last
# lines are shown, so the reason is on the screen.
quietly() {
  local log rc=0
  log="$(mktemp)"
  "$@" >"$log" 2>&1 || rc=$?
  [ "$rc" = 0 ] || tail -n 8 "$log" | sed 's/^/    /'
  rm -f "$log"
  return "$rc"
}
# The apps the set-up wrote (data/stack): their folders, then Docker Compose. Starboard starts them itself only when
# it has Docker access, which is off unless the person says yes, so the installer does it: after the terminal set-up,
# or with --start-apps when the browser set-up asks the Run first window. Folders are made, and given to the apps'
# user, with Starboard's own helper image, the same way Starboard does it, so no sudo is needed.
start_apps() {
  local env=data/stack/.env file=data/stack/compose.yaml key dir top puid pgid log pid n=0 total running helper status quiet_keys
  [ -s "$file" ] && [ -s "$env" ] || { echo "There are no apps to start: the set-up has not written them."; return 0; }
  puid="$(sed -n 's/^PUID=//p' "$env" | tail -n 1)"; pgid="$(sed -n 's/^PGID=//p' "$env" | tail -n 1)"
  [[ "$puid" =~ ^[0-9]+$ ]] || puid="$(id -u)"; [[ "$pgid" =~ ^[0-9]+$ ]] || pgid="$(id -g)"
  helper="$(sed -n 's/^HELPER_IMAGE = "\(.*\)"$/\1/p' starboard/containers.py)"
  say "Starting your apps"
  dirs=()
  for key in CONFIG_DIR DATA_DIR; do
    dir="$(sed -n "s/^$key=//p" "$env" | tail -n 1)"; dir="${dir//\'/}"
    [[ "$dir" =~ ^/[A-Za-z0-9._/-]{1,250}$ ]] && [[ "$dir/" != *"/../"* ]] || { echo "The apps' folder in $env is not one Starboard can use: $dir"; return 1; }
    dirs+=("$dir")
  done
  helped() {  # helped "shell command": run as root in the helper, with each apps' folder's nearest existing parent
    local binds=() d
    for d in "${dirs[@]}"; do top="$d"; while [ ! -e "$top" ]; do top="$(dirname "$top")"; done; binds+=(-v "$top:$top"); done
    docker run --rm "${binds[@]}" --entrypoint sh "$helper" -c "$1"
  }
  # Each app's own settings folder too, before it starts: an app given a folder owned by root can stop at once
  # (Seerr does: "EACCES: permission denied, mkdir '/app/config/logs/'").
  local subs
  subs="$(grep -o '\${CONFIG_DIR}/[A-Za-z0-9._-]*' "$file" | grep -v -- '-db$' | sort -u | sed "s#^\${CONFIG_DIR}#${dirs[0]}#; s#.*#'&'#" | paste -sd' ' -)"
  # And every folder the apps use inside the media folder (data/stack/folders.txt, from Install apps): Reelix does not
  # make its library folders itself.
  local more
  more="$(grep -E '^/[A-Za-z0-9._/-]{1,250}$' data/stack/folders.txt 2>/dev/null | grep -v -- '/\.\./' | grep -F -- "${dirs[1]}/" \
    | sed "s#.*#'&'#" | paste -sd' ' - || true)"
  subs="$subs $more"
  quietly helped "mkdir -p '${dirs[0]}' '${dirs[1]}' $subs && chown $puid:$pgid '${dirs[0]}' '${dirs[1]}' $subs" \
    || { echo "Could not make the apps' folders, ${dirs[*]}."; return 1; }
  # The Starboard container can write data/stack, so the file is checked with Starboard's own rules before anything
  # starts: catalogue images only, no privileged containers or host access, folders inside the settings and media
  # folders (starboard/compose_check.py). From a terminal, a person can still choose to start what it lists.
  local problems
  problems="$(docker compose -p media-stack -f "$file" --env-file "$env" config --format json 2>/dev/null \
    | python3 -m starboard.compose_check "$env" 2>&1)" || {
    echo "The set-up file (data/stack/compose.yaml) has things Starboard did not write:"
    printf '%s\n' "$problems" | sed 's/^/  - /'
    if [ -t 0 ] && [ -z "${STARTER_RUN:-}" ]; then
      local answer
      read -r -p "Start it anyway? Only if you added these yourself. [y/N] " answer
      [[ "$answer" =~ ^[Yy] ]] || { echo "Nothing was started."; return 1; }
    else
      echo "Nothing was started. If you added these yourself, run ./install.sh --start-apps in a terminal to choose."
      return 1
    fi
  }
  # First settings files Starboard wrote (data/stack/seed/<app>/<file>, such as SABnzbd's port and folders): each
  # goes in the app's settings folder only when the app has none yet, so your own settings are never replaced.
  local seed app_dir name
  for seed in data/stack/seed/*/*; do
    [ -f "$seed" ] || continue
    app_dir="$(basename "$(dirname "$seed")")"; name="$(basename "$seed")"
    [[ "$app_dir" =~ ^[a-z0-9-]+$ ]] && [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || continue
    top="${dirs[0]}/$app_dir"
    docker run --rm -i -v "${dirs[0]}:${dirs[0]}" --entrypoint sh "$helper" -c \
      "[ -e '$top/$name' ] || { mkdir -p '$top' && cat > '$top/$name' && chmod 600 '$top/$name' && chown $puid:$pgid '$top' '$top/$name'; }" \
      < "$seed" >/dev/null 2>&1 || echo "Could not give $app_dir its first settings; it starts with its own."
  done
  # Settings, Your install moving from SABnzbd to NZBGet when Starboard has no Docker access: it cannot read
  # SABnzbd's settings itself, so they are copied for it into data/stack (only your user can read the copy), and
  # Starboard moves the Usenet servers into NZBGet, then removes the copy.
  if [ -f data/stack/want-sab-servers ]; then
    if [ -s "${dirs[0]}/sabnzbd/sabnzbd.ini" ]; then
      (umask 077; helped "cat '${dirs[0]}/sabnzbd/sabnzbd.ini'" > data/stack/sab-servers.ini) 2>/dev/null || rm -f data/stack/sab-servers.ini
    fi
    rm -f data/stack/want-sab-servers
  fi
  total="$(grep -c '^    container_name:' "$file" || true)"
  echo "Downloading $total apps and starting them. On a slow connection this can take 20 minutes or more."
  log="$(mktemp)"
  # A download that breaks off (the connection reset, a timeout) is tried again, twice, after a pause: Docker keeps
  # what it has, so each try carries on from there.
  local try
  for try in 1 2 3; do
    docker compose -p media-stack -f "$file" --env-file "$env" up -d --quiet-pull --remove-orphans >"$log" 2>&1 &
    pid=$!
    quiet_keys=""
    if [ -t 0 ] && [ -t 1 ]; then quiet_keys="$(stty -g 2>/dev/null)" && stty -echo -icanon 2>/dev/null; fi
    while kill -0 "$pid" 2>/dev/null; do
      sleep 5; n=$(( n + 5 ))
      [ -t 1 ] && printf '\r  Still working: %d min %02d s ' $(( n / 60 )) $(( n % 60 ))
    done
    if [ -n "$quiet_keys" ]; then
      while read -r -t 0.05 -n 64 _ 2>/dev/null; do :; done
      stty "$quiet_keys" 2>/dev/null
    fi
    status=0
    wait "$pid" || status=$?
    [ "$status" != 0 ] && [ "$try" -lt 3 ] && grep -qiE 'connection reset|timeout|timed out|TLS handshake|unexpected EOF|i/o timeout|no such host|temporary failure|503|502|429 Too Many' "$log" || break
    [ -t 1 ] && printf '\r%40s\r' ""
    echo "The download broke off. Trying again in 20 seconds (try $(( try + 1 )) of 3)."
    sleep 20
  done
  [ -t 1 ] && printf '\r%40s\r' ""
  date +%s > data/stack/started-at  # Starboard waits for this to finish a change made in Settings, Your install
  # Folders Docker made for the apps are owned by root: give them to the apps' user, as Starboard's helper does.
  # Not a database's folder (jellystat-db, storyarr-db): the database owns it, and changing it while the database
  # sets itself up leaves it unfinished ("no pg_hba.conf entry").
  quietly helped "for d in '${dirs[0]}'/* '${dirs[1]}'/media '${dirs[1]}'/downloads; do case \"\$d\" in *-db) continue ;; esac; [ -d \"\$d\" ] && chown $puid:$pgid \"\$d\"; done; true" || true
  if [ "$status" != 0 ]; then
    running="$(docker compose -p media-stack -f "$file" --env-file "$env" ps -q --status running 2>/dev/null | wc -l)"
    echo "$running of $total apps are running. Some did not start. The last lines Docker wrote:"
    tail -n 8 "$log" | fold -s -w $(( WRAP - 4 )) | sed 's/^/    /'
    rm -f "$log"
    echo "Fix what it says, then try again. From this folder: ./install.sh --start-apps"
    reelix_tokens  # Reelix may be running even when another app is not
    return 1
  fi
  rm -f "$log"
  reelix_tokens
  running="$(docker compose -p media-stack -f "$file" --env-file "$env" ps -q --status running 2>/dev/null | wc -l)"
  echo "$running of $total apps are running. Open Starboard to see them."
}
# Reelix's one-time set-up token and qBittorrent's first password are only in their logs, which only Docker can read:
# they go into data/stack/reelix-setup.json (only your user can read it) for Starboard's Reelix set-up, which then
# makes Reelix's admin account and gives qBittorrent a lasting password. Starboard removes the file when it is done.
reelix_tokens() {
  local note=data/stack/reelix-setup.json token="" qb="" i
  [ -s "$note" ] || return 0
  for i in $(seq 1 40); do
    token="$(docker logs reelix 2>&1 | grep -o 'setup token: [A-Za-z0-9_-]*' | tail -n 1 | awk '{print $NF}')"
    [ -n "$token" ] && break
    sleep 3
  done
  qb="$(docker logs qbittorrent 2>&1 | grep -o 'temporary password is provided for this session: [^ ]*' | tail -n 1 | awk '{print $NF}')"
  python3 -I - "$note" "$token" "$qb" <<'PY'
import json, os, sys
path, token, qb = sys.argv[1:4]
with open(path, encoding="utf-8") as f:
    info = json.load(f)
if token:
    info["token"] = token
if qb:
    info["qbittorrent_password"] = qb
fd = os.open(path + ".new", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(info, f)
os.replace(path + ".new", path)
PY
  [ -n "$token" ] && echo "Reelix is ready to be set up." || echo "Reelix has not printed its set-up token yet."
}
if [ "${START_APPS:-0}" = 1 ]; then
  start_apps
  exit $?
fi
# yes_no "Question" default: 1 for yes, 0 for no. An empty answer takes the default.
yes_no() {
  local hint answer
  if [ "$2" = 1 ]; then hint="Y/n"; else hint="y/N"; fi
  printf '%s [%s]: ' "$1" "$hint"
  read -r answer || answer=""
  case "$answer" in
    [Yy]*) return 0 ;;
    [Nn]*) return 1 ;;
    *) [ "$2" = 1 ] ;;
  esac
}
env_value() {
  if [ -f .env ]; then sed -n "s/^$1=//p" .env | tail -n 1; fi
}

[[ "$PORT" =~ ^[0-9]+$ ]] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || fail "the port must be a number from 1 to 65535"
[ "$(id -u)" -ne 0 ] || fail "run this as your normal user, not root"
command -v git >/dev/null || fail "install git first"
[ -d .git ] || fail "run this inside a git clone of Starboard, so ./update.sh can update it later"

# Each item is one line here and wraps to the window, with the lines after the first indented under it.
item() { if [ -t 1 ]; then printf '%s\n' "$1" | fold -s -w $(( WRAP > 20 ? WRAP - 5 : 15 )) | sed '1s/^/  /;2,$s/^/     /'; else printf '  %s\n' "$1"; fi; }
para() { if [ -t 1 ]; then printf '%s\n' "$1" | fold -s -w "$WRAP"; else printf '%s\n' "$1"; fi; }
echo
if [ "$ASK" = 0 ]; then
  # --yes: the person answered already (the Run first window's second run, or a script), so one line is enough.
  echo "Starboard installer, with your earlier answers (--yes)."
else
  echo "Starboard installer"
  echo
  echo "What this does, in order:"
  item "1. Checks that Docker (or, with --native, Python and systemd) is installed. It changes nothing."
  item "2. Asks what Starboard may access on this computer. Each one is optional: say no and only that part of Starboard is missing. Change your answers later by running ./install.sh again. Settings, About and updates shows what Starboard can access now."
  item "3. Writes your answers to .env and compose.access.yaml in this folder (only you can read .env)."
  item "4. Builds and starts Starboard: with Docker, \`docker compose up -d --build\`; with --native, a systemd service for your user only. Neither needs sudo. Disk health is the one step that does, and only if you say yes to it."
  echo
  para "Starboard runs as your user, in a read-only container with no extra privileges, and keeps its settings in ./data. It never sends your settings anywhere."
fi

say "Step 1: checking what is installed"
if [ "$MODE" = docker ]; then
  command -v docker >/dev/null || fail "install Docker first, or use --native"
  docker compose version >/dev/null 2>&1 || fail "install the Docker Compose plugin first, or use --native"
  echo "Docker and Docker Compose are installed."
else
  command -v python3 >/dev/null || fail "install Python 3.10 or newer first"
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || fail "Python 3.10 or newer is needed"
  command -v systemctl >/dev/null || fail "--native needs systemd"
  echo "Python and systemd are installed."
fi

NAME=""
if [ ! -f data/config.json ]; then
  # The name is asked in the set-up, beside the password, in the browser and the terminal alike.
  NAME="$(printf '%s' "${NAME:-Starboard}" | tr -d '\n\r=|&\\"' | cut -c1-60)"
fi

say "Step 2: what Starboard may access"

# A new install asks only what Starboard needs to start: the home network and Docker. Everything that depends on
# where the media goes (folders to show, Live TV, disk health) is asked in Starboard's set-up, after Storage, and
# these questions come back when you run the installer again. Drive pools are offered here when there is more
# than one extra drive, because the pool helper runs on this computer with sudo.
FIRST=0
[ -f data/config.json ] || FIRST=1
LATER=1
[ "$ASK" = 1 ] && [ "$FIRST" = 0 ] || LATER=0
# Drives besides the one the system is on.
extra_drives() {
  command -v lsblk >/dev/null || { echo 0; return; }
  lsblk -dn -o NAME,TYPE 2>/dev/null | awk '$2 == "disk" {print $1}' | while read -r d; do
    lsblk -n -o MOUNTPOINTS "/dev/$d" 2>/dev/null | grep -qxE '/|/boot(/efi)?' || echo "$d"
  done | wc -l
}

# Home network: asked on the first install only; after that it is a switch in Settings, Security.
if [ "$ASK" = 1 ] && [ ! -f data/config.json ] && [ "$NETWORK" = 1 ]; then
  echo
  echo "Home network: phones and other computers on your home network can open Starboard, with your password."
  echo "  No: only this computer can. You can change this later in Settings, Security."
  yes_no "Let your home network open Starboard?" 1 || NETWORK=0
fi

if [ -f data/config.json ] && [ "$NETWORK" = 0 ]; then
  echo
  echo "Note: --local-only applies to a new install only. Starboard is already set up, so change who can open it"
  echo "in Settings, Security, Who can open the dashboard. It takes effect at once."
fi

# Docker, for app updates.
if [ "$MODE" = docker ]; then
  if [ -z "$DOCKER" ]; then
    DOCKER="$(env_value STARBOARD_ALLOW_DOCKER)"
    DOCKER="${DOCKER:-0}"
    if [ "$ASK" = 1 ]; then
      echo
      echo "App updates: Starboard lists your containers and, when you choose Update, downloads the new image"
      echo "  and restarts the app with Docker Compose. For that it needs the Docker socket, which is full"
      echo "  control of Docker, and so of this computer."
      echo "  No: Apps, Updates says that updates are off. Nothing else changes."
      if yes_no "Give Starboard access to Docker for app updates?" "$DOCKER"; then DOCKER=1; else DOCKER=0; fi
    fi
  fi
  if [ "$DOCKER" = 1 ] && [ ! -S /var/run/docker.sock ]; then
    fail "there is no Docker socket at /var/run/docker.sock"
  fi
else
  DOCKER=0
fi

# Per-app use.
if [ -z "$APPUSE" ]; then
  APPUSE="$(env_value STARBOARD_ALLOW_APPUSE)"
  APPUSE="${APPUSE:-0}"
  if [ "$LATER" = 1 ]; then
    echo
    echo "Per-app use: System, Monitor can list each app's processor and memory use. Starboard reads two small"
    echo "  files per container from /sys/fs/cgroup, read-only, every 2 seconds while Monitor is open. With Docker"
    echo "  access it also shows the apps' names; without it, their short IDs. No: Monitor shows the whole server only."
    if yes_no "Show each app's processor and memory use?" "$APPUSE"; then APPUSE=1; else APPUSE=0; fi
  fi
fi
if [ "$APPUSE" = 1 ] && [ ! -d /sys/fs/cgroup/system.slice ]; then
  echo "This computer has no /sys/fs/cgroup/system.slice (cgroup v2 with systemd), so per-app use stays off."
  APPUSE=0
fi

# Live TV for Jellyfin.
if [ "$LIVETV" = "-" ]; then
  LIVETV="$(env_value STARBOARD_LIVETV_PATH)"
  if [ "$LATER" = 1 ]; then
    echo
    echo "Live TV for Jellyfin: Starboard can build free channel playlists and TV guides once a day (Settings,"
    echo "  Jellyfin; inactive until you activate it there). For that it needs to write in the folder Jellyfin reads its"
    echo "  Live TV files from, and nowhere else. No: the Live TV switch says it needs this folder."
    [ -n "$LIVETV" ] && echo "  Now: $LIVETV"
    if yes_no "Give Starboard a Live TV folder?" "$([ -n "$LIVETV" ] && echo 1 || echo 0)"; then
      printf '  Folder (for example /srv/jellyfin/config/iptv) [%s]: ' "$LIVETV"
      read -r answer || answer=""
      LIVETV="${answer:-$LIVETV}"
    else
      LIVETV=""
    fi
  fi
fi
if [ -n "$LIVETV" ] && [ ! -d "$LIVETV" ]; then fail "there is no folder $LIVETV"; fi
if [ -n "$LIVETV" ] && [ ! -w "$LIVETV" ]; then
  fail "you cannot write in $LIVETV; give your user that folder first (for example: sudo chown -R $(id -un) \"$LIVETV\")"
fi

# Folders for free space.
if [ "$DISKS_GIVEN" = 0 ]; then
  hand="$(env_value STARBOARD_DISKS)"
  saved="$(env_value STARBOARD_DISK_PATHS)"
  if [ -n "$hand" ] && [ -z "$saved" ]; then
    echo
    echo "Free space: you set up folders by hand (STARBOARD_DISKS), so the installer leaves them as they are."
    DISKS_GIVEN=skip
  else
    IFS=',' read -r -a DISKS <<< "$saved"
    if [ "$LATER" = 1 ]; then
      echo
      echo "Free space: System, Storage can show how full your folders or drives are. Starboard reads them"
      echo "  read-only and does not open the files. No: Storage shows no folders."
      if [ "${#DISKS[@]}" -gt 0 ]; then echo "  Now: ${DISKS[*]}"; had=1; else had=0; fi
      if yes_no "Choose folders to show?" "$had"; then
        DISKS=()
        echo "  Enter one per line as Name=/path, such as Media=/mnt/media. An empty line finishes."
        while true; do
          printf '  Folder: '
          read -r line || line=""
          [ -z "$line" ] && break
          DISKS+=("$line")
        done
      else
        DISKS=()
      fi
    fi
  fi
fi
# Values go into .env and compose.access.yaml: refuse characters that would break those files.
safe_value() { case "$1" in *[\|\&\\\"\'\$\`]*|*$'\n'*) return 1 ;; esac; return 0; }
if [ -n "$LIVETV" ] && ! safe_value "$LIVETV"; then fail "the Live TV folder's name has a character Starboard cannot use (| & \\ \" ' \$ \`)"; fi
if ! safe_value "$PWD"; then fail "this folder's path has a character Starboard cannot use (| & \\ \" ' \$ \`); move it"; fi
if [ "$DISKS_GIVEN" != skip ]; then
  for d in "${DISKS[@]+"${DISKS[@]}"}"; do
    safe_value "$d" || fail "a folder name has a character Starboard cannot use (| & \\ \" ' \$ \`): $d"
    [[ "$d" =~ ^[^=,]+=/[^,]*$ ]] || fail "write each folder as Name=/path, with no commas: $d"
    [ -d "${d#*=}" ] || fail "there is no folder ${d#*=}"
  done
fi

# Disk health.
if [ -z "$HEALTH" ]; then
  previous="$(env_value STARBOARD_ALLOW_HEALTH)"
  HEALTH="${previous:-0}"
  if [ -n "$(env_value STARBOARD_SMART_DIR)" ] && [ -z "$previous" ]; then
    echo
    echo "Disk health: you set up reports by hand (STARBOARD_SMART_DIR), so the installer leaves them as they are."
    HEALTH=skip
  elif [ "$LATER" = 1 ]; then
    echo
    echo "Disk health: a small script (deploy/starboard-smart.sh) runs smartctl as root every 30 minutes,"
    echo "  through a systemd timer, and saves each drive's health report in ./smart. Starboard reads them"
    echo "  read-only. Setting it up runs deploy/install-smart.sh with sudo, so you are asked for your"
    echo "  password. It needs smartmontools. No: System, Disk health says reports are not set up."
    if yes_no "Set up Disk health reports?" "$HEALTH"; then HEALTH=1; else HEALTH=0; fi
  fi
fi

# Drive pools (DASH-87).
if [ -z "$POOL" ]; then
  previous="$(env_value STARBOARD_ALLOW_POOL)"
  POOL="${previous:-0}"
  if [ -n "$(env_value STARBOARD_POOL_DIR)" ] && [ -z "$previous" ]; then
    echo
    echo "Drive pools: you set up the pool helper by hand (STARBOARD_POOL_DIR), so the installer leaves it as it is."
    POOL=skip
  elif [ "$ASK" = 1 ] && { [ "$FIRST" = 0 ] || [ "$(extra_drives)" -ge 2 ]; }; then
    echo
    echo "Drive pools: a pool joins several drives into one folder, /mnt/pool, and a backup drive protects it."
    echo "  The pool helper (deploy/install-pool.sh) does that work as root; Starboard only asks it, and every"
    echo "  change needs your Starboard password and is checked first. Setting it up runs sudo, so you are asked"
    echo "  for this computer's password. It needs mergerfs, rsync and gdisk (and snapraid for a parity drive)."
    echo "  No: System, Storage, Pool says the helper is not set up."
    if yes_no "Set up Drive pools?" "$POOL"; then POOL=1; else POOL=0; fi
  fi
fi

if [ "$ASK" = 1 ] && [ "$FIRST" = 1 ]; then
  echo
  echo "Where your media goes, the folders Starboard shows, Live TV and disk health come next, in Starboard's"
  echo "  set-up, once your media folder is chosen."
fi

say "Step 3: saving your answers"
[ -f .env ] || (umask 077 && cp example.env .env)
set_env() {
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
set_env STARBOARD_MODE "$MODE"
set_env STARBOARD_PORT "$PORT"
set_env STARBOARD_NETWORK "$NETWORK"
if [ -n "$NAME" ]; then set_env STARBOARD_NAME "\"$NAME\""; fi
set_env STARBOARD_UID "$(id -u)"
set_env STARBOARD_GID "$(id -g)"
set_env STARBOARD_ALLOW_DOCKER "$DOCKER"
set_env STARBOARD_ALLOW_APPUSE "$APPUSE"
set_env STARBOARD_LIVETV_PATH "$LIVETV"
if [ -n "$LIVETV" ]; then
  if [ "$MODE" = docker ]; then set_env STARBOARD_IPTV_DIR /iptv; else set_env STARBOARD_IPTV_DIR "$LIVETV"; fi
else
  set_env STARBOARD_IPTV_DIR ""
fi
if [ "$APPUSE" = 1 ]; then
  if [ "$MODE" = docker ]; then set_env STARBOARD_CGROUP /host-cgroup; else set_env STARBOARD_CGROUP /sys/fs/cgroup; fi
else
  set_env STARBOARD_CGROUP ""
fi
if [ "$HEALTH" != skip ]; then set_env STARBOARD_ALLOW_HEALTH "$HEALTH"; fi
if [ "$POOL" != skip ]; then set_env STARBOARD_ALLOW_POOL "$POOL"; fi
if ! grep -q '^STARBOARD_REPO=.\+' .env; then
  origin="$(git remote get-url origin 2>/dev/null || true)"
  repo="$(printf '%s' "$origin" | sed -nE 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#p')"
  if [ -n "$repo" ]; then set_env STARBOARD_REPO "$repo"; fi
fi
mkdir -p data backups
chmod 700 data backups

# compose.access.yaml: the mounts your answers need. Rewritten on every run.
{
  echo "# Written by ./install.sh from your answers. Run ./install.sh again to change them."
  echo "services:"
  echo "  starboard:"
  if [ "$DOCKER" = 1 ]; then
    echo "    group_add:"
    echo "      - \"$(stat -c %g /var/run/docker.sock)\"  # the group that owns the Docker socket"
  fi
  echo "    volumes:"
  echo "      - ./data:/data"
  if [ "$DOCKER" = 1 ]; then echo "      - /var/run/docker.sock:/var/run/docker.sock  # app updates"; fi
  if [ "$APPUSE" = 1 ]; then echo "      - /sys/fs/cgroup:/host-cgroup:ro  # per-app use"; fi
  if [ -n "$LIVETV" ]; then echo "      - \"$LIVETV:/iptv\"  # Live TV for Jellyfin (read-write)"; fi
  if [ "$DISKS_GIVEN" != skip ]; then
    i=0
    for d in "${DISKS[@]+"${DISKS[@]}"}"; do
      i=$((i + 1))
      echo "      - \"${d#*=}:/disks/$i:ro,rslave\"  # free space: ${d%%=*}"
    done
  fi
  if [ "$HEALTH" = 1 ]; then
    echo "      - ./smart:/smart:ro  # Disk health reports"
    echo "      - ./smart/requests:/smart/requests  # the one place Starboard writes: Read disks now"
  fi
  if [ "$POOL" = 1 ]; then
    echo "      - ./pool/status:/pool/status:ro  # Drive pools: the pool helper's answers"
    echo "      - ./pool/requests:/pool/requests  # Drive pools: the one place Starboard asks the helper"
  fi
} > compose.access.yaml
if [ "$DISKS_GIVEN" != skip ]; then
  paths=""; inside=""; i=0
  for d in "${DISKS[@]+"${DISKS[@]}"}"; do
    i=$((i + 1))
    paths="${paths:+$paths,}$d"
    # Docker sees each folder at /disks/N; the native service reads it where it is.
    if [ "$MODE" = docker ]; then target="/disks/$i"; else target="${d#*=}"; fi
    inside="${inside:+$inside,}${d%%=*}=$target"
  done
  set_env STARBOARD_DISK_PATHS "$paths"
  set_env STARBOARD_DISKS "$inside"
fi
if [ "$HEALTH" = 1 ]; then
  if [ "$MODE" = docker ]; then set_env STARBOARD_SMART_DIR /smart; else set_env STARBOARD_SMART_DIR "$PWD/smart"; fi
elif [ "$HEALTH" = 0 ]; then
  set_env STARBOARD_SMART_DIR ""
fi
if [ "$POOL" = 1 ]; then
  if [ "$MODE" = docker ]; then set_env STARBOARD_POOL_DIR /pool; else set_env STARBOARD_POOL_DIR "$PWD/pool"; fi
elif [ "$POOL" = 0 ]; then
  set_env STARBOARD_POOL_DIR ""
fi
# Your own extra mounts go in compose.override.yaml, which this installer never changes once it exists.
if [ ! -f compose.override.yaml ]; then
  printf '# Your own changes for Starboard. Ignored by git; ./install.sh and ./update.sh leave it alone.\nservices:\n  starboard: {}\n' > compose.override.yaml
fi
set_env COMPOSE_FILE "compose.yaml:compose.access.yaml:compose.override.yaml"
chmod 600 .env
echo "Saved .env and compose.access.yaml."

if [ "$HEALTH" = 1 ]; then
  say "Setting up Disk health (sudo)"
  if [ -f /etc/systemd/system/starboard-smart.timer ]; then
    echo "The Disk health timer is already installed."
  else
    # smartmontools reads each disk's health report. It lives in /usr/sbin, which is not on every user's path.
    if ! command -v smartctl >/dev/null && [ ! -x /usr/sbin/smartctl ]; then
      echo "Disk health needs smartmontools, which reads each disk's health report. Installing it now (sudo asks for your password)."
      sudo -v || fail "sudo did not accept the password, so smartmontools is not installed"
      if command -v apt-get >/dev/null; then
        quietly sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q smartmontools \
          || { quietly sudo apt-get update -q && quietly sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q smartmontools; }
      elif command -v dnf >/dev/null; then
        quietly sudo dnf install -y -q smartmontools
      else
        false
      fi || fail "smartmontools did not install. Install it yourself (for example: sudo apt install smartmontools), then run ./install.sh again"
    fi
    mkdir -p smart/requests
    sudo -v || fail "sudo did not accept the password, so Disk health is not set up"
    quietly sudo deploy/install-smart.sh "$PWD/smart" || fail "Disk health did not set up; the lines above say why"
    echo "Disk health is set up. Starboard reads each disk's report from $PWD/smart."
  fi
elif [ "$HEALTH" = 0 ] && [ -f /etc/systemd/system/starboard-smart.timer ]; then
  echo "Starboard no longer reads Disk health reports. The timer is still installed; to remove it, run:"
  echo "  sudo deploy/install-smart.sh --remove"
fi

if [ "$POOL" = 1 ]; then
  say "Setting up Drive pools (sudo)"
  if [ -f /etc/systemd/system/starboard-pool.path ] && cmp -s starboard/pool_helper.py /usr/local/bin/starboard-pool; then
    echo "The pool helper is already installed."
  else
    mkdir -p pool/requests pool/status
    sudo -v || fail "sudo did not accept the password, so the pool helper is not installed"
    quietly sudo deploy/install-pool.sh "$PWD/pool" || fail "the pool helper did not install; the lines above say why"
    echo "The pool helper is installed."
  fi
elif [ "$POOL" = 0 ] && [ -f /etc/systemd/system/starboard-pool.path ]; then
  echo "Starboard no longer uses the pool helper. It is still installed; to remove it, run:"
  echo "  sudo deploy/install-pool.sh --remove"
fi

if [ "$MODE" = docker ]; then
  say "Step 4: building and starting the container"
  if [ "${STARBOARD_QUIET_BUILD:-}" = 1 ] && [ -t 1 ]; then
    # From the Run first script: the build's own lines go to a log, and an animation shows it is working.
    build_log="$(mktemp "${TMPDIR:-/tmp}/starboard-build.XXXXXX")"
    docker compose up -d --build > "$build_log" 2>&1 &
    build=$!
    # shellcheck disable=SC1003  # the four spinner characters, a backslash among them
    spin='|/-\'
    i=0
    cols=$(tput cols 2>/dev/null || echo 80)
    # Keys pressed meanwhile are not shown, so Enter cannot push the line down; what was typed is thrown away after.
    quiet_keys=""
    if [ -t 0 ]; then quiet_keys="$(stty -g 2>/dev/null)" && stty -echo -icanon 2>/dev/null; fi
    while kill -0 "$build" 2>/dev/null; do
      # One line, redrawn in place and cut to the window, so it never wraps onto a second line.
      printf '\r\033[2K%s' "$(printf '  %s Building and starting Starboard. Please wait, this can take some time...' "${spin:i++%4:1}" | cut -c1-$(( cols - 1 )))"
      sleep 0.2
    done
    if [ -n "$quiet_keys" ]; then
      while read -r -t 0.05 -n 64 _ 2>/dev/null; do :; done
      stty "$quiet_keys" 2>/dev/null
    fi
    printf '\r\033[2K'
    if wait "$build"; then
      echo "  Built and started."
    else
      echo "  Building and starting Starboard did not finish. The last lines of the build:"
      tail -n 15 "$build_log" | sed 's/^/    /'
      case "$(tail -n 40 "$build_log")" in
        *"no space left"*|*"No space left"*) fail "the disk is full. Free some space, then run this again" ;;
        *"Could not resolve"*|*"dial tcp"*|*"TLS handshake"*|*"i/o timeout"*) fail "this computer could not reach the internet to download what Starboard is built from. Check the network, then run this again" ;;
        *"permission denied"*) fail "your user is not allowed to use Docker yet. Sign out and back in, then run this again" ;;
        *) fail "building Starboard did not work. The last lines of the build are above; the whole log is in $build_log" ;;
      esac
    fi
  else
    docker compose up -d --build
  fi
else
  say "Step 4: installing the systemd user service"
  unit_dir="$HOME/.config/systemd/user"
  mkdir -p "$unit_dir"
  sed -e "s|@DIR@|$PWD|g" -e "s|@PORT@|$PORT|g" deploy/starboard.service > "$unit_dir/starboard.service"
  systemctl --user daemon-reload
  systemctl --user enable --now starboard.service
  systemctl --user restart starboard.service
  echo "To keep it running after you sign out: loginctl enable-linger $USER"
fi

say "Waiting for Starboard to start"
for _ in $(seq 1 30); do
  if python3 -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$PORT/healthz', timeout=2)" 2>/dev/null; then
    ok=1; break
  fi
  sleep 2
done
[ "${ok:-}" = 1 ] || fail "Starboard did not start. See: docker compose logs starboard (or journalctl --user -u starboard)"

say "Starboard is running"
echo "On this computer: http://localhost:$PORT"
lan="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [ -f data/config.json ] && grep -q '"network_access": true' data/config.json && [ -n "$lan" ]; then
  echo "On your phone or other computers: http://$lan:$PORT"
fi
echo "What Starboard can access, and how to change it: Settings, About and updates."
if [ "$TERMINAL" = 1 ]; then
  echo "To update later: ./update.sh"
  # The rest of set-up, here: the password, the apps and download hours (starboard/terminal_setup.py).
  status=0
  STARBOARD_STARTS_APPS=1 python3 -m starboard.terminal_setup --port "$PORT" --data data --address "${lan:-}" || status=$?
  exit "$status"
fi
# No setup code once the set-up has finished: that is not a failure (set -e and pipefail would make it one).
code="$( { [ -f data/setup-token ] && [ ! -L data/setup-token ] && head -c 64 data/setup-token; } 2>/dev/null | tr -cd 'A-Za-z0-9_-' || true)"
if [ -n "$code" ]; then
  echo "Setup code (you need it once, to choose your password): $code"
  echo "No browser here? Finish in the terminal instead: python3 -m starboard.terminal_setup --port $PORT"
fi
echo "To update later: ./update.sh"
