"""Plug-ins from a zip file (DASH-414, plug-in API 1.15). Owner, 14 November 2026: "Add a task to add zip file installs
of plugins". For a private plug-in such as On demand, whose repository Starboard cannot download from: Settings,
Plug-ins, Add a plug-in, Upload a zip file.

What Starboard checks before anything is shown (read, below):
- the zip is at most 50 MB, unpacks to at most 200 MB in at most 2,000 files, counted as it is read, not from what the
  zip says about itself, so a zip bomb stops at the limit;
- every name stays inside the zip: no folder above it (..), no address from the top of the disk (/), no backslash or
  drive letter, no two files with the same name, and nothing but files and folders (no links, devices or pipes);
- nothing is encrypted, and starboard-plugin.json is at the top of the zip, not in a folder inside it;
- a plug-in with a container built from the zip (build: true, API 1.15) has a Dockerfile at the top, which may only
  build: no parser directives (# syntax= would run someone else's builder), no RUN --mount, --network or
  --security, no ADD from the internet or git, no COPY --from another image, no VOLUME or ONBUILD, and FROM names an
  image by name, never a variable or another plug-in's local/ image.

Then the same warning as for an address (What it may do) and the password. The build runs through Docker's own
builder with limits: 2 GB of memory with no swap beyond it, 2 processor cores, 20 minutes, no build arguments or
secrets, and only the zip's own files to build from (a tar Starboard writes from the checked files, so a link in the
zip could never point outside it). The image is tagged local/<id>:<version>, so Roll back finds the version before
without a download; the zip is kept beside the plug-in (zips/<version>.zip, the current and the previous) so a
missing image is built again on Activate. An image over 3 GB is removed (it is Starboard's own) and refused.

Nothing is downloaded from the person's computer into Starboard except the zip itself, streamed to
data/plugins/.uploads, which is tidied after an hour."""
import datetime as dt
import io
import json
import os
import re
import secrets
import shutil
import stat
import tarfile
import threading
import time
import urllib.parse
import zipfile

from . import logs, plugins

MANIFEST = "starboard-plugin.json"
DOCKERFILE = "Dockerfile"
MAX_ZIP = 50 * 1024 * 1024
MAX_UNPACKED = 200 * 1024 * 1024
MAX_FILES = 2000
MAX_MANIFEST = 256 * 1024
MAX_DOCKERFILE = 64 * 1024
MAX_NAME = 240
UPLOAD_HOURS = 1
BUILD_MEMORY_MB = 2048
BUILD_CPUS = 2
BUILD_MINUTES = 20
MAX_IMAGE = 3 * 1024 ** 3
MAX_STAGES = 6
KEPT_ZIPS = "zips"
TOKEN = r"^[0-9a-f]{32}$"


class ZipProblem(ValueError):
    """The zip cannot be used, in words for the page."""


class BuildFailed(ValueError):
    """Docker could not build the image, in words for the page, with the last lines of the build."""


# Uploads -------------------------------------------------------------------------------------------------------------

def uploads(data_dir):
    from . import plugins_admin as pa
    return os.path.join(pa.root(data_dir), ".uploads")


def _tidy(data_dir, now=None):
    """Uploads older than an hour go: Starboard's own copies of zips that were looked at and not installed."""
    where = uploads(data_dir)
    now = time.time() if now is None else now
    try:
        names = os.listdir(where)
    except OSError:
        return
    for name in names:
        p = os.path.join(where, name)
        try:
            if now - os.path.getmtime(p) > UPLOAD_HOURS * 3600:
                os.remove(p)  # nosec: Starboard's own upload copy, never the person's file
        except OSError:
            pass


