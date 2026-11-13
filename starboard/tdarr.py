"""Tdarr from Starboard (owner, 10 November 2026, DASH-306: "Tdarr settings should be used in Starboard and when added,
not need to be logged into", with basic choices). Starboard gives Tdarr its API key (discovery._tdarr) and sets it up:

- Libraries: films (/media/movies) and series (/media/tv), each on or off, with the cache folder /temp.
- What it does: save space (convert to H.265 with the widely used Migz plug-ins, keeping a file only when it got
  smaller), check files only (health checks, nothing converted), or nothing.
- How many at once: conversions on the processor (health checks run one at a time).
- When: any time, or in quiet hours (DASH-411): Starboard's download hours when they are set, otherwise 01:00 to
  06:00, the same hours plug-in jobs use. A Tdarr not set up yet starts with quiet hours chosen.

Nothing else of Tdarr's is changed; its own page still shows everything."""
from . import services

DAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
LIBRARIES = {"films": ("Films", "/media/movies", "sb-films"), "series": ("Series", "/media/tv", "sb-series")}
MODES = ("save_space", "check_only", "off")
# Save space: remove image streams, put streams in order, convert to H.265 on the processor, keep only if smaller.
SAVE_SPACE = [("Tdarr_Plugin_MC93_MigzImageRemoval", True), ("Tdarr_Plugin_lmg1_Reorder_Streams", True),
              ("Tdarr_Plugin_MC93_Migz1FFMPEG_CPU", True), ("Tdarr_Plugin_a9he_New_file_size_check", True)]
TEMPLATE = {  # Tdarr 2.x library fields, as its own page writes them
    "priority": 0, "foldersToIgnore": "", "foldersToIgnoreCaseInsensitive": False, "folderWatchScanInterval": 30,
    "scannerThreadCount": 2, "cache": "/temp", "output": "", "folderToFolderConversion": False,
    "folderToFolderConversionDeleteSource": False, "folderToFolderRecordHistory": True, "copyIfConditionsMet": False,
    "container": ".mkv", "containerFilter": "mkv,mp4,mov,m4v,mpg,mpeg,avi,flv,webm,wmv,vob,evo,iso,m2ts,ts",
    "folderWatching": True, "useFsEvents": False, "scheduledScanFindNew": True, "processLibrary": True,
    "processTranscodes": True, "processHealthChecks": True, "scanOnStart": True, "exifToolScan": True, "mediaInfoScan": True,
    "ffprobeShowData": False, "isDirectoryLibrary": False, "closedCaptionScan": False, "scanButtons": True, "scanFound": "",
    "navItemSelected": "navSourceFolder", "pluginCommunity": True, "handbrake": True, "ffmpeg": False, "handbrakescan": True,
    "ffmpegscan": False, "preset": "", "holdNewFiles": False, "holdFor": 3600, "holdForDisplayUnit": "hours",
    "pluginStackOverview": True, "filterResolutionsSkip": "", "filterCodecsSkip": "", "filterContainersSkip": "",
    "filterHardlinked": False, "processPluginsSequentially": True,
    "decisionMaker": {"settingsPlugin": True, "settingsFlows": False, "settingsVideo": False},
}


def _svc(cfg):
    s = next((x for x in cfg.data["services"] if x.get("type") == "tdarr" and x.get("api_key")), None)
    if not s:
        raise ValueError("Starboard has no key for Tdarr yet")
    return s


def _db(s, collection, mode, doc="", obj=None):
    return services.tdarr(s, "cruddb", {"data": {"collection": collection, "mode": mode, "docID": doc, "obj": obj or {}}})


def quiet_hours(cfg):
    """The hours Tdarr may work in when it is limited to quiet hours: the download hours when they are set, otherwise
    01:00 to 06:00, as plug-in jobs use (plugin_life._in_quiet_hours). (start, end), the end not included."""
    hours = (cfg.data.get("download_hours") if cfg is not None else None) or {}
    if hours.get("enabled"):
        return int(hours.get("start", 1)) % 24, int(hours.get("end", 6)) % 24
    return 1, 6


def _in(h, start, end):
    return start <= h < end if start < end else (h >= start or h < end)


def _schedule(night, hours=(1, 6)):
    return [{"_id": f"{d}:{h:02d}-{(h + 1) % 24:02d}", "checked": _in(h, *hours) if night else True} for d in DAYS for h in range(24)]


