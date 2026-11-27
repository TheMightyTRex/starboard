"""Updates as runs you can follow (DASH-424): one place that knows what can be updated (Starboard, Reelix, the other
apps and the plug-ins), starts an update, says how it is going step by step, and rolls a plug-in back. The plug-in's
own page and Starboard's API (/api/v1/updates, with the updates scope) both use it.

Each kind reuses what already does the work:
- Starboard: self_update (update.sh in the updater helper, with its backup, health check and way back).
- Reelix: reelix_updates.run (a copy of its settings, the new image, five minutes to answer healthy, or back).
- Another app: containers.update keeping the old image, two minutes to be running and not unhealthy, or back with
  containers.go_back; its old image is removed once the new one is healthy.
- A plug-in: plugin_update.update_safely (before, settings migration, install, health, after; back by itself).

Nothing is checked or fetched here that the pages do not already: what can be updated comes from Starboard's
release check, the last check for app updates and the catalogues already read. One update runs at a time, in its own
thread, which ends with it. The last 20 runs are kept in data/update-runs.json, so a page or a script can read how
one ended after Starboard restarted.
"""
import collections
import json
import os
import re
import threading
import time
import uuid

from . import api_v1, logs

RUNS = "update-runs.json"
KEEP = 20
APP_HEALTHY_WITHIN = 120
APP_STEADY = 15  # seconds an updated app must stay running, with no restart, to count as working
_lock = threading.Lock()
_active = {}  # run id -> thread, while it runs
_runs = collections.OrderedDict()
_loaded = set()


class Busy(Exception):
    """Another update is running: 409."""


class Watching(Busy):
    """The media server's container would restart while someone is watching (DASH-566): an update by itself, or one of Install all
    updates, waits for nobody to be watching. `people` says how many."""

    def __init__(self, words, people=0):
        super().__init__(words)
        self.people = people


class Refused(Exception):
    """Starboard cannot do it, in words for the page and the API: 409."""


# The record ---------------------------------------------------------------------------------------------------

def _path(data_dir):
    return os.path.join(data_dir, RUNS)


def _load(data_dir):
    if data_dir in _loaded:
        return
    _loaded.add(data_dir)
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            for r in json.load(f) or []:
                if isinstance(r, dict) and r.get("id"):
                    _runs[r["id"]] = r
    except (OSError, ValueError):
        pass


def _save(data_dir):
    keep = list(_runs.values())[-KEEP:]
    tmp = _path(data_dir) + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(keep, f)
    os.replace(tmp, _path(data_dir))


def _new(data_dir, target, kind, name, action, came, going, by, steps, extra=None):
    run = {**(extra or {}), "id": uuid.uuid4().hex[:12], "target": target, "kind": kind, "name": name, "action": action,
           "from": came or "", "to": going or "", "by": by, "started": time.time(), "finished": None, "state": "running",
           "said": "", "steps": [{"id": k, "label": label, "state": "waiting", "detail": ""} for k, label in steps]}
    with _lock:
        _load(data_dir)
        _runs[run["id"]] = run
        while len(_runs) > KEEP:  # the oldest goes, but never a running batch (DASH-454), whose updates come after it
            old = next((k for k, r in _runs.items() if not (r.get("kind") == "batch" and r["state"] == "running")), None)
            _runs.pop(old if old else next(iter(_runs)))
        _save(data_dir)
    api_v1.audit(data_dir, "update_started" if action == "update" else "rollback_started", target=target, version=going or "",
                 previous=came or "", by=by)
    return run


def _step(data_dir, run, step, state, detail=""):
    with _lock:
        found = next((s for s in run["steps"] if s["id"] == step), None)
        if not found:  # going back appears only when it is needed
            found = {"id": step, "label": f"Going back to {run['from']}" if run["from"] else "Going back", "state": "waiting", "detail": ""}
            run["steps"].append(found)
        # skipped from a step means it does not apply (no before step, not active): not-needed, left out of the dialog
        found.update(state={"now": "working", "skipped": "not-needed"}.get(state, state), detail=str(detail or "")[:300])
        _save(data_dir)


