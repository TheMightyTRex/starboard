#!/usr/bin/env bash
# The end-to-end update test, kept (DASH-418): real updates, in containers, never a virtual machine.
#
#   flock /mnt/pool/build-cache/heavy.lock bash tools/update_e2e.sh
#
# Everything runs inside one sealed Docker (docker:dind, privileged, capped at 3 GB and 4 processors), so nothing
# on this computer is touched: no container, image or folder of the computer's own Docker. Inside it:
#
# A. Starboard from a release to the next: the release before (FROM, default v0.18.0) installed with its own
#    install.sh, with a password, a setting and a plug-in data folder that belongs to another user, then
#    ./update.sh --to a made-up release of this build. It must answer, be the new version, and keep the setting and
#    the plug-in's data (DASH-415, DASH-429).
# B. The way back: ./update.sh to a made-up broken release (it cannot start). It must go back by itself, with the
#    setting and the plug-in's data as they were.
# C. Update now's own path: from inside the running Starboard, the updater helper (self_update.plan and launch,
#    as the page's Update now runs it), to one more made-up release. It must finish, answer and be that version.
# D. An app, as Apps, Updates and Settings, Updates update it (update_runs): a small app from a registry inside
#    the sealed Docker, updated with a copy of its settings, then to a broken version that must go back by itself.
#    With REELIX=1 (the default), Reelix by itself the same way (reelix_updates.run): the published Lite image,
#    then a broken one that must go back by itself to an answering Reelix; REELIX_TO=<tag> also updates it to that
#    published version first. A plug-in from the catalogue with Roll back is in the starboard-plugins smoke test.
#
# The sealed Docker's images are kept in /mnt/pool/build-cache/update-e2e-docker for the next run. Each run's own
# folder is removed at the end, and the container with it. Exit 0 when every stage passed.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
FROM="${FROM:-v0.18.0}"
DIND="docker:27.5.1-dind"
CACHE="${CACHE:-/mnt/pool/build-cache/update-e2e-docker}"
run_dir="$(mktemp -d /mnt/pool/build-cache/update-e2e-run.XXXXXX)"
name="starboard-update-e2e-$$"
cleanup() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  # The run's folder holds root-owned files from the sealed Docker: removed by a container, as root.
  docker run --rm -v "$run_dir:/r" alpine:3.21 sh -c 'rm -rf /r/* /r/.[!.]*' >/dev/null 2>&1 || true
  rmdir "$run_dir" 2>/dev/null || true
}
trap cleanup EXIT
mkdir -p "$CACHE"

# The releases: a copy of this repository with the made-up releases on top of this build (never pushed anywhere).
git clone -q --no-local "$here" "$run_dir/make"
git -C "$here" diff --quiet HEAD || echo "Note: uncommitted changes are not in the test; it uses the last commit."
cd "$run_dir/make"
git -c advice.detachedHead=false checkout -q "$(git -C "$here" rev-parse HEAD)"
git rev-parse -q --verify "refs/tags/$FROM" >/dev/null || { echo "There is no release $FROM" >&2; exit 2; }
G=(git -c user.name=TheMightyTRexUK -c user.email=nobody)
echo "0.18.90" > VERSION; "${G[@]}" commit -qam "E2E: this build as a release"; git tag v0.18.90
echo "0.18.91" > VERSION
printf 'raise SystemExit("E2E: this made-up release cannot start")\n' > starboard/__main__.py
"${G[@]}" commit -qam "E2E: a broken release"; git tag v0.18.91
git -c advice.detachedHead=false checkout -q v0.18.90
echo "0.18.92" > VERSION; "${G[@]}" commit -qam "E2E: the next release, for Update now"; git tag v0.18.92
git clone -q --no-local --bare . "$run_dir/origin.git"
cd "$here"

docker run --name "$name" --privileged --memory 3g --memory-swap 3g --cpus 4 \
  -e DOCKER_TLS_CERTDIR= -e FROM="$FROM" -e REELIX="${REELIX:-1}" -e REELIX_TO="${REELIX_TO:-}" \
  -v "$CACHE:/var/lib/docker" -v "$run_dir:/e2e" \
  -v "$here/tools/update_e2e_inner.sh:/e2e-tools/inner.sh:ro" -v "$here/tools/update_e2e_apps.py:/e2e-tools/apps.py:ro" \
  --entrypoint sh "$DIND" /e2e-tools/inner.sh