def receive(data_dir, length, stream):
    """Streams an uploaded zip to data/plugins/.uploads and checks it. Returns (token, manifest, report)."""
    if not 0 < length <= MAX_ZIP:
        raise ZipProblem("Choose a zip file up to 50 MB")
    _tidy(data_dir)
    os.makedirs(uploads(data_dir), mode=0o700, exist_ok=True)
    token = secrets.token_hex(16)
    path = os.path.join(uploads(data_dir), f"{token}.zip")
    left = length
    with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
        while left:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            left -= len(chunk)
    if left:
        _drop(path)
        raise ZipProblem("The upload stopped before the end. Try again")
    try:
        manifest, report = read(path)
    except ZipProblem:
        _drop(path)
        raise
    return token, manifest, report


def _drop(path):
    try:
        os.remove(path)  # nosec: Starboard's own upload copy
    except OSError:
        pass


def path_of(data_dir, token):
    if not re.match(TOKEN, str(token or "")):
        raise LookupError("That zip file is no longer here. Upload it again")
    p = os.path.join(uploads(data_dir), f"{token}.zip")
    if not os.path.isfile(p):
        raise LookupError("That zip file is no longer here. Upload it again")
    return p


def manifest_of(data_dir, token):
    """(manifest, report, path) for an upload, checked again: the file could have changed since it was looked at."""
    p = path_of(data_dir, token)
    manifest, report = read(p)
    return manifest, report, p


# Reading and checking ------------------------------------------------------------------------------------------------

def _name_problem(name):
    if not name or len(name) > MAX_NAME or "\x00" in name:
        return "a name that is empty, too long or has a null in it"
    if "\\" in name:
        return f"a backslash in {name!r}"
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        return f"{name!r}, which starts at the top of a disk"
    parts = name.rstrip("/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        return f"{name!r}, which points outside the zip or has an empty part"
    if len(parts) > 20:
        return f"{name!r}, which is more than 20 folders deep"
    return None


def read(path):
    """Checks a zip and returns (manifest, report). report: {files, size, dockerfile: {from: [...]} or None,
    problems: [what the manifest or Dockerfile breaks]}. Raises ZipProblem when the zip itself cannot be used."""
    try:
        size = os.path.getsize(path)
    except OSError:
        raise ZipProblem("Starboard could not read that file") from None
    if size > MAX_ZIP:
        raise ZipProblem("Choose a zip file up to 50 MB")
    if not zipfile.is_zipfile(path):
        raise ZipProblem("That is not a zip file")
    seen, files, total, manifest_raw, docker_raw = set(), 0, 0, None, None
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) > MAX_FILES:
                raise ZipProblem(f"The zip has more than {MAX_FILES:,} files")
            for info in infos:
                why = _name_problem(info.filename)
                if why:
                    raise ZipProblem(f"The zip has {why}")
                key = info.filename.rstrip("/").lower()
                if key in seen:
                    raise ZipProblem(f"The zip has {info.filename!r} twice")
                seen.add(key)
                if info.flag_bits & 0x1:
                    raise ZipProblem("The zip is encrypted. Starboard takes only plain zip files")
                kind = stat.S_IFMT(info.external_attr >> 16)
                if info.is_dir():
                    if kind not in (0, stat.S_IFDIR):
                        raise ZipProblem(f"The zip has {info.filename!r}, which is not a file or folder")
                    continue
                if kind not in (0, stat.S_IFREG):
                    raise ZipProblem(f"The zip has {info.filename!r}, which is a link or a special file. "
                                     "Starboard takes only files and folders")
                files += 1
                # Read every file, counting what comes out: a zip can say a file is small and be a zip bomb.
                with z.open(info) as f:
                    got = 0
                    keep = info.filename in (MANIFEST, DOCKERFILE)
                    buf = io.BytesIO() if keep else None
                    while True:
                        chunk = f.read(1 << 16)
                        if not chunk:
                            break
                        got += len(chunk)
                        total += len(chunk)
                        if total > MAX_UNPACKED:
                            raise ZipProblem("The zip unpacks to more than 200 MB")
                        if keep:
                            if got > (MAX_MANIFEST if info.filename == MANIFEST else MAX_DOCKERFILE):
                                raise ZipProblem(f"{info.filename} is too big")
                            buf.write(chunk)
                    if info.filename == MANIFEST:
                        manifest_raw = buf.getvalue()
                    elif info.filename == DOCKERFILE:
                        docker_raw = buf.getvalue()
    except zipfile.BadZipFile as e:
        raise ZipProblem(f"The zip is damaged ({str(e)[:80]})") from None
    except (RuntimeError, NotImplementedError, EOFError, OSError) as e:  # an unknown packing or a bad checksum
        raise ZipProblem(f"Starboard could not unpack the zip ({str(e)[:80]})") from None
    if manifest_raw is None:
        nested = sorted(n for n in seen if n.endswith("/" + MANIFEST.lower()))
        raise ZipProblem(f"{MANIFEST} must be at the top of the zip" + (", not in a folder inside it" if nested else ""))
    try:
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ZipProblem(f"{MANIFEST} is not readable JSON") from None
    if not isinstance(manifest, dict):
        raise ZipProblem(f"{MANIFEST} must be a JSON object")
    report = {"files": files, "size": total, "dockerfile": None, "problems": []}
    if plugins.builds(manifest):
        if docker_raw is None:
            report["problems"].append("A container is built from the zip, so it needs a Dockerfile at the top of the zip")
        else:
            try:
                text = docker_raw.decode("utf-8")
            except UnicodeDecodeError:
                text = None
                report["problems"].append("The Dockerfile is not plain text")
            if text is not None:
                problems, bases = check_dockerfile(text)
                report["dockerfile"] = {"from": bases}
                report["problems"] += problems
    return manifest, report