def _end(data_dir, run, state, said, app=None):
    with _lock:
        run.update(state=state, said=str(said or "")[:600], finished=time.time())
        for s in run["steps"]:
            if s["state"] in ("waiting", "working"):
                s["state"] = "skipped" if state != "updated" else "done"
        _active.pop(run["id"], None)
        _save(data_dir)
    api_v1.audit(data_dir, "update_finished", target=run["target"], action=run["action"], state=state, version=run["to"])
    ok = state in ("updated", "rolled-back", "up-to-date")
    logs.event("info" if ok else "error", "updates", f"{run['name']}: {said}")
    # Activity, History, Across apps (DASH-68): one entry for each app, plug-in or Starboard part that was updated or
    # was not. A roll back someone asked for, nothing to do, and Install all updates' own summary write nothing.
    if state in ("updated", "failed", "went-back", "refused") and run.get("action") != "update-all" and not run.get("items"):
        from . import activity_log
        versions = " to ".join(str(v) for v in (run.get("from"), run.get("to")) if v)
        activity_log.note("upgraded" if state == "updated" else "failed", run["name"],
                          f"{run['name']} updated{' from ' + versions if run.get('from') and run.get('to') else ' to ' + versions if versions else ''}"
                          if state == "updated" else f"{run['name']} was not updated", "" if state == "updated" else said, key=f"update:{run['id']}")
    watch = getattr(app, "watch", None)
    if watch and not ok:
        try:
            watch.alert(f"update:{run['target']}:{run['id']}", f"{run['name']} was not updated", str(said), "problem")
        except Exception as e:  # noqa: BLE001  the alert is a help, never a stop
            logs.error("updates", f"The update alert was not sent: {e}", e)


def _go(data_dir, run, work):
    def body():
        try:
            work()
        except Exception as e:  # noqa: BLE001  any failure ends the run with words, never a stuck "running"
            logs.error("updates", f"{run['name']}: the update stopped: {e}", e)
            _end(data_dir, run, "failed", f"It stopped: {str(e)[:200]}")
    t = threading.Thread(target=body, name=f"update-{run['kind']}", daemon=True)
    with _lock:
        _active[run["id"]] = t
    t.start()


def _starboard_running(app):
    from . import self_update
    return self_update.running(self_update.load(app.data_dir), data_dir=app.data_dir)


def _busy():
    with _lock:
        return any(t.is_alive() for t in _active.values())


# What can be updated -------------------------------------------------------------------------------------------------

def targets(app):
    """Everything Starboard can update, from what it already knows: [{id, kind, name, current, latest,
    update_available, can_update, why, can_roll_back, roll_back_to, note}]; an app or Reelix also has big_change
    (a new major version, from the last look at its image) and icon ({service, v}); a plug-in has logo ({url, alt}
    or None)."""
    from . import containers, self_update
    from . import plugins_admin as pa
    out = []
    try:
        s = self_update.status(app)
        out.append({"id": "starboard", "kind": "starboard", "name": "Starboard", "current": s["current"], "latest": (s.get("latest") or "").lstrip("v"),
                    "update_available": bool(s["newer"]), "can_update": bool(s["newer"] and s["can"] and not s["running"]),
                    "why": s.get("why") or ("" if s["newer"] else "Starboard is up to date"), "can_roll_back": False,
                    "roll_back_to": "", "note": "Starboard goes back by itself when the new version does not answer"})
    except Exception as e:  # noqa: BLE001  one part that cannot be read never hides the others
        out.append({"id": "starboard", "kind": "starboard", "name": "Starboard", "current": getattr(app, "version", ""), "latest": "",
                    "update_available": False, "can_update": False, "why": str(e)[:200], "can_roll_back": False, "roll_back_to": "", "note": ""})
    services = app.config.data["services"]
    if containers.available():
        try:
            rows = containers.apps(services)["items"]
        except containers.DockerError:
            rows = []
        for r in rows:
            if not r.get("container"):
                continue
            reelix = _is_reelix(services, r["id"])
            svc = next((x for x in services if x.get("id") == r["id"]), {})
            out.append({"id": "reelix" if reelix else f"app:{r['id']}", "kind": "reelix" if reelix else "app", "name": r["name"],
                        # its icon, as Starboard keeps it for the dashboard (/api/icons/<id>), for What is new (DASH-475)
                        "icon": {"service": r["id"], "v": str(svc.get("icon") or "")},
                        "current": r["container"].get("version") or "", "latest": r.get("latest") or "",
                        "update_available": bool(r.get("update")), "can_update": bool(r.get("update")) and r["container"].get("compose", False),
                        "why": "" if r.get("update") else ("Check for updates first" if "update" not in r else "Up to date"),
                        "can_roll_back": False, "roll_back_to": "", "big_change": bool(r.get("update") and r.get("big_change")),
                        "note": "Goes back by itself when the new version is not healthy"})
    return out + plugin_targets(app)


