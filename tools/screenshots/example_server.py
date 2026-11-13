#!/usr/bin/env python3
"""Starboard with made-up data only, for the README screenshots (tools/screenshots.sh starts it).

Nothing real is read: the folders, drives, apps found on this computer and container access are all
replaced with examples, and a fake Sonarr and Radarr answer on a second port. Data lives in a temporary
folder that is thrown away. Usage:  python3 tools/screenshots/example_server.py DATA_DIR [PORT]
It prints READY when signed-in screenshots can start, and writes a throwaway password to DATA_DIR/password.
"""
import datetime as dt
import time
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
from starboard import changes, child, containers, discovery, stack, sysinfo  # noqa: E402
child.ENABLED = os.environ.get("STARBOARD_CHILD_JOBS") == "1"  # heavy jobs in a short-lived process, as the server (DASH-79)
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


def _never_docker(*a, **k):  # the test copy never reaches this computer's Docker, whatever a page asks
    raise containers.DockerError("Example data: Docker is not used")


containers.docker = _never_docker
containers._helper = _never_docker
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
# Plug-ins (DASH-149, DASH-284): the Styles plug-in added and active, and a made-up Hello card that the help's
# Add a plug-in pictures preview from an address (nothing is fetched: the address answers with this manifest).
from starboard import plugins_admin  # noqa: E402
_HELLO = {"manifest_version": 1, "id": "hello-card", "name": "Hello card", "version": "0.1.0",
          "description": "A made-up example that shows one number on your dashboard.", "author": "TheMightyTRexUK",
          "licence": "MIT", "homepage": "https://example.invalid/hello", "support_url": "https://example.invalid/hello/issues",
          "starboard_api": ">=1.0 <2.0", "permissions": ["apps:read"], "health": "/health",
          "containers": [{"name": "main", "image": "ghcr.io/example/hello@sha256:" + "a" * 64, "port": 8080, "volumes": ["data"]}],
          "cards": [{"id": "count", "title": "Hello", "type": "stat", "path": "/card", "format": "number",
                     "example": {"value": 42, "label": "hellos", "note": "3 today"}}]}
plugins_admin.fetch_manifest = lambda address, opener=None: dict(_HELLO)


def _example_dispatcharr():
    """Dispatcharr (DASH-228), an add-on: set up by Starboard, with a made-up playlist of 48 streams read but no channels
    and no guide yet, and a made-up Jellyfin without its tuner, so Settings, Apps, Dispatcharr shows every part. Both
    answer here, in this process (tests/dispatcharr_stand_in.py): nothing is fetched."""
    from starboard import dispatcharr
    from tests.dispatcharr_stand_in import StandIn
    fake = StandIn(admin_password="made-up", streams=48, prefix="/dispatcharr")
    fake.key = KEY
    fake.playlists.append({"id": 1, "name": dispatcharr.PLAYLIST, "server_url": "https://iptv.example/get.php?type=m3u_plus",
                           "account_type": "STD", "max_streams": 2, "status": "success",
                           "last_message": "Read 48 streams in 6 groups."})
    dispatcharr.OPENER = fake
    dispatcharr.jellyfin = lambda cfg: {"name": "Jellyfin", "type": "jellyfin", "url": "http://jellyfin.example:8096", "api_key": "made-up"}
    dispatcharr.inside_address = lambda cfg, data_dir: dispatcharr.INSIDE


def _example_full_backups():
    """System, Backup and restore, Full without media (DASH-260): the media folder on its own disk, so the page says
    which disk the copies go on, and two made-up copies in the folder. Nothing is read from this computer."""
    from starboard import full_backup
    full_backup._drives = lambda data_dir: [{"mount": "/srv/media", "device": "sdb1", "size": 4000 * 1000 ** 3, "fs": "ext4",
                                             "model": "WDC WD40EFRX", "label": ""}]
    apps = ["audiobookshelf", "bazarr", "gluetun", "jellyfin", "qbittorrent", "reelix"]
    day = dt.datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)
    full_backup.found = lambda folder: [
        {"name": f"starboard-full-{d:%Y-%m-%d-%H%M%S}.starboard", "path": f"{folder}/starboard-full-{d:%Y-%m-%d-%H%M%S}.starboard",
         "size": 640 * 1000 ** 2 + n * 3 * 1000 ** 2, "created": d.isoformat(timespec="seconds"), "version": "0.15.0", "pictures": False,
         "apps": apps, "site_name": "Harbour", "config_dir": "/srv/media-stack/config"}
        for n, d in enumerate(day - dt.timedelta(days=7 * k) for k in range(2))]
def _example_copies(data):
    """Copies off this computer (DASH-380): set to a made-up USB disk, with last night's copy made. The helper is a
    stand-in that answers as the real one would, so Test and Copy the newest now work without Docker."""
    from starboard import backup_copies
    usb = str(data / "example-computer" / "mnt" / "usb-backup" / "starboard")
    if not (data / backup_copies.SETTINGS).exists():
        backup_copies.save(str(data), {**backup_copies.settings(str(data)), "kind": "disk", "folder": usb, "keep": 5},
                           backup_copies.secrets(str(data)))
        last = dt.datetime.now().replace(hour=3, minute=4, second=0).timestamp()
        backup_copies._say(str(data), state="done", started=last - 40, finished=last, where=usb,
                           file=str(data / "example-computer" / "mnt" / "disk2" / "backups" / "starboard-full-2026-11-13-030000.starboard"),
                           said=f"Copied to {usb}, which keeps 5 full backups")
    backup_copies._helper = lambda script, binds, image=None, network="none", volumes=(), timeout=7200: (0, "COUNT 5\n")
    backup_copies.newest = lambda data_dir: str(data / "example-computer" / "mnt" / "disk2" / "backups" / "starboard-full-2026-11-13-030000.starboard")


def _example_folders(data):
    """The folder picker (DASH-240) browses a made-up tree, never this computer's own folders."""
    from starboard import folders
    root = data / "example-computer"
    for d in ("mnt/disk1/media/movies", "mnt/disk1/media/tv", "mnt/disk1/media/books", "mnt/disk2/backups", "mnt/pool/media",
              "srv/media/downloads", "srv/apps/config", "home/sam/media"):
        (root / d).mkdir(parents=True, exist_ok=True)
    folders.ROOTS = tuple(str(root / r) for r in ("mnt", "srv", "home"))


_STYLES_CHANGES = [
    {"version": "1.1.0", "date": "2026-11-12",
     "added": ["**Three new styles:** Sunset, Graphite and Editorial, each checked for contrast in light and dark.",
               "Styles may set heading weight and the focus ring's width."],
     "changed": ["Midnight's accent is a little brighter, so links stand out on cards."],
     "fixed": ["Paper's chips no longer lose their border in high contrast.",
               "A style chosen on a phone is kept after Starboard restarts."]},
    {"version": "1.0.0", "date": "2026-11-10", "added": ["The first ten styles."]}]


