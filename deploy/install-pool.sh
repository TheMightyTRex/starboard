#!/bin/sh
# Installs Starboard's drive pool helper (DASH-87). Run once with sudo:
#   sudo deploy/install-pool.sh /home/you/starboard/pool
# ./install.sh runs this for you when you say yes to Drive pools. To remove the helper again:
#   sudo deploy/install-pool.sh --remove
# The helper (/usr/local/bin/starboard-pool) runs as root. Starboard never does: it drops a request in
# FOLDER/requests, the one place it may write, and reads the answers in FOLDER/status. The helper accepts only a
# fixed list of actions, plans every change first, and erases a drive only with the end of its serial number.
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo"; exit 1; }
UNITS="starboard-pool.path starboard-pool.service starboard-pool-nightly.timer starboard-pool-nightly.service"
if [ "${1:-}" = "--remove" ]; then
  for u in $UNITS; do systemctl disable --now "$u" 2>/dev/null || true; rm -f "/etc/systemd/system/$u"; done
  rm -f /usr/local/bin/starboard-pool
  systemctl daemon-reload
  echo "Removed the pool helper. The pool, its drives and Starboard's lines in /etc/fstab stay as they are;"
  echo "saved copies of the files it changed are in /var/lib/starboard-pool/saved."
  exit 0
fi
OUT="${1:?usage: sudo deploy/install-pool.sh FOLDER}"
command -v python3 >/dev/null || { echo "Install python3 first (apt install python3)"; exit 1; }
missing=""
for t in mergerfs rsync sgdisk; do command -v "$t" >/dev/null || missing="$missing $t"; done
if [ -n "$missing" ]; then
  echo "The pool needs:$missing. Install them first, for example: sudo apt install mergerfs rsync gdisk"
  echo "(and snapraid for a parity drive)"
  exit 1
fi
case "$OUT" in /*) ;; *) echo "Give the folder as a full path, starting with /"; exit 1 ;; esac
[ -L "$OUT" ] && { echo "Stopped: $OUT is a link"; exit 1; }
install -m 755 "$(dirname "$0")/../starboard/pool_helper.py" /usr/local/bin/starboard-pool
mkdir -p /var/lib/starboard-pool && chmod 700 /var/lib/starboard-pool
printf '{"folder": "%s"}\n' "$OUT" > /var/lib/starboard-pool/exchange.json
mkdir -p "$OUT/requests" "$OUT/status"
chown "${SUDO_UID:-0}:${SUDO_GID:-0}" "$OUT" "$OUT/requests"
chmod 700 "$OUT/requests"
chown root:root "$OUT/status" && chmod 755 "$OUT/status"
cat > /etc/systemd/system/starboard-pool.service <<UNIT
[Unit]
Description=Answer Starboard's drive pool requests
[Service]
Type=oneshot
ExecStart=/usr/local/bin/starboard-pool serve "$OUT"
NoNewPrivileges=yes
PrivateTmp=yes
UNIT
cat > /etc/systemd/system/starboard-pool.path <<UNIT
[Unit]
Description=Watch for Starboard's drive pool requests
[Path]
PathExistsGlob=$OUT/requests/*.json
Unit=starboard-pool.service
[Install]
WantedBy=paths.target
UNIT
cat > /etc/systemd/system/starboard-pool-nightly.service <<UNIT
[Unit]
Description=Starboard's nightly parity check and copy for the backup drives
RequiresMountsFor=/mnt/pool
[Service]
Type=oneshot
Nice=19
IOSchedulingClass=idle
ExecStart=/usr/local/bin/starboard-pool nightly
UNIT
cat > /etc/systemd/system/starboard-pool-nightly.timer <<UNIT
[Unit]
Description=Run Starboard's backup drive check every night
[Timer]
OnCalendar=*-*-* 02:00
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now starboard-pool.path
systemctl start starboard-pool.service
echo "Installed the pool helper. Starboard reads its answers from $OUT/status (STARBOARD_POOL_DIR)."
