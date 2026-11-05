#!/usr/bin/env bash
# Drive pools (DASH-87), inside a throwaway VM with blank virtual drives: tools/vm/vm.sh pool debian runs this twice,
#   bash tools/vm/pool-test.sh before   adds, keeps, erases, balances, parity, take-out and a request from Starboard
#   bash tools/vm/pool-test.sh after    after a restart: the pool and every file came back by themselves
# Never run it on a real computer: it erases the drives with the serial numbers SBDISK0001 to SBDISK0005.
set -uo pipefail
cd "$(dirname "$0")/../.."
[ "$(hostname)" = starboard-test ] || { echo "Stopped: this erases drives, so it only runs in the test VM (hostname starboard-test)"; exit 2; }
H="sudo python3 starboard/pool_helper.py"
J="$H --json"
check() { # check ID "what" command...
  local id="$1" what="$2"; shift 2
  if "$@" >/dev/null 2>&1; then echo "PASS $id $what"; else echo "FAIL $id $what"; fi
}
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
drive() { ls /dev/disk/by-id/virtio-SBDISK000"$1"; }
plan() { $J plan "$@" | field 'd.get("id") or d.get("error")'; }
apply() { $H apply "$@"; }

if [ "${1:-}" = before ]; then
  echo "== packages"
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq mergerfs rsync gdisk snapraid >/dev/null 2>&1
  check POOL-00 "mergerfs, rsync, sgdisk and snapraid installed" command -v mergerfs rsync sgdisk snapraid
  for n in 1 2 3 4 5; do [ -e "$(drive $n)" ] || echo "FAIL POOL-00 blank drive $n is missing"; done

  echo "== the drive list"
  $H drives
  check POOL-01 "the system drive is never offered" bash -c "$J drives | python3 -c \"import json,sys; d=json.load(sys.stdin); assert [x['use'] for x in d if x['name']=='vda']==['system']\""
  check POOL-01 "the blank drives are free, with their serial endings" bash -c "$J drives | python3 -c \"import json,sys; d=json.load(sys.stdin); assert sorted(x['ends'] for x in d if x['use']=='free')==['0001','0002','0003','0004','0005']\""

  echo "== add drive 1, erased: the pool is made"
  P=$(plan add "$(drive 1)" --as pool --erase)
  check POOL-02 "the check made a plan" test ${#P} = 12
  check POOL-02 "the check changed nothing" bash -c "! grep -q starboard-pool /etc/fstab"
  check POOL-03 "no erase without the serial ending" bash -c "! $H apply $P"
  check POOL-03 "no erase with the wrong ending" bash -c "! $H apply $P --confirm $(drive 1)=9999"
  check POOL-03 "nothing changed after the refusals" bash -c "! grep -q starboard-pool /etc/fstab"
  apply "$P" --confirm "$(drive 1)=0001"
  check POOL-04 "disk1 mounted" mountpoint -q /mnt/disks/disk1
  check POOL-04 "the pool is mounted" mountpoint -q /mnt/pool
  check POOL-04 "fstab has Starboard's block, mounted by UUID with nofail" bash -c "grep -A3 'starboard-pool begin' /etc/fstab | grep -q 'UUID=.*/mnt/disks/disk1 ext4 .*nofail'"
  check POOL-04 "a copy of fstab was saved first" sudo bash -c "ls /var/lib/starboard-pool/saved/fstab.*"
  check POOL-04 "Docker waits for the pool" test -f /etc/systemd/system/docker.service.d/starboard-pool.conf
  check POOL-04 "ext4 with no space held back" bash -c "sudo tune2fs -l \$(findmnt -no SOURCE /mnt/disks/disk1) | grep -q 'Reserved block count: *0$'"

  echo "== drive 2 has files of its own: keep them"
  sudo mkfs.ext4 -q -F -L old "$(drive 2)"
  sudo mkdir -p /media/old && sudo mount "$(drive 2)" /media/old
  for s in 1 2 3 4 5 6; do
    sudo mkdir -p "/media/old/media/tv/Example series $s/Season 1"
    sudo fallocate -l 200M "/media/old/media/tv/Example series $s/Season 1/episode 1.mkv"
  done
  sudo bash -c 'head -c 5000000 /dev/urandom > "/media/old/media/tv/Example series 1/Season 1/sample.mkv"'
  SUM=$(md5sum "/media/old/media/tv/Example series 1/Season 1/sample.mkv" | cut -d' ' -f1)
  echo "$SUM" > ~/sample.md5
  sudo find /media/old/media -exec touch -h -d '3 hours ago' {} +
  P=$(plan add "$(drive 2)" --as pool)
  apply "$P"
  check POOL-05 "kept drive mounted as disk2" mountpoint -q /mnt/disks/disk2
  check POOL-05 "its files are in the pool" test -f "/mnt/pool/media/tv/Example series 1/Season 1/sample.mkv"
  check POOL-05 "the pool line lists both drives" grep -q '/mnt/disks/disk1:/mnt/disks/disk2 /mnt/pool fuse.mergerfs' /etc/fstab
  check POOL-05 "the drive was added while the pool was in use" bash -c "getfattr -n user.mergerfs.branches --only-values /mnt/pool/.mergerfs 2>/dev/null | grep -q disk2 || ls /mnt/pool/media/tv | grep -q 'Example series 1'"

  echo "== balance"
  BEFORE=$(find /mnt/pool/media -type f | wc -l)
  P=$(plan balance)
  $J plan balance | field '"moves:", len(d["moves"])'
  check POOL-06 "the check found folders to move" bash -c "$J plan balance | python3 -c \"import json,sys; assert json.load(sys.stdin)['moves']\""
  apply "$P"
  check POOL-06 "folders moved to disk1, whole" bash -c "ls /mnt/disks/disk1/media/tv | grep -q 'Example series'"
  check POOL-06 "no folder is split between the drives" bash -c "! comm -12 <(ls /mnt/disks/disk1/media/tv | sort) <(ls /mnt/disks/disk2/media/tv | sort) | grep -q ."
  check POOL-06 "the pool still has every file" test "$(find /mnt/pool/media -type f | wc -l)" = "$BEFORE"
  check POOL-06 "the sample file is unchanged" test "$(md5sum "/mnt/pool/media/tv/Example series 1/Season 1/sample.mkv" | cut -d' ' -f1)" = "$SUM"

  echo "== drive 3 as parity"
  P=$(plan add "$(drive 3)" --as parity --erase)
  apply "$P" --confirm "$(drive 3)=0003"
  check POOL-07 "parity drive mounted" mountpoint -q /mnt/parity/parity1
  check POOL-07 "snapraid.conf written by Starboard" bash -c "head -1 /etc/snapraid.conf | grep -q starboard-pool"
  check POOL-07 "parity is not in the pool" bash -c "! grep -q parity1 <(grep fuse.mergerfs /etc/fstab)"
  sudo python3 starboard/pool_helper.py nightly
  check POOL-07 "the nightly check protected every file" sudo grep -q '"state": "done"' /var/lib/starboard-pool/nightly.json
  check POOL-07 "a too small drive is refused as parity" bash -c "$J plan add $(drive 5) --as parity --erase | grep -q 'at least as big'"

  echo "== add drive 4, then take it out again"
  apply "$(plan add "$(drive 4)" --as pool --erase)" --confirm "$(drive 4)=0004"
  sudo mkdir -p "/mnt/disks/disk4/media/films/Example film (2020)"
  sudo fallocate -l 50M "/mnt/disks/disk4/media/films/Example film (2020)/film.mkv"
  sudo find /mnt/disks/disk4/media -exec touch -h -d '3 hours ago' {} +
  P=$(plan remove disk4)
  apply "$P"
  check POOL-08 "disk4 is out of fstab" bash -c "! grep -q disk4 /etc/fstab"
  check POOL-08 "disk4 is unmounted" bash -c "! mountpoint -q /mnt/disks/disk4"
  check POOL-08 "its film moved to the other drives" test -f "/mnt/pool/media/films/Example film (2020)/film.mkv"
  check POOL-08 "the drive was not erased" sudo blkid -s LABEL -o value "$(drive 4)-part1"
  sudo python3 starboard/pool_helper.py nightly
  check POOL-08 "the nightly check runs without the drive" sudo grep -q '"state": "done"' /var/lib/starboard-pool/nightly.json

  echo "== a request from Starboard, through the requests folder"
  sudo deploy/install-pool.sh "$HOME/sbpool" >/dev/null
  echo '{"action": "drives", "id": "0123456789abcdef"}' > "$HOME/sbpool/requests/0123456789abcdef.json"
  for _ in $(seq 1 30); do [ -f "$HOME/sbpool/status/answers/0123456789abcdef.json" ] && break; sleep 2; done
  check POOL-09 "the helper answered" grep -q '"ok": true' "$HOME/sbpool/status/answers/0123456789abcdef.json"
  check POOL-09 "Starboard cannot write the answers" bash -c "! touch $HOME/sbpool/status/x"
  echo '{"action": "shell", "id": "fedcba9876543210", "cmd": "touch /root/x"}' > "$HOME/sbpool/requests/fedcba9876543210.json"
  for _ in $(seq 1 30); do [ -f "$HOME/sbpool/status/answers/fedcba9876543210.json" ] && break; sleep 2; done
  check POOL-09 "an unknown request is refused" grep -q '"ok": false' "$HOME/sbpool/status/answers/fedcba9876543210.json"
  check POOL-09 "and did nothing" sudo test ! -e /root/x
  findmnt --verify --tab-file /etc/fstab >/dev/null 2>&1; echo "     findmnt --verify exit: $?"
fi

if [ "${1:-}" = after ]; then
  echo "== after a restart"
  check POOL-10 "disk1 and disk2 mounted by themselves" bash -c "mountpoint -q /mnt/disks/disk1 && mountpoint -q /mnt/disks/disk2"
  check POOL-10 "the pool mounted by itself" mountpoint -q /mnt/pool
  check POOL-10 "the parity drive mounted" mountpoint -q /mnt/parity/parity1
  check POOL-10 "the sample file is unchanged" test "$(md5sum "/mnt/pool/media/tv/Example series 1/Season 1/sample.mkv" | cut -d' ' -f1)" = "$(cat ~/sample.md5)"
  check POOL-10 "the helper still answers" bash -c "$H status >/dev/null"
fi
