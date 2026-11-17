"""Bring in media you already have (DASH-455, owner, 16 November 2026): copies films, series, music, books and
audiobooks from places the person already keeps them into Starboard's media folders, tidied and named so Reelix and
Jellyfin match them. Never moves, renames or deletes anything at a source.

The step has four parts, the same in the browser and the terminal set-up:
1. Sources, in order: folders on this computer, another disk, a network share (SMB or NFS), OneDrive or Google Drive.
   The earlier source wins when the same title is in two places.
2. What is in each: Starboard looks at file types and folder shapes and counts films, series, music, books and
   audiobooks. The person can correct a whole source or one folder in it.
3. Check names: each title's new name and place, matched with Reelix's own lookup (the names Reelix and Jellyfin match
   best). Matched, Needs a look (choose between matches) and Left where it is (with why). Space needed against free.
4. Copy: in the background at low priority (nice and ionice, one copy at a time), pausable, carrying on after a
   restart. Then Reelix's own library import adds each title and Reelix's rename gives each file Reelix's own name.

Safety, which tests/test_bring_in.py holds to:
- Sources are read only. Shares are mounted read only, disks are bound read only into the short-lived helper, cloud
  services are signed in to with read-only access. The copy script only reads a source: cp, ln and stat.
- Free space is checked before the copy and before each file; the copy stops cleanly when it would run out.
- A file already at the destination is never written over.
- Hard links (same disk only, films and series only, off by default) make the library file the same file as the
  source: nothing is copied and no space is used. Music and books are always copied, as Reelix may write their tags.

Lightweight first (MAIN-DESIGN.md): nothing runs until the person asks. A look is one listing of the source; quick
fingerprints are read only for files of exactly the same size; the copy is one helper at a time at the lowest
processor and disk priority, and no thread runs after it ends.
"""
import hashlib
import json
import os
import re
import shlex
import subprocess  # nosec B404: the copy script, with fixed arguments, when Starboard runs outside Docker
import threading
import time

from . import folders

KINDS = ("films", "series", "music", "books", "audiobooks")
WORDS = {"films": "Films", "series": "Series", "music": "Music", "books": "Books", "audiobooks": "Audiobooks"}
ONE = {"films": "film", "series": "series", "music": "album", "books": "book", "audiobooks": "audiobook"}
MANY = {"films": "films", "series": "series", "music": "albums", "books": "books", "audiobooks": "audiobooks"}
# Where each kind goes, inside the media folder (stack.DATA_FOLDERS), and how Reelix sees it.
TARGET = {"films": "media/movies", "series": "media/tv", "music": "media/music", "books": "media/books",
          "audiobooks": "media/audiobooks"}
REELIX_DATA = "/data"
SOURCE_KINDS = ("computer", "disk", "smb", "nfs", "onedrive", "gdrive")
SOURCE_WORDS = {"computer": "This computer", "disk": "Another disk", "smb": "Network share (SMB)",
                "nfs": "Network share (NFS)", "onedrive": "OneDrive", "gdrive": "Google Drive"}
CLOUD = ("onedrive", "gdrive")

VIDEO = {".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".ts", ".m2ts", ".webm", ".mpg", ".mpeg", ".flv", ".vob", ".iso"}
AUDIO = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".wma", ".alac", ".aiff", ".ape"}
AUDIOBOOK = {".m4b"}
BOOK = {".epub", ".mobi", ".azw", ".azw3", ".pdf", ".cbz", ".cbr", ".djvu", ".fb2"}
SUBTITLE = {".srt", ".ass", ".ssa", ".sub", ".idx", ".vtt", ".sup", ".smi"}
ARTWORK = {".jpg", ".jpeg", ".png", ".webp", ".tbn"}
NFO = {".nfo"}
CUE = {".cue", ".log", ".m3u", ".m3u8"}  # an album's own lists travel with it
# Never brought in: system files and leftovers of downloads.
JUNK_NAMES = {"thumbs.db", "desktop.ini", ".ds_store", "folder.ini", "rarbg.txt", "rarbg.com.txt", "torrent downloaded from.txt"}
GENERIC = {"movies", "movie", "films", "film", "tv", "tv shows", "tvshows", "shows", "series", "music", "audio", "mp3",
           "flac", "books", "ebooks", "e-books", "audiobooks", "audio books", "audiobook", "media", "downloads", "video",
           "videos", "complete", "completed", "library", "share", "public", "data", "my videos", "my music", "documents"}
# Only the first 512 characters of a name are matched: no real file name is longer, and it bounds the patterns' work.
NAME_MAX = 512
SAMPLE_RE = re.compile(r"(^|[\s._\-\[(/])sample([\s._\-\])/]|$)", re.I)
EPISODE_RES = (re.compile(r"(?i)^(?P<show>.*?)[\s._\-\[(]*s(?P<s>\d{1,2})[\s._-]*e(?P<e>\d{1,3})(?:[-_ ]?e?(?P<e2>\d{1,3}))?(?!\d)"),
               re.compile(r"(?i)^(?P<show>.*?)[\s._\-\[(]*(?P<s>\d{1,2})x(?P<e>\d{2,3})(?!\d)"))
SEASON_RE = re.compile(r"(?i)^(season|series|staffel|saison)[\s._-]*(\d{1,2})$|^s(\d{1,2})$")
YEAR_RE = re.compile(r"(?<![\d])(19[0-9]{2}|20[0-9]{2})(?![\d])")
QUALITY_RE = re.compile(r"(?i)[\s._\-\[(](2160p|1080p|1080i|720p|576p|480p|4k|uhd|bluray|blu-ray|bdrip|brrip|web-?dl|webrip|"
                        r"hdtv|dvdrip|dvd|x264|x265|h\.?264|h\.?265|hevc|xvid|divx|remux|proper|repack|extended|"
                        r"unrated|directors\.?cut|hdr|10bit|aac|ac3|dts|atmos)([\s._\-\])]|$)")
ILLEGAL = re.compile(r'[<>"/\\|?*\x00-\x1f]')
MARGIN = 10 * 10 ** 9  # always left free on the media disk
MIN_SAMPLE = 200 * 10 ** 6  # a video this small beside a much bigger one in the same folder is a sample or an extra
MAX_FILES = 300_000  # one look reads at most this many files
BATCH_FILES, BATCH_BYTES = 200, 50 * 10 ** 9
STATE = "bring-in"
_lock = threading.Lock()  # one copy at a time
_jobs = {}


class BringInError(Exception):
    pass


# Files and state ------------------------------------------------------------------------------------------------------

def _dir(data_dir):
    path = os.path.join(data_dir, STATE)
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def _read(data_dir, name, default):
    try:
        with open(os.path.join(_dir(data_dir), name), encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, type(default)) else default
    except (OSError, ValueError):
        return default


def _write(data_dir, name, value, private=False):
    path = os.path.join(_dir(data_dir), name)
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(value, f)
    os.replace(path + ".tmp", path)


def settings(data_dir):
    s = _read(data_dir, "sources.json", {})
    return {"sources": [x for x in s.get("sources") or [] if isinstance(x, dict) and x.get("id")],
            "hardlinks": bool(s.get("hardlinks")), "media": str(s.get("media") or "")}


def _secrets(data_dir):
    return _read(data_dir, "secret.json", {})


def fold(text):
    """A title as compared: lower case, letters and numbers only, "and" for "&", no leading "the"."""
    t = str(text or "").lower().replace("&", " and ")
    t = re.sub(r"[^0-9a-z]+", " ", t).strip()
    return re.sub(r"^the ", "", t)


def tidy_name(text):
    """A file or folder name Jellyfin and every disk accept: a colon becomes " -", other forbidden marks go."""
    t = str(text or "").replace(": ", " - ").replace(":", "-")
    t = ILLEGAL.sub("", t)
    t = " ".join(t.split()).strip(" .")
    return t[:180] or "Unknown"


def _words(stem):
    return " ".join(re.sub(r"[._]+", " ", stem).split()).strip(" -[]()")


# Sources ----------------------------------------------------------------------------------------------------------------

def _source_id(sources):
    used = {s["id"] for s in sources}
    n = 1
    while f"s{n}" in used:
        n += 1
    return f"s{n}"


def check_source(data_dir, given, sources):
    """A source the page or the terminal sent, checked: {id, kind, path, address, user, name}. Raises ValueError with a
    sentence. A share's password goes to secret.json, never back to the page."""
    from . import backup_copies
    kind = str(given.get("kind") or "")
    if kind not in SOURCE_KINDS:
        raise ValueError("Choose where the media is")
    out = {"id": str(given.get("id") or "") or _source_id(sources), "kind": kind, "path": "", "address": "", "user": "",
           "fix": given.get("fix") if isinstance(given.get("fix"), dict) else {}}
    if not re.match(r"^s\d{1,3}$", out["id"]):
        raise ValueError("That is not a source Starboard knows")
    path = str(given.get("path") or "").strip()
    if kind in ("computer", "disk"):
        path = folders.tidy(path)
        if not folders.allowed(path):
            raise ValueError("Choose a folder under " + ", ".join(folders.ROOTS))
        media = settings(data_dir)["media"]
        if media and (path == media or path.startswith(media.rstrip("/") + "/media")):
            raise ValueError("That is Starboard's own media folder. Choose the folder your media is in now")
        out["path"] = path
    elif kind == "smb":
        address = str(given.get("address") or "").strip().replace("\\", "/")
        if not backup_copies.SMB_RE.match(address):
            raise ValueError("Write the share as //computer/share, such as //192.168.1.20/media or //nas.home/media")
        user = str(given.get("user") or "").strip()[:100]
        if "," in user or "=" in user:
            raise ValueError("A user name cannot have a comma or an equals sign")
        out.update(address=address, user=user, path=_rel(path))
    elif kind == "nfs":
        address = str(given.get("address") or "").strip()
        if not backup_copies.NFS_RE.match(address):
            raise ValueError("Write the share as computer:/folder, such as 192.168.1.20:/export/media")
        out.update(address=address, path=_rel(path))
    else:
        out["path"] = _rel(path)
    out["name"] = describe(out)
    return out


