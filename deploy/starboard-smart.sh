#!/bin/sh
# Saves each disk's SMART report as JSON for Starboard's Disk health page. Runs as root (smartctl needs it),
# from starboard-smart.timer every 30 minutes, and from starboard-smart.path when Starboard asks for a reading
# now (an empty file in FOLDER/requests). Also saves the list of drives and partitions (lsblk.json), so
# System, Storage can show drives that are not mounted. Starboard reads the folder, read-only.
#   Install: sudo deploy/install-smart.sh /path/to/folder
set -eu
OUT="${1:?usage: starboard-smart.sh FOLDER}"
mkdir -p "$OUT/current" "$OUT/requests"
rm -f "$OUT/requests/read"
# Drives and partitions: names, sizes, file systems and where they are mounted.
lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,LABEL,MODEL,SERIAL > "$OUT/.lsblk.tmp" 2>/dev/null && mv "$OUT/.lsblk.tmp" "$OUT/lsblk.json" && chmod 644 "$OUT/lsblk.json" || rm -f "$OUT/.lsblk.tmp"
for dev in /sys/block/sd* /sys/block/nvme*n*; do
  [ -e "$dev" ] || continue
  name="$(basename "$dev")"
  tmp="$OUT/current/.$name.tmp"
  # -n standby: do not wake sleeping disks just to read them.
  smartctl -x -j -n standby "/dev/$name" > "$tmp" 2>/dev/null || true
  serial="$(sed -n 's/.*"serial_number": *"\([^"]*\)".*/\1/p' "$tmp" | head -n 1 | tr -cd 'A-Za-z0-9_-')"
  if [ -n "$serial" ]; then mv "$tmp" "$OUT/current/$serial.json"; chmod 644 "$OUT/current/$serial.json"; else rm -f "$tmp"; fi
done
