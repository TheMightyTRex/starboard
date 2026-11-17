"""Automatic updates for everything (DASH-422): one design for Starboard, Reelix, your other apps, Starboard's
plug-ins (from a catalogue or from an address) and Jellyfin's own plug-ins. Each part is deactivated until the owner
chooses it, in Settings, Updates or in either set-up, and runs only in the update hours (Settings, Updates, When:
the download hours when set, otherwise 01:00 to 06:00; or always 01:00 to 06:00).

Every part keeps the same promises, through the update run it already has (update_runs.py):
- a copy first: update.sh's backup of data/ (Starboard); /config as reelix-before-update.tgz (Reelix); each app's
  /config without its caches (update_runs.save_app_settings); the plug-in's settings, kept for Roll back; a copy of
  Jellyfin's plug-ins folder;
- a health check: Starboard answers; Reelix answers healthy; the app runs and is not unhealthy; the plug-in answers
  its health path; each Jellyfin plug-in is active after Jellyfin's restart;
- the way back, by itself: every part but Jellyfin's plug-ins (Jellyfin keeps no older version, so a plug-in that
  does not start is deactivated by Jellyfin, said in an alert, and the copy is there to put back);
- what is new afterwards: Recent updates on Settings, Updates, and one alert where alerts go;
- an alert when an update failed (update_runs._end) or waits for the owner (a plug-in that asks for new
  permissions never updates by itself; a version that failed is not tried again until updated by hand).

Lightweight (DASH-421): one job each, woken hourly by Starboard's jobs thread only while a part is activated; outside
the update hours a look costs nothing (no request); inside them, once a day: the registries for the apps (the same
look as Check on Apps, Updates), the catalogues (read at most once a day anyway), each plug-in's own address, and
Jellyfin's Update plugins task. Starboard (GitHub, at most every 6 hours) and Reelix keep their own jobs.
"""
import datetime as dt
import json
import os
import threading
import time
import urllib.error

from . import logs

STATE = "auto-updates.json"
RUN_WAIT = 45 * 60  # an update run that takes longer has stopped
_lock = threading.Lock()

# The parts, in the order the pages and both set-ups show them (web/setup-answers.json has the words).
PARTS = [
    {"id": "starboard", "key": "starboard_auto_update", "job": "starboardupdate", "name": "Starboard"},
    {"id": "reelix", "key": "reelix_auto_update", "job": "reelixupdate", "name": "Reelix"},
    {"id": "apps", "key": "apps_auto_update", "job": "appsupdate", "name": "Your other apps"},
    {"id": "plugins", "key": "plugins_auto_update", "job": "pluginsupdate", "name": "Starboard plug-ins"},
    {"id": "jellyfin_plugins", "key": "jellyfin_plugins_auto_update", "job": "jellyfinpluginsupdate", "name": "Jellyfin's plug-ins"},
]
KEYS = {p["id"]: p["key"] for p in PARTS}

# How each part is kept safe, for Settings, Updates (the same words in the help).
SAFETY = {
    "starboard": {"copy": "Your settings (data/), by update.sh", "check": "Starboard answers within a minute",
                  "back": "By itself, with your settings as they were"},
    "reelix": {"copy": "Reelix's settings, as reelix-before-update.tgz", "check": "Reelix answers healthy within 5 minutes",
               "back": "By itself, to the image before"},
    "apps": {"copy": "Each app's settings folder, without its caches", "check": "It runs, and is not unhealthy, within 2 minutes",
             "back": "By itself, to the image before (not for an app whose Compose file names the new version)"},
    "plugins": {"copy": "Its settings, kept for Roll back", "check": "It answers its health path",
                "back": "By itself, with your settings as they were; Roll back later on its page"},
    "jellyfin_plugins": {"copy": "Jellyfin's plug-ins folder, as jellyfin-plugins-before-update.tgz", "check": "Each plug-in is active after Jellyfin restarts",
                         "back": "Not by itself: Jellyfin keeps no older version. A plug-in that does not start is deactivated by Jellyfin, and the copy can be put back"},
}


# The record ---------------------------------------------------------------------------------------------------------

def _path(data_dir):
    return os.path.join(data_dir, STATE)


def load(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data_dir, data):
    tmp = _path(data_dir) + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, _path(data_dir))


def _change(data_dir, fn):
    with _lock:
        data = load(data_dir)
        fn(data)
        _save(data_dir, data)
        return data


