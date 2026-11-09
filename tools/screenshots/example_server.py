#!/usr/bin/env python3
"""Starboard with made-up data only, for the README screenshots (tools/screenshots.sh starts it).

Nothing real is read: the folders, drives, apps found on this computer and container access are all
replaced with examples, and a fake Sonarr and Radarr answer on a second port. Data lives in a temporary
folder that is thrown away. Usage:  python3 tools/screenshots/example_server.py DATA_DIR [PORT]
It prints READY when signed-in screenshots can start, and writes a throwaway password to DATA_DIR/password.
"""
import datetime as dt
import json
import os
import pathlib
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
DATA = pathlib.Path(sys.argv[1])
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 18792
FAKE_PORT = PORT + 1
os.environ["STARBOARD_HISTORY"] = "0"
os.environ["STARBOARD_REPO"] = "TheMightyTRex/starboard"  # the public repository: release notes and Report a problem
os.environ["STARBOARD_DISKS"] = ("Media pool=/disks/pool,System disk=/data,Drive 1=/disks/each/1,Drive 2=/disks/each/2,"
                                 "Drive 3=/disks/each/3,Drive 4=/disks/each/4")
from starboard import changes, containers, discovery, stack, sysinfo  # noqa: E402
os.environ["EXAMPLE_REELIX_BASE"] = f"http://127.0.0.1:{FAKE_PORT}/reelix"
import example_library  # noqa: E402  (a made-up Reelix library: tools/screenshots/example_library.py)
from starboard.server import make_server  # noqa: E402
from tests.reelix_stand_in import StandIn  # noqa: E402

GB, TB = 1024 ** 3, 1024 ** 4
DISKS = {"Media pool": (24 * TB, 14.2 * TB), "System disk": (0.5 * TB, 0.12 * TB), "Drive 1": (8 * TB, 6.9 * TB),
         "Drive 2": (8 * TB, 4.1 * TB), "Drive 3": (4 * TB, 2.2 * TB), "Drive 4": (4 * TB, 1.0 * TB)}
_snapshot = sysinfo.snapshot


def example_snapshot(disk_paths):
    out = _snapshot([])
    out["disks"] = [{"label": label, "total": int(DISKS[label][0]), "used": int(DISKS[label][1]),
                     "free": int(DISKS[label][0] - DISKS[label][1]), "filesystem": "mergerfs" if label == "Media pool" else "ext4",
                     "path": path, "source": "/disks/each/1:/disks/each/2:/disks/each/3:/disks/each/4" if label == "Media pool" else "/dev/sdx1"}
                    for label, path in disk_paths]
    return out


sysinfo.snapshot = example_snapshot
containers.available = lambda: False
# EXAMPLE_CONTAINERS=1: a made-up Reelix container on 0.7.1 with 0.7.2 waiting, for What is new (journeys and
# screenshots). Docker itself is never called: every other request to it fails as if Docker were busy.
EXAMPLE_CONTAINERS = os.environ.get("EXAMPLE_CONTAINERS") == "1"
REELIX = {"id": "example-reelix", "name": "reelix", "image": "ghcr.io/themightytrex/reelix:lite", "image_id": "sha256:example",
          "state": "running", "status": "Up 2 hours", "version": "0.7.1", "created": dt.date.today().isoformat(),
          "digests": ["ghcr.io/themightytrex/reelix@sha256:example"], "service": "reelix", "project": "media",
          "folder": "", "files": ""}
EXAMPLE_CHANGELOG = """# Changelog

## [Unreleased]

## [0.7.2] - 2026-11-06

### Added
- **Shelves for radio:** stations and series on one page, with **Follow** on each.

### Fixed
- **Imports** of a folder with `&` in its name no longer stop half way.

## [0.7.1] - 2026-11-04

### Fixed
- **Large libraries:** the first scan lists every folder at once, then fills in matches in batches.

## [0.7.0] - 2026-11-03

### Added
- **An installer** for Windows, with a choice of just you or everyone on the computer.
"""
if EXAMPLE_CONTAINERS:
    def _no_docker(*a, **k):
        raise containers.DockerError("Example data: Docker is not used")
    containers.available = lambda: True
    containers.docker = _no_docker
    containers.containers = lambda light=False: [{"id": REELIX["id"], "name": REELIX["name"]}] if light else [dict(REELIX)]
    containers._check_one = lambda c: {"latest": "0.7.2", "update": True, "unknown": False, "big_change": False}
    changes._fetch = lambda url: changes.parse(EXAMPLE_CHANGELOG)
