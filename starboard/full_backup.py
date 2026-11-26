"""Full without media (DASH-260, owner, 9 and 12 November 2026): one encrypted file that rebuilds the server on a new
install: Starboard's settings, plug-ins and set-up files (the Compose file and .env), and every app's own settings
and database, from the settings folder. Media is never in it, nor anything that can be fetched again (caches, logs,
transcodes). Pictures (posters, covers, artwork, logos) go in only when asked: they can be most of the size.

Making one: each app stops for the moment its own folder is copied, so its database is copied whole, then starts
again. The copy is written to a folder on another disk (never inside Starboard's own folder), and only the newest
KEEP are kept there. A short-lived helper container does the reading and writing on the computer, with no network.

The file is encrypted with a password the person chooses (AES-256-GCM in 1 MiB parts, the key made with scrypt),
so a copy on a disk or in the cloud gives nothing away. Its header (date, apps, size, with or without pictures) is
not secret, so a new install can list the copies before asking for the password. Restoring needs the same password.

Encryption needs the cryptography library (in Starboard's image, like Pillow); without it, making one says so.
"""
import base64
import datetime
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import struct
import tarfile
import threading
import time

from . import folders

MAGIC = b"STARBOARD-BACKUP\x01"
CHUNK = 1024 * 1024
KEEP = 5
SCRYPT = {"n": 2 ** 15, "r": 8, "p": 1}
NAME_RE = re.compile(r"^starboard-full-\d{4}-\d{2}-\d{2}-\d{6}(-pictures)?\.starboard$")
STATUS = "backup-full.json"
RESTORE_STATUS = "restore-full.json"  # restoring one on this server (DASH-387)
CHECKED = "backup-checked.json"  # which copies read back as written (DASH-381)
WORK = "backup-work"
# Nothing that can be downloaded or made again goes in (owner, 12 November 2026: "take out anything that can be re
# download"): caches, logs, transcodes, fetched artwork and posters, guides, queued download files. On the owner's
# server that leaves about 1.3 GB, mostly Jellyfin's database, which compresses to about a third.
# Starboard's own folder: what never goes in, and the pictures only the person added (station logos from a zip).
KEY_FILE = "backup-key.json"  # the scheduled copies' key (DASH-17): never in a backup itself
# Copies off this computer (DASH-380): the share's password and rclone's config, and the copy's own work folder and status.
COPY_SKIP = ("backup-copies-secret.json", "backup-copies-status.json", "backup-copies-test.json", "backup-copy-work/",
             "settings-zip-key.json", "settings-zip-status.json")
STARBOARD_SKIP = ("sessions.json", "logs/", "backups/", WORK + "/", "plugins/.removed/", "setup-token", "posters/", "icons/", KEY_FILE, *COPY_SKIP,
                  STATUS, RESTORE_STATUS, CHECKED,
                  "library/films.json", "library/tv.json", "library/music.json", "library/books.json", "library/audiobooks.json",
                  "library/radio.json", "library/network-logos.json", "space.json", "usage.json", "disk-temps.json", "imports/")
STARBOARD_PICTURES = ("library/station-logos/",)
# In each app's folder: always left out (it comes back by itself), and the pictures someone may have added by hand.
APP_SKIP = ["*cache*", "*/Cache/*", "*/logs/*", "*/log/*", "*/Logs/*", "*.log", "*.log.*", "*/transcodes/*", "*/transcode/*",
            "*/temp/*", "*/tmp/*", "*/Backups/*", "*/backups/*", "*/crashreports/*", "*.pid", "*/ipc-socket", "*/keyframes/*",
            "*/attachments/*", "*/trickplay/*", "*/__pycache__/*", "*/data/metadata/*", "*/MediaCover/*", "*/nzb/*", "*xmltv*",
            "*/omdb/*", "*/streams/*", "*/collections/*.jpg", "*/collections/*.png", "*.db-shm"]
# Never put back from a backup (older ones hold some of them): what this Starboard is doing now, and its own keys.
NEVER_BACK = (STATUS, RESTORE_STATUS, CHECKED, KEY_FILE, "sessions.json", "setup-token", *(c for c in COPY_SKIP if not c.endswith("/")))
# Left beside a database by an app that did not close it cleanly. Put under an older database they would be played
# into it, so a restore on a running server removes them first (DASH-387).
SIDE_FILES = ("*-wal", "*-shm", "*-journal")
APP_PICTURES = ["*/metadata/items/*", "*/metadata/authors/*", "*/covers/*", "*/logos/*", "*/artwork/*", "*/images/*", "*/item-images/*"]
PICTURE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")

_lock = threading.Lock()
_restoring = threading.Lock()  # held while a full backup is restored on this server (DASH-387)


class BackupError(Exception):
    pass


# Encryption -------------------------------------------------------------------------------------------------------

def _aes():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise BackupError("This Starboard cannot encrypt backups: its image has no cryptography library. Update Starboard, then try again") from None
    return AESGCM


def key_of(password, salt):
    if len(password or "") < 10:
        raise BackupError("Use a backup password of at least 10 characters")
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, dklen=32, maxmem=64 * 1024 * 1024, **SCRYPT)


