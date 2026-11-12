"""Backup and restore: Starboard's own settings, and (optionally) a backup job that runs on the server.

Starboard's settings: a JSON file with the apps, API keys, categories and settings, never the password or
sessions. Restoring saves a copy of the current settings first.

Server backup: Starboard cannot read the whole server, so a job on the host does the work. Starboard only drops
an empty file into STARBOARD_JOBS_DIR/requests, named "backup", or "backup-with-prompt" to ask for a rebuild
prompt for an AI assistant as well (since DASH-17 the file holds {"keep": n, "scheduled": true or false}: how many
backups the job should keep, which a job may read or ignore), and reads STARBOARD_JOBS_DIR/<that name>.json
({"status", "started", "finished", "summary"}) for the result. STARBOARD_BACKUP_DIR (read-only) lists the
backup files that job made.
"""

import glob
import json
import os
import re
import time

from .config import DEFAULTS, DESIGNS, SCHEMA, SERVICE_TYPES, UPCOMING_DAYS, UPCOMING_VIEWS, ConfigError, migrate, validate_service

FORMAT = "starboard-settings"
GENERAL_KEYS = ("site_name", "server_name", "design", "groups", "show_home_address", "show_outside_address",
                "session_days", "secure_cookies", "update_check", "network_access", "upcoming_view", "upcoming_days", "download_hours",
                "fetch_icons", "show_posters", "watch", "extras", "performance", "dashboard", "logs", "ux_notes", "settings_advanced",
                "reelix_auto_update", "infinite_scroll", "backup_schedule", "backup_keep_versions")
# Settings kept with their own checks when restored (DASH-350, catalogue sources).
OTHER_KEYS = ("history_keep_days", "history_cleared_at", "plugin_catalogues")
# Never in a backup: the sign-in, and what belongs to this install only. tests/test_backup_layout.py fails when a
# setting is in none of these three lists, so a new setting cannot be left out by mistake.
NEVER_KEYS = ("auth", "schema", "last_version", "setup_guide_done", "feedback_default_on", "services", "first_setup_pending",
              "version_since")
SAVED_RE = re.compile(r"^config-\d{4}-\d{2}-\d{2}-\d{6}-[a-z]+(-[a-z]+)*\.json$")  # each part can match only one way


SECRET_VPN = ("wireguard_private_key", "openvpn_password", "openvpn_user")


def install_choice(data_dir):
    """The Install apps choice (DASH-268), so a restore on a rebuilt server can bring the same apps back: the apps,
    folders, user and group, time zone, Reelix version and the VPN's provider. Never a key or password: the VPN's
    secrets are asked again, and every app's own secrets are made up again when the files are written."""
    from . import stack
    choice = stack.current_choice(data_dir) if data_dir else None
    if not choice:
        return None
    out = {k: choice[k] for k in ("apps", "config_dir", "data_dir", "puid", "pgid", "tz", "reelix_edition") if k in choice}
    if choice.get("vpn"):
        out["vpn"] = {k: v for k, v in choice["vpn"].items() if k not in SECRET_VPN}
    return out


def export(config, version, data_dir=None):
    d = config.data
    out = {
        "format": FORMAT,
        "version": version,
        "schema": SCHEMA,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "settings": {k: d[k] for k in GENERAL_KEYS if k in d},
        "services": d["services"],
    }
    out["settings"].update({k: d[k] for k in OTHER_KEYS if k in d})
    install = install_choice(data_dir)
    if install:
        out["install"] = install
    if data_dir:
        out["plugins"] = plugin_settings(data_dir)
        out["logos"] = logo_choices(data_dir)
    return out


def plugin_settings(data_dir):
    """Each added plug-in: where it came from, whether it is active, and its settings (secrets as the apps' keys)."""
    from . import plugins_admin
    out = {}
    root = os.path.join(data_dir, "plugins")
    for pid in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if pid.startswith(".") or not os.path.isfile(os.path.join(root, pid, "manifest.json")):
            continue
        read = lambda name, default: plugins_admin._read(os.path.join(root, pid, name), default)  # noqa: E731
        manifest = read("manifest.json", {})
        out[pid] = {"name": manifest.get("name", pid), "version": manifest.get("version", ""), "manifest": manifest,
                    "state": read("state.json", {}), "settings": read("settings.json", {})}
    return out


def logo_choices(data_dir):
    """The tone chosen for each channel and station logo, and which station logo file is whose."""
    out = {}
    for name in ("network-logos.json", "station-logos.json"):
        try:
            with open(os.path.join(data_dir, "library", name), encoding="utf-8") as f:
                got = json.load(f)
        except (OSError, ValueError):
            continue
        out[name] = {k: {f: v[f] for f in ("tone", "file") if f in v} for k, v in got.items()
                     if isinstance(v, dict) and ("tone" in v or "file" in v)}
    return out


