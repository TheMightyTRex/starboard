"""Recommended Jellyfin plug-ins (DASH-404), in Settings, Apps, Jellyfin: install and set up, one choice each.

Everything goes through Jellyfin's own API with the key in Manage apps (checked against Jellyfin 12.4's OpenAPI on
13 November 2026): /Repositories to add a plug-in repository, /Packages/Installed/{name} to install (Jellyfin picks the
newest version that suits its own version), /Plugins to read what is installed, /Plugins/{id}/{version}/Enable and
Disable, /Plugins/{id}/Configuration, /ScheduledTasks/{id}/Triggers, and /System/Restart. Starboard never uninstalls
a plug-in: switching to another choice deactivates the old one, which stays installed so it can come back.

The choices (research, 13 November 2026, from each project's manifest and source):
- Skip intros and credits, three ways:
  - Downloaded times (the default, the lightest): TheIntroDB (Jellyfin 12 and later, community times from
    theintrodb.org, no key needed, updated 3 November 2026), or SkipMe.db from the Intro Skipper team for Jellyfin
    10.11.5 to 11 (crowd-sourced times, updated 8 June 2026). Nothing is analysed: Jellyfin fills in the times during
    its own Media segment scan. Only shows other people have timed are covered.
  - Analysed on this server: Intro Skipper (Jellyfin 10.11.11 and later). Starboard sets it to analyse only in quiet
    hours: its "Detect and Analyze Media Segments" task runs daily at the start of download hours and stops at their
    end, analysis of new items as they arrive is deactivated, and one episode at a time (MaxParallelism 1).
  - Not skipped.
- Playback Reporting (Jellyfin's own repository): play statistics, which the lighter watch statistics plug-in reads.
- Merge Versions (danieladov's repository): copies of the same film or episode become one item with a version choice.
  Its two merge tasks move from every 24 hours to the start of quiet hours.
- Trakt (Jellyfin's own repository): records what is watched on trakt.tv. Each person links their own account in
  Jellyfin, so Starboard only installs it.
- Picture shrinker (DASH-433, TheMightyTRexUK's one repository for its Jellyfin plug-ins, Jellyfin 10.11 and 12): shrinks posters and photos of
  people inside Jellyfin, with a backup of each original, on a task in Jellyfin's Scheduled Tasks. It follows the same rules as
  Starboard's own Picture shrinker plug-in, which stays idle while this one is installed. Starboard leaves its schedule
  as it comes (every Sunday at 03:30). Its repository moved on 17 November 2026 from its own address to
  TheMightyTRex/jellyfin-plugins, one address for every Jellyfin plug-in by TheMightyTRexUK: when Starboard next offers
  Jellyfin plug-ins, it replaces the old address in Jellyfin with the new one (MOVED), and leaves every other
  repository as it is.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .livetv_jellyfin import _call

OFFICIAL = ("Jellyfin Stable", "https://repo.jellyfin.org/files/plugin/manifest.json")
INTRO_SKIPPER = ("Intro Skipper", "https://intro-skipper.org/manifest.json")
TREX = ("TheMightyTRexUK", "https://raw.githubusercontent.com/TheMightyTRex/jellyfin-plugins/main/manifest.json")
# Repository addresses that have moved: the old address -> the repository that replaces it in Jellyfin.
MOVED = {"https://raw.githubusercontent.com/TheMightyTRex/jellyfin-plugin-picture-shrinker/main/manifest.json": TREX}

PACKAGES = {
    "theintrodb": {"name": "TheIntroDB", "guid": "c9e41b95-63e4-45e2-9db6-b83df21ae5e7", "min": (12, 0),
                   "repo": ("TheIntroDB", "https://raw.githubusercontent.com/TheIntroDB/jellyfin-plugin/main/manifest.json")},
    "skipmedb": {"name": "SkipMe.db", "guid": "b2a63e62-0ac5-4575-9ad2-2c7534ccb83d", "min": (10, 11, 5), "repo": INTRO_SKIPPER},
    "introskipper": {"name": "Intro Skipper", "guid": "c83d86bb-a1e0-4c35-a113-e2101cf4ee6b", "min": (10, 11, 11), "repo": INTRO_SKIPPER},
    "playback": {"name": "Playback Reporting", "guid": "5c534381-91a3-43cb-907a-35aa02eb9d2c", "min": (10, 11), "repo": OFFICIAL},
    "merge": {"name": "Merge Versions", "guid": "f21bbed8-3a97-4d8b-88b2-48aaa65427cb", "min": (10, 11),
              "repo": ("Merge Versions", "https://raw.githubusercontent.com/danieladov/JellyfinPluginManifest/master/manifest.json")},
    "trakt": {"name": "Trakt", "guid": "4fe3201e-d6ae-4f2e-8917-e12bda571281", "min": (10, 11), "repo": OFFICIAL},
    "pictures": {"name": "Picture shrinker", "guid": "80bf9325-d299-4e24-ac74-c087aeec3011", "min": (10, 11), "below": (13,),
                 "needs": "Needs Jellyfin 10.11 or 12.", "released_only": True, "repo": TREX},
}

SKIP = ("theintrodb", "skipmedb", "introskipper")

GROUPS = [
    {"id": "skip", "title": "Skip intros and credits",
     "what": "A Skip button, or an automatic skip, for intros, recaps and credits. Fewer presses for keyboard, switch and remote users.",
     "choices": [
         {"id": "downloaded", "label": "Downloaded times (recommended)",
          "hint": "Times other people have marked, downloaded when Jellyfin scans. Almost no processor or memory. Shows nobody has timed yet have no Skip button."},
         {"id": "analysed", "label": "Analysed on this server, in quiet hours",
          "hint": "Intro Skipper listens to each episode to find the intro and credits. It covers every show, but uses a processor core for each episode, so Starboard keeps it to quiet hours, one episode at a time."},
         {"id": "none", "label": "Do not skip", "hint": "Nothing is added. A plug-in Starboard installed before is deactivated, not removed."}]},
    {"id": "playback", "title": "Playback Reporting",
     "what": "Keeps a record of what each person plays, for watch statistics. The lighter watch statistics plug-in reads it, so a Full install can do without Jellystat.",
     "choices": [{"id": "on", "label": "Install and activate"}, {"id": "none", "label": "Do not install"}]},
    {"id": "merge", "title": "Merge Versions",
     "what": "Two copies of the same film or episode, for example HD and 4K, become one item with a choice of version.",
     "choices": [{"id": "on", "label": "Install and activate", "hint": "Starboard sets its merge to run once a day, at the start of quiet hours."},
                 {"id": "none", "label": "Do not install"}]},
    {"id": "trakt", "title": "Trakt",
     "what": "Records what each person watches on trakt.tv, and can bring their Trakt history in. Each person links their own Trakt account in Jellyfin afterwards.",
     "choices": [{"id": "on", "label": "Install and activate"}, {"id": "none", "label": "Do not install"}]},
    {"id": "pictures", "title": "Picture shrinker",
     "what": "Shrinks the posters and photos of cast and crew Jellyfin keeps, so they take less space, with a backup of each original. It runs inside Jellyfin, in its Scheduled Tasks; Starboard's own Picture shrinker plug-in stays idle while it is installed.",
     "choices": [{"id": "on", "label": "Install and activate", "hint": "It runs every Sunday at 03:30 until you change it in Jellyfin's Scheduled Tasks. Its settings are in Jellyfin's Dashboard, Plugins."},
                 {"id": "none", "label": "Do not install"}]},
]
COST = {"skip": {"downloaded": "A few MB inside Jellyfin; a short download for each episode when Jellyfin scans.",
                 "analysed": "A few MB inside Jellyfin; while analysing, about 1 processor core for each episode, in quiet hours only.",
                 "none": "Nothing."},
        "playback": "A few MB inside Jellyfin and a small database that grows with each play.",
        "merge": "A few MB inside Jellyfin; a short library scan once a day in quiet hours.",
        "trakt": "A few MB inside Jellyfin; a small message to Trakt when someone finishes watching.",
        "pictures": "A few MB inside Jellyfin; during a run, one processor core at the lowest priority. The backup takes about as much space as the pictures did."}

_lock = threading.Lock()
TICKS_PER_HOUR = 36_000_000_000


def find(services):
    """The Jellyfin in Manage apps with its key, or None (the example server swaps this for its stand-in)."""
    return next((s for s in services or [] if s.get("type") == "jellyfin" and s.get("enabled", True)
                 and s.get("url") and s.get("api_key")), None)


def _version(text):
    out = []
    for part in str(text or "").split(".")[:3]:
        try:
            out.append(int(part))
        except ValueError:
            break
    return tuple(out)


def _norm(guid):
    return str(guid or "").replace("-", "").lower()


def _state_path(data_dir):
    return os.path.join(data_dir, "jellyfin-plugins.json")


def _read(data_dir):
    try:
        with open(_state_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(data_dir, data):
    tmp = _state_path(data_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, _state_path(data_dir))


def quiet_hours(cfg_data):
    """Start hour and length of quiet hours: download hours when set, otherwise 01:00 to 06:00 (as plug-in jobs)."""
    hours = (cfg_data or {}).get("download_hours") or {}
    start, end = (int(hours.get("start", 1)), int(hours.get("end", 6))) if hours.get("enabled") else (1, 6)
    return start % 24, ((end - start) % 24) or 24


def downloaded_choice(version):
    """TheIntroDB on Jellyfin 12 and later, SkipMe.db on 10.11.5 and later, None on older Jellyfin."""
    v = _version(version)
    for key in ("theintrodb", "skipmedb"):
        if v >= PACKAGES[key]["min"]:
            return key
    return None


def suits(key, version):
    """True when this Jellyfin's version is one the package is made for (from min, and below `below` when given)."""
    pkg, v = PACKAGES[key], _version(version)
    return v >= pkg["min"] and (not pkg.get("below") or v < pkg["below"])


