"""A download that needs attention, in full (DASH-496). Owner, 19 November 2026: "For needs attention - I want a slide
out with a list of things to do with the file including delete".

Activity, Downloads, Queue opens a slide-out when a download's name is selected. For a download marked Needs
attention or Failed, Starboard asks, only then (lightweight rule: nothing on a timer):

- the app's queue for that one download: its state, messages, the folder it downloaded to and its download id;
- what is in that folder: Starboard runs `find` inside the app's own container (Docker's exec), so the paths are
  the ones the app itself sees, with no folder mounted into Starboard. Each file is sorted into media, a sample, an
  archive, a program (an .exe posing as an episode) or other;
- what is wrong, in plain words, from the messages and the files, and which actions fit, the likeliest first.

It also does the jobs the queue actions cannot:

- unpack: the RAR archives with `unrar` inside the app's container (Reelix has it since 10 November 2026), and zip
  files with BusyBox's `unzip` in the pinned Docker helper image, which borrows the app's folders (VolumesFrom).
  Up to three rounds, for archives inside archives. Then Reelix is asked to try the import again. One at a time.
- delete: the download app removes the download and deletes its data (Reelix's remove_from_client), with the
  blocklist when asked. What is left afterwards (a Usenet folder the client no longer tracks, say) is deleted by
  Starboard, but only the files it listed and only when the folder is the download's own: named like the release,
  at least three folders deep, and holding no other download in the queue.
- choose the film: Reelix's manual import, with a film from the library chosen by hand.

Without the Docker connection the slide-out still explains the messages and offers the queue actions; it says that
the folder could not be read.
"""
import posixpath
import re
import threading
import time
import urllib.parse

from . import containers, logs, services

MAX_FILES = 2000
DEPTH = "5"
VIDEO = {"mkv", "mp4", "avi", "m4v", "ts", "m2ts", "wmv", "mov", "webm", "mpg", "mpeg", "vob", "iso"}
AUDIO = {"mp3", "flac", "m4a", "m4b", "aac", "ogg", "opus", "wav", "wma", "alac", "ape"}
BOOK = {"epub", "mobi", "azw", "azw3", "pdf", "cbz", "cbr", "cb7", "djvu", "fb2"}
SUBTITLE = {"srt", "ass", "ssa", "sub", "idx", "vtt", "sup"}
PROGRAM = {"exe", "msi", "bat", "cmd", "scr", "com", "pif", "vbs", "vbe", "ps1", "jar", "lnk", "apk", "dmg", "app", "hta", "wsf", "cpl"}
_RAR_PART = re.compile(r"\.part(\d+)\.rar$", re.I)
_OLD_VOLUME = re.compile(r"\.(r\d{2}|s\d{2}|\d{3})$", re.I)
_SAMPLE = re.compile(r"(^|[\W_])sample([\W_]|$)", re.I)
KIND_WORDS = {"media": "Media", "sample": "Sample", "archive": "Archive", "program": "Program", "subtitle": "Subtitles", "other": "Other"}
REELIX_STUCK = {"import_pending", "importPending", "importBlocked", "failed_pending", "failedPending"}
KINDS = {"sonarr": "episode", "radarr": "film", "readarr": "book", "lidarr": "album",
         "series": "episode", "movie": "film", "book": "book", "album": "album", "radio_episode": "radio episode"}

_jobs = {}
_jobs_lock = threading.Lock()
_unpacking = threading.Lock()  # one unpack at a time, on the whole server


# Sizes and words -------------------------------------------------------------------------------------------

def size_words(n):
    n = float(n or 0)
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{int(n)} bytes" if unit == "bytes" else f"{n:.1f} {unit}".replace(".0 ", " ")
        n /= 1024
    return ""


def _plural(n, word, many=None):
    return f"{n} {word if n == 1 else (many or word + 's')}"


# The download ------------------------------------------------------------------------------------------------

def _native_for(all_services, service):
    if service.get("icon") != "reelix":
        return None
    natives = services.reelix_native(all_services)
    base = str(service.get("url", "")).rstrip("/")
    base = next((base[:-len(x)] for x in services.COMPAT_SUFFIXES if base.endswith(x)), base)
    return next((n for n in natives if n["url"][:-len("/api/v1")] == base), natives[0] if natives else None)


