"""Moving Radarr, Sonarr, Lidarr, Readarr, Prowlarr and Seerr into Reelix (DASH-127, 128 and 129; 8 November 2026).

Reelix already knows how to do the move: its migrator reads each app over the app's own API and recreates its
library, profiles, indexers and requests (POST /api/v1/system/migrate/preview and /run, then GET /system/migrate to
follow a run). Starboard does not copy any of that (Reelix is GPL-3.0, Starboard MIT); it calls that API and fills in
what a person would otherwise have to type:

- each app's address and API key: the key from the app's own settings file (discovery.read_key), the address by
  the app's container name on its Docker network, which Reelix joins for the move and leaves afterwards;
- the keys the apps hide, so Reelix cannot read them over the API (DASH-128): Prowlarr's indexer keys, read from
  Prowlarr's own database. Anything still missing is listed for the person to type;
- path differences: where an app sees the media under another path than Reelix does, a path rewrite;
- qBittorrent (DASH-129): Reelix gets it by the name it has on Starboard's stack (gluetun when it runs through the
  VPN), with the password the person gives, checked against qBittorrent first.

The order is Reelix's own advice: Prowlarr first, Seerr last. Search for missing stays off. Download apps are not
moved: Starboard connects Reelix to its own qBittorrent and NZBGet. The moved indexers can be held (switched off) so
the old apps stay the only ones searching until the switch, then switched on with one call.
"""
import io
import json
import os
import re
import sqlite3
import tarfile
import tempfile
import threading
import time
import urllib.parse

from . import containers, discovery, reelix_setup, stack

# (source kind in Reelix, catalogue key for the key file, container names, the app's own port)
SOURCES = [
    ("prowlarr", "prowlarr", ("prowlarr",), 9696),
    ("radarr", "radarr", ("radarr",), 7878),
    ("sonarr", "sonarr", ("sonarr",), 8989),
    ("lidarr", "lidarr", ("lidarr",), 8686),
    ("readarr", "readarr", ("readarr", "bookshelf"), 8787),
    ("jellyseerr", "seerr", ("seerr", "jellyseerr", "overseerr"), 5055),
]
LABELS = {"prowlarr": "Prowlarr", "radarr": "Radarr", "sonarr": "Sonarr", "lidarr": "Lidarr", "readarr": "Readarr",
          "jellyseerr": "Seerr"}
# Everything except download apps, which Starboard connects itself.
CATEGORIES = ["tag", "root_folder", "quality_profile", "indexer", "remote_path_mapping", "movie", "series", "author",
              "artist", "user", "request"]
REELIX = "reelix"
RESULT = "reelix-move.json"


def _inspect(name):
    return containers.docker("GET", f"/containers/{urllib.parse.quote(name, safe='')}/json")


def path_rewrites(source_info, reelix_info):
    """Rewrites for where the source app sees media under another path than Reelix does: for each folder the app
    mounts, where Reelix sees that same folder on the computer."""
    reelix = [(m.get("Source", ""), m.get("Destination", "")) for m in reelix_info.get("Mounts") or [] if m.get("Type") == "bind"]
    out = []
    for m in source_info.get("Mounts") or []:
        src, dst = m.get("Source", ""), m.get("Destination", "")
        if m.get("Type") != "bind" or not src or dst in ("/config", "/app/config"):
            continue
        for rsrc, rdst in sorted(reelix, key=lambda r: -len(r[0])):
            if rsrc and (src == rsrc or src.startswith(rsrc.rstrip("/") + "/")):
                seen = rdst.rstrip("/") + src[len(rsrc.rstrip("/")):]
                if seen != dst:
                    out.append({"from": dst, "to": seen})
                break
    return out


def sources():
    """The apps found here to move, each with its address as Reelix reaches it, its key, the networks Reelix joins to
    reach it, and path rewrites. Raises ValueError when Reelix or Docker is not there."""
    if not containers.available():
        raise ValueError("Starboard needs Docker access to move your apps into Reelix")
    listing = containers.docker("GET", "/containers/json") or []
    names = {c["Names"][0].lstrip("/"): c for c in listing}
    if REELIX not in names:
        raise ValueError("Reelix is not running. Install it first, in Install apps")
    reelix_info = _inspect(REELIX)
    by_id = {c["Id"]: c for c in listing}
    out = []
    for kind, keyfile, candidates, port in SOURCES:
        name = next((n for n in candidates if n in names), None)
        if not name:
            continue
        info = _inspect(name)
        mode = ((info.get("HostConfig") or {}).get("NetworkMode") or "")
        owner = by_id.get(mode.split(":", 1)[1]) if mode.startswith("container:") else names[name]
        owner = owner or names[name]
        host = owner["Names"][0].lstrip("/")
        networks = [n for n in ((owner.get("NetworkSettings") or {}).get("Networks") or {}) if n not in ("host", "none")]
        key = discovery.read_key(keyfile, name)
        out.append({"source": kind, "app": LABELS[kind], "container": name, "url": f"http://{host}:{port}",
                    "api_key": key, "networks": networks, "path_rewrites": path_rewrites(info, reelix_info)})
    if not out:
        raise ValueError("Starboard found none of Radarr, Sonarr, Lidarr, Readarr, Prowlarr or Seerr running here")
    return out


