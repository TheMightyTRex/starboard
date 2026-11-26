"""The server's settings zip, copied to the same places as the full backups, always encrypted first (owner, 26 November 2026).

The server's own backup job (backup-settings.py on the owner's server) writes server-settings-DATE.zip. It holds API keys
and passwords, so it never leaves the computer as it is. After the job has written the zip it asks Starboard (the
settings-copy call of the public API, or Copy now on the page) to send it to every place that is activated. Starboard
encrypts while it copies, with rclone's own "crypt" layer, then reads the copy back by its checksum before the place
counts as safe.

Why rclone crypt (and not age or Starboard's own format): the copy has to be opened on a day when the server and Starboard
may both be gone. rclone is one small program that runs on any computer, is already the program that sends the copy, and
documents its crypt format publicly. Nothing new is installed. The key is two phrases, shown once and kept by the owner in
their password manager; Starboard keeps a copy in its own folder (readable by Starboard only, never in a backup) only so
it can encrypt the next one. A place that cannot be written through crypt is not sent the zip: the plain file is never
uploaded.

Nothing runs between copies: no thread, no timer.
"""
import json
import os
import re
import secrets
import stat
import threading
import time

from . import backup, backup_copies, folders, full_backup, logs

KEY_FILE = "settings-zip-key.json"
STATUS = "settings-zip-status.json"
NAME_RE = re.compile(r"^server-settings-\d{4}-\d{2}-\d{2}\.zip$")
SUFFIX = ".enc"
SETTINGS_GLOB = r"^server-settings-[0-9-]+\.zip$"
_lock = threading.Lock()


class ZipError(Exception):
    pass


# The key -----------------------------------------------------------------------------------------------------------

def _read_key(data_dir):
    try:
        with open(os.path.join(data_dir, KEY_FILE), encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and len(str(raw.get("password"))) >= 16 and len(str(raw.get("salt"))) >= 16:
            return raw
    except (OSError, ValueError):
        pass
    return None


def key_status(data_dir):
    k = _read_key(data_dir)
    return {"set": bool(k), "made": (k or {}).get("made")}


def make_key(data_dir, replace=False):
    """Makes the two phrases and keeps them. Returns the recovery card, once: the page shows it and it is never read
    back. A key already kept is not replaced unless replace is true, as copies made with it need it."""
    if _read_key(data_dir) and not replace:
        raise ZipError("A key is kept already. Replacing it means older copies need the old key: keep that safe")
    key = {"password": secrets.token_urlsafe(24), "salt": secrets.token_urlsafe(24), "made": time.time()}
    path = os.path.join(data_dir, KEY_FILE)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(key, f)
    os.replace(path + ".tmp", path)
    return card(key)


def forget_key(data_dir):
    try:
        os.remove(os.path.join(data_dir, KEY_FILE))
    except FileNotFoundError:
        pass


def card(key):
    """What the owner stores: the two phrases and the exact commands that open a copy on any computer with rclone."""
    return {"password": key["password"], "salt": key["salt"], "text": (
        "Starboard server settings backup key\n"
        f"Password: {key['password']}\n"
        f"Salt: {key['salt']}\n\n"
        "To open a copy on any computer with rclone installed (rclone.org):\n"
        "  rclone config create settingscrypt crypt remote /folder/with/the/copies filename_encryption off \\\n"
        "    directory_name_encryption false suffix .enc password PASSWORD password2 SALT --obscure\n"
        "  rclone copy settingscrypt: /folder/to/put/the/zips --include 'server-settings-*.zip'\n"
        "Replace PASSWORD and SALT with the two phrases above. Without them the copies cannot be opened.\n")}


# Where the zip is ----------------------------------------------------------------------------------------------------

def _host_of(path):
    """The computer's own path for a folder that Starboard sees inside its container (from its own mounts)."""
    from . import containers, stack
    if not containers.available():
        raise ZipError("Starboard needs Docker access to make copies")
    path = os.path.abspath(path)
    me = os.environ.get("HOSTNAME", "")
    best = None
    try:
        own = containers.docker("GET", f"/containers/{me}/json") if re.match(r"^[0-9a-f]{12,64}$", me) else {}
    except containers.DockerError:
        own = {}
    for m in own.get("Mounts") or []:
        dest = m.get("Destination", "")
        if (path == dest or path.startswith(dest.rstrip("/") + "/")) and stack._SAFE_PATH.match(m.get("Source", "")):
            if best is None or len(dest) > len(best[0]):
                best = (dest, m["Source"])
    if best:
        return best[1] + path[len(best[0]):]
    if os.path.exists("/.dockerenv"):
        raise ZipError("Starboard cannot find where the server backups folder is on this computer")
    return path


def zip_path(folder, name):
    """The settings zip called `name` inside `folder`, as a real path, or None. The name must be exactly a server settings
    zip's (no folder part, no ..), the folder is resolved, and the file must be a plain file that stays inside it: a link
    (to a file or a folder elsewhere) or an absolute name is refused, never followed."""
    if not folder or not isinstance(name, str) or not NAME_RE.fullmatch(name):
        return None
    root = os.path.realpath(folder)
    path = os.path.normpath(os.path.join(root, name))
    if os.path.dirname(path) != root or os.path.commonpath([root, path]) != root:
        return None
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode) or os.path.realpath(path) != path:  # not a link, not a folder, nowhere else
        return None
    return path


