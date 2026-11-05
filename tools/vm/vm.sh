#!/usr/bin/env bash
# Test Starboard's install on a clean Linux system, in a throwaway virtual machine (TEST-PLAN INS and UPD tests).
#
#   tools/vm/vm.sh prepare ubuntu     Download the cloud image once and make a ready system with Docker and git
#   tools/vm/vm.sh test ubuntu        Start a fresh copy of the ready system, install this checkout, run the checks
#   tools/vm/vm.sh shell ubuntu       Start a fresh copy and open a shell in it (for trying things by hand)
#   tools/vm/vm.sh clean ubuntu       Delete that system's files (the downloaded image stays)
#   tools/vm/vm.sh pool debian        Drive pools (DASH-87): a fresh system with five blank virtual drives; adds,
#                                     keeps, erases, balances, parity, take-out, requests, then a restart
#
# VM_TAG=name keeps this run's disk and process files apart, so two sessions can each test a copy of one system.
# VM_DISKS="2G 3G 4G 2G 1G" adds blank virtual drives (serial numbers SBDISK0001 and up) to shell and test runs.
#
# Systems: ubuntu (24.04), debian (12), fedora (42), and arm64: Debian 12 for 64-bit ARM, like Raspberry Pi
# OS (64-bit), with 1 GB of memory like a small Pi (VM_MEMORY=512 for a Pi Zero 2 W). arm64 needs the packages
# qemu-system-arm and qemu-efi-aarch64, and is always emulated, so slow. Plain QEMU with user networking: no root, no libvirt,
# nothing on the home network. Hardware speed-up (KVM) is used when /dev/kvm exists; without it everything
# still works, about ten times slower. Files live in ~/.cache/starboard-vm (STARBOARD_VM_DIR), never in the repo.
# Each test starts from the ready system, so nothing from one run reaches the next.
set -euo pipefail

cd "$(dirname "$0")/../.."
DIR="${STARBOARD_VM_DIR:-$HOME/.cache/starboard-vm}"
SSH_PORT="${VM_SSH_PORT:-2222}"
WEB_PORT="${VM_WEB_PORT:-18095}"
MEMORY="${VM_MEMORY:-}"
ACTION="${1:-}"
SYSTEM="${2:-ubuntu}"

case "$SYSTEM" in
  ubuntu) URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img" ;;
  debian) URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2" ;;
  fedora) URL="https://download.fedoraproject.org/pub/fedora/linux/releases/42/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-42-1.1.x86_64.qcow2" ;;
  arm64) URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-arm64.qcow2" ;;
  *) echo "Choose ubuntu, debian, fedora or arm64" >&2; exit 2 ;;
esac

mkdir -p "$DIR"
chmod 700 "$DIR"
BASE="$DIR/$SYSTEM-cloud.img"
READY="$DIR/$SYSTEM-ready.qcow2"
RUN="$DIR/$SYSTEM${VM_TAG:+-$VM_TAG}-run.qcow2"
PID="$DIR/$SYSTEM${VM_TAG:+-$VM_TAG}.pid"
VM_DISKS="${VM_DISKS:-}"
KEY="$DIR/id_ed25519"
LOG="$DIR/$SYSTEM${VM_TAG:+-$VM_TAG}-console.log"
[ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N "" -C starboard-vm -f "$KEY"

if [ "$SYSTEM" = arm64 ]; then
  QEMU=qemu-system-aarch64
  FIRMWARE="$(ls /usr/share/qemu-efi-aarch64/QEMU_EFI.fd /usr/share/AAVMF/AAVMF_CODE.fd 2>/dev/null | head -n 1)"
  [ -n "$FIRMWARE" ] && command -v "$QEMU" >/dev/null || { echo "Install qemu-system-arm and qemu-efi-aarch64 first" >&2; exit 1; }
  # shellcheck disable=SC2054  # the commas are inside one option value
  ACCEL=(-machine virt -accel tcg,thread=multi -cpu cortex-a72 -bios "$FIRMWARE"); SPEED="emulated 64-bit ARM (slow)"
  MEMORY="${MEMORY:-1024}"; WAIT=3600
else
  QEMU=qemu-system-x86_64
  if [ -w /dev/kvm ]; then ACCEL=(-accel kvm -cpu host); SPEED="KVM"; else ACCEL=(-accel tcg -cpu max); SPEED="software only (slow)"; fi
  MEMORY="${MEMORY:-2048}"; WAIT=1200
fi
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
  "$QEMU" "${ACCEL[@]}" -smp 2 -m "$MEMORY" -nographic -serial "file:$LOG" -monitor none \
    -drive "file=$disk,if=virtio,format=qcow2" \
    -nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:$SSH_PORT-:22,hostfwd=tcp:127.0.0.1:$WEB_PORT-:8095" \
    "$@" >/dev/null 2>&1 &
  echo $! > "$PID"
}

stop() {
  local pid; pid="$(cat "$PID" 2>/dev/null || true)"
  [ -n "$pid" ] || return 0
  "${SSH[@]}" sudo poweroff >/dev/null 2>&1 || true
  for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 2; done
  kill "$pid" 2>/dev/null || true
  rm -f "$PID"
}

