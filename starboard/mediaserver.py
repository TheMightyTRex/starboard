"""The media server contract (DASH-565, design/media-server-plugins.md): what Starboard asks of a media server, and the
one place that is filled by whichever media server is active. Jellyfin is the first, and the default, so nothing a
person sees changes.

A media server is an adapter: a small class with the calls below. Starboard asks the active one for its name, status,
libraries, what is playing, what was added, users, a refresh and a sign-in check, and draws only the capabilities it
offers (no empty panel and no disabled button). The adapters here run in Starboard's own process and are imported only
when asked for, so a server that is not active costs no memory. A media server plug-in (Plex and Emby are next,
DASH-566) fills the same slot.

The active one is `extras.media_server`; when it is not set it is "jellyfin", so an existing install needs no
migration, and an older Starboard ignores the key. Nothing is written until a person chooses another server."""

import re
import time
import urllib.parse

from . import services

DEFAULT = "jellyfin"
PAGE = "/settings-jellyfin.html"  # Settings, Apps: the active media server's tab, whichever it is (its address is kept for older links)

# What a media server may offer beyond the nine required calls; a page draws a part only when it is listed.
CAPABILITIES = ("admin_libraries", "admin_tasks", "admin_activity", "admin_logs", "play", "watched", "restart", "own_plugins", "conversion_test", "live_tv", "libraries_add", "first_run",
                "history_import", "user_defaults", "metadata_folder", "detect", "updates")
# What each capability means to a person, and why a server without it says so (the Media server tab lists every one for each
# server, so nothing is hidden: "Yes", or "No" with the reason in words). A server's own reasons are in its `limits`.
CAPABILITY_LABELS = {
    "admin_libraries": "Libraries and scans", "admin_tasks": "Scheduled tasks", "admin_activity": "Activity", "admin_logs": "The server's logs",
    "play": "Play from Library", "watched": "Watched and not watched", "restart": "Restart from Starboard",
    "own_plugins": "The server's own plug-ins and their updates", "conversion_test": "Test of video conversion",
    "live_tv": "Live TV channels", "libraries_add": "Libraries filled by plug-ins", "first_run": "First set-up by Starboard",
    "history_import": "Watch history import", "user_defaults": "Defaults for every user",
    "metadata_folder": "Pictures and details folder", "detect": "Finding it on this computer", "updates": "Checking and updating the server",
}
REQUIRED = ("describe", "status", "libraries", "playing", "recent", "refresh", "users", "sign_in_check", "keys_needed")