def state(cfg):
    s = _svc(cfg)
    libs = {x.get("_id"): x for x in (_db(s, "LibrarySettingsJSONDB", "getAll") or []) if isinstance(x, dict)}
    mine = {k: libs.get(v[2]) for k, v in LIBRARIES.items()}
    any_lib = next((x for x in mine.values() if x), None) or {}
    if not any_lib:
        mode = "save_space"
    elif not any_lib.get("processLibrary"):
        mode = "off"
    elif not any_lib.get("processTranscodes"):
        mode = "check_only"
    else:
        mode = "save_space"
    nodes = services.tdarr(s, "get-nodes") or {}
    node = next(iter(nodes.values()), {}) if isinstance(nodes, dict) else {}
    limits = node.get("workerLimits") or {}
    sched = any_lib.get("schedule") or []
    night = (bool(sched) and not all(x.get("checked") for x in sched)) if any_lib else True  # new: quiet hours (DASH-411)
    start, end = quiet_hours(cfg)
    stats = _db(s, "StatisticsJSONDB", "getById", "statistics") or {}
    others = [x.get("name") for k, x in libs.items() if k not in {v[2] for v in LIBRARIES.values()}]
    return {"libraries": {k: bool(v and v.get("processLibrary", True)) for k, v in mine.items()}, "mode": mode,
            "at_once": int(limits.get("transcodecpu") or 0), "night": night, "node": node.get("nodeName") or "",
            "files": int(stats.get("totalFileCount") or 0), "converted": int(stats.get("totalTranscodeCount") or 0),
            "checked": int(stats.get("totalHealthCheckCount") or 0), "saved_gb": round(float(stats.get("sizeDiff") or 0), 1),
            "other_libraries": [o for o in others if o], "quiet_hours": f"{start:02d}:00 to {end:02d}:00",
            "quiet_from_download_hours": bool(((cfg.data.get("download_hours") or {}).get("enabled")))}


def save(cfg, choice):
    """Writes the choices into Tdarr. Returns the new state and what was done, in words."""
    s = _svc(cfg)
    mode = choice.get("mode", "save_space")
    if mode not in MODES:
        raise ValueError("Choose Save space, Check files only or Off")
    at_once = int(choice.get("at_once", 1))
    if not 0 <= at_once <= 4:
        raise ValueError("At once is 0 to 4")
    night = bool(choice.get("night"))
    wanted = choice.get("libraries") or {}
    libs = {x.get("_id"): x for x in (_db(s, "LibrarySettingsJSONDB", "getAll") or []) if isinstance(x, dict)}
    done = []
    for key, (name, folder, doc) in LIBRARIES.items():
        on = bool(wanted.get(key, True))
        fields = {"processLibrary": on and mode != "off", "processTranscodes": mode == "save_space",
                  "processHealthChecks": mode != "off", "schedule": _schedule(night, quiet_hours(cfg)),
                  "pluginIDs": [{"_id": f"plugin{i + 1}", "id": pid, "checked": c, "source": "Community", "priority": i, "InputsDB": {}}
                                for i, (pid, c) in enumerate(SAVE_SPACE)]}
        if doc in libs:
            _db(s, "LibrarySettingsJSONDB", "update", doc, fields)
        elif on:
            _db(s, "LibrarySettingsJSONDB", "insert", doc, {**TEMPLATE, **fields, "_id": doc, "name": name, "folder": folder})
            done.append(f"Added {name} ({folder})")
    nodes = services.tdarr(s, "get-nodes") or {}
    for nid, node in (nodes.items() if isinstance(nodes, dict) else []):
        limits = node.get("workerLimits") or {}
        for kind, target in (("transcodecpu", at_once if mode == "save_space" else 0), ("healthcheckcpu", 1 if mode != "off" else 0)):
            have = int(limits.get(kind) or 0)
            for _ in range(abs(target - have)):
                services.tdarr(s, "alter-worker-limit", {"data": {"nodeID": nid, "process": "increase" if target > have else "decrease",
                                                                  "workerType": kind}})
    done.append({"save_space": "Converting to H.265 to save space", "check_only": "Checking files only", "off": "Not converting or checking"}[mode]
                + (f", {at_once} at a time" if mode == "save_space" else "") + (", in quiet hours only" if night else ""))
    from . import setup_left
    setup_left.record(cfg.data_dir, tdarr=True)  # Still to set up: done
    return {"state": state(cfg), "done": done}
