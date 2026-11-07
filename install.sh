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
#   --plain               Plain lines with no boxes, colour or redrawing, for software that reads text aloud
#                         (the same as STARBOARD_PLAIN=1)
#
# In a terminal it is drawn like the Run first script and the terminal set-up (lib/terminal-frame.sh, the rules in
# the design system's docs/TERMINAL.md): a heading box and progress bar, one question at a time with numbered
# answers, a bar for each job, help with ?, feedback with f, and plain lines for screen readers. Every way it can
# stop has an error number (IN-01 and so on), explained on the help page Run first and installer error numbers.
# Your settings go in ./data and .env, which git ignores.
set -uo pipefail

cd "$(dirname "$(readlink -f "$0")")" || exit 1
ERR_URL="https://themightytrex.github.io/starboard/help/topics/run-first-errors.html"
err() { printf 'Error %s. What it means and how to fix it: %s#%s\n' "$1" "$ERR_URL" "$(printf '%s' "$1" | tr 'A-Z' 'a-z')"; }

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
START_APPS=0
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
    -h|--help) sed -n '2,34p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; err IN-01 >&2; exit 2 ;;
  esac
  shift
done
[ -t 0 ] || ASK=0
[ "$TERMINAL" = 0 ] || [ -t 0 ] || { echo "Stopped: --terminal needs a terminal to type in" >&2; err IN-02 >&2; exit 2; }
[ "$(id -u)" -ne 0 ] || { echo "Stopped: run this as your normal user, not root" >&2; err IN-04 >&2; exit 1; }

# The frame: answers come from the terminal; with --yes, or with no terminal, nothing is asked and plain lines are
# written (the Run first window keeps them in its log).
IN=""; [ "$ASK" = 1 ] && IN=/dev/tty
PLAIN="${STARBOARD_PLAIN:+1}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/starboard-install.XXXXXX")" || { echo "Stopped: no temporary folder" >&2; exit 1; }
LOG="$WORK/install.log"
: > "$LOG"
APP_VERSION="$(cat VERSION 2>/dev/null || echo unknown)"
STEPS=1
TITLES=("" "Starboard installer")
FEEDBACK_WHO="Installer"
# Starboard's own feedback flow (starboard/terminal_setup.py --feedback), used by the shared frame's f and r keys once
# Starboard is on this computer; before that, the frame shows a link instead.
app_feedback() {
  local dir="${FEEDBACK_DIR:-.}" extra=()
  command -v python3 >/dev/null && [ -f "$dir/starboard/terminal_setup.py" ] || return 1
  finish
  [ -z "$1" ] || extra+=(--problem "$1")
  [ "$FANCY" = 1 ] || extra+=(--plain)
  ( cd "$dir" && python3 -m starboard.terminal_setup --feedback "$FEEDBACK_WHO|$STEP|${TITLES[$STEP]}" "${extra[@]}" < "$IN" )
  return 0
}
# shellcheck source=lib/terminal-frame.sh
. lib/terminal-frame.sh

# fail CODE "reason": stops here, before or between jobs, with the reason and its error number.
fail() {
  finish
  echo
  printf 'Stopped: %s\n' "$2" | fold -s -w $(( COLS > 20 ? COLS - 1 : 79 ))
  err "$1"
  exit 1
}
# stop CODE "reason": inside a job (a subshell). The reason goes to the job's caller, which shows it under the bar.
stop() { printf '%s|%s\n' "$1" "$2" > "$WORK/reason"; echo "Stopped: $2"; exit 1; }
# job "name" function: runs one job with its bar; when it fails, its reason and error number go under the bar, with
# Try again (recommended), Show the details or Stop.
JOB_N=0
JOB_OF=1
JOBS_INTRO=""
job() {
  local name="$1" fn="$2" code reason
  JOB_N=$(( JOB_N + 1 ))
  while :; do
    rm -f "$WORK/reason"
    work "$name" "$fn" "$JOB_N" "$JOB_OF" && return 0
    code="IN-29"; reason="Something went wrong while ${name,}."
    if [ -s "$WORK/reason" ]; then IFS='|' read -r code reason < "$WORK/reason"; fi
    job_failed "$name" "${reason^}" "" "$code"
    [ "$FANCY" = 1 ] && { jobs_page "$STEP" "$JOBS_INTRO"; say ""; }
  done
}

env_value() {
  if [ -f .env ]; then sed -n "s/^$1=//p" .env | tail -n 1; fi
}
yes_or_no() { if [ "$1" = 1 ]; then echo 1; else echo 2; fi; }  # the answer number for a yes (1) or no (2) value
last() { [ "$1" = "$2" ] && printf ' (your last answer)'; }

