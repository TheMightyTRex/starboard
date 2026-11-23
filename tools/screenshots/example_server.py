#!/usr/bin/env python3
"""Starboard with made-up data only, for the README screenshots (tools/screenshots.sh starts it).

Nothing real is read: the folders, drives, apps found on this computer and container access are all
replaced with examples, and made-up apps answer on a second port. Data lives in a temporary folder that is thrown
away. Usage:  python3 tools/screenshots/example_server.py DATA_DIR [PORT]

The apps are the default install (stack.INSTALLS["basics"]): Reelix Lite, Jellyfin, Audiobookshelf, qBittorrent,
NZBGet, Gluetun and Bazarr, so every screenshot shows what a new install has. EXAMPLE_SETUP=existing adds an older
set-up beside them (two Sonarrs and a Radarr), for the help on moving from apps you already run, such as Copy app
settings; tools/screenshots/shoot.mjs adds the same apps for its one Copy app settings picture.
It prints READY when signed-in screenshots can start, and writes a throwaway password to DATA_DIR/password.
"""
import base64
import datetime as dt
import time
import json
import os
import pathlib
import re
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
os.environ["STARBOARD_DISKS"] = ("Media pool=/disks/pool,System disk=/data,Disk 1=/disks/each/1,Disk 2=/disks/each/2,"
                                 "Disk 3=/disks/each/3,Disk 4=/disks/each/4")
from starboard import changes, child, containers, discovery, stack, sysinfo  # noqa: E402
child.ENABLED = os.environ.get("STARBOARD_CHILD_JOBS") == "1"  # heavy jobs in a short-lived process, as the server (DASH-79)
os.environ["EXAMPLE_REELIX_BASE"] = f"http://127.0.0.1:{FAKE_PORT}/reelix"
import example_library  # noqa: E402  (a made-up Reelix library: tools/screenshots/example_library.py)
from starboard.server import make_server  # noqa: E402
from tests.reelix_stand_in import StandIn  # noqa: E402

GB, TB = 1024 ** 3, 1024 ** 4
DISKS = {"Media pool": (24 * TB, 14.2 * TB), "System disk": (0.5 * TB, 0.12 * TB), "Disk 1": (8 * TB, 6.9 * TB),
         "Disk 2": (8 * TB, 4.1 * TB), "Disk 3": (4 * TB, 2.2 * TB), "Disk 4": (4 * TB, 1.0 * TB)}
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
QUEUE_GONE = set()  # downloads removed or ignored in this run (DASH-496)
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
    # A download that needs attention (DASH-496): made-up download folders, read, unpacked and deleted in memory.
    from starboard import queue_files  # noqa: E402
    MB = 1024 * 1024
    FOLDERS = {
        "/data/downloads/complete/Sample.Science.Weekly.3": [("Sample.Science.Weekly.3.par2", 41_000)],
        "/data/downloads/complete/Old.Show.S05E01": [("Old.Show.S05E01.1080p/old.show.s05e01.rar", 95 * MB),
                                                     *[(f"Old.Show.S05E01.1080p/old.show.s05e01.r{n:02d}", 95 * MB) for n in range(14)],
                                                     ("Old.Show.S05E01.1080p/old.show.s05e01.nfo", 2_100)],
        "/data/downloads/torrents/Harbour.Lights.S01E06.1080p.WEB": [("Harbour.Lights.S01E06.1080p.WEB.mkv.exe", 2_480_000),
                                                                    ("Read me to play.txt", 640)],
    }
    UNPACKED = {"/data/downloads/complete/Old.Show.S05E01": ("Old.Show.S05E01.1080p/Old.Show.S05E01.1080p.mkv", 1_380 * MB)}

    def _example_run(container, cmd, user="", timeout=60):
        if cmd[0] == "find" and "-printf" in cmd:
            files = FOLDERS.get(cmd[1])
            if files is None:
                return 1, "", f"find: '{cmd[1]}': No such file or directory\n"
            return 0, "d\t4096\t1000:1000\t\n" + "".join(f"f\t{n}\t1000:1000\t{name}\n" for name, n in files), ""
        if cmd[0] == "sh":
            return 0, "/usr/bin/unrar\n", ""
        if cmd[:2] == ["unrar", "lb"]:
            return 0, "Old.Show.S05E01.1080p.mkv\n", ""
        if cmd[0] == "unrar":
            time.sleep(EXAMPLE_STEP * 4)
            folder = next(k for k in FOLDERS if cmd[-2].startswith(k + "/"))
            if folder in UNPACKED and UNPACKED[folder] not in FOLDERS[folder]:
                FOLDERS[folder].append(UNPACKED[folder])
            return 0, "", ""
        if cmd[0] == "rm":
            gone = set(cmd[3:])
            for k in FOLDERS:
                FOLDERS[k] = [f for f in FOLDERS[k] if f"{k}/{f[0]}" not in gone and k not in gone]
            return 0, "", ""
        if cmd[0] == "find":  # empty folders
            if not FOLDERS.get(cmd[1]):
                FOLDERS.pop(cmd[1], None)
            return 0, "", ""
        return 1, "", "not in the example"
    queue_files.run_in = _example_run
    queue_files.run_helper = lambda container, cmd, user="", timeout=1800: (0, "")
# The apps' own log limit (DASH-451), as Docker reports it on a server whose daemon.json caps every container's log.
from starboard import app_logs  # noqa: E402
app_logs.limits = lambda docker=None, now=None: {"available": True, "driver": "json-file", "max_size": "10m", "max_file": "3",
                                                 "per_app": 30 * 1024 * 1024, "capped": 9, "uncapped": []}
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
_real_fetch_catalogue = plugins_admin.fetch_catalogue


def _offline_catalogue(address, opener=None):
    """Starboard's own collection comes from the copy it ships (plugins/catalogue.json), never from GitHub, so the
    journeys see the same catalogue with or without internet (DASH-411: the Apps you can add group)."""
    if address == plugins_admin.CATALOGUE_URL:
        raise ValueError("Example data: the shipped copy is used")
    return _real_fetch_catalogue(address, opener)


plugins_admin.fetch_catalogue = _offline_catalogue


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