def _rel(path):
    """A folder inside a share or a cloud service, as /films or "" for the whole of it."""
    path = "/" + str(path or "").strip().strip("/")
    if "\x00" in path or "/../" in path + "/" or "//" in path:
        raise ValueError("That is not a folder Starboard can use")
    return "" if path == "/" else path


def describe(s):
    """The source in a few words, for the list and the report."""
    if s["kind"] in ("computer", "disk"):
        return s["path"]
    if s["kind"] in ("smb", "nfs"):
        return s["address"] + (s["path"] if s["kind"] == "smb" else s["path"])
    return f"{SOURCE_WORDS[s['kind']]}{s['path'] or ', all of it'}"


def save_sources(data_dir, given, hardlinks=None, media=None):
    """Keeps the sources in the order given. A share's password, when sent, is kept apart and never sent back."""
    old = settings(data_dir)
    out = []
    secrets = _secrets(data_dir)
    for g in given or []:
        if not isinstance(g, dict):
            continue
        s = check_source(data_dir, g, out)
        if g.get("password"):
            secrets[s["id"]] = str(g["password"])[:200]
        out.append(s)
    if len(out) > 20:
        raise ValueError("Bring in from at most 20 places at once")
    keep = {s["id"] for s in out}
    secrets = {k: v for k, v in secrets.items() if k in keep}
    _write(data_dir, "secret.json", secrets, private=True)
    _write(data_dir, "sources.json", {"sources": out, "hardlinks": old["hardlinks"] if hardlinks is None else bool(hardlinks),
                                      "media": old["media"] if media is None else str(media or "")})
    return public(data_dir)


def public(data_dir):
    s = settings(data_dir)
    secrets = _secrets(data_dir)
    looks = _read(data_dir, "looks.json", {})
    for x in s["sources"]:
        x["password_set"] = x["id"] in secrets
        x["look"] = looks.get(x["id"])
    return {**s, "job": status(data_dir), "kinds": list(KINDS), "words": WORDS, "link_offered": link_offered(data_dir)}


# Reading a source -------------------------------------------------------------------------------------------------------

def _in_docker():
    return os.path.exists("/.dockerenv")


def _local(s):
    """Read straight from this computer: Starboard runs outside Docker (or a test), and the source is a folder."""
    return s["kind"] in ("computer", "disk") and not _in_docker()


def _walk(root, limit=MAX_FILES):
    """(relative path, size, mtime, device, inode) of every file under root, links not followed, at most limit."""
    out = []
    for here, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            full = os.path.join(here, name)
            try:
                st = os.lstat(full)
            except OSError:
                continue
            if not os.path.isfile(full) or os.path.islink(full):
                continue
            out.append((os.path.relpath(full, root), st.st_size, int(st.st_mtime), st.st_dev, st.st_ino))
            if len(out) >= limit:
                return out
    return out


LIST_SCRIPT = ("cd {where} 2>/dev/null || {{ echo NOFOLDER; exit 0; }}; "
               "find . -type d -name '.*' ! -name . -prune -o -type f -print 2>/dev/null | head -n {limit} | "
               "while IFS= read -r f; do stat -c '%s\t%Y\t%d\t%i\t%n' \"$f\" 2>/dev/null; done")


def _parse_listing(text):
    out = []
    for line in text.splitlines():
        parts = line.split("\t", 4)
        if len(parts) == 5 and parts[0].isdigit() and parts[1].isdigit():
            rel = parts[4][2:] if parts[4].startswith("./") else parts[4]
            out.append((rel, int(parts[0]), int(parts[1]), int(parts[2]) if parts[2].isdigit() else 0,
                        int(parts[3]) if parts[3].isdigit() else 0))
        elif line.strip() == "NOFOLDER":
            raise BringInError("Starboard could not open that folder")
    return out


def listing(data_dir, s, run=None):
    """Every file in a source: [(relative path, size, mtime, device, inode)]. run(script, mounts) is the helper, given
    by tests; by default a short-lived helper container with the source mounted read only."""
    if s["kind"] in CLOUD:  # listed at the service (read only); once copied down, from the staging folder
        staged = _staging(data_dir, s)
        if os.path.isdir(staged) and os.listdir(staged):
            return _walk(staged)
        from . import cloud_sources
        try:
            return cloud_sources.files(data_dir, s["kind"], s["path"], run=run)
        except cloud_sources.CloudSourceError as e:
            raise BringInError(str(e)) from None
    if _local(s) and run is None:
        real = folders.inside(s["path"])
        if not os.path.isdir(real):
            raise BringInError(f"There is no folder at {s['path']}")
        return _walk(real)
    mounts, where = _mounts(data_dir, s, "/s")
    script = LIST_SCRIPT.format(where=shlex.quote(where), limit=MAX_FILES)
    code, text = (run or _helper)(script, mounts, data_dir=data_dir)  # data_dir: a share's password is read from it
    if code:
        raise BringInError(_plain(text, s))
    return _parse_listing(text)


def _mounts(data_dir, s, at):
    """[(kind, source, target)] for the helper, read only, and the folder inside the helper to read."""
    if s["kind"] in ("computer", "disk"):
        root = next(r for r in folders.ROOTS if s["path"] == r or s["path"].startswith(r + "/"))
        return [("bind", root, at)], at + s["path"][len(root):]
    if s["kind"] in ("smb", "nfs"):
        return [("share", s, at)], at + s["path"]
    return [("bind", _staging(data_dir, s), at)], at


def _plain(text, s):
    low = (text or "").lower()
    if "permission denied" in low or "access denied" in low:
        return f"Starboard was not allowed to read {describe(s)}. Check the user name, password and the folder's permissions"
    if "no such device" in low or "host is down" in low or "no route to host" in low or ("mount" in low and "fail" in low):
        return f"The share {describe(s)} did not answer. Check it is on and the address is right"
    if "no space left" in low:
        return "The media disk is full. Free some space, or bring in less"
    return ((text or "").strip().splitlines() or ["Starboard could not read it"])[-1][:240]


def _helper(script, mounts, data_dir=None, user=None, timeout=3600, watch=None, stop=None):
    """Runs a script in the short-lived helper (the backup helper image): binds read only unless the target is /t, a
    share as a read-only volume. watch(text) is called with new output every few seconds; stop() ends it early.
    Returns (exit code, output)."""
    from . import backup_copies, containers, stack
    try:
        containers.ensure_image()
    except containers.DockerError as e:
        raise BringInError(f"Docker did not do it: {e}") from None
    binds, volumes, made = [], [], []
    for kind, src, target in mounts:
        if kind == "bind":
            binds.append(f"{src}:{target}:{'rw' if target == '/t' else 'ro'}")
        else:
            env = stack.env_values(data_dir) if data_dir else {}
            vol = _share_volume(src, _secrets(data_dir or "").get(src["id"], "") if data_dir else "", env)
            made.append(vol)
            volumes.append({"Type": "volume", "Source": vol, "Target": target, "ReadOnly": True})
    body = {"Image": containers.HELPER_IMAGE, "Entrypoint": ["sh", "-c"], "Cmd": [script], "Labels": {"starboard.updater": "1"},
            "HostConfig": {"Binds": binds, "Mounts": volumes, "NetworkMode": "none", "Memory": 256 * 1024 ** 2}}
    if user:
        body["User"] = user
    cid = None
    try:
        cid = containers.docker("POST", f"/containers/create?name=starboard-bring-in-{int(time.time() * 1000)}", body)["Id"]
        containers.docker("POST", f"/containers/{cid}/start")
        began, seen = time.time(), b""
        while True:
            state = containers.docker("GET", f"/containers/{cid}/json").get("State") or {}
            raw = containers.docker("GET", f"/containers/{cid}/logs?stdout=1&stderr=1", raw=True)
            if watch and raw != seen:
                watch(_demux(raw))
                seen = raw
            if not state.get("Running"):
                return int(state.get("ExitCode") or 0), _demux(raw)
            if (stop and stop()) or time.time() - began > timeout:
                containers.docker("POST", f"/containers/{cid}/kill")
                return 143, _demux(raw)
            time.sleep(3)
    except containers.DockerError as e:
        raise BringInError(f"Docker did not do it: {e}") from None
    finally:
        if cid:
            try:
                containers.docker("DELETE", f"/containers/{cid}?force=1")
            except containers.DockerError:
                pass
        for v in made:
            backup_copies._let_go(v)


