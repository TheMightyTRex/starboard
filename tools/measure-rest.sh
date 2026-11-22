#!/usr/bin/env bash
# Starboard's rest check (DASH-516). Read only: samples `docker stats` and /proc/diskstats on this computer and says
# which containers use the processor and memory, and which disks are read or written, while nobody is using the server.
#   tools/measure-rest.sh [minutes] [label]      (default 10 minutes; writes to $OUT or /mnt/pool/build-cache/rest/<label>)
# Pause downloads and conversions first, or they are what you measure. Disk names to watch: DISKS="sda sdb".
set -euo pipefail
mins="${1:-10}"; label="${2:-now}"
out="${OUT:-/mnt/pool/build-cache/rest}/$label"; mkdir -p "$out"
disks="${DISKS:-$(lsblk -dno NAME,TYPE | awk '$2=="disk"{print $1}' | tr '\n' ' ')}"
snap() { awk -v d="$disks" 'BEGIN{n=split(d,a," ");for(i=1;i<=n;i++)w[a[i]]=1} ($3 in w){print $3, $4, $8}' /proc/diskstats; }
snap > "$out/disk.0"
for i in $(seq 1 "$mins"); do
  docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' >> "$out/stats.txt"
  echo "--- $(date +%s)" >> "$out/stats.txt"
  sleep 60
  snap > "$out/disk.$i"
done
python3 - "$out" "$mins" <<'P'
import collections, sys
out, mins = sys.argv[1], int(sys.argv[2])
read = lambda i: {l.split()[0]: (int(l.split()[1]), int(l.split()[2])) for l in open(f"{out}/disk.{i}")}
a, b = read(0), read(mins)
print(f"Disks over {mins} minutes (reads, writes completed):")
for k in sorted(a):
    print(f"  {k}: {b[k][0] - a[k][0]} reads, {b[k][1] - a[k][1]} writes")
cpu = collections.defaultdict(list)
for line in open(f"{out}/stats.txt"):
    p = line.split()
    if len(p) >= 4 and p[1].endswith("%"):
        cpu[p[0]].append(float(p[1][:-1]))
print("Containers by average processor use:")
for k, v in sorted(cpu.items(), key=lambda x: -sum(x[1]))[:12]:
    print(f"  {k}: {sum(v) / len(v):.2f}%")
P
