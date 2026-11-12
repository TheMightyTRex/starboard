#!/usr/bin/env bash
# Run this computer with no screen or keyboard (DASH-89):  sudo deploy/headless.sh
#
# For a server that sits in a cupboard: it should never sleep, never wait at a boot menu with nobody to press Enter,
# repair its disks at start without asking, and start again by itself after a crash. This script changes the
# operating system's settings for that. It first shows each change, what is set now and what it would set, and
# changes nothing until you say yes. It saves a copy of every file it edits, and --undo puts each change back.
#
#   (no option)   Show the changes, then ask before making any of them
#   --check       Only show what is set now and what would change. Changes nothing
#   --undo        Show what this script changed before, then ask before putting it back
#   --firmware    What to set in the firmware (BIOS or UEFI) yourself, which no script can change. Changes nothing
#
# It needs sudo for everything but --check and --firmware. It never runs as part of Starboard's tests, the installer
# or an update: only when you run it. Plain lines throughout, so software that reads text aloud reads every line.
# The firmware words are in the help too; the full plan is Starboard's HEADLESS-AND-RECOVERY notes, part 2.
set -uo pipefail

SAVED=/var/lib/starboard/headless          # copies of edited files, and the list of what was changed
LOGIND=/etc/systemd/logind.conf.d/starboard-headless.conf
GRUB_DROP=/etc/default/grub.d/starboard-headless.cfg
SYSCTL=/etc/sysctl.d/90-starboard-headless.conf
WATCHDOG=/etc/systemd/system.conf.d/starboard-headless.conf
PI_CMDLINE=/boot/firmware/cmdline.txt     # Raspberry Pi OS: no GRUB, the kernel options are in this file
SLEEP_TARGETS=(sleep.target suspend.target hibernate.target hybrid-sleep.target)

MODE=apply
case "${1:-}" in
  "") ;;
  --check) MODE=check ;;
  --undo) MODE=undo ;;
  --firmware) MODE=firmware ;;
  -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
  *) echo "Unknown option: $1. Run it with --help for the options." >&2; exit 2 ;;
esac

IN=/dev/tty
{ : < /dev/tty; } 2>/dev/null || IN=""
tell() { printf '%s\n' "$1" | fold -s -w "$(( $(tput cols 2>/dev/null || echo 80) > 20 ? $(tput cols 2>/dev/null || echo 80) - 1 : 79 ))"; }

firmware() {
  tell "In the firmware (BIOS or UEFI): set these yourself"
  tell "No script can change these. Start the computer and press the key it shows at the very start (often Delete, F2, F10 or Esc) to open its settings. The names differ between makers; look for words like these:"
  echo
  tell "1. Restore on AC power loss (also called After power failure or AC back): set it to Power On, or Last State. The computer then comes back on by itself after a power cut."
  tell "2. Halt on errors, or Keyboard required: set it to No errors, or Not required. The computer then starts with no keyboard plugged in."
  tell "3. Wake on LAN: set it to Enabled, so another device at home can switch it on."
  tell "4. Boot order: the system drive first, and network boot off, so it does not wait trying to start from the network."
  tell "5. Integrated graphics: leave it on. Some computers do not start with no display adapter, and Jellyfin can use it to convert video."
  echo
  tell "Some computers do not start, or start at a tiny size, with no display plugged in. A dummy HDMI plug (a small adapter that pretends to be a display) puts that right."
  tell "Save the settings and leave (often F10), then check the computer starts with the display and keyboard unplugged."
}
if [ "$MODE" = firmware ]; then firmware; exit 0; fi

if [ "$MODE" != check ] && [ "$(id -u)" -ne 0 ]; then
  tell "Stopped: this changes the computer's settings, so run it with sudo: sudo deploy/headless.sh"
  tell "To only see what it would change, run: deploy/headless.sh --check"
  exit 1
fi

has() { command -v "$1" >/dev/null 2>&1; }
pi() { [ -f "$PI_CMDLINE" ] && ! [ -f /etc/default/grub ]; }

