"""Download hours: qBittorrent and SABnzbd only download between two hours of the day.

Settings, General turns it on and sets the hours (whole hours, the server's local time). Once a minute:
- outside the hours, unfinished torrents are stopped and SABnzbd is paused, including anything new the apps
  add. Seeding torrents are left alone. Something you start yourself in the client while paused is left running.
- when the hours start, only what Starboard stopped is started again.
Resume now runs everything until the hours end; Pause now pauses until they start; Follow the hours drops either.
Turning the hours off starts again what Starboard stopped, then leaves the clients alone.
State (what Starboard stopped, any override) lives in data/schedule.json.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta

from . import logs, services
from .services import ServiceError

PAUSED = ("stoppedDL", "pausedDL")


def next_hour(hour, now):
    t = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    return t if t > now else t + timedelta(days=1)


def in_hours(start, end, now):
    return start <= now.hour < end if start < end else (now.hour >= start or now.hour < end)


class Schedule:
    def __init__(self, config):
        self.config = config
        self.path = os.path.join(config.data_dir, "schedule.json")
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.thread = None

    # State --------------------------------------------------------------------

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
        state.setdefault("override", None)
        state.setdefault("until", 0)
        state.setdefault("applied", None)
        state.setdefault("clients", {})
        return state

    def save(self, state):
        tmp = self.path + ".tmp"
        with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, self.path)

    def hours(self):
        return self.config.data["download_hours"]

    def clients(self):
        return [s for s in self.config.data["services"]
                if s["type"] in ("qbittorrent", "sabnzbd", "nzbget") and s.get("enabled", True) and s.get("url") and s.get("api_key")]

    def wanted(self, state, now):
        """("run" or "pause", "manual" or "hours")"""
        if state["override"] and state["until"] > now.timestamp():
            return state["override"], "manual"
        h = self.hours()
        return ("run" if in_hours(h["start"], h["end"], now) else "pause"), "hours"

    # Clients ------------------------------------------------------------------

    def apply(self, action, state, manual=False, enforcing=False):
        """Runs or pauses every client. enforcing: the minute-by-minute pause, which leaves alone anything
        started in the client by hand since Starboard paused it."""
        errors = []
        for client in self.clients():
            mine = state["clients"].setdefault(client["id"], {"stopped": [], "started_by_you": [], "sab_paused": False})
            try:
                if client["type"] == "qbittorrent":
                    self._qbit(client, mine, action, manual, enforcing)
                elif client["type"] == "nzbget":
                    self._nzbget(client, mine, action, enforcing)
                else:
                    self._sab(client, mine, action, enforcing)
            except ServiceError as e:
                errors.append(str(e))
        return errors

    def _qbit(self, client, mine, action, manual, enforcing):
        torrents = services.qbit(client, "torrents/info") or []
        ours, yours = set(mine["stopped"]), set(mine["started_by_you"])
        unfinished = [t for t in torrents if t.get("progress", 1) < 1]
        if action == "pause":
            active = {t["hash"] for t in unfinished if t.get("state") not in PAUSED}
            if enforcing:
                yours |= active & ours  # Starboard stopped it and it is running again: someone started it
                ours -= yours
                active -= yours
            if active:
                services.qbit(client, "torrents/stop", {"hashes": "|".join(sorted(active))})
                ours |= active
        else:
            stopped = {t["hash"] for t in unfinished if t.get("state") in PAUSED}
            # The hours starting restart only what Starboard stopped; Resume now restarts every unfinished torrent.
            target = stopped if manual else stopped & ours
            if target:
                services.qbit(client, "torrents/start", {"hashes": "|".join(sorted(target))})
            ours -= target
            yours = set()
        present = {t["hash"] for t in torrents}
        mine["stopped"], mine["started_by_you"] = sorted(ours & present), sorted(yours & present)

    def _nzbget(self, client, mine, action, enforcing):
        paused = bool((services.nzbget(client, "status") or {}).get("DownloadPaused"))
        if action == "pause" and not paused:
            if not (enforcing and mine.get("nzbget_paused")):  # paused by Starboard and running again: leave it
                services.nzbget(client, "pausedownload")
                mine["nzbget_paused"] = True
        elif action == "run":
            if paused:
                services.nzbget(client, "resumedownload")
            mine["nzbget_paused"] = False

    def _sab(self, client, mine, action, enforcing):
        paused = services.sab(client, "queue", limit=0)["queue"]["paused"]
        if action == "pause" and not paused:
            if not (enforcing and mine.get("sab_paused")):  # paused by Starboard and running again: leave it
                services.sab(client, "pause")
                mine["sab_paused"] = True
        elif action == "run":
            if paused:
                services.sab(client, "resume")
            mine["sab_paused"] = False

    # The minute-by-minute check -------------------------------------------------

    def tick(self):
        if not self.hours()["enabled"] and not os.path.exists(self.path):
            return  # never used: nothing to check or undo, and no file to write
        with self.lock:
            state = self.load()
            before = json.dumps(state, sort_keys=True)
            now = datetime.now()
            if state["override"] and state["until"] <= now.timestamp():
                state["override"], state["until"] = None, 0
            if not self.hours()["enabled"]:
                if state["applied"] == "pause":
                    self.apply("run", state)  # starts again only what Starboard stopped
                state.update(applied=None, override=None, until=0)
            else:
                want, _ = self.wanted(state, now)
                # Pausing is checked every minute (it catches new downloads); running only when it changes.
                if want == "pause" or state["applied"] != want:
                    if state["applied"] != want:
                        logs.event("info", "download hours", "Downloads paused" if want == "pause" else "Downloads running again")
                    self.apply(want, state, enforcing=want == "pause" and state["applied"] == "pause")
                    state["applied"] = want
            if json.dumps(state, sort_keys=True) != before:  # write only when something changed
                self.save(state)

    def needed(self):
        """On, or off but still holding downloads it paused (they are started again first)."""
        return self.hours()["enabled"] or self.load().get("applied") == "pause"

    def loop(self):
        while True:
            try:
                self.tick()
            except Exception as e:  # keep checking whatever one client does
                logs.event("warning", "download hours", str(e))
            if not self.needed():
                self.thread = None
                return  # off and nothing to undo: no thread at all until it is turned on again
            every = int(self.config.data.get("performance", {}).get("schedule_every", 60))
            self.wake.wait(every)
            self.wake.clear()

    def start(self):
        self.ensure()

    def ensure(self):
        if self.thread and self.thread.is_alive():
            self.wake.set()
            return
        if self.needed():
            self.thread = threading.Thread(target=self.loop, name="download-hours", daemon=True)
            self.thread.start()

    # The page -----------------------------------------------------------------

    def status(self):
        h = self.hours()
        state = self.load()
        now = datetime.now()
        out = {"enabled": h["enabled"], "start": h["start"], "end": h["end"],
               "clients": [c["name"] for c in self.clients()]}
        if not h["enabled"]:
            return out
        want, reason = self.wanted(state, now)
        change = datetime.fromtimestamp(state["until"]) if reason == "manual" else next_hour(h["end"] if want == "run" else h["start"], now)
        out.update(mode=want, reason=reason, next_change=change.isoformat(timespec="minutes"))
        return out

    def act(self, action):
        """resume, pause or follow (the hours)."""
        if not self.hours()["enabled"]:
            raise ValueError("Activate download hours in Settings, General first")
        h = self.hours()
        with self.lock:
            state = self.load()
            now = datetime.now()
            if action == "resume":
                state.update(override="run", until=next_hour(h["end"], now).timestamp())
                errors = self.apply("run", state, manual=True)
            elif action == "pause":
                state.update(override="pause", until=next_hour(h["start"], now).timestamp())
                errors = self.apply("pause", state)
            elif action == "follow":
                state.update(override=None, until=0)
                errors = self.apply(self.wanted(state, now)[0], state)
            else:
                raise ValueError("Choose resume, pause or follow")
            state["applied"] = self.wanted(state, now)[0]
            self.save(state)
        return dict(self.status(), errors=errors)
