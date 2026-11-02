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
#   --disk-health         Set up Disk health reports (installs a timer with sudo; asks for your password)
#   --no-disk-health      Stop reading Disk health reports (and say how to remove the timer)
#   --yes                 Do not ask: use the options above, and your last answers (or No) for the rest
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
    --disk-health) HEALTH=1 ;;
    --no-disk-health) HEALTH=0 ;;
    --yes) ASK=0 ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -t 0 ] || ASK=0

say() { printf '\n== %s\n' "$*"; }
fail() { printf 'Stopped: %s\n' "$*" >&2; exit 1; }
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

cat <<'TEXT'

Starboard installer

What this does, in order:
  1. Checks that Docker (or, with --native, Python and systemd) is installed. It changes nothing.
  2. Asks what Starboard may access on this computer. Each one is optional: say no and only that part of
     Starboard is missing. Change your answers later by running ./install.sh again. Settings, About and
     updates shows what Starboard can access now.
  3. Writes your answers to .env and compose.access.yaml in this folder (only you can read .env).
  4. Builds and starts Starboard: with Docker, `docker compose up -d --build`; with --native, a systemd
     service for your user only. Neither needs sudo. Disk health is the one step that does, and only if
     you say yes to it.

Starboard runs as your user, in a read-only container with no extra privileges, and keeps its settings
in ./data. It never sends your settings anywhere.
TEXT

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
  if [ "$ASK" = 1 ]; then
    printf '\nName your dashboard (shown in the header; change it later in Settings) [Starboard]: '
    read -r NAME || NAME=""
  fi
  NAME="$(printf '%s' "${NAME:-Starboard}" | tr -d '\n\r=|&\\"' | cut -c1-60)"
fi

say "Step 2: what Starboard may access"

# Home network: asked on the first install only; after that it is a switch in Settings, Security.
if [ "$ASK" = 1 ] && [ ! -f data/config.json ] && [ "$NETWORK" = 1 ]; then
  echo
  echo "Home network: phones and other computers on your home network can open Starboard, with your password."
  echo "  No: only this computer can. You can change this later in Settings, Security."
  yes_no "Let your home network open Starboard?" 1 || NETWORK=0
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
    if [ "$ASK" = 1 ]; then
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
if [ "$DISKS_GIVEN" != skip ]; then
  for d in "${DISKS[@]+"${DISKS[@]}"}"; do
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
  elif [ "$ASK" = 1 ]; then
    echo
    echo "Disk health: a small script (deploy/starboard-smart.sh) runs smartctl as root every 30 minutes,"
    echo "  through a systemd timer, and saves each drive's health report in ./smart. Starboard reads them"
    echo "  read-only. Setting it up runs deploy/install-smart.sh with sudo, so you are asked for your"
    echo "  password. It needs smartmontools. No: System, Disk health says reports are not set up."
    if yes_no "Set up Disk health reports?" "$HEALTH"; then HEALTH=1; else HEALTH=0; fi
  fi
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
if [ "$HEALTH" != skip ]; then set_env STARBOARD_ALLOW_HEALTH "$HEALTH"; fi
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
  if [ "$DISKS_GIVEN" != skip ]; then
    i=0
    for d in "${DISKS[@]+"${DISKS[@]}"}"; do
      i=$((i + 1))
      echo "      - \"${d#*=}:/disks/$i:ro,rslave\"  # free space: ${d%%=*}"
    done
  fi
  if [ "$HEALTH" = 1 ]; then echo "      - ./smart:/smart:ro  # Disk health reports"; fi
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
    command -v smartctl >/dev/null || fail "install smartmontools first (for example: sudo apt install smartmontools), then run ./install.sh again"
    mkdir -p smart
    echo "Running: sudo deploy/install-smart.sh $PWD/smart"
    sudo deploy/install-smart.sh "$PWD/smart"
  fi
elif [ "$HEALTH" = 0 ] && [ -f /etc/systemd/system/starboard-smart.timer ]; then
  echo "Starboard no longer reads Disk health reports. The timer is still installed; to remove it, run:"
  echo "  sudo deploy/install-smart.sh --remove"
fi

if [ "$MODE" = docker ]; then
  say "Step 4: building and starting the container"
  docker compose up -d --build
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
if [ -f data/setup-token ]; then
  echo "Setup code (you need it once, to choose your password): $(cat data/setup-token)"
fi
echo "To update later: ./update.sh"