stack._port_free = lambda port: True
stack.reelix_url = lambda data_dir: f"http://127.0.0.1:{FAKE_PORT}/reelix"  # the made-up Reelix, for Settings, Reelix
discovery.search = lambda services: {"docker": False, "items": [
    {"key": k, "name": n, "type": k, "url": f"http://127.0.0.1:{p}", "port": p, "needs_key": True, "background": False,
     "container": "", "already": False, "can_read_key": False} for k, n, p in (("bazarr", "Bazarr", 6767), ("prowlarr", "Prowlarr", 9696))]}

KEY = "example-key"
today = dt.date.today()


# Reelix's admin settings (Settings, Reelix), with made-up sites and media servers. Any password is taken.
REELIX_ADMIN = StandIn(any_password=True)
for _name, _impl, _state in (("Internet Archive", "definition:internetarchive", 0), ("1337x", "definition:1337x", 0),
                             ("YTS", "definition:yts", 2), ("My Jackett", "torznab", 0)):
    _site = REELIX_ADMIN.add("indexers", _impl, _name, {"base_url": "https://example.invalid/"}, enabled=_name != "My Jackett")
    _site["status"]["failure_count"] = _state
    if _state:
        _site["status"]["last_failure_reason"] = "connection: the site took too long to answer"
REELIX_ADMIN.add("mediaservers", "jellyfin", "Jellyfin", {"url": "http://jellyfin:8096", "api_key": "made-up"})
REELIX_ADMIN.add("downloadclients", "qbittorrent", "qBittorrent", {"host": "gluetun", "port": 8080, "password": "made-up"})
REELIX_ADMIN.search.update(proxy={"kind": "http", "host": "gluetun", "port": 8888}, allow_private_addresses=True)