# Starting the apps the set-up wrote (data/stack) ---------------------------------------------------------------
# Starboard starts them itself only when it has Docker access, which is off unless the person says yes, so the
# installer does it: after the terminal set-up, or with --start-apps when the browser set-up asks the Run first
# window. Folders are made, and given to the apps' user, with Starboard's own helper image, the same way Starboard
# does it, so no sudo is needed.
SA_ENV=data/stack/.env
SA_FILE=data/stack/compose.yaml
sa_dirs() {
  local key dir
  SA_DIRS=()
  for key in CONFIG_DIR DATA_DIR; do
    dir="$(sed -n "s/^$key=//p" "$SA_ENV" | tail -n 1)"; dir="${dir//\'/}"
    [[ "$dir" =~ ^/[A-Za-z0-9._/-]{1,250}$ ]] && [[ "$dir/" != *"/../"* ]] || return 1
    SA_DIRS+=("$dir")
  done
  SA_PUID="$(sed -n 's/^PUID=//p' "$SA_ENV" | tail -n 1)"; SA_PGID="$(sed -n 's/^PGID=//p' "$SA_ENV" | tail -n 1)"
  [[ "$SA_PUID" =~ ^[0-9]+$ ]] || SA_PUID="$(id -u)"; [[ "$SA_PGID" =~ ^[0-9]+$ ]] || SA_PGID="$(id -g)"
  SA_HELPER="$(sed -n 's/^HELPER_IMAGE = "\(.*\)"$/\1/p' starboard/containers.py)"
  SA_TOTAL="$(grep -c '^    container_name:' "$SA_FILE" || true)"
}
helped() {  # helped "shell command": run as root in the helper, with each apps' folder's nearest existing parent
  local binds=() d top
  for d in "${SA_DIRS[@]}"; do top="$d"; while [ ! -e "$top" ]; do top="$(dirname "$top")"; done; binds+=(-v "$top:$top"); done
  docker run --rm "${binds[@]}" --entrypoint sh "$SA_HELPER" -c "$1"
}
sa_folders() {
  # Each app's own settings folder too, before it starts: an app given a folder owned by root can stop at once
  # (Seerr does: "EACCES: permission denied, mkdir '/app/config/logs/'"). And every folder the apps use inside the
  # media folder (data/stack/folders.txt, from Install apps): Reelix does not make its library folders itself.
  local subs more
  subs="$(grep -o '\${CONFIG_DIR}/[A-Za-z0-9._-]*' "$SA_FILE" | grep -v -- '-db$' | sort -u | sed "s#^\${CONFIG_DIR}#${SA_DIRS[0]}#; s#.*#'&'#" | paste -sd' ' -)"
  more="$(grep -E '^/[A-Za-z0-9._/-]{1,250}$' data/stack/folders.txt 2>/dev/null | grep -v -- '/\.\./' | grep -F -- "${SA_DIRS[1]}/" \
    | sed "s#.*#'&'#" | paste -sd' ' - || true)"
  helped "mkdir -p '${SA_DIRS[0]}' '${SA_DIRS[1]}' $subs $more && chown $SA_PUID:$SA_PGID '${SA_DIRS[0]}' '${SA_DIRS[1]}' $subs $more" \
    || stop IN-31 "Starboard could not make the apps' folders, ${SA_DIRS[*]}."
}
sa_seed() {
  # First settings files Starboard wrote (data/stack/seed/<app>/<file>, such as SABnzbd's port and folders): each
  # goes in the app's settings folder only when the app has none yet, so your own settings are never replaced.
  local seed app_dir name top sab_key
  for seed in data/stack/seed/*/*; do
    [ -f "$seed" ] || continue
    app_dir="$(basename "$(dirname "$seed")")"; name="$(basename "$seed")"
    [[ "$app_dir" =~ ^[a-z0-9-]+$ ]] && [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || continue
    top="${SA_DIRS[0]}/$app_dir"
    docker run --rm -i -v "${SA_DIRS[0]}:${SA_DIRS[0]}" --entrypoint sh "$SA_HELPER" -c \
      "[ -e '$top/$name' ] || { mkdir -p '$top' && cat > '$top/$name' && chmod 600 '$top/$name' && chown $SA_PUID:$SA_PGID '$top' '$top/$name'; }" \
      < "$seed" >/dev/null 2>&1 || echo "Could not give $app_dir its first settings; it starts with its own."
  done
  # SABnzbd keeps the API key in its own settings, which stay when it is taken away and added again: Starboard is
  # given the key SABnzbd really has, so Starboard and Reelix can still use it.
  if [ -f data/stack/seed/sabnzbd/sabnzbd.ini ] && grep -q '^SABNZBD_API_KEY=' "$SA_ENV"; then
    sab_key="$(docker run --rm -v "${SA_DIRS[0]}:${SA_DIRS[0]}:ro" --entrypoint sh "$SA_HELPER" -c \
      "sed -n 's/^api_key *= *//p' '${SA_DIRS[0]}/sabnzbd/sabnzbd.ini' 2>/dev/null | head -n 1" 2>/dev/null | tr -d '\r')"
    if [[ "$sab_key" =~ ^[0-9A-Za-z]{16,64}$ ]] && ! grep -qx "SABNZBD_API_KEY=$sab_key" "$SA_ENV"; then
      sed -i "s/^SABNZBD_API_KEY=.*/SABNZBD_API_KEY=$sab_key/" "$SA_ENV"
    fi
  fi
  # Settings, Your install moving from SABnzbd to NZBGet when Starboard has no Docker access: it cannot read
  # SABnzbd's settings itself, so they are copied for it into data/stack (only your user can read the copy), and
  # Starboard moves the Usenet servers into NZBGet, then removes the copy.
  if [ -f data/stack/want-sab-servers ]; then
    if [ -s "${SA_DIRS[0]}/sabnzbd/sabnzbd.ini" ]; then
      (umask 077; helped "cat '${SA_DIRS[0]}/sabnzbd/sabnzbd.ini'" > data/stack/sab-servers.ini) 2>/dev/null || rm -f data/stack/sab-servers.ini
    fi
    rm -f data/stack/want-sab-servers
  fi
}
# How far Downloading and starting has got, after the timer: apps whose image is on this computer, then apps
# running (the same words as the browser set-up's Start step).
sa_count() {
  local have=0 img running
  for img in $SA_IMAGES; do docker image inspect "$img" > /dev/null 2>&1 && have=$(( have + 1 )); done
  [ "${SA_NOW:-0}" -gt 0 ] || return 0
  if [ "$have" -lt "$SA_NOW" ]; then echo "$have of $SA_NOW installed"; return; fi
  running="$(docker compose -p media-stack -f "$SA_FILE" --env-file "$SA_ENV" ps -q --status running 2>/dev/null | wc -l)"
  echo "$running of $SA_NOW running"
}
sa_up() {
  # A download that breaks off (the connection reset, a timeout) is tried again, twice, after a pause: Docker keeps
  # what it has, so each try carries on from there.
  local try status=0 running
  for try in 1 2 3; do
    status=0
    docker compose -p media-stack -f "$SA_FILE" --env-file "$SA_ENV" up -d --quiet-pull --remove-orphans > "$WORK/up.log" 2>&1 || status=$?
    cat "$WORK/up.log"
    [ "$status" != 0 ] && [ "$try" -lt 3 ] && grep -qiE 'connection reset|timeout|timed out|TLS handshake|unexpected EOF|i/o timeout|no such host|temporary failure|503|502|429 Too Many' "$WORK/up.log" || break
    echo "The download broke off. Trying again in 20 seconds (try $(( try + 1 )) of 3)."
    sleep 20
  done
  date +%s > data/stack/started-at  # Starboard waits for this to finish a change made in Settings, Your install
  # Folders Docker made for the apps are owned by root: give them to the apps' user, as Starboard's helper does.
  # Not a database's folder (jellystat-db, storyarr-db): the database owns it, and changing it while the database
  # sets itself up leaves it unfinished ("no pg_hba.conf entry").
  helped "for d in '${SA_DIRS[0]}'/* '${SA_DIRS[1]}'/media '${SA_DIRS[1]}'/downloads; do case \"\$d\" in *-db) continue ;; esac; [ -d \"\$d\" ] && chown $SA_PUID:$SA_PGID \"\$d\"; done; true" || true
  reelix_tokens  # Reelix may be running even when another app is not
  if [ "$status" != 0 ]; then
    running="$(docker compose -p media-stack -f "$SA_FILE" --env-file "$SA_ENV" ps -q --status running 2>/dev/null | wc -l)"
    stop IN-33 "$running of $SA_TOTAL apps are running; some did not start. Show the details for the last lines Docker wrote, fix what they say, then try again."
  fi
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
  if [ -n "$token" ]; then echo "Reelix is ready to be set up."; else echo "Reelix has not printed its set-up token yet."; fi
}
start_apps() {
  local problems running line
  STEPS=1; TITLES=("" "Start your apps" "Done")
  STEP=1
  page 1
  if [ ! -s "$SA_FILE" ] || [ ! -s "$SA_ENV" ]; then
    para "There are no apps to start: the set-up has not written them."
    finish; return 0
  fi
  sa_dirs || fail IN-30 "the apps' folder in $SA_ENV is not one Starboard can use"
  # The Starboard container can write data/stack, so the file is checked with Starboard's own rules before anything
  # starts: catalogue images only, no privileged containers or host access, folders inside the settings and media
  # folders (starboard/compose_check.py). From a terminal, a person can still choose to start what it lists.
  if ! problems="$(docker compose -p media-stack -f "$SA_FILE" --env-file "$SA_ENV" config --format json 2>/dev/null \
      | python3 -m starboard.compose_check "$SA_ENV" 2>&1)"; then
    note "The set-up file (data/stack/compose.yaml) has things Starboard did not write:"
    while IFS= read -r line; do hang "    - " "" "$line"; done <<< "$problems"
    if [ -n "$IN" ] && [ -z "${STARTER_RUN:-}" ]; then
      until choose "Start it anyway? Only if you added these yourself." 1 \
"Starboard checks the apps' file before starting them, because the Starboard container can write it. Start it only if you changed it yourself and know why." \
        "No, start nothing (recommended)" "Yes, start it: I added these myself"; do :; done
      [ "$CHOICE" = 2 ] || fail IN-32 "the set-up file has things Starboard did not write, so nothing was started"
    else
      fail IN-32 "the set-up file has things Starboard did not write, so nothing was started. If you added these yourself, run ./install.sh --start-apps in a terminal to choose"
    fi
  fi
  JOBS_INTRO="Downloading $SA_TOTAL apps and starting them. On a slow connection this can take 20 minutes or more. Please wait..."
  para "$JOBS_INTRO"
  say ""
  JOB_N=0; JOB_OF=3
  job "Making the apps' folders" sa_folders
  job "Giving the apps their first settings" sa_seed
  # One line per app that starts now (not the "later" ones), so two apps on one image both count.
  SA_IMAGES="$(docker compose -p media-stack -f "$SA_FILE" --env-file "$SA_ENV" config --images 2>/dev/null)"
  SA_NOW="$(printf '%s\n' "$SA_IMAGES" | grep -c . || true)"
  JOB_COUNT=sa_count
  job "Downloading and starting $SA_TOTAL apps" sa_up
  JOB_COUNT=""; COUNT_NOW=""
  running="$(docker compose -p media-stack -f "$SA_FILE" --env-file "$SA_ENV" ps -q --status running 2>/dev/null | wc -l)"
  say ""
  ok "$running of $SA_TOTAL apps are running. Open Starboard to see them."
  finish
}
if [ "$START_APPS" = 1 ]; then
  start_apps
  exit $?
