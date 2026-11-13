"""Moving Radarr, Sonarr, Lidarr, Readarr, Prowlarr and Seerr into Reelix (DASH-127, 128 and 129; 8 November 2026).

Reelix already knows how to do the move: its migrator reads each app over the app's own API and recreates its
library, profiles, indexers and requests (POST /api/v1/system/migrate/preview and /run, then GET /system/migrate to
follow a run). Starboard does not copy any of that (Reelix is GPL-3.0, Starboard MIT); it calls that API and fills in
what a person would otherwise have to type:

- each app's address and API key: the key from the app's own settings file (discovery.read_key), the address by
  the app's container name on its Docker network, which Reelix joins for the move and leaves afterwards;
- the keys the apps hide, so Reelix cannot read them over the API (DASH-128): indexer keys, read from Prowlarr's own
  database, or Radarr's, Sonarr's, Lidarr's or Readarr's for sites added straight into them. Anything still missing
  is listed in the preview, by name, for the person to type; SABnzbd's key, for a SABnzbd that stays, comes from
  sabnzbd.ini once Starboard runs it (server.after_takeover);
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

from . import containers, discovery, reelix_setup, stack, tasklist

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


# Each app's own database, in its /config folder (Bookshelf, the Readarr fork, may name its own).
DATABASES = {"prowlarr": ("prowlarr.db",), "radarr": ("radarr.db",), "sonarr": ("sonarr.db",), "lidarr": ("lidarr.db",),
             "readarr": ("readarr.db", "bookshelf.db")}


def app_secrets(container, source, wanted):
    """An app's hidden keys from its own database (with its write-ahead log), read through Docker into a private
    temporary folder that is emptied straight after; {} when there is none or it cannot be read. Indexers added
    straight into Radarr, Sonarr, Lidarr or Readarr hide their keys as Prowlarr's do (DASH-128)."""
    if not wanted or source not in DATABASES:
        return {}
    for name in DATABASES[source]:
        files, folder = _read_files(container, [f"/config/{name}", f"/config/{name}-wal"])
        try:
            db = files.get(f"/config/{name}")
            if db:
                return hidden_from_db(db, wanted)
        except sqlite3.Error:
            return {}
        finally:
            for f in os.listdir(folder):
                os.remove(os.path.join(folder, f))
            os.rmdir(folder)
    return {}


def prowlarr_secrets(container, wanted):
    """Prowlarr's hidden indexer keys from its database (prowlarr.db with its write-ahead log); {} when unreadable."""
    return app_secrets(container, "prowlarr", wanted)


def hidden_secrets(src, wanted):
    """The hidden keys Starboard can read for this app."""
    if src["source"] == "prowlarr":
        return prowlarr_secrets(src["container"], wanted)
    return app_secrets(src["container"], src["source"], wanted)


def _moves(item):
    """Whether the move takes this item: download apps are left out (Starboard connects its own), so a key they hide
    is never asked for or counted (DASH-251)."""
    category = item.get("category") or str(item.get("key") or "").split(":", 1)[0]
    return category in CATEGORIES


def missing(plan):
    """The "<item key>:<field>" secrets a preview says are still needed, for what moves."""
    return [f"{i['key']}:{field}" for i in plan.get("items") or [] if _moves(i) for field in i.get("missing_secrets") or []]


def needs(plan, still):
    """The keys still to type, each with what it belongs to, for the page: [{id, name, category, field}]."""
    names = {i.get("key"): i for i in plan.get("items") or []}
    out = []
    for want in still:
        key, _, field = want.rpartition(":")
        item = names.get(key) or {}
        out.append({"id": want, "name": item.get("name") or key, "category": item.get("category") or key.split(":", 1)[0],
                    "field": field})
    return out


# The move itself -----------------------------------------------------------------------------------------------

# The hidden keys the last preview read from each app's database, so the move does not read them again. Held in
# memory only, never written or logged.
_found = {}

