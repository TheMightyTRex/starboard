#!/usr/bin/env bash
# Locked out by the two-step code or single sign-on? Run this on the server, in the Starboard folder:  ./reset-sign-in.sh
#
# It turns off the two-step code and single sign-on, allows the password again, signs everyone out and restarts
# Starboard. Your password, apps and settings stay as they are; so do the provider details, which stay off until you
# turn single sign-on on again. Works for the installer (Docker or --native). With the ready-made image, see
# docs/help (Get back in when sign-in is locked).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
[ -d data ] || { echo "Stopped: no data folder here. Run this in the folder you installed Starboard in." >&2; exit 1; }

touch data/reset-sign-in
if [ -f /etc/systemd/user/starboard.service ] || systemctl --user cat starboard >/dev/null 2>&1; then
  systemctl --user restart starboard
else
  docker compose restart starboard >/dev/null
fi
for _ in $(seq 1 30); do
  [ ! -f data/reset-sign-in ] && break
  sleep 1
done
[ ! -f data/reset-sign-in ] || { echo "Stopped: Starboard did not restart. Its log says why: docker compose logs starboard (or, for --native, journalctl --user -u starboard)" >&2; exit 1; }
echo "The two-step code and single sign-on are off, the password works again and everyone is signed out."
echo "Open Starboard and sign in with your password."
