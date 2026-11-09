"""Container updates: which image each app runs, whether its registry has a newer one, and updating it.

Optional. It works only when the Docker socket is mounted into Starboard (STARBOARD_DOCKER, default
/var/run/docker.sock), which the installer asks about. Access to the socket is full control of Docker.

- apps(services): every app on the Apps page, in the same order, with the container it runs in. The container is
  the one the app names in Settings, or else one whose name or Compose service matches the app's ID or name.
- check(): asks each image's registry whether its tag now points at a newer build, and reads that build's
  version label. Only a few small JSON documents are downloaded. An image pinned to a version (such as v1.4.2)
  is offered the newest higher stable version instead.
- update(ids): pulls each new image, then runs `docker compose up -d` for its Compose project in a short-lived
  docker:cli container, so anything that depends on it is recreated too. For a pinned image, the Compose file is
  copied and its tag changed first. If the project folder has `starboard-before-update/<service>.sh`, that
  runs first (a database backup, for example); if it fails, nothing changes.
"""

import concurrent.futures as cf
import http.client
import json
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# docker:27-cli, pinned to one exact build: it gets the Docker socket, so a changed tag must not change what runs.
HELPER_IMAGE = "docker@sha256:851f91d241214e7c6db86513b270d58776379aacc5eb9c4a87e5b47115e3065c"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
PINNED = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)([-+.].+)?$")  # a version tag, or a test build such as v0.4.9-dev.6
ACCEPT = ", ".join(["application/vnd.oci.image.index.v1+json", "application/vnd.docker.distribution.manifest.list.v2+json",
                    "application/vnd.docker.distribution.manifest.v2+json", "application/vnd.oci.image.manifest.v1+json"])

_lock = threading.Lock()
_state = {"check": {}, "checked_at": None, "job": None}
_tokens = {}


class DockerError(Exception):
    pass


def socket_path():
    return os.environ.get("STARBOARD_DOCKER", "/var/run/docker.sock")


def available():
    path = socket_path()
    return os.path.exists(path) and os.access(path, os.R_OK | os.W_OK)


# Docker Engine API over the unix socket ------------------------------------------

class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, timeout=900):
        super().__init__("localhost", timeout=timeout)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(socket_path())


DOCKER_READ_LIMIT = 64 * 1024 * 1024  # an answer bigger than this is refused, not read into memory


def docker(method, path, body=None, raw=False, timeout=30):
    c = _UnixConnection(timeout)
    try:
        c.request(method, path, body=json.dumps(body) if body is not None else None,
                  headers={"Content-Type": "application/json"} if body is not None else {})
        r = c.getresponse()
        data = r.read(DOCKER_READ_LIMIT + 1)
        if len(data) > DOCKER_READ_LIMIT:
            raise DockerError("Docker's answer was too big to read")
    except OSError as e:
        raise DockerError(f"Cannot reach Docker: {e}") from None
    finally:
        c.close()
    if r.status >= 400:
        raise DockerError(f"Docker answered {r.status}: {data[:200].decode('utf-8', 'replace')}")
    if raw:
        return data
    return json.loads(data) if data else None


def _label_version(labels):
    m = re.search(r"version:-\s*(\S+)", labels.get("build_version", ""))  # linuxserver.io images
    if m:
        return m.group(1)
    for k in ("org.opencontainers.image.version", "version", "org.label-schema.version"):
        if labels.get(k):
            return labels[k]
    return ""


def version_of(labels, env=None):
    v = _label_version(labels or {})
    if v and not re.search(r"python|alpine|debian|ubuntu", v, re.I):  # base-image labels say nothing about the app
        return v
    for e in env or []:
        k, _, val = e.partition("=")
        if k in ("APP_VERSION", "NGINX_VERSION", "PG_VERSION", "VERSION") and val:
            return val
    return ""