def typed_for(src, typed):
    """What the person typed for this app: `typed` is {source: {"indexer:3:apiKey": value}}, one set per app, as the
    same item key can be in two apps; a flat {"indexer:3:apiKey": value} (the terminal set-up) goes to every app."""
    typed = typed or {}
    mine = typed.get(src["source"])
    flat = {k: v for k, v in typed.items() if isinstance(v, str)}
    return flat | (dict(mine) if isinstance(mine, dict) else {})


def _connection(src, typed=None):
    return {"source": src["source"], "url": src["url"], "api_key": src["api_key"] or "",
            "path_rewrites": src["path_rewrites"], "secrets": dict(src.get("secrets") or {}) | typed_for(src, typed)}


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
            if need:
                src["secrets"] = hidden_secrets(src, need)
                _found[src["source"]] = dict(src["secrets"])
                if src["secrets"]:
                    _, plan = admin.call("POST", "/system/migrate/preview", _connection(src, typed), timeout=180)
                    need = missing(plan or {})
            out.append({"source": src["source"], "app": src["app"], "version": (plan or {}).get("version"),
                        "counts": counts(plan or {}), "notes": (plan or {}).get("notes") or [],
                        "skipped": [{"name": i.get("name"), "category": i.get("category"), "why": i.get("detail")}
                                    for i in (plan or {}).get("items") or [] if i.get("action") == "skip"],
                        "still_missing": need, "needs": needs(plan or {}, need), "filled": len(src.get("secrets") or {})})
    finally:
        leave_networks(joined, docker)
    return out


def _admin(base, password, opener=None):
    if not base or not re.match(r"^http://127\.0\.0\.1:\d{2,5}$", base):
        raise reelix_setup.ReelixError("Reelix was not installed by Install apps, so Starboard cannot reach it")
    admin = reelix_setup.Session(base, opener=opener)
    admin.call("POST", "/auth/login", {"username": reelix_setup.ADMIN, "password": password, "remember_me": False})
    return admin


def follow(admin, seconds=4 * 3600, wait=3.0, sleep=time.sleep, on_progress=None):
    """Waits for Reelix's current run to finish; returns its last report. `on_progress(run)` hears each look while it
    runs (done, total and current, for the dialog: DASH-252)."""
    began = time.time()
    while True:
        _, run = admin.call("GET", "/system/migrate", timeout=30)
        if not run or run.get("state") != "running":
            return run or {}
        if on_progress:
            on_progress(run)
        if time.time() - began > seconds:
            raise reelix_setup.ReelixError("Reelix's move is taking longer than four hours. It carries on: see Reelix, System, Migrate")
        sleep(wait)


def progress_words(app, run):
    """What a run is doing now, in words: "Radarr: 120 of 340, Harbour Street (2019)"."""
    done, total, current = run.get("done") or 0, run.get("total") or 0, run.get("current") or ""
    part = f"{done} of {total}" if total else "starting"
    return f"{app}: {part}" + (f", {current}" if current else "")


def not_moved(items):
    return [{"name": i.get("name"), "category": i.get("category"), "why": i.get("detail"), "key": i.get("key")}
            for i in items if i.get("action") in ("skip", "failed")]