fi

# Checks before anything is asked -------------------------------------------------------------------------------

[[ "$PORT" =~ ^[0-9]+$ ]] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || fail IN-03 "the port must be a number from 1 to 65535"
command -v git >/dev/null || fail IN-05 "install git first"
[ -d .git ] || fail IN-06 "run this inside a git clone of Starboard, so ./update.sh can update it later"
if [ "$MODE" = docker ]; then
  command -v docker >/dev/null || fail IN-07 "install Docker first, or use --native"
  docker compose version >/dev/null 2>&1 || fail IN-08 "install the Docker Compose plugin first, or use --native"
  READY="Docker and Docker Compose are installed."
else
  command -v python3 >/dev/null || fail IN-09 "install Python 3.10 or newer first"
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || fail IN-09 "Python 3.10 or newer is needed"
  command -v systemctl >/dev/null || fail IN-10 "--native needs systemd"
  READY="Python and systemd are installed."
fi

NAME=""
# The name is asked in the set-up, beside the password, in the browser and the terminal alike.
[ -f data/config.json ] || NAME="Starboard"
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

# Saved answers are the defaults; things set up by hand are left alone, and said so on the install step.
NOTES=()
[ -f data/config.json ] && [ "$NETWORK" = 0 ] && \
  NOTES+=("--local-only applies to a new install only. Starboard is already set up, so change who can open it in Settings, Security, Who can open the dashboard. It takes effect at once.")