def newest_zip():
    """The newest server settings zip in the server backups folder: (name, size) or None."""
    folder = backup.backup_dir()
    best = None
    if folder and os.path.isdir(folder):
        for name in os.listdir(folder):
            p = zip_path(folder, name)
            if p and (best is None or name > best[0]):
                best = (name, os.path.getsize(p))
    return best


# Status ---------------------------------------------------------------------------------------------------------------

def status(data_dir, dest):
    return backup_copies._per_place(data_dir, STATUS, dest) or {"state": "none"}


def _say(data_dir, dest, **kw):
    now = status(data_dir, dest)
    now.update(kw)
    backup_copies._set_per_place(data_dir, STATUS, dest, now)


def overview(data_dir):
    """For the page and the API: the key, and each place's last settings copy in words."""
    rows = []
    for d in backup_copies.destinations(data_dir):
        st = status(data_dir, d["id"])
        words = {"running": "Copying", "done": "Encrypted, copied and read back", "failed": "Failed"}.get(st.get("state"), "Not copied yet")
        shape = {"running": "refresh-cw", "done": "circle-check", "failed": "circle-alert"}.get(st.get("state"), "circle")
        rows.append({"id": d["id"], "title": backup_copies.title_of(d), "enabled": d["enabled"], "state": st.get("state"), "state_word": words, "shape": shape,
                     "file": st.get("file") or "", "finished": st.get("finished"), "error": st.get("error") or ""})
    zip_ = newest_zip()
    return {"key": key_status(data_dir), "places": rows, "newest": {"name": zip_[0], "size": zip_[1]} if zip_ else None,
            "encryption": "rclone crypt"}


# Copying -------------------------------------------------------------------------------------------------------------

def start(data_dir, name=None):
    """Copies the zip (by name, in the server backups folder; the newest when none is given) to every place that is activated,
    encrypted, in the background. Refused with no key, no place, or a copy running already."""
    key = _read_key(data_dir)
    if not key:
        raise ZipError("Make the key for the server settings copies first: they are never sent without being encrypted")
    zip_ = newest_zip()
    folder = backup.backup_dir()
    if name is None:
        if not zip_:
            raise ZipError("There is no server settings backup to copy yet")
        name = zip_[0]
    if not zip_path(folder, name):
        raise ZipError("That is not a server settings backup in the server backups folder. Only a plain file named server-settings-DATE.zip inside it is sent, never a link or another folder")
    places = [d for d in backup_copies.destinations(data_dir) if d["enabled"]]
    if not places:
        raise ZipError("Activate a place for the copies first")
    host_folder = _host_of(folder)
    if not _lock.acquire(blocking=False):
        raise ZipError("A server settings copy is being made already")
    for d in places:
        _say(data_dir, d["id"], state="running", started=time.time(), finished=None, file=name, error="")
    threading.Thread(target=_go, args=(data_dir, places, name, host_folder, key), name="settings-zip-copy", daemon=True).start()
    return overview(data_dir)


def _go(data_dir, places, name, host_folder, key):
    failed = []
    try:
        for d in places:  # one failing never stops the others
            try:
                said = _copy_one(data_dir, d, name, host_folder, key)
                _say(data_dir, d["id"], state="done", finished=time.time(), said=said)
                logs.event("info", "backup", f"Server settings copy to {backup_copies.title_of(d)}: {said}")
            except Exception as e:  # noqa: BLE001 - the page says what
                why = str(e) or e.__class__.__name__
                _say(data_dir, d["id"], state="failed", finished=time.time(), error=why)
                failed.append((backup_copies.title_of(d), why))
                logs.event("warning", "backup", f"Server settings copy to {backup_copies.title_of(d)} failed: {why}")
        if failed:
            logs.event("error", "backup", "Server settings backup not safe: " + "; ".join(f"{n}: {w}" for n, w in failed)[:600])
    finally:
        _lock.release()


