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
   of its own, kept in Reelix, and it saves into /data/downloads/torrents in the shared media folder. Then searches
   through the VPN when Gluetun is installed, the sites to search chosen in the set-up, and Jellyfin and
   Audiobookshelf when Starboard has their keys (reelix_sites.py).
5. Reelix on Starboard's dashboard: Reelix answers on Radarr's, Sonarr's, Readarr's and Lidarr's addresses as well
   (/radarr/api/v3 and so on), so Starboard's own support for those shows its queue, calendar and wanted lists,
   with the manager key.

Every step can run again: what exists already is left as it is. 6 November 2026.
"""
import base64
import http.cookiejar
import json
import os
import re
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
    ("radio", "/radio/rootfolders", {"kind": "radio"}, "/data/media/radio"),
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


def _rewrite_setup(data_dir, info):
    path = setup_file(data_dir)
    try:
        tmp = path + ".new"
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            json.dump(info, f)
        os.replace(tmp, path)
    except OSError:
        pass


def wait_until_up(base, seconds=180, opener=None):
    """Waits until Reelix answers. "Unhealthy" (503) is an answer too: Reelix says so while a download app it was
    given cannot be reached, which is often what the caller is about to fix (owner's takeover, 8 November 2026)."""
    began = time.time()
    while True:
        try:
            Session(base, opener=opener).call("GET", "/system/health", timeout=5, ok=(200, 503))
            return
        except ReelixError:
            if time.time() - began > seconds:
                raise
            time.sleep(3)


_TOKEN = re.compile(r"setup[ _]token[:=] ?([A-Za-z0-9_-]{8,200})")  # the start-up banner, or a later warning line
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_QBIT = re.compile(r"temporary password is provided for this session: (\S{6,100})")


def _log_text(container, docker=None):
    """The last lines a container wrote, through Docker's API (its log stream has an 8-byte header per chunk)."""
    from . import containers
    raw = (docker or containers.docker)("GET", f"/containers/{container}/logs?stdout=1&stderr=1&tail=20000", raw=True, timeout=20)
    text, i = b"", 0
    while i + 8 <= len(raw):
        n = int.from_bytes(raw[i + 4:i + 8], "big")
        text += raw[i + 8:i + 8 + n]
        i += 8 + n
    return _ANSI.sub("", text.decode("utf-8", "replace"))


def tokens_from_docker(data_dir, info, docker=None, available=None):
    """Reelix's one-time set-up token, and qBittorrent's first password when Install apps installed qBittorrent, read
    from their logs when the installer has not put them in reelix-setup.json: a start from the browser does not run
    the installer (8 November 2026). Saves what it found and returns the updated info."""
    from . import containers, stack
    if info.get("token") or not (available or containers.available)():
        return info
    found = {}
    try:
        m = _TOKEN.findall(_log_text("reelix", docker))
        if m:
            found["token"] = m[-1]
        if "qbittorrent" in stack.chosen_keys(data_dir) and not info.get("qbittorrent_password") \
                and not stack.qbittorrent_password(data_dir):
            q = _QBIT.findall(_log_text("qbittorrent", docker))
            if q:
                found["qbittorrent_password"] = q[-1]
    except containers.DockerError:
        return info
    if found:
        info = {**info, **found}
        _rewrite_setup(data_dir, info)
    return info


def set_up(cfg, data_dir, password, log=lambda line: None, opener=None, qbit=None, nzbget=None):
    """Runs every step; returns a list of what was done. Raises ReelixError when Reelix cannot be set up at all."""
    info = read_setup(data_dir)
    if not info:
        raise ReelixError("There is nothing to set up: Reelix was not installed by Install apps")
    base = info["url"]
    groups = set(info.get("groups") or [g for g, *_ in FOLDERS])
    done = []
    wait_until_up(base, opener=opener)
    info = tokens_from_docker(data_dir, info)

    # 0. Jellyfin's and Audiobookshelf's first runs (DASH-179, DASH-180), before anything of Reelix's, so they are
    # never left for anyone on the network to claim when Reelix's own set-up stops: their admin (admin, with the
    # Starboard password), their libraries and a key for Starboard, so step 4f can connect them to Reelix.
    from . import app_setup
    found = {}
    done += app_setup.first_runs(cfg, data_dir, password, groups, log=log, opener=opener, found=found)

    # 1. The admin account, or signing in to it when an earlier run made it.
    admin = Session(base, opener=opener)
    _, status = admin.call("GET", "/setup")
    if (status or {}).get("needs_setup"):
        if not info.get("token"):
            raise ReelixError("Reelix needs its set-up token, and Starboard could not read it from Reelix's log. Restart Reelix, "
                                  "then select Finish setting up Reelix in Settings, Reelix, or run ./install.sh --start-apps")
        admin.call("POST", "/setup", {"username": ADMIN, "password": password, "setup_token": info["token"]})
        done.append("Made the Reelix admin account (admin, with your Starboard password)")
    else:
        admin.call("POST", "/auth/login", {"username": ADMIN, "password": password, "remember_me": False})
    log("admin ready")

    # 2. The manager user and its key, unless Starboard has one already.
    key = next((s.get("api_key") for s in cfg.data["services"] if s.get("icon") == "reelix" and s.get("api_key")), None)
    if not key:
        _, roles = admin.call("GET", "/users/roles")  # {"roles": [{"id": "manager", "name", "permissions"}], "permissions": [...]}
        presets = roles.get("roles", []) if isinstance(roles, dict) else (roles or [])
        role = next((r for r in presets if isinstance(r, dict) and "manager" in (str(r.get("id", "")).lower(), str(r.get("name", "")).lower())), None)
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
        key = (made or {}).get("key")  # the full key, shown once; "api_key" describes it
        if not isinstance(key, str):
            key = (made or {}).get("api_key") if isinstance((made or {}).get("api_key"), str) else None
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

    # 3b. Films and series information (the TMDB key, DASH-178) and the language of releases (DASH-189), before
    # Reelix searches or scans anything, so the first matches are right.
    from . import setup_answers, setup_left
    if info.get("tmdb"):
        try:
            _, meta = admin.call("GET", "/settings/metadata")
            admin.call("PUT", "/settings/metadata", setup_answers.tmdb_settings(info["tmdb"], meta))
            done.append("Added your TMDB key to Reelix")
            setup_left.record(data_dir, tmdb=True)
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"Your TMDB key is not in Reelix yet ({e}). Add it in Settings, Reelix")
    if "language" in info:
        try:
            done += setup_answers.apply_language(admin, info["language"])
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"The language of releases is not set yet ({e})")

    # 3b2. Picture quality (VM test F7): new films and series use the recommended level, HD-1080p, unless a level is
    # already chosen; otherwise Reelix takes its first, Anything.
    try:
        from . import reelix_quality
        done += reelix_quality.recommended_for_new(admin)
    except (ReelixError, OSError, ValueError) as e:
        done.append(f"Picture quality is not set yet ({e}). Choose it in Settings, Reelix")

    # 3c. Naming (Season 6, not Season 06, DASH-188) and how hard Reelix works in the background, from how much the
    # server does (Light on a small server, DASH-200).
    from . import config as _config, reelix_library
    try:
        preset = (cfg.data.get("performance") or {}).get("preset") or _config.recommended_preset()
        done += reelix_library.set_up(admin, preset)
    except (ReelixError, OSError, ValueError) as e:
        done.append(f"Reelix's naming and background pace are not set yet ({e}). Change them in Settings, Reelix")

    # 3d. The full version: YouTube and Spotify downloads on, into the shared media folder (DASH-216).
    if info.get("edition") == "full":
        from . import reelix_direct
        try:
            done += reelix_direct.set_up(admin)
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"YouTube and Spotify are not switched on yet ({e}). Switch them on in Settings, Reelix")

    # 4. qBittorrent. Since DASH-232 its password is made up before its first start (data/stack/.env, written into
    # its settings file as a hash); an older install still swaps the temporary one from its log for a lasting one.
    from . import stack as _stack_q
    seeded = _stack_q.qbittorrent_password(data_dir) if "qbittorrent" in (_stack_q.chosen_keys(data_dir) or []) else None
    if seeded or (info.get("qbittorrent_password") and qbit):
        try:
            lasting = seeded or qbit(info["qbittorrent_password"])
            _, clients = admin.call("GET", "/downloadclients")
            if not any(c.get("implementation") == "qbittorrent" for c in (clients or [])):
                admin.call("POST", "/downloadclients", {
                    "implementation": "qbittorrent", "name": "qBittorrent", "enabled": True, "priority": 25, "tags": [],
                    "settings": {"host": info.get("qbittorrent_host", "qbittorrent"), "port": 8080, "use_ssl": False,
                                 "username": "admin", "password": lasting}})
                done.append("Connected Reelix to qBittorrent")
            _, profiles = admin.call("GET", "/delayprofiles")
            default = next((p for p in (profiles or []) if not p.get("tags")), None)
            if default and default.get("preferred_protocol") != "torrent" and not info.get("usenet") and not info.get("sabnzbd"):
                admin.call("PUT", f"/delayprofiles/{default['id']}", {**default, "preferred_protocol": "torrent"})
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"qBittorrent is not connected yet ({e}). Add it in Starboard: Settings, Reelix, Download apps")

    # qBittorrent's temporary password has done its job, whatever happened: it leaves the file now.
    if info.pop("qbittorrent_password", None) is not None:
        _rewrite_setup(data_dir, info)

    # 4b. NZBGet, the default Usenet app: its downloads go in the shared media folder, and Reelix signs in with the
    # password Install apps made up (data/stack/.env).
    if info.get("usenet") == "nzbget" and nzbget:
        try:
            user, pw = nzbget(data_dir)
            _, clients = admin.call("GET", "/downloadclients")
            if not any(c.get("implementation") == "nzbget" for c in (clients or [])):
                admin.call("POST", "/downloadclients", {
                    "implementation": "nzbget", "name": "NZBGet", "enabled": True, "priority": 1, "tags": [],
                    "settings": {"host": info.get("usenet_host", "nzbget"), "port": 6789, "use_ssl": False,
                                 "username": user, "password": pw}})
                done.append("Connected Reelix to NZBGet")
            _, profiles = admin.call("GET", "/delayprofiles")
            default = next((p for p in (profiles or []) if not p.get("tags")), None)
            if default and default.get("preferred_protocol") != "usenet":
                admin.call("PUT", f"/delayprofiles/{default['id']}", {**default, "preferred_protocol": "usenet"})
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"NZBGet is not connected yet ({e}). Add it in Starboard: Settings, Reelix, Download apps")

    # 4c. SABnzbd, when chosen in place of NZBGet: on port 8085, with the API key Install apps made up (its first
    # settings file has the same key, data/stack/seed/sabnzbd/sabnzbd.ini).
    if info.get("usenet") == "sabnzbd":
        from . import stack
        key = stack.sabnzbd_key(data_dir)
        try:
            if not key:
                raise ReelixError("its API key is not in data/stack/.env")
            _, clients = admin.call("GET", "/downloadclients")
            if not any(c.get("implementation") == "sabnzbd" for c in (clients or [])):
                admin.call("POST", "/downloadclients", {
                    "implementation": "sabnzbd", "name": "SABnzbd", "enabled": True, "priority": 1, "tags": [],
                    "settings": {"host": info.get("usenet_host", "sabnzbd"), "port": stack.SABNZBD_PORT, "use_ssl": False,
                                 "api_key": key}})
                done.append("Connected Reelix to SABnzbd")
            _, profiles = admin.call("GET", "/delayprofiles")
            default = next((p for p in (profiles or []) if not p.get("tags")), None)
            if default and default.get("preferred_protocol") != "usenet":
                admin.call("PUT", f"/delayprofiles/{default['id']}", {**default, "preferred_protocol": "usenet"})
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"SABnzbd is not connected yet ({e}). Add it in Starboard: Settings, Reelix, Download apps")

    # 4c1. Soulseek through slskd (DASH-94): a download app and, with Reelix's add_indexer, a site to search, with the
    # API key Install apps made up. Finished files land in the shared media folder, so moves are instant.
    if info.get("slskd_host"):
        from . import stack
        key = stack.slskd_key(data_dir)
        try:
            if not key:
                raise ReelixError("its API key is not in data/stack/.env")
            _, clients = admin.call("GET", "/downloadclients")
            if not any(c.get("implementation") == "slskd" for c in (clients or [])):
                admin.call("POST", "/downloadclients", {
                    "implementation": "slskd", "name": "Soulseek", "enabled": True, "priority": 50, "tags": [],
                    "settings": {"host": info["slskd_host"], "port": 5030, "use_ssl": False, "api_key": key,
                                 "downloads_dir": "/data/downloads/soulseek", "fail_on_file_error": False, "add_indexer": True}})
                done.append("Connected Reelix to Soulseek, for downloads and searches")
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"Soulseek is not connected yet ({e}). Add it in Starboard: Settings, Reelix, Download apps")

    # 4c2. Your Usenet server into NZBGet or SABnzbd (DASH-183), as typed in the set-up.
    done += setup_answers.apply_usenet(data_dir, opener=opener)

    # 4d. Searches through the VPN (DASH-133), as Prowlarr's were when it ran inside Gluetun.
    from . import reelix_sites
    if info.get("vpn"):
        try:
            reelix_sites.set_vpn(admin, data_dir, True)
            done.append("Reelix searches through the VPN")
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"Reelix does not search through the VPN yet ({e}). Activate Search through the VPN in Settings, Reelix, Sites to search")

    # 4d1. Reelix's own updates: it may check, but never installs itself; Starboard updates the Reelix image on
    # Apps, Updates (DASH-187). Reelix's default is already off; this keeps it so.
    try:
        admin.call("PUT", "/system/updates/settings", {"automatic": True, "auto_install": False})
    except (ReelixError, OSError, ValueError):
        pass  # an older Reelix without the setting: nothing to switch off

    # 4d2. FlareSolverr, whenever it is installed (DASH-219).
    try:
        line = reelix_sites.connect_flaresolverr(admin, data_dir)
        if line:
            done.append(line)
    except (ReelixError, OSError, ValueError) as e:
        done.append(f"Reelix does not use FlareSolverr yet ({e})")

    # 4e. The sites to search chosen in the set-up (DASH-155): nothing unless chosen.
    try:
        done += reelix_sites.add_sites(admin, reelix_sites.clean_choice(info.get("sites")))
    except (ReelixError, OSError, ValueError) as e:
        done.append(f"The sites to search were not added ({e}). Add them in Settings, Reelix, Sites to search")

    # 4e2. Reelix's radio into Audiobookshelf's Radio library, made by the first run at step 0 (DASH-181).
    if "radio" in groups:
        try:
            lines = app_setup.radio_settings(admin, found)
            done += lines
            if lines:
                setup_left.record(data_dir, radio=True)
        except (ReelixError, OSError, ValueError) as e:
            done.append(f"Reelix's radio is not pointed at Audiobookshelf yet ({e})")

    # 4f. Jellyfin and Audiobookshelf (DASH-156), with the keys Starboard already has, so new files show at once.
    try:
        lines = reelix_sites.connect_media_servers(admin, cfg.data["services"], data_dir)
        done += lines
        _, have = admin.call("GET", "/mediaservers")
        if have:  # connected now, or before this run
            setup_left.record(data_dir, media_servers=True)
    except (ReelixError, OSError, ValueError) as e:
        done.append(f"Jellyfin and Audiobookshelf are not connected to Reelix yet ({e}). Connect them in Settings, Reelix, Media servers")

    # 4g. Bazarr to Reelix (DASH-182), with Bazarr's made-up key and the manager key.
    from . import stack as _stack
    bazarr = _stack.app_url(data_dir, "bazarr", 6767) if "bazarr" in (_stack.chosen_keys(data_dir) or []) else None
    if bazarr and _stack.bazarr_key(data_dir):
        try:
            done += app_setup.bazarr_connect(bazarr, _stack.bazarr_key(data_dir), key, opener=opener)
        except app_setup.AppSetupError as e:
            done.append(f"Bazarr is not connected to Reelix yet: {e}")

    # 5. Reelix on the dashboard, through its compatible addresses, with the manager key.
    host = base
    for kind, name, prefix, needs in COMPAT:
        if groups & needs:
            cfg.upsert_service({"name": name, "type": kind, "url": host + prefix, "api_key": key, "icon": "reelix",
                                "link": host, "description": "Reelix"})
    # The link entry keeps the manager key too: radio has no compatible address, so Coming up and Downloads read
    # Reelix's own radio pages with it (services.reelix_native).
    cfg.upsert_service({"name": "Reelix", "type": "link", "url": host, "icon": "reelix", "api_key": key,
                        "description": "Films, series, books, music and radio"})
    done.append("Added Reelix to your apps")

    # The token has done its job: it no longer works once an account exists, so the file is no longer needed.
    try:
        os.remove(setup_file(data_dir))
    except OSError:
        pass
    return done