# Each change: its name, what is set now, what it sets, and whether it is set already.
NAMES=(sleep power bootmenu repair crash watchdog)
title() {
  case "$1" in
    sleep) echo "Never sleep" ;;
    power) echo "The lid and the power button" ;;
    bootmenu) echo "No waiting at the boot menu" ;;
    repair) echo "Repair the disks at start without asking" ;;
    crash) echo "Start again 10 seconds after a crash" ;;
    watchdog) echo "Start again if the computer freezes" ;;
  esac
}
applies() {
  case "$1" in
    sleep|power) has systemctl ;;
    bootmenu) [ -f /etc/default/grub ] && has update-grub ;;
    repair) { [ -f /etc/default/grub ] && has update-grub; } || pi ;;
    crash) [ -d /etc/sysctl.d ] ;;
    watchdog) [ -e /dev/watchdog ] && has systemctl ;;
  esac
}
now() {
  case "$1" in
    sleep) local m; m="$(systemctl is-enabled sleep.target 2>/dev/null || true)"
           if [ "$m" = masked ]; then echo "sleep is deactivated"; else echo "it can sleep or suspend when idle or when asked"; fi ;;
    power) if [ -f "$LOGIND" ]; then echo "set by this script"; else echo "closing a laptop's lid suspends it"; fi ;;
    bootmenu) local t; t="$(sed -n 's/^GRUB_TIMEOUT=//p' /etc/default/grub /etc/default/grub.d/*.cfg 2>/dev/null | tail -n 1 | tr -d '"')"
              echo "the boot menu waits ${t:-an unknown number of} seconds, and for ever after a failed start" ;;
    repair) if is_set repair; then echo "repairs without asking"; else echo "a disk check that finds a problem stops the start and waits for someone to type"; fi ;;
    crash) echo "after a crash it waits $(cat /proc/sys/kernel/panic 2>/dev/null || echo 0) seconds (0 is for ever)" ;;
    watchdog) if [ -f "$WATCHDOG" ]; then echo "set by this script"; else echo "the computer's watchdog is not used"; fi ;;
  esac
}
will() {
  case "$1" in
    sleep) echo "sleep, suspend and hibernate are deactivated: systemctl mask ${SLEEP_TARGETS[*]}" ;;
    power) echo "the lid is ignored, and one short press of the power button shuts down cleanly: $LOGIND" ;;
    bootmenu) echo "the menu waits 2 seconds, and 5 after a failed start: $GRUB_DROP, then update-grub" ;;
    repair) if pi; then echo "fsck.repair=yes added to $PI_CMDLINE (a copy is saved first)"
            else echo "fsck.repair=yes added to the kernel options: ${GRUB_DROP%.cfg}-repair.cfg, then update-grub"; fi ;;
    crash) echo "kernel.panic = 10 in $SYSCTL, applied now" ;;
    watchdog) echo "RuntimeWatchdogSec=30s and RebootWatchdogSec=10min in $WATCHDOG, from the next start" ;;
  esac
}
is_set() {
  case "$1" in
    sleep) [ "$(systemctl is-enabled sleep.target 2>/dev/null || true)" = masked ] ;;
    power) [ -f "$LOGIND" ] ;;
    bootmenu) [ -f "$GRUB_DROP" ] ;;
    repair) if pi; then grep -q 'fsck.repair=yes' "$PI_CMDLINE"; else [ -f "${GRUB_DROP%.cfg}-repair.cfg" ]; fi ;;
    crash) [ -f "$SYSCTL" ] ;;
    watchdog) [ -f "$WATCHDOG" ] ;;
  esac
}