def find(all_services, service_id, item_id):
    """One download in the queue, from the app's own queue: {title, state, messages, output_path, download_id, kind,
    media_id, can_manual_import, client, reelix, service_id, item_id, size}. LookupError when it has gone."""
    service = next((s for s in all_services if str(s.get("id")) == str(service_id)), None)
    if not service or not str(item_id).isdigit():
        raise LookupError("This download is not in the queue")
    item_id = int(item_id)
    native = _native_for(all_services, service)
    if native:
        page = services._api(native, "/queue", {"page": 1, "page_size": 0}) or {}
        r = next((x for x in page.get("items") or [] if x.get("id") == item_id), None)
        if r:
            media = r.get("media") or {}
            return {"title": r.get("title") or "Unknown", "state": r.get("state") or "", "client_state": r.get("client_state") or "",
                    "messages": [str(m) for m in r.get("messages") or []][:30], "output_path": r.get("output_path") or "",
                    "download_id": r.get("download_id") or "", "kind": KINDS.get(media.get("kind", ""), KINDS.get(service["type"], "")),
                    "media_id": media.get("id"), "media_title": media.get("title") or "", "can_manual_import": bool(r.get("can_manual_import")),
                    "client": r.get("download_client") or "", "reelix": True, "service_id": service["id"], "item_id": item_id,
                    "size": r.get("size") or 0, "native": native, "service": service}
    if service["type"] not in ("sonarr", "radarr", "lidarr", "readarr"):
        raise LookupError("This download is not in the queue")
    params = {"pageSize": 250, "includeUnknownSeriesItems": "true"}
    page = services._api(service, "/queue", params) or {}
    r = next((x for x in page.get("records") or [] if x.get("id") == item_id), None)
    if not r:
        raise LookupError("This download has left the queue")
    messages = [str(m) for s in r.get("statusMessages") or [] for m in s.get("messages") or []]
    if r.get("errorMessage"):
        messages.insert(0, str(r["errorMessage"]))
    return {"title": r.get("title") or "Unknown", "state": services._queue_state(r), "client_state": r.get("status") or "",
            "messages": messages[:30], "output_path": r.get("outputPath") or "", "download_id": r.get("downloadId") or "",
            "kind": KINDS.get(service["type"], ""), "media_id": r.get("movieId") or r.get("seriesId"), "media_title": "",
            "can_manual_import": False, "client": r.get("downloadClient") or "", "reelix": service.get("icon") == "reelix",
            "service_id": service["id"], "item_id": item_id, "size": r.get("size") or 0, "native": native, "service": service}


def container_for(all_services, service):
    """The running container the app is in, by the same rules as Apps, Updates; for Reelix's Sonarr-style entries,
    the Reelix entry's container. None without the Docker connection."""
    if not containers.available():
        return None
    try:
        found = [{**c, "service": c.get("service", "")} for c in containers.containers(light=True)]
    except containers.DockerError:
        return None
    candidates = [service]
    if service.get("icon") == "reelix":
        candidates += [s for s in all_services if s.get("icon") == "reelix" and s is not service]
        candidates.append({"id": "reelix", "name": "Reelix"})
    for s in candidates:
        c = containers.match(s, found)
        if c:
            return c["name"]
    return None


# Running a command in the app's container ------------------------------------------------------------------

def _demux(raw):
    out, err, i = b"", b"", 0
    while i + 8 <= len(raw):
        n = int.from_bytes(raw[i + 4:i + 8], "big")
        chunk = raw[i + 8:i + 8 + n]
        if raw[i] == 2:
            err += chunk
        else:
            out += chunk
        i += 8 + n
    return out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def run_in(container, cmd, user="", timeout=60):
    """Runs one command (a list, never a shell line) in a running container. Returns (exit code, stdout, stderr)."""
    body = {"AttachStdout": True, "AttachStderr": True, "Cmd": [str(c) for c in cmd]}
    if user:
        body["User"] = user
    made = containers.docker("POST", f"/containers/{urllib.parse.quote(container, safe='')}/exec", body)
    raw = containers.docker("POST", f"/exec/{made['Id']}/start", {"Detach": False, "Tty": False}, raw=True, timeout=timeout)
    code = (containers.docker("GET", f"/exec/{made['Id']}/json") or {}).get("ExitCode")
    out, err = _demux(raw or b"")
    return (code if isinstance(code, int) else 1), out, err


