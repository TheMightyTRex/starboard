"""After an unexpected shutdown (DASH-88): notice it, check what a power cut can leave behind, and report it.

Lightweight first: one check at start, nothing in the background. Starboard writes data/running.json when it starts
(with the computer's boot id) and touches it with the space reading it already takes every few minutes; when it is
stopped properly (Docker, systemd or Ctrl+C send it SIGTERM or SIGINT) it writes data/clean-stop. At the next start:

- no clean-stop and a different boot id: the server went off without shutting down (a power cut, a crash, the power
  button held), at about the time running.json was last touched;
- no clean-stop and the same boot id: Starboard itself was stopped without warning (its container was killed).

Then, once, after the apps have had time to start (APPS_WAIT seconds), it checks the folders Starboard watches, the
pool (mounted, and any pool job that stopped part-way), a full backup that was cut off, and the apps, and writes one
report (data/recovery.json). System, Overview shows it until it is dismissed, and it goes out through Alerts when
an alert channel is set. Plan: ~/Documents/Claude/starboard/drive-pool/HEADLESS-AND-RECOVERY.md part 1. The deeper
checks there (file system repairs, half-moved folders, SnapRAID, keeping the media apps stopped while a pool drive is
missing) belong to the pool helper, which runs as root.
"""

import json
import os
import threading
import time

from . import logs

RUNNING = "running.json"
CLEAN = "clean-stop"
REPORT = "recovery.json"
APPS_WAIT = 180


def boot_id(path="/proc/sys/kernel/random/boot_id"):
    try:
        with open(path, encoding="ascii") as f:
            return f.read().strip()[:64]
    except OSError:
        return ""


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            found = json.load(f)
        return found if isinstance(found, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path, data):
    tmp = path + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def at_start(data_dir, boot=None, now=None):
    """Called once as Starboard starts. Returns {"kind": "server" or "starboard", "last_seen": time} when the last
    stop was not clean, else None, and marks this start."""
    boot = boot_id() if boot is None else boot
    now = time.time() if now is None else now
    running_path, clean_path = os.path.join(data_dir, RUNNING), os.path.join(data_dir, CLEAN)
    before = _read(running_path)
    try:
        last_seen = os.path.getmtime(running_path) if before else 0
    except OSError:
        last_seen = 0
    clean = os.path.exists(clean_path)
    try:
        os.remove(clean_path)
    except OSError:
        pass
    verdict = None
    if before and not clean:
        other_boot = bool(before.get("boot")) and bool(boot) and before["boot"] != boot
        verdict = {"kind": "server" if other_boot else "starboard", "last_seen": last_seen or before.get("started", 0)}
    try:
        _write(running_path, {"boot": boot, "started": now, "pid": os.getpid()})
    except OSError:
        pass
    return verdict


def heartbeat(data_dir):
    """Keeps the last time Starboard was seen running: called with the space reading it already takes."""
    try:
        os.utime(os.path.join(data_dir, RUNNING))
    except OSError:
        pass


def mark_clean(data_dir):
    try:
        with open(os.path.join(data_dir, CLEAN), "w", encoding="utf-8") as f:
            f.write(f"{time.time():.0f}\n")
    except OSError:
        pass


def _when(t):
    return time.strftime("%H:%M on %d %B", time.localtime(t)) if t else "an unknown time"