def _example_self_update():
    """Update now (DASH-417): a newer made-up release, and an update that only writes update.sh's lines over a few
    seconds, so Settings, Updates shows Update now and its progress. Nothing is fetched, built or restarted."""
    from starboard import server as server_mod, self_update
    major, minor, _ = (int(x) for x in (REPO / "VERSION").read_text().strip().split("."))
    newer = f"v{major}.{minor + 1}.0"
    def latest_release(self):  # remembered as the real check does, so the side menu's update dot shows
        self._latest.update(tag=newer, checked=time.time())
        return newer
    server_mod.App.latest_release = latest_release
    # What is new for the made-up release (DASH-462): its changelog at its tag, without reaching GitHub.
    from starboard import changes as changes_mod
    real_fetch = changes_mod._fetch
    made_up = f"""# Changelog

## [{newer[1:]}] (18 November 2026)

### Added
- **Check for updates:** Settings, Updates asks every part for new versions when you choose.

### Changed
- **Install all updates:** Shown when one update or more is ready.

### Fixed
- **Release notes:** Dates are written out in full.

### Security
- **Checks:** Every scanner ran and found nothing to fix.
"""
    changes_mod._fetch = lambda url: changes_mod.parse(made_up) if url.endswith(f"/{newer}/CHANGELOG.md") else real_fetch(url)
    self_update.plan = lambda data_dir, root: {"how": "native", "folder": str(REPO)}

    def launch(p, to):
        lines = ["== Fetching releases", f"Available: {to}", "== Backing up your settings", f"== Installing {to}",
                 f"== Building {to}", "== Restarting Starboard", "== Checking that Starboard answers", f"== Updated to {to}",
                 "@@ finished 0"]

        def write():
            for line in lines:
                time.sleep(0.6)
                with open(DATA / self_update.LOG, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        threading.Thread(target=write, daemon=True).start()
    self_update.launch = launch


def _example_updates(data):
    """Settings, Updates (DASH-420, DASH-422): recent updates (one by itself, one went back, one Roll back by hand),
    the apps' last automatic look, and a newer Playback Reporting for Jellyfin's Update plugins task. Nothing real
    is updated: the runs are only written down."""
    import time as _t
    now = _t.time()
    runs = [
        {"id": "a1b2c3d4e5f6", "target": "app:sonarr", "kind": "app", "name": "Sonarr", "action": "update", "from": "4.0.10", "to": "4.0.11",
         "by": "automatic", "started": now - 26 * 3600, "finished": now - 26 * 3600 + 95, "state": "updated", "said": "Sonarr is updated and running",
         "steps": [{"id": "backup", "label": "Saving a copy of its settings", "state": "done", "detail": "sonarr-before-update.tgz, beside its Compose file"},
                   {"id": "install", "label": "Getting and installing the new version", "state": "done", "detail": "4.0.11"},
                   {"id": "health", "label": "Waiting for it to run", "state": "done", "detail": "It is running"}]},
        {"id": "b2c3d4e5f6a1", "target": "reelix", "kind": "reelix", "name": "Reelix", "action": "update", "from": "0.7.0", "to": "0.7.1",
         "by": "you", "started": now - 5 * 3600, "finished": now - 5 * 3600 + 340, "state": "went-back",
         "said": "Reelix's new version was not healthy; Starboard went back to the previous one",
         "steps": [{"id": "health", "label": "Waiting for it to answer healthy", "state": "failed", "detail": "It did not answer healthy within 5 minutes"}]},
        {"id": "c3d4e5f6a1b2", "target": "plugin:watch-stats", "kind": "plugin", "name": "Watch statistics", "action": "rollback", "from": "1.2.0", "to": "1.1.0",
         "by": "you", "started": now - 2 * 3600, "finished": now - 2 * 3600 + 20, "state": "rolled-back", "said": "Watch statistics is back on 1.1.0, with your settings as they were",
         "steps": []},
    ]
    (data / "update-runs.json").write_text(json.dumps(runs))
    (data / "auto-updates.json").write_text(json.dumps({"last": {"apps": {"day": dt.date.today().isoformat(), "at": now - 26 * 3600,
                                                                          "runs": [{"name": "Sonarr", "from": "4.0.10", "to": "4.0.11", "state": "updated", "said": ""}]}}}))
    JELLYFIN.updates[jellyfin_plugins.PACKAGES["playback"]["guid"].replace("-", "")] = "20.0.0.0"


def _example_update_all():
    """Install all updates (DASH-454): each update of the batch only acts its steps over a few seconds (nothing is
    fetched, installed or restarted), except Starboard's own, which writes update.sh's lines as Update now does, and
    Jellyfin's plug-ins, which the stand-in Jellyfin updates and restarts. With EXAMPLE_UPDATE_ALL=1, more updates
    wait: Sonarr (which goes back by itself), Reelix, Radarr 6 (a big change, held back) and Watch statistics (asks
    for new permissions, held back)."""
    from starboard import update_batch, update_runs
    real_targets, real_start, real_hold = update_runs.targets, update_runs.start, update_batch._plugin_hold
    more = os.environ.get("EXAMPLE_UPDATE_ALL") == "1"

    def targets(app):
        out = real_targets(app)
        if not more:
            return out
        for t in out:
            if t["id"] == "reelix":
                t.update(update_available=True, can_update=True, latest="0.7.2", why="")
            if t["id"] == "plugin:watch-stats":
                t.update(update_available=True, can_update=True, latest="1.1.0", why="")
        app_row = lambda tid, name, cur, new, big: {"id": tid, "kind": "app", "name": name, "current": cur, "latest": new,  # noqa: E731
                                                    "update_available": True, "can_update": True, "why": "", "can_roll_back": False,
                                                    "roll_back_to": "", "big_change": big, "note": "Goes back by itself when the new version is not healthy"}
        return out[:1] + [app_row("app:sonarr", "Sonarr", "4.0.11", "4.0.12", False), app_row("app:radarr", "Radarr", "5.14.0", "6.0.0", True)] + out[1:]

    def hold(app, t, known):
        if t["id"] == "plugin:watch-stats":
            return "It asks for new permissions (jellyfin:write). Update it on its own page"
        return real_hold(app, t, known)

    def start(app, target, by="you", address="", note=None, batch=None):
        if not batch or target == "starboard":
            return real_start(app, target, by=by, address=address, note=note, batch=batch)
        t = next(x for x in update_runs.targets(app) if x["id"] == target)
        steps = [("backup", "Saving a copy of its settings"), ("install", "Installing the new version"), ("health", "Checking it works")]
        run = update_runs._new(app.data_dir, target, t["kind"], t["name"], "update", t["current"], t["latest"], by, steps)

        def work():
            for k, _ in steps:
                update_runs._step(app.data_dir, run, k, "now")
                time.sleep(1.5)
                if target == "app:sonarr" and k == "health":
                    update_runs._step(app.data_dir, run, k, "failed", "It kept stopping and starting again within 2 minutes")
                    update_runs._step(app.data_dir, run, "going-back", "now")
                    time.sleep(1)
                    update_runs._step(app.data_dir, run, "going-back", "done")
                    return update_runs._end(app.data_dir, run, "went-back", "Sonarr's new version kept stopping and starting again within 2 minutes, "
                                            "so Starboard went back to the version before", app)
                update_runs._step(app.data_dir, run, k, "done")
            update_runs._end(app.data_dir, run, "updated", f"{t['name']} is updated and running", app)
        update_runs._go(app.data_dir, run, work)
        return run
    update_runs.targets, update_runs.start, update_batch._plugin_hold = targets, start, hold
    if os.environ.get("EXAMPLE_UPDATE_ALL_DONE") == "1":  # a batch that ended ten minutes ago, so the page opens with its panel
        now = time.time()
        steps = [("app:sonarr", "Sonarr 4.0.11 to 4.0.12", "went-back", "Sonarr's new version kept stopping and starting again within 2 minutes, so Starboard went back to the version before"),
                 ("jellyfin-plugins", "Jellyfin's plug-ins", "done", "Updated: Playback Reporting 19.0.0.0 to 20.0.0.0"),
                 ("plugin:picture-shrinker", "Picture shrinker 1.0.0 to 1.1.0", "done", "Picture shrinker is updated"),
                 ("reelix", "Reelix 0.7.1 to 0.7.2", "done", "Reelix is updated and running"),
                 ("starboard", "Starboard 0.19.1 to 0.20.0", "done", "Starboard is updated to 0.20.0"),
                 ("app:radarr", "Radarr 5.14.0 to 6.0.0", "held", "Version 6.0.0 is a big change. Read what is new and update it on its own"),
                 ("plugin:watch-stats", "Watch statistics 1.0.0 to 1.1.0", "held", "It asks for new permissions (jellyfin:write). Update it on its own page")]
        batch = {"id": "d4e5f6a1b2c3", "target": "all", "kind": "batch", "name": "All updates", "action": "update", "from": "", "to": "4 updates",
                 "by": "you", "started": now - 900, "finished": now - 600, "state": "some-updated",
                 "said": "4 of 5 updated. Went back by itself: Sonarr. Held back for you: Radarr, Watch statistics",
                 "items": [{"target": k, "name": label.split(" ")[0] if k.startswith("app:") else label} for k, label, _, _ in steps],
                 "steps": [{"id": k, "label": label, "state": st, "detail": d} for k, label, st, d in steps]}
        path = DATA / "update-runs.json"
        path.write_text(json.dumps(json.loads(path.read_text()) + [batch]))


def _example_saved_copies(data):
    """Settings, Restore, and System, Backup and restore, Copies Starboard saved: two made-up copies of the settings, one
    made before an update changed them and one before a restore, so the list the help describes has something in it."""
    import shutil
    from starboard import config as settings_config
    folder = os.path.join(str(data), "backups")
    source = os.path.join(str(data), "config.json")
    if not os.path.exists(source):
        return
    os.makedirs(folder, mode=0o700, exist_ok=True)
    versions = {}
    for days, reason, version in ((9, "before-migration", "0.25.0"), (3, "before-restore", "0.26.0")):
        when = dt.datetime.now() - dt.timedelta(days=days)
        name = f"config-{when:%Y-%m-%d-%H%M%S}-{reason}.json"
        shutil.copy2(source, os.path.join(folder, name))
        os.utime(os.path.join(folder, name), (when.timestamp(), when.timestamp()))  # the list says when each was made
        versions[name] = version
    settings_config._write_versions(folder, versions)


def _example_full_backups():
    """System, Backup and restore, Full without media (DASH-260): the media folder on its own disk, so the page says
    which disk the copies go on, and two made-up copies in the folder. Nothing is read from this computer."""
    from starboard import full_backup
    full_backup._drives = lambda data_dir: [{"mount": "/srv/media", "device": "sdb1", "size": 4000 * 1000 ** 3, "fs": "ext4",
                                             "model": "WDC WD40EFRX", "label": ""}]
    apps = ["audiobookshelf", "bazarr", "gluetun", "jellyfin", "nzbget", "qbittorrent", "reelix"]
    day = dt.datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)
    full_backup.found = lambda folder: [
        {"name": f"starboard-full-{d:%Y-%m-%d-%H%M%S}.starboard", "path": f"{folder}/starboard-full-{d:%Y-%m-%d-%H%M%S}.starboard",
         "size": 640 * 1000 ** 2 + n * 3 * 1000 ** 2, "created": d.isoformat(timespec="seconds"), "version": "0.15.0", "pictures": False,
         "apps": apps, "site_name": "Harbour", "config_dir": "/srv/media-stack/config"}
        for n, d in enumerate(day - dt.timedelta(days=7 * k) for k in range(2))]
    # Each copy is checked after it is made (DASH-381): the newest here read back as written; the older one was
    # made before Starboard checked, so it has no mark.
    newest = full_backup.found("/x")[0]
    (DATA / full_backup.CHECKED).write_text(json.dumps({newest["name"]: {"size": newest["size"], "at": day.timestamp() + 95}}))

    # Restore on this server (DASH-387): nothing is restored here. The made-up backup password is "made-up backup";
    # another is refused as the real one is. The steps pass in a few seconds, then it says it finished.
    def start_restore(data_dir, version, file_path, password, apply_settings, site_name=""):
        if password != "made-up backup":
            raise full_backup.BackupError("That password does not open this backup")
        made = next((b["created"] for b in full_backup.found(os.path.dirname(file_path)) if b["path"] == file_path), None)
        safety = f"{os.path.dirname(file_path)}/starboard-full-{dt.datetime.now():%Y-%m-%d-%H%M%S}.starboard"
        full_backup._tell(data_dir, state="running", step="Making a full backup of how things are now", started=time.time(), finished=None, error="",
                          file=file_path, safety="", stopped=[], created=made, apps=[], count=None)

        def steps():
            for step in ("Stopping the apps", "Putting the backup back", "Starting the apps again"):
                time.sleep(1.2)
                full_backup._tell(data_dir, step=step, safety=safety)
            time.sleep(1.2)
            full_backup._tell(data_dir, state="done", step="", finished=time.time(), apps=apps, count=len(apps))
        threading.Thread(target=steps, daemon=True).start()
    full_backup.start_restore = start_restore


def _example_reelix_backup_place():
    """Where Reelix keeps its backups (DASH-386): its settings on the system disk and the media folder on its own
    disk, so the choice is offered. Choosing is remembered while the example server runs; nothing is moved."""
    from starboard import reelix_backup_place as rbp
    kept = {"chosen": "settings", "now": "settings"}
    choices = [{"key": "settings", "folder": "/srv/media-stack/config/reelix/backups", "disk": "the system disk", "system": True, "mount": "/"},
               {"key": "media", "folder": "/srv/media/backups/reelix", "disk": "WDC WD40EFRX", "system": False, "mount": "/srv/media"}]
    rbp.place = lambda data_dir, running_folder: {**kept, "restart": kept["now"] != kept["chosen"], "choices": choices, "other": "", "same_disk": False}

    def choose(data_dir, key, backups, restore_waiting, run_in=None):
        if key not in rbp.PLACES:
            raise ValueError("Choose next to Reelix's settings or the media folder")
        kept["chosen"] = key
        return "Reelix keeps its backups " + ("next to its settings" if key == "settings" else "in the media folder") + " from its next start"
    rbp.choose = choose


def _example_tdarr():
    """Tdarr's settings (DASH-306), on Settings, Tdarr and on the Tdarr plug-in page's Settings topic: made-up answers
    as Tdarr gives them, kept while the example server runs. Nothing is sent anywhere."""
    from starboard import tdarr
    have = {"libraries": {"films": True, "series": True}, "mode": "save_space", "at_once": 1, "night": True, "node": "starboard",
            "files": 4210, "converted": 318, "checked": 4196, "saved_gb": 612.4, "other_libraries": ["TV"],
            "quiet_hours": "01:00 to 06:00", "quiet_from_download_hours": False}
    tdarr.state = lambda cfg: dict(have)

    def save(cfg, choice):
        have.update({"mode": choice.get("mode", have["mode"]), "at_once": int(choice.get("at_once", 1)),
                     "night": bool(choice.get("night")), "libraries": choice.get("libraries") or have["libraries"]})
        return {"state": dict(have), "done": ["Saved"]}
    tdarr.save = save


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
    # Test connection (DASH-452) answers with every check done, 1.8 TB free and 5 backups there.
    backup_copies._helper = lambda script, binds, image=None, network="none", volumes=(), timeout=7200: (
        0, "STEP-FOLDER\nSTEP-WRITE\nSTEP-READ\nSTEP-REMOVE\nFREE 1979120929996\nCOUNT 5\n")
    backup_copies.newest = lambda data_dir: str(data / "example-computer" / "mnt" / "disk2" / "backups" / "starboard-full-2026-11-13-030000.starboard")
    backup_copies.newest_size = lambda data_dir: 412 * 1024 ** 2
    real_test = backup_copies.test

    def test(data_dir):  # the example server has no Docker: the stand-in helper above answers instead
        was, folder = containers.available, stack.host_folder
        containers.available = lambda: True
        stack.host_folder = lambda d: str(data / "stack")  # where Starboard's folder would be, for a cloud place's config
        try:
            return real_test(data_dir)
        finally:
            containers.available, stack.host_folder = was, folder
    backup_copies.test = test
    _example_cloud(data)