def run_helper(container, cmd, user="", timeout=1800):
    """Runs one command in a short-lived container from the pinned helper image that sees the app's folders, with no
    network. Returns (exit code, output)."""
    containers.ensure_image()
    body = {"Image": containers.HELPER_IMAGE, "Entrypoint": [], "Cmd": [str(c) for c in cmd], "Labels": {"starboard.unpack": "1"},
            "NetworkDisabled": True, "HostConfig": {"VolumesFrom": [container], "NetworkMode": "none", "Memory": 256 * 1024 * 1024}}
    if user:
        body["User"] = user
    cid = containers.docker("POST", f"/containers/create?name=starboard-unpack-{int(time.time() * 1000)}", body)["Id"]
    try:
        containers.docker("POST", f"/containers/{cid}/start")
        code = (containers.docker("POST", f"/containers/{cid}/wait", timeout=timeout) or {}).get("StatusCode", 1)
        raw = containers.docker("GET", f"/containers/{cid}/logs?stdout=1&stderr=1&tail=40", raw=True)
    finally:
        try:
            containers.docker("DELETE", f"/containers/{cid}?force=1")
        except containers.DockerError:
            pass
    out, err = _demux(raw or b"")
    return code, (out + err)


# What is in the folder -------------------------------------------------------------------------------------

def kind_of(name, size=0):
    lower = name.lower()
    ext = lower.rsplit(".", 1)[-1] if "." in posixpath.basename(lower) else ""
    if ext in PROGRAM:
        return "program"
    if ext in ("rar", "zip", "7z") or _OLD_VOLUME.search(lower):
        return "archive"
    if ext in VIDEO or ext in AUDIO or ext in BOOK:
        return "sample" if ext in VIDEO and _SAMPLE.search(lower) else "media"
    if ext in SUBTITLE:
        return "subtitle"
    return "other"


def parse_listing(text, path):
    """find's lines (type, size, owner, relative path) as files, with the folder's owner."""
    files, owner, single = [], "", False
    for line in text.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        kind, size, who, rel = parts
        if not rel:
            owner = owner or who
            if kind == "f":  # the download is one file, not a folder
                single = True
                rel = posixpath.basename(path)
            else:
                continue
        if kind != "f":
            continue
        size = int(size) if size.isdigit() else 0
        files.append({"name": rel, "size": size, "kind": kind_of(rel, size)})
        if len(files) >= MAX_FILES:
            break
    files.sort(key=lambda f: (["program", "media", "archive", "sample", "subtitle", "other"].index(f["kind"]), f["name"].lower()))
    return files, owner, single


def summary(files, missing=False):
    """What the folder holds, in counts and words: {media, sample, archive, program, total_size, verdict, words}."""
    count = {k: sum(1 for f in files if f["kind"] == k) for k in KIND_WORDS}
    total = sum(f["size"] for f in files)
    if missing:
        verdict, words = "missing", "The download folder is not there any more, or is empty."
    elif count["program"]:
        verdict, words = "program", f"{_plural(count['program'], 'program')} (such as an .exe), which is not media."
    elif count["media"]:
        verdict, words = "media", f"{_plural(count['media'], 'media file')}."
    elif count["archive"]:
        verdict, words = "archive", "Archives only: the media is packed inside them."
    elif count["sample"]:
        verdict, words = "sample", "A sample only: a short clip, not the whole thing."
    elif files:
        verdict, words = "other", "No media: only small extra files."
    else:
        verdict, words = "missing", "The download folder is empty."
    return {**count, "total_size": total, "verdict": verdict, "words": words, "files": len(files)}


def _set_name(name):
    """The name a RAR set is shown under: the .rar file for its .r00 to .r99 parts and its .partNN.rar volumes."""
    lower = name.lower()
    m = _RAR_PART.search(lower)
    if m:
        return name[:m.start()] + ".rar"
    m = re.search(r"\.r\d{2}$", lower)
    return name[:m.start()] + ".rar" if m else None


def grouped(files):
    """The files as the slide-out lists them: each RAR set as one row with its number of parts and total size."""
    out, sets = [], {}
    for f in files:
        key = _set_name(f["name"]) or (f["name"] if f["name"].lower().endswith(".rar") else None)
        if f["kind"] == "archive" and key:
            g = sets.get(key)
            if not g:
                g = sets[key] = {"name": key, "size": 0, "kind": "archive", "parts": 0}
                out.append(g)
            g["size"] += f["size"]
            g["parts"] += 1
        else:
            out.append(dict(f))
    return out