class MediaServer:
    """The contract. Each call takes the saved services (Settings, Apps) and answers plain data; one that cannot be
    answered raises services.ServiceError with a sentence for people."""

    id = ""
    name = ""
    service_type = ""  # the entry in the saved services that holds its address and key
    capabilities = ()
    page = ""  # its own settings page, when it has one

    def find_service(self, services_list):
        """The saved app that holds its address and key (enabled, with both), or None."""
        return next((s for s in services_list or [] if isinstance(s, dict) and s.get("type") == self.service_type
                     and s.get("enabled", True) and s.get("api_key") and s.get("url")), None)

    def _service(self, services_list):
        found = self.find_service(services_list)
        if not found:
            raise services.ServiceError(f"{self.name} is not set up yet. Add it with its API key in Settings, Apps")
        return found

    limits = {}  # capability id: the plain reason this server does not offer it (or offers it only in part)

    def capability_rows(self):
        """Every capability, each marked Yes or No for this server with a reason in words (never a colour alone)."""
        return [{"id": c, "label": CAPABILITY_LABELS[c], "can": c in self.capabilities,
                 "why": "" if c in self.capabilities else self.limits.get(c, f"{self.name} does not offer this through Starboard yet")}
                for c in CAPABILITIES]

    # Administration (DASH-568): the server's own admin jobs Starboard can do, each read or done only when a person asks. ----------
    admin_coverage_rows = ()  # (job, who does it: "starboard", "server" or "no", words, page of the server's own admin, "" for none)

    def admin_coverage(self):
        """Every administration job of this server: where it is done, so a person never has to guess. `who` is "starboard" (done
        on the media server tab), "server" (done in the server's own pages: the words say why and `page` says where) or "no"
        (nobody can, through the server's interface)."""
        return [{"job": j, "who": w, "says": t, "page": p} for j, w, t, p in self.admin_coverage_rows]

    def _no(self, what):
        raise services.ServiceError(f"{self.name} does not give Starboard {what}")

    def admin_libraries(self, services_list):
        """[{id, name, type, folders: [str], count: int or None}]."""
        self._no("its libraries")

    def admin_scan(self, services_list, library_id="", how="new"):
        """Asks the server to scan one library, or all when library_id is "". how: "new" (new and changed files) or "all"
        (every file and its details again)."""
        self._no("a scan")

    def admin_tasks(self, services_list):
        """[{id, name, group, state ("idle", "running"), last: words, when: words about its times}]."""
        self._no("its scheduled tasks")

    def admin_run_task(self, services_list, task_id):
        self._no("a way to run a task")

    def admin_activity(self, services_list, limit=40):
        """[{when, what, who, kind}], newest first."""
        self._no("its activity")

    def admin_logs(self, services_list):
        """[{name, size, when}], newest first."""
        self._no("its log files")

    def admin_log(self, services_list, name, lines=300):
        """The last `lines` lines of one log file, as text."""
        self._no("its log files")

    # Items in the server, for Play and Watched (optional: offered when "play" or "watched" is a capability) -------------
    def play_info(self, services_list):
        """What a Play link needs besides the item's id: {"server_id": ...} or {}."""
        return {}

    def play_link(self, base, item_id, server_id=""):
        raise NotImplementedError

    def film_ids(self, services_list):
        """{("tmdb" or "imdb", id): the server's own id} for every film it has."""
        raise NotImplementedError

    def watched_user(self, services_list, wanted=""):
        """(id, name) of the person whose watched state is shown, or None."""
        raise NotImplementedError

    def watched_film(self, services_list, who, tmdb):
        """{"id", "watched"} for a film, or None when the server does not have it."""
        raise NotImplementedError

    def watched_series(self, services_list, who, tmdb):
        """{"id", "episodes": {(season, episode): {"id", "watched"}}} for a series, or None."""
        raise NotImplementedError

    def mark(self, services_list, who, ids, watched):
        raise NotImplementedError

    def describe(self):
        return {"id": self.id, "name": self.name, "kind": "media-server", "page": self.page, "capabilities": list(self.capabilities),
                "capability_rows": self.capability_rows()}

    def status(self, services_list):
        raise NotImplementedError

    def libraries(self, services_list):
        raise NotImplementedError

    def playing(self, services_list):
        raise NotImplementedError

    def recent(self, services_list, limit=12):
        raise NotImplementedError

    def refresh(self, services_list):
        raise NotImplementedError

    def users(self, services_list):
        raise NotImplementedError

    def sign_in_check(self, services_list):
        raise NotImplementedError

    def keys_needed(self):
        raise NotImplementedError

    def legacy_status(self, services_list):
        """The answer the dashboard and System have always had from GET /api/jellyfin (its own words for each part)."""
        raise NotImplementedError


def _trigger_words(triggers):
    """A scheduled task's times in plain words, from the server's trigger list (ticks are tenths of a microsecond)."""
    out = []
    for t in triggers or []:
        if not isinstance(t, dict):
            continue
        kind = t.get("Type")
        if kind == "DailyTrigger":
            out.append(f"every day at {_clock(t.get('TimeOfDayTicks'))}")
        elif kind == "WeeklyTrigger":
            out.append(f"every {t.get('DayOfWeek', 'week')} at {_clock(t.get('TimeOfDayTicks'))}")
        elif kind == "IntervalTrigger":
            mins = round((t.get("IntervalTicks") or 0) / 600_000_000)
            out.append(f"every {mins // 60} hours" if mins >= 120 and mins % 60 == 0 else f"every {mins} minutes")
        elif kind == "StartupTrigger":
            out.append("when the server starts")
    return ", ".join(out) or "only when you run it"