def plugin_targets(app):
    """Starboard's plug-ins, as targets() lists them (Settings, Updates; Settings, Plug-ins, Manage and Updates,
    Plug-ins use these same rows)."""
    from . import plugin_life, plugin_systems
    from . import plugins_admin as pa
    services = app.config.data["services"]
    out = []
    known = plugin_life.updates_known(app.data_dir)
    for p in pa.listing(app.data_dir):
        if p.get("builtin"):
            continue
        u = known.get(p["id"])
        st = p.get("status") or {}
        out.append({"id": f"plugin:{p['id']}", "kind": "plugin", "name": p["name"], "current": p.get("version") or "",
                    "latest": (u or {}).get("version") or "", "update_available": bool(u), "can_update": bool(u),
                    "why": "" if u else "No newer version is known from the catalogues", "can_roll_back": bool(st.get("can_roll_back")),
                    "roll_back_to": st.get("previous_version") or "", "note": (u or {}).get("changelog") or "",
                    "logo": p.get("logo"),  # {url, alt} of its own logo, or None for its initials (DASH-475)
                    # the system it needs, and whether it is here (DASH-567), said in Ready to update
                    "system": plugin_systems.judge(p.get("system"), plugin_systems.present_in(services))})
        if u:  # the same words on every page that lists it: what it newly asks for, and why it waits for the owner
            from . import plugin_updates
            out[-1].update(plugin_updates.waiting_words(app, p["id"], p.get("version") or "", u))
    return out


def counts(items):
    """How many updates wait, in one place (the pages, the alert and the API all say this number): {total, by_kind}."""
    waiting = [t for t in items if t.get("update_available")]
    by_kind = {}
    for t in waiting:
        by_kind[t["kind"]] = by_kind.get(t["kind"], 0) + 1
    return {"total": len(waiting), "by_kind": by_kind}


def _is_reelix(services, sid):
    s = next((x for x in services if x.get("id") == sid), None)
    return bool(s and s.get("icon") == "reelix" and s.get("type") == "link")


def _media_dir(app):
    from . import stack
    media = (stack.env_values(app.data_dir).get("DATA_DIR") or "").rstrip("/")
    return f"{media}/media" if media else "/nonexistent-media-folder"


# Starting ---------------------------------------------------------------------------------------------------------

def start(app, target, by="you", address="", note=None, batch=None):
    """Starts an update of `target` (starboard, reelix, app:<id> or plugin:<id>) to the newest version Starboard
    knows. `address`: a plug-in's own manifest address (the page's Update from an address; never from the API).
    `batch`: the id of the Install all updates run starting it (DASH-454), which is itself the update running.
    Returns the run. Raises LookupError, Refused or Busy."""
    target = str(target or "")
    if not re.match(r"^(starboard|reelix|app:[A-Za-z0-9_-]{1,64}|plugin:[a-z0-9-]{3,40})$", target):
        raise ValueError("target must be starboard, reelix, app:<id> or plugin:<id>, from /api/v1/updates")
    if (not batch and _busy()) or _starboard_running(app):
        raise Busy("An update is already running. Wait for it to finish")
    if batch and batch not in _active:
        raise Busy("Install all updates has stopped")
    if by != "automatic":  # DASH-422: by hand, a version the automatic update stopped trying is tried again
        from . import auto_updates
        auto_updates.forget_skip(app.data_dir, target)
    if target == "starboard":
        return _start_starboard(app, by)
    if target.startswith("app:") and (by == "automatic" or batch):  # by hand, your own click is the go-ahead
        from . import mediaserver
        n = mediaserver.watching(app.config.data, target.split(":", 1)[1])
        if n:
            raise Watching(f"{n} {'person is' if n == 1 else 'people are'} watching, so the media server is not restarted now", n)
    if target == "reelix" or target.startswith("app:"):
        return _start_app(app, target, by)
    return _start_plugin(app, target.split(":", 1)[1], by, address)


