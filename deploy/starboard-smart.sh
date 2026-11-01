#!/bin/sh
# Saves each disk's SMART report as JSON for Starboard's Disk health page. Runs as root (smartctl needs it),
# from starboard-smart.timer, every 30 minutes. Starboard only reads the folder, read-only.
#   Install: sudo deploy/install-smart.sh /path/to/folder
set -eu
OUT="${1:?usage: starboard-smart.sh FOLDER}"
mkdir -p "$OUT/current"
for dev in /sys/block/sd* /sys/block/nvme*n*; do
  [ -e "$dev" ] || continue
  name="$(basename "$dev")"
  tmp="$OUT/current/.$name.tmp"
  # -n standby: do not wake sleeping disks just to read them.
  smartctl -x -j -n standby "/dev/$name" > "$tmp" 2>/dev/null || true
  serial="$(sed -n 's/.*"serial_number": *"\([^"]*\)".*/\1/p' "$tmp" | head -n 1 | tr -cd 'A-Za-z0-9_-')"
  if [ -n "$serial" ]; then mv "$tmp" "$OUT/current/$serial.json"; chmod 644 "$OUT/current/$serial.json"; else rm -f "$tmp"; fi
done