def _example_cloud(data):
    """Connect a cloud service (DASH-452) with stand-ins only: no real sign-in, no Docker. Complete on the phone talks
    to tests/oauth_stand_in.py on PORT + 2 (open /device/approve?user_code=... there to approve, as a phone would), with
    the page shown as Google's or Microsoft's; Complete in this browser shows a made-up sign-in link, and any address
    pasted back with its state signs in after a second. The folders and the test answer as a real service would."""
    from starboard import cloud_connect as cc
    from tests.oauth_stand_in import StandIn
    os.environ.setdefault("STARBOARD_GOOGLE_CLIENT_ID", "example.apps.example")
    os.environ.setdefault("STARBOARD_GOOGLE_CLIENT_SECRET", "example")
    os.environ.setdefault("STARBOARD_MICROSOFT_CLIENT_ID", "example-microsoft")
    svc = StandIn("127.0.0.1", PORT + 2).start()
    b = svc.base
    cc.TEST_HOOK = {"device": {"drive": {"code": b + "/device/code", "token": b + "/token", "pages": ("www.google.com",)},
                               "onedrive": {"code": b + "/device/code", "token": b + "/token", "pages": ("microsoft.com",)}},
                    "graph": b + "/me/drive", "hosts": ()}
    real_http = cc._http

    def http(url, form=None, headers=None):
        status, got = real_http(url, form, headers)
        if url.endswith("/device/code") and status == 200:  # shown as the service's own page
            google = "googleapis" in (form or {}).get("scope", "")
            got["verification_uri"] = "https://www.google.com/device" if google else "https://microsoft.com/devicelogin"
        return status, got
    cc.HTTP = http

    class Runner:
        def authorize(self, sess):
            state = secrets.token_urlsafe(16)
            sess["cid"] = "example-signin"
            link = {"drive": f"https://accounts.google.com/o/oauth2/auth?access_type=offline&client_id=example&redirect_uri=http%3A%2F%2F127.0.0.1%3A53682%2F&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file&state={state}",
                    "onedrive": f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=example&redirect_uri=http%3A%2F%2Flocalhost%3A53682%2F&response_type=code&state={state}",
                    "dropbox": f"https://www.dropbox.com/oauth2/authorize?client_id=example&redirect_uri=http%3A%2F%2Flocalhost%3A53682%2F&response_type=code&state={state}"}[sess["service"]]
            work = sess["work"]
            (pathlib.Path(work) / "link").write_text(link + "\n")

            def listen():  # rclone's listener: an answer, then the token a second later
                until = time.time() + cc.SIGNIN_LIMIT
                while time.time() < until and os.path.isdir(work):
                    if os.path.exists(os.path.join(work, "answer")):
                        time.sleep(1)
                        tok = {"access_token": "standin-example", "token_type": "Bearer", "refresh_token": "r", "expiry": "2026-11-16T12:00:00Z"}
                        (pathlib.Path(work) / "out").write_text("Paste the following into your remote machine --->\n" + json.dumps(tok) + "\n<---End paste\n")
                        (pathlib.Path(work) / "done").write_text("0")
                        return
                    time.sleep(0.3)
            threading.Thread(target=listen, daemon=True).start()

        def short(self, sess, script, work):
            if "config create" in script:
                (pathlib.Path(work) / "rclone.conf").write_text(f"[{cc.REMOTE}]\ntype = {sess['service']}\n")
                return 0, ""
            if "lsf --dirs-only" in script:
                return 0, "Documents/\nPhotos/\nstarboard-backups/\n"
            return 0, "STEP-FOLDER\nSTEP-WRITE\nSTEP-READ\nSTEP-REMOVE\nFREE 1979120929996\n"

        def remove(self, cid):
            pass
    cc.RUN = Runner()


def _example_folders(data):
    """The folder picker (DASH-240) browses a made-up tree, never this computer's own folders."""
    from starboard import folders
    root = data / "example-computer"
    for d in ("mnt/disk1/media/movies", "mnt/disk1/media/tv", "mnt/disk1/media/books", "mnt/disk2/backups", "mnt/pool/media",
              "srv/media/downloads", "srv/apps/config", "home/sam/media"):
        (root / d).mkdir(parents=True, exist_ok=True)
    folders.ROOTS = tuple(str(root / r) for r in ("mnt", "media", "srv", "home"))
    _example_bring_in(data, root)


GB_ = 10 ** 9
# Bring in media (DASH-455): made-up media on an old disk, in a home folder and on a pretend network share. The files
# are sparse (no space used), so sizes look real. The share is read from a folder here; nothing is mounted.
BRING_IN_FILES = {
    "mnt/disk2/Old media/Films/Harbour.Lights.2019.1080p.BluRay.x264/Harbour.Lights.2019.1080p.BluRay.x264.mkv": 9.2,
    "mnt/disk2/Old media/Films/Harbour.Lights.2019.1080p.BluRay.x264/Harbour.Lights.2019.1080p.BluRay.x264.en.srt": 0.0001,
    "mnt/disk2/Old media/Films/Harbour.Lights.2019.1080p.BluRay.x264/Sample/sample.mkv": 0.05,
    "mnt/disk2/Old media/Films/Harbour.Lights.2019.1080p.BluRay.x264/RARBG.txt": 0.000001,
    "mnt/disk2/Old media/Films/The Long Field (2021)/The Long Field (2021).mkv": 14.1,
    "mnt/disk2/Old media/Films/The Long Field (2021)/poster.jpg": 0.0004,
    "mnt/disk2/Old media/Films/Paper.Planets.2017.720p.WEB-DL.mp4": 3.4,
    "mnt/disk2/Old media/Films/Tidewater.mkv": 7.7,
    "mnt/disk2/Old media/TV/Copper Valley (2018)/Season 1/Copper.Valley.S01E01.1080p.mkv": 2.1,
    "mnt/disk2/Old media/TV/Copper Valley (2018)/Season 1/Copper.Valley.S01E02.1080p.mkv": 2.2,
    "mnt/disk2/Old media/TV/Copper Valley (2018)/Season 1/Copper.Valley.S01E03.1080p.mkv": 2.0,
    "mnt/disk2/Old media/TV/Saltmarsh/Season 2/Saltmarsh - 2x01.mkv": 1.4,
    "mnt/disk2/Old media/TV/Saltmarsh/Season 2/Saltmarsh - 2x02.mkv": 1.5,
    "mnt/disk2/Old media/Music/Midnight Garden/First Light/01 Morning.flac": 0.04,
    "mnt/disk2/Old media/Music/Midnight Garden/First Light/02 Harbour Wall.flac": 0.05,
    "mnt/disk2/Old media/Music/Midnight Garden/First Light/cover.jpg": 0.0003,
    "mnt/disk2/Old media/Thumbs.db": 0.00001,
    "home/sam/Videos/Glass Orchard 2015.mkv": 6.3,
    "home/sam/Videos/Northern.Line.2023.2160p.mkv": 21.5,
    "home/sam/Videos/Paper Planets (2017).mkv": 3.4,
    "home/sam/Books/Alex Rivers/The Quiet Coast.epub": 0.002,
    "home/sam/Audiobooks/Sam Harper/Winter Map/Winter Map.m4b": 0.4,
    "srv/share-example/Kids/Little Lanterns/Season 1/Little.Lanterns.S01E01.mkv": 0.9,
    "srv/share-example/Kids/Little Lanterns/Season 1/Little.Lanterns.S01E02.mkv": 0.9,
    "srv/share-example/Films/Quiet.Coast.2010.1080p.mkv": 8.8,
    "media/usb/Backup of phone/IMG_0001.jpg": 0.003,
}


def _example_bring_in(data, root):
    from starboard import bring_in, folders as fo
    for rel, gb in BRING_IN_FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.truncate(int(gb * GB_))  # sparse: the size shows, no space is used
    (root / "srv/media/media/movies").mkdir(parents=True, exist_ok=True)
    fo.disk_places = lambda: [{"name": "Disk 2", "path": str(root / "mnt/disk2")}, {"name": "USB disk", "path": str(root / "media/usb")}]
    # The example tree lives in a throwaway folder: names show as this computer would show them (/mnt/disk2...).
    real_describe, real_places = bring_in.describe, fo.places
    bring_in.describe = lambda s: real_describe(s).replace(str(root), "")
    fo.places = lambda data_dir=None, purpose="": [{**p, "detail": p["detail"].replace(str(root), "")} for p in real_places(data_dir, purpose)]
    share = root / "srv/share-example"
    real_listing = bring_in.listing

    def listing(data_dir, s, run=None):
        if s["kind"] in ("smb", "nfs"):
            return bring_in._walk(str(share) + s["path"])
        return real_listing(data_dir, s, run)

    def share_browse(data_dir, sid, rel, run=None):
        rel = bring_in._rel(rel)
        here = share / rel.strip("/")
        names = sorted(n.name for n in here.iterdir() if n.is_dir()) if here.is_dir() else []
        parts = [x for x in rel.split("/") if x]
        return {"path": rel, "place": f"share:{sid}", "parent": "/".join(rel.split("/")[:-1]) if rel else None,
                "crumbs": [{"name": "//192.0.2.20/media", "path": ""}] + [{"name": x, "path": "/" + "/".join(parts[:i + 1])} for i, x in enumerate(parts)],
                "folders": [{"name": n, "path": f"{rel}/{n}"} for n in names], "free": None, "total": None, "why": ""}
    bring_in.listing = listing
    real_prints = bring_in._prints

    def prints(data_dir, s, rels, run=None):
        if s["kind"] in ("smb", "nfs"):
            return {r: bring_in._quick_print(str(share) + s["path"] + "/" + r) for r in rels}
        return real_prints(data_dir, s, rels, run)
    bring_in._prints = prints
    bring_in._free = lambda media: int(9.8 * 10 ** 12)  # the made-up media pool's free space, as Storage shows it
    bring_in.share_browse = share_browse
    bring_in.share_sizes = lambda data_dir, sid, rel, run=None: fo.group_sizes(bring_in._walk(str(share / bring_in._rel(rel).strip("/"))))
    if os.environ.get("EXAMPLE_BRING_IN_EMPTY") != "1":
        bring_in.save_sources(str(data), [{"kind": "disk", "path": str(root / "mnt/disk2/Old media")},
                                          {"kind": "computer", "path": str(root / "home/sam")},
                                          {"kind": "smb", "address": "//192.0.2.20/media", "user": "sam", "path": ""}],
                              media=str(root / "srv/media"))


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