def skipped(data_dir, target, version):
    """A version that failed by itself waits for an update by hand (as Starboard's own automatic update)."""
    return bool(version) and (load(data_dir).get("skip") or {}).get(target) == version


def forget_skip(data_dir, target):
    """An update by hand tries the version again, so the automatic update may too afterwards."""
    if target in (load(data_dir).get("skip") or {}):
        _change(data_dir, lambda d: (d.get("skip") or {}).pop(target, None))


def remember_address(data_dir, pid, address):
    """A plug-in added or updated from its own address (not a catalogue): the automatic update looks there."""
    from . import plugins_admin as pa
    where = os.path.join(pa.folder(data_dir, pid), "state.json")
    st = pa._read(where, {}) or {}
    if address and st.get("update_address") != address:
        st["update_address"] = str(address)[:500]
        pa._write(where, st)


# When ---------------------------------------------------------------------------------------------------------------

def in_hours(cfg_data, now=None):
    from . import self_update
    return self_update.in_quiet_hours(cfg_data, now or dt.datetime.now())


def hours_words(cfg_data):
    from . import self_update
    start, end = self_update.update_hours(cfg_data)
    which = ("your download hours" if (cfg_data or {}).get("auto_update_hours", "download") == "download"
             and ((cfg_data or {}).get("download_hours") or {}).get("enabled") else "the quiet hours")
    return f"{which}, {start:02d}:00 to {end:02d}:00"


def due(app, part, now=None):
    """(True, "") when the part's automatic update should look now; otherwise (False, why)."""
    data = app.config.data
    if not data.get(KEYS[part]):
        return False, "Deactivated"
    now = now or dt.datetime.now()
    if not in_hours(data, now):
        return False, "Waiting for the update hours"
    last = (load(app.data_dir).get("last") or {}).get(part) or {}
    if last.get("day") == now.date().isoformat():
        return False, "Already looked today"
    return True, ""


# Running one update to its end ---------------------------------------------------------------------------------------

def _run(app, target, address="", wait=RUN_WAIT, sleep=time.sleep):
    """Starts an automatic update run and waits for its end. Returns {name, from, to, state, said}."""
    from . import update_runs
    try:
        run = update_runs.start(app, target, by="automatic", address=address)
    except update_runs.Busy as e:
        return {"target": target, "name": target, "state": "waiting", "said": str(e), "from": "", "to": ""}
    except (update_runs.Refused, LookupError, ValueError, OSError) as e:
        return {"target": target, "name": target, "state": "refused", "said": str(e)[:300], "from": "", "to": ""}
    until = time.monotonic() + wait
    while True:
        r = update_runs.get(app, run["id"])
        if r["state"] != "running" or time.monotonic() >= until:
            out = {k: r.get(k) for k in ("target", "name", "from", "to", "state", "said")}
            if r["state"] == "running":
                out.update(state="failed", said="It took more than 45 minutes")
            return out
        sleep(5)


def _finish(app, part, runs, now=None, extra_said=""):
    """Records the look, marks what failed so it waits for an update by hand, and sends one What is new alert for
    what updated. Returns the summary in words, for System, Jobs."""
    now = now or dt.datetime.now()
    failed = [r for r in runs if r["state"] in ("failed", "went-back", "refused")]
    updated = [r for r in runs if r["state"] == "updated"]

    def change(d):
        d.setdefault("last", {})[part] = {"day": now.date().isoformat(), "at": time.time(),
                                          "runs": [{k: r.get(k) for k in ("name", "from", "to", "state", "said")} for r in runs][:30]}
        skip = d.setdefault("skip", {})
        for r in failed:
            if r.get("to"):
                skip[r["target"]] = r["to"]
    _change(app.data_dir, change)
    if updated:
        lines = "; ".join(f"{r['name']} {r['from'] or 'before'} to {r['to'] or 'the newest'}" for r in updated)
        watch = getattr(app, "watch", None)
        if watch:
            try:
                watch.alert(f"auto-updated:{part}:{now.date().isoformat()}", "Updated by itself",
                            f"{lines}. What is new: Settings, Updates, Recent updates.", "info")
            except Exception as e:  # noqa: BLE001  the alert is a help, never a stop
                logs.error("updates", f"The What is new alert was not sent: {e}", e)
    words = []
    if updated:
        words.append(f"Updated {', '.join(r['name'] for r in updated)}")
    if failed:
        words.append(f"Not updated: {', '.join(r['name'] for r in failed)}")
    if extra_said:
        words.append(extra_said)
    return ". ".join(words) or "Everything is up to date"