IMAGE_NAME = r"^[a-z0-9]+([._-][a-z0-9]+)*(:\d+)?(/[a-z0-9]+([._-][a-z0-9]+)*)*(:[A-Za-z0-9_][A-Za-z0-9._-]{0,127})?(@sha256:[0-9a-f]{64})?$"
ALLOWED = {"FROM", "RUN", "COPY", "ADD", "WORKDIR", "ENV", "ARG", "USER", "CMD", "ENTRYPOINT", "EXPOSE", "LABEL",
           "HEALTHCHECK", "STOPSIGNAL", "SHELL", "MAINTAINER"}
REFUSED = {"ONBUILD": "ONBUILD, which would run inside other builds",
           "VOLUME": "VOLUME, which would give the plug-in a folder outside the ones Starboard mounts"}


def _instructions(text):
    """[(line number, instruction, rest)] with continuation lines joined and comments left out."""
    out, buf, start = [], "", 0
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not buf and (not s or s.startswith("#")):
            continue
        if buf and s.startswith("#"):
            continue  # a comment inside a continued instruction
        if not buf:
            start = n
        if s.endswith("\\"):
            buf += s[:-1] + " "
            continue
        buf += s
        word, _, rest = buf.partition(" ")
        out.append((start, word.upper(), rest.strip()))
        buf = ""
    if buf:
        word, _, rest = buf.partition(" ")
        out.append((start, word.upper(), rest.strip()))
    return out


