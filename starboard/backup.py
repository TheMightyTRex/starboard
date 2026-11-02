"""Backup and restore: Starboard's own settings, and (optionally) a backup job that runs on the server.

Starboard's settings: a JSON file with the apps, API keys, categories and settings, never the password or
sessions. Restoring saves a copy of the current settings first.

Server backup: Starboard cannot read the whole server, so a job on the host does the work. Starboard only drops
an empty file into STARBOARD_JOBS_DIR/requests, named "backup", or "backup-with-prompt" to ask for a rebuild
prompt for an AI assistant as well, and reads STARBOARD_JOBS_DIR/<that name>.json
({"status", "started", "finished", "summary"}) for the result. STARBOARD_BACKUP_DIR (read-only) lists the
backup files that job made.
"""

import glob
import json
import os
import re
import time

from .config import ConfigError, validate_service

FORMAT = "starboard-settings"
GENERAL_KEYS = ("site_name", "design", "groups", "show_home_address", "show_outside_address",
                "session_days", "secure_cookies", "update_check", "network_access", "upcoming_view", "upcoming_days", "download_hours")
SAVED_RE = re.compile(r"^config-[0-9-]+-[a-z-]+\.json$")


def export(config, version):
    d = config.data
    return {
        "format": FORMAT,
        "version": version,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "settings": {k: d[k] for k in GENERAL_KEYS if k in d},
        "services": d["services"],
    }


def restore(config, backup):
    """Replaces apps and settings with the backup's, after checking every part. Password and sessions stay."""
    if not isinstance(backup, dict) or backup.get("format") != FORMAT:
        raise ConfigError("This is not a Starboard settings backup")
    services = backup.get("services")
    settings = backup.get("settings") or {}
    if not isinstance(services, list) or not isinstance(settings, dict):
        raise ConfigError("This backup is incomplete")
    clean = []
    seen = set()
    for s in services:
        c = validate_service(s)
        c["id"] = str(s.get("id", ""))
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,39}$", c["id"]) or c["id"] in seen:
            raise ConfigError("An app in this backup has a missing or repeated ID")
        seen.add(c["id"])
        clean.append(c)
    with config.lock:
        config.backup("before-restore")
        saved = dict(config.data)
        try:
            config.update_general({k: settings[k] for k in GENERAL_KEYS if k in settings})
            config.data["services"] = clean
            config.save()
        except (ConfigError, ValueError, TypeError):
            config.data.clear()
            config.data.update(saved)
            config.save()
            raise
    return len(clean)


def saved_copies(config):
    folder = os.path.join(config.data_dir, "backups")
    out = []
    for path in sorted(glob.glob(os.path.join(folder, "config-*.json")), reverse=True)[:30]:
        name = os.path.basename(path)
        reason = name.rsplit("-", 1)[-1].removesuffix(".json")
        out.append({"name": name, "saved": os.path.getmtime(path), "size": os.path.getsize(path),
                    "reason": {"migration": "Before an update changed the settings", "restore": "Before a restore"}.get(reason, reason)})
    return out


def restore_saved(config, name):
    if not SAVED_RE.match(name or ""):
        raise ConfigError("Choose a saved copy from the list")
    path = os.path.join(config.data_dir, "backups", name)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Saved copies are whole settings files: turn them into the backup format, keeping the password.
    return restore(config, {"format": FORMAT, "settings": data, "services": data.get("services", [])})


# Server backup through a host job ------------------------------------------------

JOB_NAMES = ("backup", "backup-with-prompt")


def jobs_dir():
    return os.environ.get("STARBOARD_JOBS_DIR", "")


def backup_dir():
    return os.environ.get("STARBOARD_BACKUP_DIR", "")


def server_status():
    jobs, folder = jobs_dir(), backup_dir()
    status = None
    if jobs:
        for job in JOB_NAMES:
            try:
                with open(os.path.join(jobs, f"{job}.json"), encoding="utf-8") as f:
                    raw = json.load(f)
            except (OSError, ValueError):
                continue
            if not status or (raw.get("started") or 0) > (status.get("started") or 0):
                status = {k: raw.get(k) for k in ("status", "started", "finished", "summary", "exit")}
                status["with_prompt"] = job == "backup-with-prompt"
        if any(os.path.exists(os.path.join(jobs, "requests", job)) for job in JOB_NAMES):
            status = dict(status or {}, status="waiting")
    files = []
    if folder and os.path.isdir(folder):
        for path in glob.glob(os.path.join(folder, "*")):
            if os.path.isfile(path) and re.search(r"\.(zip|tar|tar\.gz|tgz|gz|7z|dump|sql|md)$", path):
                files.append({"name": os.path.basename(path), "size": os.path.getsize(path), "modified": os.path.getmtime(path)})
        files.sort(key=lambda f: f["modified"], reverse=True)
    return {"can_run": bool(jobs) and os.access(os.path.join(jobs, "requests"), os.W_OK),
            "configured": bool(jobs or folder), "status": status, "files": files[:50]}


def request_server_backup(with_prompt=False):
    jobs = jobs_dir()
    if not jobs:
        raise ConfigError("No server backup job is set up. See Backup and restore in the README")
    path = os.path.join(jobs, "requests", "backup-with-prompt" if with_prompt else "backup")
    try:
        with open(path, "w"):
            pass
    except OSError:
        raise ConfigError("Starboard cannot ask for a backup: the requests folder is not writable") from None
