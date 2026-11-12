"""A plug-in's life after it is added (DASH-330, ideas from Jellyfin and Stremio; design in
PLUGIN-SYSTEM-COMPARISON-2026-11-12): clear states with one sentence and one button each, updates that keep the
previous version for Roll back, catalogue versions checked by SHA-256 and by the Starboard API they need, events
sent to the plug-ins that asked for them, and the jobs plug-ins declare, run by Starboard's one clock.

Everything is kept in the plug-in's own folder (data/plugins/<id>/): state.json, and previous/ with the manifest,
settings and Compose file of the version before the last update. Only one previous version is kept.
"""
import datetime as dt
import hashlib
import json
import os
import shutil
import threading
import time
import urllib.request

from . import api_v1, logs, plugins
from . import plugins_admin as pa

# Each state: one sentence and one button (the button's action, for the page).
STATES = {
    "needs-setup": ("Fill in its settings, then activate it.", "Set it up", "settings"),
    "not-supported": ("This Starboard is newer than this version was made for, so it is stopped. An update may fix it.",
                      "Look for an update", "update"),
    "failed": ("It did not start, or stopped answering.", "Try again", "enable"),
}


# States -------------------------------------------------------------------------------------------------------

def missing_settings(manifest, values):
    """The labels of required settings with no value yet."""
    return [s.get("label") or s.get("key") for s in manifest.get("settings") or []
            if isinstance(s, dict) and s.get("required") and values.get(s.get("key")) in (None, "", [])]


def status(data_dir, pid, manifest=None, st=None):
    """{state, sentence, button, action, missing, can_roll_back, previous_version}. The state is the stored one
    (installed, enabled, disabled, failed) unless the plug-in needs setting up or this Starboard is past its range."""
    where = pa.folder(data_dir, pid)
    m = manifest or pa._read(os.path.join(where, "manifest.json"), {}) or {}
    st = st if st is not None else pa._read(os.path.join(where, "state.json"), {}) or {}
    values = pa._read(os.path.join(where, "settings.json"), {}) or {}
    state = st.get("state", "installed")
    missing = missing_settings(m, values)
    if m.get("starboard_api") and not plugins._range_ok(m["starboard_api"], plugins.API_VERSION):
        state = "not-supported"
    elif state != "enabled" and (missing or (m.get("setup_required") and not st.get("set_up"))):
        state = "needs-setup"
    previous = pa._read(os.path.join(where, "previous", "manifest.json"))
    out = {"state": state, "missing": missing, "can_roll_back": bool(previous),
           "previous_version": (previous or {}).get("version")}
    if state in STATES:
        sentence, button, action = STATES[state]
        if state == "needs-setup" and missing:
            sentence = f"Fill in {', '.join(missing)}, then activate it."
        if state == "failed" and st.get("message"):
            sentence = f"{sentence} {st['message'][-160:]}"
        out.update(sentence=sentence, button=button, action=action)
        # A failure soon after an update offers Roll back first (design, change 4).
        if state == "failed" and previous and time.time() - float(st.get("updated_at") or 0) < 600:
            out.update(button=f"Roll back to {previous.get('version')}", action="rollback")
    return out


def can_enable(data_dir, pid):
    """Refuses Turn on while it needs setting up or is not supported, in the words the page shows."""
    s = status(data_dir, pid)
    if s["state"] in ("needs-setup", "not-supported"):
        raise ValueError(s["sentence"])


def mark_set_up(data_dir, pid):
    """A plug-in with setup_required counts as set up once its settings are saved with nothing required missing."""
    path = os.path.join(pa.folder(data_dir, pid), "state.json")
    st = pa._read(path, {}) or {}
    if not st.get("set_up"):
        st["set_up"] = True
        pa._write(path, st)


# Catalogue versions ------------------------------------------------------------------------------------------------