def check_dockerfile(text):
    """What a zip's Dockerfile may do (DASH-414): build an image from public images and the zip's own files. Returns
    (problems, base images)."""
    problems, bases, stages = [], [], []
    if len(text.encode("utf-8")) > MAX_DOCKERFILE:
        return ["The Dockerfile is bigger than 64 KB"], []
    for line in text.splitlines():  # parser directives come first, before any instruction
        s = line.strip()
        if not s:
            continue
        if re.match(r"^#\s*[A-Za-z]+\s*=", s):
            problems.append(f"The Dockerfile has the directive {s[:40]!r}. Starboard builds with Docker's own builder, "
                            "so leave out # syntax= and the other directives")
            continue
        break
    steps = _instructions(text)
    if not steps or steps[0][1] not in ("FROM", "ARG"):
        problems.append("The Dockerfile must start with FROM")
    for n, word, rest in steps:
        where = f"Dockerfile line {n}"
        if word in REFUSED:
            problems.append(f"{where}: {REFUSED[word]}, is not allowed")
            continue
        if word not in ALLOWED:
            problems.append(f"{where}: {word} is not an instruction Starboard builds with")
            continue
        lead = []
        for token in rest.split():
            if not token.startswith("--"):
                break
            lead.append(token)
        if word == "FROM":
            parts = [t for t in rest.split() if not t.startswith("--platform=")]
            if any(t.startswith("--") and not t.startswith("--platform=") for t in rest.split()):
                problems.append(f"{where}: FROM takes only --platform")
            if not parts:
                problems.append(f"{where}: FROM needs an image")
                continue
            image = parts[0]
            if len(parts) == 3 and parts[1].upper() == "AS" and re.match(r"^[a-z][a-z0-9_.-]{0,30}$", parts[2]):
                stages.append(parts[2])
            elif len(parts) != 1:
                problems.append(f"{where}: FROM is an image, then AS and a short name if you need one")
            if "$" in image:
                problems.append(f"{where}: FROM names its image in full, not with a variable, so the image used is clear")
            elif image.lower() in [s.lower() for s in stages[:-1 if len(parts) == 3 else None]] or image == "scratch":
                pass
            elif not re.match(IMAGE_NAME, image):
                problems.append(f"{where}: {image[:60]!r} is not an image name")
            elif image.startswith("local/"):
                problems.append(f"{where}: FROM may not use an image built on this computer ({image[:60]})")
            else:
                bases.append(image)
            if len(stages) + len(bases) > MAX_STAGES:
                problems.append(f"{where}: at most {MAX_STAGES} FROM lines")
        elif word == "RUN":
            if lead:
                problems.append(f"{where}: RUN {lead[0].split('=')[0]} is not allowed; Starboard's builds have no mounts, "
                                "host network or extra rights")
        elif word in ("COPY", "ADD"):
            for token in lead:
                name, _, value = token.partition("=")
                if name in ("--chown", "--chmod"):
                    continue
                if name == "--from" and word == "COPY" and (value in stages or value.isdigit()):
                    continue
                if name == "--from":
                    problems.append(f"{where}: COPY --from may name only an earlier stage of this Dockerfile, not {value[:40]!r}")
                else:
                    problems.append(f"{where}: {word} {name} is not allowed")
            if word == "ADD":
                sources = [t for t in rest.split() if not t.startswith("--")][:-1]
                if any("://" in t or t.startswith("git@") for t in sources):
                    problems.append(f"{where}: ADD may copy only files from the zip, not from the internet or git")
    return problems, bases


def build_words(manifest):
    """The line in What it may do for a plug-in that builds its own image (API 1.15)."""
    return (f"Starboard builds its image, {plugins.built_image(manifest)}, from the Dockerfile in the zip. The build can "
            f"fetch what the Dockerfile names from the internet, with up to {BUILD_MEMORY_MB // 1024} GB of memory and "
            f"{BUILD_CPUS} processor cores for up to {BUILD_MINUTES} minutes, and reads only the zip's own files: never "
            "your folders, other apps or Docker")


def logo_of(path, manifest):
    """(bytes, content type) for the logo beside the manifest in the zip, cleaned as one from an address; None."""
    from . import plugin_logo
    logo = manifest.get("logo")
    if not isinstance(logo, dict) or plugin_logo.check_entry(logo):
        return None
    try:
        with zipfile.ZipFile(path) as z:
            info = z.getinfo(logo["file"])
            if info.file_size > plugin_logo.PNG_MAX:
                return None
            with z.open(info) as f:
                return plugin_logo.clean(f.read(plugin_logo.PNG_MAX + 1), logo["file"])
    except (KeyError, OSError, ValueError, zipfile.BadZipFile):
        return None


