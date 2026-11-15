"""Automatic Reelix updates (DASH-263, DASH-95): when switched on in Settings, Update settings, Starboard installs a
new Reelix image by itself, once a day at most and in the quiet hours (DASH-417: download hours when set, otherwise
01:00 to 06:00), for the Lite or full version it runs (the fork's public images now;
upstream's once it is public, RFX-59). Reelix's own self-update is never used: Starboard does it, so it can save
Reelix's settings first and go back if the new version is not healthy.

1. Ask the image's registry whether its tag points at a newer build (containers.check).
2. Save a copy of Reelix's settings folder (/config) next to the set-up files, as reelix-before-update.tgz.
3. Update it as Apps, Updates does, keeping the old image.
4. Wait up to 5 minutes for Reelix's health check. If it does not answer healthy, put the old image back and start
   it again, and say so in the log and the alerts.
5. Note the exact build now running, its version tag such as full-0.8.7-trex.1, in reelix-installed.json (DASH-419)."""
import time
import urllib.error
import urllib.request

from . import containers, logs, reelix_version, stack

HEALTHY_WITHIN = 300


def _reelix_container():
    return next((c for c in containers.containers() if c["name"] == "reelix"), None)


def _healthy(base, wait=HEALTHY_WITHIN, sleep=time.sleep):
    began = time.time()
    while time.time() - began < wait:
        try:
            with urllib.request.urlopen(base + "/api/v1/system/health", timeout=5) as r:  # Reelix on this computer  # nosec B310
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        sleep(10)
    return False


def _save_settings(folder):
    """A copy of Reelix's /config, made in a short-lived container that shares Reelix's folders."""
    script = (f"docker run --rm --volumes-from reelix --entrypoint tar {containers.HELPER_IMAGE} czf - -C / config "
              "> reelix-before-update.tgz.new && mv reelix-before-update.tgz.new reelix-before-update.tgz")
    code, text = containers._helper(folder, script)
    if code != 0:
        raise containers.DockerError(f"Reelix's settings could not be saved first: {text[-200:]}")


def run(cfg, data_dir, progress=None):
    """One check, and an update when there is one. Returns what happened, in words. `progress(step, state, detail)`
    hears each step (DASH-424: the update API and the Apps page follow it); the automatic job passes none."""
    say = progress or (lambda *a: None)
    if not containers.available():
        return "Starboard has no Docker access, so it cannot update Reelix by itself"
    c = _reelix_container()
    if not c:
        return "Reelix does not run in a container Starboard knows"
    services = cfg.data["services"]
    reelix = next((s for s in services if s.get("icon") == "reelix" and s["type"] == "link"), None)
    if not reelix:
        return "Reelix is not on your apps"
    say("check", "now", "")
    found = containers.check(services)["items"]
    mine = next((a for a in found if a.get("id") == reelix["id"]), None)
    if not (mine and mine.get("update")):
        say("check", "done", "Reelix is up to date")
        return "Reelix is up to date"
    say("check", "done", f"Version {mine.get('latest') or 'newer'} is out")
    old_image = c["image_id"]
    say("backup", "now", "")
    _save_settings(c["folder"] or stack.host_folder(data_dir))
    say("backup", "done", "reelix-before-update.tgz, beside the set-up files")
    say("install", "now", "")
    containers.update(services, [reelix["id"]], keep_old=True)
    while not (containers.job() or {}).get("finished"):
        time.sleep(5)
    say("install", "done", "")
    say("health", "now", "")
    base = stack.reelix_url(data_dir) or reelix["url"].rstrip("/")
    if _healthy(base):
        containers.forget_old(old_image)
        reelix_version.note(data_dir, "update")  # the exact build now running (DASH-419)
        say("health", "done", "It answered healthy")
        logs.event("info", "updates", "Reelix updated and is healthy")
        return "Reelix updated and is healthy"
    say("health", "failed", f"It did not answer healthy within {HEALTHY_WITHIN // 60} minutes")
    say("going-back", "now", "")
    containers.go_back(c, old_image)  # the tag points at the image that worked again, and Reelix starts on it
    reelix_version.note(data_dir, "back")
    say("going-back", "done", "Back on the version before")
    logs.event("error", "updates", "Reelix's new version was not healthy, so Starboard went back to the previous one. "
                                   "Its settings from before are in reelix-before-update.tgz beside the set-up files")
    return "Reelix's new version was not healthy; Starboard went back to the previous one"
