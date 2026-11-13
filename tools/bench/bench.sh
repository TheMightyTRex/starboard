#!/bin/bash
# Idle benchmark of Starboard, Reelix and the apps other media server stacks use (DASH-398). The method of
# the help centre's comparison tests (docs/help/comparisons/how-the-tests-were-run.md): each app on a fresh,
# empty config in a Docker volume, on an internal Docker network with no way out, no limits. 120 s to settle,
# then docker stats --no-stream every 5 s for 180 s (36 samples). Three apps at a time.
#
# The images below are the ones measured on 13 November 2026, pinned by digest. Change a digest to test a
# newer version. Starboard and Reelix are named by tag (STARBOARD_IMAGE, REELIX_FULL_IMAGE, REELIX_LITE_IMAGE).
# The On demand plug-in is measured only when ON_DEMAND_IMAGE names its image.
#
# Usage:
#   ./bench.sh pull        pull every image below by digest (tags on this computer are not moved)
#   ./bench.sh run         run all batches (START=n begins at entry n; ONLY="a b" runs only those names)
#   ./bench.sh recyclarr   time one "recyclarr sync" run, sampled every second
#   ./bench.sh live        read-only reading of every running container for 180 s
#   ./bench.sh online      extra: Heimdall idle and one Recyclarr sync with internet (not the closed network)
#   ./bench.sh clean       remove every bench- container and volume, and the bench network
#
# Every container, volume and the network are named bench-...; nothing else is touched. Results go to OUT
# (default ./bench-results). Then: python3 -I summarise.py OUT/samples.txt > OUT/summary.tsv
set -u
OUT=${OUT:-$PWD/bench-results}
NET=bench-net
SETTLE=${SETTLE:-120}
SAMPLES=${SAMPLES:-36}
# Throwaway values for the two apps that will not start without one. Made fresh on each run.
HOMARR_KEY=$(openssl rand -hex 32)
DBPASS=$(openssl rand -hex 16)
JWT=$(openssl rand -hex 32)
# A made-up Sonarr key for Recyclarr's run (there is no Sonarr to accept it).
FAKE_KEY=$(openssl rand -hex 16)