def first_volumes(files):
    """The archives to unpack: each RAR set's first volume and each zip file. 7-Zip and split .001 files are listed
    as not unpackable."""
    out, other = [], []
    for f in files:
        lower = f["name"].lower()
        if lower.endswith(".rar"):
            m = _RAR_PART.search(lower)
            if not m or int(m.group(1)) == 1:
                out.append({"name": f["name"], "kind": "rar"})
        elif lower.endswith(".zip"):
            out.append({"name": f["name"], "kind": "zip"})
        elif lower.endswith(".7z") or lower.endswith(".001"):
            other.append(f["name"])
    return out, other


def list_folder(container, path):
    """({files, owner, single, missing}) for a download's folder, as the app's container sees it."""
    code, out, err = run_in(container, ["find", path, "-maxdepth", DEPTH, "-xdev", "-printf", "%y\t%s\t%U:%G\t%P\n"], timeout=30)
    if code != 0 and not out:
        if "No such file" in err:
            return {"files": [], "owner": "", "single": False, "missing": True}
        raise RuntimeError((err or "find did not answer").strip().splitlines()[-1][:200])
    files, owner, single = parse_listing(out, path)
    return {"files": files, "owner": owner, "single": single, "missing": not files}


# Plain words and the actions that fit -------------------------------------------------------------------------

def _has(messages, *needles):
    text = " ".join(messages).lower()
    return any(n in text for n in needles)


def diagnose(item, folder):
    """What is wrong, most important first: [{tone, title, text}]. folder is None when it could not be read."""
    m = item["messages"]
    app = "Reelix" if item["reelix"] else "The app"
    s = folder["summary"] if folder else None
    out = []
    if s and s["program"]:
        out.append({"tone": "danger", "title": "This download holds a program, not media",
                    "text": "A file such as an .exe posing as an episode or film is a sign of a fake or harmful release. "
                            "Do not open it. Remove it, delete the files and add it to the blocklist, so it is never downloaded again."})
    if _has(m, "not part of the series"):
        out.append({"tone": "warning", "title": "The episode is numbered differently",
                    "text": f"This release numbers its episodes another way, so {app} could not tell which episode it is. "
                            "Choose the episode, or remove the download if you already have it."})
    if _has(m, "not an upgrade"):
        out.append({"tone": "warning", "title": "You already have a copy that is as good or better",
                    "text": f"{app} kept the copy in your library. If you do not want this one, remove it and delete the files to free the space."})
    if _has(m, "already imported", "has already been imported", "was already imported"):
        out.append({"tone": "warning", "title": "This was imported before",
                    "text": "The files are already in your library. Remove the download and delete the files to free the space."})
    if (item["state"] in ("failed_pending", "failedPending", "failed") or item["client_state"] == "failed") and not out:
        out.append({"tone": "warning", "title": "The download failed",
                    "text": f"{item['client'] or 'The download client'} could not finish it. Find another release, or remove it."})
        return out
    nothing = _has(m, "no video files", "no files found", "no audio files", "no book files", "no files were found",
                   "nothing to import", "no eligible")
    if s and not s["program"] and (nothing or not out):
        if s["media"] and s["archive"] and nothing:
            out.append({"tone": "warning", "title": "The files are ready to import",
                        "text": f"The archives are unpacked and the media files are in the folder now. Try the import again, and {app} imports them."})
        elif s["verdict"] == "archive" or (s["archive"] and not s["media"]):
            out.append({"tone": "warning", "title": "The files are inside archives",
                        "text": f"{app} found nothing it could import because the media is packed in archives. "
                                "Unpack the archives, then it imports what is inside."})
        elif s["verdict"] == "sample":
            out.append({"tone": "warning", "title": "Only a sample was downloaded",
                        "text": "The folder holds a short sample clip, not the whole thing. Find another release, and delete this one."})
        elif s["verdict"] == "other":
            out.append({"tone": "warning", "title": "No media was downloaded",
                        "text": "The folder holds only small extra files, such as .nfo or .par2 files. Find another release, and delete this one."})
        elif s["verdict"] == "missing":
            out.append({"tone": "warning", "title": "The files are missing",
                        "text": "The download folder is not there any more or is empty, so there is nothing to import. "
                                "Remove it from the list, or find another release."})
    if not out:
        out.append({"tone": "warning", "title": f"{app} needs a decision from you" if m else f"{app} flagged it without a message",
                    "text": "Read its messages, then choose an action." if m else "Try the import again, or choose another action."})
    return out


