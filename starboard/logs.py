"""Starboard's own log, for System, Logs and for reporting a problem.

One file a day in data/logs (one JSON line per entry), kept for as many days as Settings, General says (60 by
default); older days are removed once a day when something is written. No thread of its own.

Normal logging records what happened: Starboard starting, signing in, settings and apps changing, background
work, alerts, updates and every error. Detailed logging (for reporting a problem) adds each page request and
each call to your apps, with how long it took, and the full detail of errors. It can turn itself off after
24 hours.

Personal details are removed from every entry before it is written, in both modes: passwords, API keys and
tokens, IP addresses, host and computer names, email addresses, user names in folder paths, and the names you
gave Starboard (the dashboard's name). Media titles and app names stay, because they help find a problem.
"""

import json
import os
import platform
import re
import socket
import sys
import threading
import time
import traceback

LEVELS = ("error", "warning", "info", "detail")
KEEP_CHOICES = (7, 14, 30, 60, 90, 180, 365)
DETAIL_CHOICES = ("off", "day", "on")
DEFAULTS = {"keep_days": 60, "detail": "off", "detail_until": 0}

_current = None  # the running app's log, so any module can write with logs.event()


def event(level, area, message, **extra):
    """Writes to the running log, if there is one (tests and tools run without)."""
    if _current:
        _current.write(level, area, message, **extra)
    elif level != "detail":
        print(f"[starboard] {area}: {message}", flush=True)


def detail(area, message, **extra):
    if _current and _current.detailed():
        _current.write("detail", area, message, **extra)


def error(area, message, exc=None):
    """An error, with where it happened when detailed logging is on (or always, for one Starboard did not expect)."""
    extra = {}
    if exc is not None:
        extra["trace"] = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)[-6:])
    event("error", area, message, **extra)


# Removing personal details -------------------------------------------------------------------------------

_SECRET = re.compile(r"(?i)\b(api[_-]?key|apikey|token|password|passwd|secret|auth|authorization|cookie|session|x-api-key)"
                     r"(\s*[=:]\s*|\"\s*:\s*\")([^\s&,;\"']+)")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
_LONG = re.compile(r"\b[A-Za-z0-9_-]{24,}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IPV4 = re.compile(r"\b(?!127\.0\.0\.1\b)(?!0\.0\.0\.0\b)(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6 = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b")
_URL_HOST = re.compile(r"(?i)\b(https?://)(?!127\.0\.0\.1\b|localhost\b)([^/\s:\"']+)")
_HOME = re.compile(r"(/home/|/Users/)[^/\s\"']+")


def redact(text, words=()):
    text = str(text)
    text = _BEARER.sub(lambda m: f"{m.group(1)} [removed]", text)  # first, so "Authorization: Bearer x" loses x
    text = _SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)}[removed]", text)
    text = _EMAIL.sub("[email]", text)
    text = _URL_HOST.sub(lambda m: f"{m.group(1)}[host]", text)
    text = _IPV4.sub("[address]", text)
    text = _IPV6.sub("[address]", text)
    text = _HOME.sub(lambda m: f"{m.group(1)}[user]", text)
    for w in words:
        if w and len(w) >= 3 and w.strip().lower() != "starboard":  # the default name is not personal
            text = re.sub(re.escape(w), "[name]", text, flags=re.I)
    text = _LONG.sub("[removed]", text)  # last: keys and tokens the patterns above did not name
    return text