save_copy() {  # a copy of a file before it is edited, kept in $SAVED/saved
  local f="$1" to
  to="$SAVED/saved/$(printf '%s' "$f" | tr '/' '_').$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$SAVED/saved" && cp -a "$f" "$to" && printf '%s\t%s\n' "$f" "$to" >> "$SAVED/copies"
}
note_done() { mkdir -p "$SAVED"; grep -qx "$1" "$SAVED/applied" 2>/dev/null || echo "$1" >> "$SAVED/applied"; }
# Undo never deletes: what this script wrote moves to $SAVED/undone, where you can look at it or delete it yourself.
put_aside() {
  local f="$1" to
  to="$SAVED/undone/$(date +%Y%m%d-%H%M%S)"
  [ -e "$f" ] || return 0
  mkdir -p "$to" && mv "$f" "$to/$(printf '%s' "$f" | tr '/' '_')"
}

apply() {
  case "$1" in
    sleep) systemctl mask "${SLEEP_TARGETS[@]}" ;;
    power) mkdir -p "$(dirname "$LOGIND")" && printf '%s\n' "# Written by Starboard's deploy/headless.sh. Undo: sudo deploy/headless.sh --undo" \
             "[Login]" "HandleLidSwitch=ignore" "HandleLidSwitchExternalPower=ignore" "HandleLidSwitchDocked=ignore" "HandlePowerKey=poweroff" \
             > "$LOGIND" && echo "The lid and power button take effect at the next start." ;;
    bootmenu) mkdir -p /etc/default/grub.d && printf '%s\n' "# Written by Starboard's deploy/headless.sh. Undo: sudo deploy/headless.sh --undo" \
                "GRUB_TIMEOUT=2" "GRUB_RECORDFAIL_TIMEOUT=5" > "$GRUB_DROP" && update-grub ;;
    repair) if pi; then save_copy "$PI_CMDLINE" && sed -i '1 s/$/ fsck.repair=yes/' "$PI_CMDLINE"
            else mkdir -p /etc/default/grub.d && printf '%s\n' "# Written by Starboard's deploy/headless.sh. Undo: sudo deploy/headless.sh --undo" \
                   'GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT:-} fsck.repair=yes"' > "${GRUB_DROP%.cfg}-repair.cfg" && update-grub; fi ;;
    crash) printf '%s\n' "# Written by Starboard's deploy/headless.sh. Undo: sudo deploy/headless.sh --undo" "kernel.panic = 10" > "$SYSCTL" \
             && sysctl -q -p "$SYSCTL" ;;
    watchdog) mkdir -p "$(dirname "$WATCHDOG")" && printf '%s\n' "# Written by Starboard's deploy/headless.sh. Undo: sudo deploy/headless.sh --undo" \
                "[Manager]" "RuntimeWatchdogSec=30s" "RebootWatchdogSec=10min" > "$WATCHDOG" ;;
  esac
}
undo() {
  local saved
  case "$1" in
    sleep) systemctl unmask "${SLEEP_TARGETS[@]}" ;;
    power) put_aside "$LOGIND" ;;
    bootmenu) put_aside "$GRUB_DROP" && update-grub ;;
    repair) if pi; then
              saved="$(awk -F'\t' -v f="$PI_CMDLINE" '$1 == f {print $2; exit}' "$SAVED/copies" 2>/dev/null)"
              if [ -n "$saved" ] && [ -f "$saved" ]; then cp -a "$PI_CMDLINE" "$SAVED/saved/cmdline.before-undo.$(date +%Y%m%d-%H%M%S)" && cp -a "$saved" "$PI_CMDLINE"
              else sed -i '1 s/ fsck.repair=yes//' "$PI_CMDLINE"; fi
            else put_aside "${GRUB_DROP%.cfg}-repair.cfg" && update-grub; fi ;;
    crash) put_aside "$SYSCTL" && sysctl -q --system ;;
    watchdog) put_aside "$WATCHDOG" ;;
  esac
}