# Building ------------------------------------------------------------------------------------------------------------

def _context(path, out):
    """Writes the build context: a tar of the zip's checked files only, owned by root with plain modes, so nothing in
    the zip (a link, a device, an owner) reaches Docker. Returns its size."""
    with zipfile.ZipFile(path) as z, tarfile.open(fileobj=out, mode="w") as tar:
        for info in z.infolist():
            if info.is_dir() or _name_problem(info.filename):
                continue
            kind = stat.S_IFMT(info.external_attr >> 16)
            if kind not in (0, stat.S_IFREG):
                continue
            t = tarfile.TarInfo(info.filename)
            t.size = info.file_size
            t.mode = 0o755 if (info.external_attr >> 16) & 0o111 else 0o644
            t.uid = t.gid = 0
            t.mtime = 0
            with z.open(info) as f:
                tar.addfile(t, f)
    return out.tell()


def build(data_dir, pid, manifest, path, say=None, deadline_seconds=None):
    """Builds local/<id>:<version> from the zip's Dockerfile with Docker's own builder and the limits above. Returns
    the last lines of the build. Raises BuildFailed."""
    from . import containers
    say = say or (lambda line: None)
    tag = plugins.built_image(manifest)
    tmp = os.path.join(uploads(data_dir), f"context-{secrets.token_hex(8)}.tar")
    os.makedirs(uploads(data_dir), mode=0o700, exist_ok=True)
    lines, error = [], ""
    limit = BUILD_MINUTES * 60 if deadline_seconds is None else deadline_seconds
    try:
        with open(os.open(tmp, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600), "w+b") as ctx:
            size = _context(path, ctx)
            ctx.seek(0)
            query = urllib.parse.urlencode({
                "t": tag, "dockerfile": DOCKERFILE, "version": "1",  # Docker's own builder, which honours the limits below
                "memory": BUILD_MEMORY_MB * 1024 * 1024, "memswap": BUILD_MEMORY_MB * 1024 * 1024,
                "cpuperiod": 100000, "cpuquota": BUILD_CPUS * 100000, "rm": "1", "forcerm": "1", "networkmode": "default",
                "labels": json.dumps({"starboard.plugin": pid, "starboard.built-from": "zip",
                                      "org.opencontainers.image.version": str(manifest.get("version"))})})
            # One wait as long as the whole build may take: a quiet step (a long compile) is not cut short, and a
            # build past its time ends when the wait does.
            conn = containers._UnixConnection(max(5, limit))
            started = time.monotonic()
            try:
                conn.request("POST", f"/build?{query}", body=ctx, headers={"Content-Type": "application/x-tar", "Content-Length": str(size)})
                r = conn.getresponse()
                if r.status >= 400:
                    raise BuildFailed(f"Docker would not build it: {r.read(300).decode('utf-8', 'replace')}")
                while True:
                    if time.monotonic() - started > limit:
                        raise BuildFailed(f"The build took longer than {max(1, limit // 60)} minutes, so Starboard stopped it")
                    raw = r.readline(1 << 16)
                    if not raw:
                        break
                    try:
                        msg = json.loads(raw)
                    except ValueError:
                        continue
                    if msg.get("error"):
                        error = str(msg["error"]).strip()
                    text = str(msg.get("stream") or msg.get("status") or "").rstrip()
                    for ln in text.splitlines():
                        if ln.strip():
                            lines.append(ln[:300])
                            say(ln[:300])
                    del lines[:-60]
            except TimeoutError:
                raise BuildFailed(f"The build took longer than {max(1, limit // 60)} minutes, so Starboard stopped it") from None
            except OSError as e:
                raise BuildFailed(f"The build stopped: {e}") from None
            finally:
                conn.close()  # leaving early ends the build on Docker's side too
    finally:
        _drop(tmp)
    if error:
        raise BuildFailed(f"The build failed: {error[:300]}")
    try:
        info = containers.docker("GET", f"/images/{urllib.parse.quote(tag, safe='')}/json")
    except containers.DockerError:
        raise BuildFailed("The build finished without an image") from None
    if int(info.get("Size") or 0) > MAX_IMAGE:
        try:
            containers.docker("DELETE", f"/images/{urllib.parse.quote(tag, safe='')}")  # Starboard's own build, just made
        except containers.DockerError:
            pass
        raise BuildFailed(f"The image is {int(info['Size']) / 1024 ** 3:.1f} GB; a plug-in's image may be up to 3 GB")
    logs.event("info", "plug-ins", f"Built {tag} from the zip")
    return lines