def switch_usenet(base, password, to, host, creds=None, sab_key=None, opener=None):
    """After Settings, Your install swapped the Usenet app: Reelix's download apps get the new one and lose the other.
    `base` is Reelix's address from data/stack (stack.reelix_url), never a dashboard entry: the admin password goes
    there. `creds` (user, password) for NZBGet, `sab_key` for SABnzbd. Returns what was done."""
    if not base or not re.match(r"^http://127\.0\.0\.1:\d{2,5}$", base):
        raise ReelixError("Reelix was not installed by Install apps, so Starboard cannot reach it")
    admin = Session(base, opener=opener)
    admin.call("POST", "/auth/login", {"username": ADMIN, "password": password, "remember_me": False})
    _, clients = admin.call("GET", "/downloadclients")
    done = []
    other = "sabnzbd" if to == "nzbget" else "nzbget"
    for c in clients or []:
        if c.get("implementation") == other:
            admin.call("DELETE", f"/downloadclients/{c['id']}", ok=(200, 204))
            done.append(f"Took {c.get('name', other)} out of Reelix")
    if not any(c.get("implementation") == to for c in clients or []):
        if to == "nzbget" and creds:
            settings = {"host": host, "port": 6789, "use_ssl": False, "username": creds[0], "password": creds[1]}
        elif to == "sabnzbd" and sab_key:
            settings = {"host": host, "port": 8085, "use_ssl": False, "api_key": sab_key}
        else:
            return done + [f"Add {'NZBGet' if to == 'nzbget' else 'SABnzbd'} in Starboard: Settings, Reelix, Download apps"]
        admin.call("POST", "/downloadclients", {"implementation": to, "name": "NZBGet" if to == "nzbget" else "SABnzbd",
                                                "enabled": True, "priority": 1, "tags": [], "settings": settings})
        done.append(f"Connected Reelix to {'NZBGet' if to == 'nzbget' else 'SABnzbd'}")
    return done


