"""Reelix's own backups, logs and scheduled tasks in Starboard's System pages (DASH-201, 202, 203). Reelix keeps them
behind its admin password, so Starboard asks for it when the section is opened (decision, owner, 9 November 2026,
since RFX-84 was not asked upstream). Backups: the list, the schedule and how many to keep, Make one now and Restore.
Logs: the newest lines, with a level filter. Tasks: each scheduled task with its last and next run, and Run now."""
LEVELS = ("error", "warn", "info", "debug")


def backups(reelix):
    _, o = reelix.call("GET", "/system/backups")
    o = o or {}
    return {"backups": [{"name": b.get("name"), "kind": b.get("kind"), "size": b.get("size_bytes") or 0, "when": b.get("created_at"),
                         "version": b.get("version")} for b in o.get("backups") or []],
            "every": (o.get("settings") or {}).get("interval_days", 7), "keep": (o.get("settings") or {}).get("retention", 5),
            "folder": o.get("backup_dir") or "", "restore_waiting": bool(o.get("pending_restore"))}


def backup_now(reelix):
    reelix.call("POST", "/system/backups", timeout=300, ok=(200, 201, 202))
    return {**backups(reelix), "done": "Reelix made a backup"}


def backup_settings(reelix, every, keep):
    try:
        every, keep = int(every), int(keep)
    except (TypeError, ValueError):
        raise ValueError("Days and how many to keep are whole numbers") from None
    if not (0 <= every <= 365 and 1 <= keep <= 100):
        raise ValueError("Every 0 to 365 days (0 is off), keeping 1 to 100")
    reelix.call("PUT", "/system/backups/settings", {"interval_days": every, "retention": keep})
    return {**backups(reelix), "done": "Backup schedule saved" if every else "Scheduled backups are off"}


def restore(reelix, name):
    name = str(name or "")
    if not name or "/" in name or ".." in name or len(name) > 200:
        raise ValueError("Choose a backup from the list")
    reelix.call("POST", f"/system/backups/{name}/restore", ok=(200, 202, 204))
    return {**backups(reelix), "done": "Reelix restores this backup when it starts again. Restart Reelix on System, Apps"}


def logs(reelix, level="", lines=200):
    params = {"limit": max(20, min(int(lines or 200), 1000))}
    if level in LEVELS:
        params["level"] = level
    _, o = reelix.call("GET", "/system/logs?" + "&".join(f"{k}={v}" for k, v in params.items()))
    o = o or {}
    return {"lines": [{"when": e.get("time"), "level": e.get("level") or "", "where": e.get("target") or "", "message": e.get("message") or ""}
                      for e in o.get("entries") or []], "cut": bool(o.get("truncated"))}


def tasks(reelix):
    _, t = reelix.call("GET", "/system/tasks")
    _, j = reelix.call("GET", "/system/jobs?limit=20")
    return {"tasks": [{"kind": x.get("kind"), "name": x.get("name") or x.get("kind"), "on": x.get("enabled", True), "running": x.get("running", False),
                       "last": x.get("last_run"), "next": x.get("next_run"), "error": x.get("last_error") or ""} for x in t or []],
            "recent": [{"kind": x.get("kind"), "status": x.get("status"), "when": x.get("finished_at") or x.get("started_at") or x.get("created_at"),
                        "error": x.get("error") or ""} for x in (j.get("items") if isinstance(j, dict) else j) or []]}


def run_task(reelix, kind):
    kind = str(kind or "")
    if not kind.replace("_", "").isalnum():
        raise ValueError("Choose a task from the list")
    reelix.call("POST", f"/system/tasks/{kind}/run", ok=(200, 202, 204))
    return {**tasks(reelix), "done": "Reelix started it"}
