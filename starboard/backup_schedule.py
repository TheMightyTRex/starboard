"""Scheduled backups (DASH-17, owner, 9 November 2026): Settings, General, Backup and restore, Schedule.

- Off (the default): Starboard makes no backup by itself.
- Manual: backups are made only by hand; the page reminds you when the newest is more than 30 days old.
- Monthly (owner, 16 November 2026: "I also want monthly backups as a choice"): on the 1st of each month at 03:00,
  keeping the newest 6.
- Weekly: every Sunday at 03:00, keeping the newest 4.
- Nightly: every night at 03:00, keeping the newest 7.

At the time, Starboard makes a Full without media copy when it set up the apps and the person let it keep the backup
key (full_backup.save_key), then asks the server's own backup job (STARBOARD_JOBS_DIR) when one is set up, telling it
how many to keep. Either can run alone.

Lightweight: with Off or Manual there is no thread at all. With Monthly, Weekly or Nightly one thread sleeps until the next run
(waking at most every 6 hours to allow for the clock changing), so it uses no processor time in between. A run missed
while Starboard was stopped is made once when it starts again, if it is less than a day late; a monthly one is made
once at any time before the next 1st, so a server that was off on the 1st still gets that month's backup.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta

from . import backup, full_backup, logs

MODES = ("off", "manual", "monthly", "weekly", "nightly")  # least to most often, as the page lists them
KEEP = {"monthly": 6, "weekly": 4, "nightly": 7}
HOUR = 3
REMIND_DAYS = 30
STATE = "backup-schedule.json"
NO_KEY = ("No full backup was made: Starboard is not keeping a backup password, so it cannot make one by itself. "
          "Go to Settings, General, Backup and restore, Schedule, and keep the password")
PERIOD_DAYS = {"monthly": 31, "weekly": 7, "nightly": 1}


def keep_for(mode):
    """How many copies stay in the folder: the schedule's own number, else full backups' usual 5."""
    return KEEP.get(mode, full_backup.KEEP)


def _first_of_next_month(t):
    return (t.replace(day=1) + timedelta(days=32)).replace(day=1)


def next_run(mode, now):
    """The next run after now (a datetime), or None when nothing is scheduled."""
    if mode not in KEEP:
        return None
    t = now.replace(hour=HOUR, minute=0, second=0, microsecond=0)
    if mode == "monthly":  # the 1st of the month: day=1 first, so a 29th, 30th or 31st never makes a date that is not there
        t = t.replace(day=1)
        return t if t > now else _first_of_next_month(t)
    if mode == "weekly":
        t += timedelta(days=(6 - t.weekday()) % 7)  # Sunday is 6
        return t if t > now else t + timedelta(days=7)
    return t if t > now else t + timedelta(days=1)


def previous_run(mode, now):
    """The last scheduled time at or before now, or None."""
    nxt = next_run(mode, now)
    if nxt is None:
        return None
    if mode == "monthly":
        return (nxt - timedelta(days=1)).replace(day=1)  # the 1st of the month before the next run
    return nxt - timedelta(days=7 if mode == "weekly" else 1)


def late_limit(mode):
    """How late a missed run may still be made once when Starboard starts: a day, or a whole month for Monthly."""
    return 31 * 86400 if mode == "monthly" else 86400


class Scheduler:
    def __init__(self, app):
        self.app = app
        self.path = os.path.join(app.data_dir, STATE)
        self.wake = threading.Event()
        self.thread = None
        self.lock = threading.Lock()

    # State ------------------------------------------------------------------------------------------------------

    def mode(self):
        m = self.app.config.data.get("backup_schedule", "off")
        return m if m in MODES else "off"

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                got = json.load(f)
            return got if isinstance(got, dict) else {}
        except (OSError, ValueError):
            return {}

    def save(self, state):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, self.path)

    # The thread -------------------------------------------------------------------------------------------------

    def ensure(self):
        """Call after the setting changes: starts the thread for Monthly, Weekly or Nightly, or lets it end."""
        with self.lock:
            state = self.load()
            mode = self.mode()
            if state.get("mode") != mode:  # a new choice counts from now, so it never runs at once
                state.update(mode=mode, since=time.time())
                self.save(state)
            if mode in KEEP and not (self.thread and self.thread.is_alive()):
                self.thread = threading.Thread(target=self.loop, name="backup-schedule", daemon=True)
                self.thread.start()
            else:
                self.wake.set()

    def loop(self):
        missed = self._missed()
        while True:
            self.wake.clear()
            mode = self.mode()
            if mode not in KEEP:
                return
            now = datetime.now()
            if missed:
                missed = False
                self.run()
                continue
            due = next_run(mode, now)
            wait = (due - now).total_seconds()
            if wait > 1:
                self.wake.wait(min(wait, 6 * 3600))
                if self.wake.is_set() or datetime.now() < due:
                    continue  # the setting changed, or a 6-hour check: work it out again
            self.run()
            time.sleep(1)

    def _missed(self, now=None):
        """True when a scheduled run was missed while Starboard was stopped and should be made once now."""
        mode, state = self.mode(), self.load()
        now = now or datetime.now()
        prev = previous_run(mode, now)
        if prev is None:
            return False
        at, then = prev.timestamp(), now.timestamp()
        return at > (state.get("since") or then) and at > (state.get("last_run") or 0) and then - at < late_limit(mode)

    # One run ------------------------------------------------------------------------------------------------------

    def run(self):
        """Makes the scheduled backups now. Returns what happened in one sentence."""
        app, mode = self.app, self.mode()
        keep = keep_for(mode)
        said, problems = [], []
        saved = full_backup.saved_key(app.data_dir)
        if saved:
            try:
                full_backup.start(app.data_dir, app.version, "", saved["folder"], saved["pictures"],
                                  app.config.data.get("site_name", ""), keep=keep, saved=saved)
                said.append(self._wait_full())
            except full_backup.BackupError as e:
                said.append(f"The full backup did not start: {e}")
                problems.append(said[-1])
        else:
            # 26 November 2026: with no kept password this used to say nothing about the full backup, so the schedule
            # looked healthy for two weeks while no full backup was made. It now says so, in the page and as an alert.
            problems.append(NO_KEY)
            if backup.server_status()["can_run"]:  # with nothing else done, "Nothing was backed up" below says it
                said.append(NO_KEY)
        if backup.server_status()["can_run"]:
            try:
                backup.request_server_backup(keep=keep, scheduled=True)
                said.append("Asked the server's backup job to run")
            except ValueError as e:
                said.append(str(e))
        if not said:
            said.append("Nothing was backed up: let Starboard keep the backup password for Full without media, or set up the server's backup job")
        result = ". ".join(said)
        state = self.load()
        state.update(last_run=time.time(), last_result=result)
        self.save(state)
        failed = problems or result.startswith("Nothing") or "did not" in result
        logs.event("warning" if failed else "info", "backup", f"Scheduled backup: {result}")
        watch = getattr(app, "watch", None)
        if problems and watch:
            try:
                watch.alert(f"backup-schedule:{time.strftime('%Y-%m-%d')}", "The scheduled full backup was not made",
                            f"{problems[0]} The server's settings backup is not a full backup of the apps.", "problem")
            except Exception as e:  # noqa: BLE001 - an alert that cannot be sent never stops the run
                logs.event("warning", "backup", f"Could not raise the alert: {e}")
        return result

    def _wait_full(self, limit=3 * 3600):
        """Waits for the full backup to finish (checking every 30 seconds), so the server's job does not run at once."""
        until = time.time() + limit
        while time.time() < until:
            s = full_backup.status(self.app.data_dir)
            if s.get("state") == "done":
                return f"Made a full backup ({s.get('file', '')})"
            if s.get("state") == "failed":
                return f"The full backup did not finish: {s.get('error', '')}"
            time.sleep(30)
        return "The full backup is still running after 3 hours"

    # For the page -----------------------------------------------------------------------------------------------

    def status(self):
        mode, state = self.mode(), self.load()
        nxt = next_run(mode, datetime.now())
        saved = full_backup.saved_key(self.app.data_dir)
        server = backup.server_status()
        newest = max([full_backup.status(self.app.data_dir).get("finished") or 0]
                     + [(server.get("status") or {}).get("finished") or 0 if (server.get("status") or {}).get("status") == "done" else 0])
        full_done = full_backup.status(self.app.data_dir).get("finished") if full_backup.status(self.app.data_dir).get("state") == "done" else None
        late = bool(KEEP.get(mode)) and (not full_done or time.time() - full_done > PERIOD_DAYS[mode] * 2 * 86400 + 86400)
        return {"late": late, "mode": mode, "modes": list(MODES), "keep": keep_for(mode), "next": nxt.timestamp() if nxt else None,
                "last_run": state.get("last_run"), "last_result": state.get("last_result", ""),
                "key": {"folder": saved["folder"], "pictures": saved["pictures"], "saved": saved["saved"]} if saved else None,
                "server_job": bool(server["can_run"]), "newest": newest or None,
                "remind": mode == "manual" and (not newest or time.time() - newest > REMIND_DAYS * 86400)}