def _example_plugins(data_dir):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "example-plugin-styles.json"), encoding="utf-8") as f:
        styles = json.load(f)
    if not plugins_admin.listing(data_dir):
        # Added at 1.0.0, then updated to 1.1.0 with its changes (API 1.10), so its State shows What is new until
        # Got it (DASH-393). Nothing is fetched: the update is given the manifest.
        from starboard import plugin_life
        plugins_admin.install(data_dir, {**styles, "version": "1.0.0", "styles": styles["styles"][:10]}, "/nonexistent-media")
        plugins_admin.enable(data_dir, "styles")
        plugin_life.update(data_dir, "styles", {**styles, "starboard_api": ">=1.10 <2.0", "changes": _STYLES_CHANGES}, "/nonexistent-media")


# Live TV (DASH-361): the built-in plug-in added and active, with made-up channels in three lists and one of your own,
# so its Channels sub menus can be tried. Its screens run Live TV's own code here, in this process: nothing is fetched,
# no container starts, and Jellyfin is never told.
_LIVETV_CHANNELS = [  # (name, section, list, region)
    ("Harbour One", "Entertainment", "channels.m3u", "UK"), ("Harbour Two", "Entertainment", "channels.m3u", "UK"),
    ("Coast News", "News", "channels.m3u", "UK"), ("Little Lanterns", "Kids", "channels.m3u", "UK"),
    ("Saltmarsh Drama", "Entertainment", "samsung.m3u", "UK"), ("Quiet Coast Comedy", "Entertainment", "samsung.m3u", "UK"),
    ("Paper Planets Kids", "Kids", "samsung.m3u", "UK"), ("Northern Line News", "News", "samsung.m3u", "UK"),
    ("Copper Valley Sport", "Sport", "samsung.m3u", "UK"), ("Tidewater Films", "Movies", "samsung.m3u", "UK"),
    ("Midnight Garden Music", "Music", "samsung.m3u", "UK"), ("Long Field Living", "Lifestyle", "samsung.m3u", "UK"),
    ("Glass Orchard Docs", "Documentaries", "samsung.m3u", "UK"), ("Station Eleven Classics", "Movies", "samsung.m3u", "UK"),
    ("Lighthouse Westerns", "Movies", "samsung.m3u", "US"), ("Small Hours News", "News", "samsung.m3u", "US"),
    ("Winter Map Weather", "News", "samsung.m3u", "US"), ("Harbour Street Sport", "Sport", "samsung.m3u", "US"),
    ("Riverbend Cooking", "Lifestyle", "samsung.m3u", "US"), ("Cartoon Coves", "Kids", "samsung.m3u", "US"),
    ("Open Road Comedy", "Entertainment", "samsung.m3u", "US"), ("Desert Docs", "Documentaries", "samsung.m3u", "US"),
    ("Pier Films", "Movies", "pluto.m3u", "UK"), ("Pier Thrillers", "Movies", "pluto.m3u", "UK"),
    ("Pier Mysteries", "Entertainment", "pluto.m3u", "UK"), ("Pier Nature", "Documentaries", "pluto.m3u", "UK"),
    ("Pier Retro", "Entertainment", "pluto.m3u", "UK"), ("Community Radio Vision", "Other", "own.m3u", ""),
    ("Harbour Council Live", "News", "own.m3u", "")]
_LIVETV_HIDDEN = ("Quiet Coast Comedy", "Station Eleven Classics", "Lighthouse Westerns", "Winter Map Weather", "Pier Retro")


def _example_keys(data_dir):
    """Two made-up API keys, so Settings, Security, API keys shows a read key and a manage key with scopes (DASH-274)."""
    from starboard import api_v1
    if not any(not k["name"].startswith("Plug-in: ") for k in api_v1.list_keys(data_dir)):
        api_v1.create_key(data_dir, "Home Assistant", "read", ["apps", "system"], 365)
        api_v1.create_key(data_dir, "Requests helper", "manage", ["requests"], 90)


def _example_livetv(data_dir):
    from starboard import livetv, livetv_own, livetv_plugin, plugin_cards, plugin_custom, plugin_watch
    root = os.path.join(data_dir, "example-livetv")
    iptv, own = os.path.join(root, "iptv"), os.path.join(root, "data")
    os.makedirs(iptv, exist_ok=True)
    os.makedirs(own, exist_ok=True)
    livetv.folder = lambda: iptv
    livetv_plugin.DATA = own
    livetv_plugin.JELLYFIN = os.path.join(own, "no-jellyfin.json")  # no Jellyfin: nothing is told
    if not os.path.exists(os.path.join(iptv, livetv.ALL)):
        src = "a1b2c3d4e5"
        with open(os.path.join(own, livetv_own.FILE), "w", encoding="utf-8") as f:
            json.dump([{"id": src, "url": "https://example.invalid/harbour.m3u", "kind": "list", "name": "Harbour community",
                        "on": True, "said": "2 of 3 channels play", "state": "ok", "guide": "https://example.invalid/harbour-guide.xml.gz",
                        "guide_said": "2 of 2 channels have programmes",
                        "result": {"added": 1, "inactive": 1, "total": 3, "text": "1 is already in Live TV, so it came in inactive: "
                                   "activate it in Channels when you want. 1 address answers Not found"}}], f)
        nxt = {b: n for b, n in livetv.BLOCKS}
        chans = []
        for i, (name, section, lst, region) in enumerate(_LIVETV_CHANNELS):
            chans.append({"id": f"example-{i}", "name": name, "number": str(nxt[section]), "section": section, "list": lst,
                          "region": region, "source": src if lst == "own.m3u" else ""})
            nxt[section] += 1
        with open(os.path.join(iptv, livetv.ALL), "w", encoding="utf-8") as f:
            json.dump(chans, f)
        livetv.save_hidden(own, {c["id"] for c in chans if c["name"] in _LIVETV_HIDDEN})
        # The lists as the run writes them, with a made-up guide, for the On TV now card (DASH-359)
        for lst in livetv.FILES:
            with open(os.path.join(iptv, lst), "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n" + "".join(f'#EXTINF:-1 tvg-id="{c["id"]}" tvg-chno="{c["number"]}" group-title="{c["section"]}",{c["name"]}\n'
                                               f'https://example.invalid/{c["id"]}.m3u8\n' for c in chans if c["list"] == lst and c["name"] not in _LIVETV_HIDDEN))
    shows = ("Morning Briefing", "Football Extra", "Classic Film Club", "Darts: The Final", "Nature Watch", "Harbour Kitchen", "Hits Hour",
             "Home Makeover", "The Quiz", "Evening News")
    start = int(time.time()) // 1800 * 1800 - 1800
    stamp = lambda t: time.strftime("%Y%m%d%H%M%S +0000", time.gmtime(t))
    with open(os.path.join(iptv, "guide-own.xml"), "w", encoding="utf-8") as f:  # made fresh at each start, so "now" is now
        f.write('<?xml version="1.0" encoding="utf-8"?><tv>' + "".join(
            f'<programme channel="example-{i}" start="{stamp(start + k * 3600 + (i % 3) * 900)}" stop="{stamp(start + (k + 1) * 3600 + (i % 3) * 900)}">'
            f'<title>{shows[(i + k) % len(shows)]}</title></programme>' for i in range(len(_LIVETV_CHANNELS)) for k in range(5)) + "</tv>")
    livetv.write_now(iptv, own)
    if not any(p["id"] == "livetv" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, plugins_admin.builtins()["livetv"], "/nonexistent-media", builtin=True,
                              defaults={"address": "http://192.168.1.20:8095", "jellyfin_folder": "/config/iptv"},
                              host={"image": "starboard", "user": "1000:1000", "iptv": iptv, "tz": None})
        plugins_admin.set_state(data_dir, "livetv", "enabled")

    def nothing_fetched(url, *a, **k):
        raise OSError("this is example data, so nothing is fetched")

    screens = {"channels": (livetv_plugin.channels_screen, livetv_plugin.channels_act),
               "sources": (livetv_plugin.sources_screen, lambda body: livetv_plugin.sources_act(body, nothing_fetched))}
    real_call, real_upload, real_ask, real_action = plugin_custom.call, plugin_custom.upload, plugin_watch._ask, plugin_cards.action

    def call(data_dir_, pid, key, body=None, opener=None):
        if pid != "livetv":
            return real_call(data_dir_, pid, key, body, opener)
        if key not in screens:
            raise LookupError("No such screen")
        if body is not None and body.get("action") not in plugin_custom.ACTIONS:
            raise ValueError("Not something this screen does")
        try:
            return plugin_custom.clean(screens[key][0]() if body is None else screens[key][1](body))
        except (OSError, KeyError) as e:
            raise ValueError(f"That address did not answer: {e}"[:200]) from None

    def upload(data_dir_, pid, key, name, length, stream, item=""):
        if pid != "livetv" or key != "sources":
            return real_upload(data_dir_, pid, key, name, length, stream, item)
        return plugin_custom.clean(livetv_plugin.sources_upload(name, stream, length, item))

    plugin_custom.call, plugin_custom.upload = call, upload
    livetv_plugin.SETTINGS = os.path.join(own, "settings.json")
    # Example data: a list just added is "tested" without fetching, half way, so its notice shows; guides are not read
    livetv_plugin._quick = lambda sid: livetv_own._update(own, sid, said="Testing", state="unknown", progress={"done": 4, "total": 13})
    livetv_plugin._guides_now = lambda: None
    real_answer = plugin_cards.answer
    plugin_cards.answer = lambda d, pid, cid, opener=None: (  # the On TV now card, from the made-up guide (DASH-359)
        {"type": "guide", "format": "number", "data": plugin_cards.clean("guide", livetv_plugin.now_card())} if pid == "livetv" and cid == "now"
        else real_answer(d, pid, cid, opener))
    plugin_watch._ask = lambda pid, main, path: "ok" if pid == "livetv" else real_ask(pid, main, path)
    plugin_cards.action = lambda d, pid, aid, opener=None: (
        {"said": "Live TV is running now. This is example data, so nothing is fetched."} if pid == "livetv" else real_action(d, pid, aid, opener))