def run_all(base, password, srcs, typed=None, hold=True, opener=None, docker=None, sleep=time.sleep, log=lambda line: None,
            tasks=None):
    """Moves each app in order, one at a time, with search for missing off. With `hold`, the indexers Reelix has
    afterwards are switched off, so only the old apps search until the switch. Returns a report per app. `tasks`
    (tasklist.Tasks) hears each app start, its progress and its result; when one stops the move, the rest are marked
    as not started, with why."""
    admin = _admin(base, password, opener)
    joined = join_networks([n for s in srcs for n in s["networks"]], docker)
    report = []
    current = None
    try:
        for src in srcs:
            current = src
            tid = f"app-{src['source']}"
            if not src.get("api_key"):
                report.append({"source": src["source"], "app": src["app"], "state": "failed", "error": "no API key"})
                if tasks:
                    tasks.fail(tid, f"Starboard could not read {src['app']}'s API key, so it was not moved")
                continue
            if tasks:
                tasks.start(tid, "Reading it", now=f"Moving {src['app']}")
            if not src.get("secrets") and _found.get(src["source"]):
                src["secrets"] = dict(_found[src["source"]])  # what the last preview read from its database
            if src["source"] == "prowlarr" and not src.get("secrets"):
                # Prowlarr's preview is only its sites, so it is quick to ask again; Radarr's or Sonarr's reads the
                # whole library, so theirs are read only when "Show what moves" asks (lightweight first).
                _, plan = admin.call("POST", "/system/migrate/preview", _connection(src, typed), timeout=180)
                src["secrets"] = prowlarr_secrets(src["container"], missing(plan or {}))
            log(f"Moving {src['app']}")
            admin.call("POST", "/system/migrate/run", {**_connection(src, typed), "categories": CATEGORIES, "search_missing": False},
                       timeout=60, ok=(200, 201, 202, 204))

            def heard(run, src=src, tid=tid):
                if tasks:
                    words = progress_words(src["app"], run)
                    tasks.note(tid, words, now=words)
            run = follow(admin, sleep=sleep, on_progress=heard)
            items = run.get("items") or []
            left = not_moved(items)
            report.append({"source": src["source"], "app": src["app"], "state": run.get("state"), "error": run.get("error"),
                           "counts": counts({"items": items}), "not_moved": left})
            if tasks:
                made = sum(1 for i in items if i.get("action") in ("create", "existing"))
                if run.get("state") == "finished":
                    tasks.done(tid, f"{made} moved" + (f", {len(left)} not moved" if left else ""))
                else:
                    tasks.fail(tid, run.get("error") or "Reelix stopped this move")
        current = None
    except Exception as e:
        if tasks:
            name = current["app"] if current else "Reelix"
            tasks.stop_rest(f"Not started, because the move stopped at {name}: {e}")
        raise
    finally:
        leave_networks(joined, docker)
    if hold:
        if tasks:
            tasks.start("hold", now="Holding the sites to search")
        held = []
        set_indexers(admin, False, changed_out=held)
        report.append({"held": len(held), "held_sites": held})
        if tasks:
            tasks.done("hold", f"{len(held)} held")
    return report


def set_indexers(admin, on, ids=None, changed_out=None):
    """Switches every indexer in Reelix on or off (or only those in `ids`); returns how many changed, and lists them
    ({id, name}) in `changed_out`. Hidden keys come back masked and Reelix keeps the stored ones when they are sent
    back that way."""
    _, have = admin.call("GET", "/indexers")
    changed = 0
    wanted = {int(i) for i in ids} if ids is not None else None
    for ix in have or []:
        if bool(ix.get("enabled")) == on or (wanted is not None and ix.get("id") not in wanted):
            continue
        body = {f: ix.get(f) for f in ("implementation", "name", "priority", "tags", "settings")} | {"enabled": on}
        admin.call("PUT", f"/indexers/{ix['id']}", body)
        changed += 1
        if changed_out is not None:
            changed_out.append({"id": ix["id"], "name": ix.get("name") or ""})
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