def _start_starboard(app, by):
    from . import self_update
    latest = app.latest_release()
    if not latest or not self_update.newer(latest, app.version):
        raise Refused("Starboard is up to date: no newer release is known")
    run = _new(app.data_dir, "starboard", "starboard", "Starboard", "update", app.version, latest.lstrip("v"), by,
               [(k, label) for k, label in self_update.STEPS], extra={"delegate": "self-update"})
    try:
        self_update.start(app, latest, by="api" if by.startswith("api") else "you")
    except self_update.Refused as e:
        _end(app.data_dir, run, "refused", str(e), app)
        raise Refused(str(e)) from None
    return run


def _start_app(app, target, by):
    from . import containers, reelix_updates
    if not containers.available():
        raise Refused("Starboard has no Docker access, so it cannot update apps")
    services = app.config.data["services"]
    if target == "reelix":
        sid = next((s["id"] for s in services if _is_reelix(services, s["id"])), None)
        if not sid:
            raise LookupError("Reelix is not on your apps")
    else:
        sid = target.split(":", 1)[1]
        if _is_reelix(services, sid):
            target = "reelix"
    row = next((r for r in containers.apps(services)["items"] if r["id"] == sid and r.get("container")), None)
    if not row:
        raise LookupError("No app with that id runs in a container Starboard knows")
    if target == "reelix":
        run = _new(app.data_dir, target, "reelix", row["name"], "update", row["container"].get("version"), row.get("latest"), by,
                   [("check", "Finding the new version"), ("backup", "Saving a copy of its settings"),
                    ("install", "Installing the new version"), ("health", "Waiting for it to answer healthy")])

        def work():
            said = reelix_updates.run(app.config, app.data_dir, progress=lambda *a: _step(app.data_dir, run, *a))
            state = ("up-to-date" if "up to date" in said else "went-back" if "went back" in said
                     else "updated" if "healthy" in said else "refused")
            _end(app.data_dir, run, state, said, app)
        _go(app.data_dir, run, work)
        return run
    if not row.get("update"):
        raise Refused(f"No newer version of {row['name']} is known. Check for updates first: POST /api/v1/containers/check, or Check on Apps, Updates")
    if not row["container"].get("compose"):
        raise Refused(f"{row['name']} was not started by Docker Compose, so Starboard cannot update it")
    run = _new(app.data_dir, target, "app", row["name"], "update", row["container"].get("version"), row.get("latest"), by,
               [("backup", "Saving a copy of its settings"), ("install", "Getting and installing the new version"),
                ("health", "Waiting for it to run")])

    def work():
        found = containers.containers()
        before = next((c for c in found if c["name"] == row["container"]["name"]), None)
        pinned = bool(row.get("target_tag"))
        # DASH-422: a copy of its settings first, as Reelix's, so the update never loses them.
        _step(app.data_dir, run, "backup", "now")
        state, said = save_app_settings(before) if before else ("skipped", "It was not found")
        _step(app.data_dir, run, "backup", state, said)
        _step(app.data_dir, run, "install", "now")
        containers.update(services, [sid], keep_old=True)
        while not (containers.job() or {}).get("finished"):
            time.sleep(3)
        item = ((containers.job() or {}).get("items") or {}).get(row["container"]["name"]) or {}
        if item.get("phase") != "done":
            _step(app.data_dir, run, "install", "failed", item.get("error") or "")
            if before and (not pinned or (item.get("error") or "").startswith("The restart did not finish")):  # a download that failed changed nothing
                _back(app, run, before, row, pinned)
                return _end(app.data_dir, run, "went-back", f"{row['name']} did not start on the new version, so it went back. {item.get('error') or ''}".strip(), app)
            return _end(app.data_dir, run, "failed", f"{row['name']} was not updated. {item.get('error') or ''}".strip(), app)
        _step(app.data_dir, run, "install", "done", item.get("version") or "")
        _step(app.data_dir, run, "health", "now")
        ok, why = _app_healthy(row["container"]["name"])
        if ok:
            if before:
                containers.forget_old(before["image_id"])
            if pinned and before:
                _kept_image(app, before["image"], _new_ref(before["image"], row["target_tag"]))
            _step(app.data_dir, run, "health", "done", "It is running")
            return _end(app.data_dir, run, "updated", f"{row['name']} is updated and running", app)
        _step(app.data_dir, run, "health", "failed", why)
        if before:
            _back(app, run, before, row, pinned)
            return _end(app.data_dir, run, "went-back", f"{row['name']}'s new version {why.lower()}, so Starboard went back to the version before", app)
        _end(app.data_dir, run, "failed", f"{row['name']}'s new version {why.lower()}, and the version before was not found to go back to", app)
    _go(app.data_dir, run, work)
    return run