# Watch statistics (DASH-402): the example plug-in added and active, with made-up plays, so its read-only tables
# (plug-in API 1.11) can be tried. Its screen answers here, in this process: nothing is fetched and no container starts.
_PLAYS = [  # (days ago, hour, who, title, device, minutes)
    (0, 20, "Sam", "Slow Horses: Failure's Contagious", "Lounge TV", 52), (0, 18, "Alex", "Dune: Part Two", "Bedroom TV", 166),
    (1, 21, "Sam", "Slow Horses: Last Stop", "Lounge TV", 49), (1, 19, "Robin", "Bluey: Keepy Uppy", "Tablet", 7),
    (2, 20, "Alex", "The Bear: Tomorrow", "Phone", 31), (2, 9, "Robin", "Bluey: Camping", "Tablet", 8),
    (3, 22, "Sam", "Brazil", "Lounge TV", 142), (4, 20, "Alex", "Slow Horses: Last Stop", "Bedroom TV", 50),
    (5, 17, "Robin", "Paddington 2", "Lounge TV", 103), (6, 21, "Sam", "The Bear: Tomorrow", "Lounge TV", 33)]


def _watch_stats_screen(key):
    """The three read-only tables, as the plug-in answers them: plays by day, top titles, and people."""
    today = dt.datetime.now().replace(minute=0, second=0, microsecond=0)
    top, people, rows = {}, {}, []
    for i, (ago, hour, who, title, device, mins) in enumerate(_PLAYS):
        when = (today - dt.timedelta(days=ago)).replace(hour=hour)
        day = "Today" if ago == 0 else "Yesterday" if ago == 1 else f"{when:%A} {when.day} {when:%B}"
        if key == "plays":
            rows.append({"id": f"play-{i}", "title": title, "group": day, "actions": [],
                         "cells": {"time": when.strftime("%H:%M"), "person": who, "title": title, "device": device, "minutes": str(mins)}})
        name = title.split(":")[0]
        t = top.setdefault(name, {"plays": 0, "people": set(), "mins": 0})
        t["plays"], t["mins"] = t["plays"] + 1, t["mins"] + mins
        t["people"].add(who)
        p = people.setdefault(who, {"plays": 0, "mins": 0, "last": title})
        p["plays"], p["mins"] = p["plays"] + 1, p["mins"] + mins
    if key == "titles":
        rows = [{"id": f"top-{n}", "title": n, "group": "Series" if n in ("Slow Horses", "Bluey", "The Bear") else "Films", "actions": [],
                 "cells": {"title": n, "plays": str(t["plays"]), "people": str(len(t["people"])), "hours": f"{t['mins'] / 60:.1f}"}}
                for n, t in sorted(top.items(), key=lambda kv: -kv[1]["plays"])]
        cols = [("title", "Title", ""), ("plays", "Plays", "number"), ("people", "People", "number"), ("hours", "Hours", "number")]
    elif key == "people":
        rows = [{"id": f"person-{w}", "title": w, "group": "Everyone", "actions": [],
                 "cells": {"person": w, "plays": str(p["plays"]), "hours": f"{p['mins'] / 60:.1f}", "last": p["last"]}}
                for w, p in sorted(people.items())]
        cols = [("person", "Person", ""), ("plays", "Plays", "number"), ("hours", "Hours", "number"), ("last", "Last watched", "")]
    else:
        cols = [("time", "Time", ""), ("person", "Person", ""), ("title", "Title", ""), ("device", "Device", ""), ("minutes", "Minutes", "number")]
    return {"type": "list", "title": {"plays": "Plays", "titles": "Titles", "people": "People"}.get(key, "Plays"), "layout": "folds",
            "readonly": True, "intro": "From Jellyfin's Playback Reporting, over the last 30 days. This is example data.",
            "columns": [{"key": k, "label": w, "type": t} for k, w, t in cols], "items": rows}


