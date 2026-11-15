"""Plug-ins that update safely (plug-in API 1.14, DASH-424; owner, 14 November 2026: "update the plugin framework and
api page with update tools"). A manifest may add an update object:

    "update": {
      "before": {"path": "/update/before", "time_limit_seconds": 60},
      "after": {"path": "/update/after", "time_limit_seconds": 60},
      "health_wait_seconds": 90,
      "migrations": [{"version": "2.0.0", "rename": {"minutes": "every_minutes"}, "remove": ["old_mode"],
                      "defaults": {"every_minutes": 30}}]
    }

- before: Starboard POSTs {from, to} to the version that is installed, before anything changes, so it can finish or
  pause its work. An answer other than 2xx, {"ok": false}, or no answer within the time limit stops the update, and
  nothing is changed. The installed version's manifest is the one read, so a step added in 2.0.0 runs from the update
  after 2.0.0.
- migrations: how the saved settings move from an older version. Each step whose version is above the installed
  version and at or below the new one is applied, oldest first: rename moves a value to its new key, remove drops a
  key, and defaults sets a new value only where the person still had the old version's default (or nothing). The
  settings from before are kept in previous/ with the version, so Roll back puts them back as they were.
- health: after the new version starts, Starboard asks its health path every 3 seconds until it answers 200, for up
  to health_wait_seconds (60 when left out). A version that does not start or does not answer in time is rolled back
  by itself to the one before, and the old version's after step is told {outcome: "rolled_back"}.
- after: Starboard POSTs {from, to, outcome} to the version now running, to tidy up or start its work again. A
  failing after step does not undo the update; it is said in the update's result and the log.

Nothing here runs on a timer: each step is one call while an update runs, in the update's own thread.
"""
import json
import re
import time
import urllib.error
import urllib.request

from . import api_v1, logs, plugins

UPDATE = {"before", "after", "health_wait_seconds", "migrations"}
STEP = {"path", "time_limit_seconds"}
MIGRATION = {"version", "rename", "remove", "defaults"}
STEP_LIMIT, STEP_LIMIT_MIN, STEP_LIMIT_MAX = 60, 5, 300
HEALTH_WAIT, HEALTH_WAIT_MIN, HEALTH_WAIT_MAX = 60, 10, 600
HEALTH_EVERY = 3
MAX_MIGRATIONS, MAX_KEYS = 20, 20
KEY = r"^[a-z][a-z0-9_]{0,40}$"
PATH = r"^/[A-Za-z0-9/_-]{1,80}$"


def _key(version):
    try:
        return tuple(int(x) for x in str(version).split("-")[0].split("."))
    except ValueError:
        return (0,)


# The check (plugins.check and the tester) -------------------------------------------------------------------------

