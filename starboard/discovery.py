"""Finding apps on this server, for Search for new apps (Settings, Apps, Manage apps, and the set-up wizard).

Only when asked. Starboard tries the usual port of each app it knows (and, with Docker access, every port a
container publishes), on this computer, and recognises each app by its page title or a small status address.
Apps already in Manage apps are left out. With Docker access, it can also read the API keys of Sonarr, Radarr,
Lidarr, Readarr, Prowlarr, SABnzbd and Seerr from their own settings files, so you do not have to copy them.
"""

import concurrent.futures as cf
import io
import json
import os
import re
import tarfile
import urllib.error
import urllib.parse
import urllib.request

from . import containers

# key: (name, Starboard's kind, usual ports, how to recognise it, needs an API key, background service)
# How to recognise: ("title", text) matches the page title; ("body", text) the first 64 KB; ("json", path, field)
# a JSON status address that has that field.
CATALOGUE = {
    "sonarr": ("Sonarr", "sonarr", [8989], ("title", "sonarr"), True, False),
    "radarr": ("Radarr", "radarr", [7878], ("title", "radarr"), True, False),
    "lidarr": ("Lidarr", "lidarr", [8686], ("title", "lidarr"), True, False),
    "readarr": ("Readarr", "readarr", [8787], ("title", "readarr"), True, False),
    "prowlarr": ("Prowlarr", "prowlarr", [9696], ("title", "prowlarr"), True, False),
    "bazarr": ("Bazarr", "bazarr", [6767], ("title", "bazarr"), True, False),
    "whisparr": ("Whisparr", "link", [6969], ("title", "whisparr"), False, False),
    "jellyfin": ("Jellyfin", "jellyfin", [8096], ("json", "/System/Info/Public", "ProductName"), True, False),
    "emby": ("Emby", "link", [8096, 8920], ("json", "/emby/System/Info/Public", "Version"), False, False),
    "plex": ("Plex", "link", [32400], ("body", "MediaContainer"), False, False),
    "seerr": ("Seerr", "seerr", [5055], ("json", "/api/v1/status", "commitTag"), True, False),
    "qbittorrent": ("qBittorrent", "qbittorrent", [8080, 8081], ("title", "qbittorrent"), True, False),
    "sabnzbd": ("SABnzbd", "sabnzbd", [8080, 8085, 8090], ("title", "sabnzbd"), True, False),
    "transmission": ("Transmission", "link", [9091], ("body", "transmission"), False, False),
    "deluge": ("Deluge", "link", [8112], ("title", "deluge"), False, False),
    "nzbget": ("NZBGet", "nzbget", [6789], ("title", "nzbget"), True, False),
    "gluetun": ("Gluetun (VPN)", "gluetun", [8000], ("json", "/v1/publicip/ip", "public_ip"), False, True),
    "flaresolverr": ("FlareSolverr", "link", [8191], ("body", "flaresolverr"), False, True),
    "slskd": ("Soulseek (slskd)", "slskd", [5030], ("title", "slskd"), False, True),  # DASH-94
    "tautulli": ("Tautulli", "link", [8181], ("title", "tautulli"), False, False),
    "audiobookshelf": ("Audiobookshelf", "audiobookshelf", [13378], ("json", "/status", "serverVersion"), False, False),
    "navidrome": ("Navidrome", "link", [4533], ("title", "navidrome"), False, False),
    "kavita": ("Kavita", "link", [5000], ("title", "kavita"), False, False),
    "komga": ("Komga", "link", [25600], ("title", "komga"), False, False),
    "calibre-web": ("Calibre-Web", "link", [8083], ("title", "calibre"), False, False),
    "immich": ("Immich", "link", [2283], ("title", "immich"), False, False),
    "storyarr": ("Storyarr", "link", [8000], ("title", "storyarr"), False, False),
    "wizarr": ("Wizarr", "link", [5690], ("body", "wizarr"), False, False),
    "jellystat": ("Jellystat", "link", [3000], ("title", "jellystat"), False, False),
    "profilarr": ("Profilarr", "link", [6868], ("title", "profilarr"), False, False),
    "kapowarr": ("Kapowarr", "link", [5656, 5757], ("title", "kapowarr"), False, False),
    "dispatcharr": ("Dispatcharr", "link", [9191], ("title", "dispatcharr"), False, False),
    "dozzle": ("Dozzle", "link", [9999, 8080], ("title", "dozzle"), False, False),
    "tdarr": ("Tdarr", "tdarr", [8265], ("title", "tdarr"), True, False),  # DASH-306: set up from Starboard, with a key it gives
    "uptime-kuma": ("Uptime Kuma", "link", [3001], ("title", "uptime kuma"), False, False),
    "portainer": ("Portainer", "link", [9000, 9443], ("title", "portainer"), False, False),
    "home-assistant": ("Home Assistant", "link", [8123], ("title", "home assistant"), False, False),
    "pi-hole": ("Pi-hole", "link", [80, 8053], ("title", "pi-hole"), False, False),
    "adguard": ("AdGuard Home", "link", [3000, 3080], ("title", "adguard"), False, False),
    "grafana": ("Grafana", "link", [3000], ("title", "grafana"), False, False),
    "syncthing": ("Syncthing", "link", [8384], ("title", "syncthing"), False, False),
    "nextcloud": ("Nextcloud", "link", [8443, 11000], ("title", "nextcloud"), False, False),
    "paperless": ("Paperless-ngx", "link", [8000], ("title", "paperless"), False, False),
    "vaultwarden": ("Vaultwarden", "link", [8222], ("title", "vaultwarden"), False, False),
    "homepage": ("Homepage", "link", [3000], ("body", "gethomepage"), False, False),
    "homarr": ("Homarr", "link", [7575], ("title", "homarr"), False, False),
}

