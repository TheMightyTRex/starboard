#!/bin/sh
# Installs the SMART report job as a systemd timer. Run once with sudo:
#   sudo deploy/install-smart.sh /home/you/starboard/smart
# Then set STARBOARD_SMART_DIR=/smart in .env and mount the folder read-only in compose.override.yaml.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo"; exit 1; }
OUT="${1:?usage: sudo deploy/install-smart.sh FOLDER}"
command -v smartctl >/dev/null || { echo "Install smartmontools first (apt install smartmontools)"; exit 1; }
install -m 755 "$(dirname "$0")/starboard-smart.sh" /usr/local/bin/starboard-smart
cat > /etc/systemd/system/starboard-smart.service <<UNIT
[Unit]
Description=Save SMART reports for Starboard
[Service]
Type=oneshot
ExecStart=/usr/local/bin/starboard-smart $OUT
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
systemctl daemon-reload
systemctl enable --now starboard-smart.timer
systemctl start starboard-smart.service
echo "Saved reports in $OUT/current. Starboard reads them from STARBOARD_SMART_DIR."