def check(manifest):
    """Problems with the optional update object, as plain sentences."""
    u = manifest.get("update")
    if u is None:
        return []
    if not isinstance(u, dict):
        return ["update must be an object with before, after, health_wait_seconds or migrations"]
    out = [f"update: unknown field {k}" for k in sorted(set(u) - UPDATE)]
    containers = manifest.get("containers") or []
    for which in ("before", "after"):
        if which not in u:
            continue
        s = u[which]
        if not (isinstance(s, dict) and not set(s) - STEP and isinstance(s.get("path"), str) and re.match(PATH, s["path"])):
            out.append(f"update.{which}: needs a path on the plug-in, such as /update/{which}, and may give time_limit_seconds")
        elif "time_limit_seconds" in s and not (isinstance(s["time_limit_seconds"], int) and not isinstance(s["time_limit_seconds"], bool)
                                                and STEP_LIMIT_MIN <= s["time_limit_seconds"] <= STEP_LIMIT_MAX):
            out.append(f"update.{which}: time_limit_seconds must be a whole number from {STEP_LIMIT_MIN} to {STEP_LIMIT_MAX}")
        elif not containers:
            out.append(f"update.{which}: needs a container to call")
    if "health_wait_seconds" in u:
        w = u["health_wait_seconds"]
        if not (isinstance(w, int) and not isinstance(w, bool) and HEALTH_WAIT_MIN <= w <= HEALTH_WAIT_MAX):
            out.append(f"update.health_wait_seconds must be a whole number from {HEALTH_WAIT_MIN} to {HEALTH_WAIT_MAX}")
        elif not manifest.get("health"):
            out.append("update.health_wait_seconds needs a health path for Starboard to ask")
    migrations = u.get("migrations")
    if migrations is None:
        return out
    if not (isinstance(migrations, list) and 1 <= len(migrations) <= MAX_MIGRATIONS):
        return out + [f"update.migrations must list one to {MAX_MIGRATIONS} steps"]
    keys = {s.get("key") for s in manifest.get("settings") or [] if isinstance(s, dict)}
    seen = set()
    for i, m in enumerate(migrations):
        where = f"update.migrations[{i}]"
        if not isinstance(m, dict):
            out.append(f"{where} must be an object")
            continue
        out += [f"{where}: unknown field {k}" for k in sorted(set(m) - MIGRATION)]
        v = m.get("version")
        if not (isinstance(v, str) and re.match(plugins.SEMVER, v)) or v in seen:
            out.append(f"{where}: needs its own version, such as 2.0.0: the version that made the change")
        elif isinstance(manifest.get("version"), str) and _key(v) > _key(manifest["version"]):
            out.append(f"{where}: version {v} is newer than this plug-in's version {manifest['version']}")
        seen.add(v)
        if not any(k in m for k in ("rename", "remove", "defaults")):
            out.append(f"{where}: needs at least one of rename, remove or defaults")
        rename = m.get("rename", {})
        if not (isinstance(rename, dict) and len(rename) <= MAX_KEYS
                and all(re.match(KEY, str(a)) and isinstance(b, str) and re.match(KEY, b) and a != b for a, b in rename.items())):
            out.append(f"{where}: rename maps up to {MAX_KEYS} old setting keys to their new keys, such as {{\"minutes\": \"every_minutes\"}}")
        else:
            out += [f"{where}: rename moves {a} to {b}, which is not one of this version's settings" for a, b in rename.items() if b not in keys]
        remove = m.get("remove", [])
        if not (isinstance(remove, list) and len(remove) <= MAX_KEYS and all(isinstance(k, str) and re.match(KEY, k) for k in remove)):
            out.append(f"{where}: remove lists up to {MAX_KEYS} setting keys this version no longer has")
        else:  # a key removed and then made again by a later rename is allowed
            renamed_to = {b for later in migrations if isinstance(later, dict) and isinstance(later.get("rename"), dict)
                          for b in later["rename"].values()}
            out += [f"{where}: remove names {k}, which is still one of this version's settings" for k in remove
                    if k in keys and k not in renamed_to]
        defaults = m.get("defaults", {})
        if not (isinstance(defaults, dict) and len(defaults) <= MAX_KEYS
                and all(re.match(KEY, str(k)) and isinstance(val, (str, int, float, bool, list, dict)) for k, val in defaults.items())):
            out.append(f"{where}: defaults maps up to {MAX_KEYS} setting keys to their new default values")
        else:
            out += [f"{where}: defaults sets {k}, which is not one of this version's settings" for k in defaults if k not in keys]
    return out


def update_info(manifest):
    """What a manifest's update object says, with Starboard's defaults filled in."""
    u = manifest.get("update") if isinstance(manifest.get("update"), dict) else {}

    def step(which):
        s = u.get(which)
        return {"path": s["path"], "time_limit_seconds": int(s.get("time_limit_seconds") or STEP_LIMIT)} if isinstance(s, dict) and s.get("path") else None
    return {"before": step("before"), "after": step("after"),
            "health_wait_seconds": int(u.get("health_wait_seconds") or HEALTH_WAIT) if manifest.get("health") else 0,
            "migrations": [m for m in u.get("migrations") or [] if isinstance(m, dict)]}


# Settings migration ---------------------------------------------------------------------------------------------

def migrate(old, new, values):
    """Moves the saved settings `values` from the old manifest's version to the new one's. Returns (values, said):
    said lists each change in words, for the update's progress and the audit log. Going to an older version
    migrates nothing: Roll back puts back the settings kept from before."""
    values = dict(values or {})
    low, high = _key(old.get("version") or "0"), _key(new.get("version") or "0")
    if high <= low:
        return values, []
    old_defaults = {s["key"]: s.get("default") for s in old.get("settings") or [] if isinstance(s, dict) and "key" in s}
    steps = [m for m in update_info(new)["migrations"] if low < _key(m.get("version")) <= high]
    steps.sort(key=lambda m: _key(m.get("version")))
    said = []
    for m in steps:
        for a, b in (m.get("rename") or {}).items():
            if a in values:
                if b not in values:
                    values[b] = values[a]
                    said.append(f"{a} is now {b}")
                    old_defaults.setdefault(b, old_defaults.get(a))
                del values[a]
        for k in m.get("remove") or []:
            if k in values:
                del values[k]
                said.append(f"{k} was removed")
        for k, v in (m.get("defaults") or {}).items():
            if k not in values or values[k] == old_defaults.get(k):
                if values.get(k) != v:
                    said.append(f"{k} takes the new default")
                values[k] = v
    return values, said