# The parts ----------------------------------------------------------------------------------------------------------

def apps(app, now=None, force=False):
    """Your other apps (not Reelix, which has its own job, and not Starboard): one look at each image's registry, then
    each app with a newer version, one at a time, with a copy of its settings, a health check and the way back."""
    from . import containers, update_runs
    ok, why = (True, "") if force else due(app, "apps", now)
    if not ok:
        return why
    if not containers.available():
        return _finish(app, "apps", [], now, "Starboard has no Docker access, so it cannot update apps by itself")
    services = app.config.data["services"]
    try:
        rows = containers.check(services)["items"]
    except containers.DockerError as e:
        return _finish(app, "apps", [], now, f"Docker did not answer: {e}")
    runs = []
    for r in rows:
        c = r.get("container") or {}
        if not (r.get("update") and c.get("compose")) or update_runs._is_reelix(services, r["id"]) or c.get("name") == "starboard":
            continue
        target = f"app:{r['id']}"
        if skipped(app.data_dir, target, r.get("latest")):
            continue
        out = _run(app, target)
        out["name"] = r["name"] if out["name"] == target else out["name"]
        runs.append(out)
    return _finish(app, "apps", runs, now)


def _plugin_candidates(app):
    """Plug-ins with a newer version: from the catalogues (read at most once a day) or the plug-in's own address.
    Returns [(pid, name, current, manifest, address)], and the ones that wait for the owner, in words."""
    from . import plugin_life, plugins_admin as pa
    try:
        pa.catalogue(app.config)
    except Exception as e:  # noqa: BLE001  a catalogue that does not answer leaves the rest to update
        logs.event("warning", "updates", f"The plug-in catalogues were not read: {e}")
    known = plugin_life.updates_known(app.data_dir)
    out, waiting = [], []
    for p in pa.basics(app.data_dir):
        if p.get("builtin"):
            continue
        where = pa.folder(app.data_dir, p["id"])
        st = pa._read(os.path.join(where, "state.json"), {}) or {}
        old = pa._read(os.path.join(where, "manifest.json"), {}) or {}
        address, manifest = "", None
        try:
            if p["id"] in known:
                manifest = pa.fetch_manifest(known[p["id"]]["manifest"], sha256=known[p["id"]].get("sha256", ""))
            elif st.get("update_address"):
                address = st["update_address"]
                got = pa.fetch_manifest(address)
                if got.get("id") == p["id"] and plugin_life._newer(str(got.get("version") or "0"), p.get("version") or "0"):
                    manifest = got
        except Exception as e:  # noqa: BLE001  one plug-in that cannot be read never stops the others
            waiting.append(f"{p['name']}: its new version could not be read ({str(e)[:120]})")
            continue
        if not manifest:
            continue
        if plugin_life.new_permissions(old, manifest):
            waiting.append(f"{p['name']} {manifest.get('version')} asks for new permissions, so it waits for you")
            continue
        out.append((p["id"], p["name"], p.get("version") or "", manifest, address))
    return out, waiting


def plugins(app, now=None, force=False):
    """Starboard's plug-ins, from a catalogue or their own address, each with its update steps (before, settings,
    install, health, after) and Roll back by itself. A version that asks for new permissions waits for the owner."""
    ok, why = (True, "") if force else due(app, "plugins", now)
    if not ok:
        return why
    found, waiting = _plugin_candidates(app)
    runs = []
    for pid, name, _current, manifest, address in found:
        target = f"plugin:{pid}"
        if skipped(app.data_dir, target, manifest.get("version")):
            continue
        out = _run(app, target, address=address)
        out["name"] = name if out["name"] == target else out["name"]
        runs.append(out)
    if waiting:
        _waits(app, "plugins", waiting)
    return _finish(app, "plugins", runs, now, "; ".join(waiting))


def _waits(app, part, lines):
    watch = getattr(app, "watch", None)
    if watch:
        try:
            watch.alert(f"update-waits:{part}:{'|'.join(lines)[:200]}", "An update waits for you", "; ".join(lines) + ". See Settings, Updates.", "warning")
        except Exception as e:  # noqa: BLE001
            logs.error("updates", f"The alert was not sent: {e}", e)


# Jellyfin's own plug-ins ---------------------------------------------------------------------------------------------

JF_STEPS = [("backup", "Saving a copy of Jellyfin's plug-ins"), ("install", "Jellyfin updates its plug-ins"),
            ("restart", "Restarting Jellyfin when nobody is watching"), ("health", "Checking each plug-in is active")]
