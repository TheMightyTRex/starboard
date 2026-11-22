#!/usr/bin/env bash
# Read-only measurements for the About page's "How lean Starboard is" and the help article of the same name
# (DASH-408). Run it on the server Starboard runs on, then write the figures and the date into
# web/settings-updates.html and docs/help/topics/how-lean-starboard-is.md. It changes nothing.
#
#   bash tools/measure-lean.sh [container]     (default: starboard; takes about 2 minutes 40 seconds)
set -euo pipefail
name="${1:-starboard}"
cid=$(docker inspect "$name" --format '{{.Id}}')
cg=/sys/fs/cgroup/system.slice/docker-$cid.scope
[ -f "$cg/cpu.stat" ] || { echo "No control group folder at $cg: this server keeps containers' control groups elsewhere" >&2; exit 1; }
echo "When: $(date -u +%FT%TZ)"
echo "Host: $(nproc) processors, $(free -m | awk '/Mem:/{print $2}') MiB memory, load $(cut -d' ' -f1-3 /proc/loadavg)"
echo "Started: $(docker inspect "$name" --format '{{.State.StartedAt}}')"
echo "--- docker stats, six readings 5 seconds apart"
for _ in 1 2 3 4 5 6; do docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' "$name"; sleep 5; done
a=$(awk '/usage_usec/{print $2}' "$cg/cpu.stat"); t0=$(date +%s.%N)
sleep 120
b=$(awk '/usage_usec/{print $2}' "$cg/cpu.stat"); t1=$(date +%s.%N)
echo "--- processor over $(echo "$t1 - $t0" | bc) seconds: $(echo "($b - $a) / 1000000 / ($t1 - $t0) * 100" | bc -l | cut -c1-6)% of one processor"
up=$(( $(date +%s) - $(date -d "$(docker inspect "$name" --format '{{.State.StartedAt}}')" +%s) ))
echo "--- processor since it started: $(echo "$b / 1000000" | bc -l | cut -c1-6) seconds in $up seconds = $(echo "$b / 1000000 / $up * 100" | bc -l | cut -c1-5)% of one processor"
echo "--- memory, whole container with cache: $(echo "$(cat "$cg/memory.current") / 1048576" | bc -l | cut -c1-5) MiB"
echo "--- process"; docker top "$name" -o pid,rss,etime,comm
echo "--- image"; docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -E "^$name:" || docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep -i "$name"