def _example_signin(app):
    """Sign-in methods (DASH-512): single sign-on set up with made-up provider details and tested (nothing is called: the
    pictures never press Test sign-in), and two stand-ins so the pictures can show the whole set-up: the password
    "example-password" is taken for the changes in Settings, Security, Sign-in, and the code 123456 is a right code."""
    from starboard import server as _server, totp as _totp
    app.config.data["auth"]["oidc"] = {
        "enabled": False, "name": "Authentik", "issuer": "https://auth.example.org/application/o/starboard/", "client_id": "starboard",
        "client_secret": "made-up-client-secret", "redirect_uri": f"http://127.0.0.1:{PORT}/api/oidc/callback", "scopes": "openid email",
        "claim": "email", "value": "you@example.org", "tested": True}
    app.config.save()
    real = _server.Handler.check_password

    def check_password(self, data):
        if data.get("password") == "example-password":
            return None
        return real(self, data)
    _server.Handler.check_password = check_password
    real_verify = _totp.verify
    _totp.verify = lambda secret, code, last_step=0, now=None: (int(time.time() // 30) + 1 if str(code).strip() == "123456" else real_verify(secret, code, last_step, now))

def _example_transcode():
    """Hardware video conversion check (DASH-515): the real check, with a made-up Jellyfin container whose answers are
    written here, so the help's pictures show a chip where VAAPI works and Quick Sync does not. Nothing runs."""
    from starboard import transcode_check
    real = transcode_check.check
    probe = ("FFMPEG=/usr/lib/jellyfin-ffmpeg/ffmpeg\nVERSION=ffmpeg version 7.1.1-Jellyfin\nDRI=yes\n"
             "NODE=/dev/dri/renderD128 gid=105 access=ok vendor=0x8086\nNVIDIA=\nGROUPS=1000 44 105\n"
             "ENC=h264_qsv\nENC=h264_vaapi\nENC=libx264\n")

    def answer(script):
        if "FFMPEG=" in script:
            return 0, probe
        if "h264_qsv" in script:
            return 1, "[h264_qsv] Error creating a MFX session: -9.\nDevice creation failed: -1313558101."
        return 0, ""
    transcode_check.check = lambda services, **k: real(
        services, listing=[{"id": "j1", "name": "jellyfin"}], inspect=lambda n: {"State": {"Running": True}, "Config": {"Env": ["PUID=1000"]}},
        exec_fn=answer)


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


def _example_app_plugins(data_dir):
    """App plug-ins (plug-in API 1.13, DASH-411): Jellystat active with its page on the home network at port 3000, and
    Tdarr added but not active, offering to copy the Tdarr the main install runs. Nothing is started."""
    base = {"manifest_version": 1, "author": "TheMightyTRexUK", "licence": "MIT", "starboard_api": ">=1.13 <2.0"}
    if not any(p["id"] == "jellystat" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {**base, "id": "jellystat", "name": "Jellystat", "version": "1.0.0",
            "description": "Jellystat, the full watch statistics app for Jellyfin, with its own database.",
            "homepage": "https://example.invalid/jellystat", "support_url": "https://example.invalid/jellystat/issues",
            "permissions": ["jellyfin:key", "network:lan", "network:port"],
            "containers": [{"name": "app", "image": "ghcr.io/example/jellystat@sha256:" + "d" * 64, "port": 3000, "network": "lan",
                            "publish": True, "host_port": 3000, "volumes": ["data:/app/backend/backup-data"],
                            "env": {"POSTGRES_PASSWORD": "{secret:db_password}"}},
                           {"name": "db", "image": "ghcr.io/example/postgres@sha256:" + "e" * 64, "port": 5432, "user": "70:70",
                            "volumes": ["data"], "tmpfs": ["/var/run/postgresql"], "env": {"POSTGRES_PASSWORD": "{secret:db_password}"}}]},
            "/nonexistent-media")
        st_path = os.path.join(plugins_admin.folder(data_dir, "jellystat"), "state.json")
        st = plugins_admin._read(st_path, {})
        st.update(state="enabled", ports={"app": 3000})
        plugins_admin._write(st_path, st)
    if not any(p["id"] == "tdarr" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {**base, "id": "tdarr", "name": "Tdarr", "version": "1.0.0",
            "description": "Tdarr converts your films and series to save space, in quiet hours.",
            "homepage": "https://example.invalid/tdarr", "support_url": "https://example.invalid/tdarr/issues",
            "permissions": ["network:lan", "network:port"],
            "containers": [{"name": "server", "image": "ghcr.io/example/tdarr@sha256:" + "f" * 64, "port": 8265, "network": "lan",
                            "publish": True, "host_port": 8265, "volumes": ["data/server:/app/server", "data/configs:/app/configs",
                                                                            "media/movies", "media/tv"]}],
            "adopt": {"app": "tdarr", "name": "Tdarr", "into": "server", "stop": True,
                      "copy": {"/app/server": "server", "/app/configs": "configs"}}}, "/nonexistent-media")


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
                         {"key": "days", "label": "Over the last", "type": "number", "unit": "days", "default": 30, "min": 1, "max": 365}],
            # No logo, so its card band shows its initials (plug-in API 1.14, DASH-428)
            "cards": [{"id": "week", "title": "Watched this week", "type": "stat", "path": "/card/week", "format": "number"}]},
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
            "actions": [{"id": "test-telegram", "label": "Send a test to Telegram", "path": "/test/telegram",
                         "confirm": "Sends a test message to your Telegram chat now. Continue?"}],  # DASH-441
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
    real_answer = plugin_cards.answer

    def answer(d, pid, cid, opener=None):  # its card, with a time and no status: the band shows only when it updated
        if pid != "watch-stats":
            return real_answer(d, pid, cid, opener)
        return {"type": "stat", "format": "number", "asked": int(time.time()),
                "data": plugin_cards.clean("stat", {"value": 42, "label": "hours watched", "note": "Up 6 hours on last week",
                                                     "updated": int(time.time()) - 600})}
    plugin_cards.answer = answer
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


# Direct play (DASH-425, plug-in API 1.14): the example plug-in added and active, with made-up progress, so its card
# (converting now, next up and the totals, every 10 seconds here) and its Files table show. Its card answers go
# through Starboard's own card code with a stand-in for the container, so the 10-second floor is the real one: the
# Space saved card asks for 2 seconds and is held to 10. Nothing is converted and no container starts.
_DP_NEXT = [("Slow Horses, series 1 episode 3", "Add a playable sound track"), ("Brazil (1985)", "Repackage as MKV"),
            ("Paddington 2 (2017)", "Shrink"), ("Bluey, series 2 episode 7", "Convert to H.264")]
_DP_ASKED = {"now": 0, "saved": 0}


# Direct play's logo (plug-in API 1.14, DASH-428): a play symbol on a screen, as its starboard-plugin.json names it.
_DP_LOGO = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><title>Direct play</title>'
            b'<rect x="0" y="0" width="24" height="24" rx="4" fill="#0b5f5a"/>'
            b'<rect x="4" y="5" width="16" height="11" rx="1.5" fill="none" stroke="#ffffff" stroke-width="1.8"/>'
            b'<path d="M10.5 8v5l4-2.5z" fill="#ffffff"/><path d="M8.5 19h7" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round"/></svg>')


def _dp_card(cid, every):
    _DP_ASKED[cid] += 1
    if cid == "saved":
        return {"value": 1030000000000, "label": "saved", "note": "1,173 files fixed, 40 files to do", "refresh_seconds": 2,
                "status": "done", "status_label": "All checked"}
    pct = (34 + _DP_ASKED["now"]) % 100
    # The card band (API 1.14): converting, and when the conversion last moved on
    return {"refresh_seconds": every, "status": "converting", "updated": int(time.time()) - 30, "items": [
        {"title": "Converting now: Dune (2021)", "detail": f"Shrink, {pct}% done, about 1 hour 5 minutes left"},
        *[{"title": f"Next: {t}", "detail": d} for t, d in _DP_NEXT],
        {"title": "Totals", "detail": "1,173 files fixed, 1.03 TB saved, 40 files still to do"}]}


def _dp_screen():
    rows = [("Dune (2021)", "Converting now", "Shrink", "31.4 Mbps", "38.2 GB")] + [(t, "Still to do", d, "sound is DTS" if "sound" in d else "example", "4.1 GB") for t, d in _DP_NEXT]
    rows += [("The Bear, series 1 episode 1", "Left alone", "Left alone", "HEVC: left alone, Jellyfin converts it as it plays", "1.2 GB")]
    return {"type": "list", "title": "Files", "layout": "folds", "readonly": True,
            "intro": "1,173 files fixed, 1.03 TB saved, 40 files still to do. This is example data.",
            "columns": [{"key": "title", "label": "Title"}, {"key": "needs", "label": "What it needs"}, {"key": "why", "label": "Why"},
                        {"key": "size", "label": "Size"}],
            "filters": [{"key": "needs", "label": "What it needs"}],
            "notices": [{"id": "now", "tone": "info", "title": "Converting Dune (2021)", "text": "Shrink, about 1 hour 5 minutes left", "progress": 34}],
            "items": [{"id": f"r{i}", "title": t, "group": g, "actions": [], "cells": {"title": t, "needs": n, "why": w, "size": z}}
                      for i, (t, g, n, w, z) in enumerate(rows)]}