def containers(light=False):
    """Every container. light=True: names and IDs only, with no request per image (for Monitor's names)."""
    out = []
    listed = docker("GET", "/containers/json?all=1")
    if light:
        return [{"id": c["Id"], "name": c["Names"][0].lstrip("/")} for c in listed]
    for c in listed:
        labels = c.get("Labels") or {}
        image = c["Image"]
        if image.startswith("sha256:"):
            continue  # no tag to compare with
        ref = image if ":" in image.split("/")[-1] or "@" in image else image + ":latest"
        try:
            info = docker("GET", f"/images/{urllib.parse.quote(c['ImageID'], safe='')}/json")
        except DockerError:
            info = {}
        conf = info.get("Config") or {}

        def own(key):
            # Labels can come from the image itself (Compose stamps the images it builds), so they are only trusted
            # after _compose checks every name, the folder and the files; a made-up label can then at most name a
            # Compose project already on this computer, never run a command.
            return labels.get(key, "")
        tag = parse_ref(ref)[2]
        version = version_of(conf.get("Labels"), conf.get("Env")) or (tag if tag != "latest" else "")
        out.append({
            "id": c["Id"], "name": c["Names"][0].lstrip("/"), "image": ref, "image_id": c["ImageID"],
            "state": c.get("State", ""), "status": c.get("Status", ""),
            "version": version, "created": (info.get("Created") or "")[:10],
            "digests": info.get("RepoDigests") or [],
            **_compose(own("com.docker.compose.service"), own("com.docker.compose.project"),
                       own("com.docker.compose.project.working_dir"), own("com.docker.compose.project.config_files")),
        })
    return out


def _compose(service, project, folder, files):
    """The Compose details Starboard may use, or blanks: every name strictly checked, the folder a real project
    folder (never /), and every Compose file inside it."""
    import posixpath
    blank = {"service": "", "project": "", "folder": "", "files": []}
    if not (NAME_RE.match(service or "") and NAME_RE.match(project or "")):
        return blank
    folder = folder or ""
    if not folder.startswith("/") or posixpath.normpath(folder) != folder or folder.count("/") < 2:
        return blank
    names = [f for f in (files or "").split(",") if f]
    for f in names:
        if posixpath.normpath(f) != f or not f.startswith(folder + "/") or not f.endswith((".yml", ".yaml")) or "'" in f:
            return blank
    return {"service": service, "project": project, "folder": folder, "files": names}


