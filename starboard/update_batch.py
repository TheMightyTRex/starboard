"""Install all updates (DASH-454): every waiting update as one batch, from Settings, Updates or the API.

"All at once" is one action, run safely: the updates run one at a time, as every other update does (in parallel
they would overload a small server and the way back of one would undo another), in this order:

1. the other apps, then Jellyfin's plug-ins (Jellyfin installs them; it is not restarted yet);
2. Starboard's plug-ins;
3. Reelix;
4. Jellyfin restarts once, for all its plug-ins, and never while someone is watching: it waits, and says so;
5. Starboard itself, last, because it restarts Starboard. The page reconnects and shows the result.

Each update keeps its own copy first, check afterwards and way back (update_runs, auto_updates). One that fails goes
back by itself, and the rest carry on. What always waits for the person is held back and listed: a plug-in that asks
for new permissions, a big change (a new major version), a plug-in that comes as a zip file, and anything Starboard
cannot update here (such as an app not started by Docker Compose).

The batch is one run in update-runs.json (kind "batch", target "all"), so Recent updates lists it with each update's
own run; its steps are the updates, in order, each with its state. Lightweight: nothing is fetched to show the
button (the page already knows what is waiting); the plan reads each waiting plug-in's new manifest, which the update
reads anyway, and keeps it for ten minutes. While it runs, one thread waits on each update in turn.
"""
import re
import time

from . import logs, update_runs

ORDER = {"app": 1, "jellyfin-plugins": 2, "plugin": 3, "reelix": 4, "starboard": 9}  # 5: Jellyfin's one restart
ITEM_WAIT = 45 * 60  # an update that takes longer has stopped (as auto_updates.RUN_WAIT)
WATCH_WAIT = 3 * 60 * 60  # how long Jellyfin's restart waits for nobody to be watching
WATCH_LOOK = 60  # seconds between looks at who is watching (one request to Jellyfin)
MANIFEST_KEEP = 600
_manifests = {}  # (address, sha256) -> (time, manifest)
_sleep = time.sleep  # the tests make the waits short

# Each update's state in the batch, with its words and icon on the page.
STATES = ("waiting", "working", "done", "went-back", "failed", "held")
DONE = ("updated", "up-to-date", "rolled-back")


def _major(v):
    m = re.match(r"v?(\d+)\.", str(v or ""))
    return m.group(1) if m else None


def big_change(current, latest):
    """A new first number is a big change (0.19 to 0.20 is not; 0.20 to 1.0 and 4.2 to 5.0 are), as Apps, Updates."""
    a, b = _major(current), _major(latest)
    return bool(a and b and a != b)


def _manifest(address, sha256=""):
    from . import plugins_admin as pa
    hit = _manifests.get((address, sha256))
    if hit and time.time() - hit[0] < MANIFEST_KEEP:
        return hit[1]
    got = pa.fetch_manifest(address, sha256=sha256)
    _manifests[(address, sha256)] = (time.time(), got)
    return got


def _plugin_hold(app, t, known):
    """Why a plug-in's update waits for the person, or "" when it can go in the batch."""
    from . import plugin_life, plugins
    from . import plugins_admin as pa
    import os
    pid = t["id"].split(":", 1)[1]
    k = known.get(pid)
    if not k:
        return "No newer version is known from the catalogues"
    try:
        manifest = _manifest(k["manifest"], k.get("sha256", ""))
    except Exception as e:  # noqa: BLE001  one that cannot be read is held back; the rest go on
        return f"Its new version could not be read ({str(e)[:120]})"
    old = pa._read(os.path.join(pa.folder(app.data_dir, pid), "manifest.json"), {}) or {}
    new = plugin_life.new_permissions(old, manifest)
    if new:
        return f"It asks for new permissions ({', '.join(new)}). Update it on its own page"
    if plugins.builds(manifest):
        return "It comes as a zip file. Use Update from a zip file on its page"
    if big_change(t.get("current"), manifest.get("version")):
        return f"Version {manifest.get('version')} is a big change. Read what is new and update it on its own page"
    return ""