def clean_versions(entry):
    """A catalogue entry's versions, newest first, each {version, starboard_api, manifest, sha256, changelog,
    released}; an entry without versions is one version from its own manifest address."""
    import re
    raw = entry.get("versions") if isinstance(entry.get("versions"), list) else [entry]
    out = []
    for v in raw[:50]:
        if not isinstance(v, dict):
            continue
        address = str(v.get("manifest") or v.get("manifest_url") or "")
        sha = str(v.get("manifest_sha256") or "").lower()
        if not re.match(r"^https://\S{1,400}$", address):
            continue
        out.append({"version": str(v.get("version") or "")[:30], "starboard_api": str(v.get("starboard_api") or "")[:40],
                    "manifest": address, "sha256": sha if re.match(r"^[0-9a-f]{64}$", sha) else "",
                    "changelog": str(v.get("changelog") or "")[:600], "released": str(v.get("released") or "")[:10]})

    def key(v):
        try:
            return tuple(int(x) for x in v["version"].split("-")[0].split("."))
        except ValueError:
            return (0,)
    return sorted(out, key=key, reverse=True)


def best_version(versions):
    """(the newest version this Starboard can run, or None; how many newer were hidden; the API they need)."""
    hidden, needs = 0, ""
    for v in versions:
        if not v["starboard_api"] or plugins._range_ok(v["starboard_api"], plugins.API_VERSION):
            return v, hidden, needs
        hidden += 1
        needs = needs or v["starboard_api"]
    return None, hidden, needs


def fetch_checked(address, sha256="", opener=None):
    """A manifest from its address; with a catalogue's SHA-256, refused when the file changed since it was listed."""
    from . import outside
    outside.check_url(address)
    req = urllib.request.Request(address, headers={"User-Agent": "Starboard", "Accept": "application/json"})
    with (opener or urllib.request.build_opener()).open(req, timeout=5) as r:  # checked above  # nosec B310
        raw = r.read(pa.MAX_MANIFEST + 1)
    if len(raw) > pa.MAX_MANIFEST:
        raise ValueError("That manifest is too large")
    if sha256 and hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("The file changed since the catalogue listed it, so Starboard did not use it")
    return pa.parse(raw)


def updates_known(data_dir):
    """For each added plug-in, a newer version from a catalogue Starboard has already read (nothing is fetched here):
    {id: {version, changelog, manifest, sha256}}."""
    out = {}
    have = {p["id"]: p for p in pa.listing(data_dir)}
    for hit in list(pa._catalogues.values()):
        for e in hit.get("items") or []:
            p = have.get(e["id"])
            v = (e.get("versions") or [None])[0] if e.get("versions") else None
            if p and v and _newer(v["version"], p.get("version") or "0") and (e["id"] not in out or _newer(v["version"], out[e["id"]]["version"])):
                out[e["id"]] = {k: v[k] for k in ("version", "changelog", "manifest", "sha256")}
    return out


def _newer(a, b):
    def parts(v):
        try:
            return tuple(int(x) for x in str(v).split("-")[0].split("."))
        except ValueError:
            return (0,)
    return parts(a) > parts(b)


# Update and Roll back --------------------------------------------------------------------------------------------

FILES = ("manifest.json", "settings.json", "compose.yaml")


def _new_key_if_scopes_changed(data_dir, pid, old, new, st):
    if plugins.key_scopes(old) == plugins.key_scopes(new) or not new.get("containers"):
        return st
    if st.get("key_id"):
        api_v1.revoke_key(data_dir, st["key_id"])
    key, item = api_v1.create_key(data_dir, f"Plug-in: {new['name']}"[:60], "read", plugins.key_scopes(new), None)
    pa._write(os.path.join(pa.folder(data_dir, pid), "key"), key)
    return {**st, "key_id": item["id"]}


def new_permissions(old, new):
    """What the new version may do that the installed one may not: shown as New in the update warning."""
    return sorted(set(new.get("permissions") or []) - set(old.get("permissions") or []))