def _demux(raw):
    text, i = b"", 0
    while i + 8 <= len(raw):
        n = int.from_bytes(raw[i + 4:i + 8], "big")
        text += raw[i + 8:i + 8 + n]
        i += 8 + n
    return text.decode("utf-8", "replace")


def _share_volume(s, password, env):
    """A short-lived Docker volume on the share, mounted read only: Starboard can never change a file there."""
    from . import backup_copies, containers
    name = f"starboard-bring-in-{int(time.time() * 1000)}"
    if s["kind"] == "smb":
        m = backup_copies.SMB_RE.match(s["address"])
        ip = backup_copies._address(m.group(1))
        opts = [f"addr={ip}", "vers=3.0", "ro", f"uid={int(env.get('PUID') or 1000)}", f"gid={int(env.get('PGID') or 1000)}"]
        opts += [f"username={s['user']}", "password=" + password.replace(",", ",,")] if s["user"] else ["guest"]
        driver = {"type": "cifs", "device": f"//{ip}/{m.group(2)}{m.group(3)}", "o": ",".join(opts)}
    else:
        m = backup_copies.NFS_RE.match(s["address"])
        driver = {"type": "nfs", "device": f":{m.group(2) or '/'}", "o": f"addr={backup_copies._address(m.group(1))},nfsvers=4,ro"}
    try:
        containers.docker("POST", "/volumes/create", {"Name": name, "Driver": "local", "DriverOpts": driver,
                                                      "Labels": {"starboard.updater": "1"}})
    except containers.DockerError as e:
        raise BringInError(f"Docker could not reach the share: {e}") from None
    return name


def _staging(data_dir, s):
    """Where a cloud source is copied down to, on the media disk, before it is brought in like any folder."""
    media = settings(data_dir)["media"] or _media(data_dir)
    return os.path.join(media, ".starboard-bring-in", s["id"])


def _media(data_dir):
    from . import stack
    return stack.env_values(data_dir).get("DATA_DIR", "")


DIRS_SCRIPT = ("cd {where} 2>/dev/null || {{ echo NOFOLDER; exit 0; }}; "
               "for d in */; do [ -d \"$d\" ] && printf 'D\\t%s\\n' \"${{d%/}}\"; done 2>/dev/null | head -n 300")


def _share(data_dir, sid):
    s = next((x for x in settings(data_dir)["sources"] if x["id"] == sid and x["kind"] in ("smb", "nfs")), None)
    if not s:
        raise BringInError("That share is not on the list any more")
    return s


def share_browse(data_dir, sid, rel, run=None):
    """One folder of a network share, as the picker shows it: the share is mounted read only in the helper."""
    s = _share(data_dir, sid)
    rel = _rel(rel)
    code, text = (run or _helper)(DIRS_SCRIPT.format(where=shlex.quote("/r" + rel)), [("share", s, "/r")], data_dir=data_dir)
    if "NOFOLDER" in text:
        raise LookupError("There is no folder there")
    if code:
        raise BringInError(_plain(text, s))
    names = [ln[2:] for ln in text.splitlines() if ln.startswith("D\t") and not ln[2:].startswith(".")]
    crumbs = [{"name": s["address"], "path": ""}]
    parts = [p for p in rel.split("/") if p]
    for i, part in enumerate(parts):
        crumbs.append({"name": part, "path": "/" + "/".join(parts[:i + 1])})
    return {"path": rel, "place": f"share:{sid}", "parent": "/".join(rel.split("/")[:-1]) if rel else None, "crumbs": crumbs,
            "folders": [{"name": n, "path": f"{rel}/{n}"} for n in names], "free": None, "total": None, "why": ""}


def share_sizes(data_dir, sid, rel, run=None):
    s = _share(data_dir, sid)
    code, text = (run or _helper)(LIST_SCRIPT.format(where=shlex.quote("/r" + _rel(rel)), limit=200_000), [("share", s, "/r")], data_dir=data_dir)
    return folders.group_sizes(_parse_listing(text))


# What is in each ------------------------------------------------------------------------------------------------------

def kind_of(rel, size=0):
    """What one file is, by its type and the folders above it: a kind, "extra" (subtitles, artwork, .nfo, an album's
    lists), or "junk"."""
    name = os.path.basename(rel)
    ext = os.path.splitext(name)[1].lower()
    parts = [p.lower() for p in rel.split("/")[:-1]]
    if name.lower() in JUNK_NAMES or name.startswith("._"):
        return "junk"
    if ext in VIDEO:
        stem = _words(os.path.splitext(name)[0])[:NAME_MAX]
        if EPISODE_RES[0].match(stem) or EPISODE_RES[1].match(stem):
            return "series"
        if any(SEASON_RE.match(p) for p in parts) or any(p in ("tv", "tv shows", "tvshows", "series", "shows") for p in parts):
            return "series"
        return "films"
    if ext in AUDIOBOOK or (ext in AUDIO and any("audiobook" in p or "audio book" in p or p == "hörbücher" for p in parts)):
        return "audiobooks"
    if ext in AUDIO:
        return "music"
    if ext in BOOK:
        return "books"
    if ext in SUBTITLE | ARTWORK | NFO | CUE:
        return "extra"
    return "junk"


def _fix_for(fixes, rel):
    """The person's correction for a file: the longest folder (or the whole source, "") that covers it."""
    best, kind = -1, None
    for folder, k in (fixes or {}).items():
        if folder == "" or rel == folder or rel.startswith(folder.rstrip("/") + "/"):
            if len(folder) > best:
                best, kind = len(folder), k
    return kind


def summary(files, fixes=None):
    """What a look found: per kind, how many titles and their size; the folders at the top with what each holds; and
    what is left (other files)."""
    counts = {k: {"titles": set(), "size": 0, "files": 0} for k in KINDS}
    tops = {}
    other = {"files": 0, "size": 0}
    for rel, size, *_ in files:
        k = kind_of(rel, size)
        if k in ("films", "series") and SAMPLE_RE.search(rel):
            k = "junk"  # a sample is not counted as a title
        fixed = _fix_for(fixes, rel)
        if fixed and k in KINDS + ("extra",):
            k = fixed if k in KINDS else k
        top = rel.split("/")[0] if "/" in rel else ""
        t = tops.setdefault(top, {k2: set() for k2 in KINDS} | {"size": 0})
        t["size"] += size
        if k in KINDS:
            counts[k]["titles"].add(_title_key(k, rel))
            counts[k]["size"] += size
            counts[k]["files"] += 1
            t[k].add(_title_key(k, rel))
        elif k == "junk" or k == "leave":
            other["files"] += 1
            other["size"] += size
    found = {k: {"titles": len(v["titles"]), "size": v["size"], "files": v["files"]} for k, v in counts.items() if v["files"]}
    folders_ = [{"path": p, "size": v["size"], "main": max(KINDS, key=lambda k: len(v[k])) if any(v[k] for k in KINDS) else None,
                 "kinds": {k: len(v[k]) for k in KINDS if v[k]}, "fix": (fixes or {}).get(p)} for p, v in sorted(tops.items()) if p]
    return {"found": found, "folders": folders_[:200], "other": other, "files": len(files),
            "size": sum(f[1] for f in files), "fix": (fixes or {}).get("")}


def _title_key(kind, rel):
    """The title one media file belongs to, for counting: a film, a show, an album, a book."""
    parts = rel.split("/")
    if kind == "films":
        t = parse_film(rel)
        return ("films", fold(t["title"]), t["year"])
    if kind == "series":
        e = parse_episode(rel)
        return ("series", fold(e["show"]) if e else fold(parts[0]))
    if kind == "books":
        return ("books", fold(os.path.splitext(parts[-1])[0]))
    return (kind, "/".join(parts[:-1]) or parts[-1])


def look(data_dir, source_id, run=None):
    """Reads one source and says what is in it. The listing is kept for Check names."""
    s = next((x for x in settings(data_dir)["sources"] if x["id"] == source_id), None)
    if not s:
        raise BringInError("That source is not on the list any more")
    files = listing(data_dir, s, run)
    _write(data_dir, f"files-{s['id']}.json", files)
    got = summary(files, s.get("fix"))
    got["at"] = time.time()
    looks = _read(data_dir, "looks.json", {})
    looks[s["id"]] = got
    _write(data_dir, "looks.json", looks)
    return got


def fix(data_dir, source_id, folder, kind):
    """The person's correction: a whole source ("") or one folder in it is films, series... or left where it is."""
    if kind not in KINDS + ("leave", ""):
        raise ValueError("Choose what is in it")
    st = settings(data_dir)
    s = next((x for x in st["sources"] if x["id"] == source_id), None)
    if not s:
        raise BringInError("That source is not on the list any more")
    folder = str(folder or "").strip("/")
    if "\x00" in folder or ".." in folder.split("/"):
        raise ValueError("That is not a folder in this source")
    fixes = dict(s.get("fix") or {})
    if kind:
        fixes[folder] = kind
    else:
        fixes.pop(folder, None)
    s["fix"] = fixes
    _write(data_dir, "sources.json", {**{k: st[k] for k in ("hardlinks", "media")}, "sources": st["sources"]})
    files = _read(data_dir, f"files-{s['id']}.json", [])
    got = summary([tuple(f) for f in files], fixes)
    got["at"] = time.time()
    looks = _read(data_dir, "looks.json", {})
    looks[s["id"]] = got
    _write(data_dir, "looks.json", looks)
    return got