def _example_direct_play(data_dir):
    from starboard import plugin_cards, plugin_custom, plugin_watch
    if not any(p["id"] == "direct-play" for p in plugins_admin.listing(data_dir)):
        sw = lambda key, label, on=False: {"key": key, "label": label, "type": "switch", "default": on, "group": "Devices"}  # noqa: E731
        plugins_admin.install(data_dir, {
            "manifest_version": 1, "id": "direct-play", "name": "Direct play", "version": "1.0.0",
            "description": "Makes your films and series play directly on the devices you choose, so Jellyfin does not convert them as they play.",
            "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://example.invalid/direct-play",
            "support_url": "https://example.invalid/direct-play/issues", "starboard_api": ">=1.14 <2.0",
            "permissions": ["jellyfin:key", "reelix:key", "network:lan"], "needs": ["jellyfin"], "health": "/health",
            "containers": [{"name": "main", "image": "ghcr.io/example/direct-play@sha256:" + "f" * 64, "port": 8080, "network": "lan",
                            "volumes": ["data", "media/movies", "media/tv"], "user": "media"}],
            "resources": {"main": {"memory": 512, "cpus": 1.0}},
            "settings": [{"key": "files", "label": "Files", "type": "custom", "choices": "/files", "group": "Files"},
                         sw("device_roku_express", "Roku Express and older Rokus", True), sw("device_roku_4k", "Roku 4K"),
                         sw("device_fire_tv", "Fire TV Sticks"), sw("device_shield", "Nvidia Shield"),
                         {"key": "when", "label": "When it works", "type": "choice", "default": "weekends", "group": "When it works",
                          "choices": [{"value": "weekends", "label": "At weekends"}, {"value": "quiet", "label": "In Starboard's quiet hours"},
                                      {"value": "any", "label": "Any time"}]},
                         {"key": "card_seconds", "label": "Card updates every", "type": "choice", "default": "30", "group": "More",
                          "choices": [{"value": "10", "label": "10 seconds"}, {"value": "30", "label": "30 seconds"},
                                      {"value": "60", "label": "1 minute"}, {"value": "300", "label": "5 minutes"}]}],
            # Pause fixing asks first (DASH-441: the journeys check a confirm); the real plug-in does not.
            "actions": [{"id": "pause", "label": "Pause fixing", "path": "/pause", "confirm": "Stops converting files until you select Resume fixing. Continue?"},
                        {"id": "resume", "label": "Resume fixing", "path": "/resume"}],
            "cards": [{"id": "now", "title": "Direct play", "type": "list", "path": "/card", "refresh_seconds": 30},
                      {"id": "saved", "title": "Space saved by Direct play", "type": "stat", "path": "/summary", "format": "bytes"}],
            "logo": {"file": "logo.svg", "alt": "A play symbol on a screen"}},  # plug-in API 1.14 (DASH-428)
            "/nonexistent-media")
        from starboard import plugin_logo
        plugins_admin.keep_logo(data_dir, "direct-play", (plugin_logo.clean_svg(_DP_LOGO), "image/svg+xml"))
        plugins_admin.save_settings(data_dir, "direct-play", {"card_seconds": "10"})
        plugins_admin.set_state(data_dir, "direct-play", "enabled")
    real_answer, real_call, real_ask, real_action = plugin_cards.answer, plugin_custom.call, plugin_watch._ask, plugin_cards.action

    class Stand:  # the plug-in's container, answering from the made-up progress
        def __init__(self, body):
            self.body = json.dumps(body).encode()

        def open(self, req, timeout=None):
            body = self.body

            class R:
                def read(self, n):
                    return body

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False
            return R()

    def answer(d, pid, cid, opener=None):
        if pid != "direct-play":
            return real_answer(d, pid, cid, opener)
        saved = plugins_admin._read_kept(os.path.join(plugins_admin.folder(d, "direct-play"), "settings.json"), {}) or {}
        every = int(saved.get("card_seconds") or 30)
        return real_answer(d, pid, cid, _LazyStand(lambda: _dp_card(cid, every), Stand))

    def call(data_dir_, pid, key, body=None, opener=None):
        if pid != "direct-play":
            return real_call(data_dir_, pid, key, body, opener)
        out = plugin_custom.clean(_dp_screen())
        if body is not None:
            out["said"] = "This is example data, so nothing changed"
        return out
    plugin_cards.answer, plugin_custom.call = answer, call
    real_host = plugin_cards._host
    plugin_cards._host = lambda pid, main, wake=True: "direct-play.invalid" if pid == "direct-play" else real_host(pid, main, wake)
    plugin_watch._ask = lambda pid, main, path: "ok" if pid == "direct-play" else real_ask(pid, main, path)
    plugin_cards.action = lambda d, pid, aid, opener=None: (
        {"said": "Paused. This is example data, so nothing was converted" if aid == "pause" else "Resumed. This is example data"}
        if pid == "direct-play" else real_action(d, pid, aid, opener))


# A picture shrinker (DASH-432, plug-in API 1.14): a PNG logo, the jellyfin:metadata permission, a schedule setting
# that its job runs on, and a card whose band says it is waiting for its next run. Nothing is read or shrunk.
def _png_logo(side=64):
    import struct
    import zlib
    rows = b"".join(b"\x00" + b"".join(b"\x4b\x3f\xa6" if 16 <= x < 48 and 16 <= y < 48 else b"\xe8\xea\xee" for x in range(side))
                    for y in range(side))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def _example_on_demand_zip(data_dir):
    """Batch 0.19 (plug-in API 1.15): On demand added from a zip file (DASH-414), its container built from the zip, with
    two Jellyfin libraries (DASH-430), so its page shows Update from a zip file and its libraries; Jellyfin's
    metadata still in its settings folder (DASH-431), so Settings, Jellyfin offers to move it, and the move runs as
    made-up steps; nothing is built, moved or started."""
    from starboard import jellyfin_metadata, plugin_zip, plugins
    if not any(p["id"] == "on-demand" for p in plugins_admin.listing(data_dir)):
        m = {"manifest_version": 1, "author": "TheMightyTRexUK", "licence": "LicenseRef-Private", "starboard_api": ">=1.15 <2.0",
             "id": "on-demand", "name": "On demand", "version": "0.9.2",
             "description": "Films and series from your Stremio add-ons, in two Jellyfin libraries, played through your VPN.",
             "homepage": "https://example.invalid/on-demand", "support_url": "https://example.invalid/on-demand/issues",
             "permissions": ["network:vpn", "jellyfin:key", "jellyfin:libraries"], "needs": ["jellyfin", "gluetun"],
             "containers": [{"name": "on-demand", "image": "local/on-demand:0.9.2", "build": True, "network": "vpn", "port": 7790,
                             "user": "1000:1000", "volumes": ["data", "media/on-demand"]}],
             "jellyfin_libraries": [{"name": "On demand Films", "type": "movies", "folder": "media/on-demand/films"},
                                    {"name": "On demand TV", "type": "tvshows", "folder": "media/on-demand/tv"}]}
        plugins_admin.install(data_dir, m, "/nonexistent-media")
        where = plugins_admin.folder(data_dir, "on-demand")
        os.makedirs(os.path.join(where, "zips"), mode=0o700, exist_ok=True)
        st = plugins_admin._read(os.path.join(where, "state.json"), {})
        st["libraries"] = {"items": [{"name": "On demand Films", "path": "/data/media/on-demand/films", "realtime_monitor": False},
                                     {"name": "On demand TV", "path": "/data/media/on-demand/tv", "realtime_monitor": False}],
                           "said": "Jellyfin has them as the plug-in wants"}
        plugins_admin._write(os.path.join(where, "state.json"), st)
    # The build never reaches Docker here: a made-up build with its steps, then the install as it really runs.
    def fake_build(data_dir_, pid, manifest, path, say=None, deadline_seconds=None):
        for line in ("Step 1/7 : FROM python:3.12-alpine", "Step 3/7 : RUN apk upgrade --no-cache", "Successfully tagged " + plugins.built_image(manifest)):
            (say or (lambda x: None))(line)
            time.sleep(0.4)
        return ["Successfully tagged " + plugins.built_image(manifest)]
    plugin_zip.build = fake_build
    plugin_zip.ensure_images = lambda *a, **k: False
    state = {"moved": False}
    jellyfin_metadata.status = lambda data_dir_, name="jellyfin": {"moved": state["moved"], "can_move": not state["moved"], "why": "",
                                                                   "where": "/metadata" if state["moved"] else "/config/data/metadata"}

    def fake_move(data_dir_, services=None, name="jellyfin", project=None, helper=None, wait=None):
        for k, _label in jellyfin_metadata.STEPS:
            jellyfin_metadata._step(k, "working")
            time.sleep(0.3)
            jellyfin_metadata._step(k, "done", {"move": "About 14,312 MB in 150,525 folders, now in /srv/config/jellyfin-metadata"}.get(k, ""))
        state["moved"] = True
        return ["Jellyfin's pictures and details are in /srv/config/jellyfin-metadata, outside its settings folder",
                "Jellyfin watches 2,074 folders; the computer allows 127,879, with no watcher errors in its log", "8 of 8 sampled posters load"]
    jellyfin_metadata.move = fake_move


def _example_picture_shrinker(data_dir):
    from starboard import plugin_cards, plugin_life, plugin_logo, plugin_watch
    plugins_admin.jellyfin_metadata_dir = lambda d: "/srv/media-stack/config/jellyfin-metadata"  # as Install apps sets it (DASH-431)
    if not any(p["id"] == "picture-shrinker" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {
            "manifest_version": 1, "id": "picture-shrinker", "name": "Picture shrinker", "version": "1.0.0",
            "description": "Shrinks the posters and photos Jellyfin keeps, so they take less space. Each is checked before it replaces the original.",
            "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://example.invalid/picture-shrinker",
            "support_url": "https://example.invalid/picture-shrinker/issues", "starboard_api": ">=1.15 <2.0",
            "permissions": ["jellyfin:metadata"], "needs": ["jellyfin"], "health": "/health",
            "containers": [{"name": "main", "image": "ghcr.io/example/picture-shrinker@sha256:" + "e" * 64, "port": 8080,
                            "volumes": ["data", "jellyfin-metadata"], "user": "media", "start": "when_needed"}],
            "settings": [{"key": "when", "label": "When to shrink", "type": "schedule", "hint": "It runs at this time, in quiet hours or not.",
                          "default": {"every": "month", "date": 31, "time": "03:30"}},
                         {"key": "poster_height", "label": "Posters no taller than", "type": "number", "unit": "pixels", "default": 900, "min": 300, "max": 3000}],
            "jobs": [{"id": "shrink", "label": "Shrink pictures", "path": "/jobs/shrink", "schedule": "when", "time_limit_minutes": 120}],
            # A title for each card size (plug-in API 1.15, DASH-443), each within its size's limit
            "cards": [{"id": "saved", "title": "Space saved", "type": "stat", "path": "/card", "format": "bytes",
                       "titles": {"small": "Space saved", "medium": "Picture space saved", "half": "Pictures: space saved",
                                  "wide": "Space saved by shrinking pictures", "full": "Space saved by shrinking posters and photos"}}],
            "logo": {"file": "logo.png", "alt": "A small square inside a larger one"}},
            "/nonexistent-media")
        plugins_admin.keep_logo(data_dir, "picture-shrinker", (plugin_logo.check_png(_png_logo()), "image/png"))
        plugins_admin.set_state(data_dir, "picture-shrinker", "enabled")
    real_answer, real_ask, real_run = plugin_cards.answer, plugin_watch._ask, plugin_life.run_job

    def answer(d, pid, cid, opener=None):
        if pid != "picture-shrinker":
            return real_answer(d, pid, cid, opener)
        return {"type": "stat", "format": "bytes", "asked": int(time.time()),
                "data": plugin_cards.clean("stat", {"value": 41200000000, "label": "saved", "note": "18,402 pictures shrunk",
                                                     "status": "scheduled", "status_label": "Waiting for 03:30", "updated": int(time.time()) - 86400})}

    def run_job(d, pid, jid, helper=None):  # Run now: said as done, nothing shrunk
        if pid != "picture-shrinker":
            return real_run(d, pid, jid, helper)
        plugin_life._record(d, f"{pid}/{jid}", started=time.time(), finished=time.time(), status="done",
                            summary="Shrank 0 pictures. This is example data")
        return "Shrank 0 pictures. This is example data"
    plugin_cards.answer, plugin_life.run_job = answer, run_job
    plugin_watch._ask = lambda pid, main, path: "ok" if pid == "picture-shrinker" else real_ask(pid, main, path)
    # Never in quiet hours here, so the automatic updates (plug-ins update by themselves on this server) do not install
    # Picture shrinker 1.1.0 part way through the journeys when they run at night (17 November 2026).
    from starboard import auto_updates
    auto_updates.in_hours = lambda cfg_data, now=None: False
    # A catalogue entry with its logo as catalogue.json carries it (API 1.14): Disk forecast's, as a data address that
    # Starboard cleans like a logo file; Direct play's entry shows it once added, others their initials.
    real_entry = plugins_admin._clean_entry
    disk = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="4" fill="#1f5f99"/>'
                            b'<rect x="4" y="6" width="16" height="12" rx="1.5" fill="none" stroke="#ffffff" stroke-width="1.8"/>'
                            b'<path d="M4 14h16" stroke="#ffffff" stroke-width="1.8"/><circle cx="16.5" cy="16" r="1" fill="#ffffff"/></svg>').decode()
    plugins_admin._clean_entry = lambda e: real_entry({**e, "logo": "data:image/svg+xml;base64," + disk, "logo_alt": "A disk drive"}
                                                      if isinstance(e, dict) and e.get("id") == "disk-forecast" else e)


