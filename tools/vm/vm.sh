#!/usr/bin/env bash
# Test Starboard's install on a clean Linux system, in a throwaway virtual machine (TEST-PLAN INS and UPD tests).
#
#   tools/vm/vm.sh prepare ubuntu     Download the cloud image once and make a ready system with Docker and git
#   tools/vm/vm.sh test ubuntu        Start a fresh copy of the ready system, install this checkout, run the checks
#   tools/vm/vm.sh shell ubuntu       Start a fresh copy and open a shell in it (for trying things by hand)
#   tools/vm/vm.sh clean ubuntu       Delete that system's files (the downloaded image stays)
#
# Systems: ubuntu (24.04), debian (12), fedora (42). Plain QEMU with user networking: no root, no libvirt,
# nothing on the home network. Hardware speed-up (KVM) is used when /dev/kvm exists; without it everything
# still works, about ten times slower. Files live in ~/.cache/starboard-vm (STARBOARD_VM_DIR), never in the repo.
# Each test starts from the ready system, so nothing from one run reaches the next.
set -euo pipefail

cd "$(dirname "$0")/../.."
REPO="$PWD"
DIR="${STARBOARD_VM_DIR:-$HOME/.cache/starboard-vm}"
SSH_PORT="${VM_SSH_PORT:-2222}"
WEB_PORT="${VM_WEB_PORT:-18095}"
MEMORY="${VM_MEMORY:-2048}"
ACTION="${1:-}"
SYSTEM="${2:-ubuntu}"

case "$SYSTEM" in
  ubuntu) URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img" ;;
  debian) URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2" ;;
  fedora) URL="https://download.fedoraproject.org/pub/fedora/linux/releases/42/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-42-1.1.x86_64.qcow2" ;;
  *) echo "Choose ubuntu, debian or fedora" >&2; exit 2 ;;
esac