class FakeArr(BaseHTTPRequestHandler):
    def reelix_admin(self, method):
        """Reelix's admin routes, signed in with a cookie (never the manager key, which reads radio and the queue)."""
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}") if length else {}
        with REELIX_ADMIN.lock:
            status, answer, cookie = REELIX_ADMIN.handle(method, self.path.split("?")[0][len("/reelix/api/v1"):], body, dict(self.headers))
        raw = json.dumps(answer).encode() if answer is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        self.reelix_admin("POST")

    def do_PUT(self):
        self.reelix_admin("PUT")

    def do_DELETE(self):
        self.reelix_admin("DELETE")

    def log_message(self, *a):
        pass

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path
        if p.startswith("/abs"):  # a made-up Audiobookshelf, for Settings, Audiobookshelf
            if p == "/abs/status":
                return self.send_json({"app": "audiobookshelf", "serverVersion": "2.37.2"})
            if p.startswith("/abs/api/users"):
                return self.send_json({"users": [{"id": "u1", "username": "sam"}, {"id": "u2", "username": "alex"}, {"id": "u3", "username": "jo"}]})
            return self.send_json({"libraries": []})
        if p.startswith("/reelix/api/v1/") and not self.headers.get("X-Api-Key"):
            return self.reelix_admin("GET")
        if p.startswith("/reelix/posters/"):  # the made-up Library's posters: small pictures drawn by example_library
            body = example_library.png(int(p.rsplit("/", 1)[1].split(".")[0]))
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if p.startswith("/reelix/api/v1/"):  # a made-up Reelix: radio, read from its own API (Coming up, Downloads), and the Library
            path, _, query = p[len("/reelix/api/v1"):].partition("?")
            found = example_library.answer(path, dict(urllib.parse.parse_qsl(query)))
            return self.send_json(found if found is not None else example_reelix(path))
        film = "/films" in p
        if "/system/status" in p:
            return self.send_json({"version": "6.0.4" if film else "4.0.16"})
        if "/queue" in p:
            recs = [
                {"id": 1, "title": "Example.Show.S02E03.1080p", "size": 2e9, "sizeleft": 6e8, "status": "downloading", "trackedDownloadState": "downloading", "timeleft": "00:12:00"},
                {"id": 2, "title": "Another.Show.S01E07.720p", "size": 1e9, "sizeleft": 1e9, "status": "queued", "trackedDownloadState": "downloading"},
                {"id": 3, "title": "Old.Show.S05E01", "size": 3e9, "sizeleft": 0, "status": "completed", "trackedDownloadState": "importPending", "trackedDownloadStatus": "warning",
                 "statusMessages": [{"title": "Old.Show.S05E01", "messages": ["No files found are eligible for import"]}]},
            ]
            if film:
                recs = [{"id": 11, "title": "A.Film.2025.2160p", "size": 8e9, "sizeleft": 2e9, "status": "downloading", "trackedDownloadState": "downloading", "timeleft": "00:40:00"}]
            return self.send_json({"records": recs, "totalRecords": len(recs)})
        if "/calendar" in p:
            items = []
            for i in range(0, 40, 3):
                d = (today + dt.timedelta(days=i)).isoformat() + "T20:00:00Z"
                if film:
                    items.append({"title": f"Sample film {i + 1}", "year": 2026, "digitalRelease": d, "hasFile": i % 3 == 0, "images": [{"coverType": "poster", "remoteUrl": ""}], "overview": "A made-up film for the preview."})
                else:
                    items.append({"seriesId": 1, "title": f"Episode {i + 1}", "seasonNumber": 2, "episodeNumber": i + 1, "airDateUtc": d, "hasFile": i < 2,
                                  "series": {"title": "Example Show", "images": [{"coverType": "poster", "remoteUrl": ""}]}, "overview": "A made-up episode for the preview."})
            return self.send_json(items)
        if "/lookup" in p:
            return self.send_json([{"title": "Example result", "year": 2024, "tvdbId": 1, "tmdbId": 1, "overview": "A made-up search result.", "images": []}])
        # Settings for Copy app settings: the 4K copy is new, so it has only some of them.
        new = "/tv4k" in p
        if p.endswith("/tag"):
            return self.send_json([{"id": 1, "label": "kids"}] + ([] if new else [{"id": 2, "label": "anime"}]))
        if p.endswith("/customformat"):
            return self.send_json([] if new else [{"id": 1, "name": "x265", "specifications": []}, {"id": 2, "name": "Remux", "specifications": []}])
        if p.endswith("/downloadclient"):
            return self.send_json([] if new else [{"id": 1, "name": "qBittorrent", "implementationName": "qBittorrent", "fields": [{"name": "password", "label": "Password", "value": "********"}]},
                                                  {"id": 2, "name": "SABnzbd", "implementationName": "SABnzbd", "fields": [{"name": "apiKey", "label": "API Key", "value": "********"}]}])
        if p.endswith("/remotepathmapping"):
            return self.send_json([])
        if "/qualityprofile" in p:
            return self.send_json([{"id": 1, "name": "HD"}] + ([] if new else [{"id": 2, "name": "Ultra HD"}]))
        if "/rootfolder" in p:
            return self.send_json([{"path": "/media", "freeSpace": 10**12}])
        return self.send_json([], 200)



def _post(self):
    if not self.headers.get("X-Api-Key"):  # Reelix's admin routes, signed in with a cookie (Settings, Reelix)
        return self.reelix_admin("POST")
    length = int(self.headers.get("Content-Length") or 0)
    body = json.loads(self.rfile.read(length) or b"{}")
    found = example_library.add(self.path[len("/reelix/api/v1"):].split("?")[0], body) if self.path.startswith("/reelix/api/v1/") else None
    return self.send_json(found or {}, 201 if found else 404)


FakeArr.do_POST = _post


