"""Cloud services as places to bring media in from (DASH-455): OneDrive and Google Drive.

Signing in is the cloud backup wizard's sign-in (DASH-452, starboard/cloud_connect.py), asked for read-only access:
OneDrive with Complete on the phone (once Starboard has its own sign-in at Microsoft) or Complete in this browser;
Google Drive with Complete in this browser only, because reading files that are already in someone's Drive needs
drive.readonly, which Google's sign-in on a phone (the device flow) does not allow. The sign-in's rclone remote is kept
with Bring in media's own secrets (readable by Starboard only, never sent to the browser), apart from the backup copies.

Files are listed and copied down with rclone, in its pinned image in a short-lived helper, into a staging folder on the
media disk (<media>/.starboard-bring-in/<source>), then brought in like any other folder. rclone only reads from the
service: list and copy. The staging folder goes to the holding folder on the media disk at the end.
"""
import json
import os
import re
import shlex

SERVICES = (("onedrive", "OneDrive", "onedrive"), ("gdrive", "Google Drive", "drive"))
WORDS = {k: n for k, n, _ in SERVICES}
SID = {k: s for k, _, s in SERVICES}
REMOTE = "starboard-cloud"
RC = "rclone --config /c/rclone.conf --contimeout 30s --timeout 5m --retries 3"


class CloudSourceError(Exception):
    pass


def ready():
    try:
        from . import cloud_connect  # noqa: F401
    except ImportError:
        return False
    return True


def _secret_key(service):
    return f"cloud:{service}"


def connected(data_dir, service):
    from . import bring_in
    return bool(bring_in._secrets(data_dir).get(_secret_key(service)))


def ways(service):
    """How each service can be signed in to, read only: Google Drive in this browser only."""
    from . import cloud_connect
    phone = service == "onedrive" and bool(cloud_connect.client("onedrive"))
    return (["phone"] if phone else []) + ["browser"]


def places(data_dir):
    out = []
    for key, name, _ in SERVICES:
        on = connected(data_dir, key)
        out.append({"id": f"cloud:{key}", "kind": "cloud", "service": key, "name": name, "ways": ways(key), "ready": on, "path": "",
                    "detail": "Signed in, read only" if on else "Read only. Sign in to choose a folder"})
    return out


# Signing in ----------------------------------------------------------------------------------------------------------

def start(data_dir, service, way):
    from . import cloud_connect
    if service not in SID:
        raise CloudSourceError("Choose OneDrive or Google Drive")
    return cloud_connect.start(data_dir, SID[service], way, read_only=True)


def keep(data_dir, service, session_id):
    """Once signed in, the remote is kept for Bring in media and the sign-in ends. Nothing is written to the backup
    settings."""
    from . import bring_in, cloud_connect
    with cloud_connect._lock:
        sess = cloud_connect._session
        if not sess or sess.get("id") != session_id or sess.get("service") != SID.get(service) or not sess.get("read_only"):
            raise CloudSourceError("That sign-in has ended. Select Start again")
        config = sess.get("config")
    if not config:
        raise CloudSourceError("Sign in first")
    secrets = bring_in._secrets(data_dir)
    secrets[_secret_key(service)] = config
    bring_in._write(data_dir, "secret.json", secrets, private=True)
    cloud_connect.cancel()
    return places(data_dir)


def forget(data_dir, service):
    from . import bring_in
    secrets = bring_in._secrets(data_dir)
    secrets.pop(_secret_key(service), None)
    bring_in._write(data_dir, "secret.json", secrets, private=True)
    return places(data_dir)


# rclone, read only -----------------------------------------------------------------------------------------------------

def _work(data_dir):
    from . import bring_in
    path = os.path.join(bring_in._dir(data_dir), "work")
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def _host(path, data_dir):
    """The work folder as Docker sees it: Starboard's own folder on this computer when it runs in a container."""
    from . import stack
    host = stack.host_folder(data_dir)
    if host and path.startswith(data_dir.rstrip("/") + "/"):
        return os.path.dirname(host) + path[len(data_dir.rstrip("/")):]
    return path


def _remote(path):
    rel = "/" + str(path or "").strip("/")
    if "\x00" in rel or "/../" in rel + "/" or not re.match(r"^[^\n\r]*$", rel):
        raise CloudSourceError("That is not a folder Starboard can use")
    return f"{REMOTE}:{rel.strip('/')}"


