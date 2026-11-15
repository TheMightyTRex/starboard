#!/bin/sh
# Inside the sealed Docker of tools/update_e2e.sh (DASH-418). Runs as root only to start Docker, make the test user
# and give a plug-in's data folder to another user; Starboard is installed and updated as the test user, as on a server.
set -eu
log() { printf '\n######## %s\n' "$*"; }
apk add --no-cache bash git python3 curl shadow >/dev/null
addgroup -g 2375 docker 2>/dev/null || true
id tester >/dev/null 2>&1 || adduser -D -u 1000 -s /bin/bash tester
addgroup tester docker
dockerd-entrypoint.sh dockerd --group docker > /var/log/dockerd.log 2>&1 &
for i in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 1; done
docker info >/dev/null 2>&1 || { tail -30 /var/log/dockerd.log; exit 1; }
chown -R tester /e2e
exec bash -s <<'INNER'
set -uo pipefail
PORT=18555
H=/home/tester/starboard
FAILED=0
pass() { printf 'PASS %s\n' "$*"; }
fail() { printf 'FAIL %s\n' "$*"; FAILED=$((FAILED + 1)); }
as() { su tester -s /bin/bash -c "$*"; }
api() { curl -s -b /tmp/jar -c /tmp/jar -H 'Content-Type: application/json' "$@"; }
answers() { for _ in $(seq 1 "${1:-60}"); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/healthz" && return 0; sleep 2; done; return 1; }
version() { curl -s -b /tmp/jar "http://127.0.0.1:$PORT/api/version" | python3 -c 'import sys,json;print(json.load(sys.stdin)["current"])' 2>/dev/null; }
setting() { curl -s -b /tmp/jar "http://127.0.0.1:$PORT/api/config" | python3 -c 'import sys,json;print(json.load(sys.stdin)["server_name"])' 2>/dev/null; }
plugin_kept() { [ "$(cat $H/data/plugins/e2e-fake/data/kept 2>/dev/null)" = "the plug-in's own data" ] && [ "$(stat -c %u $H/data/plugins/e2e-fake/data)" = 4242 ]; }
sign_in() { api -o /dev/null -X POST "http://127.0.0.1:$PORT/api/login" -d '{"password":"e2e correct horse battery"}'; }

printf '\n######## A. Starboard %s, installed with its own installer\n' "$FROM"
as "git clone -q /e2e/origin.git $H && cd $H && git -c advice.detachedHead=false checkout -q $FROM"
started=$SECONDS
as "cd $H && ./install.sh --yes --port $PORT --docker --no-starter --local-only" > /e2e/install.log 2>&1
if answers 90; then pass "$FROM installed and answers ($((SECONDS - started)) s)"; else fail "$FROM did not start"; tail -40 /e2e/install.log; exit 1; fi
token="$(cat $H/data/setup-token)"
api -o /dev/null -X POST "http://127.0.0.1:$PORT/api/setup" -d "{\"token\":\"$token\",\"password\":\"e2e correct horse battery\"}"
api -o /dev/null -X PUT "http://127.0.0.1:$PORT/api/config/general" -d '{"server_name":"E2E kept","setup_guide_done":true}'
[ "$(setting)" = "E2E kept" ] && pass "a setting saved before the update" || fail "the setting was not saved"
mkdir -p $H/data/plugins/e2e-fake/data
echo '{"id":"e2e-fake","name":"E2E fake","version":"1.0.0"}' > $H/data/plugins/e2e-fake/manifest.json
echo "the plug-in's own data" > $H/data/plugins/e2e-fake/data/kept
chown -R tester $H/data/plugins/e2e-fake && chown -R 4242:4242 $H/data/plugins/e2e-fake/data && chmod 700 $H/data/plugins/e2e-fake/data
[ "$(version)" = "${FROM#v}" ] && pass "version ${FROM#v}" || fail "version is $(version), not ${FROM#v}"

printf '\n######## A. ./update.sh --to v0.18.90 (this build)\n'
started=$SECONDS
as "cd $H && ./update.sh --to v0.18.90" > /e2e/update-a.log 2>&1; code=$?
grep -q '^== Using the update steps from v0.18.90' /e2e/update-a.log && pass "the new release's own update.sh took over (DASH-429)" || echo "note: no hand-over (the same update.sh)"
if [ "$code" = 0 ] && grep -q '^== Updated to v0.18.90' /e2e/update-a.log; then pass "updated in $((SECONDS - started)) s"; else fail "update.sh ended with $code"; tail -30 /e2e/update-a.log; fi
sign_in
[ "$(version)" = "0.18.90" ] && pass "it answers as 0.18.90" || fail "it answers as $(version)"
[ "$(setting)" = "E2E kept" ] && pass "the setting is kept" || fail "the setting was lost: $(setting)"
plugin_kept && pass "the plug-in's own data is kept, still its user's (DASH-415)" || fail "the plug-in's data was changed or lost"

printf '\n######## B. The way back: ./update.sh --to v0.18.91 (cannot start)\n'
started=$SECONDS
as "cd $H && ./update.sh --to v0.18.91" > /e2e/update-b.log 2>&1; code=$?
if [ "$code" != 0 ] && grep -q '^Back on v0.18.90 with your settings restored' /e2e/update-b.log; then pass "it went back by itself in $((SECONDS - started)) s"; else fail "no way back (exit $code)"; tail -30 /e2e/update-b.log; fi
answers 30 && sign_in
[ "$(version)" = "0.18.90" ] && pass "back on 0.18.90" || fail "it answers as $(version)"
[ "$(setting)" = "E2E kept" ] && pass "the setting is as it was" || fail "the setting was lost: $(setting)"
plugin_kept && pass "the plug-in's own data is as it was" || fail "the plug-in's data was changed or lost after going back"

printf '\n######## C. Update now: the updater helper from inside Starboard, to v0.18.92\n'
started=$SECONDS
said="$(docker exec starboard python -c '
from starboard import self_update
p = self_update.plan("/data", "/app")
print("plan", p["how"], p["folder"], p["uid"])
self_update.save("/data", {"state": "running", "by": "you", "from": "0.18.90", "to": "v0.18.92"})
open("/data/self-update.log", "w").write("== Preparing the update\n")
self_update.launch(p, "v0.18.92")
print("launched")' 2>&1)"
echo "$said"
if echo "$said" | grep -q launched; then
  for _ in $(seq 1 120); do grep -q '^@@ finished' $H/data/self-update.log 2>/dev/null && break; sleep 3; done
  if grep -q '^@@ finished 0' $H/data/self-update.log && grep -q '^== Updated to v0.18.92' $H/data/self-update.log; then pass "Update now's helper updated it in $((SECONDS - started)) s"
  else fail "Update now's helper did not finish"; tail -30 $H/data/self-update.log; fi
  answers 60 && sign_in
  [ "$(version)" = "0.18.92" ] && pass "it answers as 0.18.92" || fail "it answers as $(version)"
  [ "$(setting)" = "E2E kept" ] && pass "the setting is kept" || fail "the setting was lost: $(setting)"
  plugin_kept && pass "the plug-in's own data is kept" || fail "the plug-in's data was changed or lost"
  docker ps -a --filter label=starboard.self-update --format '{{.Names}}' | grep -q . && fail "the helper container was left behind" || pass "the helper removed itself"
else
  fail "Update now's helper could not start: $said"
fi

printf '\n######## D. An app and Reelix, as Settings, Updates and Apps, Updates update them\n'
docker run -d --name e2e-registry --restart no -p 127.0.0.1:5000:5000 registry:2 >/dev/null
as "cd $H && E2E_FAILED=0 REELIX=$REELIX REELIX_TO='$REELIX_TO' python3 -I /e2e-tools/apps.py" ; [ $? = 0 ] || FAILED=$((FAILED + 1))

printf '\n######## Clean up\n'
as "cd $H && docker compose down -v --rmi local" >/dev/null 2>&1 || true
docker ps -aq | xargs -r docker rm -f >/dev/null 2>&1 || true
docker image rm -f $(docker images -q 'starboard:local' 'starboard-updater' 'localhost:5000/*' '127.0.0.1:5000/*' 2>/dev/null) >/dev/null 2>&1 || true
docker image prune -f >/dev/null 2>&1 || true  # inside the sealed Docker only: its dangling builds
echo
if [ "$FAILED" = 0 ]; then echo "The end-to-end update test passed."; else echo "$FAILED checks failed."; fi
exit "$FAILED"
INNER
