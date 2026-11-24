#!/usr/bin/env bash
# Runs the free security scanners against this checkout and a throwaway copy of it:  tools/security-scan.sh
#
#   Trivy      known problems in the image's packages and Python libraries, and the Dockerfile's set-up
#   Gitleaks   keys and passwords anywhere in the git history (.gitleaksignore lists made-up test keys)
#   Bandit     risky patterns in Starboard's Python code (each reviewed line is marked nosec with its reason)
#   ShellCheck mistakes in the shell scripts
#   Hadolint   the Dockerfile
#   ZAP        a baseline scan of a running throwaway copy, signed out (--full: also an active scan, signed in).
#              The copy and ZAP share a private Docker network with no way out, so ZAP cannot reach your other
#              apps, this computer or the internet: its crawler treats every port on one address as one site.
#
# Everything runs in Docker from pinned images; nothing is installed and the live server is never touched.
# Needs Docker, and network access to download the scanners (about 2 GB the first time, mostly ZAP).
#
# Options:  --full      also the ZAP active scan, signed in (about 1 to 2 hours)
#           --dry-run   print the ZAP settings and the commands it would run, then stop; nothing is built or started
#
# The full scan needs no tuning (DASH-543; found by the 0.28.0 release, whose active scan took four tries):
#   ZAP_MEMORY      the memory cap for ZAP's container, default 8g (6g was too little: the 0.28.0 scan hit it). On a 16 GB
#                   server that is about half, inside the heavy-job limit of about two thirds; run nothing else heavy beside it.
#   ZAP_HEAP        ZAP's Java heap, default 2g.
#   ZAP_JVM_EXTRA   extra Java options, default excludes java.net.URLDecoder.decode from compilation: ZAP 2.17.0's Java
#                   17 compiler crashed in that method during the active scan (0.28.0), so it is left to the interpreter.
#   ZAP_CPUS        processors for ZAP, default 4.
#   ZAP_TIME_LIMIT  minutes the active scan may take, default 150 (0.28.0 took 65 minutes on its last try, 0.29.0 about 2
#                   hours). When it runs out, ZAP's container is removed and the scan FAILS with "did not finish in time",
#                   never hangs and never counts as a pass.
#   SCAN_REPORTS    a folder to keep ZAP's reports in.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
NET=starboard-scan-net
TARGET="http://starboard-scan:8095"
FULL=0
DRY=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --dry-run) DRY=1 ;;
    *) echo "Unknown option $arg. Use --full or --dry-run." >&2; exit 2 ;;
  esac
done
TRIVY=aquasec/trivy:0.69.1
ZAP=zaproxy/zap-stable:2.17.0
# ZAP (Java and its headless Firefox, about 5 GB in all) is capped at 6 GB, so a scan cannot run the server out of memory (14 November 2026: an uncapped active scan grew
# to 4 GB beside other work and the computer ran out of memory; 3 GB was too little for its browser). Run nothing else heavy beside it.
ZAP_MEMORY="${ZAP_MEMORY:-8g}"  # 8g since 23 November 2026 (DASH-543): the active scan hit the old 6g cap
ZAP_LIMITS="--memory $ZAP_MEMORY --memory-swap $ZAP_MEMORY --cpus ${ZAP_CPUS:-4}"
# ZAP sizes its Java heap from the whole computer's memory (it reads only cgroup v1 limits), which does not fit
# under the cap above, so it is given its heap in its own JVM properties file (the first line of .ZAP_JVM.properties).
ZAP_HEAP="${ZAP_HEAP:-2g}"
# The Java option the 0.28.0 and 0.29.0 scans needed: ZAP's compiler crashed in URLDecoder.decode (a fault in Java, not in Starboard).
ZAP_JVM_EXTRA="${ZAP_JVM_EXTRA--XX:CompileCommand=quiet -XX:CompileCommand=exclude,java.net.URLDecoder::decode}"
ZAP_TIME_LIMIT="${ZAP_TIME_LIMIT:-150}"  # minutes for the active scan
case "$ZAP_TIME_LIMIT" in ''|*[!0-9]*) echo "ZAP_TIME_LIMIT must be a whole number of minutes, not '$ZAP_TIME_LIMIT'." >&2; exit 2 ;; esac
if [ "$DRY" = 1 ]; then
  echo "Dry run: nothing is built or started."
  echo "ZAP image:        $ZAP"
  echo "ZAP limits:       $ZAP_LIMITS"
  echo "ZAP JVM line:     -Xmx$ZAP_HEAP $ZAP_JVM_EXTRA"
  echo "Active scan:      $([ "$FULL" = 1 ] && echo "yes (--full), time limit $ZAP_TIME_LIMIT minutes" || echo "no (add --full)")"
  echo "ZAP command:      docker run --rm --name starboard-zap --network $NET $ZAP_LIMITS ... $ZAP zap-full-scan.py -t $TARGET/index.html -j -m 5 -T 45 ..."
  exit 0
