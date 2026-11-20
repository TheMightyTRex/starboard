"""Starboard's own background jobs: Live TV, applying imported watch history and user defaults (Jellyfin), and
applying listening progress (Audiobookshelf).

Each is off until turned on in Settings, Apps, Jellyfin or Settings, Apps, Audiobookshelf. One thread runs them, and it starts only when one is on:
it wakes every 10 minutes and runs whatever is due (Live TV daily, the others hourly). Each job's last run
is kept in data/jobs.json, for System, Apps, Other services and Settings.
"""

import json
import os
import threading
import time

from . import child, listening, livetv, logs, migrate, vpn_ports

JOBS = {
    "livetv": {"title": "Live TV channels and guide", "every": 3600, "what": "Refreshes Jellyfin's free TV guides daily, and its channels when a channel list changes"},
    "import": {"title": "Watch history import", "every": 3600, "what": "Applies imported watch history to Jellyfin as the media arrives"},
    "defaults": {"title": "Jellyfin user defaults", "every": 3600, "what": "Gives every Jellyfin user your defaults, unless they chose otherwise"},
    "listening": {"title": "Listening progress", "every": 3600, "what": "Applies listening progress to Audiobookshelf as the books are scanned in"},
    "vpnport": {"title": "VPN port forwarding", "every": 600, "what": "Keeps qBittorrent listening on the port the VPN forwards"},
    "reelixupdate": {"title": "Reelix updates", "every": 86400, "what": "Installs a new Reelix by itself in quiet hours, with a way back if it is not healthy"},
    # DASH-417: hourly, so it finds the quiet hours; each look is one cached question (GitHub at most every 6 hours).
    "starboardupdate": {"title": "Starboard updates", "every": 3600, "what": "Installs a new Starboard release by itself in quiet hours, with a way back if it does not start"},
    # DASH-422: hourly, so each finds the update hours; outside them a look asks nothing, inside them once a day.
    "appsupdate": {"title": "App updates", "every": 3600, "what": "Updates your other apps by themselves in the update hours, with a copy of their settings and a way back"},
    "pluginsupdate": {"title": "Plug-in updates", "every": 3600, "what": "Updates Starboard's plug-ins by themselves in the update hours, with Roll back if one does not answer"},
    "jellyfinpluginsupdate": {"title": "Jellyfin plug-in updates", "every": 3600, "what": "Lets Jellyfin update its own plug-ins in the update hours, with a copy first and a check that each starts"},
}
AUTO = {"reelixupdate": "reelix_auto_update", "starboardupdate": "starboard_auto_update", "appsupdate": "apps_auto_update",
        "pluginsupdate": "plugins_auto_update", "jellyfinpluginsupdate": "jellyfin_plugins_auto_update"}
SETTING = {"livetv": "livetv", "import": "import_keep", "defaults": "defaults", "listening": "listening_keep"}
PAGE = {"listening": "/settings-audiobookshelf.html"}