def _example_watch_stats(data_dir):
    from starboard import plugin_cards, plugin_custom, plugin_watch
    if not any(p["id"] == "watch-stats" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {
            "manifest_version": 1, "id": "watch-stats", "name": "Watch statistics", "version": "1.0.0",
            "description": "What was watched, by whom and when, from Jellyfin's Playback Reporting.", "author": "TheMightyTRexUK",
            "licence": "MIT", "homepage": "https://example.invalid/watch-stats", "support_url": "https://example.invalid/watch-stats/issues",
            "starboard_api": ">=1.11 <2.0", "permissions": ["jellyfin:key", "network:lan"], "health": "/health",
            "containers": [{"name": "main", "image": "ghcr.io/example/watch-stats@sha256:" + "b" * 64, "port": 8080, "network": "lan",
                            "volumes": ["data"], "start": "when_needed"}],
            "settings": [{"key": "plays", "label": "Recent plays", "type": "custom", "choices": "/screen/plays"},
                         {"key": "titles", "label": "Top titles", "type": "custom", "choices": "/screen/titles"},
                         {"key": "people", "label": "People", "type": "custom", "choices": "/screen/people"},
                         {"key": "days", "label": "Over the last", "type": "number", "unit": "days", "default": 30, "min": 1, "max": 365}]},
            "/nonexistent-media")
        plugins_admin.set_state(data_dir, "watch-stats", "enabled")
    if not any(p["id"] == "notifications" for p in plugins_admin.listing(data_dir)):
        # Notifications (DASH-401): its settings in sections, secrets shown only as set or not set; nothing is sent.
        sw = lambda key, label, group, on=True: {"key": key, "label": label, "type": "switch", "default": on, "group": group}  # noqa: E731
        plugins_admin.install(data_dir, {
            "manifest_version": 1, "id": "notifications", "name": "Notifications", "version": "1.0.0",
            "description": "Sends Starboard's events to email, Telegram, Discord, Signal, Pushover, ntfy or a webhook, in plain words.",
            "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://example.invalid/notifications",
            "support_url": "https://example.invalid/notifications/issues", "starboard_api": ">=1.11 <2.0",
            "permissions": ["apps:read", "downloads:read", "media:read", "system:read", "network:lan"], "health": "/health",
            "containers": [{"name": "main", "image": "ghcr.io/example/notifications@sha256:" + "c" * 64, "port": 8080, "network": "lan",
                            "volumes": ["data"], "start": "when_needed"}],
            "settings": [sw("send_requests", "Something someone asked for is ready", "What to send"),
                         sw("send_failed", "A download failed", "What to send"), sw("send_disk", "A disk is nearly full", "What to send"),
                         sw("email_active", "Send by email", "Email", False),
                         {"key": "smtp_host", "label": "Email server", "type": "text", "group": "Email"},
                         {"key": "smtp_password", "label": "Password", "type": "secret", "group": "Email"},
                         sw("telegram_active", "Send by Telegram", "Telegram"),
                         {"key": "telegram_token", "label": "Bot token", "type": "secret", "group": "Telegram"},
                         {"key": "telegram_chat", "label": "Telegram chat", "type": "list", "group": "Telegram"}],
            "actions": [{"id": "test-telegram", "label": "Send a test to Telegram", "path": "/test/telegram"}],
            "events": ["request.available", "download.failed", "disk.nearly_full", "app.down", "app.up", "update.available"],
            "jobs": [{"id": "weekly", "label": "Send New this week on the chosen day", "path": "/jobs/weekly", "daily": "09:00"}]},
            "/nonexistent-media")
        plugins_admin.save_settings(data_dir, "notifications", {"telegram_token": "tg-example-token-401", "telegram_chat": ["42"], "smtp_host": "smtp.example.com"})
        # Deactivated, so the plug-in clock never sends it events or runs its job here: no container is asked for.
        plugins_admin.set_state(data_dir, "notifications", "disabled")
    real_call, real_ask, real_action = plugin_custom.call, plugin_watch._ask, plugin_cards.action

    def call(data_dir_, pid, key, body=None, opener=None):
        if pid != "watch-stats":
            return real_call(data_dir_, pid, key, body, opener)
        if body is not None:
            raise ValueError("These figures are read only")
        return plugin_custom.clean(_watch_stats_screen(key))
    plugin_custom.call = call
    plugin_watch._ask = lambda pid, main, path: "ok" if pid in ("watch-stats", "notifications") else real_ask(pid, main, path)
    plugin_cards.action = lambda d, pid, aid, opener=None: (
        {"said": "Test sent by Telegram. This is example data, so nothing was sent."} if pid == "notifications" else real_action(d, pid, aid, opener))


# Audio description sources (DASH-410, plug-in API 1.12): the Audio description plug-in's AudioVault and YouDescribe
# links and its MovieReading and Earcatch guide, and the Audio description tracks plug-in's list, with rows in each
# state, an upload that takes only a file, and links that open in a new tab. Answered here; nothing is fetched.
_AD_FILMS = [("Brazil", 1985), ("Paddington 2", 2017), ("The Bear", 0), ("Bluey", 0)]


def _ad_screen(key):
    if key == "audiovault":
        items = [{"id": f"film:{n}", "title": f"{n} ({y})" if y else n, "group": "Films" if y else "Series", "actions": [], "state": "off",
                  "state_label": "No description here", "menu": "films" if y else "series",
                  "link": {"url": ("https://audiovault.net/movies?search=" if y else "https://audiovault.net/shows?search=") + n.replace(" ", "%20"),
                           "label": f"Search AudioVault for {n}" + (f" ({y})" if y else "")}} for n, y in _AD_FILMS]
        return {"type": "list", "title": "Search AudioVault", "items": items,
                "menus": [{"id": "films", "title": "Films", "group": "Your library", "detail": "2 titles"},
                          {"id": "series", "title": "Series", "group": "Your library", "detail": "2 titles"}],
                "intro": "Each link opens AudioVault's own search for a title without audio description. Starboard never downloads from "
                         "AudioVault or reads its pages. This is example data."}
    if key == "apps":
        return {"type": "list", "title": "MovieReading and Earcatch", "intro": "Phone apps that play a description in step, by listening. This is example data.",
                "items": [{"id": "mr-ios", "title": "MovieReading for iPhone and iPad", "group": "MovieReading", "actions": [], "state": "ok", "state_label": "Link only",
                           "link": {"url": "https://apps.apple.com/app/id460349347", "label": "MovieReading on the App Store"}},
                          {"id": "step-1", "title": "Get the description first", "group": "Using one with Jellyfin", "actions": [], "state": "off",
                           "state_label": "Step 1", "detail": "Install the app and download the description for your film at home on Wi-Fi."}]}
    rows = [{"id": "Dune (2021).mp3", "title": "Dune (2021).mp3", "group": "Added: check each plays in step", "actions": [], "state": "ok", "state_label": "Added",
             "detail": "Added to Dune (2021) as English (Audio Description). Play it in Jellyfin, then say whether it plays in step.",
             "choice": {"label": "Plays in step?", "value": "wait", "options": [["wait", "Not checked yet"], ["right", "Yes: put the original away"],
                                                                                 ["undo", "No: take the track off"]]}},
            {"id": "Brazil (1985).mp3", "title": "Brazil (1985).mp3", "group": "To check", "actions": [], "state": "warning", "state_label": "Lengths differ",
             "detail": "Brazil (1985): the track is 3 minutes 28 seconds longer than the film, so it is probably for another cut, such as an extended one.",
             "link": {"url": "https://audiovault.net/movies?search=Brazil", "label": "Search AudioVault for Brazil"}},
            {"id": "Heat.mp3", "title": "Heat.mp3", "group": "To check", "actions": [], "state": "warning", "state_label": "Choose the title",
             "detail": "More than one title could match. Choose the right one.",
             "choice": {"label": "Film or episode", "value": "", "options": [["", "Choose one"], ["m1", "Heat (1995)"], ["m2", "Heat (1986)"]]}}]
    return {"type": "list", "title": "Description tracks to add", "items": rows,
            "intro": "Put a description track you already have in the audio-description folder, or upload one here. This is example data.",
            "add": {"label": "Upload a description track", "file_only": True,
                    "file": {"label": "Choose a description track", "accept": ".mp3,.m4a,.zip", "hint": "MP3, M4A or a zip of them, up to 60 MB."}}}


