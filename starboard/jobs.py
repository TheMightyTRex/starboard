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

from . import listening, livetv, logs, migrate

JOBS = {
    "livetv": {"title": "Live TV channels and guide", "every": 3600, "what": "Refreshes Jellyfin's free TV guides daily, and its channels when a channel list changes"},
    "import": {"title": "Watch history import", "every": 3600, "what": "Applies imported watch history to Jellyfin as the media arrives"},
    "defaults": {"title": "Jellyfin user defaults", "every": 3600, "what": "Gives every Jellyfin user your defaults, unless they chose otherwise"},
    "listening": {"title": "Listening progress", "every": 3600, "what": "Applies listening progress to Audiobookshelf as the books are scanned in"},
}
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
        return bool(self.settings().get(SETTING[key]))

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
            if key == "livetv":
                summary = livetv.run(self.self_url(), bool(self.settings().get("white_logos", True)), force=force)
            elif key == "import":
                summary = migrate.apply(self.app.config.data_dir, services)
            elif key == "listening":
                summary = listening.apply(self.app.config.data_dir, services)
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
            if key == "livetv":
                needs = [] if livetv.folder() and os.path.isdir(livetv.folder()) else ["Jellyfin's Live TV folder (./install.sh asks)"]
            row["needs"] = needs
            out.append(row)
        return {"jobs": out, "self_url": self.self_url(), "pillow": livetv.pillow()}