fi
work="$(mktemp -d)"
# SCAN_REPORTS=folder keeps ZAP's reports (each warning with its address) after the scan; otherwise they go with it.
trap '[ -n "${SCAN_REPORTS:-}" ] && mkdir -p "$SCAN_REPORTS" && cp -r "$work/zap/." "$SCAN_REPORTS/"; docker rm -f starboard-scan starboard-zap >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; rm -rf "$work"' EXIT
failed=0
say() { printf '\n== %s\n' "$*"; }
result() { if [ "$1" = 0 ]; then echo "PASS $2"; else echo "FAIL $2"; failed=1; fi; }

say "Building a throwaway image of this checkout"
docker build -q -t starboard:scan . >/dev/null || { echo "The image did not build" >&2; exit 1; }

say "Trivy: known problems in the image"
# Trivy's database (about 900 MB unpacked) is kept in TRIVY_CACHE when set, else in memory for this run: its
# database cannot open on a FUSE file system such as a mergerfs pool ("failed to open db: no such device").
if [ -n "${TRIVY_CACHE:-}" ]; then TRIVY_CACHE_ARGS=(-v "$TRIVY_CACHE:/root/.cache"); else TRIVY_CACHE_ARGS=(--tmpfs /root/.cache:size=3g); fi
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "${TRIVY_CACHE_ARGS[@]}" "$TRIVY" \
  image --quiet --scanners vuln,secret --exit-code 1 starboard:scan
result $? "Trivy image"
docker run --rm -v "$PWD:/src:ro" "${TRIVY_CACHE_ARGS[@]}" "$TRIVY" config --quiet --exit-code 1 /src
result $? "Trivy configuration"

say "Gitleaks: the whole git history"
# In a git worktree, .git is a file naming a folder in the main checkout's .git: that is mounted too, at the same
# path, or Gitleaks scans no commits at all and still passes (found 17 November 2026).
GIT_COMMON=$(git rev-parse --path-format=absolute --git-common-dir)
docker run --rm -v "$PWD:/repo:ro" -v "$GIT_COMMON:$GIT_COMMON:ro" zricethezav/gitleaks:v8.28.0 git /repo --no-banner --redact
result $? "Gitleaks"

say "Bandit: medium and high"
docker run --rm -v "$PWD:/src:ro" python:3.12.16-alpine3.24 sh -c \
  "pip install -q bandit==1.9.4 >/dev/null 2>&1 && bandit -q -r /src/starboard -ll 2>/dev/null"
result $? "Bandit"