def example_reelix(path):
    """Reelix's own radio and queue answers, with made-up shows."""
    shows = [{"id": 1, "title": "The Example Hour"}, {"id": 2, "title": "Sample Science Weekly"}]
    if path == "/radio/shows":
        return {"items": shows, "total": len(shows), "page": 1, "page_size": 20}
    if path.startswith("/radio/shows/") and path.endswith("/episodes"):
        show = int(path.split("/")[3])
        eps = []
        for n, day in enumerate(range(-1, 30, 7 if show == 1 else 10)):
            when = (today + dt.timedelta(days=day)).isoformat() + ("T19:00:00Z" if show == 1 else "T07:30:00Z")
            eps.append({"id": show * 100 + n, "series_number": 4 if show == 1 else None, "number": n + 1,
                        "title": ["Tides", "Lighthouses", "Harbours", "Storms", "Islands"][n % 5] if show == 1 else f"Ask a scientist {n + 1}",
                        "first_broadcast": when, "monitored": True, "status": "in_library" if day < 0 else "not_released",
                        "synopsis": "A made-up episode for the preview."})
        return {"series": [], "episodes": eps}
    if path == "/queue":
        return {"items": [{"id": 31, "title": "The.Example.Hour.S04E02.mp3", "download_client": "NZBGet", "download_id": "ex31",
                           "state": "downloading", "client_state": "downloading", "progress": 0.35, "size": 60_000_000,
                           "remaining": 39_000_000, "eta_secs": 240, "messages": [], "added": today.isoformat() + "T09:00:00Z",
                           "media": {"kind": "radio_episode", "id": 101, "title": "Lighthouses", "subtitle": "The Example Hour"}}],
                "total": 1, "page": 1, "page_size": 0}
    return []


def call(method, path, body=None, cookie=None):
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    h = {"Content-Type": "application/json", "X-Starboard": "1", "Origin": f"http://127.0.0.1:{PORT}"}
    if cookie:
        h["Cookie"] = cookie
    conn.request(method, path, json.dumps(body) if body is not None else None, h)
    r = conn.getresponse()
    return r, r.read()


APPS = [
    ("Example TV", "sonarr", "Downloads", "tv"),
    ("Example music", "link", "Watch and listen", "music"),
    ("Example books", "link", "Watch and listen", "books"),
    ("Example films", "radarr", "Downloads", "films"),
    ("Example TV 4K", "sonarr", "Downloads", "tv4k"),
    ("Media player", "link", "Watch and listen", "player"),
    ("Audiobookshelf", "audiobookshelf", "Watch and listen", "abs"),
    ("Not running", "link", "Watch and listen", None),
]


def example_pool(data):
    """System, Storage, Pool with made-up drives: a pretend pool helper on a pretend computer under DATA/pool-root,
    answering Starboard's requests every half second. Nothing touches a real drive."""
    from starboard import pool_helper as ph
    root = data / "pool-root"
    gb = 1000 ** 3
    devices = [("sda", 250 * gb, "S2R5NX0H2E7A", "Samsung SSD 850 EVO", "/"), ("sdb", 4000 * gb, "WD-WCC7K1A7Q2K", "WDC WD40EFRX", None),
               ("sdc", 3000 * gb, "ZDH1A81F", "ST3000VN007", None), ("sdd", 2000 * gb, "Z4Z00C3D", "TOSHIBA HDWD120", None),
               ("sde", 4000 * gb, "WD-WX52D55B0", "WDC WD40EFZX", None), ("sdf", 4000 * gb, "WD-WX11D9KX1", "WDC WD40EFRX", None)]
    byid = root / "dev/disk/by-id"
    byid.mkdir(parents=True, exist_ok=True)
    (root / "etc").mkdir(exist_ok=True)
    (root / "etc/fstab").write_text("UUID=example-root / ext4 defaults 0 1\n")
    tree = []
    for name, size, serial, model, mount in devices:
        (root / "dev" / name).touch()
        link = byid / f"ata-{model.replace(' ', '_')}_{serial}"
        if not link.exists():
            link.symlink_to(f"../../{name}")
        parts = [{"name": name + "1", "type": "part", "size": size, "fstype": "ext4", "uuid": "example-root", "mountpoints": ["/"]}] if mount else None
        tree.append({"name": name, "type": "disk", "size": size, "serial": serial, "model": model, "tran": "sata", "rota": True,
                     "rm": False, "mountpoints": [None], "children": parts})
    exchange = data / "pool"
    (exchange / "requests").mkdir(parents=True, exist_ok=True)
    fill = {"/mnt/disks/disk1": 0.85, "/mnt/disks/disk2": 0.63, "/mnt/disks/disk3": 0.15, "/mnt/parity/parity1": 0.7}
    host = ph.Host(root=str(root), exchange=str(exchange), run=lambda cmd: "", lsblk=lambda: {"blockdevices": tree}, mounts={})
    sizes = {}

    def statvfs(path):
        size = sizes.get(path) or (4000 * gb if path.startswith("/mnt/disks/") else 0)
        if not size:
            return None
        used = int(size * fill.get(path, 0.0))
        return {"size": size, "used": used, "free": size - used}
    host.statvfs = statvfs
    ph.units = lambda branch, depth=3: {f"media/tv/Example series {branch[-1]}{n}": (int(90 * gb + n * 37 * gb), 0)
                                        for n in range(12)} if branch.endswith(("disk1", "disk2")) else {}
    for name, role in (("sdb", "pool"), ("sdc", "pool"), ("sdd", "pool"), ("sde", "parity")):
        d = next(x for x in ph.drives(host) if x["name"] == name)
        plan = ph.plan_add(host, name, role, erase=True)
        ph.apply(host, plan["id"], {d["by_id"]: d["ends"]})
        cfg = host.config()
        sizes[next(x["mount"] for x in cfg["drives"] if x["by_id"] == d["by_id"])] = d["size"]
    sizes[host.pool] = sum(v for k, v in sizes.items() if k.startswith("/mnt/disks"))
    fill[host.pool] = 0.62
    ph.write_json(str(root / "var/lib/starboard-pool/nightly.json"), {"at": dt.datetime.now().timestamp() - 30000,
                  "results": [{"what": "parity", "state": "done", "say": "Every file is protected"}]})
    ph.publish_status(host)
    os.environ["STARBOARD_POOL_DIR"] = str(exchange)

    def loop():
        while True:
            try:
                if any(n.endswith(".json") for n in os.listdir(exchange / "requests")):
                    ph.serve(host)
            except Exception as e:  # noqa: BLE001 - an example: say what went wrong and carry on
                print("pool example:", e, flush=True)
            threading.Event().wait(0.5)
    threading.Thread(target=loop, daemon=True).start()