# A package marked released_only (DASH-433's Picture shrinker) is offered only once its repository lists a version
# for this Jellyfin: its repository is public before its first release, and Jellyfin cannot install from an empty list.
# The list is read at most every 6 hours, only when Settings, Apps, Jellyfin is opened or a choice is made. A version
# suits this Jellyfin when its targetAbi is on the same line and not newer: Jellyfin 10 lines are two numbers (10.11),
# from Jellyfin 12 one number (12.0.0.0 suits 12.0 to 12.4), as Jellyfin 12's plug-ins all target 12.0.0.0.
RELEASE_CHECK_SECONDS = 6 * 3600
_released = {}  # repository address -> (when read, [targetAbi of each version])


def _fetch_manifest(url):
    with urllib.request.urlopen(url, timeout=10) as r:  # a fixed GitHub address from PACKAGES  # nosec B310
        return json.loads(r.read(2_000_000))


def released(key, version, fetch=None, now=None):
    """True when the package needs no release check, or its repository lists a version this Jellyfin can run."""
    pkg = PACKAGES[key]
    if not pkg.get("released_only"):
        return True
    url, now = pkg["repo"][1], now or time.time()
    seen = _released.get(url)
    if not seen or now - seen[0] > RELEASE_CHECK_SECONDS:
        try:
            listed = [p for p in (fetch or _fetch_manifest)(url) or [] if str(p.get("guid", "")).lower() == pkg["guid"]]
            abis = [str(v.get("targetAbi") or "") for p in listed for v in p.get("versions") or []]
        except (urllib.error.URLError, OSError, ValueError, AttributeError, TypeError):
            abis = seen[1] if seen else []  # unknown: keep what was read before, or not offered yet
        seen = _released[url] = (now, abis)
    have = _version(version)
    return any(_version(a) and _line(_version(a)) == _line(have) and _version(a) <= have for a in seen[1])