ASK_DOCKER=0
if [ "$MODE" = docker ]; then
  if [ -z "$DOCKER" ]; then ASK_DOCKER=$ASK; DOCKER="$(env_value STARBOARD_ALLOW_DOCKER)"; DOCKER="${DOCKER:-0}"; fi
else
  DOCKER=0
fi
ASK_APPUSE=0
if [ -z "$APPUSE" ]; then ASK_APPUSE=$LATER; APPUSE="$(env_value STARBOARD_ALLOW_APPUSE)"; APPUSE="${APPUSE:-0}"; fi
ASK_LIVETV=0
if [ "$LIVETV" = "-" ]; then ASK_LIVETV=$LATER; LIVETV="$(env_value STARBOARD_LIVETV_PATH)"; fi
ASK_DISKS=0
if [ "$DISKS_GIVEN" = 0 ]; then
  hand="$(env_value STARBOARD_DISKS)"; saved="$(env_value STARBOARD_DISK_PATHS)"
  if [ -n "$hand" ] && [ -z "$saved" ]; then
    NOTES+=("Free space: you set up folders by hand (STARBOARD_DISKS), so the installer leaves them as they are.")
    DISKS_GIVEN=skip
  else
    IFS=',' read -r -a DISKS <<< "$saved"
    ASK_DISKS=$LATER
  fi
fi
ASK_HEALTH=0
if [ -z "$HEALTH" ]; then
  previous="$(env_value STARBOARD_ALLOW_HEALTH)"; HEALTH="${previous:-0}"
  if [ -n "$(env_value STARBOARD_SMART_DIR)" ] && [ -z "$previous" ]; then
    NOTES+=("Disk health: you set up reports by hand (STARBOARD_SMART_DIR), so the installer leaves them as they are.")
    HEALTH=skip
  else
    ASK_HEALTH=$LATER
  fi
fi
ASK_POOL=0
if [ -z "$POOL" ]; then
  previous="$(env_value STARBOARD_ALLOW_POOL)"; POOL="${previous:-0}"
  if [ -n "$(env_value STARBOARD_POOL_DIR)" ] && [ -z "$previous" ]; then
    NOTES+=("Drive pools: you set up the pool helper by hand (STARBOARD_POOL_DIR), so the installer leaves it as it is.")
    POOL=skip
  elif [ "$ASK" = 1 ] && { [ "$FIRST" = 0 ] || [ "$(extra_drives)" -ge 2 ]; }; then
    ASK_POOL=1
  fi
