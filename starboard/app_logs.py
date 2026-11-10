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
