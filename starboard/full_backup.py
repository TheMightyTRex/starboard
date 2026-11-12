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
import urllib.parse

from . import folders

MAGIC = b"STARBOARD-BACKUP\x01"
CHUNK = 1024 * 1024
KEEP = 5
SCRYPT = {"n": 2 ** 15, "r": 8, "p": 1}
NAME_RE = re.compile(r"^starboard-full-\d{4}-\d{2}-\d{2}-\d{6}(-pictures)?\.starboard$")
STATUS = "backup-full.json"
WORK = "backup-work"
# Nothing that can be downloaded or made again goes in (owner, 12 November 2026: "take out anything that can be re
# download"): caches, logs, transcodes, fetched artwork and posters, guides, queued download files. On the owner's
# server that leaves about 1.3 GB, mostly Jellyfin's database, which compresses to about a third.
# Starboard's own folder: what never goes in, and the pictures only the person added (station logos from a zip).
STARBOARD_SKIP = ("sessions.json", "logs/", "backups/", WORK + "/", "plugins/.removed/", "setup-token", "posters/", "icons/",
                  "library/films.json", "library/tv.json", "library/music.json", "library/books.json", "library/audiobooks.json",
                  "library/radio.json", "library/network-logos.json", "space.json", "usage.json", "disk-temps.json", "imports/")
STARBOARD_PICTURES = ("library/station-logos/",)
# In each app's folder: always left out (it comes back by itself), and the pictures someone may have added by hand.
APP_SKIP = ["*cache*", "*/Cache/*", "*/logs/*", "*/log/*", "*/Logs/*", "*.log", "*.log.*", "*/transcodes/*", "*/transcode/*",
            "*/temp/*", "*/tmp/*", "*/Backups/*", "*/backups/*", "*/crashreports/*", "*.pid", "*/ipc-socket", "*/keyframes/*",
            "*/attachments/*", "*/trickplay/*", "*/__pycache__/*", "*/data/metadata/*", "*/MediaCover/*", "*/nzb/*", "*xmltv*",
            "*/omdb/*", "*/streams/*", "*/collections/*.jpg", "*/collections/*.png", "*.db-shm"]
APP_PICTURES = ["*/metadata/items/*", "*/metadata/authors/*", "*/covers/*", "*/logos/*", "*/artwork/*", "*/images/*", "*/item-images/*"]
PICTURE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")

_lock = threading.Lock()


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


class Sealed(io.RawIOBase):
    """Writes the header, then the data in encrypted parts; close() seals the last part, so a cut file is refused."""

    def __init__(self, out, key, header):
        self.out, self.aes, self.buf, self.count = out, _aes()(key), bytearray(), 0
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
    code, text = _helper(f"cd /r && for d in */; do [ -d \"$d\" ] && printf '%s\\n' \"${{d%/}}\"; done", [f"{config_dir}:/r:ro"], timeout=60)
    if code:
        raise BackupError(f"Starboard could not look in {config_dir}")
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


# Making one -----------------------------------------------------------------------------------------------------------

def start(data_dir, version, password, target, pictures, site_name=""):
    """Starts making one in the background; refuses when one is running or a part is missing."""
    from . import containers, stack
    _aes()
    key_of(password, b"0" * 16)
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
    if not _lock.acquire(blocking=False):
        raise BackupError("A backup is being made already")
    _say(data_dir, state="running", step="Starting", started=time.time(), finished=None, error="", file="", target=target, pictures=bool(pictures))
    threading.Thread(target=_make, args=(data_dir, version, password, target, bool(pictures), config_dir, host_data, site_name, env),
                     daemon=True).start()