def rehearse(old, new):
    """The update from the version before to this one, and Roll back, tried on the settings alone (DASH-423, the
    plug-in tester's --previous): nothing is installed. Returns issues [(severity, what, fix)].

    It checks that this version is newer, that the old version's settings (its defaults, and every setting given a
    value) move to keys this version has, that a setting this version gives a new type of value takes a default, and
    that Roll back gets the old settings back exactly (Starboard keeps the old settings file; here, nothing of the new
    version is left in it). A version that asks for new permissions is said too: it never updates by itself."""
    out = []
    if _key(new.get("version") or "0") <= _key(old.get("version") or "0"):
        return [("error", f"Version {new.get('version')} is not newer than {old.get('version')}",
                 "Give this version a higher number, such as 1.2.0 after 1.1.0")]
    spec = {s["key"]: s for s in new.get("settings") or [] if isinstance(s, dict) and "key" in s}
    before = {s["key"]: s.get("default", f"value-of-{s['key']}") for s in old.get("settings") or [] if isinstance(s, dict) and "key" in s}
    moved, said = migrate(old, new, before)
    for k in moved:
        if k not in spec:
            out.append(("error", f"The setting {k} from version {old.get('version')} is still there after the update, but this version has no such setting",
                        f"Add a migration for {new.get('version')}: rename {k} to its new key, or remove it"))
    for k, s in spec.items():
        if k in moved and "default" in s and type(moved[k]) is not type(s["default"]) and not (
                isinstance(moved[k], (int, float)) and isinstance(s["default"], (int, float)) and not isinstance(moved[k], bool)):
            out.append(("warning", f"The setting {k} keeps a {type(moved[k]).__name__} from version {old.get('version')}, but this version's default is a {type(s['default']).__name__}",
                        f"Give {k} a new default in a migration, so the old value is not used as it is"))
    from . import plugin_life
    added = plugin_life.new_permissions(old, new)
    if added:
        out.append(("info", f"This version asks for new permissions ({', '.join(added)}), so it never updates by itself: each owner chooses it",
                    "Nothing to fix; say why in its changes"))
    if said:
        out.append(("info", "The settings move: " + "; ".join(said), "Nothing to fix"))
    return out


# The steps, and the health check ----------------------------------------------------------------------------------

def _post(pid, main, path, body, timeout):
    """POSTs JSON to the plug-in's main container. Returns (ok, said). Tests replace it."""
    from . import plugin_cards
    url = f"http://{plugin_cards._host(pid, main)}:{int(main.get('port') or 80)}{path}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Starboard"})
    try:
        with urllib.request.build_opener().open(req, timeout=timeout) as r:  # the plug-in's own container  # nosec B310
            raw = r.read(plugin_cards.MAX_BYTES)
    except urllib.error.HTTPError as e:
        try:
            said = (json.loads(e.read(4096) or b"{}") or {}).get("said") or ""
        except ValueError:
            said = ""
        return False, plugin_cards._text(said, 200) or f"It answered {e.code}"
    except (OSError, ValueError) as e:
        if "timed out" in str(e):
            return False, f"It did not answer within {timeout} seconds"
        return False, "Starboard could not reach it"
    try:
        answer = json.loads(raw) if raw[:1] == b"{" else {}
    except ValueError:
        answer = {}
    said = plugin_cards._text(str(answer.get("said") or ""), 200)
    return answer.get("ok") is not False, said


def _ask(pid, main, path):
    from . import plugin_watch
    return plugin_watch._ask(pid, main, path)


def call_step(pid, manifest, which, body):
    """Runs the manifest's before or after step. Returns (ran, ok, said); ran is False when it has none."""
    s = update_info(manifest)[which]
    main = (manifest.get("containers") or [None])[0]
    if not s or not main:
        return False, True, ""
    ok, said = _post(pid, main, s["path"], body, s["time_limit_seconds"])
    return True, ok, said