fi
ASK_NETWORK=0
[ "$ASK" = 1 ] && [ "$FIRST" = 1 ] && [ "$NETWORK" = 1 ] && ASK_NETWORK=1
FROM_RUN_FIRST="${STARBOARD_FROM_RUN_FIRST:-}"

# The steps, one question each --------------------------------------------------------------------------------

step_welcome() {
  page "$STEP"
  para "This installs Starboard in this folder, or changes what it may access. In order, it:"
  hang "  1.  " "" "Checks that Docker (or, with --native, Python and systemd) is installed. It changes nothing."
  hang "  2.  " "" "Asks what Starboard may access on this computer, one question at a time. Each is optional: say no and only that part of Starboard is missing."
  hang "  3.  " "" "Writes your answers to .env and compose.access.yaml in this folder (only you can read .env)."
  hang "  4.  " "" "Builds and starts Starboard. That needs no sudo. Disk health and Drive pools are the only steps that do, and only if you say yes to them."
  say ""
  ok "$READY"
  say ""
  para "Starboard runs as your user, in a read-only container with no extra privileges, and keeps its settings in ./data. It never sends your settings anywhere."
  MENU_RIGHT="Enter: start"; [ "$FANCY" = 1 ] && menu
  ask "Press Enter to start" "" \
"Run ./install.sh again at any time to change your answers; your settings and password stay. Settings, About and updates in Starboard shows what it can access now." || return $?
}

step_network() {
  page "$STEP"
  choose "Can phones and other computers on your home network open Starboard?" 1 \
"Yes: anyone on your home network can open the sign-in page, and needs your Starboard password to go further. Nothing outside your home network can reach it.

No: only this computer can open Starboard. You can change this later in Settings, Security." \
    "Yes, with your password (recommended)|Phones, tablets and other computers at home can open it." \
    "No, only this computer|You can change this later in Settings, Security." || return $?
  if [ "$CHOICE" = 1 ]; then NETWORK=1; else NETWORK=0; fi
}

step_docker() {
  page "$STEP"
  para "Starboard can list your apps' containers and, when you choose Update, download the new version and restart the app. For that it needs the Docker socket, which is full control of Docker, and so of this computer."
  yes_no_step "Give Starboard access to Docker for app updates?" "$DOCKER_HELP" STARBOARD_ALLOW_DOCKER "$DOCKER" \
    "Full control of Docker, and so of this computer." \
    "Apps, Updates says that updates are off, and the Run first window starts your apps. Nothing else changes." || return $?
  DOCKER=$YES
  if [ "$DOCKER" = 1 ] && [ ! -S /var/run/docker.sock ]; then fail IN-11 "there is no Docker socket at /var/run/docker.sock"; fi
}
DOCKER_HELP="Yes gives Starboard the Docker socket. It then lists your containers, updates them when you choose Update, and starts your media apps for you. Anyone who can sign in to Starboard could then control Docker, so keep your password safe.

No: Apps, Updates says that updates are off, and the Run first window starts your apps instead. Nothing else changes. Run ./install.sh again to change this."

# A yes or no question. With no earlier answer saved (KEY empty in .env), No is recommended and comes first; with
# one, Yes comes first and the earlier answer is marked "(your last answer)". Sets YES to 1 or 0.
yes_no_step() {
  local question="$1" help="$2" key="$3" now="$4" yes_about="$5" no_about="$6" def
  if [ -z "$(env_value "$key")" ]; then
    choose "$question" 1 "$help" "No (recommended)|$no_about" "Yes|$yes_about" || return $?
    if [ "$CHOICE" = 2 ]; then YES=1; else YES=0; fi
  else
    def="$(yes_or_no "$now")"
    choose "$question" "$def" "$help" "Yes$(last "$def" 1)|$yes_about" "No$(last "$def" 2)|$no_about" || return $?
    if [ "$CHOICE" = 1 ]; then YES=1; else YES=0; fi
  fi
}
step_appuse() {
  page "$STEP"
  para "System, Monitor can list each app's processor and memory use. Starboard reads two small read-only folders for that; with Docker access it also shows the apps' names, without it their short IDs."
  yes_no_step "Show each app's processor and memory use?" "No: Monitor shows the whole server only. Run ./install.sh again to change this." STARBOARD_ALLOW_APPUSE "$APPUSE" "Read-only." "Monitor shows the whole server only." || return $?
  APPUSE=$YES
}

step_livetv() {
  local def=2 folder
  [ -n "$LIVETV" ] && def=1
  page "$STEP"
  para "Starboard can build free channel playlists and TV guides for Jellyfin once a day (Settings, Jellyfin). For that it needs to write in the folder Jellyfin reads its Live TV files from, and nowhere else."
  [ -z "$LIVETV" ] || para "Now: $LIVETV"
  choose "Give Starboard a Live TV folder?" "$def" \
"No: the Live TV switch in Settings, Jellyfin says it needs this folder." \
    "Yes$(last "$def" 1)|Starboard writes only in that folder." "No$(last "$def" 2)|No Live TV playlists." || return $?
  if [ "$CHOICE" = 2 ]; then LIVETV=""; return 0; fi
  while :; do
    ask "Folder, for example /srv/jellyfin/config/iptv [$LIVETV]:" "$LIVETV" \
"The folder Jellyfin reads its Live TV playlists and guides from. Starboard writes there and nowhere else." || return $?
    folder="$ANSWER"
    if [ ! -d "$folder" ]; then para "There is no folder $folder. Type another, or b to go back."; continue; fi
    if [ ! -w "$folder" ]; then para "You cannot write in $folder. Give your user that folder first (for example: sudo chown -R $(id -un) \"$folder\"), then type it again."; continue; fi
    LIVETV="$folder"; return 0
  done
}