def _restore_others(config, settings):
    from .activity import KEEP_CHOICES
    d = config.data
    if settings.get("history_keep_days") in KEEP_CHOICES:
        d["history_keep_days"] = settings["history_keep_days"]
    if isinstance(settings.get("history_cleared_at"), str) and len(settings["history_cleared_at"]) <= 40:
        d["history_cleared_at"] = settings["history_cleared_at"]
    cats = settings.get("plugin_catalogues")
    if isinstance(cats, list):
        d["plugin_catalogues"] = [{"url": str(c["url"])[:300], "name": str(c.get("name", ""))[:80]} for c in cats[:20]
                                  if isinstance(c, dict) and str(c.get("url", "")).startswith("https://")]


def restore_plugin_settings(data_dir, saved):
    """Puts back the settings of plug-ins added here; returns the names of those that are not added here yet."""
    from . import plugins_admin
    missing = []
    for pid, p in (saved or {}).items() if isinstance(saved, dict) else []:
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,39}$", str(pid)) or not isinstance(p, dict):
            continue
        where = os.path.join(data_dir, "plugins", pid)
        if not os.path.isfile(os.path.join(where, "manifest.json")):
            missing.append(str(p.get("name") or pid))
            continue
        if isinstance(p.get("settings"), dict):
            spec = {s.get("key"): s.get("type") for s in (plugins_admin._read(os.path.join(where, "manifest.json"), {}) or {}).get("settings") or []}
            fits = {k: v for k, v in p["settings"].items() if spec.get(k) not in (None, "custom")}
            try:
                plugins_admin.save_settings(data_dir, pid, fits)
            except (ValueError, OSError):
                missing.append(f"{p.get('name') or pid} (its settings did not fit this version)")
    return missing


def restore_logo_choices(data_dir, saved):
    for name in ("network-logos.json", "station-logos.json"):
        got = (saved or {}).get(name) if isinstance(saved, dict) else None
        if not isinstance(got, dict):
            continue
        path = os.path.join(data_dir, "library", name)
        try:
            with open(path, encoding="utf-8") as f:
                now = json.load(f)
        except (OSError, ValueError):
            now = {}
        for k, v in list(got.items())[:5000]:
            if isinstance(v, dict):
                now.setdefault(str(k)[:120], {}).update({f: str(v[f])[:200] for f in ("tone", "file") if f in v})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(now, f)


def apps_to_bring_back(backup, data_dir):
    """The backup's install choice when its apps are not on this computer (no data/stack yet), else None."""
    from . import stack
    install = (backup or {}).get("install") if isinstance(backup, dict) else None
    if not isinstance(install, dict) or not isinstance(install.get("apps"), list) or stack.chosen_keys(data_dir):
        return None
    return {k: install[k] for k in ("apps", "config_dir", "data_dir", "puid", "pgid", "tz", "reelix_edition", "vpn") if k in install}


def restore(config, backup):
    """Replaces apps and settings with the backup's, after checking every part. Password and sessions stay.

    A backup from an older version is brought up to date the way an old settings file is (backups before 0.7.4
    say no schema, so they count as schema 1). Unknown settings are ignored, a choice that no longer exists goes
    back to the default, and an app of a kind Starboard no longer knows becomes a plain link."""
    if not isinstance(backup, dict) or backup.get("format") != FORMAT:
        raise ConfigError("This is not a Starboard settings backup")
    services = backup.get("services")
    settings = backup.get("settings") or {}
    if not isinstance(services, list) or not isinstance(settings, dict):
        raise ConfigError("This backup is incomplete")
    schema = backup.get("schema") if isinstance(backup.get("schema"), int) else 1
    services = migrate({"schema": schema, "services": json.loads(json.dumps(services))})["services"]
    settings = dict(settings)
    for key, allowed in (("design", DESIGNS), ("upcoming_view", UPCOMING_VIEWS), ("upcoming_days", UPCOMING_DAYS)):
        if key in settings and settings[key] not in allowed:
            settings[key] = DEFAULTS[key]
    clean = []
    seen = set()
    for s in services:
        if isinstance(s, dict) and s.get("type") not in SERVICE_TYPES:
            s = dict(s, type="link")
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
            _restore_others(config, settings)
            config.data.pop("first_setup_pending", None)  # a restored server counts as set up (DASH-238)
            config.data["services"] = clean
            config.save()
        except (ConfigError, ValueError, TypeError):
            config.data.clear()
            config.data.update(saved)
            config.save()
            raise
    return len(clean)