# Names --------------------------------------------------------------------------------------------------------------

def _clean_title(text):
    t = QUALITY_RE.split(" " + text)[0] if QUALITY_RE.search(" " + text) else text
    t = re.sub(r"[\[(]\s*$", "", t)
    return _words(t)


def parse_film(rel):
    """{title, year} from a film's file name, or its folder's when the file's is plain (movie.mkv, CD1...)."""
    parts = rel.split("/")
    stem = os.path.splitext(parts[-1])[0]
    for text in (stem, parts[-2] if len(parts) > 1 else ""):
        words = _words(text)
        m = None
        for m in YEAR_RE.finditer(words):  # noqa: B007 - keeps the last year in the name
            pass
        if m and m.start() > 0:
            title = _clean_title(words[:m.start()])
            if title and fold(title) not in GENERIC:
                return {"title": title, "year": int(m.group(1))}
    for text in (stem, parts[-2] if len(parts) > 1 else ""):
        title = _clean_title(_words(text))
        if title and fold(title) not in GENERIC and not re.match(r"(?i)^(cd|disc|part)\s*\d+$", title):
            return {"title": title, "year": None}
    return {"title": _words(stem) or "Unknown", "year": None}


def parse_episode(rel):
    """{show, year, season, episode, last} for an episode, or None. The show is taken from the file name, else from
    the folder above its season folder."""
    parts = rel.split("/")
    stem = _words(os.path.splitext(parts[-1])[0])[:NAME_MAX]
    m = EPISODE_RES[0].match(stem) or EPISODE_RES[1].match(stem)
    if not m:
        return None
    show = _clean_title(m.group("show") or "")
    if not show or fold(show) in GENERIC:
        above = [p for p in parts[:-1] if not SEASON_RE.match(p.strip()) and fold(p) not in GENERIC]
        show = _words(above[-1]) if above else ""
    year = None
    y = YEAR_RE.search(show)
    if y and y.start() > 0:
        year = int(y.group(1))
        show = _words(show[:y.start()])
    if year is None:  # the show's own folder often has its year: Copper Valley (2018)/Season 1/Copper.Valley.S01E01.mkv
        for part in parts[:-1]:
            w = _words(part)
            y = YEAR_RE.search(w)
            if y and y.start() > 0 and fold(w[:y.start()]) == fold(show):
                year = int(y.group(1))
                break
    return {"show": show or "Unknown", "year": year, "season": int(m.group("s")), "episode": int(m.group("e")),
            "last": int(m.group("e2")) if m.groupdict().get("e2") else None}


def film_place(title, year):
    """Title (Year)/Title (Year): Reelix's own film naming, which Jellyfin matches best."""
    name = tidy_name(f"{title} ({year})" if year else title)
    return f"{TARGET['films']}/{name}", name


def episode_place(show, year, season, episode, last=None):
    folder = tidy_name(f"{show} ({year})" if year else show)
    ep = f"S{season:02d}E{episode:02d}" + (f"-E{last:02d}" if last and last > episode else "")
    return f"{TARGET['series']}/{folder}/Season {season:02d}", f"{tidy_name(show)} - {ep}"


def _author_title(rel, kind):
    """(author or artist, title or album) from the folders above a book, an audiobook or a track."""
    parts = [p for p in rel.split("/")[:-1] if fold(p) not in GENERIC]
    stem = _words(os.path.splitext(rel.split("/")[-1])[0])
    if kind == "books":
        if len(parts) >= 2:
            return _words(parts[-2]), _words(parts[-1])
        if len(parts) == 1:
            return _words(parts[0]), stem
        m = re.match(r"^(.+?)\s+-\s+(.+)$", stem)
        return (m.group(1), m.group(2)) if m else ("", stem)
    if len(parts) >= 2:
        return _words(parts[-2]), _words(parts[-1])
    if len(parts) == 1:
        m = re.match(r"^(.+?)\s+-\s+(.+)$", _words(parts[0]))
        return (m.group(1), m.group(2)) if m else ("", _words(parts[0]))
    return "", ""


# The plan (Check names) ---------------------------------------------------------------------------------------------

def _quick_print(path):
    """A quick fingerprint: the size and the first and last 64 KB. Only read for files of exactly the same size."""
    h = hashlib.sha1(usedforsecurity=False)
    with open(path, "rb") as f:
        h.update(f.read(65536))
        size = os.fstat(f.fileno()).st_size
        if size > 131072:
            f.seek(-65536, os.SEEK_END)
            h.update(f.read(65536))
    return f"{size}:{h.hexdigest()}"


PRINT_SCRIPT = "cd {where} || exit 3; for f in {names}; do printf '%s\\t' \"$f\"; (head -c 65536 \"$f\"; tail -c 65536 \"$f\") | sha1sum | cut -c1-40; done"


def _prints(data_dir, s, rels, run=None):
    """{relative path: fingerprint} for the files given (only ones that share a size with another)."""
    if not rels:
        return {}
    if s["kind"] in CLOUD or (_local(s) and run is None):
        root = _staging(data_dir, s) if s["kind"] in CLOUD else folders.inside(s["path"])
        out = {}
        for r in rels:
            try:
                out[r] = _quick_print(os.path.join(root, r))
            except OSError:
                pass
        return out
    mounts, where = _mounts(data_dir, s, "/s")
    out = {}
    for i in range(0, len(rels), 300):
        chunk = rels[i:i + 300]
        try:
            code, text = (run or _helper)(PRINT_SCRIPT.format(where=shlex.quote(where), names=" ".join(shlex.quote(r) for r in chunk)), mounts,
                                          data_dir=data_dir)
        except BringInError:
            return out  # without fingerprints, exact copies under other names are found by their titles only
        for line in text.splitlines():
            name, _, digest = line.rpartition("\t")
            if name in chunk and re.match(r"^[0-9a-f]{40}$", digest):
                out[name] = digest
    return out


def _host_path(data_dir, s, rel):
    """Where a source file is, for the copy: this computer's own path, or a share's path inside the share."""
    if s["kind"] in CLOUD:
        return os.path.join(_staging(data_dir, s), rel)
    return (s["path"].rstrip("/") + "/" + rel) if s["kind"] in ("computer", "disk") else f"{s['path']}/{rel}"


def _extras_for(files_here, main_stem, new_stem, is_film):
    """The subtitles, artwork and .nfo beside a film or an episode, each with its new name: the part after the video's
    own name is kept (.en.srt, -poster.jpg); a film's folder pictures (poster.jpg, fanart.jpg) keep their names."""
    out = []
    low = main_stem.lower()
    for rel, size in files_here:
        name = os.path.basename(rel)
        stem, ext = os.path.splitext(name)
        if ext.lower() not in SUBTITLE | ARTWORK | NFO:
            continue
        if stem.lower().startswith(low):
            out.append((rel, size, new_stem + name[len(main_stem):]))
        elif is_film and (ext.lower() in ARTWORK | NFO) and stem.lower() in ("poster", "fanart", "folder", "cover", "banner",
                                                                                "logo", "clearart", "disc", "landscape", "backdrop", "movie", "thumb"):
            out.append((rel, size, name))
    return out


