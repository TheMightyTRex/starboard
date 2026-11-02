"""Settings file: load, save, migrate and keep secrets out of what the browser sees."""

import json
import os
import re
import secrets
import shutil
import threading
import time

SCHEMA = 1

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
    "link": {"label": "Other app", "api": "", "searchable": False},
}

DESIGNS = ["health", "tiles", "shelf", "command", "board"]

UPCOMING_VIEWS = ("list", "calendar")
UPCOMING_DAYS = (7, 14, 30, 60, 90)

DEFAULTS = {
    "schema": SCHEMA,
    "site_name": "Starboard",
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
        for key, value in DEFAULTS.items():
            data.setdefault(key, json.loads(json.dumps(value)))
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
            if "design" in incoming:
                if incoming["design"] not in DESIGNS:
                    raise ConfigError("Choose one of the designs")
                d["design"] = incoming["design"]
            if "groups" in incoming:
                groups = [str(g).strip()[:40] for g in incoming["groups"] if str(g).strip()]
                d["groups"] = groups[:20] or DEFAULTS["groups"]
            for key in ("secure_cookies", "update_check", "network_access", "show_home_address", "show_outside_address",
                        "fetch_icons", "show_posters"):
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
            if "download_hours" in incoming:
                d["download_hours"] = clean_hours(incoming["download_hours"], d["download_hours"])
            if "session_days" in incoming:
                days = int(incoming["session_days"])
                if not 1 <= days <= 90:
                    raise ConfigError("Keep people signed in for 1 to 90 days")
                d["session_days"] = days
            self.save()


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
    clean["api_key"] = str(clean.get("api_key", "")).strip()[:200]
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