step_disks() {
  local def=2 line
  [ "${#DISKS[@]}" -gt 0 ] && def=1
  page "$STEP"
  para "System, Storage can show how full your folders or drives are. Starboard reads them read-only and does not open the files."
  [ "${#DISKS[@]}" = 0 ] || para "Now: ${DISKS[*]}"
  choose "Choose folders to show?" "$def" \
"Each folder is a name and a path, such as Media=/mnt/media. No: Storage shows no folders." \
    "Yes$(last "$def" 1)|One name and folder per line." "No$(last "$def" 2)|Storage shows no folders." || return $?
  if [ "$CHOICE" = 2 ]; then DISKS=(); return 0; fi
  DISKS=()
  para "Type one per line as Name=/path, such as Media=/mnt/media. An empty line finishes."
  while :; do
    ask "Folder:" "" "One per line as Name=/path, such as Media=/mnt/media. An empty line finishes." || return $?
    line="$ANSWER"
    [ -z "$line" ] && return 0
    if ! [[ "$line" =~ ^[^=,]+=/[^,]*$ ]]; then para "Write it as Name=/path, with no commas, such as Media=/mnt/media."; continue; fi
    if [ ! -d "${line#*=}" ]; then para "There is no folder ${line#*=}. Type another."; continue; fi
    DISKS+=("$line")
  done
}

step_health() {
  page "$STEP"
  para "A small script (deploy/starboard-smart.sh) runs smartctl as root every 30 minutes, through a systemd timer, and saves each drive's health report in ./smart. Starboard reads them read-only. It needs smartmontools."
  yes_no_step "Set up Disk health reports?" "Setting it up runs deploy/install-smart.sh with sudo, so you are asked for this computer's password. No: System, Disk health says reports are not set up." STARBOARD_ALLOW_HEALTH "$HEALTH" "sudo asks for your password." "Disk health says reports are not set up." || return $?
  HEALTH=$YES
}

step_pool() {
  page "$STEP"
  para "A pool joins several drives into one folder, /mnt/pool, and a backup drive protects it. The pool helper (deploy/install-pool.sh) does that work as root; Starboard only asks it, and every change needs your Starboard password and is checked first. It needs mergerfs, rsync and gdisk (and snapraid for a parity drive)."
  yes_no_step "Set up Drive pools?" "Setting it up runs sudo, so you are asked for this computer's password. No: System, Storage, Pool says the helper is not set up." STARBOARD_ALLOW_POOL "$POOL" "sudo asks for your password." "Pool says the helper is not set up." || return $?
  POOL=$YES
}

# The jobs ---------------------------------------------------------------------------------------------------------