def nzbget_rpc(key, base="http://127.0.0.1:6789", opener=None, wait=180, timeout=20):
    """A function calling NZBGet's JSON-RPC as `key` ("user:password"), waiting up to `wait` seconds (3 minutes
    while the apps start) for it to answer; a page asks once, with wait=0 and a short timeout."""
    token = base64.b64encode(key.encode()).decode()
    jar = opener or urllib.request.build_opener()

    def rpc(method, params=None):
        req = urllib.request.Request(base + "/jsonrpc", data=json.dumps({"method": method, "params": params or [], "id": 1}).encode(),
                                     headers={"Authorization": f"Basic {token}", "Content-Type": "application/json",
                                              "User-Agent": "Starboard"})
        with jar.open(req, timeout=timeout) as resp:  # NZBGet on this computer, from the stack Starboard wrote  # nosec B310
            return json.loads(resp.read(2_000_000)).get("result")

    began = time.time()
    while True:
        try:
            rpc("version")
            return rpc
        except (urllib.error.URLError, OSError, ValueError):
            if time.time() - began >= wait:
                raise ReelixError("NZBGet did not answer") from None
            time.sleep(3)


NZBGET_FOLDERS = {"MainDir": "/data/downloads/usenet", "DestDir": "/data/downloads/usenet/completed",
                  "InterDir": "/data/downloads/usenet/intermediate"}