def image_present(tag):
    from . import containers
    try:
        containers.docker("GET", f"/images/{urllib.parse.quote(tag, safe='')}/json")
        return True
    except containers.DockerError:
        return False


def keep(data_dir, pid, version, path):
    """Keeps the zip beside the plug-in (zips/<version>.zip), so a missing image is built again; zips of versions that
    are neither the current nor the kept one go to data/plugins/.removed, never deleted."""
    from . import plugins_admin as pa
    where = os.path.join(pa.folder(data_dir, pid), KEPT_ZIPS)
    os.makedirs(where, mode=0o700, exist_ok=True)
    os.replace(path, os.path.join(where, f"{version}.zip"))
    tidy_kept(data_dir, pid)


def tidy_kept(data_dir, pid):
    from . import plugins_admin as pa
    base = pa.folder(data_dir, pid)
    where = os.path.join(base, KEPT_ZIPS)
    wanted = {str((pa._read(os.path.join(base, f), {}) or {}).get("version")) for f in ("manifest.json", "previous/manifest.json")}
    try:
        names = os.listdir(where)
    except OSError:
        return
    for name in names:
        if name.endswith(".zip") and name[:-4] not in wanted:
            aside = os.path.join(pa.root(data_dir), ".removed", f"{pid}-zips")
            os.makedirs(aside, mode=0o700, exist_ok=True)
            shutil.move(os.path.join(where, name), os.path.join(aside, f"{dt.datetime.now():%Y%m%d-%H%M%S}-{name}"))


def ensure_images(data_dir, pid, say=None):
    """Before Activate: a plug-in built from a zip whose image has gone (a prune, a new disk) is built again from its
    kept zip. Raises ValueError when it cannot be."""
    from . import containers
    from . import plugins_admin as pa
    m = pa._read(os.path.join(pa.folder(data_dir, pid), "manifest.json"), {}) or {}
    if not plugins.builds(m) or not containers.available() or image_present(plugins.built_image(m)):
        return False
    kept = os.path.join(pa.folder(data_dir, pid), KEPT_ZIPS, f"{m.get('version')}.zip")
    if not os.path.isfile(kept):
        raise ValueError(f"Its image {plugins.built_image(m)} is not on this computer and its zip is not kept. "
                         "Upload the zip again with Update from a zip file")
    read(kept)  # checked again before it is built
    build(data_dir, pid, m, kept, say)
    return True


# Installing and updating ---------------------------------------------------------------------------------------------

_jobs = {}
_lock = threading.Lock()


