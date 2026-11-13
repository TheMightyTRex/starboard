"""The folder picker's server side (DASH-240, decided 10 November 2026): browse and check folders on this computer.

Browse lists one folder's sub-folders with the disk they are on and its free space; Check says, in plain words,
whether a typed folder exists or will be made, which disk it is on, how much is free, and whether it is somewhere
Starboard never uses (a system folder, the whole disk, a home folder itself). Typing stays allowed: a trailing slash
and spaces at the ends are tidied, not refused.

Only the usual places are browsed (ROOTS, and whatever lies under them), never /etc or the whole disk. Starboard
outside Docker reads the folders itself. Inside Docker it cannot see the computer's folders, so it asks its short-
lived helper image with the usual place mounted read only (never making a folder); without Docker access, Browse says so and
typing still works.
"""
import os
import re
import shlex

ROOTS = ("/mnt", "/media", "/srv", "/home", "/data", "/opt")
MAX_FOLDERS = 300
NAME = re.compile(r"^[^\x00/\n]{1,255}$")


def tidy(path):
    """A typed folder made tidy: spaces at the ends and trailing slashes go; ~ means the person's home folder."""
    path = str(path or "").strip().strip('"').strip("'").strip()
    home = os.environ.get("STARBOARD_HOST_HOME") or ""
    if path == "~" or path.startswith("~/"):
        if not home:
            raise ValueError("Write the whole folder, starting with /, such as /home/sam/media")
        path = home + path[1:]
    while len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    if not path.startswith("/"):
        raise ValueError("Write the whole folder, starting with /, such as /mnt/media")
    if "\x00" in path or "/../" in path + "/" or "//" in path:
        raise ValueError("That is not a folder Starboard can use")
    return path


def allowed(path):
    """Inside one of the usual places (and not a root itself, such as /home)."""
    return any(path == r or path.startswith(r + "/") for r in ROOTS)


def inside(path):
    """The folder as the disk really has it (links followed, no ..), or ValueError when that lies outside the usual
    places: a link under /mnt that points at /etc is not browsed. Checked again here, where the folder is read."""
    real = os.path.realpath(path)
    roots = tuple(os.path.realpath(r) for r in ROOTS)
    if not real.startswith(roots):
        raise ValueError("Starboard only looks in " + ", ".join(ROOTS))
    if not any(real == r or real.startswith(r + os.sep) for r in roots):  # /mntx is not inside /mnt
        raise ValueError("Starboard only looks in " + ", ".join(ROOTS))
    return real


def _in_docker():
    return os.path.exists("/.dockerenv")


def _local(path):
    try:
        names = sorted(n for n in os.listdir(path) if os.path.isdir(os.path.join(path, n)) and not n.startswith("."))
    except FileNotFoundError:
        return {"exists": False, "folders": []}
    except PermissionError:
        return {"exists": True, "readable": False, "folders": []}
    st = os.statvfs(path)
    return {"exists": True, "readable": True, "folders": names[:MAX_FOLDERS], "free": st.f_bavail * st.f_frsize,
            "total": st.f_blocks * st.f_frsize}


def _root_of(path):
    return next(r for r in ROOTS if path == r or path.startswith(r + "/"))


def _parse(text):
    out = {"exists": True, "readable": True, "folders": []}
    for line in text.splitlines():
        parts = line.split("\t")
        if parts[0] == "NOFOLDER":
            out["exists"] = False
        elif parts[0] == "NEAREST" and len(parts) == 2:
            out["made_in"] = parts[1]
        elif parts[0] == "D" and len(parts) == 2 and NAME.match(parts[1]) and not parts[1].startswith("."):
            out["folders"].append(parts[1])
        elif parts[0] == "F" and len(parts) == 3 and parts[1].isdigit():
            out["free"], out["total"] = int(parts[1]) * 1024, int(parts[2]) * 1024
    return out


def _script(rel):
    """Run in the helper with the place mounted read only at /r: the folder's sub-folders and free space, or, when it
    is missing, the nearest folder above it that exists and its free space."""
    q = shlex.quote("/r" + rel)
    return (f"p={q}; if [ -d \"$p\" ]; then cd \"$p\" || exit 0; "
            f"for d in */; do [ -d \"$d\" ] && printf 'D\\t%s\\n' \"${{d%/}}\"; done 2>/dev/null | head -n {MAX_FOLDERS}; "
            "else echo NOFOLDER; while [ ! -d \"$p\" ] && [ \"$p\" != /r ]; do p=\"${p%/*}\"; done; "
            "printf 'NEAREST\\t%s\\n' \"${p#/r}\"; fi; "
            "df -Pk \"$p\" | awk 'NR==2 {print \"F\\t\" $4 \"\\t\" $2}'")