# Where each app keeps its API key inside its container (read through Docker, only when asked).
KEY_FILES = {
    "sonarr": ("/config/config.xml", r"<ApiKey>([A-Za-z0-9]{20,64})</ApiKey>"),
    "radarr": ("/config/config.xml", r"<ApiKey>([A-Za-z0-9]{20,64})</ApiKey>"),
    "lidarr": ("/config/config.xml", r"<ApiKey>([A-Za-z0-9]{20,64})</ApiKey>"),
    "readarr": ("/config/config.xml", r"<ApiKey>([A-Za-z0-9]{20,64})</ApiKey>"),
    "prowlarr": ("/config/config.xml", r"<ApiKey>([A-Za-z0-9]{20,64})</ApiKey>"),
    "sabnzbd": ("/config/sabnzbd.ini", r"(?m)^api_key\s*=\s*([A-Za-z0-9]{16,64})\s*$"),
    "seerr": ("/app/config/settings.json", r'"apiKey"\s*:\s*"([A-Za-z0-9=+/]{20,120})"'),
    # Bazarr's own key, under auth: (its config also holds Sonarr's and Radarr's keys, under their own names).
    "bazarr": ("/config/config/config.yaml", r"(?m)^auth:[ \t]*\n(?:[ \t]+.*\n)*?[ \t]+apikey:[ \t]*['\"]?([A-Za-z0-9]{32})['\"]?[ \t]*$"),
}
# Apps whose key is not one line of a settings file: read by a function of their own (below), from the files the
# app keeps in its container. Each returns the key, or None.
KEY_DATABASES = {
    # Jellyfin: an API key it already has (Dashboard, API keys), from its database, newest first.
    "jellyfin": (("/config/data/jellyfin.db", "/config/jellyfin.db", "/data/data/jellyfin.db"),
                 "SELECT AccessToken FROM ApiKeys WHERE length(AccessToken) >= 32 ORDER BY DateCreated DESC LIMIT 1"),
    # Audiobookshelf: the root user's API token, which its API takes as a key.
    "audiobookshelf": (("/config/absdatabase.sqlite",),
                       "SELECT token FROM users WHERE type = 'root' AND token IS NOT NULL AND length(token) >= 20 LIMIT 1"),
}
READABLE = set(KEY_FILES) | set(KEY_DATABASES) | {"nzbget", "tdarr"}
# Container names an app may have besides its key: Seerr is still often named after Overseerr or Jellyseerr, which
# merged into it in 2026 (the same API, settings file and port).
OWN_NAMES = {"seerr": ("seerr", "jellyseerr", "overseerr")}