def _example_audio_description(data_dir):
    from starboard import plugin_custom, plugin_watch
    base = {"author": "TheMightyTRexUK", "licence": "MIT", "starboard_api": ">=1.12 <2.0", "health": "/health"}
    # Its id is not audio-description, so the Catalogue's offer of the real one (DASH-399) still shows here.
    if not any(p["id"] == "audio-description-sources" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {
            **base, "manifest_version": 1, "id": "audio-description-sources", "name": "Audio description", "version": "1.1.0",
            "description": "Finds films and series in Jellyfin with a described sound track, and links to places with more.",
            "homepage": "https://example.invalid/audio-description", "support_url": "https://example.invalid/audio-description/issues",
            "permissions": ["jellyfin:key", "network:lan"],
            "containers": [{"name": "main", "image": "ghcr.io/example/audio-description@sha256:" + "d" * 64, "port": 8080, "network": "lan",
                            "volumes": ["data"], "start": "when_needed"}],
            "settings": [{"key": "audiovault_links", "label": "AudioVault search links", "type": "switch", "default": True, "group": "Sources"},
                         {"key": "audiovault", "label": "Search AudioVault", "type": "custom", "choices": "/audiovault", "group": "AudioVault"},
                         {"key": "apps", "label": "MovieReading and Earcatch", "type": "custom", "choices": "/apps", "group": "MovieReading and Earcatch"}]},
            "/nonexistent-media")
        plugins_admin.set_state(data_dir, "audio-description-sources", "enabled")
    if not any(p["id"] == "audio-description-tracks" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {
            **base, "manifest_version": 1, "id": "audio-description-tracks", "name": "Audio description tracks", "version": "1.0.0",
            "description": "Adds a description track you already have to its film in Jellyfin, after checking the lengths match.",
            "homepage": "https://example.invalid/audio-description-tracks", "support_url": "https://example.invalid/audio-description-tracks/issues",
            "permissions": ["jellyfin:key", "network:lan"],
            "containers": [{"name": "main", "image": "ghcr.io/example/audio-description-tracks@sha256:" + "e" * 64, "port": 8080, "network": "lan",
                            "volumes": ["data", "media/movies", "media/tv", "media/audio-description"], "user": "media", "start": "when_needed"}],
            "settings": [{"key": "inbox", "label": "Description tracks to add", "type": "custom", "choices": "/inbox", "group": "Tracks"}]},
            "/nonexistent-media")
        plugins_admin.set_state(data_dir, "audio-description-tracks", "enabled")
    real_call, real_ask = plugin_custom.call, plugin_watch._ask
    ours = {"audio-description-sources", "audio-description-tracks"}

    def call(data_dir_, pid, key, body=None, opener=None):
        if pid not in ours:
            return real_call(data_dir_, pid, key, body, opener)
        out = plugin_custom.clean(_ad_screen(key))
        if body is not None:
            out["said"] = "This is example data, so nothing changed"
        return out
    plugin_custom.call = call
    plugin_watch._ask = lambda pid, main, path: "ok" if pid in ours else real_ask(pid, main, path)


from starboard import noip  # noqa: E402  The No-IP updater (DASH-170), with made-up addresses
noip.status = lambda data_dir, **k: {"installed": True, "running": True, "state": "refused", "last_update": "2026-11-09T10:19:01Z",
                                     "address": "203.0.113.7", "said": "Type a new DDNS key or password below, then save. The updater starts again with it.",
                                     "username": "examplekey", "hostnames": "home.example.net", "password_set": True}
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


# A stand-in Jellyfin for Settings, Apps, Jellyfin, Recommended plug-ins (DASH-404), answering on the fake port under
# /jellyfin: Playback Reporting installed and active, the rest not installed. Only that section talks to it, and no
# real Jellyfin is ever changed (tests/jellyfin_stand_in.py).
from tests.jellyfin_stand_in import KEY as JF_KEY, StandIn as JellyfinStandIn  # noqa: E402
from starboard import jellyfin_plugins  # noqa: E402
JELLYFIN = JellyfinStandIn(plugins=[{"Name": "Playback Reporting", "Version": "19.0.0.0", "Status": "Active",
                                     "Id": jellyfin_plugins.PACKAGES["playback"]["guid"].replace("-", "")}])
jellyfin_plugins.find = lambda services: {"type": "jellyfin", "name": "Jellyfin", "url": f"http://127.0.0.1:{FAKE_PORT}/jellyfin", "api_key": JF_KEY}


