"""Sets Reelix up over HTTP once Install apps has started it, so nobody has to open Reelix's own pages.

Reelix (GPL-3.0) and Starboard (MIT) stay separate: this module only calls Reelix's documented HTTP API, written for
Starboard from the API's behaviour (see ~/Documents/Claude/starboard/REELIX-API-RECIPE-2026-11-06.md); no Reelix code
is copied. What it does, in order:

1. The admin account, with the one-time set-up token the installer read from Reelix's log (data/stack/reelix-setup.json)
   and Starboard's own password, so one password opens both. The password is used for these calls and not kept.
2. A second Reelix user, "starboard", with manager rights only, and an API key for it. Starboard keeps that key,
   never an admin key: admin changes later ask for the password again.
3. Library folders for what was chosen (films, series, books, audiobooks, music), in the shared media folder.
4. qBittorrent as Reelix's download app, when it was installed: its temporary first password is replaced with one
   of its own, kept in Reelix, and it saves into /data/downloads/torrents in the shared media folder.
5. Reelix on Starboard's dashboard: Reelix answers on Radarr's, Sonarr's, Readarr's and Lidarr's addresses as well
   (/radarr/api/v3 and so on), so Starboard's own support for those shows its queue, calendar and wanted lists,
   with the manager key.

Every step can run again: what exists already is left as it is. 6 November 2026.
"""
import http.cookiejar
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

ADMIN = "admin"
MANAGER = "starboard"
# Reelix's folders for each kind, inside the shared media folder (Reelix sees it as /data), matching stack.DATA_FOLDERS.
FOLDERS = [
    ("movies", "/rootfolders", {"media_kind": "movie"}, "/data/media/movies"),
    ("tv", "/rootfolders", {"media_kind": "series"}, "/data/media/tv"),
    ("ebooks", "/bookrootfolders", {"kind": "ebook"}, "/data/media/books"),
    ("audiobooks", "/bookrootfolders", {"kind": "audiobook"}, "/data/media/audiobooks"),
    ("music", "/musicrootfolders", {"kind": "music"}, "/data/media/music"),
]
# Starboard's dashboard entries for Reelix: (service type, name, compatible address, the groups that need it).
COMPAT = [
    ("radarr", "Reelix films", "/radarr", {"movies"}),
    ("sonarr", "Reelix series", "/sonarr", {"tv"}),
    ("readarr", "Reelix books", "/readarr", {"ebooks", "audiobooks"}),
    ("lidarr", "Reelix music", "/lidarr", {"music"}),
]


class ReelixError(Exception):
    pass


class Session:
    """One signed-in conversation with Reelix: a cookie after sign-in, or an API key."""

    def __init__(self, base, key=None, opener=None):
        self.base = base.rstrip("/")
        self.key = key
        self.opener = opener or urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method, path, body=None, timeout=20, ok=(200, 201, 204)):
        headers = {"Accept": "application/json", "User-Agent": "Starboard"}
        if self.key:
            headers["X-Api-Key"] = self.key
        else:
            headers["x-reelix-request"] = "starboard"  # Reelix's check against cross-site requests, for cookie sign-in
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + "/api/v1" + path, data=data, method=method, headers=headers)
        try:
            with self.opener.open(req, timeout=timeout) as resp:  # Reelix's address comes from the installer's file  # nosec B310
                status, raw = resp.status, resp.read(2_000_000)
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read(20000)
        except (urllib.error.URLError, OSError) as e:
            raise ReelixError(f"Reelix did not answer at {self.base}: {getattr(e, 'reason', e)}") from e
        try:
            answer = json.loads(raw) if raw else None
        except ValueError:
            answer = None
        if status not in ok:
            message = (answer.get("message") or answer.get("error") or "") if isinstance(answer, dict) else ""
            raise ReelixError(f"Reelix said {status} to {method} {path}" + (f": {message}" if message else "")) from None
        return status, answer


def setup_file(data_dir):
    return os.path.join(data_dir, "stack", "reelix-setup.json")


def read_setup(data_dir):
    """What the installer left: {url, token, qbittorrent_password, groups}, or None."""
    try:
        with open(setup_file(data_dir), encoding="utf-8") as f:
            info = json.load(f)
        return info if isinstance(info, dict) and info.get("url") else None
    except (OSError, ValueError):
        return None


def wait_until_up(base, seconds=180, opener=None):
    began = time.time()
    while True:
        try:
            Session(base, opener=opener).call("GET", "/system/health", timeout=5)
            return
        except ReelixError:
            if time.time() - began > seconds:
                raise
            time.sleep(3)