def _new_ref(image, tag):
    return image.rsplit(":", 1)[0] + ":" + tag


def _kept_image(app, old, new):
    """The tag an update wrote into the Compose file goes into data/stack/kept.json too (DASH-547)."""
    from . import stack
    try:
        stack.keep_image(app.data_dir, old, new)
    except OSError:
        pass


def _back(app, run, before, row, pinned):
    """Puts an app back on the version it ran: the old image under its tag, or, for an image pinned to a tag, the old
    tag in the Compose file again (the old image was kept)."""
    from . import containers
    _step(app.data_dir, run, "going-back", "now")
    if pinned:
        containers.go_back_pinned(before, _new_ref(before["image"], row["target_tag"]))
    else:
        containers.go_back(before, before["image_id"])
    _step(app.data_dir, run, "going-back", "done")


# What is left out of an app's settings copy: what the app makes again by itself, and can be many gigabytes
# (Jellyfin's metadata and transcodes, the *arr apps' MediaCover and their own backups).
NOT_COPIED = ("cache", "metadata", "data/metadata", "transcodes", "data/transcodes", "MediaCover", "logs", "log",
              "Backups", "backups", "Cache")


def save_app_settings(c):
    """A copy of an app's settings folder (/config) before its update, as <container>-before-update.tgz beside its
    Compose file, made in a short-lived container that shares the app's folders (as reelix_updates._save_settings).
    Returns (step state, words): done; skipped when there is nothing to copy (no /config, not started by Compose);
    failed when the copy could not be made, and the update carries on without it."""
    from . import containers
    name = str(c.get("name") or "")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$", name) or not c.get("folder"):
        return "skipped", "It was not started by Docker Compose, so no copy was made"
    try:
        info = containers.docker("GET", f"/containers/{c['id']}/json")
    except containers.DockerError as e:
        return "failed", f"Docker did not say where its settings are, so it carries on without a copy: {e}"
    if not any(m.get("Destination") == "/config" for m in info.get("Mounts") or []):
        return "skipped", "It keeps no settings folder (/config) to copy"
    leave_out = " ".join(f"--exclude=config/{x}" for x in NOT_COPIED)
    copy = f"{name}-before-update.tgz"
    script = (f"docker run --rm --volumes-from {name} --entrypoint tar {containers.HELPER_IMAGE} czf - -C / {leave_out} config "
              f"> {copy}.new && mv {copy}.new {copy}")
    code, text = containers._helper(c["folder"], script)
    if code != 0:
        return "failed", f"The copy could not be made, so it carries on without one: {text.strip()[-160:]}"
    return "done", f"{copy}, beside its Compose file"


def _run_mark(containers, c):
    """What tells one run of a container from the next: its id, restart count and start time (one Docker call)."""
    try:
        info = containers.docker("GET", f"/containers/{c['id']}/json") or {}
    except Exception:  # noqa: BLE001  unknown: the list's status is used alone
        return c.get("id"), None, None
    return c.get("id"), info.get("RestartCount"), (info.get("State") or {}).get("StartedAt")