# Scheduled copies (DASH-17) run with nobody there to type the password, so the person can let Starboard keep the key
# made from it (never the password itself) in its own folder, readable by Starboard only. A copy made with it opens with
# the same password as any other, because the salt the key was made with goes in each copy's header.

def save_key(data_dir, password, folder, pictures):
    _place(folder)
    salt = secrets.token_bytes(16)
    key = key_of(password, salt)
    path = os.path.join(data_dir, KEY_FILE)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"salt": base64.b64encode(salt).decode(), "key": base64.b64encode(key).decode(), "folder": folders.tidy(folder),
                   "pictures": bool(pictures), "saved": time.time()}, f)
    os.replace(path + ".tmp", path)


def saved_key(data_dir):
    """{"salt", "key" (bytes), "folder", "pictures", "saved"}, or None when no key is kept."""
    try:
        with open(os.path.join(data_dir, KEY_FILE), encoding="utf-8") as f:
            raw = json.load(f)
        salt, key = base64.b64decode(raw["salt"]), base64.b64decode(raw["key"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if len(salt) != 16 or len(key) != 32 or not raw.get("folder"):
        return None
    return {"salt": salt, "key": key, "folder": str(raw["folder"]), "pictures": bool(raw.get("pictures")), "saved": raw.get("saved")}


def forget_key(data_dir):
    try:
        os.remove(os.path.join(data_dir, KEY_FILE))
    except FileNotFoundError:
        pass


class Sealed(io.RawIOBase):
    """Writes the header, then the data in encrypted parts; close() seals the last part, so a cut file is refused."""

    def __init__(self, out, key, header):
        self.out, self.aes, self.buf, self.count = out, _aes()(key), bytearray(), 0
        self.last = 0  # how many bytes the last part takes at the end of the file, for the check after writing
        self.prefix = base64.b64decode(header["nonce"])
        self.head = json.dumps(header, sort_keys=True).encode("utf-8")
        out.write(MAGIC + struct.pack(">I", len(self.head)) + self.head)

    def writable(self):
        return True

    def write(self, data):
        self.buf += data
        while len(self.buf) > CHUNK:
            self._part(bytes(self.buf[:CHUNK]), False)
            del self.buf[:CHUNK]
        return len(data)

    def _part(self, plain, last):
        nonce = self.prefix + struct.pack(">I", self.count)
        sealed = self.aes.encrypt(nonce, plain, self.head + (b"last" if last else b"more") + struct.pack(">I", self.count))
        self.out.write(struct.pack(">I", len(sealed)) + sealed)
        self.last = 4 + len(sealed)
        self.count += 1

    def close(self):
        if not self.closed:
            self._part(bytes(self.buf), True)
            self.buf.clear()
        super().close()


def read_header(f):
    if f.read(len(MAGIC)) != MAGIC:
        raise BackupError("This is not a Starboard full backup")
    size = struct.unpack(">I", f.read(4))[0]
    if size > 1024 * 1024:
        raise BackupError("This backup's header is damaged")
    head = f.read(size)
    return json.loads(head.decode("utf-8")), head


class Opened(io.RawIOBase):
    """Reads the parts back; a wrong password, a changed byte or a cut file stops it with a plain message."""

    def __init__(self, f, password):
        self.f = f
        self.header, self.head = read_header(f)
        key = key_of(password, base64.b64decode(self.header["salt"]))
        self.aes, self.prefix = _aes()(key), base64.b64decode(self.header["nonce"])
        self.buf, self.count, self.done = b"", 0, False

    def readable(self):
        return True

    def _next(self):
        raw = self.f.read(4)
        if len(raw) < 4:
            raise BackupError("This backup is cut short: the file did not finish copying")
        want = struct.unpack(">I", raw)[0]
        sealed = self.f.read(want)
        if len(sealed) < want:
            raise BackupError("This backup is cut short: the file did not finish copying")
        nonce = self.prefix + struct.pack(">I", self.count)
        from cryptography.exceptions import InvalidTag
        for last in (False, True):
            try:
                plain = self.aes.decrypt(nonce, sealed, self.head + (b"last" if last else b"more") + struct.pack(">I", self.count))
                self.count += 1
                self.done = last
                return plain
            except InvalidTag:
                continue
        raise BackupError("That password does not open this backup" if self.count == 0 else "This backup is damaged")

    def readinto(self, b):
        while not self.buf and not self.done:
            self.buf = self._next()
        n = min(len(b), len(self.buf))
        b[:n] = self.buf[:n]
        self.buf = self.buf[n:]
        return n


# The helper container -----------------------------------------------------------------------------------------------

def _helper(script, binds, timeout=7200):
    """Runs a script in the helper image with only the given folders and no network; (exit code, output)."""
    from . import containers
    containers.ensure_image()  # DASH-438: downloaded first if it is missing
    body = {"Image": containers.HELPER_IMAGE, "Cmd": ["sh", "-c", script], "Labels": {"starboard.updater": "1"},
            "HostConfig": {"Binds": list(binds), "NetworkMode": "none"}}
    cid = containers.docker("POST", f"/containers/create?name=starboard-backup-{int(time.time() * 1000)}", body)["Id"]
    try:
        containers.docker("POST", f"/containers/{cid}/start")
        code = containers.docker("POST", f"/containers/{cid}/wait", timeout=timeout).get("StatusCode", 1)
        raw = containers.docker("GET", f"/containers/{cid}/logs?stdout=1&stderr=1&tail=200", raw=True)
    finally:
        try:
            containers.docker("DELETE", f"/containers/{cid}?force=1")
        except containers.DockerError:
            pass
    text, i = b"", 0
    while i + 8 <= len(raw):
        n = int.from_bytes(raw[i + 4:i + 8], "big")
        text += raw[i + 8:i + 8 + n]
        i += 8 + n
    return code, text.decode("utf-8", "replace")


def _q(text):
    return "'" + str(text).replace("'", "'\\''") + "'"


def _place(path):
    """The usual place a folder is in (/mnt, /srv...), mounted for the helper; refused outside them."""
    path = folders.tidy(path)
    if not folders.allowed(path):
        raise BackupError("Choose a folder under " + ", ".join(folders.ROOTS))
    return next(r for r in folders.ROOTS if path == r or path.startswith(r + "/")), path


# What goes in ---------------------------------------------------------------------------------------------------

def _starboard_files(data_dir, pictures):
    out = []
    for root, dirs, files in os.walk(data_dir):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, data_dir).replace(os.sep, "/")
            if any(rel == s or rel.startswith(s) for s in STARBOARD_SKIP) or ".bak" in name or ".before-" in name or "cache" in rel.lower():
                continue
            if "/data/" in rel and rel.startswith("plugins/") and name.lower().endswith(PICTURE_EXT):
                continue  # a plug-in's fetched posters come back by themselves
            if not pictures and any(rel.startswith(s) for s in STARBOARD_PICTURES):
                continue
            out.append((full, rel))
    return out


def _app_folders(config_dir):
    code, text = _helper("cd /r && for d in */; do [ -d \"$d\" ] && printf '%s\\n' \"${d%/}\"; done", [f"{config_dir}:/r:ro"], timeout=60)
    if code:
        raise BackupError(f"Starboard could not open {config_dir}")
    return [n for n in text.splitlines() if n and folders.NAME.match(n) and not n.startswith(".")]


def _containers_using(config_dir):
    """{app folder: [container ids]} for running containers that mount a folder inside it."""
    from . import containers
    out = {}
    for c in containers.docker("GET", "/containers/json") or []:
        if (c.get("Labels") or {}).get("com.docker.compose.service") == "starboard":
            continue
        for m in c.get("Mounts") or []:
            src = m.get("Source", "")
            if src.startswith(config_dir.rstrip("/") + "/"):
                out.setdefault(src[len(config_dir.rstrip("/")) + 1:].split("/")[0], []).append(c["Id"])
    return out


def _excludes(pictures):
    return " ".join(f"--exclude={_q(p)}" for p in APP_SKIP + ([] if pictures else APP_PICTURES))


# Status -------------------------------------------------------------------------------------------------------------

def _status_path(data_dir):
    return os.path.join(data_dir, STATUS)


def status(data_dir):
    try:
        with open(_status_path(data_dir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"state": "none"}


def _say(data_dir, **kw):
    now = status(data_dir)
    now.update(kw)
    tmp = _status_path(data_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(now, f)
    os.replace(tmp, _status_path(data_dir))


# Checking one after it is made (DASH-381) -------------------------------------------------------------------------------

def _read_back(work, host_work, root, inner, name, key, sealed, size):
    """Reads the copy in the backup folder back: it has the size that was written, it starts with the same header, and
    its last part opens with the key. Cheap on purpose: the helper reads the start and at most 1 MiB of the end, never
    the whole file. Raises BackupError saying which of the three failed."""
    front = MAGIC + struct.pack(">I", len(sealed.head)) + sealed.head
    code, said = _helper(f"f={_q(inner)}/{_q(name)}; [ $(wc -c < \"$f\") -eq {int(size)} ] || exit 4; "
                         f"head -c {len(front)} \"$f\" > /w/check.head && tail -c {int(sealed.last)} \"$f\" > /w/check.tail",
                         [f"{root}:/t:ro", f"{host_work}:/w"], timeout=300)
    if code == 4:
        raise BackupError("it is not the size that was written")
    if code:
        raise BackupError(f"it could not be read: {said.strip()[-200:]}")
    with open(os.path.join(work, "check.head"), "rb") as f:
        if f.read() != front:
            raise BackupError("its start is not what was written")
    with open(os.path.join(work, "check.tail"), "rb") as f:
        tail = f.read()
    from cryptography.exceptions import InvalidTag
    n = struct.pack(">I", sealed.count - 1)
    try:
        if len(tail) < 4 or struct.unpack(">I", tail[:4])[0] != len(tail) - 4:
            raise InvalidTag
        _aes()(key).decrypt(sealed.prefix + n, tail[4:], sealed.head + b"last" + n)
    except InvalidTag:
        raise BackupError("its last part does not open") from None


def checked(data_dir):
    """{file name: {"size", "at"}} for the copies that read back as written."""
    try:
        with open(os.path.join(data_dir, CHECKED), encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in raw.items() if isinstance(v, dict)} if isinstance(raw, dict) else {}


def _note_checked(data_dir, name, size):
    marks = checked(data_dir)
    marks[name] = {"size": int(size), "at": time.time()}
    marks = dict(sorted(marks.items(), key=lambda kv: kv[1].get("at") or 0)[-60:])  # more than any folder keeps
    path = os.path.join(data_dir, CHECKED)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(marks, f)
    os.replace(path + ".tmp", path)


def with_checked(data_dir, items):
    """found()'s list with "checked": when each copy read back as written (seconds), or None. A file whose size has
    changed since is not the one that was checked."""
    marks = checked(data_dir)
    for b in items:
        mark = marks.get(b["name"]) or {}
        b["checked"] = mark.get("at") if mark.get("size") == b["size"] else None
    return items


# Making one -----------------------------------------------------------------------------------------------------------

def start(data_dir, version, password, target, pictures, site_name="", keep=KEEP, saved=None):
    """Starts making one in the background; refuses when one is running or a part is missing. A scheduled copy passes
    the kept key as saved (from saved_key) instead of a password. keep: how many copies stay in the folder."""
    from . import containers, stack
    _aes()
    if saved is None:
        key_of(password, b"0" * 16)
    keep = max(1, min(int(keep), 50))
    if not containers.available():
        raise BackupError("Starboard needs Docker access to copy your apps' settings")
    env = stack.env_values(data_dir)
    config_dir = env.get("CONFIG_DIR")
    if not config_dir:
        raise BackupError("Starboard did not install your apps, so it does not know their settings folder. Settings only still works")
    _place(target)
    host_data = stack.host_folder(data_dir)
    host_data = os.path.dirname(host_data) if host_data else None
    if not host_data:
        raise BackupError("Starboard cannot find its own folder on this computer")
    if _restoring.locked():
        raise BackupError("A full backup is being restored. Make one when it has finished")
    if not _lock.acquire(blocking=False):
        raise BackupError("A backup is being made already")
    _say(data_dir, state="running", step="Starting", started=time.time(), finished=None, error="", file="", target=target, pictures=bool(pictures),
         scheduled=saved is not None)
    threading.Thread(target=_make, args=(data_dir, version, password, target, bool(pictures), config_dir, host_data, site_name, env, keep, saved),
                     daemon=True).start()


def _make(data_dir, version, password, target, pictures, config_dir, host_data, site_name, env, keep=KEEP, saved=None, prune=True):
    """prune=False (the copy made before a restore, DASH-387) leaves every older copy, the one being restored included."""
    from . import containers
    work = os.path.join(data_dir, WORK)
    try:
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(os.path.join(work, "apps"), mode=0o700)
        apps = _app_folders(config_dir)
        using = _containers_using(config_dir)
        for n, app in enumerate(apps, 1):
            _say(data_dir, step=f"Copying {app}'s settings ({n} of {len(apps)})")
            stopped = []
            for cid in using.get(app, []):
                # Noted before it stops, so a Starboard that stops part way starts it again next time (DASH-382).
                _say(data_dir, stopped=stopped + [cid])
                try:
                    containers.docker("POST", f"/containers/{cid}/stop?t=30", timeout=60)
                    stopped.append(cid)
                except containers.DockerError:
                    pass
            try:
                code, said = _helper(f"tar -C /r -czf /w/apps/{_q(app + '.tar.gz')} {_excludes(pictures)} {_q(app)}",
                                     [f"{config_dir}:/r:ro", f"{host_data}/{WORK}:/w"])
            finally:
                for cid in stopped:
                    try:
                        containers.docker("POST", f"/containers/{cid}/start", timeout=60)
                    except containers.DockerError:
                        pass
                _say(data_dir, stopped=[])
            if code not in (0, 1):  # tar's 1: a file changed while it was read
                raise BackupError(f"Copying {app} did not work: {said.strip()[-200:]}")
        _say(data_dir, step="Encrypting")
        salt, nonce = (saved["salt"], secrets.token_bytes(8)) if saved else (secrets.token_bytes(16), secrets.token_bytes(8))
        key = saved["key"] if saved else key_of(password, salt)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        name = f"starboard-full-{stamp}{'-pictures' if pictures else ''}.starboard"
        header = {"format": 1, "kind": "full", "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "version": version,
                  "site_name": site_name, "pictures": pictures, "apps": apps, "config_dir": config_dir,
                  "data_dir": env.get("DATA_DIR", ""), "salt": base64.b64encode(salt).decode(), "nonce": base64.b64encode(nonce).decode(),
                  "kdf": {"name": "scrypt", **SCRYPT}, "cipher": "AES-256-GCM", "part": CHUNK}
        with open(os.path.join(work, name), "wb") as raw:
            sealed = Sealed(raw, key, header)
            with tarfile.open(fileobj=sealed, mode="w|") as tar:
                manifest = json.dumps({k: v for k, v in header.items() if k not in ("salt", "nonce")}).encode()
                info = tarfile.TarInfo("manifest.json")
                info.size, info.mtime = len(manifest), int(time.time())
                tar.addfile(info, io.BytesIO(manifest))
                for full, rel in _starboard_files(data_dir, pictures):
                    try:
                        tar.add(full, arcname=f"starboard/{rel}", recursive=False)
                    except OSError:
                        pass
                for app in apps:
                    tar.add(os.path.join(work, "apps", app + ".tar.gz"), arcname=f"apps/{app}.tar.gz")
            sealed.close()
        size = os.path.getsize(os.path.join(work, name))
        _say(data_dir, step="Moving it to the backup folder")
        root, path = _place(target)
        inner = "/t" + path[len(root):]
        owner = f"{int(env.get('PUID') or 1000)}:{int(env.get('PGID') or 1000)}"  # the person's own user, so they can tidy the folder
        older = f"ls -1t {_q(inner)} | grep -E '^starboard-full-[0-9-]+(-pictures)?\\.starboard$' | tail -n +{int(keep) + 1}"
        # A .part left by a copy that was cut off (the computer stopped) is never a backup: it goes first (DASH-78).
        code, said = _helper(f"mkdir -p {_q(inner)} && find {_q(inner)} -maxdepth 1 -name 'starboard-full-*.starboard.part' -delete && "
                             f"cp /w/{_q(name)} {_q(inner)}/{_q(name + '.part')} && "
                             f"mv {_q(inner)}/{_q(name + '.part')} {_q(inner)}/{_q(name)} && "
                             f"chown {owner} {_q(inner)} {_q(inner)}/{_q(name)} && chmod 600 {_q(inner)}/{_q(name)}",
                             [f"{host_data}/{WORK}:/w:ro", f"{root}:/t"])
        if code:
            raise BackupError(f"Writing to {target} did not work: {said.strip()[-200:]}")
        # DASH-381: the copy in the folder is read back (its size, its start and its last part) before anything older
        # goes. One that does not read back is set aside as a .part, so it never counts as a backup.
        _say(data_dir, step="Checking it reads back")
        try:
            _read_back(work, f"{host_data}/{WORK}", root, inner, name, key, sealed, size)
        except BackupError as e:
            _helper(f"mv {_q(inner)}/{_q(name)} {_q(inner)}/{_q(name + '.part')}", [f"{root}:/t"], timeout=120)
            raise BackupError(f"The backup was written to {target}, but did not read back as it was written ({e}). It is not kept. "
                              "Make it again. If this happens again, check the disk the folder is on") from None
        _note_checked(data_dir, name, size)
        if prune:
            code, said = _helper(f"{older} | while read -r old; do rm -f {_q(inner)}/\"$old\"; done", [f"{root}:/t"], timeout=120)
            if code:
                raise BackupError(f"Removing the older backups in {target} did not work: {said.strip()[-200:]}")
        from . import backup_copies  # DASH-380: a copy off this computer, when one is chosen; never fails the backup
        backup_copies.after_full(data_dir, f"{path}/{name}")
        _say(data_dir, state="done", step="", finished=time.time(), file=f"{path}/{name}", size=size)
    except Exception as e:  # noqa: BLE001 - whatever stops it, the page says what
        _say(data_dir, state="failed", step="", finished=time.time(), error=str(e) or e.__class__.__name__)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        _lock.release()


def start_left_stopped(data_dir):
    """At start (DASH-382): apps a full backup stopped while it copied them, when Starboard itself stopped before it
    could start them again, are started now, and a backup left "running" is marked as stopped. The same for apps a
    restore on this server had stopped (DASH-387). Returns the containers started again; one that would not start
    stays listed, for the next start."""
    from . import containers
    if _lock.locked() or _restoring.locked():
        return []  # being made or restored in this Starboard: it starts its own apps again
    started = []
    for read, write, what in ((status, _say, "Starboard stopped while the backup was being made. Make it again."),
                              (restore_status, _tell, "Starboard stopped while the backup was being restored. The apps were started again. Restore it again.")):
        now = read(data_dir)
        left = [c for c in now.get("stopped") or [] if isinstance(c, str) and re.fullmatch(r"[0-9a-zA-Z_.-]{1,128}", c)]
        still = []
        for cid in left:
            try:
                containers.docker("POST", f"/containers/{cid}/start", timeout=60)
                started.append(cid)
            except containers.DockerError:
                still.append(cid)
        if left or now.get("stopped"):
            write(data_dir, stopped=still)
        if now.get("state") == "running":
            write(data_dir, state="failed", step="", finished=time.time(), error=what)
    return started


# Finding and restoring -------------------------------------------------------------------------------------------------

def found(folder):
    """The full backups in a folder, newest first, each with its header (no password needed)."""
    root, path = _place(folder)
    inner = "/t" + path[len(root):]
    code, text = _helper(f"cd {_q(inner)} 2>/dev/null || exit 0; for f in starboard-full-*.starboard; do [ -f \"$f\" ] || continue; "
                         "s=$(wc -c < \"$f\"); printf '%s\\t%s\\t' \"$f\" \"$s\"; head -c 65536 \"$f\" | base64 | tr -d '\\n'; echo; done",
                         [f"{root}:/t:ro"], timeout=120)
    out = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not NAME_RE.match(parts[0]):
            continue
        try:
            head, _ = read_header(io.BytesIO(base64.b64decode(parts[2])))
        except (BackupError, ValueError, struct.error):
            continue
        out.append({"name": parts[0], "path": f"{path}/{parts[0]}", "size": int(parts[1]), "created": head.get("created"),
                    "version": head.get("version"), "pictures": head.get("pictures"), "apps": head.get("apps", []),
                    "site_name": head.get("site_name", ""), "config_dir": head.get("config_dir", "")})
    return sorted(out, key=lambda b: b["created"] or "", reverse=True)


def restore(data_dir, file_path, password, config_dir=None, puid=1000, pgid=1000, running=False):
    """Puts a full backup back: Starboard's files (its sign-in stays as it is now), then every app's folder into the
    settings folder. Returns {"settings": the settings backup inside, "apps": [...], "config_dir": ...}. The set-up
    then writes the Compose file (keeping the restored .env's secrets) and starts the apps.

    Nothing is changed until the whole file has been read to its last part, so a damaged or cut-off backup leaves
    Starboard and the apps as they were. running=True is for a server whose apps have run since (DASH-387): files an
    app leaves beside a database it did not close cleanly are removed first, so they are never played into the older
    database."""
    from . import containers, stack
    if not containers.available():
        raise BackupError("Starboard needs Docker access to put your apps' settings back")
    root, path = _place(file_path)
    if not NAME_RE.match(os.path.basename(path)):
        raise BackupError("Choose a Starboard full backup (a .starboard file)")
    host_data = stack.host_folder(data_dir)
    host_data = os.path.dirname(host_data) if host_data else None
    if not host_data:
        raise BackupError("Starboard cannot find its own folder on this computer")
    work = os.path.join(data_dir, WORK)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, mode=0o700)
    try:
        # The copy in the folder is readable by its owner only, and the helper writes as root: without the chmod,
        # Starboard, which never runs as root, could not open its own working copy. The work folder itself is private.
        code, said = _helper(f"cp /t{_q(path[len(root):])} /w/in.starboard && chmod 644 /w/in.starboard", [f"{root}:/t:ro", f"{host_data}/{WORK}:/w"])
        if code:
            raise BackupError(f"Starboard could not read {file_path}")
        staged = os.path.join(work, "starboard")
        with open(os.path.join(work, "in.starboard"), "rb") as raw:
            opened = Opened(raw, password)
            header = opened.header
            target = config_dir or header.get("config_dir")
            croot, cpath = _place(target)
            os.makedirs(os.path.join(work, "apps"), mode=0o700)
            with tarfile.open(fileobj=io.BufferedReader(opened, CHUNK), mode="r|") as tar:
                for m in tar:
                    name = m.name
                    if not m.isfile() or name.startswith("/") or ".." in name.split("/"):
                        continue
                    if name.startswith("starboard/"):
                        rel = name[len("starboard/"):]
                        if rel in NEVER_BACK or rel.startswith(("logs/", WORK)):
                            continue
                        dest = os.path.join(staged, rel)  # put in place below, once the whole file has been read
                    elif name.startswith("apps/") and name.endswith(".tar.gz") and folders.NAME.match(name[5:-7]):
                        dest = os.path.join(work, "apps", name[5:])
                    else:
                        continue
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with tar.extractfile(m) as src, open(dest, "wb") as out:
                        shutil.copyfileobj(src, out, CHUNK)
            while opened.read(CHUNK):  # to the sealed last part: a file cut after the archive's own end is refused too
                pass
        settings = {}
        try:
            with open(os.path.join(staged, "config.json"), encoding="utf-8") as f:
                settings = json.load(f)
        except (OSError, ValueError):
            pass
        for folder, _, files in os.walk(staged):
            for name in files:
                rel = os.path.relpath(os.path.join(folder, name), staged)
                if rel == "config.json":
                    continue  # read above and given back as "settings", never copied over: the sign-in stays
                dest = os.path.join(data_dir, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                os.replace(os.path.join(folder, name), dest)
        apps = sorted(n[:-7] for n in os.listdir(os.path.join(work, "apps")))
        inner = "/c" + cpath[len(croot):]
        side = " -o ".join(f"-name {_q(p)}" for p in SIDE_FILES)
        tidy = (f"n=$(basename \"$a\" .tar.gz); if [ -d {_q(inner)}/\"$n\" ]; then find {_q(inner)}/\"$n\" -type f \\( {side} \\) | "
                "while IFS= read -r f; do b=\"${f%-wal}\"; b=\"${b%-shm}\"; b=\"${b%-journal}\"; if [ -f \"$b\" ]; then rm -f \"$f\"; fi; done; fi; ") if running else ""
        code, said = _helper(f"mkdir -p {_q(inner)} && for a in /w/apps/*.tar.gz; do {tidy}tar -C {_q(inner)} -xzf \"$a\" || exit 3; done && "
                             f"chown -R {int(puid)}:{int(pgid)} {_q(inner)}", [f"{host_data}/{WORK}:/w:ro", f"{croot}:/c"])
        if code:
            raise BackupError(f"Putting the apps' settings back in {target} did not work: {said.strip()[-200:]}")
        return {"settings": settings, "apps": apps, "config_dir": target, "header": {k: header.get(k) for k in ("created", "version", "pictures", "site_name")}}
    finally:
        shutil.rmtree(work, ignore_errors=True)


# Restoring one on this server (DASH-387) ------------------------------------------------------------------------------
# From System, Backup and restore, on a server that is running. In order: the password is tried on the file's first
# part; a full backup of how things are now is made into the same folder with the same password, and nothing older is
# removed; the apps whose folders come back are stopped; the backup is put back (restore, running=True); Starboard's
# settings come back through the settings restore, which saves its own copy first; the apps start again. If Starboard
# stops part way, the apps are started at its next start (start_left_stopped).

def restore_status(data_dir):
    try:
        with open(os.path.join(data_dir, RESTORE_STATUS), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"state": "none"}


def _tell(data_dir, **kw):
    now = restore_status(data_dir)
    now.update(kw)
    path = os.path.join(data_dir, RESTORE_STATUS)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(now, f)
    os.replace(path + ".tmp", path)


def _version_key(v):
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(v or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def _first_part(data_dir, host_data, root, path, password):
    """The header of a backup in the folder, after its first part has opened with the password. Reads the start of
    the file only. Raises BackupError for a wrong password or a file that is not a full backup."""
    work = os.path.join(data_dir, WORK)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, mode=0o700)
    try:
        code, _ = _helper(f"head -c {CHUNK + 1024 * 1024 + 64} /t{_q(path[len(root):])} > /w/first", [f"{root}:/t:ro", f"{host_data}/{WORK}:/w"], timeout=120)
        if code:
            raise BackupError(f"Starboard could not read {path}")
        with open(os.path.join(work, "first"), "rb") as f:
            try:
                opened = Opened(f, password)
            except (ValueError, KeyError, struct.error):
                raise BackupError("This backup's header is damaged") from None
            opened._next()
            return opened.header
    finally:
        shutil.rmtree(work, ignore_errors=True)


def start_restore(data_dir, version, file_path, password, apply_settings, site_name=""):
    """Checks everything that can be checked without changing anything, then restores in the background.
    apply_settings(settings) puts Starboard's own settings back and returns how many apps they hold."""
    from . import containers, stack
    _aes()
    if not containers.available():
        raise BackupError("Starboard needs Docker access to put your apps' settings back")
    env = stack.env_values(data_dir)
    config_dir = env.get("CONFIG_DIR")
    if not config_dir:
        raise BackupError("Starboard did not install your apps, so it cannot put their settings back here. Restore a full backup in the set-up of a new install")
    root, path = _place(file_path)
    if not NAME_RE.match(os.path.basename(path)):
        raise BackupError("Choose a Starboard full backup (a .starboard file)")
    host_data = stack.host_folder(data_dir)
    host_data = os.path.dirname(host_data) if host_data else None
    if not host_data:
        raise BackupError("Starboard cannot find its own folder on this computer")
    if _lock.locked():
        raise BackupError("A backup is being made. Restore when it has finished")
    if not _restoring.acquire(blocking=False):
        raise BackupError("A full backup is being restored already")
    try:
        header = _first_part(data_dir, host_data, root, path, password)
        theirs = folders.tidy(header.get("config_dir") or config_dir)
        if theirs != folders.tidy(config_dir):
            raise BackupError(f"This backup is from a server that keeps its apps' settings in {theirs}; this one keeps them in {config_dir}. "
                              "Restore it in the set-up of a new install instead")
        made, mine = _version_key(header.get("version")), _version_key(version)
        if made and mine and made > mine:
            raise BackupError(f"This backup was made by Starboard {header.get('version')}, which is newer than this one ({version}). Update Starboard, then restore it")
        _tell(data_dir, state="running", step="Starting", started=time.time(), finished=None, error="", file=path, safety="", stopped=[],
              created=header.get("created"), apps=[], count=None)
        threading.Thread(target=_restore_here, args=(data_dir, version, path, password, header, config_dir, host_data, env, apply_settings, site_name),
                         daemon=True).start()
    except BaseException:
        _restoring.release()
        raise


def _restore_here(data_dir, version, path, password, header, config_dir, host_data, env, apply_settings, site_name):
    from . import containers
    stopped = []
    try:
        _tell(data_dir, step="Making a full backup of how things are now")
        if not _lock.acquire(blocking=False):
            raise BackupError("A backup is being made. Restore when it has finished")
        folder = os.path.dirname(path)
        while datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S") in os.path.basename(path):
            time.sleep(0.2)  # file names are to the second: the copy made now must never take the name of the one being restored
        _say(data_dir, state="running", step="Starting", started=time.time(), finished=None, error="", file="", target=folder,
             pictures=bool(header.get("pictures")), scheduled=False)
        _make(data_dir, version, password, folder, bool(header.get("pictures")), config_dir, host_data, site_name, env, prune=False)
        before = status(data_dir)
        if before.get("state") != "done":
            raise BackupError(f"The backup of how things are now did not work, so nothing was changed: {before.get('error') or 'no reason given'}")
        _tell(data_dir, safety=before.get("file") or "", step="Stopping the apps")
        using = _containers_using(config_dir)
        for app in header.get("apps") or []:
            for cid in using.get(app, []):
                _tell(data_dir, stopped=stopped + [cid])  # noted first, so a Starboard that stops here starts it again
                try:
                    containers.docker("POST", f"/containers/{cid}/stop?t=30", timeout=60)
                    stopped.append(cid)
                except containers.DockerError:
                    pass
        _tell(data_dir, stopped=list(stopped), step="Putting the backup back")
        out = restore(data_dir, path, password, config_dir=config_dir, puid=int(env.get("PUID") or 1000), pgid=int(env.get("PGID") or 1000), running=True)
        _tell(data_dir, step="Putting Starboard's settings back", apps=out["apps"])
        count = apply_settings(out["settings"] or {})
        _tell(data_dir, count=count, step="Starting the apps again")
        _start_again(data_dir, stopped)
        _tell(data_dir, state="done", step="", finished=time.time())
    except Exception as e:  # noqa: BLE001 - whatever stops it, the page says what
        _start_again(data_dir, stopped)
        _tell(data_dir, state="failed", step="", finished=time.time(), error=str(e) or e.__class__.__name__)
    finally:
        _restoring.release()


def _start_again(data_dir, stopped):
    from . import containers
    still = []
    for cid in list(stopped):
        try:
            containers.docker("POST", f"/containers/{cid}/start", timeout=60)
        except containers.DockerError:
            still.append(cid)
    stopped[:] = still
    _tell(data_dir, stopped=still)


POOL = "/mnt/pool"  # the drive pool's one folder (start.storage): its disks are never the system disk


def _drives(data_dir):
    """The mounted disks that are not the system disk (sysinfo.pool_candidates), or None with no disk list."""
    from . import sysinfo
    return sysinfo.pool_candidates(data_dir)


def disk_of(data_dir, folder, drives=False):
    """Which disk a folder is on, so the page can say so (DASH-260: never the system disk): {"system": bool, "name",
    "mount", "others": how many other disks there are}, or None when Starboard has no drive list or the folder is not
    one it can use. Reads one small file Starboard already has; nothing is measured."""
    if drives is False:
        drives = _drives(data_dir)
    if drives is None:
        return None
    try:
        path = folders.tidy(folder)
    except ValueError:
        return None
    if path == POOL or path.startswith(POOL + "/"):
        return {"system": False, "name": "the disk pool", "mount": POOL, "others": len(drives)}
    best = None
    for d in drives:
        m = (d.get("mount") or "").rstrip("/") or "/"
        if m != "/" and (path == m or path.startswith(m + "/")) and (best is None or len(m) > len(best["mount"])):
            best = {"system": False, "name": d.get("label") or d.get("model") or d.get("device") or m, "mount": m, "others": len(drives)}
    return best or {"system": True, "name": "the system disk", "mount": "/", "others": len(drives)}


def default_folder(data_dir):
    """Another disk than the system disk: the media folder's backups folder when the media is on one, else the biggest
    other disk's, else the media folder's (the page then says it is on the system disk)."""
    from . import stack
    media = stack.env_values(data_dir).get("DATA_DIR") or ""
    first = f"{media.rstrip('/')}/backups/starboard" if media else ""
    drives = _drives(data_dir)
    if not drives or (first and not (disk_of(data_dir, first, drives) or {}).get("system")):
        return first
    for d in sorted(drives, key=lambda d: -int(d.get("size") or 0)):
        folder = f"{d['mount'].rstrip('/')}/backups/starboard"
        if folders.allowed(folder):
            return folder
    return first


def sizes(data_dir):
    """Roughly how big a copy is, with and without pictures (Starboard's own part counted here; apps when asked)."""
    total = pics = 0
    for full, rel in _starboard_files(data_dir, True):
        try:
            n = os.path.getsize(full)
        except OSError:
            continue
        total += n
        if any(rel.startswith(s) for s in STARBOARD_PICTURES):
            pics += n
    return {"starboard": total, "starboard_pictures": pics}


def app_sizes(data_dir):
    """The apps' settings folder, with and without pictures, measured by the helper (du), in bytes."""
    from . import stack
    config_dir = stack.env_values(data_dir).get("CONFIG_DIR")
    if not config_dir:
        return None
    skip = " ".join(f"! -path {_q(p)}" for p in APP_SKIP)
    pics = " -o ".join(f"-path {_q(p)}" for p in APP_PICTURES)
    total = "-exec stat -c %s {} + 2>/dev/null | awk '{s+=$1} END {print s+0}'"
    script = (f"cd /r || exit 1; all=$(find . -type f {skip} {total}); "
              f"pic=$(find . -type f {skip} \\( {pics} \\) {total}); echo \"$all $pic\"")
    code, text = _helper(script, [f"{config_dir}:/r:ro"], timeout=600)
    try:
        everything, pictures = (int(x) for x in text.split()[-2:])
    except ValueError:
        return None
    return {"with_pictures": everything, "without_pictures": everything - pictures}