def plan(app):
    """What Install all updates would do now: {items: [...in order], held: [...], count}. Each item: target, kind,
    name, from, to, order; a held one has why. count is the number that will install (Jellyfin's plug-ins, whose
    new versions only Jellyfin knows, are not counted)."""
    from . import auto_updates, plugin_life
    items, held = [], []
    known = None
    for t in update_runs.targets(app):
        if not t.get("update_available"):
            continue
        item = {"target": t["id"], "kind": t["kind"], "name": t["name"], "from": t.get("current") or "",
                "to": t.get("latest") or "", "order": ORDER.get(t["kind"], 1)}
        why = ""
        if t["kind"] == "app" and t["name"].strip().lower() == "starboard":
            continue  # Starboard's own container updates as Starboard
        if not t.get("can_update"):
            why = t.get("why") or "Starboard cannot update it from here"
        elif t["kind"] == "plugin":
            if known is None:
                known = plugin_life.updates_known(app.data_dir)
            why = _plugin_hold(app, t, known)
        elif t.get("big_change") or big_change(t.get("current"), t.get("latest")):
            why = f"Version {t.get('latest')} is a big change. Read what is new and update it on its own"
        (held if why else items).append({**item, "why": why} if why else item)
    count = len(items)
    if auto_updates._jf(app.config.data.get("services") or []):
        # Check for updates may have asked Jellyfin which of its plug-ins have new versions: then they are named and
        # counted, so Install all updates is offered for them alone too.
        from . import update_check
        found = update_check.jellyfin_waiting()
        names = ", ".join(f"{j['name']} {j['latest']}" for j in found[:8])
        note = (f"Jellyfin installs the new versions of {names}" if found
                else "Jellyfin installs any new versions it has")
        items.append({"target": "jellyfin-plugins", "kind": "jellyfin-plugins", "name": "Jellyfin's plug-ins", "from": "", "to": "",
                      "order": ORDER["jellyfin-plugins"], "note": note})
        count += len(found)
    items.sort(key=lambda i: (i["order"], i["name"].lower()))
    return {"items": items, "held": held, "count": count}


# The record --------------------------------------------------------------------------------------------------------

def _label(i):
    if i["kind"] == "jellyfin-plugins":
        return "Jellyfin's plug-ins"
    return f"{i['name']} {i['from']} to {i['to']}".strip() if i.get("from") and i.get("to") else f"{i['name']} {i.get('to') or ''}".strip()


def running(app):
    """The batch running now, or None."""
    for r in update_runs.recent(app):
        if r.get("kind") == "batch" and r["state"] == "running":
            return r
    return None


def start(app, by="you", targets=None):
    """Starts Install all updates. targets: the ones the person saw and confirmed (others that appeared since are
    left for next time). Returns the batch run. Raises update_runs.Busy or update_runs.Refused."""
    if update_runs._busy() or update_runs._starboard_running(app):
        raise update_runs.Busy("An update is already running. Wait for it to finish")
    p = plan(app)
    items = p["items"]
    if targets is not None:
        want = {str(t) for t in targets}
        items = [i for i in items if i["target"] in want]
    if not [i for i in items if i["kind"] != "jellyfin-plugins"] and not (targets and "jellyfin-plugins" in targets):
        raise update_runs.Refused("Nothing is waiting to update" + (": everything waiting is held back for you" if p["held"] else ""))
    steps = [(i["target"], _label(i)) for i in items] + [(h["target"], _label(h)) for h in p["held"]]
    n = len([i for i in items if i["kind"] != "jellyfin-plugins"])
    run = update_runs._new(app.data_dir, "all", "batch", "All updates", "update", "", f"{n} {'update' if n == 1 else 'updates'}", by, steps,
                           extra={"items": [{k: i.get(k, "") for k in ("target", "kind", "name", "from", "to", "why")} for i in items + p["held"]]})
    for h in p["held"]:
        update_runs._step(app.data_dir, run, h["target"], "held", h["why"])
    logs.event("info", "updates", f"Install all updates started {update_runs_by(by)}: {', '.join(_label(i) for i in items)}")
    update_runs._go(app.data_dir, run, lambda: _work(app, run, items, by))
    return run