def _clock(ticks):
    mins = round((ticks or 0) / 600_000_000)
    return f"{mins // 60:02d}:{mins % 60:02d}"


class MediaBrowser(MediaServer):
    """What Jellyfin and Emby share: both answer the same questions in the same shapes (Jellyfin began as a copy of
    Emby), at the same paths, apart from a prefix and the header that carries the key."""

    prefix = ""

    def _headers(self, service):
        raise NotImplementedError

    def _send(self, service, method, path, body=None):
        import json
        import urllib.request
        headers = self._headers(service)
        data = None
        if body is not None:  # a change (DASH-587): a library or a person added to the new server, as JSON
            data = json.dumps(body).encode()
            headers = {**headers, "Content-Type": "application/json"}
        req = urllib.request.Request(service["url"].rstrip("/") + self.prefix + path, data=data, method=method, headers=headers)
        return services._fetch(service, req, services.TIMEOUT)

    def status(self, services_list):
        try:
            got = self.legacy_status(services_list)
        except services.ServiceError as e:
            return {"configured": True, "up": False, "name": self.name, "version": "", "update_available": False,
                    "restart_needed": False, "playing": 0, "why": str(e)}
        if not got.get("configured"):
            return {"configured": False, "up": False, "name": self.name, "version": "", "update_available": False,
                    "restart_needed": False, "playing": 0, "why": ""}
        return {"configured": True, "up": True, "name": got.get("name") or self.name, "version": got.get("version", ""),
                "update_available": bool(got.get("update")), "restart_needed": bool(got.get("restart")),
                "playing": len(got.get("playing") or []), "why": ""}

    def libraries(self, services_list):
        rows = self._send(self._service(services_list), "GET", "/Library/VirtualFolders") or []
        return [{"id": str(r.get("ItemId") or r.get("Name") or ""), "name": str(r.get("Name") or ""),
                 "type": str(r.get("CollectionType") or "mixed"), "count": None}
                for r in rows if isinstance(r, dict)]

    def playing(self, services_list):
        return [{"user": p["user"], "title": p["title"], "kind": p["type"], "device": p["device"], "converting": p["transcoding"],
                 "progress": p["progress"]} for p in self.legacy_status(services_list).get("playing") or []]

    def recent(self, services_list, limit=12):
        rows = self.legacy_status(services_list).get("added") or []
        return [{"title": r["title"], "kind": r["type"], "added": r["when"], "link": None} for r in rows[:max(0, int(limit))]]

    def refresh(self, services_list):
        self._send(self._service(services_list), "POST", "/Library/Refresh")
        return {"asked": True}

    # Administration, shared by Jellyfin and Emby (the same questions, under a prefix) ----------------------------------------
    def admin_libraries(self, services_list):
        rows = self._send(self._service(services_list), "GET", "/Library/VirtualFolders") or []
        return [{"id": str(r.get("ItemId") or ""), "name": str(r.get("Name") or ""), "type": str(r.get("CollectionType") or "mixed"),
                 "folders": [str(x) for x in r.get("Locations") or [] if isinstance(x, str)][:20], "count": None}
                for r in rows if isinstance(r, dict) and r.get("ItemId")]

    def admin_scan(self, services_list, library_id="", how="new"):
        found = self._service(services_list)
        if how not in ("new", "all"):
            raise ValueError("Choose new and changed files, or everything")
        if not library_id:
            self._send(found, "POST", "/Library/Refresh")
            return {"asked": True}
        if not re.match(r"^[0-9A-Za-z-]{1,64}$", library_id):
            raise ValueError("That is not a library")
        mode = "Default" if how == "new" else "FullRefresh"
        self._send(found, "POST", f"/Items/{library_id}/Refresh?Recursive=true&ImageRefreshMode={mode}&MetadataRefreshMode={mode}&ReplaceAllImages=false&ReplaceAllMetadata={'true' if how == 'all' else 'false'}")
        return {"asked": True}

    def admin_tasks(self, services_list):
        out = []
        for t in self._send(self._service(services_list), "GET", "/ScheduledTasks?isHidden=false") or []:
            if not isinstance(t, dict) or not t.get("Id"):
                continue
            last = t.get("LastExecutionResult") or {}
            out.append({"id": str(t["Id"]), "name": str(t.get("Name") or ""), "group": str(t.get("Category") or ""),
                        "state": "running" if t.get("State") == "Running" else "idle",
                        "last": f"{last.get('Status', '')} {str(last.get('EndTimeUtc') or '')[:16].replace('T', ' ')}".strip(),
                        "when": _trigger_words(t.get("Triggers"))})
        return out

    def admin_run_task(self, services_list, task_id):
        if not re.match(r"^[0-9A-Za-z-]{1,64}$", str(task_id)):
            raise ValueError("That is not a task")
        self._send(self._service(services_list), "POST", f"/ScheduledTasks/Running/{task_id}")
        return {"asked": True}

    def admin_activity(self, services_list, limit=40):
        got = self._send(self._service(services_list), "GET", f"/System/ActivityLog/Entries?limit={max(1, min(int(limit), 100))}") or {}
        return [{"when": str(e.get("Date") or "")[:16].replace("T", " "), "what": str(e.get("Name") or ""), "who": str(e.get("ShortOverview") or ""),
                 "kind": str(e.get("Severity") or "Information")} for e in (got.get("Items") or []) if isinstance(e, dict)]

    def admin_logs(self, services_list):
        rows = self._send(self._service(services_list), "GET", "/System/Logs") or []
        return sorted(({"name": str(r.get("Name") or ""), "size": int(r.get("Size") or 0), "when": str(r.get("DateModified") or "")[:16].replace("T", " ")}
                       for r in rows if isinstance(r, dict) and r.get("Name")), key=lambda r: r["when"], reverse=True)[:60]

    def admin_log(self, services_list, name, lines=300):
        if not re.match(r"^[A-Za-z0-9._ -]{1,120}$", str(name)) or ".." in str(name):
            raise ValueError("That is not a log file")
        got = self._send(self._service(services_list), "GET", "/System/Logs/Log?name=" + urllib.parse.quote(str(name)))
        return "\n".join(str(got).splitlines()[-max(1, min(int(lines), 1000)):])

    def users(self, services_list):
        rows = self._send(self._service(services_list), "GET", "/Users") or []
        return [{"id": str(r.get("Id") or ""), "name": str(r.get("Name") or ""),
                 "admin": bool((r.get("Policy") or {}).get("IsAdministrator"))} for r in rows if isinstance(r, dict)]

    def sign_in_check(self, services_list):
        try:
            info = self._send(self._service(services_list), "GET", "/System/Info")
        except services.ServiceError as e:
            return {"ok": False, "why": str(e)}
        return {"ok": True, "why": "", "name": (info or {}).get("ServerName") or self.name, "version": (info or {}).get("Version", "")}