def _app_healthy(name, wait=None, sleep=time.sleep, clock=time.monotonic):
    """Running, and not unhealthy, within two minutes, and still running APP_STEADY seconds later with no restart in
    between: a version that exits at once and is started again by its restart policy is running for a moment between
    tries, which is not a working app (found by the release 0.19.0 end-to-end test). A container whose health check is
    still starting is waited for."""
    from . import containers
    until = clock() + (APP_HEALTHY_WITHIN if wait is None else wait)
    why, since, seen = "did not start", None, None
    while True:
        c = next((x for x in containers.containers() if x["name"] == name), None)
        status = (c or {}).get("status", "")
        ok = c and c.get("state") == "running" and "(unhealthy)" not in status and "health: starting" not in status
        mark = _run_mark(containers, c) if ok else None
        if ok and since is not None and mark == seen:
            if clock() - since >= APP_STEADY:
                return True, ""
        elif ok:
            since, seen = clock(), mark
        else:
            since = None
            why = ("was not healthy" if "(unhealthy)" in status else "did not start" if not c or c.get("state") != "running"
                   else "was still starting")
        if clock() >= until:
            if since is not None:
                why = "kept stopping and starting again"
            return False, f"{why[:1].upper()}{why[1:]} within {APP_HEALTHY_WITHIN // 60} minutes"
        sleep(3 if since is not None else 5)


def _start_plugin(app, pid, by, address):
    from . import plugin_life, plugin_update
    from . import plugins_admin as pa
    p = next((x for x in pa.listing(app.data_dir) if x["id"] == pid), None)
    if not p:
        raise LookupError("No plug-in with that id")
    if p.get("builtin"):
        raise Refused("A plug-in built into Starboard updates with Starboard")
    known = plugin_life.updates_known(app.data_dir).get(pid)
    if address:
        manifest, source = pa.fetch_manifest(address), address
    elif known:
        manifest, source = pa.fetch_manifest(known["manifest"], sha256=known.get("sha256", "")), known["manifest"]
    else:
        raise Refused("No newer version is known. Use Check now on the plug-in's Versions tab, or give an address on the plug-in's page")
    if manifest.get("id") != pid:
        raise ValueError("That manifest is for another plug-in")
    from . import plugins
    problems = plugins.check(manifest)
    if problems:
        raise ValueError("This version cannot be used: " + "; ".join(problems[:6]))
    if plugins.builds(manifest):  # API 1.15 (DASH-414): its image is built from its zip, so the zip is the way
        raise Refused(f"{p['name']} {manifest.get('version')} builds its own container, so it comes as a zip file. "
                      "Use Update from a zip file on its page")
    logo = pa.fetch_logo(manifest, source)[0]  # its logo goes with the version (API 1.14); Roll back brings the old one back
    if address:  # DASH-422: the automatic update looks for its next version at the same address
        from . import auto_updates
        auto_updates.remember_address(app.data_dir, pid, address)
    run = _new(app.data_dir, f"plugin:{pid}", "plugin", p["name"], "update", p.get("version"), manifest.get("version"), by,
               plugin_update.STEPS)
    media = _media_dir(app)

    def work():
        r = plugin_update.update_safely(app.data_dir, pid, manifest, media, services=app.config.data["services"],
                                        note="" if address else (known or {}).get("changelog", ""), logo=logo,
                                        progress=lambda *a: _step(app.data_dir, run, *a))
        _end(app.data_dir, run, r["outcome"], r["said"], app)
        _after_plugins(app)
    _go(app.data_dir, run, work)
    return run


def _after_plugins(app):
    for name in ("plugin_clock", "plugin_idle"):
        thing = getattr(app, name, None)
        if thing is not None:
            thing.ensure()


def rollback(app, target, by="you"):
    """Rolls a plug-in back to the version kept before its last update. Starboard and the apps go back by themselves
    when a new version does not answer; going back later is done on the server (./update.sh --to)."""
    from . import plugin_update
    from . import plugins_admin as pa
    target = str(target or "")
    if target == "starboard":
        raise Refused("Starboard goes back by itself when a new version does not answer. To go back later, run ./update.sh --to v0.17.0 "
                      "(the version you want) on the server")
    if target == "reelix" or target.startswith("app:"):
        raise Refused("An app goes back by itself when its new version is not healthy; its old image is not kept after that")
    m = re.match(r"^plugin:([a-z0-9-]{3,40})$", target)
    if not m:
        raise ValueError("target must be plugin:<id>, from /api/v1/updates")
    pid = m.group(1)
    p = next((x for x in pa.listing(app.data_dir) if x["id"] == pid), None)
    if not p:
        raise LookupError("No plug-in with that id")
    if not (p.get("status") or {}).get("can_roll_back"):
        raise Refused(f"{p['name']} has no earlier version kept to go back to")
    if _busy() or _starboard_running(app):
        raise Busy("An update is already running. Wait for it to finish")
    run = _new(app.data_dir, target, "plugin", p["name"], "rollback", p.get("version"), p["status"].get("previous_version"), by,
               plugin_update.ROLLBACK_STEPS)
    media = _media_dir(app)

    def work():
        r = plugin_update.rollback_safely(app.data_dir, pid, media, services=app.config.data["services"],
                                          progress=lambda *a: _step(app.data_dir, run, *a))
        _end(app.data_dir, run, r["outcome"], r["said"], app)
        _after_plugins(app)
    _go(app.data_dir, run, work)
    return run