def update(data_dir, pid, manifest, media_dir, helper=None, services=None, dev=False):
    """Installs a newer (or any other) version over an added plug-in, keeping the one before in previous/ for Roll
    back. Settings stay; new settings get their defaults. An active plug-in is started again on the new version."""
    where = pa.folder(data_dir, pid)
    old = pa._read(os.path.join(where, "manifest.json"))
    if not old:
        raise LookupError("No plug-in with that id")
    st = pa._read(os.path.join(where, "state.json"), {}) or {}
    if st.get("builtin"):
        raise ValueError("A plug-in built into Starboard updates with Starboard")
    if manifest.get("id") != pid:
        raise ValueError("That manifest is for another plug-in")
    problems = plugins.check(manifest, dev=dev)
    if problems:
        raise ValueError("This version cannot be used: " + "; ".join(problems[:6]))
    prev = os.path.join(where, "previous")
    os.makedirs(prev, mode=0o700, exist_ok=True)
    for name in FILES:
        if os.path.exists(os.path.join(where, name)):
            shutil.copy2(os.path.join(where, name), os.path.join(prev, name))
    values = pa._read(os.path.join(where, "settings.json"), {}) or {}
    for s in manifest.get("settings") or []:
        if s.get("key") not in values and "default" in s:
            values[s["key"]] = s["default"]
    st = _new_key_if_scopes_changed(data_dir, pid, old, manifest, st)
    pa._write(os.path.join(where, "manifest.json"), manifest)
    pa._write(os.path.join(where, "settings.json"), values)
    if manifest.get("containers"):
        pa._write(os.path.join(where, "compose.yaml"), plugins.compose(manifest, pa.host_path(data_dir, pid), media_dir), 0o644)
    was_on = st.get("state") == "enabled"
    st.update(updated_at=time.time(), previous_version=old.get("version"))
    pa._write(os.path.join(where, "state.json"), st)
    api_v1.audit(data_dir, "plugin_updated", plugin=pid, version=manifest.get("version"), previous=old.get("version"))
    if was_on:
        try:
            pa.enable(data_dir, pid, helper=helper, services=services)
        except ValueError:
            pass  # enable() recorded failed; the tab offers Roll back first for ten minutes
    return f"{manifest['name']} is now {manifest['version']}; {old.get('version')} is kept for Roll back"


def rollback(data_dir, pid, media_dir, helper=None, services=None):
    """Swaps the current version with the kept one (no download), and starts it again if it was on."""
    where = pa.folder(data_dir, pid)
    prev = os.path.join(where, "previous")
    old = pa._read(os.path.join(prev, "manifest.json"))
    now = pa._read(os.path.join(where, "manifest.json"))
    if not old or not now:
        raise LookupError("There is no earlier version to go back to")
    st = pa._read(os.path.join(where, "state.json"), {}) or {}
    swap = os.path.join(where, ".swap")
    os.makedirs(swap, mode=0o700, exist_ok=True)
    for name in FILES:
        here, kept = os.path.join(where, name), os.path.join(prev, name)
        if os.path.exists(here):
            shutil.move(here, os.path.join(swap, name))
        if os.path.exists(kept):
            shutil.move(kept, here)
        if os.path.exists(os.path.join(swap, name)):
            shutil.move(os.path.join(swap, name), kept)
    os.rmdir(swap)
    st = _new_key_if_scopes_changed(data_dir, pid, now, old, st)
    was_on = st.get("state") in ("enabled", "failed")
    st.update(updated_at=0, previous_version=now.get("version"), message="")
    pa._write(os.path.join(where, "state.json"), st)
    api_v1.audit(data_dir, "plugin_rolled_back", plugin=pid, version=old.get("version"), previous=now.get("version"))
    if was_on and old.get("containers"):
        try:
            pa.enable(data_dir, pid, helper=helper, services=services)
        except ValueError:
            pass
    return f"{old.get('name', pid)} is back on {old.get('version')}; {now.get('version')} is kept in case you want it again"


# Events -------------------------------------------------------------------------------------------------------

_data_dir = None


def listen(data_dir):
    """Called once at start: from then on, events go to the plug-ins that asked for them."""
    global _data_dir
    _data_dir = data_dir


def emit(event, data=None):
    """Sends one event to every active plug-in that listed it: a POST of {event, at, data} to /events on its main
    container, 3 seconds, one retry, in the background. Nothing is kept or queued."""
    if not _data_dir or event not in plugins.EVENTS:
        return 0
    from . import plugin_cards
    sent = 0
    for p in pa.listing(_data_dir):
        if p["state"] != "enabled":
            continue
        m = pa._read(os.path.join(pa.folder(_data_dir, p["id"]), "manifest.json"), {}) or {}
        if event not in (m.get("events") or []) or not m.get("containers"):
            continue
        main = m["containers"][0]
        body = json.dumps({"event": event, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "data": data or {}}).encode()

        def send(pid=p["id"], main=main, body=body):
            url = f"http://{plugin_cards._host(pid, main)}:{int(main.get('port') or 80)}/events"
            for _ in range(2):
                try:
                    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "User-Agent": "Starboard"})
                    with urllib.request.build_opener().open(req, timeout=3):  # the plug-in's own container  # nosec B310
                        return
                except OSError:
                    time.sleep(1)
        threading.Thread(target=send, name=f"event-{p['id']}", daemon=True).start()
        sent += 1
    return sent