def check(app, verdict, status_all=None, pool_status=None, backup_status=None):
    """The checks after an unclean stop, in words: returns the report it saved."""
    from . import full_backup, pool, services
    status_all = status_all or services.status_all
    pool_status = pool_status or pool.status
    backup_status = backup_status or full_backup.status
    checked, problems, fixed = [], [], []
    # The folders Starboard watches (System, Storage): each answers.
    disks = list(getattr(app, "disks", []) or [])
    answering = 0
    for label, path in disks:
        try:
            os.statvfs(path)
            os.listdir(path)
            answering += 1
        except OSError:
            problems.append(f"{label} ({path}) is not answering. Check its drive is connected, then restart the server.")
    if disks:
        checked.append(f"{answering} of {len(disks)} folders answering")
    # The pool, when the pool helper looks after one.
    found = pool_status() or {}
    if found.get("set_up"):
        if found.get("mounted"):
            checked.append("the pool is mounted")
        else:
            problems.append("The pool is not mounted, so the apps cannot see your media. Open System, Pool.")
        job = found.get("job") or {}
        if job.get("state") == "running" and not job.get("finished"):
            problems.append(f"A pool job ({job.get('action', 'a job')}) stopped part-way. Open System, Pool to "
                            "start it again; files already moved are where they were moved to.")
    # A full backup that was being made: it cannot finish now, so it is marked as stopped.
    data_dir = app.data_dir
    backup = backup_status(data_dir) or {}
    if backup.get("state") == "running":
        try:
            full_backup._say(data_dir, state="failed", error="Stopped when the server went off. Make it again.", finished=time.time())
            fixed.append("a full backup that was being made is marked as stopped: make it again on System, Backup")
        except OSError:
            problems.append("A full backup was being made and did not finish. Make it again on System, Backup.")
    # The apps, after they have had time to start.
    apps = [s for s in app.config.data.get("services", []) if s.get("enabled") is not False and not s.get("background")]
    if apps:
        try:
            results = status_all(apps)
        except Exception:  # noqa: BLE001  a check that cannot run is said, never a stop
            results = []
        up = [r for r in results if r.get("state") == "up"]
        down = [r for r in results if r.get("state") == "down"]
        checked.append(f"{len(up)} of {len(apps)} apps answering")
        if down:
            names = ", ".join(next((s.get("name", "") for s in apps if s.get("id") == r.get("id")), "") for r in down)
            problems.append(f"Not answering: {names}. Open Activity for their last log lines, or restore from a backup.")
    who = "The server went off without shutting down" if verdict["kind"] == "server" else "Starboard stopped without shutting down"
    report = {"at": time.time(), "kind": verdict["kind"], "last_seen": verdict.get("last_seen", 0),
              "title": f"{who} at about {_when(verdict.get('last_seen'))}",
              "checked": checked, "problems": problems, "fixed": fixed, "seen": False}
    report["message"] = (f"{report['title']}. Checked: {', '.join(checked) or 'nothing to check'}. "
                         + (" ".join(problems) if problems else "Nothing needed fixing."))
    _write(os.path.join(data_dir, REPORT), report)
    logs.event("warning" if problems else "info", "recovery", report["message"])
    channel = (app.config.data.get("watch") or {}).get("channel") or {}
    if channel.get("kind") in ("ntfy", "gotify", "webhook"):
        from . import watch
        try:
            watch.send(channel, f"{app.config.data.get('site_name', 'Starboard')}: {who.lower()}", report["message"],
                       "problem" if problems else "warning")
        except ValueError as e:
            logs.event("error", "alert", f"Alert not sent: {e}")
    return report


def start(app, wait=APPS_WAIT):
    """At start: notes this start, and when the last stop was not clean, checks once in the background."""
    verdict = at_start(app.data_dir)
    if not verdict:
        return None
    logs.event("warning", "recovery", f"The last stop was not clean ({verdict['kind']}); checking in {wait} seconds")

    def later():
        time.sleep(wait)
        try:
            check(app, verdict)
        except Exception as e:  # noqa: BLE001  a report that fails is logged, never a crash
            logs.error("recovery", f"The check after an unclean stop failed: {e}", e)
    thread = threading.Thread(target=later, name="recovery", daemon=True)
    thread.start()
    return thread


def report(data_dir):
    """The last report while it has not been dismissed, or None."""
    found = _read(os.path.join(data_dir, REPORT))
    return found if found and not found.get("seen") else None


def dismiss(data_dir):
    path = os.path.join(data_dir, REPORT)
    found = _read(path)
    if found:
        found["seen"] = True
        _write(path, found)