def public(src):
    """A source without its key, for the page."""
    return {k: v for k, v in src.items() if k != "api_key"} | {"has_key": bool(src.get("api_key"))}


def join_networks(networks, docker=None):
    """Connects Reelix to each network (so it reaches the old apps by name); returns the ones it joined now."""
    docker = docker or containers.docker
    joined = []
    for net in dict.fromkeys(networks):
        try:
            docker("POST", f"/networks/{urllib.parse.quote(net, safe='')}/connect", {"Container": REELIX})
            joined.append(net)
        except containers.DockerError as e:
            if "already exists" not in str(e) and "already attached" not in str(e):
                raise
    return joined


def leave_networks(networks, docker=None):
    docker = docker or containers.docker
    for net in networks:
        try:
            docker("POST", f"/networks/{urllib.parse.quote(net, safe='')}/disconnect", {"Container": REELIX, "Force": True})
        except containers.DockerError:
            pass


# DASH-128: the keys the apps hide -----------------------------------------------------------------------------

def _read_files(container, paths, limit=containers.DOCKER_READ_LIMIT):
    """Files from a container through Docker, into a private temporary folder; returns {path: local path}."""
    folder = tempfile.mkdtemp(prefix="starboard-")
    out = {}
    for path in paths:
        try:
            raw = containers.docker("GET", f"/containers/{container}/archive?path={urllib.parse.quote(path)}", raw=True, timeout=60)
        except containers.DockerError:
            continue
        with tarfile.open(fileobj=io.BytesIO(raw[:limit])) as tar:
            member = next((m for m in tar.getmembers() if m.isfile()), None)
            if member:
                local = os.path.join(folder, os.path.basename(path))
                with open(local, "wb") as f:
                    f.write(tar.extractfile(member).read())
                out[path] = local
    return out, folder


def hidden_from_db(db_path, wanted):
    """Values for Reelix's missing secrets ("indexer:3:apiKey") from an *arr's own database file: the Settings of
    each row, in the Indexers or DownloadClients table."""
    tables = {"indexer": "Indexers", "download_client": "DownloadClients"}
    found = {}
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        for want in wanted:
            parts = want.split(":")
            if len(parts) != 3 or parts[0] not in tables or not parts[1].isdigit():
                continue
            row = con.execute(f"SELECT Settings FROM {tables[parts[0]]} WHERE Id = ?", (int(parts[1]),)).fetchone()  # nosec B608: table names from the fixed map above
            try:
                value = (json.loads(row[0]) if row else {}).get(parts[2])
            except ValueError:
                value = None
            if isinstance(value, str) and value and value != "********":
                found[want] = value
    finally:
        con.close()
    return found


def prowlarr_secrets(container, wanted):
    """Prowlarr's hidden indexer keys from its database (prowlarr.db with its write-ahead log); {} when unreadable."""
    if not wanted:
        return {}
    files, folder = _read_files(container, ["/config/prowlarr.db", "/config/prowlarr.db-wal"])
    try:
        db = files.get("/config/prowlarr.db")
        return hidden_from_db(db, wanted) if db else {}
    except sqlite3.Error:
        return {}
    finally:
        for f in os.listdir(folder):
            os.remove(os.path.join(folder, f))
        os.rmdir(folder)


def missing(plan):
    """The "<item key>:<field>" secrets a preview says are still needed."""
    return [f"{i['key']}:{field}" for i in plan.get("items") or [] for field in i.get("missing_secrets") or []]


# The move itself -----------------------------------------------------------------------------------------------

def _connection(src, typed=None):
    return {"source": src["source"], "url": src["url"], "api_key": src["api_key"] or "",
            "path_rewrites": src["path_rewrites"], "secrets": dict(src.get("secrets") or {}) | dict(typed or {})}


def counts(plan):
    out = {}
    for i in plan.get("items") or []:
        out.setdefault(i.get("category", "other"), {}).setdefault(i.get("action", "skip"), 0)
        out[i.get("category", "other")][i.get("action", "skip")] += 1
    return out