class Jellyfin(MediaBrowser):
    id = "jellyfin"
    name = "Jellyfin"
    service_type = "jellyfin"
    page = PAGE
    capabilities = ("admin_libraries", "admin_tasks", "admin_activity", "admin_logs", "play", "watched", "restart", "own_plugins", "conversion_test", "live_tv", "libraries_add", "first_run",
                    "history_import", "user_defaults", "metadata_folder", "detect", "updates")
    admin_coverage_rows = (
        ("Libraries: list, scan new and changed files, refresh everything", "starboard", "On this tab, under Administration.", ""),
        ("Libraries: add, rename or remove one, and change its folders and options", "later", "Not in Starboard yet. Use Jellyfin's Dashboard, Libraries.", "/web/#/dashboard/libraries"),
        ("People: their passwords", "starboard", "Settings, People makes and changes a password for each person.", ""),
        ("People: add or remove an account, their rights and the libraries they see", "later", "Not in Starboard yet. Use Jellyfin's Dashboard, Users.", "/web/#/dashboard/users"),
        ("Scheduled tasks: read, and run now", "starboard", "On this tab, under Administration.", ""),
        ("Scheduled tasks: change when they run", "later", "Not in Starboard yet. Use Jellyfin's Dashboard, Scheduled Tasks.", "/web/#/dashboard/tasks"),
        ("Activity and server logs", "starboard", "On this tab, under Administration.", ""),
        ("Video conversion: test which kind works", "starboard", "System, Overview has the test.", ""),
        ("Video conversion: change the settings", "later", "Not in Starboard yet. Use Jellyfin's Dashboard, Playback.", "/web/#/dashboard/playback/transcoding"),
        ("Remote access, ports and the network", "later", "Not in Starboard yet. Use Jellyfin's Dashboard, Networking.", "/web/#/dashboard/networking"),
        ("Jellyfin's own plug-ins and their updates", "starboard", "Settings, Apps, Jellyfin, Recommended plug-ins, and Ready to update.", ""),
        ("Devices, sessions and API keys", "later", "Not in Starboard yet. Use Jellyfin's Dashboard, Devices and API Keys.", "/web/#/dashboard/devices"),
        ("Server name, language and branding", "later", "Not in Starboard yet. Use Jellyfin's Dashboard, General.", "/web/#/dashboard/settings"),
        ("Update the server", "starboard", "Ready to update changes its container and waits while anyone is watching.", ""),
        ("Restart", "starboard", "System, Restart where needed.", ""),
        ("Backup of the server's own database", "no", "Jellyfin has no way to do it through its interface. Starboard's backups copy its settings folder.", ""),
    )

    def _headers(self, service):
        return {"Authorization": f'MediaBrowser Token="{service.get("api_key", "")}"', "Accept": "application/json", "User-Agent": services.USER_AGENT}

    def legacy_status(self, services_list):
        return services.jellyfin(services_list)

    def keys_needed(self):
        return [{"what": "API key", "where": "Dashboard, API keys", "kept": "Settings, Apps"}]


