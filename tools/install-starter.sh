#!/usr/bin/env bash
# Starboard's set-up helper (starter.sh) as a user service, for ./update.sh (DASH-299): servers set up before 0.16.0
# get it with an update. ./install.sh installs it itself. Left off when ./install.sh --no-starter turned it off
# (data/starter-off). Never fails: the update is already done.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 0
unit_dir="$HOME/.config/systemd/user"; unit=""; was=""
[ -f deploy/starboard-starter.service ] && [ -x starter.sh ] && [ ! -e data/starter-off ] || exit 0
command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1 || exit 0
unit="$unit_dir/starboard-starter.service"
mkdir -p "$unit_dir"
[ -f "$unit" ] && was="$(cat "$unit")"
sed -e "s|@DIR@|$PWD|g" deploy/starboard-starter.service > "$unit"
loginctl enable-linger "$(id -un)" >/dev/null 2>&1 || true
if systemctl --user daemon-reload && systemctl --user enable --now starboard-starter.service >/dev/null 2>&1 \
   && { [ "$was" = "$(cat "$unit")" ] || systemctl --user restart starboard-starter.service; }; then
  echo "Starboard's set-up helper is running."
else
  echo "Starboard's set-up helper did not start; the set-up in the browser shows a command where it would help."
fi
exit 0
