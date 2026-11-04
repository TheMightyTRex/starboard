"""Settings file: load, save, migrate and keep secrets out of what the browser sees."""

import json
import os
import re
import secrets
import shutil
import threading
import time

SCHEMA = 2

SERVICE_TYPES = {
    "sonarr": {"label": "Sonarr", "api": "/api/v3", "searchable": True, "kind": "Series"},
    "radarr": {"label": "Radarr", "api": "/api/v3", "searchable": True, "kind": "Film"},
    "lidarr": {"label": "Lidarr", "api": "/api/v1", "searchable": True, "kind": "Artist"},
    "readarr": {"label": "Readarr", "api": "/api/v1", "searchable": True, "kind": "Author"},
    "prowlarr": {"label": "Prowlarr", "api": "/api/v1", "searchable": False},
    "bazarr": {"label": "Bazarr", "api": "/api", "searchable": False},
    "jellyfin": {"label": "Jellyfin", "api": "", "searchable": False},
    "qbittorrent": {"label": "qBittorrent", "api": "/api/v2", "searchable": False},
    "sabnzbd": {"label": "SABnzbd", "api": "/sabnzbd/api", "searchable": False},
    "gluetun": {"label": "Gluetun (VPN)", "api": "", "searchable": False},
    "seerr": {"label": "Seerr, Jellyseerr or Overseerr", "api": "/api/v1", "searchable": False},
    "audiobookshelf": {"label": "Audiobookshelf", "api": "/api", "searchable": False},
    "link": {"label": "Other app", "api": "", "searchable": False},
}

SERVER_NAME_MAX = 10

DESIGNS = ["health", "tiles", "shelf", "command", "board"]

UPCOMING_VIEWS = ("list", "calendar")
UPCOMING_DAYS = (7, 14, 30, 60, 90)

DEFAULTS = {
    "schema": SCHEMA,
    "site_name": "Starboard",
    # The server's own name, up to 10 characters, at the start of the level 1 menu. Empty shows nothing.
    "server_name": "",
    "design": "health",
    "secure_cookies": False,
    "session_days": 7,
    "update_check": True,
    "network_access": None,
    "show_home_address": True,
    "show_outside_address": True,  # None: take STARBOARD_NETWORK on first run (on unless it is 0)
    "fetch_icons": True,  # app icons from the dashboard-icons collection on the internet
    "show_posters": True,  # posters on Coming up, which browsers load from the image sites the apps use
    "upcoming_view": "list",
    "upcoming_days": 14,
    # Download hours: qBittorrent and SABnzbd only download from start to end (whole hours, local time).
    "download_hours": {"enabled": False, "start": 1, "end": 6},
    # Watching in the background (watch.py): off until turned on, because it runs with no page open.
    "watch": {"enabled": False, "every": 5, "weekly": False,
              "channel": {"kind": "", "url": "", "token": ""},
              "alerts": {"apps_down": True, "disk_problem": True, "disk_full": 90, "download_stuck": True,
                         "backup_failed": True, "cert_days": 14}},
    # Hourly jobs (jobs.py): each off until turned on in Settings, Apps, Jellyfin or Settings, Apps, Audiobookshelf.
    "extras": {"livetv": False, "white_logos": True, "livetv_address": "", "import_keep": False, "defaults": False,
               "listening_keep": False},
    # How much Starboard does in the background and how often (Settings, Performance).
    "performance": {"preset": "balanced", "history": True, "history_every": 300, "schedule_every": 60,
                    "downloads_refresh": 15, "monitor_refresh": 2, "card_numbers": True,
                    "storage_refresh": 0, "usage_every": "ask", "space_log": True},
    # Starboard's own log (System, Logs): days to keep, and detailed logging for reporting a problem.
    "logs": {"keep_days": 60, "detail": "off", "detail_until": 0},
    "setup_guide_done": False,
    "ux_notes": False,  # Testing: the Note an issue button on every page (the shared library's ux-notes.js)
    "last_version": "",  # the version the upgrade wizard last finished, so it opens once per upgrade
    "auth": {"password_hash": "", "session_version": 1},
    "services": [],
    "groups": ["Watch, listen and request", "Find and organise", "Search and download", "Dashboards and tools"],
}