ADAPTERS = {Jellyfin.id: Jellyfin}
from .mediaservers import emby as _emby, plex as _plex  # noqa: E402 - the others, which need the classes above
ADAPTERS.update({_emby.Emby.id: _emby.Emby, _plex.Plex.id: _plex.Plex})


def active_id(data):
    """The id of the active media server from the settings (`extras.media_server`): "jellyfin" when it is not set, or
    "" for none. An id this Starboard does not have is treated as none, never as an error."""
    extras = (data or {}).get("extras") or {}
    chosen = extras.get("media_server") if isinstance(extras, dict) else None
    if chosen is None or chosen == "":
        return DEFAULT if chosen is None else ""
    return chosen if isinstance(chosen, str) and chosen in ADAPTERS else ""


def active(data):
    """The active adapter, or None when there is no media server."""
    cls = ADAPTERS.get(active_id(data))
    return cls() if cls else None


BACK_HOURS = 24  # the way back after a change: one step for this long (design, section 4)


def back_info(data, now=None):
    """The way back after a change, while it lasts: {"id", "name", "until"} (id "" is no media server), else None."""
    extras = (data or {}).get("extras") or {}
    raw = extras.get("media_server_back") if isinstance(extras, dict) else None
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not isinstance(raw.get("at"), (int, float)):
        return None
    until = raw["at"] + BACK_HOURS * 3600
    if (now if now is not None else time.time()) >= until or (raw["id"] and raw["id"] not in ADAPTERS) or raw["id"] == active_id(data):
        return None
    return {"id": raw["id"], "name": ADAPTERS[raw["id"]].name if raw["id"] else "", "until": until}