safe_value() { case "$1" in *[\|\&\\\"\'\$\`]*|*$'\n'*) return 1 ;; esac; return 0; }
set_env() {
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
job_save() {
  local d i paths="" inside="" target origin repo
  # Values go into .env and compose.access.yaml: refuse characters that would break those files.
  if [ -n "$LIVETV" ] && ! safe_value "$LIVETV"; then stop IN-14 "the Live TV folder's name has a character Starboard cannot use (| & \\ \" ' \$ \`)"; fi
  if ! safe_value "$PWD"; then stop IN-14 "this folder's path has a character Starboard cannot use (| & \\ \" ' \$ \`); move it"; fi
  if [ -n "$LIVETV" ] && [ ! -d "$LIVETV" ]; then stop IN-12 "there is no folder $LIVETV"; fi
  if [ -n "$LIVETV" ] && [ ! -w "$LIVETV" ]; then stop IN-13 "you cannot write in $LIVETV; give your user that folder first (for example: sudo chown -R $(id -un) \"$LIVETV\")"; fi
  if [ "$DISKS_GIVEN" != skip ]; then
    for d in "${DISKS[@]+"${DISKS[@]}"}"; do
      safe_value "$d" || stop IN-14 "a folder name has a character Starboard cannot use (| & \\ \" ' \$ \`): $d"
      [[ "$d" =~ ^[^=,]+=/[^,]*$ ]] || stop IN-15 "write each folder as Name=/path, with no commas: $d"
      [ -d "${d#*=}" ] || stop IN-15 "there is no folder ${d#*=}"
    done
  fi
  if [ "$APPUSE" = 1 ] && [ ! -d /sys/fs/cgroup/system.slice ]; then
    echo "This computer has no /sys/fs/cgroup/system.slice (cgroup v2 with systemd), so per-app use stays off."
    APPUSE=0
  fi
  [ -f .env ] || (umask 077 && cp example.env .env)
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
    i=0
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
}
job_health() {
  if [ -f /etc/systemd/system/starboard-smart.timer ]; then echo "The Disk health timer is already installed."; return 0; fi
  # smartmontools reads each disk's health report. It lives in /usr/sbin, which is not on every user's path.
  if ! command -v smartctl >/dev/null && [ ! -x /usr/sbin/smartctl ]; then
    if command -v apt-get >/dev/null; then
      sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -q smartmontools \
        || { sudo -n apt-get update -q && sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -q smartmontools; }
    elif command -v dnf >/dev/null; then
      sudo -n dnf install -y -q smartmontools
    else
      false
    fi || stop IN-17 "smartmontools did not install. Install it yourself (for example: sudo apt install smartmontools), then run ./install.sh again"
  fi
  mkdir -p smart/requests
  sudo -n deploy/install-smart.sh "$PWD/smart" || stop IN-18 "Disk health did not set up. Show the details to see why."
  echo "Disk health is set up. Starboard reads each disk's report from $PWD/smart."
}
job_pool() {
  if [ -f /etc/systemd/system/starboard-pool.path ] && cmp -s starboard/pool_helper.py /usr/local/bin/starboard-pool; then
    echo "The pool helper is already installed."; return 0
  fi
  mkdir -p pool/requests pool/status
  sudo -n deploy/install-pool.sh "$PWD/pool" || stop IN-19 "the pool helper did not install. Show the details to see why."
  echo "The pool helper is installed."
}
job_build() {
  docker compose up -d --build && return 0
  case "$(tail -n 40 "$LOG")" in
    *"no space left"*|*"No space left"*) stop IN-20 "the disk is full. Free some space, then try again." ;;
    *"Could not resolve"*|*"dial tcp"*|*"TLS handshake"*|*"i/o timeout"*) stop IN-21 "this computer could not reach the internet to download what Starboard is built from. Check the network, then try again." ;;
    *"permission denied"*) stop IN-22 "your user is not allowed to use Docker yet. Sign out and back in, then run this again." ;;
    *) stop IN-23 "building Starboard did not work. Show the details for the last lines of the build." ;;
  esac
}
# While Starboard builds, the bar says which of the build's steps it is on (Docker writes "[3/8]" in its log).
build_detail() {
  local s
  s="$(grep -oE '\[[0-9]+/[0-9]+\]' "$LOG" 2>/dev/null | tail -n 1 | tr -d '[]')"
  [ -z "$s" ] || printf 'step %s of %s' "${s%/*}" "${s#*/}"
}
job_service() {
  local unit_dir="$HOME/.config/systemd/user"
  mkdir -p "$unit_dir"
  sed -e "s|@DIR@|$PWD|g" -e "s|@PORT@|$PORT|g" deploy/starboard.service > "$unit_dir/starboard.service"
  systemctl --user daemon-reload && systemctl --user enable --now starboard.service && systemctl --user restart starboard.service \
    || stop IN-23 "the Starboard service did not start. Show the details to see what systemd said."
}
job_wait() {
  local _
  for _ in $(seq 1 30); do
    python3 -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$PORT/healthz', timeout=2)" 2>/dev/null && return 0
    sleep 2
  done
  stop IN-24 "Starboard did not start. See: docker compose logs starboard (or journalctl --user -u starboard)"
}

needs_sudo() {
  { [ "$HEALTH" = 1 ] && [ ! -f /etc/systemd/system/starboard-smart.timer ]; } || \
  { [ "$POOL" = 1 ] && ! { [ -f /etc/systemd/system/starboard-pool.path ] && cmp -s starboard/pool_helper.py /usr/local/bin/starboard-pool; }; }
}
step_install() {
  local n
  page "$STEP"
  FIRST_BACK=$STEP  # files are written from here: earlier answers are changed by running the installer again
  JOBS_INTRO="Please wait, this can take some time..."
  [ "$FIRST" = 1 ] && JOBS_INTRO="Your media folder, the folders Starboard shows, Live TV and disk health come next, in Starboard's set-up. Please wait, this can take some time..."
  for n in "${NOTES[@]+"${NOTES[@]}"}"; do note "$n"; done
  if needs_sudo && ! sudo -n true 2>/dev/null; then
    if [ -z "$IN" ]; then fail IN-16 "Disk health and Drive pools need sudo, and there is no terminal to type the password in. Run ./install.sh in a terminal"; fi
    para "sudo asks for the password you use to sign in to this computer, once (nothing shows as you type)."
    say ""
    KEYS="Ctrl+C"; MENU_RIGHT="Enter: send the password"; [ "$FANCY" = 1 ] && menu
    # shellcheck disable=SC2024  # the input is for sudo itself: it reads the password from the terminal
    sudo -v < "$IN" || fail IN-16 "sudo did not accept the password"
    ( while sleep 50; do sudo -n -v 2>/dev/null || exit; done ) &
    KEEP=$!
    KEYS="? f q"; MENU_RIGHT=""; [ "$FANCY" = 1 ] && menu
  fi
  para "$JOBS_INTRO"
  say ""
  JOB_N=0
  JOB_OF=3; [ "$HEALTH" = 1 ] && JOB_OF=$(( JOB_OF + 1 )); [ "$POOL" = 1 ] && JOB_OF=$(( JOB_OF + 1 ))
  job "Saving your answers" job_save
  if [ "$HEALTH" = 1 ]; then job "Setting up Disk health" job_health; fi
  if [ "$POOL" = 1 ]; then job "Setting up Drive pools" job_pool; fi
  if [ "$MODE" = docker ]; then
    JOB_DETAIL=build_detail
    job "Building and starting Starboard" job_build
    JOB_DETAIL=""
  else
    job "Installing the Starboard service" job_service
  fi
  job "Waiting for Starboard to answer" job_wait
  return 0
}