TIMEOUT = 2.5


def _get(url, limit=65536):
    req = urllib.request.Request(url, headers={"User-Agent": "Starboard"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # http://127.0.0.1 and a port Docker reported  # nosec B310
        return r.status, r.read(limit).decode("utf-8", "replace")


def _probe(port):
    """What answers on this port: the matching catalogue keys (usually one), or none."""
    base = f"http://127.0.0.1:{port}"
    try:
        _, page = _get(base + "/")
    except urllib.error.HTTPError as e:
        page = (e.read(65536) or b"").decode("utf-8", "replace")
        # An app that asks for a sign-in before any page (NZBGet: 401, Basic realm="NZBGet", no text) names itself
        # in the sign-in request: read that as its title.
        realm = re.search(r'realm="([^"]{1,60})"', e.headers.get("WWW-Authenticate", "") if e.headers else "")
        if realm and "<title>" not in page.lower():
            page = f"<title>{realm.group(1)}</title>" + page
    except Exception:  # anything that is not a web page (another protocol, a closed port): nothing here
        return []
    title = (re.search(r"<title>([^<]*)</title>", page, re.I) or [None, ""])[1].lower()
    body = page.lower()
    found = []
    for key, (name, kind, ports, rule, needs_key, background) in CATALOGUE.items():
        if port not in ports and rule[0] != "title":
            continue  # body and JSON checks only on the app's own ports, to keep guesses honest
        if rule[0] == "title" and rule[1] in title:
            found.append(key)
        elif rule[0] == "body" and rule[1] in body:
            found.append(key)
        elif rule[0] == "json":
            try:
                status, text = _get(base + rule[1], 20000)
                if status == 200 and rule[2] in json.loads(text):
                    found.append(key)
            except Exception:  # not that app
                pass
    return found[:1]


def _known_ports(services):
    used = set()
    for s in services:
        for field in ("url", "link"):
            parts = urllib.parse.urlsplit(s.get(field) or "")
            if parts.hostname in ("127.0.0.1", "localhost") and parts.port:
                used.add(parts.port)
    return used


def search(services):
    """Apps on this computer that are not in Manage apps yet."""
    ports = {p for (_, _, ps, _, _, _) in CATALOGUE.values() for p in ps}
    docker_names, all_names = {}, []
    if containers.available():
        try:
            for c in containers.docker("GET", "/containers/json"):
                all_names.append(c["Names"][0].lstrip("/"))
                for port in c.get("Ports") or []:
                    if port.get("PublicPort") and port.get("IP") in ("0.0.0.0", "::", "127.0.0.1", None):  # compares the address Docker reported, does not listen  # nosec B104
                        ports.add(port["PublicPort"])
                        docker_names.setdefault(port["PublicPort"], c["Names"][0].lstrip("/"))
        except containers.DockerError:
            pass
    have_ports = _known_ports(services)
    have_kinds = {s["type"] for s in services}
    have_names = {re.sub(r"[^a-z0-9]", "", s["name"].lower()) for s in services}
    with cf.ThreadPoolExecutor(8) as pool:
        results = dict(zip(sorted(ports), pool.map(_probe, sorted(ports))))
    out, seen = [], set()
    for port, keys in sorted(results.items()):
        for key in keys:
            if key in seen:
                continue
            seen.add(key)
            name, kind, _, _, needs_key, background = CATALOGUE[key]
            already = port in have_ports or re.sub(r"[^a-z0-9]", "", name.lower()) in have_names or \
                (kind != "link" and kind in have_kinds)
            # The app's own container: one named after it (an app behind a VPN publishes its port through the VPN's).
            own = next((n for n in all_names if re.sub(r"[^a-z0-9]", "", n.lower()) in OWN_NAMES.get(key, (key,))), "") or \
                docker_names.get(port, "")
            out.append({"key": key, "name": name, "type": kind, "url": f"http://127.0.0.1:{port}", "port": port,
                        "needs_key": needs_key, "background": background, "container": own,
                        "already": already, "can_read_key": key in READABLE and bool(own)})
    # "known": every app this can recognise, so a set-up waiting for new apps knows which of them to wait for.
    return {"items": out, "docker": containers.available(), "known": sorted(CATALOGUE)}


def _file(container_name, path, limit):
    """One file from inside a container, through Docker's archive call (read only). None when it cannot be read."""
    try:
        raw = containers.docker("GET", f"/containers/{container_name}/archive?path={urllib.parse.quote(path)}", raw=True, timeout=10)
    except containers.DockerError:
        return None
    try:
        with tarfile.open(fileobj=io.BytesIO(raw[:limit + 1_000_000])) as tar:
            member = next((m for m in tar.getmembers() if m.isfile()), None)
            return tar.extractfile(member).read(limit) if member else None
    except (tarfile.TarError, OSError):
        return None


def _copy_out(container_name, path, dest):
    """One file from a container to `dest` on disk, through Docker's archive call, a piece at a time (Starboard is
    light first: a database of hundreds of MB never sits in memory). True when it was copied."""
    import shutil
    tar_path = dest + ".tar"
    try:
        containers.docker_to_file(f"/containers/{container_name}/archive?path={urllib.parse.quote(path)}", tar_path)
        with tarfile.open(tar_path) as tar:
            member = next((m for m in tar.getmembers() if m.isfile()), None)
            if not member:
                return False
            with tar.extractfile(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out, 1024 * 1024)
        return True
    except (containers.DockerError, tarfile.TarError, OSError):
        return False
    finally:
        try:
            os.remove(tar_path)
        except OSError:
            pass


def _from_database(container_name, paths, query):
    """A value from an app's SQLite database, copied out to a temporary folder first (with its write-ahead log) and
    opened there, so the app's own file is never touched."""
    import sqlite3
    import tempfile
    for path in paths:
        with tempfile.TemporaryDirectory() as d:
            copy = os.path.join(d, "app.db")
            if not _copy_out(container_name, path, copy):
                continue
            _copy_out(container_name, path + "-wal", copy + "-wal")
            try:
                db = sqlite3.connect(copy)
                try:
                    row = db.execute(query).fetchone()
                finally:
                    db.close()
            except sqlite3.Error:
                continue
            if row and row[0]:
                return str(row[0])
    return None


def _nzbget(container_name):
    """NZBGet signs in with its control user name and password, which Starboard keeps as user:password."""
    text = (_file(container_name, "/config/nzbget.conf", 1_000_000) or b"").decode("utf-8", "replace")
    user = re.search(r"(?m)^ControlUsername=(\S+)\s*$", text)
    word = re.search(r"(?m)^ControlPassword=(\S+)\s*$", text)
    return f"{user.group(1)}:{word.group(1)}" if user and word else None


TDARR_CONFIG = "/app/configs/Tdarr_Server_Config.json"


def _tdarr(container_name):
    """Tdarr's API key, which Starboard gives it (DASH-306, owner, 10 November 2026: "not need to be logged into"):
    Tdarr takes a key in its own settings (seededApiKey, starting tapi_) and accepts it from its next start, whether
    or not its sign-in is on. When there is none yet, Starboard writes one and restarts Tdarr once."""
    import secrets
    raw = _file(container_name, TDARR_CONFIG, 200_000)
    if not raw:
        return None
    try:
        conf = json.loads(raw.decode("utf-8"))
    except ValueError:
        return None
    key = str(conf.get("seededApiKey") or "")
    if re.match(r"^tapi_[A-Za-z0-9_]{9,64}$", key):
        return key
    key = "tapi_" + secrets.token_hex(16)
    conf["seededApiKey"] = key
    try:
        containers.put_file(container_name, TDARR_CONFIG, json.dumps(conf, indent=2).encode())
        containers.docker("POST", f"/containers/{container_name}/restart?t=30", timeout=90)
    except containers.DockerError:
        return None
    return key


def read_key(key, container_name):
    """An app's API key from its own files, through Docker. None when it cannot be read."""
    if key not in READABLE or not containers.available() or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$", container_name or ""):
        return None
    if key == "nzbget":
        return _nzbget(container_name)
    if key == "tdarr":
        return _tdarr(container_name)
    if key in KEY_DATABASES:
        return _from_database(container_name, *KEY_DATABASES[key])
    path, pattern = KEY_FILES[key]
    text = (_file(container_name, path, 1_000_000) or b"").decode("utf-8", "replace")
    m = re.search(pattern, text)
    return m.group(1) if m else None


def helper_reader(stack_folder, wait=25.0):
    """A key reader that asks the set-up helper on the server (starter.sh), which can use Docker when Starboard cannot:
    one request for every key wanted, answered in keys-found.json. Returns reader(key, container) -> key or None."""
    import json as _json
    import time as _time
    asked = {}

    def reader(key, name):
        asked[f"{key}|{name}"] = {"key": key, "container": name}
        return None

    def ask():
        if not asked:
            return {}
        request = f"{_time.time():.3f}"
        done = os.path.join(stack_folder, "keys-found.json")
        try:
            os.remove(done)
        except OSError:
            pass
        with open(os.path.join(stack_folder, "keys-request.new"), "w", encoding="utf-8") as f:
            _json.dump({"request": request, "apps": list(asked.values())}, f)
        os.replace(os.path.join(stack_folder, "keys-request.new"), os.path.join(stack_folder, "keys-request"))
        until = _time.time() + wait
        while _time.time() < until:
            try:
                with open(done, encoding="utf-8") as f:
                    got = _json.load(f)
                if got.get("request") == request:
                    os.remove(done)  # the keys stay only in Starboard's settings
                    return {k: v for k, v in (got.get("keys") or {}).items() if isinstance(v, str) and v}
            except (OSError, ValueError):
                pass
            _time.sleep(0.5)
        return {}

    reader.ask = ask
    return reader


def read_missing_keys(cfg, reader=None):
    """The set-up's keys step (owner, 10 November 2026: nothing to type): for each app on the dashboard that needs a
    key and has none, its key read from its own files and saved. `reader(key, container)` reads one key (read_key, or
    the set-up helper's, which answers every key at once). Returns {"found": [names], "missing": [services]}."""
    reader = reader or read_key
    found, missing = [], []
    needs = {v[1]: k for k, v in CATALOGUE.items() if v[4] or k in KEY_DATABASES}  # service type -> catalogue key
    wanted = []
    for s in list(cfg.data["services"]):
        key = needs.get(s.get("type"))
        if key and not s.get("api_key"):
            wanted.append((s, key, s.get("container") or key))
            reader(key, s.get("container") or key)
    answers = reader.ask() if hasattr(reader, "ask") else None
    for s, key, name in wanted:
        value = answers.get(f"{key}|{name}") if answers is not None else reader(key, name)
        if value:
            cfg.upsert_service({**s, "api_key": value})
            found.append(s["name"])
        else:
            missing.append({"name": s["name"], "type": s["type"], "url": s.get("url", "")})
    return {"found": found, "missing": missing}
