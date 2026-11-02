#!/bin/sh
# Saves each disk's SMART report as JSON for Starboard's Disk health page. Runs as root (smartctl needs it),
# from starboard-smart.timer every 30 minutes, and from starboard-smart.path when Starboard asks for a reading
# now (an empty file in FOLDER/requests). Also saves the list of drives and partitions (lsblk.json), so
# System, Storage can show drives that are not mounted. Starboard reads the folder, read-only.
#   Install: sudo deploy/install-smart.sh /path/to/folder
set -eu
OUT="${1:?usage: starboard-smart.sh FOLDER}"
# This runs as root in a folder its owner can write to, so it never follows a link someone planted there:
# reports are made in a private temporary folder and renamed into place (a rename replaces a link, it does not
# write through it), and the folders it writes in must be real folders.
for d in "$OUT" "$OUT/current"; do
  if [ -L "$d" ]; then echo "Stopped: $d is a link"; exit 1; fi
done
mkdir -p "$OUT/current" "$OUT/requests"
chown root:root "$OUT/current" && chmod 755 "$OUT/current"
rm -f "$OUT/requests/read"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# Drives and partitions: names, sizes, file systems and where they are mounted.
if lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,LABEL,MODEL,SERIAL > "$WORK/lsblk.json" 2>/dev/null; then
  chmod 644 "$WORK/lsblk.json"
  mv -f "$WORK/lsblk.json" "$OUT/lsblk.json"
fi
for dev in /sys/block/sd* /sys/block/nvme*n*; do
  [ -e "$dev" ] || continue
  name="$(basename "$dev")"
  tmp="$WORK/$name.json"
  # -n standby: do not wake sleeping disks just to read them.
  smartctl -x -j -n standby "/dev/$name" > "$tmp" 2>/dev/null || true
  serial="$(sed -n 's/.*"serial_number": *"\([^"]*\)".*/\1/p' "$tmp" | head -n 1 | tr -cd 'A-Za-z0-9_-')"
  if [ -n "$serial" ]; then chmod 644 "$tmp"; mv -f "$tmp" "$OUT/current/$serial.json"; fi
done