# Library clean-up (DASH-406, plug-in API 1.15): the library:holding permission with the media:holding volume, its rules
# and exclusions as settings, a Preview table of what would move and the space it frees, and the holding folder with a
# Put back button on each row (restore). Nothing is read, moved or put back: Put back takes the row off the list here.
_CLEANUP_HELD = [
    {"id": "h1", "title": "A made-up film (2001)", "detail": "Films. Moved Saturday 15 November, 4.2 GB. Watched by everyone, last 120 days ago"},
    {"id": "h2", "title": "Harbour lights (2019)", "detail": "Series. Moved Saturday 15 November, 31.8 GB. Ended, and every episode watched"},
    {"id": "h3", "title": "The long field (1998)", "detail": "Films. Moved Friday 14 November, 2.7 GB. Not watched for 12 months"}]


def _cleanup_screen(key, held):
    if key == "preview":
        rows = [("A quiet harbour (2004)", "Films", "Watched by everyone", "3.9 GB"), ("North road (2011)", "Films", "Not watched for 12 months", "2.2 GB"),
                ("Salt and stone (2016)", "Series", "Ended, all watched", "18.4 GB")]
        return {"type": "list", "title": "Preview", "layout": "folds", "readonly": True,
                "intro": "3 items would move to the holding folder, freeing 24.5 GB. Nothing moves until you activate Move items each day.",
                "columns": [{"key": "title", "label": "Title"}, {"key": "library", "label": "Library"}, {"key": "rule", "label": "Why"},
                            {"key": "size", "label": "Space"}],
                "items": [{"id": f"p{i}", "title": t, "group": lib, "actions": [], "cells": {"title": t, "library": lib, "rule": r, "size": z}}
                          for i, (t, lib, r, z) in enumerate(rows)]}
    return {"type": "list", "title": "Holding folder",
            "intro": "What Library clean-up moved, in media/.holding. Put back returns each to where it was, and Reelix follows it again.",
            "items": [{**h, "state": "off", "state_label": "In holding", "group": "Moved", "actions": ["restore"]} for h in held]}


def _example_network_check(data_dir):
    """A made-up plug-in with a sparkline card (plug-in API 1.17): response times over the last 24 hours, with a gap
    where a check got no answer, so the dashboard, its accessibility checks and screenshots show the card. It may send
    alerts (alerts:send), so its permissions list that too. Nothing is fetched and no container starts."""
    from starboard import plugin_cards, plugin_watch
    if not any(p["id"] == "network-check" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {
            "manifest_version": 1, "id": "network-check", "name": "Network check", "version": "1.0.0",
            "description": "Checks how quickly your router and apps answer, and sends an alert when one stops answering.",
            "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://example.invalid/network-check",
            "support_url": "https://example.invalid/network-check/issues", "starboard_api": ">=1.17 <2.0",
            "permissions": ["apps:read", "network:lan", "alerts:send"], "health": "/health",
            "containers": [{"name": "main", "image": "ghcr.io/example/network-check@sha256:" + "f" * 64, "port": 8080,
                            "network": "lan", "volumes": ["data"]}],
            "cards": [{"id": "times", "title": "Response times", "type": "sparkline", "path": "/trend",
                       "titles": {"small": "Response times", "half": "Response times"}}]},
            "/nonexistent-media")
        plugins_admin.set_state(data_dir, "network-check", "enabled")
    real_answer, real_ask = plugin_cards.answer, plugin_watch._ask
    router = [12.5, 13, 12.8, 14, 13.6, 12.9, 13.1, 15.2, 18.4, 14.1, 13, None, None, 13.4, 12.7, 12.5, 13.3, 14.8, 16.2, 15.1, 13.9, 13.2, 14, 15]
    jellyfin = [41, 39, 40, 38, 44, 52, 61, 48, 42, 40, 39, 38, 41, 43, 40, 39, 42, 47, 58, 66, 54, 45, 42, 40]
    reelix = [8.2, 8, 7.9, 8.4, 8.1, 9.3, 12.6, 9.1, 8.3, 8, 7.8, 8.2, 8.5, 8.1, 8, 7.9, 8.4, 9, 10.2, 9.4, 8.6, 8.3, 8.1, 8.2]

    def answer(d, pid, cid, opener=None):
        if pid != "network-check":
            return real_answer(d, pid, cid, opener)
        return {"type": "sparkline", "format": "number", "asked": int(time.time()),
                "data": plugin_cards.clean("sparkline", {
                    "series": [{"title": "Router", "points": router, "unit": "ms", "detail": "No answer for 2 checks at 04:00"},
                               {"title": "Jellyfin", "points": jellyfin, "unit": "ms", "detail": "Average 45 ms"},
                               {"title": "Reelix", "points": reelix, "unit": "ms", "detail": "Average 8.6 ms"}],
                    "note": "Hourly averages, the last 24 hours", "status": "ok", "updated": int(time.time()) - 300})}
    plugin_cards.answer = answer
    plugin_watch._ask = lambda pid, main, path: "ok" if pid == "network-check" else real_ask(pid, main, path)


def _example_library_cleanup(data_dir):
    from starboard import plugin_custom, plugin_watch
    if not any(p["id"] == "library-cleanup" for p in plugins_admin.listing(data_dir)):
        plugins_admin.install(data_dir, {
            "manifest_version": 1, "id": "library-cleanup", "name": "Library clean-up", "version": "1.0.0",
            "description": "Moves films and series that everyone has watched, or nobody has watched for a long time, to the holding folder. Never deletes.",
            "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://example.invalid/library-cleanup",
            "support_url": "https://example.invalid/library-cleanup/issues", "starboard_api": ">=1.15 <2.0",
            "permissions": ["jellyfin:key", "reelix:key", "library:holding", "network:lan"], "needs": ["jellyfin"], "health": "/health",
            "containers": [{"name": "main", "image": "ghcr.io/example/library-cleanup@sha256:" + "f" * 64, "port": 8080, "network": "lan",
                            "volumes": ["data", "media:holding"], "user": "media", "start": "always"}],
            "settings": [{"key": "preview", "label": "Preview", "type": "custom", "choices": "/preview", "group": "Preview"},
                         {"key": "held", "label": "Holding folder", "type": "custom", "choices": "/held", "group": "Holding folder"},
                         {"key": "active", "label": "Move items each day", "type": "switch", "default": False, "group": "Rules",
                          "hint": "In quiet hours. Look at Preview first: nothing moves until you activate this."},
                         {"key": "watched", "label": "Watched by everyone", "type": "switch", "default": True, "group": "Rules"},
                         {"key": "watched_days", "label": "Last watched more than", "type": "number", "unit": "days", "default": 90, "min": 7, "max": 3650, "group": "Rules"},
                         {"key": "keep_tag", "label": "Keep tag", "type": "text", "default": "keep", "group": "Always keep"}],
            "jobs": [{"id": "move", "label": "Move items to the holding folder", "path": "/jobs/move", "every_hours": 24, "quiet_hours": True}]},
            "/nonexistent-media")
        plugins_admin.set_state(data_dir, "library-cleanup", "enabled")
    real_call, real_ask = plugin_custom.call, plugin_watch._ask
    held = list(_CLEANUP_HELD)

    def call(data_dir_, pid, key, body=None, opener=None):
        if pid != "library-cleanup":
            return real_call(data_dir_, pid, key, body, opener)
        said = None
        if body is not None and body.get("action") == "restore":
            gone = next((h for h in held if h["id"] == body.get("id")), None)
            if gone:
                held.remove(gone)
                said = f"Put back {gone['title']}. This is example data, so nothing moved"
        out = plugin_custom.clean(_cleanup_screen(key, held))
        if body is not None:
            out["said"] = said or "This is example data, so nothing changed"
        return out
    plugin_custom.call = call
    plugin_watch._ask = lambda pid, main, path: "ok" if pid == "library-cleanup" else real_ask(pid, main, path)


def _example_plugin_update(data_dir):
    """Update tools (plug-in API 1.14, DASH-424): Picture shrinker 1.1.0 is in a catalogue, with its changes, a
    settings migration (Posters no taller than becomes Largest poster, and a new default for when it runs) and a
    before and an after step. Update shows What is new and how it is kept safe, then runs as steps; Roll back goes
    back to 1.0.0 with the settings as they were. Nothing is fetched or started: the steps answer here."""
    from starboard import plugin_life, plugin_update
    shrinker = plugins_admin._read(os.path.join(plugins_admin.folder(data_dir, "picture-shrinker"), "manifest.json")) or {}
    if shrinker.get("version") == "1.0.0" and "changes" not in shrinker:
        # 1.0.0 as installed, with its own before step, so the update asks it to get ready first.
        plugins_admin._write(os.path.join(plugins_admin.folder(data_dir, "picture-shrinker"), "manifest.json"),
                             {**shrinker, "update": {"before": {"path": "/update/before", "time_limit_seconds": 30}},
                              "changes": [{"version": "1.0.0", "date": "2026-11-10", "added": ["The first version"]}]})
        shrinker = plugins_admin._read(os.path.join(plugins_admin.folder(data_dir, "picture-shrinker"), "manifest.json"))
    newer = json.loads(json.dumps(shrinker))
    newer["version"] = "1.1.0"
    newer["settings"] = [{**st, "key": "max_poster_height", "label": "Largest poster"} if st["key"] == "poster_height" else st
                         for st in newer["settings"]]
    newer["update"] = {"before": {"path": "/update/before", "time_limit_seconds": 30}, "after": {"path": "/update/after"},
                       "health_wait_seconds": 30,
                       "migrations": [{"version": "1.1.0", "rename": {"poster_height": "max_poster_height"},
                                       "defaults": {"when": {"every": "week", "day": "sunday", "time": "03:30"}}}]}
    newer["changes"] = [{"version": "1.1.0", "date": "2026-11-14",
                         "added": ["**Photos of people** are shrunk too, as well as posters."],
                         "changed": ["Posters no taller than is now **Largest poster**; your choice moves with it.",
                                     "It runs every Sunday at 03:30 unless you chose another time."],
                         "fixed": ["A poster with an odd shape kept its size."]}] + newer["changes"]
    address = "https://example.invalid/picture-shrinker/1.1.0/starboard-plugin.json"
    real_known, real_fetch, real_compose, real_post = plugin_life.updates_known, plugins_admin.fetch_manifest, plugins_admin._compose_run, plugin_update._post

    def known(d):
        out = real_known(d)
        have = next((p for p in plugins_admin.listing(d) if p["id"] == "picture-shrinker"), None)
        if have and have.get("version") == "1.0.0":
            out["picture-shrinker"] = {"version": "1.1.0", "changelog": "Shrinks photos of people too", "manifest": address, "sha256": ""}
        return out

    def fetch(where, opener=None, sha256=""):
        return json.loads(json.dumps(newer)) if where == address else real_fetch(where, opener)

    def compose(d, pid, command, helper=None):  # its container: nothing is started here
        return (True, "") if pid == "picture-shrinker" else real_compose(d, pid, command, helper)

    def post(pid, main, path, body, timeout):
        if pid != "picture-shrinker":
            return real_post(pid, main, path, body, timeout)
        time.sleep(1.5)  # long enough to see each step in the dialog, which looks every 2 seconds
        return True, ("No job was running, so it is ready" if path.endswith("before") else "It started its schedule again")
    plugin_life.updates_known, plugins_admin.fetch_manifest = known, fetch
    plugins_admin._compose_run, plugin_update._post = compose, post