# name|image|mount point of the config volume|extra docker run arguments|command (optional)
APPS=(
"starboard|${STARBOARD_IMAGE:-ghcr.io/themightytrex/starboard}|/data||"
"reelix-full|${REELIX_FULL_IMAGE:-ghcr.io/themightytrex/reelix:full}|/config||"
"reelix-lite|${REELIX_LITE_IMAGE:-ghcr.io/themightytrex/reelix:lite}|/config||"
"radarr|lscr.io/linuxserver/radarr@sha256:51a9ac2a9eb47afc833541e5fd6c11b86eb9f810694c22fa2429e3078e9194b2|/config||"
"sonarr|lscr.io/linuxserver/sonarr@sha256:673dc4609a5672bc8e46069c86ffcea283a86b48d34a6c93d8da8c24a1b87571|/config||"
"lidarr|lscr.io/linuxserver/lidarr@sha256:a91ef0642c15c9bd7c4260fee98fa99972c61601e37c8a96411d6a9cf0e9ad40|/config||"
"prowlarr|lscr.io/linuxserver/prowlarr@sha256:6660787a99b2e58203539583663c973b48979fc00ff2cb78dc0ea17429e1f6ef|/config||"
# Readarr: lscr.io/linuxserver/readarr:develop is an empty manifest list (no amd64 build) and hotio refuses anonymous pulls, 13 Nov 2026.
# "readarr|lscr.io/linuxserver/readarr@sha256:eb37f58646a901dc7727cf448cae36daaefaba79de33b5058dab79aa4c04aefb|/config||"
"jellyseerr|ghcr.io/fallenbagel/jellyseerr@sha256:91edd5620e51ed512ecdfd8b2e157c473faf385edf88c3764dc9ec32d310c0df|/app/config||"
"overseerr|lscr.io/linuxserver/overseerr@sha256:53a1b839ffa81f139e1552840772bff8a5d13f5c78a69cce22458b9a6cd0844d|/config||"
"seerr|ghcr.io/seerr-team/seerr@sha256:aadee014b40e28cf9aa4928bc9d1183a6eb08f8c44d543cddc9efdcb16549be2|/app/config||"
"homarr|ghcr.io/homarr-labs/homarr@sha256:70bf384fa6848d058322220597eb7baca62ea80039bfb3dfcc2bfef8991e7bfc|/appdata|-e SECRET_ENCRYPTION_KEY=$HOMARR_KEY|"
"homepage|ghcr.io/gethomepage/homepage@sha256:019d8f063a7299e7c1c51ee4a70b692291809af3244894fbec2c2ac7d1f71b18|/app/config|-e HOMEPAGE_ALLOWED_HOSTS=*|"
"organizr|organizr/organizr@sha256:703de7b15e3ca0046c9bcfee03c72539f74acc5e26929f2911aa1af2be8ebb01|/config||"
"heimdall|lscr.io/linuxserver/heimdall@sha256:6abf244e7bfef9c9383d1a9292d602a65f71e5abfe741d65b14622a927da733c|/config||"
"heimdall-warm|lscr.io/linuxserver/heimdall@sha256:6abf244e7bfef9c9383d1a9292d602a65f71e5abfe741d65b14622a927da733c|/config||"
"dashy|lissy93/dashy@sha256:e054ad2407fe16ca687e5bb910664bf46b309cd444e4c92feb448423f993c9f4|/app/user-data||"
"tautulli|lscr.io/linuxserver/tautulli@sha256:5e8f80cc18f03c606a3567c8a9b37d80812ed8017d2e2f8ff2e2a91b54a3aef1|/config||"
"jellystat|cyfershepard/jellystat@sha256:e61c759ec706da378bc8374e797da1dfd298ab30f804cefd82d192c301a888c7|/app/backend/backup-data|-e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=$DBPASS -e POSTGRES_IP=bench-jellystat-db -e POSTGRES_PORT=5432 -e JWT_SECRET=$JWT|"
"navidrome|deluan/navidrome@sha256:38dc2727bfcfd5ede290f8ada114fc90368146f265ae4701ddddbcbe2a44ee52|/data|-v bench-navidrome-music:/music:ro|"
"kavita|jvmilazz0/kavita@sha256:31181a32f0dda73cae68721867028a7253d57881b58bea5754cd9e578e75421a|/kavita/config||"
"wizarr|ghcr.io/wizarrrr/wizarr@sha256:08f2c6de534ec7d36d39a4f55b7c5c379021ca881dc519c702aad0ddafbdc67a|/data||"
"maintainerr|ghcr.io/maintainerr/maintainerr@sha256:5dcd5bef9d49c614bb74453df3da198afc05a38d8e2cd96b3669bc2c76a94112|/opt/data||"
"unpackerr|golift/unpackerr@sha256:fc8b69571033f197d4db5cf22a573acb3bb891c9f8033431b9a1fcf679ca3e9c|/config||"
"bazarr|lscr.io/linuxserver/bazarr@sha256:832820dec70bce9e912c6eee7a95baf6551e03dbc63325a7208daaa455423752|/config||"
"tdarr|ghcr.io/haveagitgat/tdarr@sha256:84743e5ae433a5b49cb463b2dff2679eb02f0cac24fb88c830f49bf8aa9f1c04|/app/server|-v bench-tdarr-configs:/app/configs -v bench-tdarr-logs:/app/logs -e internalNode=false -e serverIP=0.0.0.0 -e serverPort=8266 -e webUIPort=8265 -e inContainer=true|"
"recyclarr|ghcr.io/recyclarr/recyclarr@sha256:3e9c41b9ec29bbf65fe846864058730d321a21f7695d8c0d9437b73e34d50ad9|/config||"
)
# The On demand plug-in has no published image yet; give its image to measure it.
[ -n "${ON_DEMAND_IMAGE:-}" ] && APPS+=("on-demand|$ON_DEMAND_IMAGE|/data|-e ONDEMAND_CONFIG=/data|")
DB_IMAGE=postgres@sha256:78a275d4c891f7b3a33d3f1a78eda9f1d744954d9e20122bfdc97cdda25cddaf

net() { docker network inspect $NET >/dev/null 2>&1 || docker network create --internal $NET >/dev/null; }