class Jobs:
    def __init__(self, app):
        self.app = app
        self.path = os.path.join(app.config.data_dir, "jobs.json")
        self.lock = threading.Lock()
        self.file_lock = threading.Lock()
        self.running = set()
        self.wake = threading.Event()
        self.thread = None

    def settings(self):
        return self.app.config.data["extras"]

    def enabled(self, key):
        if key == "vpnport":  # on by itself while the VPN forwards a port and both apps have their keys (DASH-233)
            return vpn_ports.wanted(self.app.config, self.app.data_dir)
        if key in AUTO:  # Settings, Updates (DASH-263, DASH-417, DASH-422)
            return bool(self.app.config.data.get(AUTO[key]))
        return bool(self.settings().get(SETTING[key]))

    def quiet_now(self):
        """Inside the quiet hours: Starboard's download hours when set, otherwise 01:00 to 06:00 (self_update.py)."""
        import datetime
        from . import self_update
        return self_update.in_quiet_hours(self.app.config.data, datetime.datetime.now())

    def self_url(self):
        """The address Jellyfin uses to reach Starboard, for logos and Pluto streams."""
        given = self.settings().get("livetv_address", "").rstrip("/")
        if given:
            return given
        info = self.app.network_info("127.0.0.1")
        addresses = info.get("addresses") or []
        return f"http://{addresses[0] if addresses else '127.0.0.1'}:{self.app.port}"

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _record(self, key, **values):
        with self.file_lock:
            data = self._load()
            data.setdefault(key, {}).update(values)
            tmp = self.path + ".tmp"
            with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, self.path)

    # Running ------------------------------------------------------------------------------

    def run(self, key, force=False):
        with self.lock:  # one run of each job at a time, however many clicks
            if key in self.running:
                return
            self.running.add(key)
        self._record(key, started=time.time(), state="running")
        services = self.app.config.data["services"]
        try:
            # The heavy ones run in a short-lived process, so the memory they use goes back to the system when they
            # end (child.py, DASH-79). Live TV also puts the channels and guides into Jellyfin itself (DASH-229).
            if key == "livetv":
                summary = child.run("livetv", {"self_url": self.self_url(),
                                               "force": force, "services": services, "settings": self.settings(),
                                               "data_dir": self.app.config.data_dir}, timeout=3 * 3600)
            elif key in ("import", "listening"):
                summary = child.run(key, {"data_dir": self.app.config.data_dir, "services": services}, timeout=3 * 3600)
            elif key == "vpnport":
                summary = vpn_ports.sync(self.app.config)
            elif key == "reelixupdate":
                from . import reelix_updates
                summary = reelix_updates.run(self.app.config, self.app.data_dir)
            elif key == "starboardupdate":
                from . import self_update
                summary = self_update.automatic(self.app)
            elif key in ("appsupdate", "pluginsupdate", "jellyfinpluginsupdate"):
                from . import auto_updates
                summary = {"appsupdate": auto_updates.apps, "pluginsupdate": auto_updates.plugins,
                           "jellyfinpluginsupdate": auto_updates.jellyfin_plugins}[key](self.app)
            else:
                summary = migrate.ensure_defaults(services)
            self._record(key, finished=time.time(), state="done", summary=summary)
            logs.event("info", "jobs", f"{key} finished: {summary}" if isinstance(summary, str) else f"{key} finished")
        except Exception as e:  # recorded for the pages; the next run tries again
            self._record(key, finished=time.time(), state="failed", summary=str(e)[:300])
            logs.error("jobs", f"{key} failed: {e}", e)
        finally:
            self.running.discard(key)

    def run_soon(self, key, force=False):
        threading.Thread(target=self.run, args=(key, force), name=f"job-{key}", daemon=True).start()

    def _loop(self):
        while True:
            last = self._load()
            for key, job in JOBS.items():
                if key == "reelixupdate" and not self.quiet_now():
                    continue  # DASH-417: Reelix's automatic update waits for the quiet hours, as Starboard's does
                if self.enabled(key) and time.time() - (last.get(key, {}).get("started") or 0) >= job["every"]:
                    self.run(key)
            if not any(self.enabled(k) for k in JOBS):
                self.thread = None
                return  # nothing on: the thread ends, and starts again when a job is turned on
            self.wake.wait(600)
            self.wake.clear()
            if not any(self.enabled(k) for k in JOBS):
                self.thread = None
                return

    def ensure(self):
        """Starts the thread if a job is on; wakes a running thread, which ends if every job is off."""
        if self.thread and self.thread.is_alive():
            self.wake.set()
            return
        if not any(self.enabled(k) for k in JOBS):
            return
        self.thread = threading.Thread(target=self._loop, name="jobs", daemon=True)
        self.thread.start()

    # The pages ----------------------------------------------------------------------------

    def status(self):
        last = self._load()
        jf = migrate.jellyfin_app(self.app.config.data["services"])
        abs_ = listening.abs_app(self.app.config.data["services"])
        out = []
        for key, job in JOBS.items():
            row = {"key": key, "title": job["title"], "what": job["what"], "enabled": self.enabled(key), "page": PAGE.get(key, "/settings-jellyfin.html"),
                   **{k: last.get(key, {}).get(k) for k in ("started", "finished", "state", "summary")}}
            if key in self.running:
                row["state"] = "running"
            needs = []
            if not jf:
                needs.append("Jellyfin with its API key in Manage apps")
            if key == "listening":
                needs = [] if abs_ else ["Audiobookshelf with an admin API key in Manage apps"]
            if key in AUTO:
                needs = []
                row["page"] = "/settings-updates.html"
            if key == "vpnport":
                needs = [] if row["enabled"] else ["Gluetun with port forwarding, and qBittorrent, each with its key"]
                row["page"] = "/settings-install.html"
            if key == "livetv":
                needs = [] if livetv.folder() and os.path.isdir(livetv.folder()) else ["Jellyfin's Live TV folder (./install.sh asks)"]
            row["needs"] = needs
            out.append(row)
        return {"jobs": out, "self_url": self.self_url()}
