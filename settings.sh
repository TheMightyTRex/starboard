#!/usr/bin/env bash
# Starboard's settings from the terminal, for a server with no desktop (DASH-90):  ./settings.sh
#
# It signs in with your Starboard password and changes settings through Starboard's own API on this computer,
# starting with the automatic update settings. The same look as the terminal set-up; --plain gives plain lines for
# software that reads text aloud (the same as STARBOARD_PLAIN=1). Starboard must be running.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")" || { echo "Stopped: the Starboard folder cannot be opened" >&2; exit 1; }
port="$(sed -n 's/^STARBOARD_PORT=//p' .env 2>/dev/null | tail -n 1)"
exec python3 -m starboard.terminal_settings --port "${port:-8095}" "$@"