def saved_copies(config):
    from .config import saved_versions
    folder = os.path.join(config.data_dir, "backups")
    versions = saved_versions(folder)
    out = []
    for path in sorted(glob.glob(os.path.join(folder, "config-*.json")), reverse=True)[:30]:
        name = os.path.basename(path)
        reason = name.rsplit("-", 1)[-1].removesuffix(".json")
        out.append({"name": name, "saved": os.path.getmtime(path), "size": os.path.getsize(path), "version": versions.get(name, ""),
                    "reason": {"migration": "Before an update changed the settings", "restore": "Before a restore"}.get(reason, reason)})
    return out


def _saved(config, name):
    if len(name or "") > 80 or not SAVED_RE.match(name or ""):
        raise ConfigError("Choose a saved copy from the list")
    with open(os.path.join(config.data_dir, "backups", name), encoding="utf-8") as f:
        return json.load(f)


def saved_detail(config, name):
    """What one saved copy holds, read only when it is opened (the list reads none of the files)."""
    data = _saved(config, name)
    services = [s for s in data.get("services") or [] if isinstance(s, dict)]
    return {"name": name, "site_name": data.get("site_name", ""), "apps": len(services),
            "categories": [g for g in data.get("groups") or [] if isinstance(g, str)],
            "app_names": sorted(str(s.get("name", "")) for s in services)[:60]}


def export_saved(config, name, version):
    """A saved copy in the download format, so it can be restored from a file later. Never the password."""
    data = _saved(config, name)
    return {"format": FORMAT, "version": version, "schema": data.get("schema", 1), "created": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(
        os.path.getmtime(os.path.join(config.data_dir, "backups", name)))),
        "settings": {k: data[k] for k in GENERAL_KEYS if k in data}, "services": data.get("services", [])}


def restore_saved(config, name):
    data = _saved(config, name)
    # Saved copies are whole settings files: turn them into the backup format, keeping the password.
    return restore(config, {"format": FORMAT, "schema": data.get("schema", 0), "settings": data, "services": data.get("services", [])})


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
                # Optional, when the host job writes them: what went in, what could not be read, earlier runs.
                for key in ("included", "unreadable"):
                    if isinstance(raw.get(key), list):
                        status[key] = [str(x)[:300] for x in raw[key][:200]]
                if isinstance(raw.get("runs"), list):
                    status["runs"] = [{k: r.get(k) for k in ("status", "started", "finished", "summary")}
                                      for r in raw["runs"][:20] if isinstance(r, dict)]
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


def server_file(name):
    """A file the server backup job made, by name, for downloading. None if it is not one of them."""
    folder = backup_dir()
    if not folder or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,200}$", name or ""):
        return None
    path = os.path.join(folder, name)
    ok = os.path.isfile(path) and re.search(r"\.(zip|tar|tar\.gz|tgz|gz|7z|dump|sql|md)$", path)
    return path if ok else None


def request_server_backup(with_prompt=False, keep=None, scheduled=False):
    jobs = jobs_dir()
    if not jobs:
        raise ConfigError("No server backup job is set up. See the help article Back up the whole server")
    path = os.path.join(jobs, "requests", "backup-with-prompt" if with_prompt else "backup")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"keep": int(keep) if keep else None, "scheduled": bool(scheduled)}, f)
    except OSError:
        raise ConfigError("Starboard cannot ask for a backup: the requests folder is not writable") from None


# Other jobs on the host --------------------------------------------------------------
# The same requests folder runs other jobs too, such as a server check: each writes <name>.json like the backup
# job does. Starboard lists every job it finds there (apart from the backups) and can ask for one to run.

JOB_TITLES = {"check": "Server check"}


def jobs_status():
    jobs = jobs_dir()
    if not jobs or not os.path.isdir(jobs):
        return {"configured": False, "items": []}
    out = []
    for path in sorted(glob.glob(os.path.join(jobs, "*.json"))):
        name = os.path.basename(path)[:-5]
        if name in JOB_NAMES or not re.match(r"^[a-z][a-z0-9-]{0,30}$", name):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            continue
        item = {k: raw.get(k) for k in ("status", "started", "finished", "summary", "exit")}
        item.update(name=name, title=raw.get("title") or JOB_TITLES.get(name) or name.replace("-", " ").capitalize(),
                    output=str(raw.get("output") or "")[-12000:])
        if os.path.exists(os.path.join(jobs, "requests", name)) and item["status"] != "running":
            item["status"] = "waiting"
        out.append(item)
    return {"configured": True, "can_run": os.access(os.path.join(jobs, "requests"), os.W_OK), "items": out}


def request_job(name):
    if name in JOB_NAMES or name not in {j["name"] for j in jobs_status()["items"]}:
        raise ConfigError("Choose a job from the list")
    try:
        with open(os.path.join(jobs_dir(), "requests", name), "w"):
            pass
    except OSError:
        raise ConfigError("Starboard cannot ask for the job: the requests folder is not writable") from None