POLLED = ("item.added", "download.finished", "playback.started")  # Starboard learns of these by checking


def listened(data_dir):
    """The events active plug-ins asked for."""
    out = set()
    for p in pa.listing(data_dir):
        if p["state"] == "enabled":
            out |= set((pa._read(os.path.join(pa.folder(data_dir, p["id"]), "manifest.json"), {}) or {}).get("events") or [])
    return out


class EventWatch:
    """New items in Jellyfin, finished downloads and playback starting, found by comparing one check with the last,
    using the same cached checks the pages use. The first check only sets the starting point, so nothing old is sent."""

    def __init__(self):
        self.seen = {}

    def check(self, wanted, app_services, send=None):
        from . import services
        send = send or emit
        sent = 0
        if wanted & {"item.added", "playback.started"}:
            jf = services.cached("jellyfin", 20, lambda: services.jellyfin(app_services))
            if jf.get("configured") is not False:
                added = {f"{a.get('type')}|{a.get('series')}|{a.get('title')}|{a.get('when')}": a for a in jf.get("added") or []}
                playing = {f"{x.get('user')}|{x.get('device')}|{x.get('title')}": x for x in jf.get("playing") or []}
                for name, now, fields in (("item.added", added, ("title", "series", "type", "year")),
                                          ("playback.started", playing, ("title", "series", "type", "user", "client"))):
                    before = self.seen.get(name)
                    if before is not None and name in wanted:
                        for key in now.keys() - before:
                            sent += send(name, {k: now[key].get(k) for k in fields}) or 0
                    self.seen[name] = set(now)
        if "download.finished" in wanted:
            q = services.cached("queue", 10, lambda: services.queue(app_services))
            done = {f"{i.get('service_name')}|{i.get('title')}": i for i in q.get("items") or [] if float(i.get("progress") or 0) >= 100}
            before = self.seen.get("download.finished")
            if before is not None:
                for key in done.keys() - before:
                    sent += send("download.finished", {"title": done[key].get("title"), "app": done[key].get("service_name")}) or 0
            self.seen["download.finished"] = set(done)
        return sent


# Jobs ---------------------------------------------------------------------------------------------------------

def _jobs_file(data_dir):
    return os.path.join(pa.root(data_dir), "jobs.json")


def jobs(data_dir):
    """Every job from every added plug-in, for System, Jobs: [{plugin, id, title, when, enabled, last...}]."""
    last = pa._read(_jobs_file(data_dir), {}) or {}
    out = []
    for p in pa.listing(data_dir):
        m = pa._read(os.path.join(pa.folder(data_dir, p["id"]), "manifest.json"), {}) or {}
        for j in m.get("jobs") or []:
            key = f"{p['id']}/{j['id']}"
            when = (f"Daily at {j['daily']}" if "daily" in j else f"Every {j['every_hours']} hours" if "every_hours" in j
                    else "Each time it starts")
            if j.get("quiet_hours"):
                when += ", in quiet hours"
            out.append({"key": key, "plugin": p["id"], "job": j["id"], "title": f"{p['name']}: {j['label']}", "when": when,
                        "enabled": p["state"] == "enabled", **{k: (last.get(key) or {}).get(k) for k in ("started", "finished", "status", "summary")}})
    return out


def _record(data_dir, key, **values):
    with _jobs_lock:
        data = pa._read(_jobs_file(data_dir), {}) or {}
        data.setdefault(key, {}).update(values)
        pa._write(_jobs_file(data_dir), data)


_jobs_lock = threading.Lock()
_running = set()