spare_drives() { # blank virtual drives, made fresh for each run: QEMU options on stdout
  local n=0 size file
  for size in $VM_DISKS; do
    n=$((n + 1))
    file="$DIR/$SYSTEM${VM_TAG:+-$VM_TAG}-drive$n.qcow2"
    rm -f "$file"
    qemu-img create -q -f qcow2 "$file" "$size"
    printf -- '-drive\nfile=%s,if=none,id=spare%d,format=qcow2\n-device\nvirtio-blk-pci,drive=spare%d,serial=SBDISK%04d\n' "$file" "$n" "$n" "$n"
  done
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
  say "Starting a fresh $SYSTEM ($SPEED)${VM_DISKS:+, with blank drives: $VM_DISKS}"
  local extra=()
  if [ -n "$VM_DISKS" ]; then mapfile -t extra < <(spare_drives); fi
  boot "$RUN" "${extra[@]+"${extra[@]}"}"
  trap stop EXIT
  wait_ssh "$WAIT"
}

case "$ACTION" in
  prepare)
    if [ ! -f "$BASE" ]; then say "Downloading the $SYSTEM cloud image"; curl -fL --progress-bar -o "$BASE.part" "$URL"; mv "$BASE.part" "$BASE"; fi
    rm -f "$READY"
    qemu-img create -q -f qcow2 -F qcow2 -b "$BASE" "$READY" 12G
    say "First start: installing Docker and git ($SPEED; this can take a while)"
    boot "$READY" -drive "file=$(seed),if=virtio,format=raw,readonly=on"
    trap stop EXIT
    wait_ssh $((WAIT * 2))
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
    vm "cd starboard && ./install.sh --yes --no-docker --no-disks --no-app-use --no-livetv --no-disk-health" | tail -n 8 || echo "     That step failed: the checks below show what it broke"
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
    vm "cd starboard && ./install.sh --yes --docker" | tail -n 3 || echo "     That step failed: the checks below show what it broke"
    check INS-05 "starts again" wait_web
    check INS-05 "setup code kept" test "$(vm "cat starboard/data/setup-token")" = "$TOKEN"
    check INS-03 "Docker socket mounted when asked" vm "docker inspect starboard --format '{{range .Mounts}}{{.Source}} {{end}}' | grep -q docker.sock"

    say "INS-06 this computer only"
    check INS-06 "a re-run with --local-only says to use Settings" vm "cd starboard && ./install.sh --yes --local-only | grep -q 'Settings, Security'"
    vm "cd starboard && docker compose down" >/dev/null 2>&1
    vm "git clone -q starboard.bundle local-only && cd local-only && ./install.sh --yes --local-only --no-docker" | tail -n 2 || echo "     That step failed: the checks below show what it broke"
    check INS-06 "answers inside the VM" vm "for i in \$(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:8095/healthz && exit 0; sleep 5; done; exit 1"
    check INS-06 "refused from outside the VM" test "$(web /healthz)" != 200
    vm "cd local-only && docker compose down" >/dev/null 2>&1

    say "UPD-01 update check"
    vm "cd starboard && git remote set-url origin https://github.com/TheMightyTRex/starboard.git"
    check UPD-01 "./update.sh --check runs" vm "cd starboard && ./update.sh --check"

    say "INS-01 the ready-made image"
    vm "mkdir -p ~/image/data && cp starboard/compose.image.yaml ~/image/ && cd ~/image && docker compose -f compose.image.yaml up -d" | tail -n 2 || echo "     That step failed: the checks below show what it broke"
    check INS-01 "published image starts" wait_web
    check INS-01 "setup code in the log" vm "docker logs starboard 2>&1 | grep -qi 'setup code'"

    say "$SYSTEM: $PASS passed, $FAIL failed"
    [ "$FAIL" = 0 ]
    ;;

  pool)
    VM_DISKS="${VM_DISKS:-2G 3G 4G 2G 1G}"
    fresh
    say "Copying this checkout ($(git rev-parse --short HEAD)) into the VM"
    tar czf "$DIR/starboard-pool.tgz" --exclude=.git --exclude=data --exclude=docs/screenshots .
    "${SCP[@]}" "$DIR/starboard-pool.tgz" tester@127.0.0.1:starboard.tgz
    "${SSH[@]}" "mkdir -p starboard && tar xzf starboard.tgz -C starboard"
    "${SSH[@]}" "cd starboard && bash tools/vm/pool-test.sh before" | tee "$DIR/pool-test.log"
    say "Restarting the VM, to check the pool comes back by itself"
    "${SSH[@]}" "sudo systemctl reboot" >/dev/null 2>&1 || true
    sleep 20
    wait_ssh "$WAIT"
    "${SSH[@]}" "cd starboard && bash tools/vm/pool-test.sh after" | tee -a "$DIR/pool-test.log"
    passed=$(grep -c '^PASS' "$DIR/pool-test.log"); failed=$(grep -c '^FAIL' "$DIR/pool-test.log" || true)
    say "$SYSTEM pool: $passed passed, $failed failed (log: $DIR/pool-test.log)"
    [ "$failed" = 0 ]
    ;;

  clean)
    rm -f "$READY" "$RUN" "$DIR/$SYSTEM-seed.iso" "$LOG" "$DIR/$SYSTEM"*-drive*.qcow2
    echo "Removed the $SYSTEM VM files (the downloaded image stays: $BASE)"
    ;;

  *) sed -n '2,17p' "$0"; exit 2 ;;
esac