def set_up(cfg, data_dir, password, log=lambda line: None, opener=None, qbit=None):
    """Runs every step; returns a list of what was done. Raises ReelixError when Reelix cannot be set up at all."""
    info = read_setup(data_dir)
    if not info:
        raise ReelixError("There is nothing to set up: Reelix was not installed by Install apps")
    base = info["url"]
    groups = set(info.get("groups") or [g for g, *_ in FOLDERS])
    done = []
    wait_until_up(base, opener=opener)

    # 1. The admin account, or signing in to it when an earlier run made it.
    admin = Session(base, opener=opener)
    _, status = admin.call("GET", "/setup")
    if (status or {}).get("needs_setup"):
        if not info.get("token"):
            raise ReelixError("Reelix needs its set-up token. Run ./install.sh --start-apps in the Starboard folder")
        admin.call("POST", "/setup", {"username": ADMIN, "password": password, "setup_token": info["token"]})
        done.append("Made the Reelix admin account (admin, with your Starboard password)")
    else:
        admin.call("POST", "/auth/login", {"username": ADMIN, "password": password, "remember_me": False})
    log("admin ready")

    # 2. The manager user and its key, unless Starboard has one already.
    key = next((s.get("api_key") for s in cfg.data["services"] if s.get("icon") == "reelix" and s.get("api_key")), None)
    if not key:
        _, roles = admin.call("GET", "/users/roles")
        role = next((r for r in (roles or []) if str(r.get("name", "")).lower() == "manager"), None)
        if not role:
            raise ReelixError("Reelix has no manager role to give Starboard")
        manager_password = secrets.token_urlsafe(24)
        _, users = admin.call("GET", "/users")
        taken = {u.get("username") for u in (users or [])}
        name = MANAGER if MANAGER not in taken else f"{MANAGER}-{secrets.token_hex(2)}"  # a fresh one; the old keeps its rights
        admin.call("POST", "/users", {"username": name, "password": manager_password, "permissions": role["permissions"],
                                      "display_name": "Starboard"})
        manager = Session(base, opener=opener)
        manager.call("POST", "/auth/login", {"username": name, "password": manager_password, "remember_me": False})
        _, made = manager.call("POST", "/auth/apikeys", {"name": "Starboard"})
        key = (made or {}).get("api_key") or (made or {}).get("key")
        if not key:
            raise ReelixError("Reelix did not give Starboard a key")
        done.append("Made a manager key for Starboard (not an admin key)")

    # 3. Library folders for what was chosen.
    for group, path, extra, folder in FOLDERS:
        if group not in groups:
            continue
        _, have = admin.call("GET", path)
        if any(str(f.get("path", "")).rstrip("/") == folder for f in (have or [])):
            continue
        admin.call("POST", path, {"path": folder, **extra})
        done.append(f"Added the library folder {folder}")

    # 4. qBittorrent, with a lasting password in place of its temporary one.
    if info.get("qbittorrent_password") and qbit:
        try:
            lasting = qbit(info["qbittorrent_password"])
            _, clients = admin.call("GET", "/downloadclients")
            if not any(c.get("implementation") == "qbittorrent" for c in (clients or [])):
                admin.call("POST", "/downloadclients", {
                    "implementation": "qbittorrent", "name": "qBittorrent", "enabled": True, "priority": 25, "tags": [],
                    "settings": {"host": info.get("qbittorrent_host", "qbittorrent"), "port": 8080, "use_ssl": False,
                                 "username": "admin", "password": lasting}})
                done.append("Connected Reelix to qBittorrent")
            _, profiles = admin.call("GET", "/delayprofiles")
            default = next((p for p in (profiles or []) if not p.get("tags")), None)
            if default and default.get("preferred_protocol") != "torrent" and not info.get("sabnzbd"):
                admin.call("PUT", f"/delayprofiles/{default['id']}", {**default, "preferred_protocol": "torrent"})
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"qBittorrent is not connected yet ({e}). Add it in Reelix, Settings, Download apps")

    # 5. Reelix on the dashboard, through its compatible addresses, with the manager key.
    host = base
    for kind, name, prefix, needs in COMPAT:
        if groups & needs:
            cfg.upsert_service({"name": name, "type": kind, "url": host + prefix, "api_key": key, "icon": "reelix",
                                "link": host, "description": "Reelix"})
    cfg.upsert_service({"name": "Reelix", "type": "link", "url": host, "icon": "reelix",
                        "description": "Films, series, books, music and radio"})
    done.append("Added Reelix to your apps")

    # The token has done its job: it no longer works once an account exists, so the file is no longer needed.
    try:
        os.remove(setup_file(data_dir))
    except OSError:
        pass
    return done


def qbit_lasting_password(base="http://127.0.0.1:8080", opener=None):
    """Signs in to qBittorrent with its temporary password and sets a lasting one; returns the lasting one."""
    def change(temporary):
        jar = opener or urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def post(path, form):
            req = urllib.request.Request(base + "/api/v2/" + path, data=urllib.parse.urlencode(form).encode(),
                                         headers={"Referer": base, "User-Agent": "Starboard"})
            with jar.open(req, timeout=15) as resp:  # qBittorrent on this computer, from the stack Starboard wrote  # nosec B310
                return resp.read(2000).decode(errors="replace")
        if "Ok" not in post("auth/login", {"username": "admin", "password": temporary}):
            raise ReelixError("qBittorrent did not accept its temporary password")
        lasting = secrets.token_urlsafe(18)
        # The save path inside the shared media folder, so a finished download moves into the library at once.
        post("app/setPreferences", {"json": json.dumps({"web_ui_password": lasting, "save_path": "/data/downloads/torrents"})})
        return lasting
    return change