def conf_ban_minutes(text):
    """How long qBittorrent bans an address after failed sign-ins (WebUI\\BanDuration, in seconds; 3600 by default)."""
    for raw in text.splitlines():
        key, _, value = raw.strip().partition("=")
        if key in ("WebUI\\BanDuration", "BanDuration") and value.strip().isdigit():
            return max(1, int(value.strip()) // 60)
    return 60


def qbit_conf(container="qbittorrent"):
    """What qBittorrent's own settings file says (DASH-251): its web user name (None when Starboard could not read
    the file, or it sets none) and how many minutes a sign-in ban lasts."""
    out = {"user": None, "read": False, "ban_minutes": 60}
    files, folder = {}, None
    try:
        files, folder = _read_files(container, ["/config/qBittorrent/qBittorrent.conf"], limit=2_000_000)
        path = files.get("/config/qBittorrent/qBittorrent.conf")
        if path:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            out.update(user=conf_user(text), read=True, ban_minutes=conf_ban_minutes(text))
    except (containers.DockerError, tarfile.TarError, OSError):
        pass
    finally:
        if folder:
            for f in os.listdir(folder):
                os.remove(os.path.join(folder, f))
            os.rmdir(folder)
    return out


def qbit_user(container="qbittorrent"):
    """qBittorrent's web user name, from its own settings file (WebUI\\Username), or "admin", its default. People
    change it (owner's server, 8 November 2026), and the sign-in fails with the right password and the wrong name."""
    return qbit_conf(container)["user"] or "admin"


def qbit_sign_in(password, base="http://127.0.0.1:8080", user="admin", opener=None):
    """How qBittorrent answers this user name and password: "ok", "wrong", "banned" (it stopped accepting sign-ins
    from Starboard's address after too many wrong ones, DASH-251) or "unreachable"."""
    import http.cookiejar
    import urllib.error
    import urllib.request
    jar = opener or urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req = urllib.request.Request(base + "/api/v2/auth/login", data=urllib.parse.urlencode({"username": user, "password": password}).encode(),
                                 headers={"Referer": base, "User-Agent": "Starboard"})
    try:
        with jar.open(req, timeout=15) as resp:  # qBittorrent on this computer  # nosec B310
            status, text = resp.status, resp.read(200).decode(errors="replace")
    except urllib.error.HTTPError as e:
        text = e.read(300).decode(errors="replace") if e.fp else ""
        return "banned" if e.code == 403 or "banned" in text.lower() else "wrong"
    except OSError:
        return "unreachable"
    if "banned" in text.lower():
        return "banned"
    return "ok" if status == 204 or (status == 200 and "Ok" in text) else "wrong"


def qbit_check(password, base="http://127.0.0.1:8080", user="admin", opener=None):
    """Whether qBittorrent accepts this user name and password."""
    return qbit_sign_in(password, base, user, opener) == "ok"


def qbit_problem(state, user, ban_minutes=60):
    """The words for a sign-in that did not work, with what to do."""
    if state == "banned":
        return (f"qBittorrent has stopped accepting sign-ins from Starboard after too many wrong passwords. It lets "
                f"Starboard try again by itself after {ban_minutes} minutes, or restart qBittorrent to clear it now: on "
                "the server, run docker restart qbittorrent. Then try again with the right password, or leave it empty")
    if state == "unreachable":
        return ("Starboard could not reach qBittorrent to check the password. Leave it empty to connect qBittorrent "
                "later in Settings, Reelix, Download apps")
    return (f"qBittorrent did not accept that password for its user {user}. Check it, or leave it empty and add "
            "qBittorrent later in Settings, Reelix, Download apps")


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
_tasks = tasklist.Tasks()


def job():
    with _lock:
        return dict(_job) | (_tasks.public() if _job else {})


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


def source_ids(src, urls=(), opener=None):
    """The ids Radarr or Sonarr has for each film or series, by the key Reelix's report uses ("movie:12"), so a title
    the move could not match waits with its TMDB, TVDB and IMDb ids (DASH-253). Tried at the app's address on its
    network, then at `urls` (its address on the dashboard). {} when none answers."""
    import urllib.request
    path = {"radarr": "/api/v3/movie", "sonarr": "/api/v3/series"}.get(src["source"])
    if not path or not src.get("api_key"):
        return {}
    prefix = "movie" if src["source"] == "radarr" else "series"
    open_ = (opener or urllib.request.build_opener()).open
    for base in dict.fromkeys([src.get("url"), *urls]):
        if not base or not re.match(r"^https?://", base):
            continue
        req = urllib.request.Request(base.rstrip("/") + path, headers={"X-Api-Key": src["api_key"], "User-Agent": "Starboard"})
        try:
            with open_(req, timeout=30) as resp:  # the person's own Radarr or Sonarr  # nosec B310
                data = json.loads(resp.read(60_000_000))
        except (OSError, ValueError):
            continue
        return {f"{prefix}:{x['id']}": {"tmdb": x.get("tmdbId") or None, "tvdb": x.get("tvdbId") or None,
                                        "imdb": x.get("imdbId") or None}
                for x in data if isinstance(x, dict) and "id" in x} if isinstance(data, list) else {}
    return {}


def move_tasks(srcs, hold=True, qbit=False):
    """The steps of a move, in order, as the dialog lists them (DASH-252)."""
    items = [(f"app-{s['source']}", s["app"]) for s in srcs]
    if hold:
        items.append(("hold", "Hold the sites to search"))
    if qbit:
        items.append(("qbittorrent", "Connect Reelix to qBittorrent"))
    items.append(("waiting", "Keep the titles that did not match"))
    return items


def start(data_dir, password, typed=None, hold=True, qbit_password=None, qbit_host=None, srcs=None, qbit_user_name="admin",
          lookup_urls=None):
    """Moves the apps into Reelix in the background. `lookup_urls` ({"radarr": [address]}) are where Starboard can
    ask Radarr and Sonarr for the ids of titles that did not match."""
    global _tasks
    srcs = srcs if srcs is not None else sources()
    base = stack.reelix_url(data_dir)
    with _lock:
        if _job and not _job.get("finished"):
            raise ValueError("Reelix is already moving your apps")
        _job.clear()
        _job.update(started=time.time(), finished=False, ok=None, step="Starting")
        _tasks = tasklist.Tasks(move_tasks(srcs, hold, bool(qbit_password)))
    tasks = _tasks

    def go():
        from . import reelix_waiting
        result = {"started": time.time(), "apps": []}
        ok = False
        try:
            def log(line):
                with _lock:
                    _job["step"] = line
            report = run_all(base, password, srcs, typed=typed, hold=hold, log=log, tasks=tasks)
            names = {s["source"]: s["container"] for s in srcs}
            result["apps"] = [r | {"container": names.get(r.get("source"))} for r in report if "source" in r]
            result["held"] = next((r["held"] for r in report if "held" in r), 0)
            result["held_sites"] = next((r.get("held_sites") or [] for r in report if "held" in r), [])
            if qbit_password:
                tasks.start("qbittorrent", now="Connecting Reelix to qBittorrent")
                result["qbittorrent"] = connect_qbittorrent(_admin(base, password), qbit_host or "gluetun", qbit_password,
                                                            user=qbit_user_name)
                tasks.done("qbittorrent", result["qbittorrent"])
            tasks.start("waiting", now="Keeping the titles that did not match")
            held = []
            for s in srcs:
                a = next((r for r in result["apps"] if r.get("source") == s["source"]), None)
                left = [i for i in (a or {}).get("not_moved") or [] if reelix_waiting.is_unmatched(i)]
                if not left:
                    continue
                ids = source_ids(s, (lookup_urls or {}).get(s["source"]) or ())
                held += [reelix_waiting.entry(s["app"], i, ids.get(i.get("key") or "", {})) for i in left]
            result["waiting"] = reelix_waiting.hold(data_dir, held)
            tasks.done("waiting", f"{len(held)} waiting for a match" if held else "Every title matched")
            ok = all(a.get("state") == "finished" for a in result["apps"])
        except Exception as e:  # noqa: BLE001  whatever stopped it, the job finishes and says why
            result["error"] = str(e)
            tasks.stop_rest(f"Not started, because the move stopped: {e}")
        tasks.finish_all()
        result["finished"] = time.time()
        save_result(data_dir, result)
        with _lock:
            _job.update(finished=True, ok=ok, ended=time.time(), step="Finished" if ok else "Stopped",
                        error=result.get("error"))
    threading.Thread(target=go, name="reelix-move", daemon=True).start()
    return job()


def activate(data_dir, password, ids):
    """Activates held sites (DASH-190): those in `ids`, or every held one when `ids` is None; the result forgets them."""
    admin = _admin(stack.reelix_url(data_dir), password)
    result = last_result(data_dir) or {}
    held = result.get("held_sites") or []
    want = [h["id"] for h in held] if ids is None else [int(i) for i in ids]
    changed = []
    set_indexers(admin, True, ids=want, changed_out=changed)
    done = {h["id"] for h in changed} | set(want)
    result["held_sites"] = [h for h in held if h["id"] not in done]
    result["held"] = len(result["held_sites"])
    save_result(data_dir, result)
    return len(changed)