def build_plan(data_dir, run=None):
    """Every title in every source, in the sources' order, each with where it goes, or why it stays. Earlier sources
    win; exact duplicates are brought in once; a title already in the media folder stays where it is."""
    st = settings(data_dir)
    media = st["media"] or _media(data_dir)
    items, left, seen_titles, seen_prints = [], [], {}, {}
    by_source = {}
    for s in st["sources"]:
        files = _read(data_dir, f"files-{s['id']}.json", None)
        if files is None:
            look(data_dir, s["id"], run)
            files = _read(data_dir, f"files-{s['id']}.json", [])
        by_source[s["id"]] = [tuple(f) for f in files]
    # Fingerprints only for media files that share a size with another one, in any source.
    sizes = {}
    for sid, files in by_source.items():
        for rel, size, *_ in files:
            if size > 1_000_000 and kind_of(rel) in KINDS:
                sizes.setdefault(size, []).append((sid, rel))
    want = {}
    for group in sizes.values():
        if len(group) > 1:
            for sid, rel in group:
                want.setdefault(sid, []).append(rel)
    prints = {}
    for s in st["sources"]:
        for rel, digest in _prints(data_dir, s, want.get(s["id"], []), run).items():
            prints[(s["id"], rel)] = digest
    existing = _existing(media)
    for order, s in enumerate(st["sources"]):
        files = by_source[s["id"]]
        here = {}
        for rel, size, *_ in files:
            here.setdefault(os.path.dirname(rel), []).append((rel, size))
        for rel, size, _mtime, dev, _ino in files:
            k = kind_of(rel, size)
            fixed = _fix_for(s.get("fix"), rel)
            if k in KINDS and fixed:
                k = fixed
            if k == "extra":
                continue  # travels with its film or episode, or stays with the album or book folder
            src = {"source": s["id"], "rel": rel, "size": size}
            if k == "leave":
                left.append({**src, "why": "You chose to leave this folder where it is"})
                continue
            if k == "junk":
                left.append({**src, "why": "Not media"})
                continue
            p = prints.get((s["id"], rel))
            if p and p in seen_prints:
                left.append({**src, "why": f"An exact copy of {seen_prints[p]}, which is brought in once"})
                continue
            if p:
                seen_prints[p] = f"{rel} in {s['name']}"
            if k in ("films", "series") and SAMPLE_RE.search(os.path.splitext(os.path.basename(rel))[0] + " " + os.path.dirname(rel).split("/")[-1]):
                left.append({**src, "why": "A sample, not the whole film or episode"})
                continue
            if k == "films":
                bigger = [x for x in here[os.path.dirname(rel)] if kind_of(x[0]) == "films" and x[1] > size]
                if bigger and os.path.dirname(rel) and size < MIN_SAMPLE:
                    left.append({**src, "why": "A small video beside the film: a sample or an extra"})
                    continue
                t = parse_film(rel)
                key = ("films", fold(t["title"]), t["year"])
                folder, stem = film_place(t["title"], t["year"])
                ext = os.path.splitext(rel)[1].lower()
                item = {"key": "|".join(map(str, key)), "kind": "films", "source": s["id"], "order": order, "title": t["title"],
                        "year": t["year"], "folder": folder, "files": [], "state": "matched" if t["year"] else "look",
                        "why": "" if t["year"] else "No year in the name: choose the right film", "choices": []}
                item["files"].append({"rel": rel, "size": size, "dst": f"{folder}/{stem}{ext}", "role": "main", "dev": dev})
                for xr, xs, new in _extras_for(here[os.path.dirname(rel)], os.path.splitext(os.path.basename(rel))[0], stem, True):
                    item["files"].append({"rel": xr, "size": xs, "dst": f"{folder}/{new}", "role": "extra"})
            elif k == "series":
                e = parse_episode(rel)
                if not e:
                    left.append({**src, "why": "No season and episode number in the name: bring it in by hand"})
                    continue
                key = ("series", fold(e["show"]), e["season"], e["episode"])
                folder, stem = episode_place(e["show"], e["year"], e["season"], e["episode"], e["last"])
                ext = os.path.splitext(rel)[1].lower()
                show_key = f"series|{fold(e['show'])}|{s['id']}"  # one per source: each copy reads only its own source
                item = next((i for i in items if i["key"] == show_key and i["source"] == s["id"]), None)
                if key in seen_titles:
                    left.append({**src, "why": _second(seen_titles[key], s)})
                    continue
                seen_titles[key] = s["name"]
                if not item:
                    item = {"key": show_key, "kind": "series", "source": s["id"], "order": order, "title": e["show"], "year": e["year"],
                            "folder": folder.rsplit("/", 1)[0], "files": [], "state": "matched", "why": "", "choices": []}
                    items.append(item)
                item["files"].append({"rel": rel, "size": size, "dst": f"{folder}/{stem}{ext}", "role": "main", "dev": dev})
                for xr, xs, new in _extras_for(here[os.path.dirname(rel)], os.path.splitext(os.path.basename(rel))[0], stem, False):
                    item["files"].append({"rel": xr, "size": xs, "dst": f"{folder}/{new}", "role": "extra"})
                continue
            else:  # music, books, audiobooks: by artist and album, or author and title
                who, what = _author_title(rel, k)
                if not who and k == "books":
                    who = "Unknown author"
                folder = f"{TARGET[k]}/{tidy_name(who or 'Unknown')}/{tidy_name(what or 'Unknown')}"
                key = (k, fold(who), fold(what))
                item_key = "|".join(map(str, key))
                item = next((i for i in items if i["key"] == item_key and i["source"] == s["id"]), None)
                if not item:
                    if key in seen_titles:
                        left.append({**src, "why": _second(seen_titles[key], s)})
                        continue
                    seen_titles[key] = s["name"]
                    item = {"key": item_key, "kind": k, "source": s["id"], "order": order, "title": what or who, "year": None,
                            "who": who, "folder": folder, "files": [], "state": "matched" if who else "look",
                            "why": "" if who else f"No {'artist' if k == 'music' else 'author'} folder: check where it goes", "choices": []}
                    items.append(item)
                    # The album's or book's own pictures and lists go with it.
                    for xr, xs in here[os.path.dirname(rel)]:
                        if kind_of(xr) == "extra":
                            item["files"].append({"rel": xr, "size": xs, "dst": f"{folder}/{os.path.basename(xr)}", "role": "extra"})
                item["files"].append({"rel": rel, "size": size, "dst": f"{folder}/{os.path.basename(rel)}", "role": "main", "dev": dev})
                continue
            # Films: one per title; the earlier source wins, and in one source the bigger file.
            if key in seen_titles:
                left.append({**src, "why": _second(seen_titles[key], s)})
                continue
            seen_titles[key] = s["name"]
            items.append(item)
    for i in items:
        i["size"] = sum(f["size"] for f in i["files"])
        if i["folder"].split("/", 2)[-1] in existing.get(i["folder"].rsplit("/", 1)[0], set()) and i["kind"] == "films":
            i["state"], i["why"] = "left", "Already in your library"
    plan = {"items": items, "left": left, "media": media, "at": time.time(), "checked": False}
    _write(data_dir, "plan.json", plan)
    return plan


def _second(first_name, s):
    return (f"The same title is in {first_name}, which comes first in your list" if first_name != s["name"]
            else "A second copy of the same title in this source: the first one found is brought in")


def _existing(media):
    """{"media/movies": {"Alien (1979)", ...}, ...}: the folders already in the media folder, by kind."""
    out = {}
    for rel in TARGET.values():
        try:
            out[rel] = {n for n in os.listdir(os.path.join(media, rel))} if media else set()
        except OSError:
            out[rel] = set()
    return out


# Matching with Reelix ---------------------------------------------------------------------------------------------------

def _reelix_ready(cfg):
    from . import media_import
    try:
        media_import._reelix(cfg)
        return True
    except media_import.ImportError_:
        return False


def _lookup(cfg, kind, title, year):
    import urllib.parse
    from . import media_import
    term = f"{title} {year}" if year else title
    path = "/movies/lookup" if kind == "films" else "/series/lookup"
    return media_import._call(cfg, "GET", f"{path}?{urllib.parse.urlencode({'term': term})}", timeout=60) or []


def judge(item, results):
    """Reelix's lookup for one title: the item marked matched (with Reelix's title, year and id), or needs a look with
    up to five choices. A match is the same title (or original title) and the same year; a series with no year in its
    name matches when only one series of that title is found."""
    want = fold(item["title"])
    rows = [r for r in results if isinstance(r, dict) and r.get("tmdb_id")]
    same = [r for r in rows if want in (fold(r.get("title")), fold(r.get("original_title")))]
    if item["year"]:
        exact = [r for r in same if r.get("year") == item["year"]]
        if not exact and item["kind"] == "series":
            exact = same if len(same) == 1 else []
    else:
        exact = same if len(same) == 1 else []
    choices = [{"tmdb_id": r["tmdb_id"], "title": r.get("title"), "year": r.get("year"), "in_library": bool(r.get("in_library"))} for r in rows[:5]]
    if len(exact) >= 1 and len({r["tmdb_id"] for r in exact}) == 1:
        r = exact[0]
        return {"state": "matched", "tmdb_id": r["tmdb_id"], "match": {"title": r.get("title"), "year": r.get("year")}, "choices": choices,
                "why": "", "in_library": bool(r.get("in_library"))}
    why = ("Reelix found no film or series of that name" if not rows else
           "More than one match: choose the right one" if len(exact) > 1 or len(same) > 1 else
           "The year does not match what Reelix found: choose the right one" if same else
           "Reelix found other titles: choose the right one, or leave it where it is")
    return {"state": "look", "choices": choices, "why": why}


def rename_to(item, title, year):
    """New places for a film's or a series' files once Reelix has given its own title and year."""
    if item["kind"] == "films":
        folder, stem = film_place(title, year)
        old_stem = None
        for f in item["files"]:
            if f["role"] == "main":
                old_stem = os.path.splitext(os.path.basename(f["dst"]))[0]
        for f in item["files"]:
            name = os.path.basename(f["dst"])
            if old_stem and name.startswith(old_stem):
                name = stem + name[len(old_stem):]
            f["dst"] = f"{folder}/{name}"
        item["folder"] = folder
    else:
        base = tidy_name(f"{title} ({year})" if year else title)
        old_show = tidy_name(item["title"])
        for f in item["files"]:
            season, name = f["dst"].split("/")[-2:]
            if name.startswith(old_show + " - "):
                name = tidy_name(title) + name[len(old_show):]
            f["dst"] = f"{TARGET['series']}/{base}/{season}/{name}"
        item["folder"] = f"{TARGET['series']}/{base}"
    item["title"], item["year"] = title, year