def state(data, added=None, now=None):
    """What GET /api/media-server answers, from the settings alone (nothing is asked of the server): the active
    one, whether it is set up, the ones this Starboard has, which of them are added as plug-ins (`added`, when the
    caller knows) and the way back while there is one."""
    one = active(data)
    saved = (data or {}).get("services") or []
    have = bool(one and one.find_service(saved))
    return {"active": one.id if one else "", "name": one.name if one else "", "configured": have,
            "capabilities": list(one.capabilities) if one else [], "page": one.page if one else "",
            # set_up: its address and key are saved; has_app: it is in Manage apps at all (with or without its key). A media
            # server that is set up and not the active one is "installed, not in use" (DASH-586).
            "available": [{"id": c.id, "name": c.name, "page": c.page, "capability_rows": c().capability_rows(), "set_up": bool(c().find_service(saved)),
                           "has_app": any(isinstance(x, dict) and x.get("type") == c.service_type and x.get("enabled", True) and x.get("url") for x in saved)}
                          for c in ADAPTERS.values()],
            "added": sorted(added if added is not None else ADAPTERS), "back": back_info(data, now)}


def status_for_pages(data):
    """The answer of GET /api/jellyfin: the active adapter's, as the pages have always had it. With no media server
    (or one this Starboard does not know) there is nothing configured."""
    one = active(data)
    if one is None:
        return {"configured": False}
    return one.legacy_status((data or {}).get("services") or [])


def in_use(data, pid):
    """True when the plug-in `pid` is the media server in use (the active one). A media server plug-in that is in use
    cannot be deactivated or removed: choose another one, or none, first (Settings, Apps, the media server tab)."""
    return bool(pid) and active_id(data) == pid


def check(data, wanted):
    """Asks the media server `wanted` whether it answers, and what it found, in words for people. Nothing is changed.
    Returns {ok, name, said, libraries}; never raises for a server that does not answer."""
    cls = ADAPTERS.get(wanted)
    if cls is None:
        raise LookupError("Starboard does not have that media server")
    one = cls()
    got = one.sign_in_check((data or {}).get("services") or [])
    if not got.get("ok"):
        return {"ok": False, "name": one.name, "said": got.get("why") or f"{one.name} did not answer", "libraries": []}
    try:
        libs = [x["name"] for x in one.libraries((data or {}).get("services") or []) if x.get("name")]
    except services.ServiceError:
        libs = []
    said = f"It answered{(' (version ' + got['version'] + ')') if got.get('version') else ''}. " + (
        f"It has {len(libs)} {'library' if len(libs) == 1 else 'libraries'}: {', '.join(libs[:8])}{' and more' if len(libs) > 8 else ''}." if libs
        else "It lists no libraries yet.")
    return {"ok": True, "name": got.get("name") or one.name, "said": said, "libraries": libs[:50]}


def choose(cfg, wanted, added, now=None):
    """Makes `wanted` the active media server ("" is none) and keeps the way back to the one before for 24 hours.
    A media server is asked first (check): if it does not answer, nothing changes. `added` lists the ids of media
    server plug-ins that are added and active. Never switches by itself. Raises LookupError for a server Starboard does
    not have and ValueError, in words, for one that is not added or does not answer. Returns {changed, said}."""
    if wanted and wanted not in ADAPTERS:
        raise LookupError("Starboard does not have that media server")
    before = active_id(cfg.data)
    if wanted == before:
        return {"changed": False, "said": f"{ADAPTERS[wanted].name if wanted else 'No media server'} is already in use"}
    if wanted:
        name = ADAPTERS[wanted].name
        if wanted not in added:
            raise ValueError(f"{name} is not added as a plug-in yet. Add it from the catalogue's Media servers first")
        got = check(cfg.data, wanted)
        if not got["ok"]:
            kept = ADAPTERS[before].name if before else "No media server"
            raise ValueError(f"{name} did not answer: {got['said']} Nothing changed: {kept} stays in use")
    _write(cfg, wanted, {"id": before, "at": now if now is not None else time.time()})
    if not wanted:
        return {"changed": True, "said": f"No media server is in use now. {ADAPTERS[before].name} stays added; you can go back to it for 24 hours"}
    return {"changed": True, "said": f"{ADAPTERS[wanted].name} answered and is now your media server" + (
        f". {ADAPTERS[before].name} stays added; you can go back to it for 24 hours" if before else "")}