# A numbered question: 1 is the recommended answer and Enter takes it (the terminal wizard rules).
ask_choice() {
  local question="$1" n="$2" answer=""
  [ -n "$IN" ] || { tell "Stopped: there is no terminal to answer in, so nothing was changed."; exit 1; }
  while :; do
    printf '%s [1]: ' "$question"
    read -r answer < "$IN" || answer=q
    answer="${answer:-1}"
    case "$answer" in q|Q) tell "Stopped. Nothing was changed."; exit 1 ;; esac
    if [[ "$answer" =~ ^[0-9]+$ ]] && [ "$answer" -ge 1 ] && [ "$answer" -le "$n" ]; then CHOICE="$answer"; return 0; fi
    tell "Type a number from 1 to $n, or q to stop."
  done
}

if [ "$MODE" = undo ]; then
  mapfile -t done_list < <(cat "$SAVED/applied" 2>/dev/null)
  if [ ${#done_list[@]} -eq 0 ]; then tell "This script has not changed anything on this computer, so there is nothing to put back."; exit 0; fi
  tell "Put back what Starboard's headless script changed"
  tell "Nothing has changed yet. These would go back to how they were:"
  for c in "${done_list[@]}"; do tell "  - $(title "$c")"; done
  tell "Files this script wrote move to $SAVED/undone, where you can look at them or delete them yourself."
  echo
  tell "Put them back?"
  echo "  1. Yes, put them back (recommended)"
  echo "  2. No, change nothing"
  ask_choice "Your choice" 2
  [ "$CHOICE" = 1 ] || { tell "Nothing was changed."; exit 0; }
  for c in "${done_list[@]}"; do
    if undo "$c"; then tell "Done: $(title "$c") is back as it was."; sed -i "/^$c\$/d" "$SAVED/applied"
    else tell "Did not finish: $(title "$c"). The lines above say why; nothing else was changed for it."; fi
  done
  exit 0
fi

tell "Run this computer with no screen or keyboard"
tell "Checking what is set now. This changes nothing."
echo
todo=()
i=0
for c in "${NAMES[@]}"; do
  applies "$c" || continue
  i=$(( i + 1 ))
  if is_set "$c"; then tell "$i. $(title "$c"): already set ($(now "$c"))."
  else
    tell "$i. $(title "$c")"
    tell "   Now: $(now "$c")."
    tell "   Change: $(will "$c")."
    todo+=("$c")
  fi
done
if pi; then tell "This is a Raspberry Pi, which has no boot menu to wait at."; fi
echo
if [ "$MODE" = check ]; then
  if [ ${#todo[@]} -eq 0 ]; then tell "Everything is set already."; else tell "To make these changes, run: sudo deploy/headless.sh"; fi
  tell "For the firmware's own settings, run: deploy/headless.sh --firmware"
  exit 0
fi
if [ ${#todo[@]} -eq 0 ]; then
  tell "Everything is set already. Nothing was changed."
  tell "For the firmware's own settings, run: deploy/headless.sh --firmware"
  exit 0
fi

tell "Nothing has changed yet. A copy of each file is saved in $SAVED first, and sudo deploy/headless.sh --undo puts every change back."
echo
tell "Make these changes?"
echo "  1. Yes, make all ${#todo[@]} (recommended)"
echo "  2. Choose which ones"
echo "  3. No, change nothing"
ask_choice "Your choice" 3
case "$CHOICE" in
  3) tell "Nothing was changed."; exit 0 ;;
  2)
    picked=()
    for c in "${todo[@]}"; do
      tell "$(title "$c"): $(will "$c")."
      echo "  1. Yes, change this (recommended)"
      echo "  2. No, leave it"
      ask_choice "Your choice" 2
      [ "$CHOICE" = 1 ] && picked+=("$c")
    done
    todo=("${picked[@]+"${picked[@]}"}") ;;
esac
[ ${#todo[@]} -gt 0 ] || { tell "Nothing was changed."; exit 0; }

echo
for c in "${todo[@]}"; do
  tell "Changing: $(title "$c")"
  if apply "$c"; then note_done "$c"; tell "Done: $(title "$c")."
  else tell "Did not finish: $(title "$c"). The lines above say why. The other changes go on."; fi
done
echo
tell "Finished. The rest takes effect at the next start. To put everything back: sudo deploy/headless.sh --undo"
echo
firmware