step_done() {
  local lan code
  page "$STEP"
  lan="$(hostname -I 2>/dev/null | awk '{print $1}')"
  LAN="$lan"
  ok "Starboard is running."
  say ""
  card "Open Starboard" "On this computer" "http://localhost:$PORT"
  if [ "$NETWORK" = 1 ] && [ -n "$lan" ]; then card_row "On other devices" "http://$lan:$PORT"; fi
  code="$( { [ -f data/setup-token ] && [ ! -L data/setup-token ] && head -c 64 data/setup-token; } 2>/dev/null | tr -cd 'A-Za-z0-9_-' || true)"
  if [ -n "$code" ] && [ "$TERMINAL" = 0 ]; then card_row "Setup code" "$code"; fi
  card_row "Ask again" "./install.sh"
  card_row "Update" "./update.sh"
  card_end
  if [ "$HEALTH" = 0 ] && [ -f /etc/systemd/system/starboard-smart.timer ]; then
    note "Starboard no longer reads Disk health reports. The timer is still installed; to remove it, run: sudo deploy/install-smart.sh --remove"
  fi
  if [ "$POOL" = 0 ] && [ -f /etc/systemd/system/starboard-pool.path ]; then
    note "Starboard no longer uses the pool helper. It is still installed; to remove it, run: sudo deploy/install-pool.sh --remove"
  fi
  [ "$MODE" = native ] && note "To keep it running after you sign out: loginctl enable-linger $USER"
  if [ -n "$code" ] && [ "$TERMINAL" = 0 ]; then
    para "You need the setup code once, to choose your password. No browser here? Finish in the terminal instead: python3 -m starboard.terminal_setup --port $PORT"
  fi
  para "What Starboard can access, and how to change it: Settings, About and updates."
  if [ "$TERMINAL" = 1 ]; then
    ask "Press Enter to set up the rest here: your password, your apps and download hours" "" \
"The terminal set-up asks the same questions as the set-up in a browser. Run it again later with: python3 -m starboard.terminal_setup" || true
  fi
}

# Run it ----------------------------------------------------------------------------------------------------------

LIST=()
[ "$ASK" = 1 ] && [ -z "$FROM_RUN_FIRST" ] && LIST+=(welcome)
[ "$ASK_NETWORK" = 1 ] && LIST+=(network)
[ "$ASK_DOCKER" = 1 ] && LIST+=(docker)
[ "$ASK_APPUSE" = 1 ] && LIST+=(appuse)
[ "$ASK_LIVETV" = 1 ] && LIST+=(livetv)
[ "$ASK_DISKS" = 1 ] && LIST+=(disks)
[ "$ASK_HEALTH" = 1 ] && LIST+=(health)
[ "$ASK_POOL" = 1 ] && LIST+=(pool)
LIST+=(install)
STEPS=${#LIST[@]}
TITLES=("")
for s in "${LIST[@]}"; do
  case "$s" in
    welcome) TITLES+=("What the installer does") ;;
    network) TITLES+=("Your home network") ;;
    docker) TITLES+=("App updates") ;;
    appuse) TITLES+=("Each app's use") ;;
    livetv) TITLES+=("Live TV") ;;
    disks) TITLES+=("Folders to show") ;;
    health) TITLES+=("Disk health") ;;
    pool) TITLES+=("Drive pools") ;;
    install) TITLES+=("Install Starboard") ;;
  esac
done
TITLES+=("Done")
[ "$SMALL" = 1 ] && para "This window is $COLS by $ROWS characters, so the installer shows plain lines. For the boxed look, make it at least 60 by 20 and run this again."
STEP=1
while [ "$STEP" -le "$STEPS" ]; do
  "step_${LIST[$(( STEP - 1 ))]}"; rc=$?
  case "$rc" in
    0) STEP=$(( STEP + 1 )); CAME_BACK=0 ;;
    10) STEP=$(( STEP - 1 )); [ "$STEP" -ge 1 ] || STEP=1; CAME_BACK=1 ;;
    *) ;;
  esac
done
STOP_WORDS="Stopped. Starboard is installed and running."
step_done
finish
if [ "$TERMINAL" = 1 ]; then
  # The rest of set-up, here: the password, the apps and download hours (starboard/terminal_setup.py), in its own frame.
  status=0
  STARBOARD_STARTS_APPS=1 python3 -m starboard.terminal_setup --port "$PORT" --data data --address "${LAN:-}" || status=$?
  exit "$status"
fi
exit 0