def job(job_id):
    """The install as the pages' task dialog reads it: tasks with states, finished, ok, now, log, title and text."""
    with _lock:
        j = _jobs.get(job_id)
        j = json.loads(json.dumps(j)) if j else None
    if not j:
        return None
    order = (["building"] if j["built"] else []) + ["installing"]
    at = j["state"]
    tasks = [{"id": "check", "label": "Checking the zip", "state": "done"}]
    for k in order:
        label = "Building its container from the zip" if k == "building" else f"Installing {j['name']}"
        if at == "installed":
            state = "done"
        elif at == "failed":
            state = "failed" if k == j.get("failed_at") else "done" if order.index(k) < order.index(j.get("failed_at") or k) else "skipped"
        else:
            state = "working" if k == at else "done" if order.index(k) < order.index(at) else "waiting"
        tasks.append({"id": k, "label": label, "state": state})
    finished = at in ("installed", "failed")
    return {"id": j["id"], "plugin": j["plugin"], "name": j["name"], "version": j["version"], "state": at, "tasks": tasks,
            "finished": finished, "ok": at == "installed" if finished else None, "now": (j["lines"] or [""])[-1] if not finished else "",
            "log": "\n".join(j["lines"]), "error": j["said"] if at == "failed" else "", "said": j["said"],
            "title": f"{j['name']} installed" if at == "installed" else f"{j['name']} was not installed" if at == "failed" else "",
            "text": j["said"]}


def _set(j, **values):
    with _lock:
        j.update(values)


def start_install(data_dir, token, media_dir, after=None):
    """Installs from an upload in the background: build, then install (not started). Returns the job to follow at
    GET /api/plugins/zip/jobs/<id>: {state: building, installing, installed or failed, lines, said, plugin}."""
    from . import plugins_admin as pa
    manifest, report, path = manifest_of(data_dir, token)
    problems = report["problems"] + plugin_tester_errors(manifest)
    if problems:
        raise ValueError("This plug-in has errors: " + "; ".join(problems[:4]))
    if os.path.exists(os.path.join(pa.folder(data_dir, manifest["id"]), "manifest.json")):
        raise ValueError(f"{manifest['name']} is already added. Update it from its page instead")
    with _lock:
        if any(j["state"] in ("building", "installing") for j in _jobs.values()):
            raise ValueError("Another zip is being installed. Wait for it to finish")
        j = {"id": secrets.token_hex(6), "plugin": manifest["id"], "name": manifest["name"], "version": manifest["version"],
             "state": "building" if plugins.builds(manifest) else "installing", "built": bool(plugins.builds(manifest)),
             "lines": [], "said": "", "started": time.time()}
        _jobs[j["id"]] = j

    def say(line):
        with _lock:
            j["lines"] = (j["lines"] + [line])[-40:]

    def work():
        try:
            if plugins.builds(manifest):
                build(data_dir, manifest["id"], manifest, path, say)
            _set(j, state="installing")
            item = pa.install(data_dir, manifest, media_dir)
            pa.keep_logo(data_dir, item["id"], logo_of(path, manifest))
            keep(data_dir, item["id"], manifest["version"], path)
            not_on = after(item) if after else ""
            logs.event("info", "plug-ins", f"Added {manifest['name']} {manifest['version']} from a zip file")
            # Activated once installed (owner, 19 November 2026), unless it needs setting up first.
            _set(j, state="installed", said=f"{manifest['name']} installed and active." if after and not not_on
                 else f"{manifest['name']} installed. {not_on or 'Activate it when you are ready'}.".replace("..", "."))
        except Exception as e:  # noqa: BLE001  any failure ends the job with words
            logs.event("error", "plug-ins", f"{manifest.get('name')} from a zip file was not installed: {e}")
            _set(j, failed_at=j["state"], state="failed", said=f"{manifest['name']} was not installed. {str(e)[:300]}")
    threading.Thread(target=work, name="plugin-zip", daemon=True).start()
    return job(j["id"])


def plugin_tester_errors(manifest):
    from . import plugin_tester
    r = plugin_tester.report(manifest)
    return [] if r["ok"] else ["Test it to list its errors"] if not r.get("issues") else [
        i.get("what", "") for i in r["issues"] if i.get("severity") == "error"][:4] or ["Test it to list its errors"]