def preview(base, password, srcs, typed=None, opener=None, docker=None):
    """Reelix's preview for each app, with the hidden keys Starboard could find filled in. Nothing changes in Reelix."""
    admin = _admin(base, password, opener)
    joined = join_networks([n for s in srcs for n in s["networks"]], docker)
    out = []
    try:
        for src in srcs:
            if not src.get("api_key"):
                out.append({"source": src["source"], "app": src["app"], "error": f"Starboard could not read {src['app']}'s API key"})
                continue
            _, plan = admin.call("POST", "/system/migrate/preview", _connection(src, typed), timeout=180)
            need = missing(plan or {})
            if need and src["source"] == "prowlarr":
                src["secrets"] = prowlarr_secrets(src["container"], need)
                if src["secrets"]:
                    _, plan = admin.call("POST", "/system/migrate/preview", _connection(src, typed), timeout=180)
                    need = missing(plan or {})
            out.append({"source": src["source"], "app": src["app"], "version": (plan or {}).get("version"),
                        "counts": counts(plan or {}), "notes": (plan or {}).get("notes") or [],
                        "skipped": [{"name": i.get("name"), "category": i.get("category"), "why": i.get("detail")}
                                    for i in (plan or {}).get("items") or [] if i.get("action") == "skip"],
                        "still_missing": need, "filled": len(src.get("secrets") or {})})
    finally:
        leave_networks(joined, docker)
    return out


def _admin(base, password, opener=None):
    if not base or not re.match(r"^http://127\.0\.0\.1:\d{2,5}$", base):
        raise reelix_setup.ReelixError("Reelix was not installed by Install apps, so Starboard cannot reach it")
    admin = reelix_setup.Session(base, opener=opener)
    admin.call("POST", "/auth/login", {"username": reelix_setup.ADMIN, "password": password, "remember_me": False})
    return admin


def follow(admin, seconds=4 * 3600, wait=3.0, sleep=time.sleep):
    """Waits for Reelix's current run to finish; returns its last report."""
    began = time.time()
    while True:
        _, run = admin.call("GET", "/system/migrate", timeout=30)
        if not run or run.get("state") != "running":
            return run or {}
        if time.time() - began > seconds:
            raise reelix_setup.ReelixError("Reelix's move is taking longer than four hours. It carries on: see Reelix, System, Migrate")
        sleep(wait)


def run_all(base, password, srcs, typed=None, hold=True, opener=None, docker=None, sleep=time.sleep, log=lambda line: None):
    """Moves each app in order, one at a time, with search for missing off. With `hold`, the indexers Reelix has
    afterwards are switched off, so only the old apps search until the switch. Returns a report per app."""
    admin = _admin(base, password, opener)
    joined = join_networks([n for s in srcs for n in s["networks"]], docker)
    report = []
    try:
        for src in srcs:
            if not src.get("api_key"):
                report.append({"source": src["source"], "app": src["app"], "state": "failed", "error": "no API key"})
                continue
            if src["source"] == "prowlarr" and not src.get("secrets"):
                _, plan = admin.call("POST", "/system/migrate/preview", _connection(src, typed), timeout=180)
                src["secrets"] = prowlarr_secrets(src["container"], missing(plan or {}))
            log(f"Moving {src['app']}")
            admin.call("POST", "/system/migrate/run", {**_connection(src, typed), "categories": CATEGORIES, "search_missing": False},
                       timeout=60, ok=(200, 201, 202, 204))
            run = follow(admin, sleep=sleep)
            items = run.get("items") or []
            report.append({"source": src["source"], "app": src["app"], "state": run.get("state"), "error": run.get("error"),
                           "counts": counts({"items": items}),
                           "not_moved": [{"name": i.get("name"), "category": i.get("category"), "why": i.get("detail")}
                                         for i in items if i.get("action") in ("skip", "failed")]})
    finally:
        leave_networks(joined, docker)
    if hold:
        held = set_indexers(admin, False)
        report.append({"held": held})
    return report


def set_indexers(admin, on):
    """Switches every indexer in Reelix on or off; returns how many changed. Hidden keys come back masked and Reelix
    keeps the stored ones when they are sent back that way."""
    _, have = admin.call("GET", "/indexers")
    changed = 0
    for ix in have or []:
        if bool(ix.get("enabled")) == on:
            continue
        body = {f: ix.get(f) for f in ("implementation", "name", "priority", "tags", "settings")} | {"enabled": on}
        admin.call("PUT", f"/indexers/{ix['id']}", body)
        changed += 1
    return changed


# DASH-129: qBittorrent, by its name on Starboard's stack, with its password --------------------------------------

def conf_user(text):
    """The web user name in qBittorrent.conf: "Username=" in its [WebUI] section (qBittorrent 5), or
    "WebUI\\Username=" in [Preferences] (older versions). None when it is not set."""
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        key, _, value = line.partition("=")
        if (section == "WebUI" and key == "Username") or key == "WebUI\\Username":
            return value.strip()[:100] or None
    return None


