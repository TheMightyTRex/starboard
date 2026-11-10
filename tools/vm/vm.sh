#!/usr/bin/env bash
# Test Starboard's install on a clean Linux system, in a throwaway virtual machine (TEST-PLAN INS and UPD tests).
#
#   tools/vm/vm.sh prepare ubuntu     Download the cloud image once and make a ready system with Docker and git
#   tools/vm/vm.sh test ubuntu        Start a fresh copy of the ready system, install this checkout, run the checks
#   tools/vm/vm.sh shell ubuntu       Start a fresh copy and open a shell in it (for trying things by hand)
#   tools/vm/vm.sh clean ubuntu       Delete that system's files (the downloaded image stays)
#   tools/vm/vm.sh pool debian        Drive pools (DASH-87): a fresh system with five blank virtual drives; adds,
#                                     keeps, erases, balances, parity, take-out, requests, then a restart
#   tools/vm/vm.sh first debian       The Run first script on a bare system with no Docker: checks, installs what
#                                     is missing, downloads this checkout and starts Starboard; then runs it again
#   tools/vm/vm.sh bare debian        A bare system with the Run first script copied in, left running to drive by hand
#   tools/vm/vm.sh new mint           As just installed: a user with a password whose sudo asks for it (on pios, as on
#                                     Raspberry Pi OS, it does not), the Run first script and this checkout copied in,
#                                     left running for tools/vm/drive.py to drive over SSH. VM_DESKTOP=1 adds a
#                                     stand-in browser so the browser route can be tested
#
# VM_TAG=name keeps this run's disk and process files apart, so two sessions can each test a copy of one system.
# VM_SHARE=/mnt/pool shares a host folder read-only (9p, tag "share"): mount -t 9p -o trans=virtio,ro share /mnt/x.
# Used for the migration test, so the test machine sees real media but cannot change it.
# VM_DISKS="2G 3G 4G 2G 1G" adds blank virtual drives (serial numbers SBDISK0001 and up) to shell and test runs.
#
# Supported systems (docs/test-plans/systems.md): mint (Linux Mint 22.3 identity on Ubuntu 24.04's cloud image),
# debian13, ubuntu2604 (Ubuntu Server 26.04), and pios (Raspberry Pi OS: Debian 13 for 64-bit ARM with Raspberry
# Pi's apt repository and /etc/rpi-issue, 4 GB). Older: ubuntu (24.04), debian (12), fedora (42), and arm64 (Debian
# 12 for 64-bit ARM, 1 GB like a small Pi; VM_MEMORY=512 for a Pi Zero 2 W). arm64 needs the packages
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
  mint) URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img" ;;
  debian13) URL="https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2" ;;
  ubuntu2604) URL="https://cloud-images.ubuntu.com/resolute/current/resolute-server-cloudimg-amd64.img" ;;
  pios) URL="https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-arm64.qcow2" ;;
  *) echo "Choose mint, debian13, ubuntu2604, pios, or the older ubuntu, debian, fedora or arm64" >&2; exit 2 ;;
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

if [ "$SYSTEM" = arm64 ] || [ "$SYSTEM" = pios ]; then
  QEMU=qemu-system-aarch64
  FIRMWARE="$(ls /usr/share/qemu-efi-aarch64/QEMU_EFI.fd /usr/share/AAVMF/AAVMF_CODE.fd 2>/dev/null | head -n 1)"
  [ -n "$FIRMWARE" ] && command -v "$QEMU" >/dev/null || { echo "Install qemu-system-arm and qemu-efi-aarch64 first" >&2; exit 1; }
  # shellcheck disable=SC2054  # the commas are inside one option value
  ACCEL=(-machine virt -accel tcg,thread=multi -cpu cortex-a72 -bios "$FIRMWARE"); SPEED="emulated 64-bit ARM (slow)"
  if [ "$SYSTEM" = pios ]; then MEMORY="${MEMORY:-4096}"; else MEMORY="${MEMORY:-1024}"; fi; WAIT=3600
else
  QEMU=qemu-system-x86_64
  if [ -w /dev/kvm ]; then ACCEL=(-accel kvm -cpu host); SPEED="KVM"; else ACCEL=(-accel tcg -cpu max); SPEED="software only (slow)"; fi
  MEMORY="${MEMORY:-2048}"; WAIT=1200
