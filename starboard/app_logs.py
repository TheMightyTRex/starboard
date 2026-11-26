"""App logs on System, Logs (DASH-223, owner, 10 November 2026): each app's latest log lines, read through Docker,
for signed-in people only, in place of Dozzle, which showed every container's logs with no sign-in. Lines are
cleaned as Starboard's own log is (logs.redact): keys, passwords, tokens, e-mail and network addresses, home
folders and the server's names are hidden, so a log can be copied into a report.
"""
import re

MAX_LINES = 1000
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def listing(docker=None):
    """{available, apps: [{name, state}]}: the containers on this computer, Starboard's own helpers left out."""
    from . import containers
    if docker is None and not containers.available():
        return {"available": False, "apps": []}
    try:
        found = (docker or containers.docker)("GET", "/containers/json?all=1")
    except containers.DockerError:
        return {"available": False, "apps": []}
    apps = []
    for c in found:
        name = (c.get("Names") or ["/"])[0].lstrip("/")
        if name.startswith("starboard-updater-") or not name:
            continue
        apps.append({"name": name, "state": c.get("State", "")})
    return {"available": True, "apps": sorted(apps, key=lambda a: a["name"].lower())}


def _text(raw):
    """Docker's log stream: an 8-byte header before each chunk when the container has no terminal."""
    if raw[:1] in (b"\x01", b"\x02") and len(raw) >= 8:
        out, i = b"", 0
        while i + 8 <= len(raw):
            n = int.from_bytes(raw[i + 4:i + 8], "big")
            out += raw[i + 8:i + 8 + n]
            i += 8 + n
        raw = out
    return _ANSI.sub("", raw.decode("utf-8", "replace"))


def lines(name, tail=300, find="", docker=None, words=()):
    """{name, lines}: the last lines of one app's log, newest last, cleaned, optionally only those with `find`."""
    from . import containers, logs
    known = {a["name"] for a in listing(docker)["apps"]}
    if name not in known:
        raise LookupError("No app with that name on this computer")
    try:
        tail = max(10, min(MAX_LINES, int(tail)))
    except (TypeError, ValueError):
        tail = 300
    raw = (docker or containers.docker)("GET", f"/containers/{name}/logs?stdout=1&stderr=1&timestamps=1&tail={tail}", raw=True, timeout=15)
    out = [logs.redact(line, words) for line in _text(raw).splitlines() if line.strip()]
    find = str(find or "").strip().lower()[:100]
    if find:
        out = [line for line in out if find in line.lower()]
    return {"name": name, "lines": out[-tail:]}


# The apps' own log limits (DASH-451): Docker keeps each container's log, and its daemon.json can cap them for every
# container (log-opts), which Starboard cannot change (it needs the server's password). Starboard reads what each
# container was given, to say it on Settings, General, Backup/Logs. Asked only when that page asks, and kept
# for 10 minutes: one listing and one look at each container, never on a timer.
LIMIT_KEEP = 600
_limits = {"at": 0, "out": None}
COMPOSE_LIMIT = {"max-size": "10m", "max-file": "3"}  # what Starboard writes for the apps and plug-ins it installs
COMPOSE_DRIVERS = ("json-file", "local", "journald", "none")  # drivers that keep the log on this computer


def compose_logging(indent="    "):
    """The logging lines of a Compose service Starboard writes: Docker's own json-file driver, 3 files of 10 MB, so a
    new install is capped even when daemon.json sets nothing. Containers already running keep what they have until
    their file is written again (an update, or Install apps run again)."""
    return [f"{indent}logging:", f"{indent}  driver: json-file", f"{indent}  options:"] + \
        [f'{indent}    {k}: "{v}"' for k, v in COMPOSE_LIMIT.items()]


def _bytes(size):
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*([kmg]?)b?\s*$", str(size or ""), re.I)
    if not m:
        return None
    return int(float(m.group(1)) * {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[m.group(2).lower()])


def limits(docker=None, now=None):
    """{available, driver, max_size, max_file, per_app (bytes or None), capped, uncapped: [names]}, the most common
    limit among the containers as the one shown. Drivers other than json-file and local keep no files here (journald
    sends them to the system's journal), so they say so with no size."""
    import time
    from . import containers
    now = now or time.time()
    if docker is None and _limits["out"] is not None and now - _limits["at"] < LIMIT_KEEP:
        return _limits["out"]
    out = {"available": False, "driver": "", "max_size": "", "max_file": "", "per_app": None, "capped": 0, "uncapped": []}
    if docker is None and not containers.available():
        return out
    ask = docker or containers.docker
    try:
        found = ask("GET", "/containers/json?all=1")
        driver = (ask("GET", "/info") or {}).get("LoggingDriver", "")
    except containers.DockerError:
        return out
    seen = {}
    for c in found:
        name = (c.get("Names") or ["/"])[0].lstrip("/")
        if not name or name.startswith("starboard-updater-"):
            continue
        try:
            conf = ((ask("GET", f"/containers/{c['Id']}/json") or {}).get("HostConfig") or {}).get("LogConfig") or {}
        except containers.DockerError:
            continue
        opts = conf.get("Config") or {}
        kind = conf.get("Type") or driver
        if kind == "json-file" and not opts.get("max-size"):
            out["uncapped"].append(name)  # Docker's default: one file that grows with no end
            continue
        if kind == "json-file":
            key = (kind, opts["max-size"], opts.get("max-file") or "1")
        elif kind == "local":  # local's own default when not set: 5 files of 20 MB
            key = (kind, opts.get("max-size") or "20m", opts.get("max-file") or "5")
        else:
            continue  # journald, syslog and the rest keep no files here
        seen[key] = seen.get(key, 0) + 1
        out["capped"] += 1
    out.update(available=True, driver=driver)
    if seen:
        (kind, size, files), _ = max(seen.items(), key=lambda kv: kv[1])
        each = _bytes(size)
        out.update(driver=kind, max_size=size, max_file=str(files),
                   per_app=each * int(files) if each and str(files).isdigit() else None)
    out["uncapped"].sort(key=str.lower)
    if docker is None:
        _limits.update(at=now, out=out)
    return out