def qbit_user(container="qbittorrent"):
    """qBittorrent's web user name, from its own settings file (WebUI\\Username), or "admin", its default. People
    change it (owner's server, 8 November 2026), and the sign-in fails with the right password and the wrong name."""
    files, folder = {}, None
    try:
        files, folder = _read_files(container, ["/config/qBittorrent/qBittorrent.conf"], limit=2_000_000)
        path = files.get("/config/qBittorrent/qBittorrent.conf")
        if path:
            with open(path, encoding="utf-8", errors="replace") as f:
                name = conf_user(f.read())
            if name:
                return name
    except (containers.DockerError, tarfile.TarError, OSError):
        pass
    finally:
        if folder:
            for f in os.listdir(folder):
                os.remove(os.path.join(folder, f))
            os.rmdir(folder)
    return "admin"


def qbit_check(password, base="http://127.0.0.1:8080", user="admin", opener=None):
    """Whether qBittorrent accepts this user name and password."""
    import http.cookiejar
    import urllib.request
    jar = opener or urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = urllib.request.Request(base + "/api/v2/auth/login", data=urllib.parse.urlencode({"username": user, "password": password}).encode(),
                                 headers={"Referer": base, "User-Agent": "Starboard"})
    try:
        with jar.open(req, timeout=15) as resp:  # qBittorrent on this computer  # nosec B310
            status, text = resp.status, resp.read(200).decode(errors="replace")
    except OSError:
        return False
    return status == 204 or (status == 200 and "Ok" in text)


def connect_qbittorrent(admin, host, password, user="admin"):
    """Reelix's qBittorrent download app at `host` (gluetun when it runs through the VPN) with this password: changed
    when Reelix has one, added when it has none."""
    _, clients = admin.call("GET", "/downloadclients")
    settings = {"host": host, "port": 8080, "use_ssl": False, "username": user, "password": password}
    have = next((c for c in clients or [] if c.get("implementation") == "qbittorrent"), None)
    if have:
        body = {f: have.get(f) for f in ("implementation", "name", "enabled", "priority", "tags")}
        body["settings"] = {**(have.get("settings") or {}), **settings}
        admin.call("PUT", f"/downloadclients/{have['id']}", body)
        return "Changed Reelix's qBittorrent to " + host
    admin.call("POST", "/downloadclients", {"implementation": "qbittorrent", "name": "qBittorrent", "enabled": True,
                                            "priority": 25, "tags": [], "settings": settings})
    return "Connected Reelix to qBittorrent at " + host


# Running it in the background, and the last result --------------------------------------------------------------

_lock = threading.Lock()
_job = {}


def job():
    with _lock:
        return dict(_job)


def save_result(data_dir, result):
    path = os.path.join(stack.folder(data_dir), RESULT)
    os.makedirs(stack.folder(data_dir), mode=0o700, exist_ok=True)
    with open(path + ".new", "w", encoding="utf-8") as f:
        json.dump(result, f)
    os.replace(path + ".new", path)


def last_result(data_dir):
    try:
        with open(os.path.join(stack.folder(data_dir), RESULT), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def moved(data_dir):
    """The apps a finished move took into Reelix (container names), for the takeover's check."""
    r = last_result(data_dir) or {}
    return [m["container"] for m in r.get("apps") or [] if m.get("state") == "finished"]


def start(data_dir, password, typed=None, hold=True, qbit_password=None, qbit_host=None, srcs=None, qbit_user_name="admin"):
    with _lock:
        if _job and not _job.get("finished"):
            raise ValueError("Reelix is already moving your apps")
        _job.clear()
        _job.update(started=time.time(), finished=False, ok=None, step="Starting")
    srcs = srcs if srcs is not None else sources()
    base = stack.reelix_url(data_dir)

    def go():
        result = {"started": time.time(), "apps": []}
        ok = False
        try:
            def log(line):
                with _lock:
                    _job["step"] = line
            report = run_all(base, password, srcs, typed=typed, hold=hold, log=log)
            names = {s["source"]: s["container"] for s in srcs}
            result["apps"] = [r | {"container": names.get(r.get("source"))} for r in report if "source" in r]
            result["held"] = next((r["held"] for r in report if "held" in r), 0)
            if qbit_password:
                result["qbittorrent"] = connect_qbittorrent(_admin(base, password), qbit_host or "gluetun", qbit_password,
                                                            user=qbit_user_name)
            ok = all(a.get("state") == "finished" for a in result["apps"])
        except (reelix_setup.ReelixError, containers.DockerError, OSError, ValueError) as e:
            result["error"] = str(e)
        result["finished"] = time.time()
        save_result(data_dir, result)
        with _lock:
            _job.update(finished=True, ok=ok, ended=time.time(), step="Finished" if ok else "Stopped")
    threading.Thread(target=go, name="reelix-move", daemon=True).start()
    return job()
