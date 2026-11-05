#!/bin/sh
# Installs the SMART report job as a systemd timer. Run once with sudo:
#   sudo deploy/install-smart.sh /home/you/starboard/smart
# ./install.sh runs this for you when you say yes to Disk health. To remove the timer again:
#   sudo deploy/install-smart.sh --remove
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo"; exit 1; }
if [ "${1:-}" = "--remove" ]; then
  systemctl disable --now starboard-smart.timer starboard-smart.path 2>/dev/null || true
  rm -f /etc/systemd/system/starboard-smart.timer /etc/systemd/system/starboard-smart.path /etc/systemd/system/starboard-smart.service /usr/local/bin/starboard-smart
  systemctl daemon-reload
  echo "Removed the Disk health timer. The reports already saved stay in their folder."
  exit 0
fi
OUT="${1:?usage: sudo deploy/install-smart.sh FOLDER}"
command -v smartctl >/dev/null || { echo "Install smartmontools first (apt install smartmontools)"; exit 1; }
install -m 755 "$(dirname "$0")/starboard-smart.sh" /usr/local/bin/starboard-smart
cat > /etc/systemd/system/starboard-smart.service <<UNIT
[Unit]
Description=Save SMART reports for Starboard
[Service]
Type=oneshot
ExecStart=/usr/local/bin/starboard-smart "$OUT"
UNIT
cat > /etc/systemd/system/starboard-smart.timer <<UNIT
[Unit]
Description=Save SMART reports for Starboard every 30 minutes
[Timer]
OnBootSec=2min
OnUnitActiveSec=30min
[Install]
WantedBy=timers.target
UNIT
# Read now: Starboard drops an empty file in $OUT/requests (the only place it may write); this runs the job.
mkdir -p "$OUT/requests"
chown -h root:root "$OUT" && chmod 755 "$OUT"  # root's folder: only the requests folder inside is the user's
chown -h "${SUDO_UID:-0}:${SUDO_GID:-0}" "$OUT/requests"
cat > /etc/systemd/system/starboard-smart.path <<UNIT
[Unit]
Description=Read SMART reports when Starboard asks
[Path]
PathExists=$OUT/requests/read
Unit=starboard-smart.service
[Install]
WantedBy=paths.target
UNIT
systemctl daemon-reload
systemctl enable --now starboard-smart.timer starboard-smart.path
systemctl start starboard-smart.service
echo "Saved reports in $OUT/current. Starboard reads them from STARBOARD_SMART_DIR."