def update_runs_by(by):
    return "by itself" if by == "automatic" else "from the API" if str(by).startswith("api") else "by you"


def _say(app, run, said):
    with update_runs._lock:
        run["said"] = said[:600]
        update_runs._save(app.data_dir)


def _wait(app, rid, sleep, wait=ITEM_WAIT):
    until = time.monotonic() + wait
    while True:
        r = update_runs.get(app, rid)
        if r["state"] != "running":
            return r
        if time.monotonic() >= until:
            r.update(state="failed", said="It took more than 45 minutes")
            return r
        sleep(3)


def _state_of(r):
    return "done" if r["state"] in DONE else "went-back" if r["state"] == "went-back" else "failed"


def _one(app, run, item, by, sleep):
    """Runs one update of the batch to its end. Returns its run (or a stand-in with state and said)."""
    try:
        r = update_runs.start(app, item["target"], by=by, batch=run["id"])
    except (update_runs.Busy, update_runs.Refused, LookupError, ValueError, OSError) as e:
        return {"id": "", "state": "refused", "said": str(e)[:300]}
    _link(app, run, item["target"], r["id"])
    return _wait(app, r["id"], sleep)


def _link(app, run, target, rid):
    with update_runs._lock:
        for i in run.get("items") or []:
            if i["target"] == target:
                i["run"] = rid
        update_runs._save(app.data_dir)


def _work(app, run, items, by, sleep=None):
    from . import auto_updates
    sleep = sleep or _sleep
    dd = app.data_dir
    jf_pending = None  # (jellyfin run, jf, news) while its restart waits for the end
    try:
        for item in [i for i in items if i["kind"] != "starboard"]:
            update_runs._step(dd, run, item["target"], "now", "")
            _say(app, run, f"Updating {item['name']}")
            if item["kind"] == "jellyfin-plugins":
                try:
                    begun = auto_updates.jellyfin_plugins_begin(app, by=by, batch=True)
                    _link(app, run, item["target"], begun[0]["id"])
                    jr, pending = auto_updates.jellyfin_plugins_run(app, begun=begun, restart_later=True, sleep=sleep)
                except (update_runs.Refused, update_runs.Busy) as e:
                    update_runs._step(dd, run, item["target"], "failed", str(e))
                    continue
                except (OSError, ValueError) as e:
                    update_runs._step(dd, run, item["target"], "failed", f"Jellyfin did not answer: {getattr(e, 'reason', e)}")
                    continue
                if pending:
                    jf_pending = (jr, *pending)
                    update_runs._step(dd, run, item["target"], "now", "Installed. Jellyfin restarts once, after the other updates")
                else:
                    update_runs._step(dd, run, item["target"], _state_of(jr), jr["said"])
                continue
            r = _one(app, run, item, by, sleep)
            update_runs._step(dd, run, item["target"], _state_of(r), r.get("said") or "")
        if jf_pending:
            jr, jf, news = jf_pending
            jf_pending = None

            def waiting(n):
                words = f"Waiting to restart Jellyfin: {n} {'person is' if n == 1 else 'people are'} watching. It restarts when nobody is"
                update_runs._step(dd, run, "jellyfin-plugins", "now", words)
                _say(app, run, words)
            _say(app, run, "Restarting Jellyfin once, for all its plug-ins")
            auto_updates.jellyfin_plugins_restart(app, jr, jf, news, sleep=sleep, watch_wait=WATCH_WAIT, watch_look=WATCH_LOOK, waiting=waiting)
            update_runs._step(dd, run, "jellyfin-plugins", _state_of(jr), jr["said"])
        sb = next((i for i in items if i["kind"] == "starboard"), None)
        if sb:
            update_runs._step(dd, run, "starboard", "now", "Starboard restarts, and this page reconnects by itself")
            _say(app, run, "Updating Starboard last. It restarts, and the page reconnects by itself")
            r = _one(app, run, sb, by, sleep)  # if Starboard restarts first, the next Starboard reads the end (settle)
            update_runs._step(dd, run, "starboard", _state_of(r), r.get("said") or "")
        _finish(app, run)
    finally:
        if jf_pending:  # the batch stopped before Jellyfin restarted: its run ends with words, never a stuck "running"
            update_runs._end(dd, jf_pending[0], "updated", f"Updated: {jf_pending[2]}. The new versions start when Jellyfin next restarts", app)