def check_names(cfg, data_dir, say=None):
    """Matches each film and series with Reelix's lookup; music and books are matched by Reelix's own import after
    the copy (by artist and author). Without Reelix (a new install, before the apps start) the plan keeps the names
    read from the files, and the copy checks each with Reelix before it copies anything."""
    plan = _read(data_dir, "plan.json", {})
    if not plan:
        raise BringInError("Check your sources first")
    if not _reelix_ready(cfg):
        plan["checked"] = False
        _write(data_dir, "plan.json", plan)
        return plan
    media = plan.get("media") or ""
    existing = _existing(media)
    todo = [i for i in plan["items"] if i["kind"] in ("films", "series") and i["state"] != "left" and not i.get("chosen")]
    for n, item in enumerate(todo):
        if say:
            say(n, len(todo))
        try:
            got = judge(item, _lookup(cfg, item["kind"], item["title"], item["year"]))
        except Exception as e:  # noqa: BLE001 - one title that cannot be looked up waits for a person
            got = {"state": "look", "choices": [], "why": f"Reelix could not find it: {e}"}
        item.update({k: v for k, v in got.items() if k != "match"})
        if got.get("match"):
            rename_to(item, got["match"]["title"] or item["title"], got["match"]["year"] or item["year"])
            name = item["folder"].rsplit("/", 1)[-1]
            if item["kind"] == "films" and (got.get("in_library") or name in existing.get(item["folder"].rsplit("/", 1)[0], set())):
                item["state"], item["why"] = "left", "Already in your library"
    plan["checked"] = True
    _write(data_dir, "plan.json", plan)
    return plan


def choose(data_dir, key, tmdb_id=None, leave=False, title=None, year=None):
    """Needs a look, answered: the match the person chose, or leave it where it is."""
    plan = _read(data_dir, "plan.json", {})
    item = next((i for i in plan.get("items") or [] if i["key"] == key), None)
    if not item:
        raise BringInError("That title is not in the list any more. Check names again")
    if leave:
        item.update(state="left", why="You chose to leave it where it is", chosen=True)
    elif tmdb_id:
        c = next((c for c in item.get("choices") or [] if str(c["tmdb_id"]) == str(tmdb_id)), None)
        if not c:
            raise ValueError("Choose one of the matches shown")
        rename_to(item, c["title"] or item["title"], c["year"] or item["year"])
        item.update(state="matched", tmdb_id=c["tmdb_id"], why="", chosen=True)
    elif title is not None:  # music and books, or no Reelix: the name as read, confirmed
        item.update(state="matched", why="", chosen=True)
    else:
        raise ValueError("Choose a match, or leave it where it is")
    _write(data_dir, "plan.json", plan)
    return _row(item, settings(data_dir))


def _row(i, st):
    names = {s["id"]: s["name"] for s in st["sources"]}
    main = next((f for f in i["files"] if f["role"] == "main"), i["files"][0] if i["files"] else {"rel": ""})
    return {"key": i["key"], "kind": i["kind"], "title": i["title"], "year": i["year"], "state": i["state"], "why": i.get("why", ""),
            "from": f"{names.get(i['source'], '')}: {main['rel']}", "to": i["folder"], "files": len(i["files"]),
            "size": i["size"], "choices": i.get("choices") or [], "first": main.get("dst", "")}


def plan_page(data_dir, state="matched", start=0, size=50):
    """One page of Check names: the titles in one state (matched, look, left), with the counts and the space."""
    plan = _read(data_dir, "plan.json", {})
    if not plan:
        raise BringInError("Check your sources first")
    st = settings(data_dir)
    names = {s["id"]: s["name"] for s in st["sources"]}
    counts = {"matched": 0, "look": 0, "left": len(plan["left"])}
    for i in plan["items"]:
        counts["left" if i["state"] == "left" else i["state"]] = counts.get(i["state"], 0) + 1
    if state == "left":
        rows = [{"key": f"left:{n}", "title": os.path.basename(x["rel"]), "state": "left", "why": x["why"],
                 "from": f"{names.get(x['source'], '')}: {x['rel']}", "size": x["size"], "kind": None}
                for n, x in enumerate(plan["left"])] + [_row(i, st) for i in plan["items"] if i["state"] == "left"]
    else:
        rows = [_row(i, st) for i in plan["items"] if i["state"] == state]
    return {"state": state, "counts": counts, "total": len(rows), "start": start, "items": rows[start:start + size],
            "space": space(data_dir, plan), "checked": plan.get("checked", False), "reelix": None}


def _linkable(data_dir, item, st):
    """A film's or an episode's files can be hard links: the person chose it, the source is a folder on this computer
    and on the same disk as the media folder (checked again by the copy, which copies when a link cannot be made)."""
    if not st["hardlinks"] or item["kind"] not in ("films", "series"):
        return False
    s = next((x for x in st["sources"] if x["id"] == item["source"]), None)
    return bool(s and s["kind"] in ("computer", "disk"))


def space(data_dir, plan=None):
    """{needed, free, enough, linked}: bytes to copy (hard links take none), and what is free on the media disk."""
    plan = plan or _read(data_dir, "plan.json", {})
    st = settings(data_dir)
    media = (plan or {}).get("media") or st["media"] or _media(data_dir)
    needed = linked = 0
    media_dev = _media_dev(data_dir, media)
    cloud = {s["id"] for s in st["sources"] if s["kind"] in CLOUD}
    for i in (plan or {}).get("items") or []:
        if i["state"] == "left":
            continue
        for f in i["files"]:
            if f.get("done"):
                continue
            if i["source"] in cloud:
                needed += f["size"]  # copied down to the staging folder first, on the same disk
            if _linkable(data_dir, i, st) and media_dev is not None and f.get("dev") == media_dev:
                linked += f["size"]
            else:
                needed += f["size"]
    free = _free(media)
    return {"needed": needed, "linked": linked, "free": free, "margin": MARGIN,
            "enough": free is None or needed + MARGIN <= free}


def _dev(path):
    while path and not os.path.exists(path):
        path = os.path.dirname(path)
    try:
        return os.stat(path).st_dev if path else None
    except OSError:
        return None


def _media_dev(data_dir, media):
    """The device number of the media folder's disk, to know which sources are on the same disk. Read here outside
    Docker; inside, once by the helper with the folder mounted read only, and kept."""
    if not media:
        return None
    if not _in_docker():
        return _dev(media)
    st = _read(data_dir, "media-dev.json", {})
    if st.get("media") == media:
        return st.get("dev")
    near = media
    try:
        root = next(r for r in folders.ROOTS if media == r or media.startswith(r + "/"))
        code, text = _helper(f"p={shlex.quote('/m' + media[len(root):])}; while [ ! -d \"$p\" ] && [ \"$p\" != /m ]; do p=\"${{p%/*}}\"; done; stat -c %d \"$p\"",
                             [("bind", root, "/m")])
        dev = int(text.strip().splitlines()[-1]) if not code else None
    except (StopIteration, ValueError, IndexError, BringInError):
        dev = None
    del near
    _write(data_dir, "media-dev.json", {"media": media, "dev": dev})
    return dev


def link_offered(data_dir):
    """Linking is offered only for films and series in a folder on this computer or a disk, on the same disk as the
    media folder (owner, 16 November 2026)."""
    st = settings(data_dir)
    media = st["media"] or _media(data_dir)
    dev = _media_dev(data_dir, media)
    if dev is None:
        return False
    for s in st["sources"]:
        if s["kind"] not in ("computer", "disk"):
            continue
        files = _read(data_dir, f"files-{s['id']}.json", [])
        if any(f[3] == dev and kind_of(f[0]) in ("films", "series") for f in files):
            return True
    return False


def _free(media):
    if not media:
        return None
    try:
        got = folders._read(media)
    except (ValueError, OSError):
        return None
    return got.get("free")


# The copy -------------------------------------------------------------------------------------------------------------

# Reads lines "source<TAB>destination<TAB>size<TAB>copy|link" on its input. For each: a file already there with the
# same size is kept (HAVE); any other file there is never written over (CLASH); free space is checked first (SPACE,
# then it stops); a link is tried when asked and the copy is made when it cannot be; the copy is made under a
# .starboard-part name and only renamed when its size is right. It only ever reads the source.
COPY_SCRIPT = r"""
nice=""; command -v nice >/dev/null 2>&1 && nice="nice -n 19"
io=""; command -v ionice >/dev/null 2>&1 && ionice -c 3 true 2>/dev/null && io="ionice -c 3"
tab="$(printf '\t')"
while IFS="$tab" read -r src dst size mode; do
  [ -n "$src" ] || continue
  if [ -e "$dst" ]; then
    if [ "$(stat -c %s "$dst")" = "$size" ]; then printf 'HAVE\t%s\n' "$dst"; else printf 'CLASH\t%s\n' "$dst"; fi
    continue
  fi
  [ -f "$src" ] || { printf 'GONE\t%s\n' "$dst"; continue; }
  dir="${dst%/*}"; mkdir -p "$dir" || { printf 'FAIL\t%s\n' "$dst"; continue; }
  if [ "$mode" = link ] && ln "$src" "$dst" 2>/dev/null; then printf 'LINK\t%s\n' "$dst"; continue; fi
  free=$(df -Pk "$dir" | awk 'NR==2 {print $4}')
  if [ -n "$free" ] && [ $((free / 1024)) -lt $(( (size + MARGIN) / 1048576 )) ]; then printf 'SPACE\t%s\n' "$dst"; exit 3; fi
  if $io $nice cp -p "$src" "$dst.starboard-part" 2>/dev/null && [ "$(stat -c %s "$dst.starboard-part")" = "$size" ]; then
    mv "$dst.starboard-part" "$dst" && printf 'DONE\t%s\n' "$dst"
  else
    printf 'FAIL\t%s\n' "$dst"
  fi
done
""".replace("MARGIN", str(MARGIN))


def status(data_dir):
    job = _read(data_dir, "job.json", {"state": "none"})
    return job


