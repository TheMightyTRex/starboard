#!/usr/bin/env bash
# Install Starboard. Run from the folder you cloned:  ./install.sh
#
#   --native         Run with this computer's Python as a systemd user service, without Docker
#   --port 8095      Port to listen on
#   --network        Let other devices on your network open it (default: this computer only)
#
# Nothing here needs sudo. Your settings go in ./data, which git ignores.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
MODE=docker
PORT=8095
BIND=127.0.0.1

while [ $# -gt 0 ]; do
  case "$1" in
    --native) MODE=native ;;
    --port) PORT="${2:?--port needs a number}"; shift ;;
    --network) BIND=0.0.0.0 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\n== %s\n' "$*"; }
fail() { printf 'Stopped: %s\n' "$*" >&2; exit 1; }

[[ "$PORT" =~ ^[0-9]+$ ]] && [ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || fail "the port must be a number from 1 to 65535"
[ "$(id -u)" -ne 0 ] || fail "run this as your normal user, not root"
command -v git >/dev/null || fail "install git first"
[ -d .git ] || fail "run this inside a git clone of Starboard, so ./update.sh can update it later"

say "Checking what is installed"
if [ "$MODE" = docker ]; then
  command -v docker >/dev/null || fail "install Docker first, or use --native"
  docker compose version >/dev/null 2>&1 || fail "install the Docker Compose plugin first, or use --native"
else
  command -v python3 >/dev/null || fail "install Python 3.10 or newer first"
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || fail "Python 3.10 or newer is needed"
  command -v systemctl >/dev/null || fail "--native needs systemd"
fi

say "Writing settings to .env"
umask 077
[ -f .env ] || cp example.env .env
set_env() {
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
set_env STARBOARD_MODE "$MODE"
set_env STARBOARD_PORT "$PORT"
set_env STARBOARD_BIND "$BIND"
set_env STARBOARD_UID "$(id -u)"
set_env STARBOARD_GID "$(id -g)"
if ! grep -q '^STARBOARD_REPO=.\+' .env; then
  origin="$(git remote get-url origin 2>/dev/null || true)"
  repo="$(printf '%s' "$origin" | sed -nE 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#p')"
  [ -n "$repo" ] && set_env STARBOARD_REPO "$repo"
fi
chmod 600 .env
mkdir -p data backups
chmod 700 data backups

if [ "$MODE" = docker ]; then
  say "Building and starting the container"
  docker compose up -d --build
else
  say "Installing the systemd user service"
  unit_dir="$HOME/.config/systemd/user"
  mkdir -p "$unit_dir"
  sed -e "s|@DIR@|$PWD|g" -e "s|@PORT@|$PORT|g" -e "s|@BIND@|$BIND|g" deploy/starboard.service > "$unit_dir/starboard.service"
  systemctl --user daemon-reload
  systemctl --user enable --now starboard.service
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

host="localhost"
[ "$BIND" = 0.0.0.0 ] && host="$(hostname -I 2>/dev/null | awk '{print $1}')"
say "Starboard is running"
echo "Open: http://${host:-localhost}:$PORT"
if [ -f data/setup-token ]; then
  echo "Setup code (you need it once, to choose your password): $(cat data/setup-token)"
fi
echo "To update later: ./update.sh"