mkdir -p "$DIR"
chmod 700 "$DIR"
BASE="$DIR/$SYSTEM-cloud.img"
READY="$DIR/$SYSTEM-ready.qcow2"
RUN="$DIR/$SYSTEM-run.qcow2"
KEY="$DIR/id_ed25519"
LOG="$DIR/$SYSTEM-console.log"
[ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N "" -C starboard-vm -f "$KEY"

if [ -w /dev/kvm ]; then ACCEL=(-accel kvm -cpu host); SPEED="KVM"; else ACCEL=(-accel tcg -cpu max); SPEED="software only (slow)"; fi
SSH=(ssh -q -i "$KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 tester@127.0.0.1)
SCP=(scp -q -i "$KEY" -P "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
say() { printf '\n== %s\n' "$*"; }

seed() { # cloud-init: a tester user with the key, Docker and git
  local user="$DIR/user-data" seediso="$DIR/$SYSTEM-seed.iso"
  cat > "$user" <<EOF
#cloud-config
hostname: starboard-test
users:
  - name: tester
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    ssh_authorized_keys: [$(cat "$KEY.pub")]
package_update: true
packages: [git, curl, python3]
runcmd:
  - [sh, -c, "curl -fsSL https://get.docker.com | sh"]
  - [sh, -c, "usermod -aG docker tester && systemctl enable --now docker"]
  - [sh, -c, "touch /var/lib/starboard-ready"]
EOF
  cloud-localds "$seediso" "$user"
  echo "$seediso"
}

boot() { # boot a disk in the background; extra arguments go to QEMU
  local disk="$1"; shift
  qemu-system-x86_64 "${ACCEL[@]}" -smp 2 -m "$MEMORY" -nographic -serial "file:$LOG" -monitor none \
    -drive "file=$disk,if=virtio,format=qcow2" \
    -nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:$SSH_PORT-:22,hostfwd=tcp:127.0.0.1:$WEB_PORT-:8095" \
    "$@" >/dev/null 2>&1 &
  echo $! > "$DIR/$SYSTEM.pid"
}

stop() {
  local pid; pid="$(cat "$DIR/$SYSTEM.pid" 2>/dev/null || true)"
  [ -n "$pid" ] || return 0
  "${SSH[@]}" sudo poweroff >/dev/null 2>&1 || true
  for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 2; done
  kill "$pid" 2>/dev/null || true
  rm -f "$DIR/$SYSTEM.pid"
}

wait_ssh() { # up to $1 seconds
  local until=$((SECONDS + $1))
  until "${SSH[@]}" true 2>/dev/null; do
    [ $SECONDS -lt $until ] || { echo "No answer over SSH; the console log is $LOG" >&2; return 1; }
    sleep 5
  done
}

fresh() { # a new copy of the ready system, started
  [ -f "$READY" ] || { echo "Run: tools/vm/vm.sh prepare $SYSTEM" >&2; exit 1; }
  rm -f "$RUN"
  qemu-img create -q -f qcow2 -F qcow2 -b "$READY" "$RUN"
  say "Starting a fresh $SYSTEM ($SPEED)"
  boot "$RUN"
  trap stop EXIT
  wait_ssh 1200
}

case "$ACTION" in
  prepare)
    if [ ! -f "$BASE" ]; then say "Downloading the $SYSTEM cloud image"; curl -fL --progress-bar -o "$BASE.part" "$URL"; mv "$BASE.part" "$BASE"; fi
    rm -f "$READY"
    qemu-img create -q -f qcow2 -F qcow2 -b "$BASE" "$READY" 12G
    say "First start: installing Docker and git ($SPEED; this can take a while)"
    boot "$READY" -drive "file=$(seed),if=virtio,format=raw,readonly=on"
    trap stop EXIT
    wait_ssh 2400
    until "${SSH[@]}" test -f /var/lib/starboard-ready; do sleep 10; done
    "${SSH[@]}" "docker --version && docker compose version && git --version"
    "${SSH[@]}" "sudo cloud-init clean --logs >/dev/null 2>&1 || true"
    say "Ready: $READY"
    ;;

  shell)
    fresh
    "${SSH[@]/-q/-t}"
    ;;

  test)
    fresh
    PASS=0; FAIL=0
    check() { # check ID "what" command...
      local id="$1" what="$2"; shift 2
      if "$@" >/dev/null 2>&1; then echo "PASS $id $what"; PASS=$((PASS + 1)); else echo "FAIL $id $what"; FAIL=$((FAIL + 1)); fi
    }
    vm() { "${SSH[@]}" "$@"; }
    web() { curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:$WEB_PORT$1"; }
    wait_web() { for _ in $(seq 1 120); do [ "$(web /healthz)" = 200 ] && return 0; sleep 5; done; return 1; }

    say "Copying this checkout ($(git rev-parse --short HEAD)) into the VM"
    git bundle create -q "$DIR/starboard.bundle" HEAD
    "${SCP[@]}" "$DIR/starboard.bundle" tester@127.0.0.1:starboard.bundle
    vm "git clone -q starboard.bundle starboard"

    say "INS-02 installer, answering No to everything"
    vm "cd starboard && ./install.sh --yes --no-docker --no-disks --no-app-use --no-livetv --no-disk-health" | tail -n 8
    check INS-02 "starts and answers /healthz" wait_web
    check INS-02 "first visit goes to set-up" test "$(web /index.html)" = 303
    check INS-02 "setup code written" vm "test -s starboard/data/setup-token"
    check INS-02 ".env readable by the owner only" vm "test \$(stat -c %a starboard/.env) = 600"
    check INS-02 "data folder private" vm "test \$(stat -c %a starboard/data) = 700"
    check INS-02 "no Docker socket mounted" vm "! docker inspect starboard --format '{{range .Mounts}}{{.Source}} {{end}}' | grep -q docker.sock"
    check SEC-01 "API refuses without signing in" test "$(web /api/config)" = 401
    check SEC-10 "another host name refused" test "$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: evil.example' "http://127.0.0.1:$WEB_PORT/healthz")" != 200
    MEM="$(vm "docker stats --no-stream --format '{{.MemUsage}}' starboard" | cut -d/ -f1)"
    echo "     idle memory: $MEM"

    say "INS-05 run the installer again with Docker access"
    TOKEN="$(vm "cat starboard/data/setup-token")"
    vm "cd starboard && ./install.sh --yes --docker" | tail -n 3
    check INS-05 "starts again" wait_web
    check INS-05 "setup code kept" test "$(vm "cat starboard/data/setup-token")" = "$TOKEN"
    check INS-03 "Docker socket mounted when asked" vm "docker inspect starboard --format '{{range .Mounts}}{{.Source}} {{end}}' | grep -q docker.sock"

    say "INS-06 this computer only"
    check INS-06 "a re-run with --local-only says to use Settings" vm "cd starboard && ./install.sh --yes --local-only | grep -q 'Settings, Security'"
    vm "cd starboard && docker compose down" >/dev/null 2>&1
    vm "git clone -q starboard.bundle local-only && cd local-only && ./install.sh --yes --local-only --no-docker" | tail -n 2
    check INS-06 "answers inside the VM" vm "for i in \$(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:8095/healthz && exit 0; sleep 5; done; exit 1"
    check INS-06 "refused from outside the VM" test "$(web /healthz)" != 200
    vm "cd local-only && docker compose down" >/dev/null 2>&1

    say "UPD-01 update check"
    vm "cd starboard && git remote set-url origin https://github.com/TheMightyTRex/starboard.git"
    check UPD-01 "./update.sh --check runs" vm "cd starboard && ./update.sh --check"

    say "INS-01 the ready-made image"
    vm "mkdir -p ~/image/data && cp compose.image.yaml ~/image/ && cd ~/image && docker compose -f compose.image.yaml up -d" | tail -n 2
    check INS-01 "published image starts" wait_web
    check INS-01 "setup code in the log" vm "docker logs starboard 2>&1 | grep -qi 'setup code'"

    say "$SYSTEM: $PASS passed, $FAIL failed"
    [ "$FAIL" = 0 ]
    ;;

  clean)
    rm -f "$READY" "$RUN" "$DIR/$SYSTEM-seed.iso" "$LOG"
    echo "Removed the $SYSTEM VM files (the downloaded image stays: $BASE)"
    ;;

  *) sed -n '2,12p' "$0"; exit 2 ;;
esac