JF_TASK = "PluginUpdates"  # Jellyfin's own scheduled task, Update plugins


def _jf(services):
    from . import jellyfin_plugins
    return jellyfin_plugins.find(services)


def _jf_call(jf, method, path, body=None):
    from .livetv_jellyfin import _call
    return _call(jf["url"], jf["api_key"], method, path, body)


def jellyfin_status(app):
    """For Settings, Updates: Jellyfin's plug-ins, and whether Jellyfin's own Update plugins task is scheduled."""
    jf = _jf(app.config.data["services"])
    if not jf:
        return {"connected": False}
    try:
        plugins = _jf_call(jf, "GET", "/Plugins") or []
        task = next((t for t in _jf_call(jf, "GET", "/ScheduledTasks") or [] if t.get("Key") == JF_TASK), None)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {"connected": False, "problem": f"Jellyfin did not answer: {getattr(e, 'reason', e)}"}
    return {"connected": True, "count": len(plugins),
            "plugins": [{"name": p.get("Name"), "version": str(p.get("Version") or ""), "status": p.get("Status")} for p in plugins][:60],
            "own_schedule": bool(task and task.get("Triggers")), "has_task": bool(task)}


def take_over_schedule(app):
    """While Starboard updates Jellyfin's plug-ins (activated), Jellyfin's own Update plugins task has no schedule,
    so they update only in the update hours, with a copy first. Done once; the owner can schedule it again in
    Jellyfin. Returns True when Jellyfin's schedule was cleared now."""
    jf = _jf(app.config.data["services"])
    if not jf or load(app.data_dir).get("jellyfin_schedule_taken"):
        return False
    try:
        task = next((t for t in _jf_call(jf, "GET", "/ScheduledTasks") or [] if t.get("Key") == JF_TASK), None)
        if task and task.get("Triggers"):
            _jf_call(jf, "POST", f"/ScheduledTasks/{task['Id']}/Triggers", [])
        _change(app.data_dir, lambda d: d.update(jellyfin_schedule_taken=time.time()))
        return bool(task and task.get("Triggers"))
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _save_jellyfin_copy(app):
    """A copy of Jellyfin's plug-ins folder (official image: /config/plugins; LinuxServer: /config/data/plugins)."""
    from . import containers
    if not containers.available():
        return "skipped", "Starboard has no Docker access, so no copy was made"
    try:
        c = next((x for x in containers.containers() if x["name"] == "jellyfin" or x.get("service") == "jellyfin"), None)
    except containers.DockerError as e:
        return "failed", f"Docker did not answer, so it carries on without a copy: {e}"
    if not c or not c.get("folder"):
        return "skipped", "Jellyfin does not run in a container Starboard started, so no copy was made"
    copy = "jellyfin-plugins-before-update.tgz"
    script = (f"docker run --rm --volumes-from {c['name']} --entrypoint sh {containers.HELPER_IMAGE} -c "
              "'cd / && tar czf - $(ls -d config/plugins config/data/plugins 2>/dev/null)' "
              f"> {copy}.new && mv {copy}.new {copy}")
    code, text = containers._helper(c["folder"], script)
    if code != 0:
        return "failed", f"The copy could not be made, so it carries on without one: {text.strip()[-160:]}"
    return "done", f"{copy}, beside the set-up files"


def jellyfin_plugins_begin(app, by="automatic", batch=False):
    """Checks that Jellyfin's plug-ins can be updated now and makes the run. Returns (run, jf, task, before).
    `batch`: started by Install all updates (DASH-454), which is itself the update running.
    Raises update_runs.Refused or Busy; Jellyfin that does not answer raises URLError or OSError."""
    from . import update_runs
    jf = _jf(app.config.data["services"])
    if not jf:
        raise update_runs.Refused("Add Jellyfin with its API key in Manage apps first")
    if (not batch and update_runs._busy()) or update_runs._starboard_running(app):
        raise update_runs.Busy("An update is already running. Wait for it to finish")
    before = {p.get("Id"): p for p in _jf_call(jf, "GET", "/Plugins") or []}
    task = next((t for t in _jf_call(jf, "GET", "/ScheduledTasks") or [] if t.get("Key") == JF_TASK), None)
    if not task:
        raise update_runs.Refused("Jellyfin has no Update plugins task, so its plug-ins cannot be updated from here")
    run = update_runs._new(app.data_dir, "jellyfin-plugins", "jellyfin-plugins", "Jellyfin's plug-ins", "update", "", "", by, JF_STEPS)
    with update_runs._lock:
        update_runs._active[run["id"]] = threading.current_thread()
    return run, jf, task, before