def script_for(s, name, keep, inner):
    """The helper's script: encrypt while copying to `inner` (the place as the helper sees it), read it back by checksum,
    keep the newest `keep`. The passphrases come from files, never the command line. Returns the script text."""
    q = backup_copies._q
    crypt = (f":crypt,remote={q_inner(inner)},filename_encryption=off,directory_name_encryption=false,suffix={SUFFIX}:")
    rc = "rclone --config /c/rclone.conf --contimeout 30s --timeout 5m --retries 3"
    return (
        'export RCLONE_CRYPT_PASSWORD="$(rclone obscure - < /c/szpass)" RCLONE_CRYPT_PASSWORD2="$(rclone obscure - < /c/szsalt)"; '
        f"C={q(crypt)}; "
        f"{rc} copyto /s/{name} \"$C\"{name} && "
        f"{rc} cryptcheck --one-way --include {q(name)} /s \"$C\" && "
        f"{rc} lsf --files-only \"$C\" | grep -E {q(SETTINGS_GLOB)} | sort -r | tail -n +{int(keep) + 1} | "
        f"while read -r old; do {rc} deletefile \"$C\"\"$old\" || exit 5; done && "
        f"echo COUNT $({rc} lsf --files-only \"$C\" | grep -cE {q(SETTINGS_GLOB)})")


def q_inner(inner):
    """A place for rclone's connection string: in double quotes, with the few characters that matter escaped."""
    if re.search(r'[\x00-\x1f"]', inner):
        raise ZipError("That place has a character rclone cannot use here")
    return '"' + inner + '"'


def _copy_one(data_dir, d, name, host_folder, key):
    from . import stack
    s, sec = backup_copies.settings(data_dir, d["id"]), backup_copies.secrets(data_dir, d["id"])
    env = stack.env_values(data_dir)
    host = stack.host_folder(data_dir)
    if not host:
        raise ZipError("Starboard cannot find its own folder on this computer")
    work = os.path.join(data_dir, backup_copies.WORK)
    os.makedirs(work, mode=0o700, exist_ok=True)
    os.chmod(work, 0o700)
    binds = [f"{host_folder}:/s:ro", f"{os.path.dirname(host)}/{backup_copies.WORK}:/c"]
    volumes, network = [], "none"
    if s["kind"] == "disk":
        root, folder = full_backup._place(s["folder"])
        binds.append(f"{root}:/t")
        inner = "/t" + folder[len(root):]
    elif s["kind"] in ("smb", "nfs"):
        volumes, inner = [backup_copies._share_volume(s, sec, env)], "/t"
    else:
        inner, network = s["remote"], "bridge"
    files = {"szpass": key["password"], "szsalt": key["salt"], "rclone.conf": sec["rclone_config"] if s["kind"] == "rclone" else ""}
    try:
        for fname, text in files.items():
            fd = os.open(os.path.join(work, fname), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
        script = script_for(s, name, s["keep_settings"], inner)
        owner = f"{os.getuid()}:{os.getgid()}"
        script = f"{script}; code=$?; chown {owner} /c/rclone.conf 2>/dev/null; chmod 600 /c/rclone.conf 2>/dev/null; exit $code"
        code, said = backup_copies._helper(script, binds, image=backup_copies.RCLONE_IMAGE, network=network, volumes=volumes)
        backup_copies.log_detail(data_dir, f"Server settings copy to {backup_copies.where(s)}", said, code)
        if s["kind"] == "rclone":  # a refreshed sign-in token
            try:
                with open(os.path.join(work, "rclone.conf"), encoding="utf-8") as f:
                    after = f.read()
                if after.strip() and after != sec["rclone_config"]:
                    backup_copies.save(data_dir, {k: v for k, v in s.items() if k != "detailed_log"}, {**sec, "rclone_config": after}, s["id"])
            except OSError:
                pass
    finally:
        for v in volumes:
            backup_copies._let_go(v)
        for fname in files:
            try:
                os.remove(os.path.join(work, fname))
            except OSError:
                pass
    if code:
        raise ZipError(_plain(said, s))
    m = re.search(r"COUNT (\d+)", said)
    n = int(m.group(1)) if m else None
    return f"Encrypted, copied to {backup_copies.where_words(s)} and read back" + (f"; {n} kept there" if n is not None else "")


def _plain(said, s):
    t = said.strip().lower()
    if "hash" in t and ("unsupported" in t or "no common" in t or "not support" in t):
        return "This place cannot check a copy by its checksum, so the settings copy was not counted as safe"
    if "differ" in t or "not the same" in t or "cryptcheck" in t and "error" in t:
        return "The copy did not read back the same as the original, so it was not counted as safe"
    return backup_copies._plain(said, s)