def wait_healthy(pid, manifest, sleep=None):
    """Asks the health path every 3 seconds until it answers 200, for up to health_wait_seconds (counted in tries, so
    each ask's own 2 seconds are on top). (ok, said)."""
    limit = update_info(manifest)["health_wait_seconds"]
    main = (manifest.get("containers") or [None])[0]
    if not limit or not main:
        return True, ""
    said = ""
    for i in range(limit // HEALTH_EVERY + 1):
        if i:
            (sleep or time.sleep)(HEALTH_EVERY)
        said = _ask(pid, main, manifest["health"])
        if said == "ok":
            return True, ""
    return False, f"It did not answer its health check within {limit} seconds. {said}"


# What is new before the update -------------------------------------------------------------------------------------

def changes_between(manifest, low, high):
    """The manifest's changes above `low` and at or below `high`, newest first, in the parts the page builds as text:
    [{version, date, sections: [{type, items}]}]. Shown before an update from the new version's manifest, and after
    it on State (plugin_life.whats_new)."""
    from . import changes
    listed = manifest.get("changes") if isinstance(manifest.get("changes"), list) and not plugins.check_changes(manifest.get("changes")) else []
    picked = [v for v in listed if (low is None or _key(v["version"]) > _key(low)) and _key(v["version"]) <= _key(high)]
    picked.sort(key=lambda v: _key(v["version"]), reverse=True)
    return [{"version": v["version"], "date": changes._date(v["date"]) if v.get("date") else "",
             "sections": [{"type": t.capitalize(), "items": [changes._inline(x.strip()) for x in v[t]]}
                          for t in plugins.CHANGE_TYPES if v.get(t)]} for v in picked]


def preview(old, new):
    """What the update warning shows about an update before it is installed: what is new, the settings that move and
    the steps Starboard will run."""
    info = update_info(new)
    _, moved = migrate(old, new, {s["key"]: s.get("default") for s in old.get("settings") or [] if isinstance(s, dict) and "key" in s})
    return {"whats_new": changes_between(new, old.get("version"), new.get("version")),
            "settings_move": [m for m in moved if not m.endswith("takes the new default")] or moved,
            "before_step": bool(update_info(old)["before"]), "after_step": bool(info["after"]),
            "health_wait_seconds": info["health_wait_seconds"]}


# The update, step by step ------------------------------------------------------------------------------------------

STEPS = [("before", "Asking it to get ready"), ("settings", "Moving its settings"), ("install", "Installing the new version"),
         ("health", "Waiting for it to answer"), ("after", "Asking it to tidy up")]


def update_safely(data_dir, pid, manifest, media_dir, services=None, note="", logo=None, progress=None, dev=False):
    """The update with its steps: before (on the installed version), the settings migration and the install
    (plugin_life.update), the health check, and after; a version that does not start or answer is rolled back.
    `progress(step, state, detail)` hears each step: state is now, done, skipped or failed. `logo`: what
    plugins_admin.fetch_logo gave for the new version, kept with it. Returns {outcome, said, from, to, migrated}:
    outcome is updated, refused (stopped before anything changed) or went-back."""
    from . import plugin_life
    from . import plugins_admin as pa
    import os
    say = progress or (lambda *a: None)
    where = pa.folder(data_dir, pid)
    old = pa._read(os.path.join(where, "manifest.json"))
    if not old:
        raise LookupError("No plug-in with that id")
    st = pa._read(os.path.join(where, "state.json"), {}) or {}
    was_on = st.get("state") == "enabled" and bool(old.get("containers"))
    came, going = old.get("version"), manifest.get("version")
    body = {"from": came, "to": going}
    # 1. before, on the version that is installed now
    if was_on and update_info(old)["before"]:
        say("before", "now", "")
        _, ok, said = call_step(pid, old, "before", body)
        if not ok:
            say("before", "failed", said)
            api_v1.audit(data_dir, "plugin_update_refused", plugin=pid, version=going, previous=came, reason=said[:200])
            logs.event("warning", "plug-ins", f"{old.get('name', pid)} was not updated: its before step said {said}")
            return {"outcome": "refused", "from": came, "to": going, "migrated": [],
                    "said": f"{old.get('name', pid)} was not updated: it was not ready. {said}".strip()}
        say("before", "done", said)
    else:
        say("before", "skipped", "It is not active" if not was_on else "It has no before step")
    # 2 and 3. the settings and the new version (plugin_life.update migrates and starts it again when it was active)
    say("settings", "now", "")
    said = plugin_life.update(data_dir, pid, manifest, media_dir, services=services, dev=dev, note=note)
    migrated = (pa._read(os.path.join(where, "state.json"), {}) or {}).get("migrated") or []
    say("settings", "done", "; ".join(migrated) if migrated else "Nothing to move")
    if logo is not None:
        pa.keep_logo(data_dir, pid, logo)
    say("install", "done", f"Version {going}")
    # 4. the health check
    healthy, why = True, ""
    if was_on:
        say("health", "now", "")
        now = pa._read(os.path.join(where, "state.json"), {}) or {}
        if now.get("state") != "enabled":
            healthy, why = False, f"It did not start. {str(now.get('message') or '')[-160:]}".strip()
        else:
            healthy, why = wait_healthy(pid, manifest)
    if not healthy:
        say("health", "failed", why)
        say("going-back", "now", "")
        plugin_life.rollback(data_dir, pid, media_dir, services=services)
        st = pa._read(os.path.join(where, "state.json"), {}) or {}
        st["message"] = f"Version {going} was rolled back by itself: {why}"[:300]
        pa._write(os.path.join(where, "state.json"), st)
        api_v1.audit(data_dir, "plugin_update_rolled_back", plugin=pid, version=going, previous=came, reason=why[:200])
        logs.event("error", "plug-ins", f"{manifest.get('name', pid)} {going} was not healthy, so Starboard went back to {came}: {why}")
        ran, ok, after_said = call_step(pid, old, "after", {**body, "outcome": "rolled_back"})
        say("going-back", "done", f"Back on {came}" + (f". {after_said}" if ran and after_said else ""))
        return {"outcome": "went-back", "from": came, "to": going, "migrated": migrated,
                "said": f"{manifest.get('name', pid)} {going} did not work, so Starboard went back to {came}. {why}".strip()}
    say("health", "done" if was_on and manifest.get("health") else "skipped",
        "It answered" if was_on and manifest.get("health") else "It is not active" if not was_on else "It has no health path")
    # 5. after, on the new version
    if was_on and update_info(manifest)["after"]:
        say("after", "now", "")
        _, ok, after_said = call_step(pid, manifest, "after", {**body, "outcome": "updated"})
        say("after", "done" if ok else "failed", after_said)
        if not ok:
            logs.event("warning", "plug-ins", f"{manifest.get('name', pid)} is updated, but its after step said: {after_said}")
            said = f"{said}. Its tidy-up step did not finish: {after_said}"
    else:
        say("after", "skipped", "It is not active" if not was_on else "It has no after step")
    return {"outcome": "updated", "from": came, "to": going, "migrated": migrated, "said": said}


ROLLBACK_STEPS = [("before", "Asking it to get ready"), ("swap", "Going back to the version before"), ("after", "Asking it to start again")]


def rollback_safely(data_dir, pid, media_dir, services=None, progress=None):
    """Roll back with the steps: before on the version running now (a failing one does not stop a Roll back, which
    is the way out of a version that is not working), the swap with its settings from before, and after on the
    version brought back, told {outcome: "rolled_back"}. Returns {outcome, said, from, to}."""
    from . import plugin_life
    from . import plugins_admin as pa
    import os
    say = progress or (lambda *a: None)
    where = pa.folder(data_dir, pid)
    now = pa._read(os.path.join(where, "manifest.json")) or {}
    kept = pa._read(os.path.join(where, "previous", "manifest.json"))
    if not kept or not now:
        raise LookupError("There is no earlier version to go back to")
    st = pa._read(os.path.join(where, "state.json"), {}) or {}
    was_on = st.get("state") in ("enabled", "failed") and bool(now.get("containers"))
    body = {"from": now.get("version"), "to": kept.get("version")}
    if was_on and st.get("state") == "enabled" and update_info(now)["before"]:
        say("before", "now", "")
        _, ok, said = call_step(pid, now, "before", body)
        say("before", "done" if ok else "failed", said if ok else f"{said}. Going back anyway")
    else:
        say("before", "skipped", "")
    say("swap", "now", "")
    said = plugin_life.rollback(data_dir, pid, media_dir, services=services)
    say("swap", "done", f"Version {kept.get('version')}, with its settings from before")
    if was_on and update_info(kept)["after"]:
        say("after", "now", "")
        _, ok, after_said = call_step(pid, kept, "after", {**body, "outcome": "rolled_back"})
        say("after", "done" if ok else "failed", after_said)
    else:
        say("after", "skipped", "")
    return {"outcome": "rolled-back", "from": now.get("version"), "to": kept.get("version"), "said": said}
