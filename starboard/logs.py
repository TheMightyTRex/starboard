"""Starboard's own log, for System, Logs and for reporting a problem.

One file a day in data/logs (one JSON line per entry). Settings, General, Backup/Logs limits Starboard's logs
(DASH-451): kept for a number of days (30 by default) and no more than a total size (50 MB by default), whichever
comes first removing the oldest days. The limits cover every log Starboard keeps itself: the day files (which hold
the jobs, updates and plug-ins' lines too), the API's audit log (audit.jsonl and its older copies) and the last
Starboard update's log (data/self-update.log). Plug-ins keep no log files in Starboard; their containers' logs are
Docker's, like the apps'. Old days go when a new day's file starts, when the limits are saved, and when the size
written since passes the limit: no timer and no thread of its own. Delete all logs (clear) empties today's file
instead of removing it, so Starboard keeps logging, and writes who deleted them as the first new line.

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
import threading
import time
import traceback

LEVELS = ("error", "warning", "info", "detail")
KEEP_CHOICES = (7, 14, 30, 60, 90, 180, 365)
SIZE_CHOICES = (10, 25, 50, 100, 250, 500)  # MB, for every log Starboard keeps together
DETAIL_CHOICES = ("off", "day", "on")
SHOW_CHOICES = (50, 100, 200, 500, 1000)  # DASH-534: the most lines System, Logs, Copy and Download give
DEFAULTS = {"keep_days": 30, "max_mb": 50, "detail": "off", "detail_until": 0, "show_lines": 200, "alerts_only": False}
DAY_FILE = re.compile(r"^\d{4}-\d{2}-\d{2}\.log$")
AUDIT_FILE = re.compile(r"^audit\.jsonl(\.\d{1,2})?$")  # api_v1.audit: audit.jsonl and audit.jsonl.1 to .5
UPDATE_LOG = "self-update.log"  # in the data folder: the last Starboard update's lines (self_update.py)

_current = None  # the running app's log, so any module can write with logs.event()
_hidden = []  # secrets Starboard was handed while it runs (such as the password for first runs), never written
MAX_HIDDEN = 20


def hide(secret):
    """Removes this exact secret from every log line from now on, wherever it turns up (an app's error message that
    repeats it back, for example). Held in memory only, and only the newest few."""
    secret = str(secret or "")
    if len(secret) >= 4 and secret not in _hidden:
        _hidden.append(secret)
        del _hidden[:-MAX_HIDDEN]


def event(level, area, message, **extra):
    """Writes to the running log, if there is one (tests and tools run without)."""
    if _current:
        _current.write(level, area, message, **extra)
    elif level != "detail":
        print(f"[starboard] {redact(area)[:30]}: {redact(message)[:2000]}", flush=True)


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
    for secret in _hidden:  # first, before any pattern can split it
        text = text.replace(secret, "[removed]")
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


# The words a line of a level must hold (see Log.read): checked on the raw bytes, so a line of another level is passed
# over before it is read as JSON.
_LEVEL_WORDS = {"problems": (b'"error"', b'"warning"'), "detail": (b'"detail"',)}
BLOCK = 64 * 1024


def _lines_backwards(path):
    """The lines of a file, last first, as bytes, read from the end in blocks: only as much of the file as is asked
    for is ever read, and none of it is kept once passed."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        rest = b""
        while pos > 0:
            step = min(BLOCK, pos)
            pos -= step
            f.seek(pos)
            chunk = f.read(step) + rest
            parts = chunk.split(b"\n")
            rest = parts[0]  # may be the end of a line that starts in the block before
            for line in reversed(parts[1:]):
                if line:
                    yield line
        if rest:
            yield rest


def _count_lines(path):
    """How many lines a file holds, counted in blocks without reading any of them as JSON."""
    n, last = 0, b"\n"
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            n += chunk.count(b"\n")
            last = chunk[-1:]
    return n + (0 if last == b"\n" else 1)


def size_words(n):
    """Bytes in words for the log and the pages' status: 352 KB, 1.2 MB."""
    n = int(n or 0)
    if n < 1024:
        return f"{n} bytes" if n != 1 else "1 byte"
    for unit in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "KB" or n >= 10 else f"{n:.1f} {unit}"