class Log:
    def __init__(self, data_dir, settings=lambda: DEFAULTS, words=lambda: ()):
        self.dir = os.path.join(data_dir, "logs")
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        self.settings = settings
        self.words = words
        self.lock = threading.Lock()
        self.pruned = None

    def _words(self):
        try:
            return [*self.words(), socket.gethostname()]
        except Exception:  # a log must never fail the thing it records
            return []

    def detailed(self):
        s = self.settings()
        mode = s.get("detail", "off")
        return mode == "on" or (mode == "day" and s.get("detail_until", 0) > time.time())

    def write(self, level, area, message, **extra):
        if level == "detail" and not self.detailed():
            return
        words = self._words()
        entry = {"t": round(time.time(), 3), "level": level if level in LEVELS else "info", "area": str(area)[:30],
                 "message": redact(message, words)[:2000]}
        for k, v in extra.items():
            entry[k] = redact(v, words)[:8000] if isinstance(v, str) else v
        if level in ("error", "warning") or area == "start":
            # Docker's own log gets only start-up and problems (with personal details removed), so it stays small
            # and holds nothing the Delete logs button cannot reach.
            print(f"[starboard] {entry['area']}: {entry['message']}", flush=True)
        day = time.strftime("%Y-%m-%d")
        try:
            with self.lock:
                fd = os.open(os.path.join(self.dir, f"{day}.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                with os.fdopen(fd, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, separators=(",", ":")) + "\n")
                if self.pruned != day:
                    self.pruned = day
                    self.prune()
        except OSError:
            pass

    def files(self):
        try:
            return sorted((n for n in os.listdir(self.dir) if re.match(r"^\d{4}-\d{2}-\d{2}\.log$", n)), reverse=True)
        except OSError:
            return []

    def prune(self):
        keep = int(self.settings().get("keep_days", 60))
        cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - keep * 86400))
        for name in self.files():
            if name[:10] < cutoff:
                try:
                    os.remove(os.path.join(self.dir, name))
                except OSError:
                    pass

    def read(self, level="all", query="", before=None, limit=300):
        """Newest first. level: all, problems (warnings and errors) or detail. before: a time, for the next page."""
        out = []
        query = query.strip().lower()
        for name in self.files():
            try:
                with open(os.path.join(self.dir, name), encoding="utf-8") as f:
                    lines = f.readlines()
            except OSError:
                continue
            for line in reversed(lines):
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if before and e.get("t", 0) >= before:
                    continue
                if level == "problems" and e.get("level") not in ("error", "warning"):
                    continue
                if level == "detail" and e.get("level") != "detail":
                    continue
                if query and query not in (e.get("message", "") + " " + e.get("area", "")).lower():
                    continue
                out.append(e)
                if len(out) >= limit:
                    return out
        return out

    def summary(self):
        names = self.files()
        size = sum(os.path.getsize(os.path.join(self.dir, n)) for n in names if os.path.exists(os.path.join(self.dir, n)))
        return {"days": len(names), "oldest": names[-1][:10] if names else None, "bytes": size}

    def clear(self):
        removed = 0
        with self.lock:
            for name in self.files():
                try:
                    os.remove(os.path.join(self.dir, name))
                    removed += 1
                except OSError:
                    pass
        return removed

    def text(self, entries):
        lines = []
        for e in reversed(entries):
            when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.get("t", 0)))
            lines.append(f"{when} {e.get('level', '').upper():7} {e.get('area', '')}: {e.get('message', '')}")
            if e.get("trace"):
                lines.extend("    " + t for t in e["trace"].rstrip().splitlines())
        return "\n".join(lines) + "\n"


def report(app, log):
    """Everything an issue needs, with personal details removed: versions, how it runs, what is switched on,
    the kinds of apps, and the last problems and detailed entries."""
    d = app.config.data
    perf = d.get("performance", {})
    kinds = {}
    for s in d.get("services", []):
        kinds[s.get("type", "link")] = kinds.get(s.get("type", "link"), 0) + 1
    on = [name for name, value in (
        ("watching and alerts", d.get("watch", {}).get("enabled")), ("download hours", d.get("download_hours", {}).get("enabled")),
        ("Live TV", d.get("extras", {}).get("livetv")), ("history import kept", d.get("extras", {}).get("import_keep")),
        ("Jellyfin user defaults", d.get("extras", {}).get("defaults")),
        ("listening progress kept", d.get("extras", {}).get("listening_keep")), ("system history", perf.get("history")),
        ("daily space record", perf.get("space_log"))) if value]
    try:
        from . import containers
        docker = containers.available()
    except Exception:
        docker = False
    lines = [
        "## About this Starboard",
        "",
        f"- Starboard {app.version}",
        f"- Python {platform.python_version()} on {platform.system()} {platform.machine()}",
        f"- Running in {'a container' if os.path.exists('/.dockerenv') else 'a native install'}; Docker access {'on' if docker else 'off'}",
        f"- Preset: {perf.get('preset', 'custom')}; sorting storage by type: {perf.get('usage_every', 'ask')}",
        f"- Switched on: {', '.join(on) or 'nothing optional'}",
        f"- Apps: {', '.join(f'{k} ({n})' for k, n in sorted(kinds.items())) or 'none'}",
        f"- Detailed logging: {'on' if log.detailed() else 'off'}",
        "",
        "## Recent problems and detail (personal details removed)",
        "",
        "```",
        log.text(log.read("all", limit=200)).rstrip(),
        "```",
    ]
    return redact("\n".join(lines), [d.get("site_name", ""), socket.gethostname()]) + "\n"


def start(data_dir, settings, words):
    global _current
    _current = Log(data_dir, settings, words)
    return _current