def go_back(cfg, now=None):
    """The one step back, while it lasts. It does not ask the old server first (it was the one in use before), so a
    person is never stuck; the pages show whether it answers."""
    back = back_info(cfg.data, now)
    if not back:
        raise ValueError("There is nothing to go back to. The way back lasts 24 hours after a change")
    before = active_id(cfg.data)
    _write(cfg, back["id"], {"id": before, "at": now if now is not None else time.time()})
    return {"changed": True, "said": f"{back['name'] or 'No media server'} is your media server again" if back["id"]
            else "No media server is in use now"}


def _write(cfg, wanted, back):
    """One write for the choice and the way back, under the settings lock."""
    with cfg.lock:
        cfg.data["extras"]["media_server"] = wanted
        cfg.data["extras"]["media_server_back"] = back
        cfg.save()
    services.forget()  # the dashboard's panel and System ask the new one at once, not from a saved answer


def watching(data, app_id):
    """How many people are watching now on the media server whose app is `app_id`, or 0 when it is not the media server in use,
    does not answer or nobody is. Asked only when an update of that app is about to start (DASH-566), so nothing runs at rest."""
    one = active(data)
    saved = (data or {}).get("services") or []
    mine = next((x for x in saved if isinstance(x, dict) and x.get("id") == app_id and one and x.get("type") == one.service_type), None)
    if not one or not mine:
        return 0
    try:
        return len(one.playing(saved))
    except (services.ServiceError, OSError, ValueError):
        return 0


ADMIN_PARTS = {"libraries": "admin_libraries", "tasks": "admin_tasks", "activity": "admin_activity", "logs": "admin_logs"}


def admin_overview(data):
    """What the Administration part of the media server tab draws, from the settings alone (nothing is asked of the server): the
    server in use, which parts it offers, and for every job where it is done (admin_coverage)."""
    one = active(data)
    if one is None:
        return {"active": "", "name": "", "parts": [], "coverage": []}
    return {"active": one.id, "name": one.name, "parts": [p for p, c in ADMIN_PARTS.items() if c in one.capabilities], "coverage": one.admin_coverage()}


def admin_read(data, part, name=""):
    """One part of the administration, read from the media server in use only now, when a person asks. Raises LookupError (no
    media server, or no such part), ValueError (a name that is not allowed) and services.ServiceError (it did not answer)."""
    one = active(data)
    if one is None:
        raise LookupError("No media server is in use")
    saved = (data or {}).get("services") or []
    if part == "log":
        if "admin_logs" not in one.capabilities:
            raise LookupError(f"{one.name} does not give Starboard its logs")
        return {"name": name, "text": one.admin_log(saved, name)}
    if part not in ADMIN_PARTS or ADMIN_PARTS[part] not in one.capabilities:
        raise LookupError(f"{one.name} does not give Starboard that")
    return {"rows": getattr(one, "admin_" + part)(saved)}


def admin_do(data, what, target="", how="new"):
    """A change a person asked for: a scan of one library (or all, target ""), or running a scheduled task. Returns {said}."""
    one = active(data)
    if one is None:
        raise LookupError("No media server is in use")
    saved = (data or {}).get("services") or []
    if what == "scan" and "admin_libraries" in one.capabilities:
        one.admin_scan(saved, target, how)
        return {"said": f"{one.name} was asked to scan {'that library' if target else 'every library'}" + (" and refresh all its details" if how == "all" else "")}
    if what == "run" and "admin_tasks" in one.capabilities:
        if not target:
            raise ValueError("Choose a task")
        one.admin_run_task(saved, target)
        return {"said": f"{one.name} was asked to run the task"}
    raise LookupError(f"{one.name} does not give Starboard that")