class FakeArr(BaseHTTPRequestHandler):
    def jellyfin(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null") if length else None
        status, answer = JELLYFIN.handle(method, self.path[len("/jellyfin"):], body, dict(self.headers))
        raw = json.dumps(answer).encode() if answer is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

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
        self._change("PUT")

    def do_DELETE(self):
        self._change("DELETE")

    def _change(self, method):
        """Library actions with the manager key go to the made-up Library; the admin's (a cookie) to Settings, Reelix."""
        if not self.headers.get("X-Api-Key") or not self.path.startswith("/reelix/api/v1/"):
            return self.reelix_admin(method)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        path, _, query = self.path[len("/reelix/api/v1"):].partition("?")
        parts = path.strip("/").split("/")
        if method == "PUT" and len(parts) == 4 and parts[:2] == ["radio", "episodes"] and parts[3] == "file":  # Match by hand (DASH-212)
            RADIO_MATCHED.add(int(body.get("file_id", 0)))
            return self.send_json({"id": int(parts[2]), "title": "the chosen episode", "file_id": body.get("file_id")})
        found = example_library.change(method, path, body, dict(urllib.parse.parse_qsl(query)))
        return self.send_json(found if found is not None else {"message": "no such route"}, 200 if found is not None else 404)

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
        if p.startswith("/jellyfin/"):
            return self.jellyfin("GET")
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
            q = dict(urllib.parse.parse_qsl(query))
            # The radio import's own shows answer first; any other radio search is the made-up library's, as before.
            mine = path == "/radio/library/review" or (path == "/radio/search" and any(x["title"].lower() == q.get("q", "").lower() for x in RADIO_ON_DISK))
            found = None if mine else example_library.answer(path, q)
            answer = found if found is not None else example_reelix(path, q)
            if path == "/radio/preview" and answer is None:
                return self.send_json({"error": "validation", "message": "no radio source recognises that link"}, 400)
            return self.send_json(answer)
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
    if self.path.startswith("/jellyfin/"):
        return self.jellyfin("POST")
    if not self.headers.get("X-Api-Key"):  # Reelix's admin routes, signed in with a cookie (Settings, Reelix)
        return self.reelix_admin("POST")
    length = int(self.headers.get("Content-Length") or 0)
    body = json.loads(self.rfile.read(length) or b"{}")
    if self.path.split("?")[0] == "/reelix/api/v1/releases/grab":  # Get this one, on Search the sites (DASH-213)
        return self.send_json({"queue_id": 77, "download_client": "NZBGet" if body.get("indexer_id") == 2 else "qBittorrent",
                               "download_id": f"ex-{body.get('guid')}"})
    if self.path.split("?")[0] == "/reelix/api/v1/radio/shows":  # a radio show added (the radio import, or from a link)
        if body.get("link"):
            RADIO_ADDED.append({"id": 10 + len(RADIO_ADDED), "title": "The Lighthouse Keepers", "external_id": body["link"]})
        else:
            RADIO_ADDED.append({"id": 10 + len(RADIO_ADDED), "title": body.get("external_id", ""), "external_id": body.get("external_id", "")})
        return self.send_json(RADIO_ADDED[-1], 201)
    if self.path.split("?")[0] == "/reelix/api/v1/command":  # Read the library again (DASH-212)
        return self.send_json({"job_id": 5}, 202)
    found = example_library.add(self.path[len("/reelix/api/v1"):].split("?")[0], body) if self.path.startswith("/reelix/api/v1/") else None
    return self.send_json(found or {}, 201 if found else 404)


FakeArr.do_POST = _post


RADIO_ON_DISK = [  # made-up radio shows in Audiobookshelf's Radio library that Reelix does not follow yet
    {"abs_item_id": "li_harbour", "title": "The Harbour Comedy Hour", "file_count": 24},
    {"abs_item_id": "li_light", "title": "Lighthouse Stories", "file_count": 12},
    {"abs_item_id": "li_night", "title": "Night Train", "file_count": 6}]
RADIO_ADDED = []
# Files in The Example Hour's podcast folder that match no episode, and one from a podcast nobody follows (DASH-212).
RADIO_UNMATCHED = [{"id": 900 + n, "abs_item_id": item, "abs_episode_id": f"ep{n}", "item_title": podcast, "title": title, "season": season,
                    "episode": number, "published_at": f"2025-0{n + 1}-0{n + 2}T19:00:00Z", "duration_secs": 1740, "size": 27_000_000 + n,
                    "path": f"/radio/{podcast}/{title}.mp3", "seen_at": "2026-11-13T06:00:00Z"}
                   for n, (item, podcast, title, season, number) in enumerate((
                       ("li_example", "The Example Hour", "Tides (repeat)", None, None), ("li_example", "The Example Hour", "Storms, extended", 4, None),
                       ("li_example", "The Example Hour", "Christmas special", None, None), ("li_quiz", "Pub Quiz Classics", "Round one", 1, 1)))]
RADIO_MATCHED = set()


def example_sites_search(query):
    """Search the sites (DASH-213): made-up releases for any words, from three made-up sites, one of which fails."""
    words = " ".join((query or {}).get("q", "").split()) or "Example"
    title = ".".join(w.capitalize() for w in words.split())
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for i, (tag, size, seeders, site, sid, days, flags) in enumerate((
            ("2160p.WEB-DL.DDP5.1.HDR.H.265-EXAMPLE", 14.2e9, 210, "Example Torrents", 1, 3, ["freeleech"]),
            ("1080p.BluRay.x264-SAMPLE", 9.8e9, 88, "Example Torrents", 1, 40, []),
            ("1080p.WEB.H264-MADEUP", 4.1e9, 512, "Harbour Usenet", 2, 1, ["internal"]),
            ("720p.HDTV.x264-OLD", 1.3e9, 4, "Example Torrents", 1, 900, []),
            ("PROPER.1080p.WEB.H264-MADEUP", 4.3e9, 120, "Harbour Usenet", 2, 0, []))):
        rows.append({"guid": f"ex-{i}", "title": f"{title}.{tag}", "protocol": "usenet" if sid == 2 else "torrent", "indexer_id": sid,
                     "indexer": site, "categories": [2000], "size": int(size), "seeders": None if sid == 2 else seeders,
                     "peers": None if sid == 2 else seeders + 12, "grabs": seeders // 3, "publish_date": (now - dt.timedelta(days=days)).isoformat(),
                     "download_url": f"https://example.invalid/get/{i}", "magnet_url": None, "info_url": f"https://example.invalid/release/{i}",
                     "download_volume_factor": 0 if flags else 1, "upload_volume_factor": 1, "indexer_flags": flags})
    return {"releases": rows, "indexers": [
        {"indexer_id": 1, "name": "Example Torrents", "count": 3, "elapsed_ms": 1840, "error": None},
        {"indexer_id": 2, "name": "Harbour Usenet", "count": 2, "elapsed_ms": 920, "error": None},
        {"indexer_id": 3, "name": "Slow Site", "count": 0, "elapsed_ms": 30000, "error": "the site took too long to answer"}]}


def example_reelix(path, query=None):
    """Reelix's own radio and queue answers, with made-up shows."""
    if path == "/indexers/search":
        return example_sites_search(query)
    shows = [{"id": 1, "title": "The Example Hour"}, {"id": 2, "title": "Sample Science Weekly"}] + RADIO_ADDED
    if path == "/radio/library/review":
        added = {a["external_id"] for a in RADIO_ADDED}
        return {"unmatched_shows": [x for x in RADIO_ON_DISK if f"ex-{x['abs_item_id']}" not in added
                                    and x["abs_item_id"] not in example_library.OWN_ADDED],  # own details (DASH-322)
                "unmatched_files": [f for f in RADIO_UNMATCHED if f["id"] not in RADIO_MATCHED],
                "synced_at": today.isoformat() + "T06:00:00Z"}
    if path == "/radio/preview":  # Add a show from a link (DASH-212): any link is a made-up show; one with "nothing" in it is not
        link = (query or {}).get("link", "")
        if "nothing" in link:
            return None
        return {"show": {"provider": "rss", "external_id": link, "title": "The Lighthouse Keepers", "broadcaster": "Example Radio 4",
                         "synopsis": "A made-up show about the people who kept the lights on, for the preview.", "web_url": link,
                         "show_id": next((a["id"] for a in RADIO_ADDED if a["external_id"] == link), None)},
                "series_count": 2, "episode_count": 14, "first_broadcast": "2019-03-04T09:00:00Z",
                "latest_episodes": [{"title": t, "first_broadcast": (today - dt.timedelta(days=7 * n)).isoformat() + "T09:00:00Z", "duration_secs": 1680}
                                    for n, t in enumerate(["Bishop Rock", "Eddystone", "Longships"])]}
    if path == "/radio/rootfolders":
        return [{"id": 1, "path": "/data/media/radio", "kind": "radio", "accessible": True, "unmapped_folders": []}]
    if path == "/radio/search":
        q = (query or {}).get("q", "")
        item = next((x for x in RADIO_ON_DISK if x["title"].lower() == q.lower()), None)
        if not item or item["abs_item_id"] == "li_night":  # one show no source knows
            return []
        return [{"provider": "bbc", "external_id": f"ex-{item['abs_item_id']}", "title": item["title"], "station_name": "Example Radio 4",
                 "episode_count": item["file_count"] + 6},
                {"provider": "apple", "external_id": f"ap-{item['abs_item_id']}", "title": item["title"] + " (podcast)", "author": "A made-up podcast",
                 "episode_count": 40}]
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
                           "media": {"kind": "radio_episode", "id": 101, "title": "Lighthouses", "subtitle": "The Example Hour"}},
                          # a film downloading, for Search's Downloading filter (DASH-301)
                          {"id": 32, "title": "Made.Up.Film.1080p.WEB-DL", "download_client": "qBittorrent", "download_id": "ex32",
                           "state": "downloading", "client_state": "downloading", "progress": 0.6, "size": 4_000_000_000,
                           "remaining": 1_600_000_000, "eta_secs": 900, "messages": [], "added": today.isoformat() + "T08:00:00Z",
                           "media": {"kind": "movie", "id": 10, "title": example_library.FILMS[9]["title"], "year": example_library.FILMS[9]["year"]}}],
                "total": 2, "page": 1, "page_size": 0}
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
    ("Dispatcharr", "link", "Watch and listen", "dispatcharr"),  # set up by Starboard, with its key (DASH-228)
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