def main():
    fake = ThreadingHTTPServer(("127.0.0.1", FAKE_PORT), FakeArr)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    DATA.mkdir(parents=True, exist_ok=True)
    types = {"tv": 8.1 * TB, "movies": 4.6 * TB, "audiobooks": 0.42 * TB, "music": 0.61 * TB, "books": 0.05 * TB,
             "downloads": 0.19 * TB, "other": 0.23 * TB}
    names = ["The Lighthouse Keepers", "Harbour Street", "Northern Line", "Station Eleven Days", "The Long Field",
             "Copper Valley", "Midnight Garden", "The Quiet Coast", "Paper Planets", "Saltmarsh"]
    biggest = [{"name": n, "type": "movies" if i in (3, 7) else "tv", "bytes": int((640 - i * 45) * GB)} for i, n in enumerate(names)]
    now = dt.datetime.now().timestamp()
    (DATA / "usage.json").write_text(json.dumps({"started": now - 120, "finished": now - 60, "folders": [
        {"label": "Media pool", "items": [], "types": {k: int(v) for k, v in types.items()}, "biggest": biggest}]}))
    (DATA / "space.json").write_text(json.dumps({(today - dt.timedelta(days=59 - i)).isoformat():
                                                  {"Media pool": [int(13.2 * TB + i * 0.017 * TB), int(24 * TB)]} for i in range(60)}))
    imports = DATA / "imports"
    imports.mkdir(exist_ok=True)
    titles = ["The Lighthouse Keepers", "Harbour Street", "Northern Line", "Copper Valley", "Midnight Garden", "The Quiet Coast",
              "Paper Planets", "Saltmarsh", "A Winter Map", "The Glass Orchard", "Small Hours", "Tidewater"]
    book = lambda i, t: {"title": t, "author": "A. Example", "asin": "", "isbn": "", "folder": "", "position_s": 3600.0 * (i + 1),
                         "duration_s": 36000.0, "finished": i % 4 == 0, "finished_at": None, "updated": now}
    (imports / "listening.json").write_text(json.dumps({"source": "Plex", "imported": now - 600, "accounts": {
        "Sam": [book(i, t) for i, t in enumerate(titles)], "Alex": [book(i, t) for i, t in enumerate(titles[:5])],
        "Jo": [book(i, t) for i, t in enumerate(titles[5:8])]}}))
    (imports / "listening-mapping.json").write_text(json.dumps({"Sam": "sam", "Alex": "alex", "Jo": ""}))
    (imports / "listening-applied.json").write_text(json.dumps({"sam": [f"b{i}" for i in range(10)], "alex": [f"b{i}" for i in range(5)]}))
    (imports / "listening-result.json").write_text(json.dumps({"finished": now - 300, "written": 14, "kept": 1, "unmatched_count": 2, "problems": [],
        "unmatched": [{"account": "Sam", "title": "Small Hours", "author": "A. Example"}, {"account": "Sam", "title": "Tidewater", "author": "A. Example"}]}))
    film = lambda t, y: {"type": "movie", "title": t, "year": y, "watched": True, "ids": {"tmdb": str(y)}}
    (imports / "history.json").write_text(json.dumps({"source": "Plex database", "imported": dt.datetime.now(dt.timezone.utc).isoformat(), "accounts": {
        "Sam": [film(t, 2000 + i) for i, t in enumerate(titles)], "Alex": [film(t, 2010 + i) for i, t in enumerate(titles[:4])]}}))
    (imports / "mapping.json").write_text(json.dumps({"Sam": "sam", "Alex": "alex"}))
    (imports / "result.json").write_text(json.dumps({"finished": dt.datetime.now(dt.timezone.utc).isoformat(), "marked": 13, "resumed": 0, "unmatched_count": 3,
        "unmatched": [{"account": "Sam", "title": "Small Hours (2010)"}, {"account": "Sam", "title": "Tidewater (2011)"},
                      {"account": "Alex", "title": "Harbour Street (2011)"}]}))
    (DATA / "jobs.json").write_text(json.dumps({"listening": {"started": now - 320, "finished": now - 300, "state": "done",
                                                               "summary": "Wrote 14 books; kept 1 that already had progress; 2 not found in Audiobookshelf"}}))
    example_pool(DATA)
    # A Basics install, as Install apps writes it, for Settings, Apps, Your install. Nothing is started.
    stack.can_download = lambda ref, check=None: True
    if not (DATA / "stack" / "compose.yaml").exists():
        basics = stack.install_choice("basics")
        stack.write(str(DATA), stack.build({"apps": basics["apps"], "config_dir": "/srv/media-stack/config",
                                            "data_dir": "/srv/media", "reelix_edition": "lite",
                                            "vpn": {"provider": "mullvad", "type": "wireguard",
                                                    "wireguard_private_key": "made-up", "wireguard_addresses": "192.168.1.20/32"}}))
    server, app = make_server("127.0.0.1", PORT, str(DATA))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if app.needs_setup:
        password = secrets.token_urlsafe(12)
        (DATA / "password").write_text(password + "\n")
        r, _ = call("POST", "/api/setup", {"token": app.setup_token, "password": password})
        cookie = r.getheader("Set-Cookie").split(";")[0]
        # A short server name, as Settings, General sets it: it starts the top row of the menu (DASH-237).
        call("PUT", "/api/config/general", {"server_name": "Harbour"}, cookie)
        for name, kind, group, path in APPS:
            url = f"http://127.0.0.1:{FAKE_PORT}/{path}" if path else "http://127.0.0.1:9/"
            call("POST", "/api/services", {"name": name, "type": kind, "group": group, "url": url, "api_key": KEY if kind != "link" else ""}, cookie)
        # Reelix, as Install apps adds it: a link with the manager key, so radio shows in Coming up and Downloads.
        call("POST", "/api/services", {"name": "Reelix", "type": "link", "group": "Downloads", "icon": "reelix",
                                       "url": f"http://127.0.0.1:{FAKE_PORT}/reelix", "api_key": KEY}, cookie)
        if EXAMPLE_CONTAINERS:
            # Reelix, seen at 0.7.0 before, so opening Apps, Updates finds it updated to 0.7.1.
            _, body = call("GET", "/api/config", cookie=cookie)
            rid = next(sv["id"] for sv in json.loads(body)["services"] if sv["name"] == "Reelix")
            (DATA / "app-changes.json").write_text(json.dumps({"seen": {rid: "0.7.0"}, "notices": {}}))
    print("READY", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