def run_job(data_dir, pid, jid, helper=None):
    """Runs one job now: starts a when-needed container first and stops it after; the job's time limit applies."""
    from . import plugin_cards
    m = pa._read(os.path.join(pa.folder(data_dir, pid), "manifest.json"), {}) or {}
    job = next((j for j in m.get("jobs") or [] if j.get("id") == jid), None)
    if not job or not m.get("containers"):
        raise LookupError("No such job")
    key = f"{pid}/{jid}"
    with _jobs_lock:
        if key in _running:
            return "It is already running"
        _running.add(key)
    main = m["containers"][0]
    started_here = False
    _record(data_dir, key, started=time.time(), status="running", summary="")
    try:
        if main.get("start") == "when_needed":
            ok, text = pa._compose_run(data_dir, pid, "up -d", helper)
            if not ok:
                raise ValueError(f"It did not start: {text.strip()[-160:]}")
            started_here = True
        url = f"http://{plugin_cards._host(pid, main)}:{int(main.get('port') or 80)}{job['path']}"
        req = urllib.request.Request(url, data=b"", method="POST", headers={"Accept": "application/json", "User-Agent": "Starboard"})
        with urllib.request.build_opener().open(req, timeout=60 * int(job.get("time_limit_minutes") or 10)) as r:  # its own container  # nosec B310
            raw = r.read(plugin_cards.MAX_BYTES)
        said = (json.loads(raw) or {}).get("said") if raw[:1] == b"{" else ""
        summary = plugin_cards._text(said or "Done", 160)
        _record(data_dir, key, finished=time.time(), status="done", summary=summary)
        return summary
    except (OSError, ValueError) as e:
        _record(data_dir, key, finished=time.time(), status="failed", summary=str(e)[:200])
        logs.event("warning", "plug-ins", f"Job {key} failed: {e}")
        return f"It failed: {e}"
    finally:
        if started_here:
            pa._compose_run(data_dir, pid, "stop", helper)
        with _jobs_lock:
            _running.discard(key)


def _in_quiet_hours(cfg, now):
    hours = (cfg.data.get("download_hours") if cfg else None) or {}
    start, end = (int(hours.get("start", 1)), int(hours.get("end", 6))) if hours.get("enabled") else (1, 6)
    h = now.hour
    return start <= h < end if start < end else (h >= start or h < end)


def due(job, last, now, started_at):
    """True when a job should run now. `last` is its last start (epoch), `started_at` when Starboard started."""
    if "at_start" in job:
        return (last or 0) < started_at
    if "every_hours" in job:
        return now.timestamp() - (last or 0) >= job["every_hours"] * 3600
    hh, mm = (int(x) for x in job["daily"].split(":"))
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return now >= target and (last or 0) < target.timestamp()


class Clock:
    """Starboard's one clock for plug-in jobs: a thread that runs only while an active plug-in has a job, wakes each
    five minutes, and runs what is due (a daily job within five minutes of its time)."""

    def __init__(self, data_dir, cfg=None):
        self.data_dir, self.cfg = data_dir, cfg
        self.started_at = time.time()
        self.thread = None
        self.wake = threading.Event()
        self.events = EventWatch()

    def _active_jobs(self):
        out = []
        for p in pa.listing(self.data_dir):
            if p["state"] == "enabled":
                m = pa._read(os.path.join(pa.folder(self.data_dir, p["id"]), "manifest.json"), {}) or {}
                out += [(p["id"], j) for j in m.get("jobs") or []]
        return out

    def _needed(self):
        return self._active_jobs(), listened(self.data_dir) & set(POLLED)

    def _loop(self):
        while True:
            todo, polled = self._needed()
            if not todo and not polled:
                self.thread = None
                return
            if polled and self.cfg is not None:
                try:
                    self.events.check(polled, self.cfg.data.get("services") or [])
                except Exception as e:  # noqa: BLE001 - an app that does not answer never stops the clock
                    logs.event("warning", "plug-ins", f"Events not checked: {e}")
            last = pa._read(_jobs_file(self.data_dir), {}) or {}
            now = dt.datetime.now()
            for pid, job in todo:
                if job.get("quiet_hours") and not _in_quiet_hours(self.cfg, now):
                    continue
                if due(job, (last.get(f"{pid}/{job['id']}") or {}).get("started"), now, self.started_at):
                    run_job(self.data_dir, pid, job["id"])
            self.wake.wait(300)
            self.wake.clear()

    def ensure(self):
        if self.thread and self.thread.is_alive():
            self.wake.set()
            return
        if any(self._needed()):
            self.thread = threading.Thread(target=self._loop, name="plugin-jobs", daemon=True)
            self.thread.start()
