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
from starboard import containers, discovery, stack, sysinfo  # noqa: E402
from starboard.server import make_server  # noqa: E402

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
stack._port_free = lambda port: True
discovery.search = lambda services: {"docker": False, "items": [
    {"key": k, "name": n, "type": k, "url": f"http://127.0.0.1:{p}", "port": p, "needs_key": True, "background": False,
     "container": "", "already": False, "can_read_key": False} for k, n, p in (("bazarr", "Bazarr", 6767), ("prowlarr", "Prowlarr", 9696))]}

KEY = "example-key"
today = dt.date.today()


class FakeArr(BaseHTTPRequestHandler):
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
    (DATA / "jobs.json").write_text(json.dumps({"listening": {"started": now - 320, "finished": now - 300, "state": "done",
                                                               "summary": "Wrote 14 books; kept 1 that already had progress; 2 not found in Audiobookshelf"}}))
    server, app = make_server("127.0.0.1", PORT, str(DATA))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if app.needs_setup:
        password = secrets.token_urlsafe(12)
        (DATA / "password").write_text(password + "\n")
        r, _ = call("POST", "/api/setup", {"token": app.setup_token, "password": password})
        cookie = r.getheader("Set-Cookie").split(";")[0]
        for name, kind, group, path in APPS:
            url = f"http://127.0.0.1:{FAKE_PORT}/{path}" if path else "http://127.0.0.1:9/"
            call("POST", "/api/services", {"name": name, "type": kind, "group": group, "url": url, "api_key": KEY if kind != "link" else ""}, cookie)
    print("READY", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