start() { # name image mount extra cmd
  set -f
  local n=bench-$1 img=$2 mnt=$3 extra=$4 cmd=$5
  docker rm -f $n >/dev/null 2>&1; docker volume rm -f $n >/dev/null 2>&1
  if [ "$1" = jellystat ]; then
    # Jellystat cannot start without its Postgres; the two are measured together.
    docker rm -f bench-jellystat-db >/dev/null 2>&1; docker volume rm -f bench-jellystat-db >/dev/null 2>&1
    docker run -d --name bench-jellystat-db --network $NET -e POSTGRES_PASSWORD=$DBPASS \
      -v bench-jellystat-db:/var/lib/postgresql/data $DB_IMAGE >/dev/null
    sleep 15
  fi
  if [ "$1" = on-demand ]; then
    # The On demand plug-in runs as user 1000 and its image has no /data, so a new volume belongs to root.
    # Starboard makes this folder for the plug-in; here the empty volume is handed to user 1000.
    docker run --rm -v $n:$mnt alpine:3.21 chown 1000:1000 $mnt
  fi
  if [ "$1" = organizr ]; then
    # Organizr fetches its own code from GitHub on the first start and stops if it cannot. The least it
    # needs: one first start with internet (Docker's default network) to fetch it, then the measured start
    # on the closed network, as for every other app.
    docker run -d --name $n-prep -e PUID=1000 -e PGID=1000 -v $n:$mnt $img >/dev/null
    local w; for w in $(seq 1 60); do
      docker exec $n-prep test -f /config/www/organizr/index.php 2>/dev/null && break; sleep 5; done
    sleep 20; docker logs $n-prep > $OUT/logs/$n-prep.txt 2>&1; docker rm -f $n-prep >/dev/null
  fi
  if [ "$1" = heimdall-warm ]; then
    # Extra run, not in the 4 November method: without internet Heimdall retries its app list every second
    # or so. Here it has one first start of 90 s with internet to fetch the list, then is measured closed.
    docker run -d --name $n-prep -e PUID=1000 -e PGID=1000 -v $n:$mnt $img >/dev/null
    sleep 90; docker logs $n-prep > $OUT/logs/$n-prep.txt 2>&1; docker rm -f $n-prep >/dev/null
  fi
  # shellcheck disable=SC2086
  docker run -d --name $n --network $NET -e PUID=1000 -e PGID=1000 -e TZ=Europe/London $extra \
    -v $n:$mnt $img $cmd >/dev/null
  set +f
}

measure() { # samples every bench- container that is running
  sleep $SETTLE
  local k; for k in $(seq 1 $SAMPLES); do
    local names; names=$(docker ps --filter name=^bench- --format '{{.Names}}' | sort)
    # shellcheck disable=SC2086
    [ -n "$names" ] && docker stats --no-stream --format "{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.PIDs}}" $names \
      | sed "s/^/$(date +%H:%M:%S) /"
    sleep 5
  done
}