def _line(v):
    """Jellyfin's release line: (10, 11) for 10.11.x, (12,) for every 12.x."""
    return tuple(v[:2]) if v and v[0] < 12 else tuple(v[:1])


NOT_RELEASED = "Not released yet. Starboard offers it once its first version for your Jellyfin is out."


def needs_words(key):
    pkg = PACKAGES[key]
    lo = ".".join(map(str, pkg["min"]))
    return pkg.get("needs") or f"Needs Jellyfin {lo} or later."


def _installed(jf, opener=None):
    plugins = _call(jf["url"], jf["api_key"], "GET", "/Plugins", opener=opener) or []
    by_guid = {_norm(p.get("Id")): p for p in plugins}
    out = {}
    for key, pkg in PACKAGES.items():
        p = by_guid.get(_norm(pkg["guid"]))
        if p:
            out[key] = {"name": p.get("Name") or pkg["name"], "version": str(p.get("Version") or ""),
                        "status": str(p.get("Status") or ""), "id": p.get("Id")}
    return out


def _active(p):
    return bool(p) and p["status"] in ("Active", "Restart")


def _chosen(group, installed):
    if group == "skip":
        if _active(installed.get("introskipper")):
            return "analysed"
        if _active(installed.get("theintrodb")) or _active(installed.get("skipmedb")):
            return "downloaded"
        return "none"
    return "on" if _active(installed.get(group)) else "none"