def _simple(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def match(service, found):
    """The container an app runs in: the one named in its settings, or one whose name matches."""
    by_name = {c["name"]: c for c in found}
    if service.get("container"):
        return by_name.get(service["container"])
    wanted = {_simple(service["id"]), _simple(service["name"])}
    for c in found:
        if _simple(c["name"]) in wanted or (c["service"] and _simple(c["service"]) in wanted):
            return c
    return None


# Registries (OCI distribution API, anonymous pull tokens) ---------------------------

def parse_ref(ref):
    name, tag = ref.rsplit(":", 1) if ":" in ref.split("/")[-1] else (ref, "latest")
    parts = name.split("/")
    if len(parts) > 1 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        return parts[0], "/".join(parts[1:]), tag
    return "registry-1.docker.io", name if "/" in name else f"library/{name}", tag


def _registry(reg, repo, path, accept=ACCEPT):
    url = f"https://{reg}/v2/{repo}/{path}"
    for attempt in range(2):
        headers = {"Accept": accept, "User-Agent": "Starboard"}
        if _tokens.get((reg, repo)):
            headers["Authorization"] = f"Bearer {_tokens[(reg, repo)]}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:  # a registry address Starboard builds, always https  # nosec B310
                return r.headers, r.read(4_000_000)
        except urllib.error.HTTPError as e:
            if e.code != 401 or attempt:
                raise
            params = dict(re.findall(r'(\w+)="([^"]*)"', e.headers.get("WWW-Authenticate", "")))
            if not params.get("realm", "").startswith("https://"):
                raise
            q = urllib.parse.urlencode({"service": params.get("service", ""), "scope": params.get("scope", f"repository:{repo}:pull")})
            with urllib.request.urlopen(f"{params['realm']}?{q}", timeout=20) as t:  # the realm is checked to start with https:// above  # nosec B310
                j = json.load(t)
            _tokens[(reg, repo)] = j.get("token") or j.get("access_token")
    raise DockerError("The registry did not accept the sign-in")


def remote(ref):
    reg, repo, tag = parse_ref(ref)
    headers, body = _registry(reg, repo, f"manifests/{tag}")
    digest = headers.get("Docker-Content-Digest", "")
    manifest = json.loads(body)
    if "manifests" in manifest:  # one image per platform: read the linux/amd64 one
        pick = next((m for m in manifest["manifests"] if (m.get("platform") or {}).get("architecture") == "amd64"
                     and (m.get("platform") or {}).get("os") == "linux"), manifest["manifests"][0])
        _, body = _registry(reg, repo, f"manifests/{pick['digest']}", accept=pick.get("mediaType", ACCEPT))
        manifest = json.loads(body)
    version = ""
    config_digest = (manifest.get("config") or {}).get("digest")
    if config_digest:
        try:
            _, blob = _registry(reg, repo, f"blobs/{config_digest}", accept="*/*")
            conf = json.loads(blob).get("config") or {}
            version = version_of(conf.get("Labels"), conf.get("Env"))
        except (urllib.error.URLError, ValueError, DockerError):
            pass
    return {"digest": digest, "version": version}


def newer_pinned(ref):
    """For an image pinned to a version tag, the newest higher stable tag in its registry, or None. A test build
    (v0.4.9-dev.6) counts as older than its release, so v0.4.9 itself is offered too."""
    reg, repo, tag = parse_ref(ref)
    now = PINNED.match(tag)
    if not now:
        return None
    current, test_build = tuple(int(x) for x in now.groups()[:3]), bool(now.group(4))
    _, body = _registry(reg, repo, "tags/list?n=1000", accept="application/json")
    best = None
    for name in json.loads(body).get("tags") or []:
        m = SEMVER.match(name)
        if m and name.startswith("v") == tag.startswith("v"):
            key = tuple(int(x) for x in m.groups())
            if (key > current or (test_build and key == current)) and (not best or key > best[0]):
                best = (key, name)
    return best[1] if best else None


def _major(v):
    m = re.match(r"v?(\d+)", v or "")
    return m.group(1) if m else None


def _check_one(c):
    try:
        r = remote(c["image"])
        local = {d.split("@", 1)[1] for d in c["digests"] if "@" in d}
        out = {"latest": r["version"], "update": bool(r["digest"] and local and r["digest"] not in local),
               "unknown": not local, "big_change": bool(_major(c["version"]) and _major(r["version"])
                                                        and _major(c["version"]) != _major(r["version"]))}
        target = newer_pinned(c["image"])
        if target:
            out.update(latest=target, target_tag=target, update=True, unknown=False, pinned=True,
                       big_change=_major(c["version"] or parse_ref(c["image"])[2]) != _major(target))
        return out
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # A local or test build (v0.4.9-dev.6) is not in the registry, but a newer release may be.
            try:
                target = newer_pinned(c["image"])
            except (urllib.error.URLError, OSError, ValueError, KeyError, DockerError):
                target = None
            if target:
                return {"latest": target, "target_tag": target, "update": True, "unknown": False, "pinned": True,
                        "big_change": _major(c["version"] or parse_ref(c["image"])[2]) != _major(target)}
        message = ("This tag is not in its registry, so it may be a local or test build" if e.code == 404
                   else f"The registry answered with error {e.code}")
        return {"latest": "", "update": False, "unknown": True, "error": message}
    except (urllib.error.URLError, OSError, ValueError, KeyError, DockerError):
        return {"latest": "", "update": False, "unknown": True, "error": "Cannot reach the image's registry"}


# The page --------------------------------------------------------------------------

def apps(services):
    """Every app on the Apps page with its container and what the last check found, in the Apps order."""
    found = containers()
    with _lock:
        checked = dict(_state["check"])
        job = json.loads(json.dumps(_state["job"])) if _state["job"] else None
    rows = []
    for s in services:
        if not s.get("enabled", True):
            continue
        c = match(s, found)
        row = {"id": s["id"], "name": s["name"], "group": s.get("group", ""), "background": bool(s.get("background")),
               "container": None}
        if c:
            row["container"] = {k: c[k] for k in ("name", "image", "state", "status", "version", "created", "service", "project")}
            row["container"]["compose"] = bool(c["folder"] and c["files"])
            row.update(checked.get(c["name"], {}))
        rows.append(row)
    return {"available": True, "items": rows, "checked_at": _state["checked_at"], "job": job,
            "containers": sorted(c["name"] for c in found)}


def check(services):
    found = {c["name"]: c for c in containers()}
    wanted = [match(s, found.values()) for s in services if s.get("enabled", True)]
    targets = {c["name"]: c for c in wanted if c}
    with cf.ThreadPoolExecutor(8) as pool:
        results = dict(zip(targets, pool.map(_check_one, targets.values())))
    with _lock:
        _state.update(check=results, checked_at=time.time())
    return apps(services)


def _pull(ref, item):
    """Pulls through the Docker API, adding up each layer's bytes so the page can show a real percentage."""
    _, _, tag = parse_ref(ref)
    image = ref.rsplit(":", 1)[0] if ":" in ref.split("/")[-1] else ref
    c = _UnixConnection()
    try:
        c.request("POST", f"/images/create?fromImage={urllib.parse.quote(image)}&tag={urllib.parse.quote(tag)}")
        r = c.getresponse()
        if r.status >= 400:
            raise DockerError(f"Docker answered {r.status} to the download")
        layers, buf = {}, b""
        while chunk := r.read1(65536):
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("error"):
                    raise DockerError(ev["error"])
                lid, st, pd = ev.get("id"), ev.get("status", ""), ev.get("progressDetail") or {}
                if not lid or len(lid) != 12:
                    continue
                cur = layers.setdefault(lid, [0, 0, 0])  # downloaded, total, unpacked
                if st == "Downloading" and pd.get("total"):
                    cur[0], cur[1] = pd.get("current", 0), pd["total"]
                elif st in ("Download complete", "Verifying Checksum") and cur[1]:
                    cur[0] = cur[1]
                elif st == "Extracting" and pd.get("total"):
                    cur[1] = cur[1] or pd["total"]
                    cur[0], cur[2] = cur[1], pd.get("current", 0) / pd["total"]
                elif st in ("Pull complete", "Already exists"):
                    cur[2] = 1
                    cur[0] = cur[1] or cur[0]
                total = sum(x[1] for x in layers.values())
                got = sum(x[0] for x in layers.values())
                done = sum(x[2] for x in layers.values()) / max(1, len(layers))
                pct = (85 * got / total + 15 * done) if total else 100 * done  # 85% download, 15% unpack
                with _lock:
                    item.update(pct=round(min(99, pct), 1))
    finally:
        c.close()


def _quote(text):
    return "'" + text.replace("'", "'\\''") + "'"


def _helper(folder, script, extra_binds=()):
    """Runs a shell script in a short-lived docker:cli container that can see the project folder (and, for
    Install apps, the settings and media folders it makes)."""
    body = {"Image": HELPER_IMAGE, "Cmd": ["sh", "-c", script], "WorkingDir": folder, "Labels": {"starboard.updater": "1"},
            "HostConfig": {"Binds": ["/var/run/docker.sock:/var/run/docker.sock", f"{folder}:{folder}", *extra_binds]}}
    cid = docker("POST", f"/containers/create?name=starboard-updater-{int(time.time() * 1000)}", body)["Id"]
    try:
        docker("POST", f"/containers/{cid}/start")
        code = docker("POST", f"/containers/{cid}/wait", timeout=1800).get("StatusCode", 1)
        raw = docker("GET", f"/containers/{cid}/logs?stdout=1&stderr=1&tail=80", raw=True)
    finally:
        try:
            docker("DELETE", f"/containers/{cid}?force=1")
        except DockerError:
            pass
    text, i = b"", 0
    while i + 8 <= len(raw):  # Docker's log stream: an 8-byte header before each chunk
        n = int.from_bytes(raw[i + 4:i + 8], "big")
        text += raw[i + 8:i + 8 + n]
        i += 8 + n
    return code, text.decode("utf-8", "replace")


def job():
    """The last update job, or None."""
    with _lock:
        return json.loads(json.dumps(_state["job"])) if _state["job"] else None


def forget_old(image_id):
    """Removes an image kept by keep_old, once nothing uses it (after an automatic update proved healthy)."""
    if image_id in {c["image_id"] for c in containers()}:
        return
    try:
        docker("DELETE", f"/images/{image_id}")
    except DockerError:
        pass


def _run(names, keep_old=False):
    job = _state["job"]
    try:
        found = {c["name"]: c for c in containers()}
        with _lock:
            targets = {n: r["target_tag"] for n, r in _state["check"].items() if r.get("target_tag")}
        old_images = {found[n]["image_id"] for n in names if n in found}
        for name in names:
            item = job["items"][name]
            with _lock:
                item.update(phase="downloading", pct=0)
            try:
                ref = found[name]["image"]
                if name in targets:
                    ref = ref.rsplit(":", 1)[0] + ":" + targets[name]
                _pull(ref, item)
                with _lock:
                    item.update(phase="downloaded", pct=100)
            except (DockerError, OSError, KeyError) as e:
                with _lock:
                    item.update(phase="failed", error=str(e)[:200])
        ready = [n for n in names if job["items"][n]["phase"] == "downloaded"]
        projects = {}
        for n in ready:
            projects.setdefault((found[n]["project"], found[n]["folder"]), []).append(n)
        log = []
        for (project, folder), group in projects.items():
            with _lock:
                for n in group:
                    job["items"][n].update(phase="installing")
            files = found[group[0]]["files"]
            steps = ["set -e"]
            stamp = time.strftime("%Y-%m-%d-%H%M")
            for n in group:
                svc = found[n]["service"]
                hook = _quote(f"starboard-before-update/{svc}.sh")
                steps.append(f"if [ -f {hook} ]; then sh {hook}; fi")
                if n in targets:
                    old = found[n]["image"]
                    new = old.rsplit(":", 1)[0] + ":" + targets[n]
                    for f in files:
                        steps.append(f"if grep -q {_quote('image: ' + old)} {_quote(f)}; then "
                                     f"cp {_quote(f)} {_quote(f + '.bak-' + svc + '-' + targets[n] + '-' + stamp)} && "
                                     f"sed -i {_quote('s#image: ' + re.escape(old) + '#image: ' + new + '#')} {_quote(f)}; fi")
            steps.append(f"docker compose -p {_quote(project)} " + " ".join(f"-f {_quote(f)}" for f in files) + " up -d 2>&1")
            try:
                code, text = _helper(folder, " && ".join(steps)) if folder and files else (1, "Not started by Docker Compose")
            except DockerError as e:
                code, text = 1, str(e)
            log.append(text)
            now = {c["name"]: c for c in containers()}
            with _lock:
                for n in group:
                    ok = code == 0 and now.get(n, {}).get("state") == "running"
                    job["items"][n].update(phase="done" if ok else "failed", version=now.get(n, {}).get("version", ""),
                                           **({} if ok else {"error": "The restart did not finish. The log below says why."}))
        with _lock:
            job["log"] = "\n".join(log)[-4000:]
            done = [n for n, i in job["items"].items() if i.get("phase") == "done"]
            failed = [n for n, i in job["items"].items() if i.get("phase") == "failed"]
        from . import logs
        if done:
            logs.event("info", "updates", f"Updated {', '.join(done)}")
        if failed:
            logs.event("error", "updates", f"Update did not finish for {', '.join(failed)}", log="\n".join(log)[-2000:])
        # Remove only the images these apps used before, if nothing uses them now. An automatic update keeps them
        # until the new version proves healthy (reelix_updates.py).
        in_use = {c["image_id"] for c in containers()}
        for image_id in (set() if keep_old else old_images - in_use):
            try:
                docker("DELETE", f"/images/{image_id}")
            except DockerError:
                pass
    except DockerError as e:
        with _lock:
            job["log"] = str(e)
        from . import logs
        logs.event("error", "updates", f"Updates stopped: {e}")
    finally:
        with _lock:
            job.update(finished=True, ended=time.time())
            _state["check"] = {}


def update(services, ids, keep_old=False):
    found = containers()
    by_id = {s["id"]: s for s in services}
    names = []
    for i in ids:
        c = match(by_id[i], found) if i in by_id else None
        if c and c["name"] not in names:
            names.append(c["name"])
    if not names:
        raise ValueError("Choose an app that runs in a container")
    with _lock:
        if _state["job"] and not _state["job"].get("finished"):
            raise ValueError("An update is already running. Wait for it to finish")
        _state["job"] = {"started": time.time(), "finished": False, "log": "",
                         "items": {n: {"phase": "queued", "pct": 0} for n in names}}
    try:
        docker("POST", f"/images/create?fromImage={urllib.parse.quote(HELPER_IMAGE, safe='')}", raw=True, timeout=300)
    except DockerError:
        pass  # the helper may already be here
    threading.Thread(target=_run, args=(names, keep_old), name="updates", daemon=True).start()
    return apps(services)