run() {
  net
  local i=${START:-0} sel=()
  for e in "${APPS[@]}"; do
    if [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" ${e%%|*} "* ]]; then sel+=("$e"); fi
  done
  while [ $i -lt ${#sel[@]} ]; do
    local batch=() j
    for j in 0 1 2; do
      [ $((i+j)) -lt ${#sel[@]} ] || break
      IFS='|' read -r name img mnt extra cmd <<< "${sel[$((i+j))]}"
      start "$name" "$img" "$mnt" "$extra" "$cmd"; batch+=("$name")
    done
    echo "$(date -Is) batch ${batch[*]} load $(cut -d' ' -f1-3 /proc/loadavg) available $(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo) MiB" >> $OUT/load.txt
    measure >> $OUT/samples.txt
    echo "$(date -Is) end load $(cut -d' ' -f1-3 /proc/loadavg)" >> $OUT/load.txt
    for n in $(docker ps -a --filter name=^bench- --format '{{.Names}}'); do
      docker inspect $n --format "$n status={{.State.Status}} restarts={{.RestartCount}} exit={{.State.ExitCode}}" >> $OUT/status.txt
      docker logs $n > $OUT/logs/$n.txt 2>&1
      docker rm -f $n >/dev/null
    done
    docker volume ls -q --filter name=^bench- | xargs -r docker volume rm -f >/dev/null
    i=$((i+3))
  done
}

recyclarr() { # times one sync run with a minimal config pointing at a Sonarr that is not there
  net
  local img; img=$(printf '%s\n' "${APPS[@]}" | awk -F'|' '$1=="recyclarr"{print $2}')
  docker volume rm -f bench-recyclarr-run >/dev/null 2>&1
  docker run --rm -e KEY=$FAKE_KEY -v bench-recyclarr-run:/config alpine:3.21 sh -c 'cat > /config/recyclarr.yml <<EOF
sonarr:
  bench:
    base_url: http://bench-sonarr:8989
    api_key: $KEY
EOF
chown -R 1000:1000 /config'
  local t0; t0=$(date +%s.%N)
  docker run -d --name bench-recyclarr-run --network $NET -e TZ=Europe/London \
    -v bench-recyclarr-run:/config $img sync >/dev/null
  while [ "$(docker inspect -f '{{.State.Running}}' bench-recyclarr-run 2>/dev/null)" = true ]; do
    docker stats --no-stream --format "{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.PIDs}}" bench-recyclarr-run | sed "s/^/$(date +%H:%M:%S.%N) /"
  done > $OUT/samples-recyclarr-run.txt
  docker inspect bench-recyclarr-run --format 'started={{.State.StartedAt}} finished={{.State.FinishedAt}} exit={{.State.ExitCode}}' > $OUT/recyclarr-run.txt
  echo "wall seconds $(echo "$(date +%s.%N) - $t0" | bc)" >> $OUT/recyclarr-run.txt
  docker logs bench-recyclarr-run > $OUT/logs/bench-recyclarr-run.txt 2>&1
  docker rm -f bench-recyclarr-run >/dev/null; docker volume rm -f bench-recyclarr-run >/dev/null
}

live() { # read only: docker stats on every running container, every 5 s for 180 s
  local k; for k in $(seq 1 36); do
    docker stats --no-stream --format "{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.PIDs}}" | sed "s/^/$(date +%H:%M:%S) /"
    sleep 5
  done > $OUT/samples-live.txt
}

online() { # extra, outside the 4 November method: Heimdall idle and one Recyclarr sync WITH internet
  # (Docker's default network), because both only fail and retry without it. Labelled as such in RESULTS.md.
  local img
  img=$(printf '%s\n' "${APPS[@]}" | awk -F'|' '$1=="heimdall"{print $2}')
  docker rm -f bench-heimdall-net >/dev/null 2>&1; docker volume rm -f bench-heimdall-net >/dev/null 2>&1
  docker run -d --name bench-heimdall-net -e PUID=1000 -e PGID=1000 -e TZ=Europe/London -v bench-heimdall-net:/config $img >/dev/null
  measure > $OUT/samples-online.txt
  docker logs bench-heimdall-net > $OUT/logs/bench-heimdall-net.txt 2>&1
  docker rm -f bench-heimdall-net >/dev/null; docker volume rm -f bench-heimdall-net >/dev/null
  img=$(printf '%s\n' "${APPS[@]}" | awk -F'|' '$1=="recyclarr"{print $2}')
  docker volume rm -f bench-recyclarr-net >/dev/null 2>&1
  docker run --rm -e KEY=$FAKE_KEY -v bench-recyclarr-net:/config alpine:3.21 sh -c 'printf "sonarr:\n  bench:\n    base_url: http://bench-sonarr:8989\n    api_key: %s\n" "$KEY" > /config/recyclarr.yml; chown -R 1000:1000 /config'
  local t0; t0=$(date +%s.%N)
  docker run -d --name bench-recyclarr-net -e TZ=Europe/London -v bench-recyclarr-net:/config $img sync >/dev/null
  while [ "$(docker inspect -f '{{.State.Running}}' bench-recyclarr-net 2>/dev/null)" = true ]; do
    docker stats --no-stream --format "{{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.PIDs}}" bench-recyclarr-net | sed "s/^/$(date +%H:%M:%S.%N) /"
  done > $OUT/samples-recyclarr-net.txt
  docker inspect bench-recyclarr-net --format 'started={{.State.StartedAt}} finished={{.State.FinishedAt}} exit={{.State.ExitCode}}' > $OUT/recyclarr-net.txt
  echo "wall seconds $(echo "$(date +%s.%N) - $t0" | bc)" >> $OUT/recyclarr-net.txt
  docker logs bench-recyclarr-net > $OUT/logs/bench-recyclarr-net.txt 2>&1
  docker rm -f bench-recyclarr-net >/dev/null; docker volume rm -f bench-recyclarr-net >/dev/null
}

pull() {
  local e img
  for e in "${APPS[@]}" "x|$DB_IMAGE"; do
    IFS='|' read -r _ img _ <<< "$e"
    if [[ $img == *@sha256:* ]]; then
      docker image inspect $img >/dev/null 2>&1 && { echo "present $img"; continue; }
    elif [[ $img == ghcr.io/themightytrex/* ]]; then
      : # Starboard and Reelix by tag: pulled, so the newest release is measured
    else
      echo "not pulled (a local image) $img"; continue
    fi
    docker pull -q $img >/dev/null 2>&1 && echo "pulled $img" || echo "FAILED $img"
  done
}

clean() {
  docker ps -aq --filter name=^bench- | xargs -r docker rm -f >/dev/null
  docker volume ls -q --filter name=^bench- | xargs -r docker volume rm -f >/dev/null
  docker network rm $NET >/dev/null 2>&1
  echo cleaned
}

mkdir -p $OUT/logs
case "${1:-run}" in
  pull) pull ;; run) run ;; online) online ;; recyclarr) recyclarr ;; live) live ;; clean) clean ;;
  *) echo "usage: $0 pull|run|recyclarr|live|online|clean"; exit 1 ;;
esac