class _LazyStand:
    """Makes the made-up answer only when Starboard really asks the container, so a kept answer is not counted."""
    def __init__(self, make, stand):
        self.make, self.stand = make, stand

    def open(self, req, timeout=None):
        return self.stand(self.make()).open(req, timeout)



from starboard import noip  # noqa: E402  The No-IP updater (DASH-170), with made-up addresses
noip.status = lambda data_dir, **k: {"installed": True, "running": True, "state": "refused", "last_update": "2026-11-09T10:19:01Z",
                                     "address": "203.0.113.7", "said": "Type a new DDNS key or password below, then save. The updater starts again with it.",
                                     "username": "examplekey", "hostnames": "home.example.net", "password_set": True}
discovery.search = lambda services: {"docker": False, "items": [
    {"key": k, "name": n, "type": discovery.CATALOGUE[k][1], "url": f"http://127.0.0.1:{p}", "port": p, "needs_key": discovery.CATALOGUE[k][4], "background": False,
     "container": "", "already": False, "can_read_key": False} for k, n, p in (("seerr", "Seerr", 5055), ("jellystat", "Jellystat", 3000))]}

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


def example_default_app(path):
    """The default install's apps, made up (DASH-441 batch: every screenshot shows the default stack): Jellyfin with
    one person watching and what was added, qBittorrent downloading through Gluetun, Bazarr. None for other paths;
    (body, status) for an address the app does not have."""
    p = path.split("?")[0]
    if p.startswith("/jf/"):
        route = p[len("/jf"):]
        if route == "/System/Info/Public":
            return {"Version": "10.11.2", "ProductName": "Jellyfin Server", "ServerName": "Harbour"}
        if route == "/System/Info":
            return {"Version": "10.11.2", "HasUpdateAvailable": False, "HasPendingRestart": False}
        if route == "/Sessions":
            film = example_library.FILMS[2]
            return [{"UserName": "Sam", "DeviceName": "Living room TV", "Client": "Jellyfin Android TV",
                     "NowPlayingItem": {"Name": film["title"], "Type": "Movie", "RunTimeTicks": 72_000_000_000},
                     "PlayState": {"PositionTicks": 30_000_000_000, "IsPaused": False}}]
        q = dict(urllib.parse.parse_qsl(path.split("?", 1)[1])) if "?" in path else {}
        if route == "/Users":  # Watched and Play in Jellyfin (DASH-276, DASH-480): one made-up admin
            return [{"Id": "e" * 32, "Name": "Sam", "Policy": {"IsAdministrator": True}}]
        if route == "/Items" and (q.get("AnyProviderIdEquals") or q.get("Fields") == "ProviderIds"):
            return example_library.jellyfin_items(q)
        if route.startswith("/Shows/") and route.endswith("/Episodes"):
            return example_library.jellyfin_episodes(route.split("/")[2])
        if route == "/Items":
            now = dt.datetime.now(dt.timezone.utc)
            return {"Items": [{"Name": f["title"], "Type": "Movie", "ProductionYear": f["year"],
                               "DateCreated": (now - dt.timedelta(hours=3 + 9 * n)).isoformat()} for n, f in enumerate(example_library.FILMS[:6])]}
        return {"message": "not in the example"}, 404
    if p.startswith("/qbit/api/v2/"):
        route = p[len("/qbit/api/v2/"):]
        if route == "app/version":
            return "v5.1.2"
        if route == "transfer/info":
            return {"dl_info_speed": 4_200_000, "up_info_speed": 350_000}
        return [], 200
    if p.startswith("/gluetun/"):
        return {"/gluetun/v1/vpn/status": {"status": "running"},
                "/gluetun/v1/publicip/ip": {"public_ip": "203.0.113.24", "country": "Netherlands", "city": "Amsterdam"},
                "/gluetun/v1/portforward": {"port": 51413}}.get(p, ({"message": "not in the example"}, 404))
    if p.startswith("/bazarr/"):
        if p == "/bazarr/api/system/status":
            return {"data": {"bazarr_version": "1.5.3"}}
        return {"data": []}
    return None


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
        if method == "DELETE" and len(parts) == 2 and parts[0] == "queue" and parts[1].isdigit():  # removed from the queue (DASH-496)
            QUEUE_GONE.add(int(parts[1]))
            return self.send_json({}, 200)
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
        default = example_default_app(p)
        if isinstance(default, str):  # qBittorrent's version is plain text
            body = default.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if default is not None:
            return self.send_json(*default) if isinstance(default, tuple) else self.send_json(default)
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
                 "statusMessages": [{"title": "Old.Show.S05E01", "messages": ["No files found are eligible for import"]}],
                 # Copy issues for an AI helper (DASH-434): the fuller details, with made-up secrets the export takes out
                 "added": (today - dt.timedelta(days=1)).isoformat() + "T09:00:00Z", "indexer": "Harbour Usenet", "protocol": "usenet",
                 "downloadClient": "NZBGet", "downloadId": "nzb-ex-0003", "outputPath": "/data/downloads/complete/Old.Show.S05E01",
                 "seriesId": 1, "episodeId": 501, "seasonNumber": 5, "quality": {"quality": {"name": "HDTV-1080p"}},
                 "series": {"title": "Old Show"}, "episode": {"seasonNumber": 5, "episodeNumber": 1, "title": "The Return"}},
                {"id": 4, "title": "Example.Show.S02E04.1080p.WEB", "size": 2.2e9, "sizeleft": 1.1e9, "status": "failed", "trackedDownloadState": "failedPending",
                 "trackedDownloadStatus": "error", "errorMessage": "Download failed: http://192.168.1.20:9696/1/api?t=get&id=abc&apikey=made-up-indexer-key-9c1e",
                 "statusMessages": [{"title": "Example.Show.S02E04.1080p.WEB", "messages": ["qBittorrent at gluetun:8080 reports the torrent is stalled with no seeds",
                                                                                            "Tracker said: passkey=made-up-passkey-77 is not registered"]}],
                 "added": (today - dt.timedelta(days=3)).isoformat() + "T21:15:00Z", "indexer": "Lighthouse Torrents", "protocol": "torrent",
                 "downloadClient": "qBittorrent", "downloadId": "8F0C2A4E9B1D7C3A5E6F8091A2B3C4D5E6F70812", "outputPath": "/home/someone/private/incomplete",
                 "seriesId": 1, "episodeId": 204, "seasonNumber": 2, "quality": {"quality": {"name": "WEBDL-1080p"}},
                 "series": {"title": "Example Show"}, "episode": {"seasonNumber": 2, "episodeNumber": 4, "title": "Harbour Lights"}},
            ]
            if os.environ.get("EXAMPLE_ATTENTION") == "1":  # DASH-496: an .exe posing as an episode, for the slide-out's pictures
                recs.append({"id": 5, "title": "Harbour.Lights.S01E06.1080p.WEB", "size": 2_480_640, "sizeleft": 0, "status": "completed",
                             "trackedDownloadState": "importPending", "trackedDownloadStatus": "warning",
                             "statusMessages": [{"title": "Harbour.Lights.S01E06.1080p.WEB", "messages": ["No video files found in the download"]}],
                             "added": today.isoformat() + "T06:10:00Z", "downloadClient": "qBittorrent", "downloadId": "ex5",
                             "outputPath": "/data/downloads/torrents/Harbour.Lights.S01E06.1080p.WEB", "seriesId": 2})
            if film:
                recs = [{"id": 11, "title": "A.Film.2025.2160p", "size": 8e9, "sizeleft": 2e9, "status": "downloading", "trackedDownloadState": "downloading", "timeleft": "00:40:00"}]
            recs = [r for r in recs if r["id"] not in QUEUE_GONE]
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
    if self.path.startswith("/nzbget/jsonrpc"):  # the made-up NZBGet of the default install
        length = int(self.headers.get("Content-Length") or 0)
        method = (json.loads(self.rfile.read(length) or b"{}") or {}).get("method")
        result = {"version": "24.3", "listgroups": [],
                  "status": {"DownloadRate": 0, "RemainingSizeMB": 0, "DownloadPaused": False, "PostPaused": False, "ScanPaused": False}}.get(method)
        return self.send_json({"id": 1, "result": result})
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
    m = re.match(r"^/reelix/api/v1/queue/(\d+)/(import|ignore)$", self.path.split("?")[0])
    if m:  # Try the import again and Ignore (DASH-205, DASH-496)
        if m.group(2) == "ignore":
            QUEUE_GONE.add(int(m.group(1)))
        return self.send_json({"id": 1, "name": "process_download"}, 202)
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
        return {"items": [i for i in [{"id": 31, "title": "The.Example.Hour.S04E02.mp3", "download_client": "NZBGet", "download_id": "ex31",
                           "state": "downloading", "client_state": "downloading", "progress": 0.35, "size": 60_000_000,
                           "remaining": 39_000_000, "eta_secs": 240, "messages": [], "added": today.isoformat() + "T09:00:00Z",
                           "media": {"kind": "radio_episode", "id": 101, "title": "Lighthouses", "subtitle": "The Example Hour"}},
                          # a film downloading, for Search's Downloading filter (DASH-301)
                          {"id": 32, "title": "Made.Up.Film.1080p.WEB-DL", "download_client": "qBittorrent", "download_id": "ex32",
                           "state": "downloading", "client_state": "downloading", "progress": 0.6, "size": 4_000_000_000,
                           "remaining": 1_600_000_000, "eta_secs": 900, "messages": [], "added": today.isoformat() + "T08:00:00Z",
                           "media": {"kind": "movie", "id": 10, "title": example_library.FILMS[9]["title"], "year": example_library.FILMS[9]["year"]}},
                          # a radio episode Reelix cannot import (DASH-434: Copy issues for an AI helper)
                          {"id": 33, "title": "Sample.Science.Weekly.Ask.a.scientist.3.mp3", "download_client": "NZBGet", "download_client_id": 2,
                           "download_id": "nzb-ex-0033", "protocol": "usenet", "state": "import_pending", "client_state": "completed",
                           "progress": 1.0, "size": 48_000_000, "remaining": 0, "eta_secs": None, "indexer": "Harbour Usenet",
                           "messages": ["No audio files were found in /data/downloads/complete/Sample.Science.Weekly.3", "The folder holds only a .par2 file"],
                           "output_path": "/data/downloads/complete/Sample.Science.Weekly.3", "can_manual_import": False,
                           "added": today.isoformat() + "T07:30:00Z",
                           "media": {"kind": "radio_episode", "id": 203, "title": "Ask a scientist 3", "subtitle": "Sample Science Weekly", "show_id": 2}}]
                          if i["id"] not in QUEUE_GONE],
                "total": 3, "page": 1, "page_size": 0}
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


