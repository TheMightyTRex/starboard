#!/usr/bin/env bash
# Walks the Run first script, the installer and the terminal set-up on fresh test machines at the window sizes the
# terminal rules ask for (design system docs/TERMINAL.md, section 10), two machines at a time, and keeps every
# screen (tools/vm/drive.py writes screens.html and result.json for each). sg is hidden first, as on newer Ubuntu.
#
#   tools/vm/rules-matrix.sh [system] [case ...]
#
# Cases: t80x24 t80x30 t140x60 t60x20 (the terminal route at that size), plain (accessible mode), browser (a
# desktop, finishing in the browser), resize (80 by 24, changed in the middle of a step), again (the installer run a
# second time on an installed machine, with its later questions). All of them when none is given. Results go in
# $STARBOARD_VM_DIR/rules/<system>/<case>, so each system keeps its own. The browser case
# stops at the window's last words: the browser part is checked by the browser tests. 7 and 8 November 2026.
set -uo pipefail
cd "$(dirname "$0")/../.."
SYSTEM="${1:-ubuntu2604}"; shift || true
CASES=("$@"); [ ${#CASES[@]} -gt 0 ] || CASES=(t80x24 t80x30 t140x60 t60x20 plain browser resize again)
export STARBOARD_VM_DIR="${STARBOARD_VM_DIR:-/mnt/pool/build-cache/starboard-vm}"
OUT="$STARBOARD_VM_DIR/rules/$SYSTEM"
mkdir -p "$OUT"
KEY="$STARBOARD_VM_DIR/id_ed25519"

one() {
  local name="$1" slot="$2" port web opts=() desktop=0 vm log
  port=$(( 2240 + slot )); web=$(( 18110 + slot ))
  case "$name" in
    t*x*) local size="${name#t}"; opts=(--cols "${size%x*}" --rows "${size#*x}") ;;
    plain) opts=(--plain) ;;
    browser) opts=(--browser --stop-after 'Press q to close it'); desktop=1 ;;
    resize) opts=(--resize-after 3) ;;
    # Installed first with no questions; that run waits for the browser set-up at its end, so it is closed once it
    # gets there (data/starter), and the installer is run again in the window.
    again) opts=(--command 'cat run-first.sh | STARBOARD_REPO=$HOME/starboard.bundle bash -s -- --yes --browser -- --yes >/dev/null 2>&1 & p=$!; until [ -f starboard/data/starter ] || ! kill -0 $p 2>/dev/null; do sleep 5; done; kill $p 2>/dev/null; sleep 2; cd starboard && ./install.sh') ;;
  esac
  log="$OUT/$name.vm.log"
  [ "$slot" = 0 ] || sleep 90  # the two machines start apart: both write the same git bundle when they start
  VM_TAG="rules$slot" VM_SSH_PORT=$port VM_WEB_PORT=$web VM_MEMORY=3584 VM_DESKTOP=$desktop \
    tools/vm/vm.sh new "$SYSTEM" > "$log" 2>&1 &
  vm=$!
  until grep -q '^== READY' "$log" 2>/dev/null || ! kill -0 "$vm" 2>/dev/null; do sleep 5; done
  if ! grep -q '^== READY' "$log"; then echo "$name: the machine did not start (see $log)"; return 1; fi
  ssh -q -p "$port" -i "$KEY" -o StrictHostKeyChecking=no tester@127.0.0.1 \
    "echo \${VM_PASSWORD:-starboard-test-pw} | sudo -S -p '' mv /usr/bin/sg /usr/bin/sg.hidden" 2>/dev/null
  rm -rf "${OUT:?}/$name"
  python3 tools/vm/drive.py --out "$OUT/$name" --port "$port" --key "$KEY" --install basics "${opts[@]}" \
    > "$OUT/$name.drive.log" 2>&1
  echo "$name: $(tail -n 3 "$OUT/$name.drive.log" | tr '\n' ' ')"
  kill "$vm" 2>/dev/null; wait "$vm" 2>/dev/null
}

i=0
while [ "$i" -lt "${#CASES[@]}" ]; do
  one "${CASES[$i]}" 0 &
  a=$!
  b=""
  if [ $(( i + 1 )) -lt "${#CASES[@]}" ]; then one "${CASES[$(( i + 1 ))]}" 1 & b=$!; fi
  wait "$a"; [ -z "$b" ] || wait "$b"
  i=$(( i + 2 ))
done