# Reading ------------------------------------------------------------------------------------------------------------

def _live(app, run):
    """A run as it is now: Starboard's own update is read from its record, which outlives the restart; any other run
    left running when Starboard restarted has stopped."""
    if run.get("kind") == "starboard" and run.get("delegate") == "self-update" and run["state"] == "running":
        from . import self_update
        j = self_update.job(app)
        states = {"working": "working", "done": "done", "waiting": "waiting", "failed": "failed", "skipped": "skipped"}
        run["steps"] = [{"id": t["id"], "label": t["label"], "state": states.get(t["state"], "waiting"), "detail": ""} for t in j.get("tasks") or []]
        if j.get("finished"):
            run.update(state={"updated": "updated", "up-to-date": "up-to-date", "went-back": "went-back", "refused": "refused"}.get(j.get("outcome"), "failed"),
                       said=j.get("text") or "", finished=time.time())
    elif run.get("kind") == "batch":  # Install all updates (DASH-454): its end may come after Starboard restarted
        from . import update_batch
        update_batch.settle(app, run)
    elif run["state"] == "running" and run["id"] not in _active:
        run.update(state="failed", said="Starboard restarted while it ran, so it did not finish. Check the plug-in's or app's state")
    return run


def get(app, rid):
    with _lock:  # a copy, taken while no step is being written
        _load(app.data_dir)
        run = json.loads(json.dumps(_runs[rid])) if rid in _runs else None
    if not run:
        raise LookupError("No update run with that id")
    return _live(app, run)


def recent(app):
    """The last 20 runs, newest first."""
    with _lock:
        _load(app.data_dir)
        runs = json.loads(json.dumps(list(_runs.values())))
    return [_live(app, r) for r in reversed(runs)]


def public(run):
    """A run for the API: times in RFC 3339, nothing else added."""
    import datetime as dt

    def iso(t):
        return dt.datetime.fromtimestamp(t, dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if t else None
    return {"id": run["id"], "target": run["target"], "kind": run["kind"], "name": run["name"], "action": run["action"],
            "from": run["from"], "to": run["to"], "by": run["by"], "state": run["state"], "said": run["said"],
            "started_at": iso(run["started"]), "finished_at": iso(run.get("finished")),
            "steps": [{k: s[k] for k in ("id", "label", "state", "detail")} for s in run["steps"]]}


def job(app, rid):
    """A run in the shape the pages' task dialog follows (settings-core.js, taskJob)."""
    run = get(app, rid)
    finished = run["state"] != "running"
    tasks = [{"id": s["id"], "label": s["label"], "state": s["state"], "detail": s["detail"]} for s in run["steps"] if s["state"] != "not-needed"]
    working = next((t for t in tasks if t["state"] == "working"), None)
    out = {"tasks": tasks, "finished": finished, "now": working["label"] if working and not finished else "",
           "state": run["state"], "from": run["from"], "to": run["to"], "id": run["id"]}
    if finished:
        out["ok"] = True if run["state"] in ("updated", "rolled-back", "up-to-date") else None if run["state"] == "went-back" else False
        titles = {"updated": f"{run['name']} is updated", "rolled-back": f"{run['name']} is back on {run['to']}",
                  "up-to-date": f"{run['name']} is up to date", "went-back": f"{run['name']} went back to {run['from']}",
                  "refused": f"{run['name']} was not updated", "failed": "The update stopped"}
        out["title"], out["text"], out["notes"] = titles.get(run["state"], "The update stopped"), run["said"], [run["said"]]
    return out