def summary(run):
    """(state, words) of a batch from its steps."""
    steps = run.get("steps") or []
    done = [s for s in steps if s["state"] == "done"]
    back = [s for s in steps if s["state"] == "went-back"]
    bad = [s for s in steps if s["state"] in ("failed", "skipped")]
    held = [s for s in steps if s["state"] == "held"]
    tried = len(steps) - len(held)
    names = {i["target"]: i["name"] for i in run.get("items") or []}
    name = lambda s: names.get(s["id"], s["label"])  # noqa: E731
    words = [f"{len(done)} of {tried} updated"]
    if back:
        words.append(f"Went back by itself: {', '.join(name(s) for s in back)}")
    if bad:
        words.append(f"Not updated: {', '.join(name(s) for s in bad)}")
    if held:
        words.append(f"Held back for you: {', '.join(name(s) for s in held)}")
    state = "updated" if len(done) == tried else "went-back" if not bad and back and not done else "some-updated" if done else "failed"
    return state, ". ".join(words)


def _finish(app, run):
    state, said = summary(run)
    update_runs._end(app.data_dir, run, state, said, app)
    watch = getattr(app, "watch", None)
    if watch:
        try:
            watch.alert(f"update-all:{run['id']}", "Install all updates finished", f"{said}. Go to Settings, Updates.",
                        "info" if state == "updated" else "warning")
        except Exception as e:  # noqa: BLE001  the alert is a help, never a stop
            logs.error("updates", f"The alert was not sent: {e}", e)


def settle(app, run):
    """A batch read after Starboard restarted: Starboard was its last update, so its end is Starboard's own run's
    end; any other batch left running stopped with Starboard. Returns the run as it is now (and writes it once)."""
    if run["state"] != "running" or run["id"] in update_runs._active:
        return run
    sb = next((i for i in run.get("items") or [] if i["target"] == "starboard" and i.get("run")), None)
    step = next((s for s in run["steps"] if s["id"] == "starboard"), None)
    if sb and step and step["state"] == "working":
        try:
            r = update_runs.get(app, sb["run"])
        except LookupError:
            r = None
        if r and r["state"] == "running":
            return run
        step.update(state=_state_of(r) if r else "failed", detail=(r or {}).get("said") or "")
        state, said = summary(run)
    else:
        for s in run["steps"]:
            if s["state"] in ("waiting", "working"):
                s["state"] = "skipped"
        state, said = "failed", "Starboard restarted while it ran, so it did not finish. " + summary(run)[1]
    run.update(state=state, said=said[:600], finished=time.time())
    with update_runs._lock:  # written once, so the next read and Recent updates agree
        saved = update_runs._runs.get(run["id"])
        if saved and saved["state"] == "running":
            saved.update(state=run["state"], said=run["said"], finished=run["finished"], steps=run["steps"])
            update_runs._save(app.data_dir)
    return run


def view(app, rid):
    """A batch for the page's panel: each update's state, the count, what is happening now."""
    run = update_runs.get(app, rid)
    if run.get("kind") != "batch":
        raise LookupError("No Install all updates with that id")
    steps = run["steps"]
    held = [s for s in steps if s["state"] == "held"]
    ended = [s for s in steps if s["state"] in ("done", "went-back", "failed", "skipped")]
    return {"id": run["id"], "state": run["state"], "finished": run["state"] != "running", "said": run["said"],
            "started": run["started"], "ended_at": run.get("finished"), "by": run["by"],
            "count": len(steps) - len(held), "ended": len(ended),
            "items": [{"target": s["id"], "label": s["label"], "state": s["state"], "detail": s["detail"]} for s in steps]}


def latest(app):
    """The newest batch, while it runs or for a day after it ended, for the page to show again on opening."""
    for r in update_runs.recent(app):
        if r.get("kind") == "batch":
            if r["state"] == "running" or time.time() - (r.get("finished") or 0) < 86400:
                return view(app, r["id"])
            return None
    return None