# The default install (stack.INSTALLS["basics"]), as Install apps adds it: Reelix is added after these, with the
# manager key. (name, kind, category, path on the made-up apps' port, icon)
WATCH, FIND, GET = "Watch, listen and request", "Find and organise", "Search and download"
APPS = [
    ("Jellyfin", "jellyfin", WATCH, "jf", "jellyfin"),
    ("Audiobookshelf", "audiobookshelf", WATCH, "abs", "audiobookshelf"),
    ("Bazarr", "bazarr", FIND, "bazarr", "bazarr"),
    ("qBittorrent", "qbittorrent", GET, "qbit", "qbittorrent"),
    ("NZBGet", "nzbget", GET, "nzbget", "nzbget"),
    ("Gluetun (VPN)", "gluetun", GET, "gluetun", "gluetun"),
]
# EXAMPLE_SETUP=existing: an older set-up beside them, for Copy app settings and the help on moving from it.
EXISTING = [
    ("Example TV", "sonarr", GET, "tv", ""),
    ("Example TV 4K", "sonarr", GET, "tv4k", ""),
    ("Example films", "radarr", GET, "films", ""),
]
if os.environ.get("EXAMPLE_SETUP") == "existing":
    APPS += EXISTING


def example_disk_health(data):
    """System, Disk health with made-up reports: a healthy disk, and a virtual disk that gives no health data, as in a
    virtual machine (DASH-114, WIZ-72)."""
    folder = data / "smart" / "current"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "sda.json").write_text(json.dumps({
        "model_name": "Harbour HDD 8TB", "serial_number": "HB0001", "device": {"name": "/dev/sda"},
        "user_capacity": {"bytes": 8 * TB}, "smart_status": {"passed": True}, "temperature": {"current": 34},
        "power_on_time": {"hours": 12000}, "ata_smart_attributes": {"table": [
            {"id": 5, "name": "Reallocated_Sector_Ct", "value": 100, "worst": 100, "thresh": 10, "raw": {"value": 0, "string": "0"}},
            {"id": 9, "name": "Power_On_Hours", "value": 87, "worst": 87, "thresh": 0, "raw": {"value": 12000, "string": "12000"}}]}}))
    (folder / "sdb.json").write_text(json.dumps({
        "model_name": "QEMU HARDDISK", "serial_number": "QM00001", "device": {"name": "/dev/sdb"},
        "user_capacity": {"bytes": 64 * GB}, "smart_support": {"available": False}}))
    os.environ["STARBOARD_SMART_DIR"] = str(data / "smart")


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
    example_disk_health(DATA)
    # A Basics install, as Install apps writes it, for Settings, Apps, Your install. Nothing is started.
    stack.can_download = lambda ref, check=None: True
    if not (DATA / "stack" / "compose.yaml").exists():
        basics = stack.install_choice("basics")
        if os.environ.get("EXAMPLE_NO_VPN") == "1":
            # DASH-440: Basics after Continue without a VPN, for the No VPN states on Downloads, the dashboard and
            # Settings, Downloads, VPN. Off by default.
            stack.write(str(DATA), stack.build({"apps": [k for k in basics["apps"] if k != "gluetun"], "config_dir": "/srv/media-stack/config",
                                                "data_dir": "/srv/media", "reelix_edition": "lite"}))
            stack.record_vpn_choice(str(DATA), False, "browser")
        else:
            stack.write(str(DATA), stack.build({"apps": basics["apps"], "config_dir": "/srv/media-stack/config",
                                                "data_dir": "/srv/media", "reelix_edition": "lite",
                                                "vpn": {"provider": "mullvad", "type": "wireguard",
                                                        "wireguard_private_key": "made-up", "wireguard_addresses": "192.168.1.20/32"}}))
    _example_plugins(str(DATA))
    _example_livetv(str(DATA))
    _example_keys(str(DATA))
    _example_transcode()
    _example_watch_stats(str(DATA))
    _example_app_plugins(str(DATA))
    _example_audio_description(str(DATA))
    _example_direct_play(str(DATA))
    _example_picture_shrinker(str(DATA))
    _example_on_demand_zip(str(DATA))
    _example_library_cleanup(str(DATA))
    _example_network_check(str(DATA))
    _example_plugin_update(str(DATA))
    _example_dispatcharr()
    _example_folders(DATA)
    _example_full_backups()
    _example_reelix_backup_place()
    _example_copies(DATA)
    _example_tdarr()
    _example_self_update()
    _example_updates(DATA)
    _example_update_all()
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
    _example_saved_copies(DATA)  # after the settings file is written
    _example_signin(app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if app.needs_setup:
        password = secrets.token_urlsafe(12)
        (DATA / "password").write_text(password + "\n")
        r, _ = call("POST", "/api/setup", {"token": app.setup_token, "password": password})
        cookie = r.getheader("Set-Cookie").split(";")[0]
        # A short server name, as Settings, General sets it: it starts the top row of the menu (DASH-237).
        # The example install is Reelix Lite, which starts with the shadows removed (DASH-536); the pictures in the README and the
        # help show the shadows the full install has, so they are kept unless EXAMPLE_SHADOWS_OFF=1 (release 0.29.0).
        call("PUT", "/api/config/general", {"server_name": "Harbour", "setup_guide_done": True,
                                            "shadows_off": os.environ.get("EXAMPLE_SHADOWS_OFF") == "1"}, cookie)  # a set-up server (DASH-238)
        # Audio description ticked in the set-up (DASH-399), so the Plug-ins pages show the offer to install it.
        call("PUT", "/api/config/general", {"extras": {"audio_description": True}}, cookie)
        # Settings, Updates (DASH-422): the plug-ins update by themselves; the rest wait for you (the default).
        call("PUT", "/api/config/general", {"plugins_auto_update": True}, cookie)
        # The dashboard with plug-in cards in the card band (plug-in API 1.14, DASH-428): Direct play with its logo and
        # a Converting chip, Picture shrinker with a PNG logo and its own words on the chip, Watch statistics without
        # a logo (its initials) and without a status, and Network check's sparkline card (plug-in API 1.17).
        call("PUT", "/api/config/general", {"dashboard": {"layout": "glance", "cards": [
            {"id": "plugin:direct-play:now", "size": "half"}, {"id": "plugin:picture-shrinker:saved", "size": "half"},
            {"id": "plugin:watch-stats:week", "size": "half"}, {"id": "playing", "size": "half"}, {"id": "health", "size": "half"},
            {"id": "downloads", "size": "half"}, {"id": "coming", "size": "half"}, {"id": "plugin:network-check:times", "size": "half"},
            {"id": "recent", "size": "full"},
            {"id": "disk", "size": "small"}, {"id": "load", "size": "small"}, {"id": "vpn", "size": "small"}, {"id": "alerts", "size": "small"}]}}, cookie)
        for name, kind, group, path, icon in APPS:
            key = {"nzbget": "starboard:made-up", "gluetun": ""}.get(kind, KEY)
            more = {}
            if kind == "jellyfin":  # its address for browsers (Play in Jellyfin, DASH-480); a real test Jellyfin when given
                more = {"link": os.environ.get("EXAMPLE_JELLYFIN_LINK", "http://192.168.1.20:8096")}
                if os.environ.get("EXAMPLE_JELLYFIN_URL"):
                    more.update(url=os.environ["EXAMPLE_JELLYFIN_URL"], api_key=os.environ.get("EXAMPLE_JELLYFIN_KEY", ""))
            call("POST", "/api/services", {"name": name, "type": kind, "group": group, "url": f"http://127.0.0.1:{FAKE_PORT}/{path}",
                                           "api_key": key, "icon": icon, **more}, cookie)
        # Reelix, as Install apps adds it: a link with the manager key, so radio shows in Coming up and Downloads.
        call("POST", "/api/services", {"name": "Reelix", "type": "link", "group": FIND, "icon": "reelix",
                                       "url": f"http://127.0.0.1:{FAKE_PORT}/reelix", "api_key": KEY}, cookie)
        if os.environ.get("EXAMPLE_ATTENTION") == "1":  # DASH-496: Reelix's TV address, so its downloads that need attention show
            call("POST", "/api/services", {"name": "Reelix TV", "type": "sonarr", "group": FIND, "icon": "reelix",
                                           "url": f"http://127.0.0.1:{FAKE_PORT}/reelix/sonarr", "api_key": KEY}, cookie)
        if EXAMPLE_CONTAINERS:
            # Reelix, seen at 0.7.0 before, so opening Apps, Updates finds it updated to 0.7.1.
            _, body = call("GET", "/api/config", cookie=cookie)
            rid = next(sv["id"] for sv in json.loads(body)["services"] if sv["name"] == "Reelix")
            (DATA / "app-changes.json").write_text(json.dumps({"seen": {rid: "0.7.0"}, "notices": {}}))
    # Activity, History, Across apps (DASH-68): what Starboard itself would have written over a few days.
    from starboard import activity_log
    hour = 3600
    activity_log.record_many(str(DATA), [
        ("upgraded", "Jellyfin", "Jellyfin updated from 10.11.2 to 10.11.3", "", now - 3 * hour, ""),
        ("failed", "", "Kavita is not responding", "Kavita did not answer.", now - 9 * hour, ""),
        ("added", "Disk forecast", "Disk forecast plug-in added, version 1.2.0", "", now - 26 * hour, ""),
        ("upgraded", "Starboard", "Starboard is updated", "Starboard v0.26.0 is installed and answering.", now - 30 * hour, ""),
        ("failed", "qBittorrent", "qBittorrent was not updated", "The new version did not start, so Starboard went back to the one before.", now - 50 * hour, ""),
        ("upgraded", "Audiobookshelf", "Audiobookshelf updated from 2.30.0 to 2.31.0", "", now - 75 * hour, "")])
    print("READY", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