say "ShellCheck"
docker run --rm -v "$PWD:/mnt:ro" -w /mnt koalaman/shellcheck:v0.11.0 -x -S warning install.sh run-first.sh update.sh reset-password.sh reset-sign-in.sh \
  tools/*.sh tools/vm/vm.sh deploy/*.sh
result $? "ShellCheck"

say "Hadolint (DL3018, pinning Alpine package versions, is left out on purpose: old versions are removed)"
docker run --rm -i hadolint/hadolint:v2.14.0 hadolint --ignore DL3018 - < Dockerfile
result $? "Hadolint"

say "ZAP against a throwaway copy, on a private network"
mkdir -p "$work/data" "$work/zap" && chmod 777 "$work/zap"
docker network rm "$NET" >/dev/null 2>&1
docker network create --internal "$NET" >/dev/null
docker run -d --name starboard-scan --network "$NET" -u "$(id -u):$(id -g)" -e STARBOARD_ALLOWED_HOSTS=starboard-scan \
  -v "$work/data:/data" --read-only --tmpfs /tmp --cap-drop ALL starboard:scan >/dev/null
for _ in $(seq 1 30); do [ -s "$work/data/setup-token" ] && break; sleep 1; done
# The warnings explained in docs/SECURITY-AND-TESTS.md are marked IGNORE in tools/zap-rules.tsv.
cp tools/zap-rules.tsv "$work/zap/rules.tsv"
printf -- "-Xmx%s %s\n" "$ZAP_HEAP" "$ZAP_JVM_EXTRA" > "$work/zap-jvm.properties"  # one line: ZAP reads the first
ZAP_LIMITS="$ZAP_LIMITS -v $work/zap-jvm.properties:/home/zap/.ZAP/.ZAP_JVM.properties:ro"
docker run --rm --network "$NET" $ZAP_LIMITS -v "$work/zap:/zap/wrk:rw" "$ZAP" \
  zap-baseline.py -t "$TARGET" -m 3 -c rules.tsv > "$work/zap/baseline.txt" 2>&1
grep -E "^(FAIL|WARN)-NEW" "$work/zap/baseline.txt"
grep -q "FAIL-NEW: 0.*WARN-NEW: 0" "$work/zap/baseline.txt"
result $? "ZAP baseline, signed out (any WARN-NEW or FAIL-NEW above needs a look)"

if [ "$FULL" = 1 ]; then
  say "ZAP active scan, signed in (up to $ZAP_TIME_LIMIT minutes)"
  # A made-up password, set from inside the copy: nothing outside the private network can reach it.
  setup='import http.client, json, secrets
token = open("/data/setup-token").read().strip()
c = http.client.HTTPConnection("127.0.0.1", 8095, timeout=20)
c.request("POST", "/api/setup", json.dumps({"token": token, "password": secrets.token_urlsafe(16)}),
          {"Content-Type": "application/json", "X-Starboard": "1", "Origin": "http://127.0.0.1:8095"})
r = c.getresponse()
r.read()
print(r.getheader("Set-Cookie").split(";")[0])'
  cookie="$(docker exec starboard-scan python -c "$setup")"
  # One browser for the AJAX spider: each headless Firefox takes 600 to 800 MB, and several did not fit under the cap.
  rules="-config ajaxSpider.numberOfBrowsers=${ZAP_BROWSERS:-1}"
  i=0
  for pair in "Cookie=$cookie" "X-Starboard=1"; do
    rules="$rules -config replacer.full_list($i).description=h$i -config replacer.full_list($i).enabled=true"
    rules="$rules -config replacer.full_list($i).matchtype=REQ_HEADER -config replacer.full_list($i).matchstr=${pair%%=*}"
    rules="$rules -config replacer.full_list($i).regex=false -config replacer.full_list($i).replacement=${pair#*=}"
    i=$((i + 1))
  done
  timeout --foreground "${ZAP_TIME_LIMIT}m" docker run --rm --name starboard-zap --network "$NET" $ZAP_LIMITS -v "$work/zap:/zap/wrk:rw" "$ZAP" \
    zap-full-scan.py -t "$TARGET/index.html" -j -m 5 -T 45 -c rules.tsv -J full.json -z "$rules" > "$work/zap/full.txt" 2>&1
  zap_status=$?
  if [ "$zap_status" = 124 ]; then  # timeout's own code: the container may still be running, so it is removed
    docker rm -f starboard-zap >/dev/null 2>&1
    echo "ZAP's active scan did not finish in time: stopped after $ZAP_TIME_LIMIT minutes (set ZAP_TIME_LIMIT to allow more). Its output so far is in full.txt (use SCAN_REPORTS=folder to keep it)."
    result 1 "ZAP active scan, signed in (did not finish in $ZAP_TIME_LIMIT minutes)"
  else
    grep -E "^(FAIL|WARN)-NEW" "$work/zap/full.txt"
    grep -q "FAIL-NEW: 0.*WARN-NEW: 0" "$work/zap/full.txt"
    result $? "ZAP active scan, signed in"
  fi
fi

say "Done"
if [ "$failed" = 0 ]; then echo "Every scanner passed."; else echo "Something needs a look: see FAIL above."; fi
exit "$failed"