def nzbget_options(options):
    """NZBGet's settings changed for Reelix, or None when nothing needs changing. linuxserver's image writes the
    finished and unfinished folders as fixed paths (/downloads/completed), so each is set, not only MainDir. Reelix
    sends films to "movies" and series to "tv": NZBGet's own "Series" category becomes "tv" (names are matched
    without regard to capitals, so "Movies" already works)."""
    values = {o["Name"]: o.get("Value", "") for o in options if isinstance(o, dict) and "Name" in o}
    want = dict(NZBGET_FOLDERS)
    names = {k: v for k, v in values.items() if k.startswith("Category") and k.endswith(".Name")}
    lower = {v.lower() for v in names.values()}
    if "tv" not in lower:
        series = next((k for k, v in names.items() if v.lower() == "series"), None)
        if series:
            want[series] = "tv"
        else:
            n = 1 + max([int(k[8:-5]) for k in names if k[8:-5].isdigit()] or [0])
            want[f"Category{n}.Name"] = "tv"
    if "movies" not in lower:
        n = 1 + max([int(k[8:-5]) for k in [*names, *[k for k in want if k.startswith("Category")]] if k[8:-5].isdigit()] or [0])
        want[f"Category{n}.Name"] = "movies"
    if all(values.get(k) == v for k, v in want.items()):
        return None
    merged = [{"Name": o["Name"], "Value": want.get(o["Name"], o.get("Value", ""))} for o in options if "Name" in o]
    merged += [{"Name": k, "Value": v} for k, v in want.items() if k not in values]
    return merged