def status(services, data_dir, cfg_data=None, opener=None):
    """What is installed and chosen, for Settings, Apps, Jellyfin. Finishes the set-up of a plug-in Starboard
    installed or activated that has become active since (after Jellyfin's restart), once for each version. A plug-in
    the owner added in Jellyfin is only read, never changed (DASH-409)."""
    jf = find(services)
    if not jf:
        return {"connected": False, "groups": []}
    try:
        info = _call(jf["url"], jf["api_key"], "GET", "/System/Info", opener=opener) or {}
        installed = _installed(jf, opener)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {"connected": False, "problem": f"Jellyfin did not answer: {getattr(e, 'reason', e)}", "groups": []}
    version = str(info.get("Version") or "")
    finished = move_repos(jf, opener) + finish_setup(jf, data_dir, installed, cfg_data, opener)
    start, length = quiet_hours(cfg_data)
    groups = []
    for g in GROUPS:
        keys = SKIP if g["id"] == "skip" else (g["id"],)
        choices = []
        for c in g["choices"]:
            c = dict(c)
            if g["id"] == "skip" and c["id"] == "downloaded":
                pick = downloaded_choice(version)
                c["available"] = bool(pick)
                c["package"] = PACKAGES[pick]["name"] if pick else ""
                if not pick:
                    c["hint"] = "Needs Jellyfin 10.11.5 or later."
            elif g["id"] == "skip" and c["id"] == "analysed":
                c["available"] = _version(version) >= PACKAGES["introskipper"]["min"]
                c["package"] = "Intro Skipper"
                if not c["available"]:
                    c["hint"] = "Needs Jellyfin 10.11.11 or later."
                else:
                    c["hint"] += f" Quiet hours now: {start:02d}:00 for {length} hours."
            elif c["id"] == "on" and PACKAGES.get(g["id"], {}).get("below"):
                c["available"] = suits(g["id"], version)
                if not c["available"]:
                    c["hint"] = needs_words(g["id"])
                elif not released(g["id"], version):
                    c["available"] = False
                    c["hint"] = NOT_RELEASED
            else:
                c["available"] = True
            if isinstance(COST[g["id"]], dict):
                c["cost"] = COST[g["id"]][c["id"]]
            choices.append(c)
        cost = COST[g["id"]] if isinstance(COST[g["id"]], str) else ""
        groups.append({"id": g["id"], "title": g["title"], "what": g["what"], "choices": choices,
                       "chosen": _chosen(g["id"], installed), "cost": cost,
                       "installed": [dict(installed[k], key=k) for k in keys if k in installed]})
    return {"connected": True, "name": jf.get("name") or "Jellyfin", "version": version,
            "restart": bool(info.get("HasPendingRestart")), "can_restart": info.get("CanSelfRestart", True) is not False,
            "finished": finished, "groups": groups}


