#!/usr/bin/env bash
# Forgotten the password? Run this on the server, in the Starboard folder:  ./reset-password.sh
#
# It removes the password, signs everyone out and restarts Starboard, which prints a new setup code. Open
# Starboard, enter the code and choose a new password. Your apps and settings stay as they are.
# Works for the installer (Docker or --native). With the ready-made image, see docs/help (Reset a forgotten password).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
[ -d data ] || { echo "Stopped: no data folder here. Run this in the folder you installed Starboard in." >&2; exit 1; }

touch data/reset-password
if [ -f /etc/systemd/user/starboard.service ] || systemctl --user cat starboard >/dev/null 2>&1; then
  systemctl --user restart starboard
else
  docker compose restart starboard >/dev/null
fi
for _ in $(seq 1 30); do
  [ ! -f data/reset-password ] && [ -s data/setup-token ] && break
  sleep 1
done
[ -s data/setup-token ] || { echo "Stopped: Starboard did not restart. Its log says why: docker compose logs starboard (or, for --native, journalctl --user -u starboard)" >&2; exit 1; }
echo "The password is removed and everyone is signed out."
echo "Open Starboard, enter this setup code and choose a new password: $(cat data/setup-token)"