def preview(data_dir, token):
    """What the page shows before Install or Update from a zip: the summary, the warning with the build, the test."""
    from . import plugin_logo, plugin_tester
    from . import plugins_admin as pa
    manifest, report, path = manifest_of(data_dir, token)
    try:
        out = {**pa.summary(manifest), "test": plugin_tester.report(manifest), "zip": {**report, "token": token}}
    except (KeyError, TypeError, AttributeError, ValueError):  # a manifest too far from the format to describe
        raise ZipProblem(f"{MANIFEST} is not a plug-in manifest Starboard can read. Test it to find out why") from None
    if report["problems"]:
        out["test"] = {**out["test"], "ok": False, "errors": out["test"]["errors"] + len(report["problems"]),
                       "issues": [{"severity": "error", "area": "zip", "where": "zip", "what": p, "fix": "Ask its maker for a zip that keeps to these rules"}
                                  for p in report["problems"]] + list(out["test"].get("issues") or [])}
    if report.get("dockerfile") and out.get("warning"):
        bases = report["dockerfile"]["from"]
        if bases:
            out["warning"]["runs"] = list(out["warning"]["runs"]) + [f"The build starts from {', '.join(bases)}"]
    got = logo_of(path, manifest)
    out["logo"] = {"url": plugin_logo.as_data(*got), "alt": manifest["logo"]["alt"]} if got else None
    return out


def start_update(app, pid, token):
    """Update from a zip file: the same run as an update from a catalogue or an address (plugin_update.update_safely,
    the 0.18.0 code, with its before, settings, install, health and after steps and its way back), with a build step
    first when the plug-in builds its image. Roll back needs nothing more: the image before keeps its own tag."""
    from . import plugin_update, update_runs
    from . import plugins_admin as pa
    p = next((x for x in pa.listing(app.data_dir) if x["id"] == pid), None)
    if not p:
        raise LookupError("No plug-in with that id")
    if p.get("builtin"):
        raise update_runs.Refused("A plug-in built into Starboard updates with Starboard")
    manifest, report, path = manifest_of(app.data_dir, token)
    if manifest.get("id") != pid:
        raise ValueError(f"That zip is for another plug-in ({str(manifest.get('id'))[:40]}), not {p['name']}")
    problems = report["problems"] + plugins.check(manifest)
    if problems:
        raise ValueError("This version cannot be used: " + "; ".join(problems[:6]))
    if update_runs._busy() or update_runs._starboard_running(app):
        raise update_runs.Busy("An update is already running. Wait for it to finish")
    built = bool(plugins.builds(manifest))
    steps = ([("build", "Building its container from the zip")] if built else []) + plugin_update.STEPS
    run = update_runs._new(app.data_dir, f"plugin:{pid}", "plugin", p["name"], "update", p.get("version"), manifest.get("version"),
                           "you", steps, {"from_zip": True})
    media = update_runs._media_dir(app)
    logo = logo_of(path, manifest)

    def work():
        if built:
            update_runs._step(app.data_dir, run, "build", "now", "")
            try:
                tail = build(app.data_dir, pid, manifest, path, lambda line: update_runs._step(app.data_dir, run, "build", "now", line))
            except BuildFailed as e:
                update_runs._step(app.data_dir, run, "build", "failed", str(e))
                update_runs._end(app.data_dir, run, "refused", f"{p['name']} was not updated: {e}. Nothing was changed", app)
                return
            update_runs._step(app.data_dir, run, "build", "done", (tail or [""])[-1])
        r = plugin_update.update_safely(app.data_dir, pid, manifest, media, services=app.config.data["services"], logo=logo,
                                        progress=lambda *a: update_runs._step(app.data_dir, run, *a))
        if r["outcome"] in ("updated", "went-back"):
            keep(app.data_dir, pid, manifest["version"], path)  # the zip of the version tried stays for its image
        update_runs._end(app.data_dir, run, r["outcome"], r["said"], app)
        update_runs._after_plugins(app)
    update_runs._go(app.data_dir, run, work)
    return run