def nzbget_ready(base="http://127.0.0.1:6789", opener=None):
    """Sets NZBGet's download folders inside the shared media folder, so a finished download moves into the library
    at once, and the categories Reelix uses; returns a function giving (user, password) from data/stack/.env."""
    def prepare(data_dir):
        from . import stack
        key = stack.nzbget_key(data_dir)
        if not key:
            raise ReelixError("NZBGet's sign-in is not in data/stack/.env")
        user, _, pw = key.partition(":")
        rpc = nzbget_rpc(key, base, opener)
        changed = nzbget_options(rpc("config") or [])
        if changed and rpc("saveconfig", [changed]):
            rpc("reload")
        return user, pw
    return prepare


def qbit_lasting_password(base="http://127.0.0.1:8080", opener=None):
    """Signs in to qBittorrent with its temporary password and sets a lasting one; returns the lasting one."""
    def change(temporary):
        jar = opener or urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def post(path, form):
            req = urllib.request.Request(base + "/api/v2/" + path, data=urllib.parse.urlencode(form).encode(),
                                         headers={"Referer": base, "User-Agent": "Starboard"})
            with jar.open(req, timeout=15) as resp:  # qBittorrent on this computer, from the stack Starboard wrote  # nosec B310
                return resp.status, resp.read(2000).decode(errors="replace")
        # qBittorrent 5.1 and later answer a right password with 204 and no text; earlier ones with 200 and "Ok."
        status, text = post("auth/login", {"username": "admin", "password": temporary})
        if not (status == 204 or (status == 200 and "Ok" in text)):
            raise ReelixError("qBittorrent did not accept its temporary password")
        lasting = secrets.token_urlsafe(18)
        # The save path inside the shared media folder, so a finished download moves into the library at once.
        post("app/setPreferences", {"json": json.dumps({"web_ui_password": lasting, "save_path": "/data/downloads/torrents"})})
        return lasting
    return change