# Apps you already run (DASH-249 to 254, DASH-190 to 192): a made-up server set up by hand, with Radarr, Sonarr,
# Prowlarr, Seerr and Profilarr beside Jellyfin, qBittorrent and Gluetun in its own Compose file. The move into Reelix,
# the takeover, Roll back, Keep it and Clear away run as made-up jobs that step through their task lists, so the
# dialog and every stage can be tested. Docker is never called. EXAMPLE_TAKEOVER=1 (on with EXAMPLE_CONTAINERS).
EXAMPLE_TAKEOVER = os.environ.get("EXAMPLE_TAKEOVER", os.environ.get("EXAMPLE_CONTAINERS", "")) == "1"
EXAMPLE_STEP = float(os.environ.get("EXAMPLE_STEP", "0.4"))  # seconds per step of a made-up job
EX = {"taken": False, "record": None, "kept": False, "cleared": []}
OWN = [("radarr", "radarr"), ("sonarr", "sonarr"), ("prowlarr", "prowlarr"), ("seerr", "jellyseerr"), ("profilarr", "profilarr"),
       ("jellyfin", "jellyfin"), ("qbittorrent", "qbittorrent"), ("gluetun", "gluetun")]


def example_takeover():
    import time as _time
    from starboard import reelix_move, reelix_waiting, takeover, tasklist
    names = {k: a["name"] for k, a in stack.APPS.items()}

    def found():
        if EX["taken"]:
            return []
        return [{"name": c, "key": k, "running": True, "project": "media", "service": c, "folder": "/srv/apps",
                 "files": ["/srv/apps/compose.yaml"]} for k, c in OWN]
    takeover.found = found

    def plan(data_dir, install="full", usenet="nzbget", config_dir=None, media_dir=None, check=None, keep_apps=()):
        if EX["taken"]:
            raise ValueError("Starboard found no apps here to take over")
        taken = [c for c in found() if c["key"] in ("jellyfin", "qbittorrent", "gluetun") or c["key"] in keep_apps]
        gone = [c for c in found() if c not in taken]
        return {"install": install, "install_name": stack.INSTALLS[install]["name"], "usenet": usenet, "sab": False,
                "take": [{"name": c["name"], "key": c["key"], "app": names[c["key"]]} for c in taken],
                "replace": [{"name": c["name"], "key": c["key"], "app": names[c["key"]], "by": "Reelix"} for c in gone],
                "leave": [], "new": ["Reelix", "NZBGet", "Bazarr"], "warnings": [], "config_base": "/srv/apps/config",
                "copies": [(f"/srv/apps/config/{c['name']}", f"/srv/media-stack/config/{c['key']}") for c in taken],
                "copy_apps": [f"{names[c['key']]}'s settings" for c in taken],
                "choice": {"config_dir": config_dir or "/srv/media-stack/config", "data_dir": media_dir or "/srv/media",
                           "apps": ["reelix", "nzbget", "bazarr"] + [c["key"] for c in taken],
                           "keep": {"jellyfin": {"port_map": {"8096": 8096}, "devices": ["/dev/dri"]}, "qbittorrent": {"vpn": True}}},
                "containers": taken + gone}
    takeover.plan = plan

    def fake_job(module, kind, items, then=None, notes=(), fail=()):
        tasks = tasklist.Tasks(items)
        with module._lock:
            if module._job and not module._job.get("finished"):
                raise ValueError("Starboard is already changing your apps. Wait until it finishes")
            module._job.clear()
            module._job.update(kind=kind, started=_time.time(), finished=False, ok=None, log="", notes=[], step="Starting")
            module._tasks = tasks

        def go():
            for tid, label in items:
                tasks.start(tid)
                for k in range(2):
                    _time.sleep(EXAMPLE_STEP)
                    tasks.note(tid, f"{k + 1} of 2", now=f"{label}: {k + 1} of 2")
                if tid in fail:
                    tasks.fail(tid, "Made up: this one did not finish")
                else:
                    tasks.done(tid)
            tasks.finish_all()
            out = then() if then else None
            with module._lock:
                module._job.update(finished=True, ok=not fail, ended=_time.time(), notes=list(notes) + list(out or []),
                                   step="Finished")
        threading.Thread(target=go, daemon=True).start()
        return module.job()

    def start(data_dir, host_stack, p, after=None, stamp=None):
        def then():
            EX["taken"] = True
            EX["record"] = {"made": _time.time(), "stamp": "example", "install": p["install"],
                            "containers": [dict(c, rollback_image="example") for c in p["containers"]], "copies": p["copies"]}
            return ["Took Radarr, Sonarr, Prowlarr and Profilarr off your apps"]
        return fake_job(takeover, "takeover", takeover.takeover_tasks(p), then)
    takeover.start = start
    takeover.read_record = lambda data_dir: EX["record"]

    def roll_back(data_dir, host_stack, after=None):
        def then():
            EX.update(taken=False, record=None)
            return ["Your old apps run again as they were before the takeover"]
        return fake_job(takeover, "rollback", takeover.rollback_tasks(EX["record"]), then)
    takeover.roll_back = roll_back

    def keep(data_dir):
        EX.update(record=None, kept=True)
    takeover.clear = keep

    def leftovers(data_dir, inspect=None):
        if not EX["kept"]:
            return None
        done = {c["name"] for c in EX["cleared"]}
        return [{"name": n, "app": names[k], "running": False, "container": False, "settings": [f"/srv/apps/config/{n}"]}
                for k, n in OWN if k in takeover.CLEAR_AWAY and n not in done]
    takeover.leftovers = leftovers
    takeover.cleared = lambda data_dir: EX["cleared"]

    def clear_away(data_dir, host_stack, wanted, after=None, stamp=None):
        items = [it for it in leftovers(data_dir) or [] if it["name"] in set(wanted)]
        if not items:
            raise ValueError("Choose at least one app to clear away")

        def then():
            for it in items:
                EX["cleared"].append({"name": it["name"], "app": it["app"], "from": it["settings"][0],
                                      "to": f"/srv/apps/config/starboard-holding/example/{it['name']}", "at": _time.time()})
            return [f"Cleared away {', '.join(it['app'] for it in items)}"]
        return fake_job(takeover, "clear", takeover.clear_tasks(items) + [("dashboard", "Update your dashboard")], then)
    takeover.clear_away = clear_away

    _host = stack.host_folder

    def host_folder(data_dir):  # the takeover's routes need a folder on the computer; nothing else changes
        f = sys._getframe(1)
        while f:
            if f.f_code.co_name == "api" and str(f.f_locals.get("path", "")).startswith("/api/takeover"):
                return "/example/stack"
            f = f.f_back
        return _host(data_dir)
    stack.host_folder = host_folder

    # The move into Reelix
    sources = [{"source": k, "app": reelix_move.LABELS[k], "container": c, "url": f"http://{c}:1", "api_key": "made-up",
                "networks": ["media_default"], "path_rewrites": []}
               for k, c in (("prowlarr", "prowlarr"), ("radarr", "radarr"), ("sonarr", "sonarr"), ("jellyseerr", "jellyseerr"))]
    reelix_move.sources = lambda: [dict(x) for x in sources] if not EX["taken"] else []
    reelix_move.qbit_conf = lambda container="qbittorrent": {"user": "harbour", "read": True, "ban_minutes": 60,
                                                             "allow_list": ["198.51.100.0/24"]}
    reelix_move.qbit_through_vpn = lambda container="qbittorrent": True  # made up: qBittorrent runs on Gluetun's network
    reelix_move.qbit_sign_in = lambda password, base="", user="admin", opener=None: \
        {"banned": "banned", "wrong": "wrong"}.get(password, "ok")
    # DASH-128: Prowlarr's made-up NZB Harbour hides its key and Starboard "could not read" it, so the preview asks
    # for it by name until it is typed; Prowlarr's other site's key was read from its database.
    def still(x, typed):
        if x["source"] != "prowlarr" or reelix_move.typed_for(x, typed).get("indexer:3:apiKey"):
            return []
        return ["indexer:3:apiKey"]
    reelix_move.preview = lambda base, password, srcs, typed=None, opener=None, docker=None: [
        {"source": x["source"], "app": x["app"], "version": "made up", "notes": [], "still_missing": still(x, typed),
         "needs": [{"id": n, "name": "NZB Harbour", "category": "indexer", "field": "apiKey"} for n in still(x, typed)],
         "filled": 1 if x["source"] == "prowlarr" else 0,
         "counts": {"movie" if x["source"] == "radarr" else "series" if x["source"] == "sonarr" else "indexer": {"create": 12, "existing": 3, "skip": 1}},
         "skipped": [{"name": "Mystery Corner (2009)", "category": "movie", "why": "TMDB isn't configured"}] if x["source"] == "radarr" else []}
        for x in srcs]

    def move_start(data_dir, password, typed=None, hold=True, qbit_password=None, qbit_host=None, srcs=None,
                   qbit_user_name="admin", lookup_urls=None):
        srcs = reelix_move.sources()

        def then():
            result = {"started": _time.time(), "finished": _time.time(), "held": 3,
                      "held_sites": [{"id": 1, "name": "Internet Archive"}, {"id": 2, "name": "1337x"}, {"id": 3, "name": "YTS"}],
                      "apps": [{"source": x["source"], "app": x["app"], "container": x["container"], "state": "finished", "error": None,
                                "counts": {}, "not_moved": []} for x in srcs]}
            for a in result["apps"]:
                if a["source"] == "prowlarr":
                    a["not_moved"] = [{"name": "Knaben", "category": "indexer", "key": "indexer:9",
                                       "why": "Reelix has no definition for knaben; sync indexer definitions and try again"}]
                if a["source"] == "radarr":
                    a["not_moved"] = [{"name": "Mystery Corner (2009)", "category": "movie", "key": "movie:41", "why": "TMDB isn't configured"},
                                      {"name": "The Lost Reel (1998)", "category": "movie", "key": "movie:42", "why": "it has no TMDB id"}]
                if a["source"] == "sonarr":
                    a["not_moved"] = [{"name": "Harbour Lights", "category": "series", "key": "series:7", "why": "TMDB isn't configured"}]
            reelix_move.save_result(data_dir, result)
            entries = [reelix_waiting.entry("Radarr", {"category": "movie", "name": "Mystery Corner (2009)", "key": "movie:41", "why": "TMDB isn't configured"},
                                            {"tmdb": 99001, "imdb": "tt0099001"}),
                       reelix_waiting.entry("Radarr", {"category": "movie", "name": "The Lost Reel (1998)", "key": "movie:42", "why": "it has no TMDB id"},
                                            {"imdb": "tt0099002"}),
                       reelix_waiting.entry("Sonarr", {"category": "series", "name": "Harbour Lights", "key": "series:7", "why": "TMDB isn't configured"},
                                            {"tvdb": 99003, "imdb": "tt0099003"})]
            reelix_waiting._write(data_dir, reelix_waiting.read(data_dir) + entries)  # held without waking the retry
        return fake_job(reelix_move, "move", reelix_move.move_tasks(srcs, hold, bool(qbit_password)), then)
    reelix_move.start = move_start

    def activate(data_dir, password, ids):
        result = reelix_move.last_result(data_dir) or {}
        held = result.get("held_sites") or []
        want = {h["id"] for h in held} if ids is None else set(ids)
        result["held_sites"] = [h for h in held if h["id"] not in want]
        result["held"] = len(result["held_sites"])
        reelix_move.save_result(data_dir, result)
        return len(held) - len(result["held_sites"])
    reelix_move.activate = activate