def jellyfin_plugins_run(app, by="automatic", sleep=time.sleep, task_wait=600, restart_wait=300, begun=None, restart_later=False):
    """Jellyfin updates its own plug-ins (its Update plugins task), with a copy first; then Jellyfin restarts when
    nobody is watching, and each plug-in must be active. Returns the finished run (update_runs record). `begun`:
    what jellyfin_plugins_begin gave, when the page started it and this runs in its own thread.

    restart_later (Install all updates, DASH-454): Jellyfin is restarted once at the end of the batch, not here.
    Returns (run, pending): pending is (jf, news) when plug-ins changed and the run waits, still running, for
    jellyfin_plugins_restart; None when the run has ended."""
    from . import update_runs
    run, jf, task, before = begun or jellyfin_plugins_begin(app, by)
    with update_runs._lock:
        update_runs._active[run["id"]] = threading.current_thread()
    step = lambda *a: update_runs._step(app.data_dir, run, *a)  # noqa: E731
    later = False
    try:
        step("backup", "now")
        step("backup", *_save_jellyfin_copy(app))
        step("install", "now")
        _jf_call(jf, "POST", f"/ScheduledTasks/Running/{task['Id']}")
        until = time.monotonic() + task_wait
        while time.monotonic() < until:
            sleep(5)
            now = _jf_call(jf, "GET", f"/ScheduledTasks/{task['Id']}") or {}
            if now.get("State") != "Running":
                break
        after = {p.get("Id"): p for p in _jf_call(jf, "GET", "/Plugins") or []}
        changed = [(p.get("Name"), str((before.get(i) or {}).get("Version") or ""), str(p.get("Version") or ""))
                   for i, p in after.items() if str(p.get("Version")) != str((before.get(i) or {}).get("Version")) or p.get("Status") == "Restart"]
        if not changed:
            step("install", "done", "Every plug-in is up to date")
            update_runs._end(app.data_dir, run, "up-to-date", "Jellyfin's plug-ins are up to date", app)
            return (run, None) if restart_later else run
        news = "; ".join(f"{n} {a or 'new'} to {b}" for n, a, b in changed)
        run.update(**{"from": "", "to": ", ".join(f"{n} {b}" for n, _, b in changed)[:200]})
        step("install", "done", news)
        if restart_later:
            step("restart", "waiting", "Once, after the other updates, for all of Jellyfin's plug-ins")
            later = True
            return run, (jf, news)
        jellyfin_plugins_restart(app, run, jf, news, sleep=sleep, restart_wait=restart_wait)
        return run
    except (urllib.error.URLError, OSError, ValueError) as e:
        update_runs._end(app.data_dir, run, "failed", f"Jellyfin did not answer: {getattr(e, 'reason', e)}", app)
        return (run, None) if restart_later else run
    finally:
        if not later:  # a run waiting for its restart stays followed until jellyfin_plugins_restart ends it
            with update_runs._lock:
                update_runs._active.pop(run["id"], None)


def _watching(jf):
    return sum(1 for s in _jf_call(jf, "GET", "/Sessions") or [] if s.get("NowPlayingItem"))