def _say(data_dir, **kw):
    job = status(data_dir)
    job.update(kw, updated=time.time())
    _write(data_dir, "job.json", job)
    return job


def start(app_or_cfg, data_dir, run=None, wait=60):
    """Starts the copy in the background, after the checks: something to bring in, nothing left needing a look that
    would be copied, and enough space. Refused while a copy runs."""
    plan = _read(data_dir, "plan.json", {})
    if not plan.get("items"):
        raise BringInError("There is nothing to bring in. Check names first")
    sp = space(data_dir, plan)
    if not sp["enough"]:
        raise BringInError(f"Not enough space: {_size(sp['needed'])} to copy and {_size(sp['free'] or 0)} free, of which "
                           f"{_size(MARGIN)} is always kept free. Leave some titles or a source out, or free some space")
    job = status(data_dir)
    if job.get("state") in ("running", "waiting") and data_dir in _jobs and _jobs[data_dir].is_alive():
        raise BringInError("A copy is running already")
    todo = sum(len(i["files"]) for i in plan["items"] if i["state"] == "matched")
    _say(data_dir, state="running", phase="starting", started=time.time(), finished=None, error="", files_total=todo,
         files_done=0, bytes_total=sum(i["size"] for i in plan["items"] if i["state"] == "matched"), bytes_done=0,
         current="", paused=False)
    _go(app_or_cfg, data_dir, run, wait)
    return status(data_dir)


def _go(app_or_cfg, data_dir, run=None, wait=60):
    t = threading.Thread(target=_run, args=(app_or_cfg, data_dir, run, wait), name="bring-in", daemon=True)
    _jobs[data_dir] = t
    t.start()


def pause(data_dir):
    job = status(data_dir)
    if job.get("state") not in ("running", "waiting"):
        raise BringInError("There is no copy running")
    return _say(data_dir, paused=True, state="paused")


def carry_on(app_or_cfg, data_dir, run=None, wait=60):
    job = status(data_dir)
    if job.get("state") not in ("paused", "stopped"):
        raise BringInError("There is no paused copy")
    _say(data_dir, paused=False, state="running", error="")
    if not (data_dir in _jobs and _jobs[data_dir].is_alive()):
        _go(app_or_cfg, data_dir, run, wait)
    return status(data_dir)


def resume_after_restart(app_or_cfg, data_dir):
    """Called once as Starboard starts: a copy that was running when it stopped carries on where it was."""
    if status(data_dir).get("state") in ("running", "waiting"):
        from . import logs
        logs.event("info", "bring in", "Carrying on bringing in your media after a restart")
        _go(app_or_cfg, data_dir)


def _cfg(app_or_cfg):
    return getattr(app_or_cfg, "config", app_or_cfg)


def _stopping(data_dir):
    return status(data_dir).get("paused") is True


def _run(app_or_cfg, data_dir, run=None, wait=60):
    from . import logs
    if not _lock.acquire(blocking=False):
        _say(data_dir, state="waiting", phase="queued", error="Another copy is running: this one starts after it")
        _lock.acquire()
    try:
        cfg = _cfg(app_or_cfg)
        plan = _read(data_dir, "plan.json", {})
        # 1. Reelix checks every name first, when the plan was made before Reelix ran (a new install).
        if not plan.get("checked"):
            while not _reelix_ready(cfg):
                _say(data_dir, state="waiting", phase="reelix", error="")
                if _stopping(data_dir):
                    return
                time.sleep(wait)
                cfg = _cfg(app_or_cfg)
            _say(data_dir, state="running", phase="checking")
            before = {i["key"]: (i["title"], i["year"], i["state"]) for i in plan["items"]}
            plan = check_names(cfg, data_dir, say=lambda n, total: _say(data_dir, current=f"{n} of {total}"))
            for i in plan["items"]:
                was = before.get(i["key"])
                if was and was[2] == "matched" and i["state"] != "matched":
                    i["why"] = (i.get("why") or "") + " (held back: Reelix did not agree with the name)"
            _write(data_dir, "plan.json", plan)
        # 2. Cloud services are copied down to the staging folder first.
        _stage_clouds(data_dir, run)
        # 3. The copy.
        _say(data_dir, state="running", phase="copying")
        if not _copy_all(data_dir, run):
            return
        # 4. Reelix adds each title and names each file its own way.
        _say(data_dir, state="running", phase="adding", current="")
        added = _add_to_reelix(cfg, data_dir)
        moved = _staging_to_holding(data_dir)
        report = _report(data_dir, added, moved)
        _say(data_dir, state="done", phase="done", finished=time.time(), current="", report=report["counts"])
        logs.event("info", "bring in", f"Brought in {report['counts']['copied']} titles; {report['counts']['look']} need a look; "
                   f"{report['counts']['left']} left where they are")
    except Exception as e:  # noqa: BLE001 - the page says what stopped it, and it can carry on
        _say(data_dir, state="stopped", error=str(e) or e.__class__.__name__)
        logs.event("warning", "bring in", f"Bringing in media stopped: {e}")
    finally:
        _lock.release()


def _copy_all(data_dir, run=None):
    """Copies every matched title's files, in batches, at low priority. Returns False when it stopped (paused, out of
    space or a problem): what is done stays done, and the next start carries on from there."""
    plan = _read(data_dir, "plan.json", {})
    st = settings(data_dir)
    media = plan.get("media") or st["media"] or _media(data_dir)
    sources = {s["id"]: s for s in st["sources"]}
    media_dev = _media_dev(data_dir, media)
    pending = [(i, f) for i in plan["items"] if i["state"] == "matched" for f in i["files"] if not f.get("done")]
    done_files = sum(1 for i in plan["items"] if i["state"] == "matched" for f in i["files"] if f.get("done"))
    done_bytes = sum(f["size"] for i in plan["items"] if i["state"] == "matched" for f in i["files"] if f.get("done"))
    while pending:
        if _stopping(data_dir):
            return False
        sp = space(data_dir, plan)
        if sp["free"] is not None and sp["free"] < MARGIN + min(f["size"] for _, f in pending[:1]):
            _say(data_dir, state="stopped", error="The media disk is nearly full, so the copy stopped. Free some space, then Carry on")
            return False
        # One batch from one source at a time, so the helper needs only that source.
        sid = pending[0][0]["source"]
        batch, total = [], 0
        for i, f in pending:
            if i["source"] != sid:
                continue
            if batch and (len(batch) >= BATCH_FILES or total + f["size"] > BATCH_BYTES):
                break
            batch.append((i, f))
            total += f["size"]
        s = sources.get(sid)
        if not s:
            for _i, f in batch:
                f["done"], f["result"] = True, "GONE"
            pending = [p for p in pending if p not in batch]
            continue
        _say(data_dir, current=batch[0][0]["title"])
        results = _copy_batch(data_dir, s, media, media_dev, st, batch, run,
                              lambda n, b: _say(data_dir, files_done=done_files + n, bytes_done=done_bytes + b))
        for _i, f in batch:
            r = results.get(f["dst"])
            if r in ("DONE", "LINK", "HAVE"):
                f["done"], f["result"] = True, r
                done_files += 1
                done_bytes += f["size"]
            elif r in ("CLASH", "GONE", "FAIL"):
                f["done"], f["result"] = True, r  # said in the report, not tried again
        _write(data_dir, "plan.json", plan)
        _say(data_dir, files_done=done_files, bytes_done=done_bytes)
        if "SPACE" in results.values():
            _say(data_dir, state="stopped", error="The media disk is nearly full, so the copy stopped. Free some space, then Carry on")
            return False
        if _stopping(data_dir):
            return False
        pending = [(i, f) for i, f in pending if not f.get("done")]
        if any(results.get(f["dst"]) is None for _, f in batch) and not any(r for r in results.values()):
            _say(data_dir, state="stopped", error="The copy did not answer. Carry on to try again")
            return False
    return True


def _copy_batch(data_dir, s, media, media_dev, st, batch, run, progress):
    """{destination: DONE|LINK|HAVE|CLASH|GONE|FAIL|SPACE} for one batch, with the destination as the plan has it."""
    local = (_local(s) or s["kind"] in CLOUD) and not _in_docker() and run is None
    lines, back = [], {}
    if local:
        src_root = _staging(data_dir, s) if s["kind"] in CLOUD else folders.inside(s["path"])
        for i, f in batch:
            dst = os.path.join(media, f["dst"])
            mode = f["mode"] = "link" if _linkable(data_dir, i, st) and f.get("dev") == media_dev else "copy"
            lines.append(f"{os.path.join(src_root, f['rel'])}\t{dst}\t{f['size']}\t{mode}")
            back[dst] = f["dst"]
        proc = subprocess.run(["sh", "-c", COPY_SCRIPT], input="\n".join(lines) + "\n", capture_output=True, text=True,  # nosec B603 B607
                              check=False, timeout=24 * 3600)
        text = proc.stdout
    else:
        mounts, where = _mounts(data_dir, s, "/s")
        mounts = mounts + [("bind", os.path.join(media, "media"), "/t")]
        for i, f in batch:
            dst = "/t/" + f["dst"][len("media/"):]
            mode = f["mode"] = "link" if _linkable(data_dir, i, st) and f.get("dev") == media_dev else "copy"
            lines.append(f"{where}/{f['rel']}\t{dst}\t{f['size']}\t{mode}")
            back[dst] = f["dst"]
        script = COPY_SCRIPT + "\n"
        script = f"cat <<'STARBOARD_LIST' | sh -c {shlex.quote(script)}\n" + "\n".join(lines) + "\nSTARBOARD_LIST\n"
        from . import stack
        env = stack.env_values(data_dir)
        user = f"{int(env.get('PUID') or 1000)}:{int(env.get('PGID') or 1000)}"
        sizes = {d: f["size"] for (i, f), d in zip(batch, back)}

        def watch(out):
            done = [ln.split("\t", 1)[1] for ln in out.splitlines() if ln.split("\t", 1)[0] in ("DONE", "LINK", "HAVE")]
            progress(len(done), sum(sizes.get(d, 0) for d in done))
        _, text = (run or _helper)(script, mounts, data_dir=data_dir, user=user, watch=watch, stop=lambda: _stopping(data_dir))
    out = {}
    for ln in text.splitlines():
        word, _, dst = ln.partition("\t")
        if dst in back:
            out[back[dst]] = word
    return out