class Log:
    def __init__(self, data_dir, settings=lambda: DEFAULTS, words=lambda: ()):
        self.data_dir = data_dir
        self.dir = os.path.join(data_dir, "logs")
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        self.settings = settings
        self.words = words
        self.lock = threading.Lock()
        self.pruned = None
        self.room = None  # bytes that can be written before the size limit is looked at again (None: not known yet)
        self._counts = {}  # day file path -> ((size, time), lines), for total()

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
        line = json.dumps(entry, separators=(",", ":")) + "\n"
        try:
            with self.lock:
                fd = os.open(os.path.join(self.dir, f"{day}.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                with os.fdopen(fd, "a", encoding="utf-8") as f:
                    f.write(line)
                if self.room is not None:
                    self.room -= len(line)
                # A new day's file, or more written since the last look than the size limit leaves room for: old days
                # go now. Counted in memory, so a write costs no extra look at the folder.
                if self.pruned != day or self.room is None or self.room < 0:
                    self.pruned = day
                    self._prune()
        except OSError:
            pass

    def files(self):
        """The day files, newest first."""
        try:
            return sorted((n for n in os.listdir(self.dir) if DAY_FILE.match(n)), reverse=True)
        except OSError:
            return []

    def limits(self):
        s = self.settings()
        try:
            keep = int(s.get("keep_days", DEFAULTS["keep_days"]))
        except (TypeError, ValueError):
            keep = DEFAULTS["keep_days"]
        try:
            most = int(s.get("max_mb", DEFAULTS["max_mb"]))
        except (TypeError, ValueError):
            most = DEFAULTS["max_mb"]
        return max(1, keep), max(1, most) * 1024 * 1024

    def covered(self):
        """Every log file the limits and Delete all logs cover, as dicts: path, name, kind (day, audit or update),
        size, and when (the day's start for a day file, else when it was last written). A file that goes while it is
        looked at, or cannot be read, is left out."""
        out = []
        try:
            names = os.listdir(self.dir)
        except OSError:
            names = []
        paths = [(os.path.join(self.dir, n), n, "day" if DAY_FILE.match(n) else "audit")
                 for n in names if DAY_FILE.match(n) or AUDIT_FILE.match(n)]
        paths.append((os.path.join(self.data_dir, UPDATE_LOG), UPDATE_LOG, "update"))
        for path, name, kind in paths:
            try:
                st = os.stat(path)
            except OSError:
                continue
            when = st.st_mtime
            if kind == "day":
                try:
                    when = time.mktime(time.strptime(name[:10], "%Y-%m-%d"))
                except ValueError:
                    continue
            out.append({"path": path, "name": name, "kind": kind, "size": st.st_size, "when": when})
        return out

    def prune(self):
        """Applies the limits now (after they are saved). Returns {"removed": files, "freed": bytes}."""
        with self.lock:
            return self._prune()

    def _prune(self):
        keep, most = self.limits()
        today = time.strftime("%Y-%m-%d")
        cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - keep * 86400))
        oldest_kept = time.time() - keep * 86400
        files = self.covered()
        # Only older days and the audit log's older copies go: today's file, the audit log being written and the
        # last update's log stay, so Starboard and the API keep logging and Settings, Updates keeps its steps.
        removable = [f for f in files if (f["kind"] == "day" and f["name"][:10] < today) or
                     (f["kind"] == "audit" and f["name"] != "audit.jsonl")]
        removed, freed = 0, 0

        def remove(f):
            nonlocal removed, freed
            try:
                os.remove(f["path"])
            except FileNotFoundError:
                pass
            except OSError:
                return False  # cannot be removed (its permissions): left, and the next oldest goes instead
            removed += 1
            freed += f["size"]
            return True

        gone = set()
        for f in removable:
            if (f["name"][:10] < cutoff) if f["kind"] == "day" else f["when"] < oldest_kept:
                if remove(f):
                    gone.add(f["path"])
        total = sum(f["size"] for f in files if f["path"] not in gone)
        for f in sorted((f for f in removable if f["path"] not in gone), key=lambda f: f["when"]):
            if total <= most:
                break
            if remove(f):
                total -= f["size"]
        # What is left to write before the size is looked at again; if today's file alone is over the limit, look
        # again after another tenth of it rather than at every line.
        self.room = most - total if total < most else most // 10
        return {"removed": removed, "freed": freed}

    def summary(self):
        files = self.covered()
        days = sorted(f["name"][:10] for f in files if f["kind"] == "day")
        keep, most = self.limits()
        return {"days": len(days), "oldest": days[0] if days else None, "bytes": sum(f["size"] for f in files),
                "files": len(files), "keep_days": keep, "max_bytes": most}

    def clear(self, by="", update_running=False):
        """Delete all logs: every log file goes, apart from today's file and the audit log being written, which are
        emptied so Starboard and the API keep writing to them, and the last update's log while an update runs. Then
        the first new line says who deleted them and how much. Returns {"removed", "emptied", "freed"}."""
        removed, emptied, freed = 0, 0, 0
        today = time.strftime("%Y-%m-%d") + ".log"
        with self.lock:
            for f in self.covered():
                if f["kind"] == "update" and update_running:
                    continue
                try:
                    if f["name"] in (today, "audit.jsonl"):
                        with open(f["path"], "r+b") as fh:
                            fh.truncate(0)
                        emptied += 1
                    else:
                        os.remove(f["path"])
                        removed += 1
                    freed += f["size"]
                except FileNotFoundError:
                    pass
                except OSError:
                    continue  # one that cannot be changed stays; the rest still go
            self.pruned = time.strftime("%Y-%m-%d")
            self.room = None
        files = removed + emptied
        self.write("info", "logs", f"All logs deleted{' by ' + by if by else ''}: {size_words(freed)} in "
                                   f"{files} {'file' if files == 1 else 'files'}")
        return {"removed": removed, "emptied": emptied, "freed": freed}

    def read(self, level="all", query="", before=None, limit=300, alerts_only=False):
        """Newest first. level: all, problems (warnings and errors) or detail. alerts_only (DASH-534) keeps only errors
        and warnings, on top of the level, so with detail it finds nothing. before: a time, for the next page. Each day
        file is read from its end, and reading stops as soon as limit entries are found."""
        out = []
        query = query.strip().lower()
        if alerts_only and level == "detail":
            return out
        # A line can only be of a level if that word is in it, so other lines are passed over before they are read as
        # JSON. The dashboard's Alerts card asks for problems every minute, and with few problems every day kept (60
        # by default) was read line by line: 250 ms each time over 60 days (optimisation review, 16 November 2026).
        problems = alerts_only or level == "problems"
        wanted = _LEVEL_WORDS["problems"] if problems else _LEVEL_WORDS.get(level)
        for name in self.files():
            try:
                for raw in _lines_backwards(os.path.join(self.dir, name)):
                    if wanted and not any(w in raw for w in wanted):
                        continue
                    try:
                        e = json.loads(raw)
                    except ValueError:
                        continue
                    if not isinstance(e, dict):
                        continue
                    if before and e.get("t", 0) >= before:
                        continue
                    if problems and e.get("level") not in ("error", "warning"):
                        continue
                    if level == "detail" and e.get("level") != "detail":
                        continue
                    if query and query not in (e.get("message", "") + " " + e.get("area", "")).lower():
                        continue
                    out.append(e)
                    if len(out) >= limit:
                        return out
            except OSError:
                continue
        return out

    def total(self):
        """How many entries the day files hold (lines, not read as JSON). A file's count is kept until its size or its
        time changes, so asking again costs a look at each file, not a read: only today's file is counted again."""
        cache = self._counts
        n = 0
        for name in self.files():
            path = os.path.join(self.dir, name)
            try:
                st = os.stat(path)
                key = (st.st_size, st.st_mtime_ns)
                if cache.get(path, (None,))[0] != key:
                    cache[path] = (key, _count_lines(path))
                n += cache[path][1]
            except OSError:
                cache.pop(path, None)
        for gone in [p for p in cache if os.path.basename(p) not in self.files()]:
            del cache[gone]
        return n

    def view(self, level="all", query="", before=None, alerts_only=None, limit=None):
        """What System, Logs, Copy and Download show: the newest entries up to the account's limit (Settings kept in
        logs.show_lines, 200 by default), only alerts when that is on, and how many there are to show from."""
        shown_max = limit or self.show_lines()
        only = self.alerts_only() if alerts_only is None else bool(alerts_only)
        entries = self.read(level, query, before, shown_max, only)
        return {"entries": entries, "limit": shown_max, "alerts_only": only, "total": self.total(),
                "all_found": len(entries) < shown_max, "filtered": bool(query.strip() or level != "all" or only)}

    def show_lines(self):
        try:
            n = int(self.settings().get("show_lines", DEFAULTS["show_lines"]))
        except (TypeError, ValueError):
            n = DEFAULTS["show_lines"]
        return n if n in SHOW_CHOICES else DEFAULTS["show_lines"]

    def alerts_only(self):
        return self.settings().get("alerts_only") is True

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
        f"- Active: {', '.join(on) or 'nothing optional'}",
        f"- Apps: {', '.join(f'{k} ({n})' for k, n in sorted(kinds.items())) or 'none'}",
        f"- Detailed logging: {'on' if log.detailed() else 'off'}",
        "",
        "## Recent problems and detail (personal details removed)",
        "",
        "```",
        log.text(log.read("all", limit=log.show_lines(), alerts_only=log.alerts_only())).rstrip(),
        "```",
    ]
    return redact("\n".join(lines), [d.get("site_name", ""), socket.gethostname()]) + "\n"