def actions(item, folder, unpack_tools):
    """The actions that fit, in order, and the one to suggest. unpack_tools: {"rar": bool, "zip": bool}."""
    s = folder["summary"] if folder else None
    reelix = item["reelix"] and item.get("native")
    stuck = item["state"] in REELIX_STUCK or item["client_state"] in ("completed", "warning", "failed")
    out = []
    if s and s["archive"] and not s["media"] and reelix:  # once the media is out, Try the import again instead
        vols, _ = first_volumes(folder["files"])
        if any(unpack_tools.get(v["kind"]) for v in vols):
            out.append("unpack")
    if reelix and item["download_id"] and _has(item["messages"], "not part of the series") and item["kind"] == "episode":
        out.append("choose-episode")
    if reelix and item["download_id"] and item["kind"] == "film" and (not s or s["media"]):
        out.append("choose-film")
    if reelix and stuck:
        out += ["ignore"] if s and s["program"] else ["import", "ignore"]  # a program is never imported
    out += ["block-search", "remove-keep", "delete", "delete-block"]
    if s and s["program"]:
        suggest = "delete-block"
    elif item["state"] in ("failed_pending", "failedPending", "failed") or item["client_state"] == "failed":
        suggest = "block-search"  # it never finished: another release is the way on
    elif "unpack" in out:
        suggest = "unpack"
    elif "choose-episode" in out:
        suggest = "choose-episode"
    elif s and s["verdict"] in ("sample", "missing", "other"):
        suggest = "block-search"  # nothing worth keeping: a whole release is needed
    elif _has(item["messages"], "not an upgrade", "already imported"):
        suggest = "delete"  # the library already has it
    elif "import" in out:
        suggest = "import"
    else:
        suggest = out[0]
    return out, suggest


def unpack_tools(container):
    """Which archives can be unpacked here: RAR with unrar in the app's container, zip with the helper image."""
    if not container:
        return {"rar": False, "zip": False}
    try:
        code, out, _ = run_in(container, ["sh", "-c", "command -v unrar"], timeout=10)
    except (containers.DockerError, KeyError):
        return {"rar": False, "zip": False}
    return {"rar": code == 0 and bool(out.strip()), "zip": True}


def details(all_services, service_id, item_id):
    """Everything the slide-out shows for one download."""
    item = find(all_services, service_id, item_id)
    container = container_for(all_services, item["service"])
    folder, folder_problem, tools = None, "", {"rar": False, "zip": False}
    if not item["output_path"]:
        folder_problem = "The app has not said where this download is yet."
    elif not container:
        folder_problem = ("Starboard cannot read the download folder without its Docker connection (the installer asks about it)."
                          if not containers.available() else f"Starboard could not find {item['service']['name']}'s container.")
    else:
        try:
            got = list_folder(container, item["output_path"])
            folder = {**got, "summary": summary(got["files"], got["missing"])}
            tools = unpack_tools(container)
        except (containers.DockerError, RuntimeError) as e:
            folder_problem = f"The download folder could not be read: {str(e)[:200]}"
    acts, suggest = actions(item, folder, tools)
    vols, not_unpackable = first_volumes(folder["files"]) if folder else ([], [])
    job = unpack_state(item["service_id"], item["item_id"])
    return {
        "title": item["title"], "state": item["state"], "client_state": item["client_state"], "messages": item["messages"],
        "kind": item["kind"], "media_title": item["media_title"], "download_id": item["download_id"], "client": item["client"],
        "reelix": item["reelix"], "path": item["output_path"],
        "files": [{**f, "kind_words": KIND_WORDS[f["kind"]], "size_words": size_words(f["size"])} for f in grouped(folder["files"])] if folder else [],
        "file_names": [f["name"] for f in folder["files"]][:200] if folder else [],
        "summary": {**folder["summary"], "total_words": size_words(folder["summary"]["total_size"])} if folder else None,
        "folder_problem": folder_problem, "diagnosis": diagnose(item, folder), "actions": acts, "suggest": suggest,
        "archives": {"to_unpack": len([v for v in vols if tools.get(v["kind"])]),
                     "rar_without_tool": len([v for v in vols if v["kind"] == "rar" and not tools["rar"]]),
                     "not_unpackable": len(not_unpackable)},
        "unpack": job,
    }


