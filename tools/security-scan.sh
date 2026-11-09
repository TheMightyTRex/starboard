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
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
NET=starboard-scan-net
TARGET="http://starboard-scan:8095"
FULL=0
[ "${1:-}" = "--full" ] && FULL=1
TRIVY=aquasec/trivy:0.69.1
ZAP=ghcr.io/zaproxy/zaproxy:stable
work="$(mktemp -d)"
# SCAN_REPORTS=folder keeps ZAP's reports (each warning with its address) after the scan; otherwise they go with it.
trap '[ -n "${SCAN_REPORTS:-}" ] && mkdir -p "$SCAN_REPORTS" && cp -r "$work/zap/." "$SCAN_REPORTS/"; docker rm -f starboard-scan >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; rm -rf "$work"' EXIT
failed=0
say() { printf '\n== %s\n' "$*"; }
result() { if [ "$1" = 0 ]; then echo "PASS $2"; else echo "FAIL $2"; failed=1; fi; }

say "Building a throwaway image of this checkout"
docker build -q -t starboard:scan . >/dev/null || { echo "The image did not build" >&2; exit 1; }

say "Trivy: known problems in the image"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$HOME/.cache/trivy:/root/.cache" "$TRIVY" \
  image --quiet --scanners vuln,secret --exit-code 1 starboard:scan
result $? "Trivy image"
docker run --rm -v "$PWD:/src:ro" -v "$HOME/.cache/trivy:/root/.cache" "$TRIVY" config --quiet --exit-code 1 /src
result $? "Trivy configuration"

say "Gitleaks: the whole git history"
docker run --rm -v "$PWD:/repo:ro" zricethezav/gitleaks:v8.28.0 git /repo --no-banner --redact
result $? "Gitleaks"

say "Bandit: medium and high"
docker run --rm -v "$PWD:/src:ro" python:3.12-alpine sh -c \
  "pip install -q bandit >/dev/null 2>&1 && bandit -q -r /src/starboard -ll 2>/dev/null"
result $? "Bandit"

say "ShellCheck"
docker run --rm -v "$PWD:/mnt:ro" -w /mnt koalaman/shellcheck:v0.11.0 -x -S warning install.sh run-first.sh update.sh reset-password.sh \
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
docker run --rm --network "$NET" -v "$work/zap:/zap/wrk:rw" "$ZAP" \
  zap-baseline.py -t "$TARGET" -m 3 -c rules.tsv > "$work/zap/baseline.txt" 2>&1
grep -E "^(FAIL|WARN)-NEW" "$work/zap/baseline.txt"
grep -q "FAIL-NEW: 0.*WARN-NEW: 0" "$work/zap/baseline.txt"
result $? "ZAP baseline, signed out (any WARN-NEW or FAIL-NEW above needs a look)"

if [ "$FULL" = 1 ]; then
  say "ZAP active scan, signed in (about 45 minutes)"
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
  rules=""
  i=0
  for pair in "Cookie=$cookie" "X-Starboard=1"; do
    rules="$rules -config replacer.full_list($i).description=h$i -config replacer.full_list($i).enabled=true"
    rules="$rules -config replacer.full_list($i).matchtype=REQ_HEADER -config replacer.full_list($i).matchstr=${pair%%=*}"
    rules="$rules -config replacer.full_list($i).regex=false -config replacer.full_list($i).replacement=${pair#*=}"
    i=$((i + 1))
  done
  docker run --rm --network "$NET" -v "$work/zap:/zap/wrk:rw" "$ZAP" \
    zap-full-scan.py -t "$TARGET/index.html" -j -m 5 -T 45 -c rules.tsv -J full.json -z "$rules" > "$work/zap/full.txt" 2>&1
  grep -E "^(FAIL|WARN)-NEW" "$work/zap/full.txt"
  grep -q "FAIL-NEW: 0.*WARN-NEW: 0" "$work/zap/full.txt"
  result $? "ZAP active scan, signed in"
fi

say "Done"
if [ "$failed" = 0 ]; then echo "Every scanner passed."; else echo "Something needs a look: see FAIL above."; fi
exit "$failed"