def start(data_dir, settings, words):
    global _current
    _current = Log(data_dir, settings, words)
    return _current


# Settings, General, Backup/Logs and the API (DASH-451) ------------------------------------------------------

def limits_answer(app, apps=None):
    """The limits, their choices, what the logs take now, what they cover, and the apps' own limit from Docker."""
    s = app.config.data["logs"]
    return {"keep_days": s.get("keep_days", DEFAULTS["keep_days"]), "max_mb": s.get("max_mb", DEFAULTS["max_mb"]),
            "show_lines": app.log.show_lines(), "alerts_only": app.log.alerts_only(),  # DASH-534: what the page, Copy and Download give
            "keep_days_choices": list(KEEP_CHOICES), "max_mb_choices": list(SIZE_CHOICES), "show_lines_choices": list(SHOW_CHOICES),
            "summary": app.log.summary(),
            "covers": ["Starboard's own log, one file a day, with its jobs, updates and plug-ins' lines",
                       "the API's audit log", "the last Starboard update's log"],
            **({"apps": apps} if apps is not None else {})}


def delete_all(app, by):
    """Delete all logs, from the page (after the password) or the API (a manage key that ticked Logs)."""
    from . import self_update
    try:
        busy = self_update.running(self_update.load(app.data_dir), data_dir=app.data_dir)
    except Exception:  # noqa: BLE001  if it cannot tell, the update's log is kept
        busy = True
    return app.log.clear(by, update_running=busy)