# Unpacking -------------------------------------------------------------------------------------------------

def _key(service_id, item_id):
    return f"{service_id}|{item_id}"


def unpack_state(service_id, item_id):
    with _jobs_lock:
        job = _jobs.get(_key(service_id, item_id))
        return dict(job) if job else None


def _set(key, **kw):
    with _jobs_lock:
        _jobs.setdefault(key, {}).update(kw, at=round(time.time()))


def start_unpack(all_services, service_id, item_id, data_dir=None):
    """Starts unpacking one download's archives in the background. Returns the job; ValueError when it cannot."""
    item = find(all_services, service_id, item_id)
    if not (item["reelix"] and item.get("native")):
        raise ValueError("Only Reelix can import a download after it is unpacked")
    container = container_for(all_services, item["service"])
    if not container or not item["output_path"]:
        raise ValueError("Starboard cannot reach the download folder")
    key = _key(item["service_id"], item["item_id"])
    current = unpack_state(item["service_id"], item["item_id"])
    if current and current.get("state") == "running":
        return current
    _set(key, state="running", words="Waiting for another unpack to finish" if _unpacking.locked() else "Unpacking", done=0)
    threading.Thread(target=_unpack, args=(item, container, key, data_dir), daemon=True, name="unpack").start()
    return unpack_state(item["service_id"], item["item_id"])


def _unpack(item, container, key, data_dir):
    with _unpacking:
        try:
            words = _unpack_rounds(item, container, key)
        except Exception as e:  # noqa: BLE001 - the job says what happened; nothing else waits on it
            logs.event("warning", "downloads", f"Unpacking {item['title']} failed: {e}")
            _set(key, state="failed", words=f"Not unpacked: {(str(e) or type(e).__name__)[:300]}")
            return
    try:
        services._api(item["native"], f"/queue/{int(item['item_id'])}/import", method="POST")
        services.forget("queue")
        words += " Reelix is importing it now."
    except services.ServiceError as e:
        words += f" Reelix could not be asked to import it ({e}); use Try the import again."
    logs.event("info", "downloads", f"Unpacked the archives of {item['title']}")
    if data_dir:
        from . import queue_issues
        queue_issues.note_tried(data_dir, "Unpacked its archives from the Downloads page and asked Reelix to import it",
                                item["service_id"], item["item_id"], item["download_id"], item["title"])
    _set(key, state="done", words=words)


def unsafe_entries(names):
    """Entries of an archive that would land outside the folder it is unpacked into: an absolute path or a .. step.
    A fake release may carry one, so such an archive is never unpacked."""
    bad = []
    for name in names:
        n = name.strip().replace("\\", "/")
        if n and (n.startswith("/") or re.match(r"^[A-Za-z]:", n) or ".." in n.split("/")):
            bad.append(name.strip())
    return bad


def _zip_names(listing):
    """Names from BusyBox's `unzip -l`: the lines between the two rules of dashes, after length, date and time."""
    names, inside = [], False
    for line in listing.splitlines():
        if line.strip().startswith("---"):
            inside = not inside
            continue
        if inside:
            parts = line.split(None, 3)
            if len(parts) == 4:
                names.append(parts[3])
    return names