fi
SSH=(ssh -q -i "$KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 tester@127.0.0.1)
SCP=(scp -q -i "$KEY" -P "$SSH_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
say() { printf '\n== %s\n' "$*"; }

seed() { # cloud-init: a tester user with the key, Docker and git (with "bare": the user only; "new": as just installed)
  local user="$DIR/user-data" seediso="$DIR/$SYSTEM-seed${1:+-$1}.iso"
  if [ "${1:-}" = new ]; then
    # As just installed: the user's sudo asks for the password, except on Raspberry Pi OS, whose first user's does
    # not. The password is a test value for these throwaway machines only.
    local sudo_rule="ALL=(ALL) ALL"; [ "$SYSTEM" = pios ] && sudo_rule="ALL=(ALL) NOPASSWD:ALL"
    cat > "$user" <<EOF
#cloud-config
hostname: starboard-test
users:
  - name: tester
    sudo: "$sudo_rule"
    shell: /bin/bash
    lock_passwd: false
    ssh_authorized_keys: [$(cat "$KEY.pub")]
chpasswd:
  expire: false
  users:
    - {name: tester, password: ${VM_PASSWORD:-starboard-test-pw}, type: text}
EOF
    case "$SYSTEM" in
      mint) # Linux Mint 22.3's identity on its Ubuntu 24.04 base, and no snaps, as on Mint
        cat >> "$user" <<'EOF'
write_files:
  - path: /usr/lib/os-release.mint
    content: |
      NAME="Linux Mint"
      VERSION="22.3 (Zena)"
      ID=linuxmint
      ID_LIKE="ubuntu debian"
      PRETTY_NAME="Linux Mint 22.3"
      VERSION_ID="22.3"
      VERSION_CODENAME=zena
      UBUNTU_CODENAME=noble
runcmd:
  - [sh, -c, "mv /usr/lib/os-release.mint /usr/lib/os-release && ln -sf ../usr/lib/os-release /etc/os-release"]
  - [sh, -c, "snap list 2>/dev/null | awk 'NR>1 {print $1}' | xargs -r -n1 snap remove --purge; apt-get purge -y snapd || true"]
  - [touch, /var/lib/starboard-new]
EOF
        ;;
      pios) # The file Raspberry Pi OS is recognised by. Raspberry Pi's own software source is left out: its signing key
        # fails Debian 13's checks on this emulated system (see os-tests/FINDINGS.md), which a real Pi may not share.
        cat >> "$user" <<'EOF'
write_files:
  - path: /etc/rpi-issue
    content: |
      Raspberry Pi reference 2026-10-01 (emulated for Starboard tests)
runcmd:
  - [touch, /var/lib/starboard-new]
EOF
        ;;
      *) printf '%s\n' "runcmd:" "  - [touch, /var/lib/starboard-new]" >> "$user" ;;
    esac
    cloud-localds "$seediso" "$user"
    echo "$seediso"
    return
  fi
  if [ "${1:-}" = bare ]; then
    printf '%s\n' "#cloud-config" "hostname: starboard-test" "users:" "  - name: tester" \
      "    sudo: ALL=(ALL) NOPASSWD:ALL" "    shell: /bin/bash" "    ssh_authorized_keys: [$(cat "$KEY.pub")]" > "$user"
    cloud-localds "$seediso" "$user"
    echo "$seediso"
    return
  fi
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
  "$QEMU" "${ACCEL[@]}" -smp "${VM_CPUS:-2}" -m "$MEMORY" -nographic -serial "file:$LOG" -monitor none \
    -drive "file=$disk,if=none,id=system,format=qcow2" -device virtio-blk-pci,drive=system,bootindex=0 \
    -nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:$SSH_PORT-:22,hostfwd=tcp:127.0.0.1:$WEB_PORT-:8095" \
    ${VM_SHARE:+-virtfs "local,path=$VM_SHARE,mount_tag=share,security_model=none,readonly=on"} \
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

  first)
    if [ ! -f "$BASE" ]; then say "Downloading the $SYSTEM cloud image"; curl -fL --progress-bar -o "$BASE.part" "$URL"; mv "$BASE.part" "$BASE"; fi
    rm -f "$RUN"
    qemu-img create -q -f qcow2 -F qcow2 -b "$BASE" "$RUN" 12G
    say "Starting a bare $SYSTEM with no Docker ($SPEED)"
    boot "$RUN" -drive "file=$(seed bare),if=virtio,format=raw,readonly=on"
    trap stop EXIT
    wait_ssh $((WAIT * 2))
    "${SSH[@]}" "cloud-init status --wait >/dev/null 2>&1 || true"
    PASS=0; FAIL=0
    check() { # check ID "what" command...
      local id="$1" what="$2"; shift 2
      if "$@" >/dev/null 2>&1; then echo "PASS $id $what"; PASS=$((PASS + 1)); else echo "FAIL $id $what"; FAIL=$((FAIL + 1)); fi
    }
    vm() { "${SSH[@]}" "$@"; }
    not_vm() { ! vm "$@"; }
    web() { curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:$WEB_PORT$1"; }
    wait_web() { for _ in $(seq 1 120); do [ "$(web /healthz)" = 200 ] && return 0; sleep 5; done; return 1; }
    RF="STARBOARD_REPO=~/starboard.bundle bash run-first.sh"

    say "Copying the Run first script and this checkout ($(git rev-parse --short HEAD)) into the VM"
    git bundle create -q "$DIR/starboard.bundle" HEAD
    "${SCP[@]}" "$DIR/starboard.bundle" run-first.sh tester@127.0.0.1:

    say "FIRST-01 check only, on a bare system"
    check FIRST-01 "--check says something is missing" not_vm "$RF --check"
    check FIRST-01 "--check changed nothing" not_vm "command -v docker"

    say "FIRST-02 install what is missing, download, start the installer"
    vm "$RF --yes --browser -- --yes" | tail -n 12 || echo "     That step failed: the checks below show what it broke"
    check FIRST-02 "Docker installed" vm "command -v docker"
    check FIRST-02 "Docker Compose installed" vm "docker compose version"
    check FIRST-02 "Docker running" vm "systemctl is-active --quiet docker"
    check FIRST-02 "tester allowed to use Docker" vm "getent group docker | grep -qw tester"
    check FIRST-02 "Starboard downloaded" vm "test -d starboard/.git"
    check FIRST-02 "Starboard starts and answers /healthz" wait_web
    check FIRST-02 "setup code written" vm "test -s starboard/data/setup-token"

    say "FIRST-03 run it again: nothing to install"
    check FIRST-03 "--check says everything is here" vm "$RF --check"
    check FIRST-03 "a second run starts the installer again" vm "$RF --yes --browser -- --yes | grep -q 'Starboard is running'"
    check FIRST-03 "and Starboard still answers" wait_web

    say "$SYSTEM Run first script: $PASS passed, $FAIL failed"
    [ "$FAIL" = 0 ]
    ;;

  new)
    # As just installed, with the user just signed in: no Docker, no git, the Run first script and this checkout
    # copied in. VM_DESKTOP=1 adds a stand-in browser (xdg-open writes the address it was given to ~/opened-urls),
    # as on a desktop computer. Stops when this command is stopped.
    if [ ! -f "$BASE" ]; then say "Downloading the $SYSTEM cloud image"; curl -fL --progress-bar -o "$BASE.part" "$URL"; mv "$BASE.part" "$BASE"; fi
    rm -f "$RUN"
    qemu-img create -q -f qcow2 -F qcow2 -b "$BASE" "$RUN" "${VM_SIZE:-64G}"
    say "Starting a newly installed $SYSTEM ($SPEED, $MEMORY MB)"
    boot "$RUN" -drive "file=$(seed new),if=virtio,format=raw,readonly=on"
    trap stop EXIT
    wait_ssh $((WAIT * 2))
    until "${SSH[@]}" test -f /var/lib/starboard-new 2>/dev/null; do sleep 10; done
    git bundle create -q "$DIR/starboard.bundle" HEAD
    "${SCP[@]}" "$DIR/starboard.bundle" run-first.sh tester@127.0.0.1:
    if [ "${VM_DESKTOP:-0}" = 1 ]; then
      "${SSH[@]}" 'mkdir -p ~/.local/bin && printf "%s\n" "#!/bin/sh" "echo \"\$*\" >> \$HOME/opened-urls" > ~/.local/bin/xdg-open && chmod +x ~/.local/bin/xdg-open'
    fi
    say "READY: ssh -tt -i $KEY -p $SSH_PORT tester@127.0.0.1"
    while kill -0 "$(cat "$PID")" 2>/dev/null; do sleep 5; done
    ;;

  bare)
    # A bare system with this checkout and the Run first script copied in, left running for a person or a capture
    # tool to drive over SSH (ssh -tt). Stops when this command is stopped.
    if [ ! -f "$BASE" ]; then say "Downloading the $SYSTEM cloud image"; curl -fL --progress-bar -o "$BASE.part" "$URL"; mv "$BASE.part" "$BASE"; fi
    rm -f "$RUN"
    qemu-img create -q -f qcow2 -F qcow2 -b "$BASE" "$RUN" 12G
    say "Starting a bare $SYSTEM with no Docker ($SPEED)"
    boot "$RUN" -drive "file=$(seed bare),if=virtio,format=raw,readonly=on"
    trap stop EXIT
    wait_ssh $((WAIT * 2))
    "${SSH[@]}" "cloud-init status --wait >/dev/null 2>&1 || true"
    git bundle create -q "$DIR/starboard.bundle" HEAD
    "${SCP[@]}" "$DIR/starboard.bundle" run-first.sh tester@127.0.0.1:
    say "READY: ssh -tt -i $KEY -p $SSH_PORT tester@127.0.0.1"
    while kill -0 "$(cat "$PID")" 2>/dev/null; do sleep 5; done
    ;;

  clean)
    rm -f "$READY" "$RUN" "$DIR/$SYSTEM-seed.iso" "$DIR/$SYSTEM-seed-"*.iso "$DIR/user-data" "$LOG" "$DIR/$SYSTEM"*-drive*.qcow2
    echo "Removed the $SYSTEM VM files (the downloaded image stays: $BASE)"
    ;;

  *) sed -n '2,17p' "$0"; exit 2 ;;
esac