def _via_helper(path, run=None):
    """The folder as the computer sees it: the helper image with the place (/mnt, /srv...) mounted read only. A mount
    of type bind never makes a missing folder, unlike a volume line."""
    from . import containers
    root = _root_of(path)
    rel = path[len(root):]
    script = _script(rel)
    if run is not None:  # tests, with a stand-in for the helper
        return _whole(_parse(run(root, script)), root)
    body = {"Image": containers.HELPER_IMAGE, "Cmd": ["sh", "-c", script], "Labels": {"starboard.updater": "1"},
            "HostConfig": {"Mounts": [{"Type": "bind", "Source": root, "Target": "/r", "ReadOnly": True}],
                           "NetworkMode": "none"}}
    try:
        cid = containers.docker("POST", f"/containers/create?name=starboard-updater-look-{os.getpid()}-{abs(hash(path)) % 10 ** 8}", body)["Id"]
    except containers.DockerError:
        return {"exists": None, "folders": [], "why": f"Starboard cannot look in {root} on this computer."}
    try:
        containers.docker("POST", f"/containers/{cid}/start")
        containers.docker("POST", f"/containers/{cid}/wait", timeout=30)
        raw = containers.docker("GET", f"/containers/{cid}/logs?stdout=1", raw=True)
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
    return _whole(_parse(text.decode("utf-8", "replace")), root)


def _whole(out, root):
    """The helper names folders inside the place it was shown: put the place back in front."""
    if out.get("made_in") is not None:
        out["made_in"] = root + out["made_in"]
    return out


def _read(path, run=None):
    if run is None and not _in_docker():
        path = inside(path)
        got = _local(path)
        if not got["exists"]:
            near = path
            while near not in ("/", "") and not os.path.isdir(near):
                near = os.path.dirname(near)
            if near and os.path.isdir(near):
                st = os.statvfs(near)
                got.update(made_in=near, free=st.f_bavail * st.f_frsize, total=st.f_blocks * st.f_frsize)
        return got
    from . import containers
    if run is None and not containers.available():
        return {"exists": None, "folders": [], "why": "Starboard cannot look at this computer's folders without Docker access. Type the folder instead."}
    return _via_helper(path, run)


def browse(path, run=None):
    """{path, parent, crumbs, folders: [{name, path}], free, total} for one folder; the roots when path is empty."""
    if not path:
        return {"path": "", "parent": None, "crumbs": [], "folders": [{"name": "/" + os.path.basename(r), "path": r} for r in ROOTS],
                "free": None, "total": None}
    path = tidy(path)
    if not allowed(path):
        raise ValueError("Starboard only looks in " + ", ".join(ROOTS))
    got = _read(path, run)
    if got.get("exists") is False:
        raise LookupError("There is no folder there")
    root = _root_of(path)  # "Where you are" starts at the place, such as /mnt, not the top of the computer
    crumbs = [{"name": "/" + os.path.basename(root), "path": root}]
    below = path[len(root):].strip("/")
    for i, part in enumerate(below.split("/") if below else []):
        crumbs.append({"name": part, "path": root + "/" + "/".join(below.split("/")[:i + 1])})
    return {"path": path, "parent": os.path.dirname(path) if path not in ROOTS else "",
            "crumbs": crumbs, "folders": [{"name": n, "path": f"{path}/{n}"} for n in got.get("folders", [])],
            "free": got.get("free"), "total": got.get("total"), "why": got.get("why", "")}


def check(path, run=None):
    """{path, ok, lines}: what Starboard can say about a typed folder, one plain line each."""
    from . import start
    try:
        path = tidy(path)
    except ValueError as e:
        return {"path": str(path or ""), "ok": False, "lines": [str(e)]}
    if not start.safe_folder(path):
        if path in start.TOP_FOLDERS or re.match(r"^/home/[^/]+$", path):  # a whole place, or a home folder itself
            why = f"That is a whole folder of the computer: choose one inside it, such as {path}/media."
        else:
            why = "Starboard never uses system folders. Choose one under " + ", ".join(ROOTS[:3]) + ", such as /srv/media."
        return {"path": path, "ok": False, "lines": [why]}
    lines = []
    try:
        got = _read(path, run) if allowed(path) else {"exists": None}
    except ValueError:  # a link that leads out of the usual places
        return {"path": path, "ok": False, "lines": ["That folder leads somewhere Starboard never uses. Choose one under " + ", ".join(ROOTS[:3]) + "."]}
    if got.get("why"):
        lines.append(got["why"])
    elif got.get("exists"):
        lines.append("This folder is there.")
    elif got.get("exists") is False:
        lines.append(f"This folder is made for you when the apps start{', inside ' + got['made_in'] if got.get('made_in') else ''}.")
    if got.get("free") is not None and got.get("total"):
        lines.append(f"{_size(got['free'])} free of {_size(got['total'])} on its disk.")
        if got["free"] < 50 * 10 ** 9:
            lines.append("Less than 50 GB free: films and series fill that quickly.")
    return {"path": path, "ok": True, "lines": lines}


def _size(n):
    for unit, size in (("TB", 10 ** 12), ("GB", 10 ** 9), ("MB", 10 ** 6)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n} bytes"