def _unpack_rounds(item, container, key):
    base = item["output_path"]
    done, count, tools = set(), 0, unpack_tools(container)
    for _ in range(3):  # archives inside archives
        got = list_folder(container, base)
        if got["single"]:
            raise RuntimeError("The download is a single file, not a folder of archives")
        vols, _ = first_volumes(got["files"])
        todo = [v for v in vols if v["name"] not in done and tools.get(v["kind"])]
        if not todo:
            break
        for v in todo:
            done.add(v["name"])
            full = posixpath.join(base, v["name"])
            into = posixpath.dirname(full) + "/"
            _set(key, words=f"Unpacking {posixpath.basename(v['name'])}", done=count)
            if v["kind"] == "rar":
                code, out, err = run_in(container, ["unrar", "lb", "--", full], user=got["owner"], timeout=120)
                names = out.splitlines() if code == 0 else []
            else:
                code, out = run_helper(container, ["unzip", "-l", full], user=got["owner"], timeout=120)
                names = _zip_names(out) if code == 0 else []
            bad = unsafe_entries(names)
            if code != 0 or bad:
                raise RuntimeError(f"{posixpath.basename(v['name'])}: " + (f"it holds {bad[0][:80]}, which would land outside the download folder, "
                                                                          "so it was not unpacked" if bad else "the archive could not be read"))
            if v["kind"] == "rar":
                code, out, err = run_in(container, ["unrar", "x", "-o-", "-y", "-idq", "--", full, into], user=got["owner"], timeout=3600)
                said = err or out
            else:
                code, said = run_helper(container, ["unzip", "-n", "-q", full, "-d", into], user=got["owner"])
            if code not in (0, 10):  # unrar 10: nothing new to extract
                raise RuntimeError(f"{posixpath.basename(v['name'])}: {(said or 'the tool stopped').strip().splitlines()[-1][:200]}")
            count += 1
    if not count:
        raise RuntimeError("No archive here could be unpacked")
    return f"Unpacked {_plural(count, 'archive')}."


# Removing and deleting ---------------------------------------------------------------------------------------

def _fold(text):
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def unsafe(path, title, other_paths=()):
    """Why Starboard must not delete this folder itself, or "" when it may: the path is the download's own."""
    if not path or not path.startswith("/") or posixpath.normpath(path) != path:
        return "the path is not a plain full path"
    if len([p for p in path.split("/") if p]) < 3:
        return "the folder is too near the top of the disk"
    name = posixpath.basename(path)
    stem = name.rsplit(".", 1)[0] if "." in name[-6:] else name
    a, b = _fold(stem), _fold(title)
    if len(a) < 6 or not (a == b or (len(b) >= 6 and (a.startswith(b) or b.startswith(a)))):
        return "the folder is not named like the release"
    for other in other_paths:
        if other and other != path and (other.startswith(path.rstrip("/") + "/")):
            return "another download is inside it"
    return ""


def _queue_paths(all_services, item):
    try:
        if item.get("native"):
            page = services._api(item["native"], "/queue", {"page": 1, "page_size": 0}) or {}
            return [x.get("output_path") or "" for x in page.get("items") or [] if x.get("id") != item["item_id"]]
    except services.ServiceError:
        pass
    return []


def remove(item, delete_files, block):
    """Asks the download app to remove the download: delete_files also has the download client delete its data.
    Returns words for anything that did not go as asked."""
    note = ""
    if item.get("native"):
        def go(from_client):
            services._api(item["native"], f"/queue/{int(item['item_id'])}",
                          {"remove_from_client": "true" if from_client else "false", "blocklist": "true" if block else "false",
                           "skip_redownload": "true"}, method="DELETE")
        try:
            go(delete_files)
        except services.ServiceError as e:
            if not delete_files:
                raise
            go(False)  # the client no longer has it (or is off): take it off Reelix's list; Starboard deletes the files
            note = f"{item['client'] or 'The download client'} could not remove it ({str(e)[:120]})."
    else:
        params = {"removeFromClient": "true" if delete_files else "false", "blocklist": "true" if block else "false",
                  "skipRedownload": "true"}
        services._api(item["service"], f"/queue/{int(item['item_id'])}", params, method="DELETE")
    services.forget("queue")
    return note