SERVICE_FIELDS = {
    "id", "name", "type", "url", "link", "outside_link", "icon", "api_key", "background", "follows", "group", "description", "enabled",
    "quality_profile_id", "metadata_profile_id", "root_folder", "search_on_add", "container",
}

# The category each well-known app goes in by default: the index of one of the four default groups.
CATEGORY_OF = {}
for _index, _names in enumerate([
    "jellyfin plex emby audiobookshelf seerr jellyseerr overseerr ombi wizarr jellystat tautulli navidrome kavita komga calibre-web immich",
    "sonarr radarr lidarr readarr storyarr dewarr bazarr kapowarr mylar whisparr tdarr",
    "prowlarr jackett qbittorrent transmission deluge sabnzbd nzbget profilarr flaresolverr slskd unpackerr autobrr",
]):
    for _name in _names.split():
        CATEGORY_OF[_name] = _index


def guess_group(service, groups):
    """The group to use when none is chosen: the app's usual category, found by name or else by its place in the list."""
    if not groups:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", str(service.get("name", "")).lower()).strip("-")
    index = CATEGORY_OF.get(slug, CATEGORY_OF.get(service.get("type", ""), 3))
    wanted = DEFAULTS["groups"][index]
    if wanted in groups:
        return wanted
    return groups[index] if index < len(groups) else groups[-1]  # renamed categories keep their place


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


class ConfigError(ValueError):
    pass