def move_repos(jf, opener=None):
    """Replaces each moved repository address in Jellyfin with its new one (MOVED), in the same place in the list and
    with its Enabled setting kept, or removes it when the new one is already there. Every other repository stays as it
    is. Returns what was done, in words; nothing when no old address is listed or Jellyfin does not answer."""
    try:
        repos = _call(jf["url"], jf["api_key"], "GET", "/Repositories", opener=opener) or []
        urls = {str(r.get("Url") or "").rstrip("/") for r in repos}
        moved = [r for r in repos if str(r.get("Url") or "").rstrip("/") in MOVED]
        if not moved:
            return []
        kept = []
        for r in repos:
            new = MOVED.get(str(r.get("Url") or "").rstrip("/"))
            if not new:
                kept.append(r)
            elif new[1] not in urls:
                kept.append(dict(r, Name=new[0], Url=new[1]))
                urls.add(new[1])
        _call(jf["url"], jf["api_key"], "POST", "/Repositories", kept, opener=opener)
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return [f"Replaced the old Picture shrinker repository address with the {TREX[0]} one, which lists every version"]


def _ensure_repo(jf, repo, opener=None):
    name, url = repo
    repos = _call(jf["url"], jf["api_key"], "GET", "/Repositories", opener=opener) or []
    for r in repos:
        if str(r.get("Url") or "").rstrip("/") == url.rstrip("/"):
            if r.get("Enabled") is False:
                r["Enabled"] = True
                _call(jf["url"], jf["api_key"], "POST", "/Repositories", repos, opener=opener)
            return False
    _call(jf["url"], jf["api_key"], "POST", "/Repositories", repos + [{"Name": name, "Url": url, "Enabled": True}], opener=opener)
    return True


def _install(jf, key, installed, opener=None):
    pkg = PACKAGES[key]
    have = installed.get(key)
    if have:
        if have["status"] == "Disabled":
            _call(jf["url"], jf["api_key"], "POST", f"/Plugins/{have['id']}/{urllib.parse.quote(have['version'])}/Enable", opener=opener)
            return f"Activated {pkg['name']} again"
        return None
    added = _ensure_repo(jf, pkg["repo"], opener)
    q = urllib.parse.urlencode({"assemblyGuid": pkg["guid"], "repositoryUrl": pkg["repo"][1]})
    try:
        _call(jf["url"], jf["api_key"], "POST", f"/Packages/Installed/{urllib.parse.quote(pkg['name'])}?{q}", opener=opener)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Jellyfin could not find {pkg['name']} for its version in {pkg['repo'][0]}") from None
        raise
    return f"Installed {pkg['name']}" + (f", from the {pkg['repo'][0]} repository Starboard added" if added else "")


def _deactivate(jf, key, installed, opener=None):
    have = installed.get(key)
    if not have or have["status"] not in ("Active", "Restart"):
        return None
    _call(jf["url"], jf["api_key"], "POST", f"/Plugins/{have['id']}/{urllib.parse.quote(have['version'])}/Disable", opener=opener)
    return f"Deactivated {PACKAGES[key]['name']} (still installed)"