def delete(all_services, service_id, item_id, block=False, data_dir=None, wait=8):
    """Remove and delete the files (and add to the blocklist). Returns {deleted, freed, freed_words, left, words}."""
    item = find(all_services, service_id, item_id)
    container = container_for(all_services, item["service"])
    path = item["output_path"]
    before = None
    if container and path:
        try:
            before = list_folder(container, path)
        except (containers.DockerError, RuntimeError):
            before = None
    other_paths = _queue_paths(all_services, item)
    note = remove(item, True, block)
    left = []
    if before and not before["missing"]:
        after = before
        for _ in range(max(1, int(wait))):  # the download client deletes in its own time
            time.sleep(1)
            try:
                after = list_folder(container, path)
            except (containers.DockerError, RuntimeError):
                continue
            if after["missing"]:
                break
        listed = {f["name"] for f in before["files"]}
        left = [f for f in after["files"] if f["name"] in listed]
        why = unsafe(path, item["title"], other_paths) if left else ""
        if left and not why:
            full = [path] if before["single"] else [posixpath.join(path, f["name"]) for f in left]
            for i in range(0, len(full), 200):
                run_in(container, ["rm", "-f", "--", *full[i:i + 200]], user=before["owner"], timeout=120)
            if not before["single"]:
                run_in(container, ["find", path, "-depth", "-type", "d", "-empty", "-delete"], user=before["owner"], timeout=60)
            again = list_folder(container, path)
            left = [f for f in again["files"] if f["name"] in listed]
        elif left:
            note = (note + " " if note else "") + f"Starboard did not delete what was left, because {why}."
    total = sum(f["size"] for f in before["files"]) if before else 0
    kept = sum(f["size"] for f in left)
    freed = max(0, total - kept)
    deleted = (len(before["files"]) - len(left)) if before else 0
    if before is None:
        words = f"Removed. {item['client'] or 'The download client'} was asked to delete the files; Starboard could not check the folder."
    elif left:
        words = f"Removed. {_plural(deleted, 'file')} deleted, {size_words(freed)} freed; {_plural(len(left), 'file')} could not be deleted."
    else:
        words = f"Removed. {_plural(deleted, 'file')} deleted, {size_words(freed)} freed."
    if block:
        words += " It is on the blocklist, so it is not downloaded again."
    if note:
        words += " " + note
    logs.event("info", "downloads", f"Removed {item['title']} and deleted its files ({deleted} deleted, {len(left)} left)"
               + (", added to the blocklist" if block else ""))
    if data_dir:
        from . import queue_issues
        queue_issues.note_tried(data_dir, "Removed it and deleted its files" + (", and added it to the blocklist" if block else "")
                                + ", from the Downloads page", item["service_id"], item["item_id"], item["download_id"], item["title"])
    return {"deleted": deleted, "freed": freed, "freed_words": size_words(freed), "left": [f["name"] for f in left][:50], "words": words}


# Choose the film -------------------------------------------------------------------------------------------

def film_options(all_services, service_id, item_id, query=""):
    """The download's media files and films in the library that match the query (or the download's own)."""
    item = find(all_services, service_id, item_id)
    if not item.get("native") or not item["download_id"]:
        raise ValueError("Only Reelix can be told which film a download is")
    native = item["native"]
    preview = services._api(native, "/manualimport?" + urllib.parse.urlencode({"download_id": item["download_id"]}), timeout=60) or []
    guess = next(((f.get("media") or {}).get("id") for f in preview if (f.get("media") or {}).get("kind") == "movie"), None) or item["media_id"]
    q = (query or item["media_title"] or "").strip()[:100]
    got = services._api(native, "/movies", {"q": q, "page": 1, "page_size": 25}) if q else {}
    films = got.get("items", got) if isinstance(got, dict) else got or []
    out = [{"id": f["id"], "title": f.get("title") or "", "year": f.get("year"), "have": bool(f.get("has_file"))} for f in films if f.get("id")]
    return {"files": [{"path": f.get("path"), "name": f.get("relative_path") or f.get("path"), "size_words": size_words(f.get("size"))} for f in preview],
            "films": out, "guess": guess, "query": q}


def choose_film(all_services, service_id, item_id, movie_id, data_dir=None):
    item = find(all_services, service_id, item_id)
    if not item.get("native") or not item["download_id"] or not str(movie_id).isdigit():
        raise ValueError("Choose a film")
    native = item["native"]
    preview = services._api(native, "/manualimport?" + urllib.parse.urlencode({"download_id": item["download_id"], "movie_id": int(movie_id)}),
                            timeout=60) or []
    files = [{"path": f["path"], "movie_id": int(movie_id), "episode_ids": [], "quality": f.get("quality"), "languages": f.get("languages") or [],
              "release_group": f.get("release_group"), "download_id": item["download_id"]}
             for f in preview if f.get("path") and kind_of(f.get("relative_path") or f["path"]) == "media"]
    if not files:
        raise ValueError("This download has no film file to import")
    services._api(native, "/manualimport", method="POST", body={"files": files, "import_mode": "auto"}, timeout=60)
    services.forget("queue")
    if data_dir:
        from . import queue_issues
        queue_issues.note_tried(data_dir, "Chose the film by hand and asked Reelix to import it", item["service_id"], item["item_id"],
                                item["download_id"], item["title"])
    return {"sent": len(files)}