def main():
    if EXAMPLE_TAKEOVER:
        example_takeover()
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
    _example_plugins(str(DATA))
    _example_livetv(str(DATA))
    _example_keys(str(DATA))
    _example_watch_stats(str(DATA))
    _example_audio_description(str(DATA))
    _example_dispatcharr()
    _example_folders(DATA)
    _example_full_backups()
    _example_copies(DATA)
    if os.environ.get("EXAMPLE_DIRECT_BROKEN") == "1":
        # DASH-218: the full Reelix's YouTube and Spotify downloads as the admin last saw them, with yt-dlp broken and
        # Spotify's sign-in run out, so Apps and System show both warnings with what to do. Off by default.
        from starboard import reelix_direct_health
        reelix_direct_health.record(str(DATA), state={"on": True, "tools": [{"tool": "yt-dlp", "ok": False}, {"tool": "FFmpeg", "ok": True},
                                                                            {"tool": "Spotify session", "ok": False}],
                                                      "spotify": {"connected": False, "problem": ""}})
        rec = reelix_direct_health.read(str(DATA))
        rec["spotify_was_connected"] = True
        reelix_direct_health._write(str(DATA), rec)
    server, app = make_server("127.0.0.1", PORT, str(DATA))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if app.needs_setup:
        password = secrets.token_urlsafe(12)
        (DATA / "password").write_text(password + "\n")
        r, _ = call("POST", "/api/setup", {"token": app.setup_token, "password": password})
        cookie = r.getheader("Set-Cookie").split(";")[0]
        # A short server name, as Settings, General sets it: it starts the top row of the menu (DASH-237).
        call("PUT", "/api/config/general", {"server_name": "Harbour", "setup_guide_done": True}, cookie)  # a set-up server (DASH-238)
        # Audio description ticked in the set-up (DASH-399), so the Plug-ins pages show the offer to install it.
        call("PUT", "/api/config/general", {"extras": {"audio_description": True}}, cookie)
        for name, kind, group, path in APPS:
            url = f"http://127.0.0.1:{FAKE_PORT}/{path}" if path else "http://127.0.0.1:9/"
            call("POST", "/api/services", {"name": name, "type": kind, "group": group, "url": url, "api_key": KEY if kind != "link" or path == "dispatcharr" else "",
                                           "icon": "dispatcharr" if path == "dispatcharr" else ""}, cookie)
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