def _stage_clouds(data_dir, run=None):
    """Copies each cloud source down into its staging folder on the media disk with rclone, read only at the cloud
    service (the sign-in asks only to read). Done once; a copy that was cut off carries on."""
    st = settings(data_dir)
    for s in st["sources"]:
        if s["kind"] not in CLOUD:
            continue
        from . import cloud_sources
        _say(data_dir, phase="downloading", current=s["name"])
        cloud_sources.copy_down(data_dir, s, _staging(data_dir, s), run=run, stop=lambda: _stopping(data_dir))


def _staging_to_holding(data_dir):
    """The staging folders of cloud sources go to the holding folder on the media disk (never deleted here). Returns
    where they went."""
    st = settings(data_dir)
    media = st["media"] or _media(data_dir)
    staging = os.path.join(media, ".starboard-bring-in") if media else ""
    if not staging or not os.path.isdir(staging) or not os.listdir(staging):
        return ""
    holding = os.path.join(media, ".starboard-holding", time.strftime("bring-in-%Y-%m-%d-%H%M%S"))
    os.makedirs(os.path.dirname(holding), exist_ok=True)
    os.replace(staging, holding)
    with open(holding + ".from.json", "w", encoding="utf-8") as f:
        json.dump({"from": staging, "what": "Files copied down from cloud services to be brought in", "held": time.time()}, f)
    return holding


def _reelix_path(rel):
    return f"{REELIX_DATA}/{rel}"


def _add_to_reelix(cfg, data_dir):
    """Reelix's own library import adds each film and series where it now is (it has its id from Check names), then
    Reelix's rename gives every file Reelix's own name. Music and books go through Reelix's book and music import,
    by artist and author folder: the sure ones are added, the rest wait in Library, Bring in. Returns {kind: added}."""
    from . import media_import
    plan = _read(data_dir, "plan.json", {})
    added = {}
    copied = [i for i in plan["items"] if i["state"] == "matched" and any(f.get("result") in ("DONE", "LINK", "HAVE") for f in i["files"])]
    try:
        roots = media_import._call(cfg, "GET", "/rootfolders") or []
        profiles = [p for p in media_import._call(cfg, "GET", "/qualityprofiles") or [] if p.get("family", "video") == "video"]
    except media_import.ImportError_:
        return {"error": "Reelix did not answer, so the titles wait in Library, Bring in"}
    for kind, media_kind, rename_kind in (("films", "movie", "movie"), ("series", "series", "series")):
        items = list({i["folder"]: i for i in copied if i["kind"] == kind and i.get("tmdb_id")}.values())  # a show from two sources once
        root = next((r for r in roots if r.get("media_kind") == media_kind and _reelix_path(TARGET[kind]).startswith(str(r.get("path", "")).rstrip("/"))), None)
        if not items or not root or not profiles:
            continue
        body = {"root_folder_id": root["id"], "search_on_add": False,
                "items": [{"path": _reelix_path(i["folder"]), "tmdb_id": int(i["tmdb_id"]), "quality_profile_id": profiles[0]["id"]} for i in items]}
        try:
            out = media_import._call(cfg, "POST", "/libraryimport", body, timeout=300) or {}
            ids = out.get("added") or []
            added[kind] = len(ids)
            for e in out.get("errors") or []:
                for i in items:
                    if _reelix_path(i["folder"]) == e.get("path"):
                        i["reelix_error"] = e.get("message")
            if ids:
                media_import._call(cfg, "POST", "/rename", {"kind": rename_kind, "ids": ids}, timeout=120)
        except media_import.ImportError_ as e:
            added[f"{kind}_error"] = str(e)
    for kind, scan_path, match_path, slim, run_fn in (
            ("music", "/musicrootfolders", "/musicimport/match", media_import._slim_artist, media_import.run_music),
            ("audiobooks", "/bookrootfolders", "/bookimport/match", lambda c: media_import._slim_book(c, None), media_import.run_books),
            ("books", "/bookrootfolders", "/bookimport/match", lambda c: media_import._slim_book(c, None), media_import.run_books)):
        items = [i for i in copied if i["kind"] == kind]
        if not items:
            continue
        try:
            roots_b = media_import._call(cfg, "GET", scan_path) or []
            want = {"music": "music", "audiobooks": "audiobook", "books": "ebook"}[kind]
            root = next((r for r in roots_b if r.get("kind", "music") == want), None)
            if not root:
                continue
            paths = sorted({_reelix_path(i["folder"].rsplit("/", 1)[0]) for i in items})
            matched = media_import._call(cfg, "POST", match_path, {"root_folder_id": root["id"], "paths": paths}, timeout=180) or []
            sure = [slim(c) for c in matched]
            keep = [{"path": c["path"], "id": c["matches"][0]["id"]} for c in sure if c.get("sure") and c.get("matches")]
            if keep:
                got = run_fn(cfg, root["id"], keep)
                added[kind] = got["added"]
            for c in sure:
                if not (c.get("sure") and c.get("matches")):
                    for i in items:
                        if _reelix_path(i["folder"].rsplit("/", 1)[0]) == c["path"]:
                            i["reelix_error"] = "Choose the right " + ("artist" if kind == "music" else "author") + " in Library, Bring in"
        except media_import.ImportError_ as e:
            added[f"{kind}_error"] = str(e)
    _write(data_dir, "plan.json", plan)
    return added


def _report(data_dir, added, moved):
    """The end report: copied, needs a look, left where it is, each with what to do."""
    plan = _read(data_dir, "plan.json", {})
    st = settings(data_dir)
    names = {s["id"]: s["name"] for s in st["sources"]}
    copied, look, left = [], [], []
    for i in plan["items"]:
        row = {"title": i["title"] + (f" ({i['year']})" if i.get("year") else ""), "kind": i["kind"], "to": i["folder"],
               "from": names.get(i["source"], "")}
        if i["state"] == "matched":
            results = [f.get("result") for f in i["files"]]
            if any(r in ("DONE", "LINK", "HAVE") for r in results):
                bad = [f for f in i["files"] if f.get("result") in ("CLASH", "FAIL", "GONE")]
                unlinked = [f for f in i["files"] if f.get("mode") == "link" and f.get("result") == "DONE"]
                copied.append({**row, "linked": "LINK" in results,
                               "note": i.get("reelix_error") or (f"{len(bad)} {'file was' if len(bad) == 1 else 'files were'} not copied: a different file "
                                                                 f"with the same name is already there" if bad else "") or
                               ("Copied, not linked: the disks under the pool are different, so a link could not be made" if unlinked else "")})
            else:
                look.append({**row, "why": "It could not be copied. Check the source is still there, then bring it in again"})
        elif i["state"] == "look":
            look.append({**row, "why": i.get("why") or "Choose the right match"})
        else:
            left.append({**row, "why": i.get("why", "")})
    seen_to, once = set(), []
    for row in copied:  # a series brought in from two sources is one title in the report
        if row["to"] not in seen_to:
            seen_to.add(row["to"])
            once.append(row)
    copied = once
    for x in plan["left"]:
        left.append({"title": os.path.basename(x["rel"]), "kind": None, "from": f"{names.get(x['source'], '')}: {x['rel']}", "why": x["why"]})
    report = {"at": time.time(), "copied": copied, "look": look, "left": left, "added": added, "holding": moved,
              "counts": {"copied": len(copied), "look": len(look), "left": len(left)}}
    _write(data_dir, "report.json", report)
    return report


def report(data_dir, part="copied", start=0, size=50):
    r = _read(data_dir, "report.json", {})
    if not r:
        raise BringInError("There is no report yet")
    rows = r.get(part) or []
    return {"counts": r["counts"], "part": part, "total": len(rows), "start": start, "items": rows[start:start + size],
            "holding": r.get("holding", ""), "added": r.get("added", {}), "at": r["at"]}


def finish(data_dir):
    """Got it: the report is put away and the step can be run again. The plan and job go; the sources stay."""
    job = status(data_dir)
    if job.get("state") in ("running", "waiting"):
        raise BringInError("The copy is still running. Pause it first")
    for name in ("job.json", "plan.json", "report.json"):
        path = os.path.join(_dir(data_dir), name)
        if os.path.exists(path):
            os.replace(path, path + ".last")  # the last run kept beside it, never deleted
    return status(data_dir)


def _size(n):
    return folders._size(n)