def jellyfin_plugins_restart(app, run, jf, news, sleep=time.sleep, restart_wait=300, watch_wait=0, watch_look=60, waiting=None):
    """Restarts Jellyfin for its updated plug-ins, when nobody is watching, and checks each plug-in is active. Ends
    the run. watch_wait: how long to wait for nobody to be watching (Install all updates, DASH-454), calling
    waiting(how many) at each look; 0 leaves the restart for later at once when someone is watching."""
    from . import update_runs
    step = lambda *a: update_runs._step(app.data_dir, run, *a)  # noqa: E731
    try:
        step("restart", "now")
        until = time.monotonic() + watch_wait
        while True:
            n = _watching(jf)
            if not n:
                break
            if time.monotonic() >= until:
                step("restart", "skipped", "")
                update_runs._end(app.data_dir, run, "updated", f"Updated: {news}. Someone is watching, so the new versions start when Jellyfin next restarts", app)
                return run
            if waiting:
                waiting(n)
            step("restart", "now", f"Waiting: {n} watching. Jellyfin restarts when nobody is")
            sleep(watch_look)
        step("restart", "now", "")
        _jf_call(jf, "POST", "/System/Restart")
        sleep(10)
        until = time.monotonic() + restart_wait
        up = False
        while time.monotonic() < until:
            try:
                info = _jf_call(jf, "GET", "/System/Info") or {}
                if not info.get("HasPendingRestart"):
                    up = True
                    break
            except (urllib.error.URLError, OSError, ValueError):
                pass
            sleep(5)
        if not up:
            step("restart", "failed", f"Jellyfin did not answer within {restart_wait // 60} minutes")
            update_runs._end(app.data_dir, run, "failed", f"Jellyfin did not start again within {restart_wait // 60} minutes after updating {news}", app)
            return run
        step("restart", "done", "Jellyfin answers")
        step("health", "now")
        bad = [p.get("Name") for p in _jf_call(jf, "GET", "/Plugins") or [] if p.get("Status") in ("Malfunctioned", "NotSupported")]
        if bad:
            step("health", "failed", ", ".join(bad))
            update_runs._end(app.data_dir, run, "failed",
                             f"{', '.join(bad)} did not start after the update, so Jellyfin deactivated it. Jellyfin keeps no older version: "
                             "the copy from before is jellyfin-plugins-before-update.tgz beside the set-up files", app)
            return run
        step("health", "done", "Each plug-in is active")
        update_runs._end(app.data_dir, run, "updated", f"Updated: {news}", app)
        return run
    except (urllib.error.URLError, OSError, ValueError) as e:
        update_runs._end(app.data_dir, run, "failed", f"Jellyfin did not answer: {getattr(e, 'reason', e)}", app)
        return run
    finally:
        with update_runs._lock:
            update_runs._active.pop(run["id"], None)


def jellyfin_plugins(app, now=None, force=False):
    """The automatic job: moves Jellyfin's own schedule aside once, then once a day in the update hours."""
    from . import update_runs
    if not app.config.data.get(KEYS["jellyfin_plugins"]):
        return "Deactivated"
    take_over_schedule(app)
    ok, why = (True, "") if force else due(app, "jellyfin_plugins", now)
    if not ok:
        return why
    try:
        run = jellyfin_plugins_run(app)
    except (update_runs.Refused, update_runs.Busy) as e:
        return _finish(app, "jellyfin_plugins", [], now, str(e))
    except (urllib.error.URLError, OSError, ValueError) as e:
        return _finish(app, "jellyfin_plugins", [], now, f"Jellyfin did not answer: {getattr(e, 'reason', e)}")
    out = {k: run.get(k) for k in ("target", "name", "from", "to", "state", "said")}
    return _finish(app, "jellyfin_plugins", [out] if out["state"] != "up-to-date" else [], now)


# Waiting updates, for the alerts (DASH-420, DASH-421) -----------------------------------------------------------------

def waiting(app):
    """What has a newer version and will not update by itself, from what Starboard already knows (nothing is fetched):
    the plug-ins the catalogues list, and the apps from the last look at the registries. [(key, name, version)]."""
    from . import containers, plugin_life
    from . import plugins_admin as pa
    data = app.config.data
    out = []
    if not data.get("plugins_auto_update"):
        names = {p["id"]: p["name"] for p in pa.basics(app.data_dir)}
        for pid, u in plugin_life.updates_known(app.data_dir).items():
            out.append((f"plugin:{pid}", names.get(pid, pid), u["version"]))
    services = data.get("services") or []
    for name, c in list((containers._state.get("check") or {}).items()):
        if not (c.get("update") and c.get("latest")):
            continue
        reelix = name == "reelix"
        if (reelix and data.get("reelix_auto_update")) or (not reelix and data.get("apps_auto_update")):
            continue
        out.append((f"app:{name}", "Reelix" if reelix else name, c["latest"]))
    del services
    return out


def summary(app):
    """Settings, Updates: each part's setting, how it is kept safe, and its last automatic look."""
    data = app.config.data
    rec = load(app.data_dir)
    parts = []
    for p in PARTS:
        last = (rec.get("last") or {}).get(p["id"])
        parts.append({"id": p["id"], "key": p["key"], "name": p["name"], "active": bool(data.get(p["key"])),
                      "safety": SAFETY[p["id"]], "last": last})
    return {"parts": parts, "hours": data.get("auto_update_hours", "download"), "hours_words": hours_words(data),
            "download_hours": bool((data.get("download_hours") or {}).get("enabled")),
            "skip": rec.get("skip") or {}}