def _make(data_dir, version, password, target, pictures, config_dir, host_data, site_name, env):
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
            if code not in (0, 1):  # tar's 1: a file changed while it was read
                raise BackupError(f"Copying {app} did not work: {said.strip()[-200:]}")
        _say(data_dir, step="Encrypting")
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(8)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        name = f"starboard-full-{stamp}{'-pictures' if pictures else ''}.starboard"
        header = {"format": 1, "kind": "full", "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "version": version,
                  "site_name": site_name, "pictures": pictures, "apps": apps, "config_dir": config_dir,
                  "data_dir": env.get("DATA_DIR", ""), "salt": base64.b64encode(salt).decode(), "nonce": base64.b64encode(nonce).decode(),
                  "kdf": {"name": "scrypt", **SCRYPT}, "cipher": "AES-256-GCM", "part": CHUNK}
        with open(os.path.join(work, name), "wb") as raw:
            sealed = Sealed(raw, key_of(password, salt), header)
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
        keep = f"ls -1t {_q(inner)} | grep -E '^starboard-full-[0-9-]+(-pictures)?\\.starboard$' | tail -n +{KEEP + 1}"
        code, said = _helper(f"mkdir -p {_q(inner)} && cp /w/{_q(name)} {_q(inner)}/{_q(name + '.part')} && "
                             f"mv {_q(inner)}/{_q(name + '.part')} {_q(inner)}/{_q(name)} && "
                             f"chown {owner} {_q(inner)} {_q(inner)}/{_q(name)} && chmod 600 {_q(inner)}/{_q(name)} && "
                             f"{keep} | while read -r old; do rm -f {_q(inner)}/\"$old\"; done",
                             [f"{host_data}/{WORK}:/w:ro", f"{root}:/t"])
        if code:
            raise BackupError(f"Writing to {target} did not work: {said.strip()[-200:]}")
        _say(data_dir, state="done", step="", finished=time.time(), file=f"{path}/{name}", size=size)
    except Exception as e:  # noqa: BLE001: whatever stops it, the page says what
        _say(data_dir, state="failed", step="", finished=time.time(), error=str(e) or e.__class__.__name__)
    finally:
        shutil.rmtree(work, ignore_errors=True)
        _lock.release()


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


def restore(data_dir, file_path, password, config_dir=None, puid=1000, pgid=1000):
    """Puts a full backup back: Starboard's files (its sign-in stays as it is now), then every app's folder into the
    settings folder. Returns {"settings": the settings backup inside, "apps": [...], "config_dir": ...}. The set-up
    then writes the Compose file (keeping the restored .env's secrets) and starts the apps."""
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
        code, said = _helper(f"cp /t{_q(path[len(root):])} /w/in.starboard", [f"{root}:/t:ro", f"{host_data}/{WORK}:/w"])
        if code:
            raise BackupError(f"Starboard could not read {file_path}")
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
                        if rel in ("config.json", "api-keys.json") or rel.startswith(("logs/", WORK)):
                            dest = os.path.join(work, "starboard", rel)  # read below, not copied over
                        else:
                            dest = os.path.join(data_dir, rel)
                    elif name.startswith("apps/") and name.endswith(".tar.gz") and folders.NAME.match(name[5:-7]):
                        dest = os.path.join(work, "apps", name[5:])
                    else:
                        continue
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with tar.extractfile(m) as src, open(dest, "wb") as out:
                        shutil.copyfileobj(src, out, CHUNK)
        settings = {}
        try:
            with open(os.path.join(work, "starboard", "config.json"), encoding="utf-8") as f:
                settings = json.load(f)
        except (OSError, ValueError):
            pass
        keys = os.path.join(work, "starboard", "api-keys.json")
        if os.path.exists(keys):
            shutil.copyfile(keys, os.path.join(data_dir, "api-keys.json"))
        apps = sorted(n[:-7] for n in os.listdir(os.path.join(work, "apps")))
        inner = "/c" + cpath[len(croot):]
        code, said = _helper(f"mkdir -p {_q(inner)} && for a in /w/apps/*.tar.gz; do tar -C {_q(inner)} -xzf \"$a\" || exit 3; done && "
                             f"chown -R {int(puid)}:{int(pgid)} {_q(inner)}", [f"{host_data}/{WORK}:/w:ro", f"{croot}:/c"])
        if code:
            raise BackupError(f"Putting the apps' settings back in {target} did not work: {said.strip()[-200:]}")
        return {"settings": settings, "apps": apps, "config_dir": target, "header": {k: header.get(k) for k in ("created", "version", "pictures", "site_name")}}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def default_folder(data_dir):
    """Another disk than Starboard's: the media folder's backups folder."""
    from . import stack
    media = stack.env_values(data_dir).get("DATA_DIR") or ""
    return f"{media.rstrip('/')}/backups/starboard" if media else ""


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