def choose(services, data_dir, group, choice, cfg_data=None, opener=None):
    """Install, activate or deactivate for one group's choice. Returns what was done, in words."""
    g = next((x for x in GROUPS if x["id"] == group), None)
    if not g or choice not in [c["id"] for c in g["choices"]]:
        raise ValueError("Choose one of the offered plug-ins")
    jf = find(services)
    if not jf:
        raise ValueError("Add Jellyfin with its API key in Manage apps first")
    with _lock:
        info = _call(jf["url"], jf["api_key"], "GET", "/System/Info", opener=opener) or {}
        installed = _installed(jf, opener)
        moved = move_repos(jf, opener)
        if group == "skip":
            want = {"downloaded": downloaded_choice(info.get("Version")), "analysed": "introskipper", "none": None}[choice]
            if choice == "downloaded" and not want:
                raise ValueError("Downloaded times need Jellyfin 10.11.5 or later")
            if choice == "analysed" and _version(info.get("Version")) < PACKAGES["introskipper"]["min"]:
                raise ValueError("Intro Skipper needs Jellyfin 10.11.11 or later")
            others = [k for k in SKIP if k != want]
        else:
            want = group if choice == "on" else None
            others = [] if want else [group]
            if want and not suits(want, info.get("Version")):
                raise ValueError(f"{PACKAGES[want]['name']}: {needs_words(want)}")
            if want and not released(want, info.get("Version")):
                raise ValueError(f"{PACKAGES[want]['name']}: {NOT_RELEASED}")
        done = [d for d in (_deactivate(jf, k, installed, opener) for k in others) if d]
        if want:
            d = _install(jf, want, installed, opener)
            if d:
                done.append(d)
                _mark_ours(data_dir, want)
    return {"done": (moved + done) or ["Nothing to change"], "restart": bool(done)}


def restart(services, opener=None):
    jf = find(services)
    if not jf:
        raise ValueError("Add Jellyfin with its API key in Manage apps first")
    _call(jf["url"], jf["api_key"], "POST", "/System/Restart", opener=opener)


def _quiet_trigger(cfg_data):
    start, length = quiet_hours(cfg_data)
    return {"Type": "DailyTrigger", "TimeOfDayTicks": start * TICKS_PER_HOUR, "MaxRuntimeTicks": length * TICKS_PER_HOUR}


def _set_task(jf, tasks, key, trigger, opener=None):
    task = next((t for t in tasks if t.get("Key") == key), None)
    if task:
        _call(jf["url"], jf["api_key"], "POST", f"/ScheduledTasks/{task['Id']}/Triggers", [trigger], opener=opener)
    return bool(task)


def _mark_ours(data_dir, key):
    """Note that Starboard installed or activated this plug-in, so its set-up may be finished later (DASH-409)."""
    state = _read(data_dir)
    ours = state.setdefault("ours", [])
    if key not in ours:
        ours.append(key)
        _write(data_dir, state)


def finish_setup(jf, data_dir, installed, cfg_data=None, opener=None):
    """Set up Intro Skipper and Merge Versions once they are active, once for each installed version, so a change
    the owner makes in Jellyfin afterwards stays. Only for a plug-in Starboard installed or activated: one the owner
    added in Jellyfin keeps its own settings, so reading the list changes nothing (DASH-409). Returns what was done,
    in words."""
    state = _read(data_dir)
    set_up = state.setdefault("set_up", {})
    ours = state.get("ours") or []
    done = []
    for key in ("introskipper", "merge"):
        p = installed.get(key)
        if key not in ours or not p or p["status"] != "Active" or set_up.get(key) == p["version"]:
            continue
        try:
            tasks = _call(jf["url"], jf["api_key"], "GET", "/ScheduledTasks", opener=opener) or []
            if key == "introskipper":
                conf = _call(jf["url"], jf["api_key"], "GET", f"/Plugins/{p['id']}/Configuration", opener=opener) or {}
                conf.update(AutoDetectIntros=False, MaxParallelism=1)
                _call(jf["url"], jf["api_key"], "POST", f"/Plugins/{p['id']}/Configuration", conf, opener=opener)
                if not _set_task(jf, tasks, "IntroSkipperDetectSegmentsTask", _quiet_trigger(cfg_data), opener):
                    continue  # Jellyfin has not listed the task yet: try again next time
                done.append("Intro Skipper analyses in quiet hours only, one episode at a time")
            else:
                found = [_set_task(jf, tasks, k, _quiet_trigger(cfg_data), opener) for k in ("MergeMoviesTask", "MergeEpisodesTask")]
                if not any(found):
                    continue
                done.append("Merge Versions merges once a day, in quiet hours")
        except (urllib.error.URLError, OSError, ValueError):
            continue
        set_up[key] = p["version"]
    if done:
        _write(data_dir, state)
    return done
