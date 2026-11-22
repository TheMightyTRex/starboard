"""Where Reelix keeps its own backups (DASH-386): next to its settings, as it does by itself, or in the media folder,
which on most servers is another disk than the settings folder, so a failed system disk does not take both.

Reelix's container sees two folders of the computer: its settings (/config) and the media folder (/data). Its backup
folder is `[paths] backup_dir` in /config/config.toml, read when Reelix starts, with no setting in its API. So
Starboard writes that one key (comments and every other line stay as they are), moves the backups already made to the
new folder, and the page offers Restart Reelix. Nothing here runs unless the person opens Reelix's backups or changes
the choice: one small read through Docker when the list is opened.
"""
import io
import re
import tarfile
import urllib.parse

from . import containers

REELIX = "reelix"
CONFIG = "/config/config.toml"
PLACES = {"settings": "/config/backups", "media": "/data/backups/reelix"}
_TABLE = re.compile(r"^\s*\[\s*([A-Za-z0-9_.-]+)\s*\]\s*(#.*)?$")
_KEY = re.compile(r"^\s*backup_dir\s*=")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


def with_backup_dir(text, folder):
    """config.toml's text with [paths] backup_dir set to folder, or taken out for None (Reelix's own default, next to
    its settings). Only that line changes."""
    lines = text.split("\n")
    out, table, done, paths_at = [], "", False, None
    for line in lines:
        m = _TABLE.match(line)
        if m:
            table = m.group(1)
            if table == "paths":
                paths_at = len(out)
        elif table == "paths" and _KEY.match(line):
            if folder is not None and not done:
                out.append(f'backup_dir = "{folder}"')
                done = True
            continue  # the old line goes (a second one would stop Reelix reading the file)
        out.append(line)
    if folder is not None and not done:
        new = f'backup_dir = "{folder}"'
        if paths_at is None:
            if out and out[-1] == "":
                out.pop()
            out += ([""] if out else []) + ["[paths]", new, ""]
        else:
            out.insert(paths_at + 1, new)
    return "\n".join(out)


def backup_dir_in(text):
    """The folder config.toml sets, or None when it leaves Reelix's default."""
    table = ""
    for line in text.split("\n"):
        m = _TABLE.match(line)
        if m:
            table = m.group(1)
        elif table == "paths" and _KEY.match(line):
            value = line.split("=", 1)[1].split("#")[0].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                return value[1:-1]
    return None


def _config_file():
    """(config.toml's text, its mode); ("", 0o644) when Reelix has not written one yet."""
    try:
        raw = containers.docker("GET", f"/containers/{REELIX}/archive?path={urllib.parse.quote(CONFIG)}", raw=True, timeout=20)
    except containers.DockerError as e:
        if "404" in str(e):
            return "", 0o644
        raise
    with tarfile.open(fileobj=io.BytesIO(raw[:4 * 1024 * 1024])) as tar:
        member = next((m for m in tar.getmembers() if m.isfile()), None)
        return (tar.extractfile(member).read().decode("utf-8", "replace"), member.mode & 0o777) if member else ("", 0o644)


def _mounts():
    """{folder inside Reelix: folder on the computer} for /config and /data, from its container."""
    info = containers.docker("GET", f"/containers/{REELIX}/json") or {}
    env = dict(e.split("=", 1) for e in (info.get("Config") or {}).get("Env") or [] if "=" in e)
    user = f"{env.get('PUID', '1000')}:{env.get('PGID', '1000')}"
    return {m.get("Destination"): m.get("Source") for m in info.get("Mounts") or [] if m.get("Destination") in ("/config", "/data")}, \
        user if re.fullmatch(r"\d+:\d+", user) else "1000:1000"


def _key_of(folder):
    return next((k for k, v in PLACES.items() if v == (folder or PLACES["settings"]).rstrip("/")), "other")


def place(data_dir, running_folder):
    """What the page shows: {"now": where Reelix keeps them as it runs, "chosen": what config.toml says, "restart":
    True while the two differ, "choices": [{"key", "folder" (on the computer), "disk", "system"}], "other": the
    folder when it is one Starboard did not choose, "same_disk": True when the media folder is on the settings' disk}.
    None when Reelix is not a container Starboard can read (added by hand, or no Docker access)."""
    from . import full_backup
    try:
        if not containers.available():
            return None
        mounts, _ = _mounts()
        chosen = _key_of(backup_dir_in(_config_file()[0]))
    except (containers.DockerError, OSError, tarfile.TarError):
        return None
    if "/config" not in mounts or "/data" not in mounts:
        return None
    choices = []
    for key, inside in PLACES.items():
        top = "/config" if key == "settings" else "/data"
        folder = mounts[top].rstrip("/") + inside[len(top):]
        disk = full_backup.disk_of(data_dir, folder)
        choices.append({"key": key, "folder": folder, "disk": (disk or {}).get("name") or "", "system": (disk or {}).get("system"),
                        "mount": (disk or {}).get("mount") or ""})
    now = _key_of(running_folder)
    known = all(c["mount"] for c in choices)
    return {"now": now, "chosen": chosen, "restart": now != chosen, "choices": choices, "other": running_folder if now == "other" else "",
            "same_disk": known and choices[0]["mount"] == choices[1]["mount"]}


def choose(data_dir, key, backups, restore_waiting, run_in=None):
    """Sets where Reelix keeps its backups and moves the ones already made (backups: their file names, from Reelix's
    own list). Returns the sentence to show. Raises ValueError in words for the page."""
    if key not in PLACES:
        raise ValueError("Choose next to Reelix's settings or the media folder")
    if restore_waiting:
        raise ValueError("A restore is waiting for Reelix to start again. Restart Reelix first, then choose where its backups go")
    if run_in is None:
        from . import queue_files
        run_in = queue_files.run_in
    try:
        if not containers.available():
            raise ValueError("Starboard needs Docker access to change where Reelix keeps its backups")
        mounts, user = _mounts()
        if "/config" not in mounts or "/data" not in mounts:
            raise ValueError("Starboard did not set this Reelix up, so it cannot change where its backups go")
        text, mode = _config_file()
        was = backup_dir_in(text) or PLACES["settings"]
        new = PLACES[key]
        if was.rstrip("/") == new:
            return "Reelix keeps its backups there already"
        # The folder first, as Reelix's own user, then the backups already made: a file is never written over, and one
        # that would not move stays where it was and is said.
        code, _, err = run_in(REELIX, ["mkdir", "-p", new], user=user, timeout=60)
        if code:
            raise ValueError(f"Reelix could not make the folder {new}: {(err or '').strip()[-200:] or 'no reason given'}")
        left = moved = 0
        for name in backups:
            if not _NAME.match(str(name or "")):
                continue
            code, _, _ = run_in(REELIX, ["mv", "-n", f"{was.rstrip('/')}/{name}", f"{new}/{name}"], user=user, timeout=1800)
            left, moved = left + (1 if code else 0), moved + (0 if code else 1)
        containers.put_file(REELIX, CONFIG, with_backup_dir(text, None if key == "settings" else new).encode("utf-8"), mode=mode)
    except containers.DockerError as e:
        raise ValueError(f"Docker did not do it: {e}") from None
    return ("Reelix keeps its backups " + ("next to its settings" if key == "settings" else "in the media folder")
            + " from its next start" + (f". {moved} moved there" if moved else "")
            + (f". {left} could not be moved and {'stays' if left == 1 else 'stay'} in {was}" if left else ""))