def rclone(data_dir, service, script, binds=(), run=None, timeout=7200):
    """Runs an rclone script with the service's remote, in rclone's own image. The remote's config is handed over in a
    file readable by Starboard only, and read back after, as rclone may refresh the sign-in's token."""
    from . import backup_copies, bring_in
    config = bring_in._secrets(data_dir).get(_secret_key(service))
    if not config:
        raise CloudSourceError(f"Sign in to {WORDS.get(service, 'the service')} first")
    work = _work(data_dir)
    conf = os.path.join(work, "rclone.conf")
    fd = os.open(conf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(config)
    owner = f"{os.getuid()}:{os.getgid()}"
    script = f"{script}; code=$?; chown {owner} /c/rclone.conf 2>/dev/null; chmod 600 /c/rclone.conf 2>/dev/null; exit $code"
    try:
        code, said = (run or backup_copies._helper)(script, list(binds) + [f"{_host(work, data_dir)}:/c"], image=backup_copies.RCLONE_IMAGE,
                                                   network="bridge", timeout=timeout)
        try:
            with open(conf, encoding="utf-8") as f:
                after = f.read()
            if after.strip() and after != config:
                secrets = bring_in._secrets(data_dir)
                secrets[_secret_key(service)] = after
                bring_in._write(data_dir, "secret.json", secrets, private=True)
        except OSError:
            pass
    finally:
        try:
            os.remove(conf)  # Starboard's own short-lived copy; the kept one is in secret.json
        except OSError:
            pass
    return code, said


def _json_list(said):
    try:
        rows = json.loads(said[said.index("["):said.rindex("]") + 1])
    except ValueError:
        return []
    return [r for r in rows if isinstance(r, dict)]


def browse(data_dir, service, rel, run=None):
    """One folder of the cloud service, as the picker shows it."""
    code, said = rclone(data_dir, service, f"{RC} lsjson --dirs-only {shlex.quote(_remote(rel))}", run=run, timeout=180)
    if code:
        raise CloudSourceError(_plain(said, service))
    rel = "/" + str(rel or "").strip("/") if str(rel or "").strip("/") else ""
    names = sorted(str(r["Name"]) for r in _json_list(said) if r.get("IsDir") and r.get("Name") and not str(r["Name"]).startswith("."))
    parts = [p for p in rel.split("/") if p]
    return {"path": rel, "place": f"cloud:{service}", "parent": "/".join(rel.split("/")[:-1]) if rel else None,
            "crumbs": [{"name": WORDS[service], "path": ""}] + [{"name": p, "path": "/" + "/".join(parts[:i + 1])} for i, p in enumerate(parts)],
            "folders": [{"name": n, "path": f"{rel}/{n}"} for n in names[:300]], "free": None, "total": None, "why": ""}


def sizes(data_dir, service, rel, run=None):
    from . import folders
    code, said = rclone(data_dir, service, f"{RC} lsjson -R --files-only --max-depth 6 {shlex.quote(_remote(rel))}", run=run, timeout=300)
    if code:
        return {}
    return folders.group_sizes([(str(r["Path"]), int(r.get("Size") or 0)) for r in _json_list(said) if r.get("Path")])


def files(data_dir, service, rel, run=None, limit=300_000):
    """Every file in the cloud folder, as a look reads a folder: (relative path, size, 0, 0, 0)."""
    code, said = rclone(data_dir, service, f"{RC} lsjson -R --files-only {shlex.quote(_remote(rel))}", run=run, timeout=1800)
    if code:
        raise CloudSourceError(_plain(said, service))
    rows = [r for r in _json_list(said) if r.get("Path") and not any(p.startswith(".") for p in str(r["Path"]).split("/"))]
    return [(str(r["Path"]), int(r.get("Size") or 0), 0, 0, 0) for r in rows[:limit]]


def copy_down(data_dir, source, staging, run=None, stop=None):
    """Copies the cloud folder down into the staging folder on the media disk. rclone copy only reads from the service;
    a copy that was cut off carries on, skipping what is already there with the same size and time."""
    from . import bring_in
    os.makedirs(staging, exist_ok=True)
    code, said = rclone(data_dir, source["kind"], f"{RC} copy --transfers 2 --checkers 4 --exclude '.*' --exclude '.*/**' "
                        f"{shlex.quote(_remote(source['path']))} /d", binds=[f"{staging}:/d"], run=run)
    if code:
        raise bring_in.BringInError(_plain(said, source["kind"]))
    return True


def _plain(said, service):
    low = (said or "").lower()
    name = WORDS.get(service, "The service")
    if "invalid_grant" in low or ("token" in low and ("expired" in low or "revoked" in low)) or "unauthenticated" in low:
        return f"{name} no longer accepts Starboard's sign-in. Sign in again"
    if "directory not found" in low:
        return f"That folder is not in {name} any more"
    if "no space left" in low:
        return "The media disk is full. Free some space, or bring in less"
    if "dial tcp" in low or "no such host" in low or "i/o timeout" in low or "connection refused" in low:
        return f"{name} did not answer. Check this computer is online, then try again"
    return ((said or "").strip().splitlines() or [f"{name} did not answer"])[-1][:240]