class Config:
    """Thread-safe settings stored as JSON in the data folder (never in the repository)."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.path = os.path.join(data_dir, "config.json")
        self.lock = threading.RLock()
        os.makedirs(data_dir, mode=0o700, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            data = json.loads(json.dumps(DEFAULTS))
            data["network_access"] = os.environ.get("STARBOARD_NETWORK", "1") != "0"
            name = os.environ.get("STARBOARD_NAME", "").strip()[:60]
            if name:
                data["site_name"] = name
            self._write(data)
            return data
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("schema", 0) < SCHEMA:
            self.backup("before-migration")
            data = migrate(data)
            self._write(data)
        if "server_name" not in data:  # added in 0.8: a short dashboard name becomes the server name
            name = str(data.get("site_name", "")).strip()
            data["server_name"] = name if name != "Starboard" and len(name) <= SERVER_NAME_MAX else ""
        for key, value in DEFAULTS.items():
            data.setdefault(key, json.loads(json.dumps(value)))
        for key, value in DEFAULTS["performance"].items():  # settings added in later versions
            data["performance"].setdefault(key, value)
        for key, value in DEFAULTS["logs"].items():
            data["logs"].setdefault(key, value)
        if data.get("design") not in DESIGNS:  # a design that has since been removed
            data["design"] = DEFAULTS["design"]
            self._write(data)
        if data["network_access"] is None:
            data["network_access"] = os.environ.get("STARBOARD_NETWORK", "1") != "0"
            self._write(data)
        return data

    def _write(self, data):
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)

    def save(self):
        with self.lock:
            self._write(self.data)

    def backup(self, reason):
        folder = os.path.join(self.data_dir, "backups")
        os.makedirs(folder, mode=0o700, exist_ok=True)
        if os.path.exists(self.path):
            name = f"config-{time.strftime('%Y-%m-%d-%H%M%S')}-{reason}.json"
            shutil.copy2(self.path, os.path.join(folder, name))
            os.chmod(os.path.join(folder, name), 0o600)

    # Services -----------------------------------------------------------

    def service(self, service_id):
        for s in self.data["services"]:
            if s["id"] == service_id:
                return s
        return None

    def upsert_service(self, incoming):
        with self.lock:
            clean = validate_service(incoming)
            if not clean["group"]:
                clean["group"] = guess_group(clean, self.data["groups"])
            current = self.service(clean["id"]) if incoming.get("id") else None
            if current:
                if not clean.get("api_key"):
                    # A saved key goes only to the server it was saved for: a new address needs the key again,
                    # so a stolen session cannot point an app elsewhere and collect its key.
                    if current.get("api_key") and not same_server(current.get("url", ""), clean.get("url", "")):
                        raise ConfigError("The address points to a different server, so enter the API key again")
                    clean["api_key"] = current.get("api_key", "")
                current.clear()
                current.update(clean)
            else:
                clean["id"] = self._new_id(clean["name"])
                self.data["services"].append(clean)
            self.save()
            return clean["id"]

    def remove_service(self, service_id):
        with self.lock:
            before = len(self.data["services"])
            self.data["services"] = [s for s in self.data["services"] if s["id"] != service_id]
            self.save()
            return len(self.data["services"]) < before

    def reorder_services(self, ids):
        with self.lock:
            by_id = {s["id"]: s for s in self.data["services"]}
            ordered = [by_id.pop(i) for i in ids if i in by_id]
            self.data["services"] = ordered + list(by_id.values())
            self.save()

    def _new_id(self, name):
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "app"
        taken = {s["id"] for s in self.data["services"]}
        candidate, n = base, 2
        while candidate in taken:
            candidate, n = f"{base}-{n}", n + 1
        return candidate

    # What the browser may see -------------------------------------------

    def public(self):
        d = self.data
        return {
            "site_name": d["site_name"],
            "server_name": d["server_name"],
            "server_name_max": SERVER_NAME_MAX,
            "design": d["design"],
            "groups": d["groups"],
            "secure_cookies": d["secure_cookies"],
            "session_days": d["session_days"],
            "update_check": d["update_check"],
            "network_access": d["network_access"],
            "show_home_address": d["show_home_address"],
            "show_outside_address": d["show_outside_address"],
            "fetch_icons": d["fetch_icons"],
            "show_posters": d["show_posters"],
            "upcoming_view": d["upcoming_view"],
            "upcoming_days": d["upcoming_days"],
            "upcoming_days_choices": UPCOMING_DAYS,
            "download_hours": d["download_hours"],
            "watch": public_watch(d["watch"]),
            "extras": d["extras"],
            "performance": dict(d["performance"], preset=matching_preset(d)),
            "logs": d["logs"],
            "setup_guide_done": d["setup_guide_done"],
            "ux_notes": d["ux_notes"],
            "last_version": d["last_version"],  # what the settings really match
            "presets": {k: v["title"] for k, v in PRESETS.items()},
            "services": [public_service(s) for s in d["services"]],
            "types": {k: {"label": v["label"], "searchable": v["searchable"]} for k, v in SERVICE_TYPES.items()},
            "category_of": CATEGORY_OF,
            "default_groups": DEFAULTS["groups"],
        }

    def update_general(self, incoming):
        with self.lock:
            d = self.data
            if "site_name" in incoming:
                name = str(incoming["site_name"]).strip()[:60]
                if not name:
                    raise ConfigError("Enter a name for the dashboard")
                d["site_name"] = name
            if "server_name" in incoming:
                name = re.sub(r"\s+", " ", str(incoming["server_name"])).strip()
                if len(name) > SERVER_NAME_MAX:
                    raise ConfigError(f"Use {SERVER_NAME_MAX} characters or fewer for the server name")
                d["server_name"] = name
            if "design" in incoming:
                if incoming["design"] not in DESIGNS:
                    raise ConfigError("Choose one of the designs")
                d["design"] = incoming["design"]
            if "groups" in incoming:
                groups = [str(g).strip()[:40] for g in incoming["groups"] if str(g).strip()]
                d["groups"] = groups[:20] or DEFAULTS["groups"]
            move = incoming.get("move_apps")
            if isinstance(move, dict) and move.get("from"):  # renaming or removing a category moves its apps in the same save
                old, new = str(move["from"]), str(move.get("to") or "").strip()[:40]
                if new not in d["groups"]:
                    raise ConfigError("Choose a category in the list for its apps")
                for s in d["services"]:
                    if s.get("group") == old:
                        s["group"] = new
            for key in ("secure_cookies", "update_check", "network_access", "show_home_address", "show_outside_address",
                        "fetch_icons", "show_posters", "setup_guide_done", "ux_notes"):
                if key in incoming:
                    d[key] = bool(incoming[key])
            if "upcoming_view" in incoming:
                if incoming["upcoming_view"] not in UPCOMING_VIEWS:
                    raise ConfigError("Choose List or Calendar")
                d["upcoming_view"] = incoming["upcoming_view"]
            if "upcoming_days" in incoming:
                days = int(incoming["upcoming_days"])
                if days not in UPCOMING_DAYS:
                    raise ConfigError("Choose 7, 14, 30, 60 or 90 days")
                d["upcoming_days"] = days
            if "last_version" in incoming:
                v = str(incoming["last_version"])[:20]
                if v and not re.match(r"^\d+\.\d+\.\d+$", v):
                    raise ConfigError("Not a version number")
                d["last_version"] = v
            if "preset" in incoming:
                apply_preset(d, incoming["preset"])
            if "performance" in incoming:
                d["performance"] = clean_performance(incoming["performance"], d["performance"])
            if "extras" in incoming:
                d["extras"] = clean_extras(incoming["extras"], d["extras"])
            if "watch" in incoming:
                d["watch"] = clean_watch(incoming["watch"], d["watch"])
            if "download_hours" in incoming:
                d["download_hours"] = clean_hours(incoming["download_hours"], d["download_hours"])
            if "preset" not in incoming:
                d["performance"]["preset"] = matching_preset(d)  # a change by hand is Custom, unless it matches one
            if "logs" in incoming:
                d["logs"] = clean_logs(incoming["logs"], d["logs"])
            if "session_days" in incoming:
                days = int(incoming["session_days"])
                if not 1 <= days <= 90:
                    raise ConfigError("Keep people signed in for 1 to 90 days")
                d["session_days"] = days
            self.save()


PERF_CHOICES = {"history_every": (60, 300, 900), "schedule_every": (60, 300), "downloads_refresh": (0, 10, 15, 30, 60),
                "monitor_refresh": (2, 5, 10), "storage_refresh": (0, 60, 300)}
USAGE_CHOICES = ("off", "ask", "open", "nightly", "weekly")

# Presets set every optional piece of background work at once. Features you choose for what they do (Live TV,
# download hours, the import itself) are left as they are; only how often and how much changes.
PRESETS = {
    "small": {"title": "Small server", "performance": {"history": False, "history_every": 900, "schedule_every": 300,
              "downloads_refresh": 30, "monitor_refresh": 5, "card_numbers": False,
              "storage_refresh": 0, "usage_every": "ask"},
              "watch": {"enabled": False}, "extras": {"white_logos": False, "import_keep": False, "defaults": False, "listening_keep": False},
              "show_posters": False},
    "balanced": {"title": "Balanced", "performance": {"history": True, "history_every": 300, "schedule_every": 60,
                 "downloads_refresh": 15, "monitor_refresh": 2, "card_numbers": True,
                 "storage_refresh": 0, "usage_every": "ask"},
                 "watch": {}, "extras": {"white_logos": True}, "show_posters": True},
    "everything": {"title": "Everything", "performance": {"history": True, "history_every": 60, "schedule_every": 60,
                   "downloads_refresh": 10, "monitor_refresh": 2, "card_numbers": True,
                   "storage_refresh": 60, "usage_every": "weekly"},
                   "watch": {"enabled": True, "every": 5, "weekly": True},
                   "extras": {"white_logos": True, "import_keep": True, "defaults": True, "listening_keep": True}, "show_posters": True},
}


def apply_preset(d, name):
    if name == "custom":
        d["performance"]["preset"] = "custom"
        return
    if name not in PRESETS:
        raise ConfigError("Choose Small server, Balanced, Everything or Custom")
    p = PRESETS[name]
    d["performance"].update(p["performance"])
    d["watch"].update(p["watch"])
    d["extras"].update(p["extras"])
    d["show_posters"] = p["show_posters"]
    d["performance"]["preset"] = name


def matching_preset(d):
    for name, p in PRESETS.items():
        if all(d["performance"].get(k) == v for k, v in p["performance"].items()) and \
                all(d["watch"].get(k) == v for k, v in p["watch"].items()) and \
                all(d["extras"].get(k) == v for k, v in p["extras"].items()) and d.get("show_posters") == p["show_posters"]:
            return name
    return "custom"


def clean_performance(incoming, current):
    if not isinstance(incoming, dict):
        raise ConfigError("Send the performance settings as an object")
    out = dict(current)
    for key in ("history", "card_numbers", "space_log"):
        if key in incoming:
            out[key] = bool(incoming[key])
    if "usage_every" in incoming:
        if incoming["usage_every"] not in USAGE_CHOICES:
            raise ConfigError("Choose when to work out what uses the space from the list")
        out["usage_every"] = incoming["usage_every"]
    for key, choices in PERF_CHOICES.items():
        if key in incoming:
            value = int(incoming[key])
            if value not in choices:
                raise ConfigError("Choose a value from the list")
            out[key] = value
    return out


def clean_logs(incoming, current):
    from .logs import DETAIL_CHOICES, KEEP_CHOICES
    if not isinstance(incoming, dict):
        raise ConfigError("Send the log settings as an object")
    out = dict(current)
    if "keep_days" in incoming:
        days = int(incoming["keep_days"])
        if days not in KEEP_CHOICES:
            raise ConfigError("Choose how long to keep logs from the list")
        out["keep_days"] = days
    if "detail" in incoming:
        if incoming["detail"] not in DETAIL_CHOICES:
            raise ConfigError("Choose Off, For 24 hours or Until I deactivate it")
        out["detail"] = incoming["detail"]
        out["detail_until"] = int(time.time()) + 86400 if out["detail"] == "day" else 0
    return out


def same_server(a, b):
    """True when two addresses reach the same server: the same scheme, host and port."""
    import urllib.parse
    pa, pb = urllib.parse.urlsplit(a or ""), urllib.parse.urlsplit(b or "")
    return (pa.scheme, pa.hostname, pa.port) == (pb.scheme, pb.hostname, pb.port)


def clean_extras(incoming, current):
    if not isinstance(incoming, dict):
        raise ConfigError("Send the Jellyfin job settings as an object")
    out = dict(current)
    for key in ("livetv", "white_logos", "import_keep", "defaults", "listening_keep"):
        if key in incoming:
            out[key] = bool(incoming[key])
    if "livetv_address" in incoming:
        url = str(incoming["livetv_address"] or "").strip().rstrip("/")[:200]
        if url and not re.match(r"^https?://[^\s/]+$", url):
            raise ConfigError("Enter the address as http://address:port, with nothing after the port")
        out["livetv_address"] = url
    return out


WATCH_EVERY = (1, 5, 10, 15, 30, 60)


def public_watch(w):
    out = json.loads(json.dumps(w))
    out["channel"]["has_token"] = bool(out["channel"].pop("token", ""))
    return out


def clean_watch(incoming, current):
    if not isinstance(incoming, dict):
        raise ConfigError("Send the alert settings as an object")
    out = json.loads(json.dumps(current))
    for key in ("enabled", "weekly"):
        if key in incoming:
            out[key] = bool(incoming[key])
    if "every" in incoming:
        every = int(incoming["every"])
        if every not in WATCH_EVERY:
            raise ConfigError("Choose how often to check from the list")
        out["every"] = every
    ch = incoming.get("channel")
    if isinstance(ch, dict):
        if "kind" in ch:
            if ch["kind"] not in ("", "ntfy", "gotify", "webhook"):
                raise ConfigError("Choose ntfy, Gotify or a webhook")
            out["channel"]["kind"] = ch["kind"]
        if "url" in ch:
            url = str(ch["url"]).strip()[:300]
            if url and not re.match(r"^https?://[^\s/]+(/\S*)?$", url):
                raise ConfigError("The alert address must start with http:// or https:// and have no spaces")
            if out["channel"].get("token") and not same_server(out["channel"].get("url", ""), url) and not ch.get("token"):
                out["channel"]["token"] = ""  # the saved token goes only to the server it was saved for
            out["channel"]["url"] = url
        if ch.get("token"):  # blank keeps the saved token
            out["channel"]["token"] = str(ch["token"]).strip()[:300]
        if ch.get("clear_token"):
            out["channel"]["token"] = ""
    alerts = incoming.get("alerts")
    if isinstance(alerts, dict):
        for key in ("apps_down", "disk_problem", "download_stuck", "backup_failed"):
            if key in alerts:
                out["alerts"][key] = bool(alerts[key])
        if "disk_full" in alerts:
            pct = int(alerts["disk_full"] or 0)
            if pct and not 50 <= pct <= 99:
                raise ConfigError("Choose a limit from 50% to 99%, or off")
            out["alerts"]["disk_full"] = pct
        if "cert_days" in alerts:
            days = int(alerts["cert_days"] or 0)
            if not 0 <= days <= 60:
                raise ConfigError("Choose from 0 to 60 days")
            out["alerts"]["cert_days"] = days
    return out


def clean_hours(incoming, current):
    if not isinstance(incoming, dict):
        raise ConfigError("Send the download hours as an object")
    out = dict(current)
    if "enabled" in incoming:
        out["enabled"] = bool(incoming["enabled"])
    for key in ("start", "end"):
        if key in incoming:
            hour = int(incoming[key])
            if not 0 <= hour <= 23:
                raise ConfigError("Choose an hour from 00:00 to 23:00")
            out[key] = hour
    if out["start"] == out["end"]:
        raise ConfigError("Choose a different time for the start and the end")
    return out


def public_service(s):
    out = {k: v for k, v in s.items() if k != "api_key"}
    out["has_api_key"] = bool(s.get("api_key"))
    out["link"] = s.get("link") or s.get("url", "")
    return out


def validate_service(s):
    if not isinstance(s, dict):
        raise ConfigError("Send the app as an object")
    clean = {k: s[k] for k in SERVICE_FIELDS if k in s}
    clean["name"] = str(clean.get("name", "")).strip()[:60]
    if not clean["name"]:
        raise ConfigError("Enter a name for the app")
    if clean.get("type") not in SERVICE_TYPES:
        raise ConfigError("Choose what kind of app this is")
    labels = {"url": "address the server uses", "link": "address to open in your browser", "outside_link": "outside address"}
    for key, label in labels.items():
        value = str(clean.get(key, "")).strip().rstrip("/")[:300]
        if value and not re.match(r"^https?://[^\s/]+$|^https?://[^\s/]+/\S*$", value):
            raise ConfigError(f"The {label} must start with http:// or https:// and have no spaces")
        clean[key] = value
    clean["background"] = bool(clean.get("background", False))
    follows = str(clean.get("follows") or "").strip()
    if follows and not _ID_RE.match(follows):
        raise ConfigError("Choose an app from the list for the status to follow")
    clean["follows"] = follows
    # A background service has no web page, so it may have no address: its status can follow another app.
    if not clean["url"] and not clean["background"]:
        raise ConfigError("Enter the address the server uses to reach the app")
    if "id" in clean and clean["id"] and not _ID_RE.match(str(clean["id"])):
        raise ConfigError("That app ID is not valid")
    clean["api_key"] = str(clean.get("api_key", "")).strip()[:2000]  # Audiobookshelf keys are over 200 characters
    clean["group"] = str(clean.get("group", "")).strip()[:40]
    icon = str(clean.get("icon", "")).strip()[:300]
    if icon and not (re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", icon.lower()) or re.match(r"^https://[^\s]+$", icon)):
        raise ConfigError("The icon must be a name such as sonarr, or an address starting with https://")
    clean["icon"] = icon
    clean["description"] = str(clean.get("description", "")).strip()[:200]
    container = str(clean.get("container", "")).strip()[:128]
    if container and not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", container):
        raise ConfigError("Choose a container from the list")
    clean["container"] = container
    clean["root_folder"] = str(clean.get("root_folder", "")).strip()[:300]
    clean["enabled"] = bool(clean.get("enabled", True))
    clean["search_on_add"] = bool(clean.get("search_on_add", True))
    for key in ("quality_profile_id", "metadata_profile_id"):
        value = clean.get(key)
        clean[key] = int(value) if str(value or "").isdigit() else None
    return clean


def migrate(data):
    """Bring an older settings file up to SCHEMA. Add a step for every schema change."""
    version = data.get("schema", 0)
    if version < 1:
        data.setdefault("auth", {"password_hash": "", "session_version": 1})
        data["schema"] = 1
    if version < 2:  # Audiobookshelf has its own type, for its API key and listening progress
        for s in data.get("services", []):
            if s.get("type") == "link" and re.sub(r"[^a-z]", "", str(s.get("name", "")).lower()) == "audiobookshelf":
                s["type"] = "audiobookshelf"
        data["schema"] = 2
    return data


def new_setup_token(data_dir):
    """A one-time code that must be entered to create the first password. Kept across restarts and updates, so the
    code the installer printed still works until a password is set."""
    path = os.path.join(data_dir, "setup-token")
    try:
        with open(path, encoding="utf-8") as f:
            existing = f.read().strip()
        if len(existing) >= 12:
            return existing
    except OSError:
        pass
    token = secrets.token_urlsafe(12)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token + "\n")
    return token
