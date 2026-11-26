"""Starboard's public API, version 1 (DASH-274): /api/v1/, for other apps, scripts, AI assistants and plug-ins.
Rules from starboard/DEVELOPER-BEST-PRACTICE-2026-11-09.md (A1 to A19, AS1 to AS18):

- Its own keys, separate from the browser's session (AS1): sb_<right>_<id>_<secret>, shown once, stored as SHA-256
  (AS2, AS3), sent only as "Authorization: Bearer" (AS4); a right and optional scopes (AS5). "read" reads; "manage"
  also does the everyday actions the pages do (approve a request, pause downloads, refresh the library). Nothing a
  key can do changes settings, keys or plug-in choices, calls an address the key gives, or needs the password:
  those stay with a signed-in person (STARBOARD-CAPABILITIES-2026-11-09.md lists them as never by key). The one
  exception, since API 1.2.0 (DASH-424): a manage key with the updates scope, which is never given unless ticked,
  may update Starboard, Reelix, an app or a plug-in to the version Starboard already knows of (never from an
  address), roll a plug-in back and (1.5.0, DASH-454) install every waiting update as one batch, each with the
  same backup, health check and way back as the pages. The second, since API 1.4.0 (DASH-451): a manage key with
  the logs scope, also never given unless ticked, may change the log limits (days and size) and delete all logs, as
  Settings, General, Backup/Logs does. The third, since API 1.8.0 (plug-in API 1.17): a plug-in's own key,
  which only reads, may raise and clear alerts with POST /api/v1/plugin/alerts, while the plug-in is active and its
  approved permissions include alerts:send; any other key gets 404 (AS6), and a plug-in may raise 30 new alerts an
  hour at most. They go out once until cleared, through the same channel, events and log as Starboard's own;
  optional expiry, last used at most once a minute, revoke (AS8); an audit line for each change and each refused
  key (AS9); refused keys count towards the sign-in lockout per address (AS10). No cookies, so no CSRF and no CORS.
- Answers: JSON, snake_case, RFC 3339 times; errors as RFC 9457 problem details (A6); lists with limit and an
  opaque cursor (A7); weak ETags and 304 (A9) with Cache-Control matching how often the answer changes; a token
  bucket per key, 120 a minute, with Retry-After and RateLimit headers (A13); X-Request-Id on every answer (A18).
- Never a secret in an answer (AS7): app keys show as set or not set.
- Writes (A10 to A12, AS9): POST only, a JSON body of at most 64 KB, Idempotency-Key kept for 24 hours, an audit
  line for every write; long work answers 202.
- Events (A15): one Server-Sent Events stream, /api/v1/events, CloudEvents-shaped, with Last-Event-ID resume from a
  ring of the last 200; at most 8 streams at once, each closed after an hour.
- AI assistants (DASH-464, API 1.7.0): POST /api/v1/mcp speaks MCP with a read key, off until the owner activates it
  in Settings, Security, API keys; its tools read through the routes here (starboard/mcp.py).
- Described in starboard/openapi.json, served at /api/v1/openapi.json; a test fails when a route and the
  description differ (A4, AS17).
"""
import base64
import collections
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.parse
import uuid

from . import deprecations

API_VERSION = "1.10.0"  # 1.10.0 (26 November 2026, DASH-603): deprecations in GET /, Deprecation and Sunset headers on a route that is going, 410 gone once removed. 1.9.0 (26 November 2026): several backup places in /backup/copies (destinations, safe, settings_zip), the test for each, and POST /backup/settings-copy. 1.8.0 (20 November 2026, plug-in API 1.17): POST /plugin/alerts, alerts from a plug-in with alerts:send, answered only to its own key. 1.7.0 (19 November 2026, DASH-464): /mcp, read-only tools for AI assistants, off until activated. 1.6.0 (16 November 2026, DASH-452): /backup/copies and its test. 1.5.0: Install all updates (DASH-454). 1.4.0 (16 November 2026, DASH-451): /logs/limits and /logs/delete. 1.3.0 (15 November 2026, DASH-434): /downloads/issues. 1.2.0 (DASH-424): updates
KEYS_FILE = "api-keys.json"
RIGHTS = ("read", "manage")  # manage: read, and the everyday actions (DASH-274). "admin" stays with the pages
SCOPES = ("apps", "downloads", "media", "system", "library", "requests")
EXPLICIT_SCOPES = ("logs", "updates")  # reached only when ticked: a key with no scopes does not have them (DASH-76, DASH-424)
ALL_SCOPES = SCOPES + EXPLICIT_SCOPES
PER_MINUTE = 120
MAX_STREAMS = 8  # A14: event streams open at once
STREAM_SECONDS = 3600  # a stream closes after an hour; the client reconnects with Last-Event-ID
KEEP_ALIVE = 25  # seconds between comments on a quiet stream, inside the server's 30 second socket time-out
IDEMPOTENCY_KEEP = 1000  # A11: Idempotency-Keys remembered, oldest dropped, for 24 hours
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "openapi.json")
PROBLEM = "https://github.com/TheMightyTRex/starboard/blob/main/docs/api/errors.md#"
SECRET_NAMES = re.compile(r"(api_?key|token|password|secret|cookie|authorization)", re.I)
_lock = threading.Lock()
_buckets = {}
_used = {}
_done = collections.OrderedDict()  # (key id, method, path, Idempotency-Key) -> (time, status, raw answer)


class NotReady(Exception):
    """What a route needs is not set up yet, such as Reelix for the Library: 409 not_set_up."""


class RateLimited(Exception):
    """Too many of one thing in a while (API 1.8.0, a plug-in's alerts): 429 rate_limited with Retry-After."""

    def __init__(self, message, wait):
        super().__init__(message)
        self.wait = wait


class Conflict(Exception):
    """It cannot be done now (DASH-424): 409 with its own code, update_running or cannot_update."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


# Keys ---------------------------------------------------------------------------------------------------------

def _path(data_dir):
    return os.path.join(data_dir, KEYS_FILE)


def _load(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            return json.load(f).get("keys", [])
    except (OSError, ValueError):
        return []


def _save(data_dir, keys):
    tmp = _path(data_dir) + ".new"
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump({"keys": keys}, f, indent=1)
    os.replace(tmp, _path(data_dir))


def _digest(key):
    return hashlib.sha256(key.encode()).hexdigest()


def public(k):
    """A key as pages and the API show it: never its secret or its hash."""
    return {"id": k["id"], "name": k["name"], "right": k["right"], "scopes": k.get("scopes") or [],
            "created_at": k["created_at"], "expires_at": k.get("expires_at"), "last_used_at": k.get("last_used_at"),
            "prefix": f"sb_{k['right']}_{k['id']}_"}


def list_keys(data_dir):
    return [public(k) for k in _load(data_dir)]


def create_key(data_dir, name, right="read", scopes=None, expires_days=90):
    """Makes a key; returns (the key, shown this once, and its public details)."""
    name = re.sub(r"\s+", " ", str(name or "")).strip()[:60]
    if not name:
        raise ValueError("Name the key after what will use it, such as Home Assistant or an AI assistant")
    if right not in RIGHTS:
        raise ValueError("Choose what the key may do: read, or read and manage")
    scopes = sorted({str(s) for s in (scopes or [])})
    if any(s not in ALL_SCOPES for s in scopes):
        raise ValueError("Choose scopes from the list")
    keys = _load(data_dir)
    if len(keys) >= 50:
        raise ValueError("Starboard keeps up to 50 keys. Revoke one you no longer use first")
    kid = secrets.token_hex(3)
    while any(k["id"] == kid for k in keys):
        kid = secrets.token_hex(3)
    key = f"sb_{right}_{kid}_{secrets.token_urlsafe(32)}"
    now = _now()
    expires = None
    if expires_days not in (None, 0, "", "never"):
        days = int(expires_days)
        if not 1 <= days <= 3650:
            raise ValueError("Choose an expiry from 1 day to 10 years, or never")
        expires = _iso(now + dt.timedelta(days=days))
    item = {"id": kid, "name": name, "right": right, "scopes": scopes, "hash": _digest(key),
            "created_at": _iso(now), "expires_at": expires, "last_used_at": None}
    keys.append(item)
    _save(data_dir, keys)
    audit(data_dir, "key_created", key_id=kid, name=name, right=right)
    return key, public(item)


def revoke_key(data_dir, kid):
    keys = _load(data_dir)
    left = [k for k in keys if k["id"] != kid]
    if len(left) == len(keys):
        return False
    _save(data_dir, left)
    audit(data_dir, "key_revoked", key_id=kid)
    return True


def find_key(data_dir, header):
    """The key's record for an Authorization header, or None. Expired keys are refused."""
    m = re.match(r"^Bearer (sb_([a-z]+)_([0-9a-f]{6})_[A-Za-z0-9_-]{20,100})$", (header or "").strip())
    if not m:
        return None
    digest = _digest(m.group(1))
    k = next((k for k in _load(data_dir) if k["id"] == m.group(3)), None)
    if not k or not hmac.compare_digest(k["hash"], digest) or k["right"] != m.group(2):
        return None
    if k.get("expires_at") and k["expires_at"] < _iso(_now()):
        return None
    return k


def note_use(data_dir, k):
    """last_used_at, written at most once a minute per key to spare the disk."""
    now = time.time()
    with _lock:
        if now - _used.get(k["id"], 0) < 60:
            return
        _used[k["id"]] = now
    keys = _load(data_dir)
    for item in keys:
        if item["id"] == k["id"]:
            item["last_used_at"] = _iso(_now())
    _save(data_dir, keys)


def take_token(kid, now=None):
    """The token bucket: (allowed, seconds to wait, tokens left)."""
    now = now or time.monotonic()
    with _lock:
        tokens, last = _buckets.get(kid, (PER_MINUTE, now))
        tokens = min(PER_MINUTE, tokens + (now - last) * PER_MINUTE / 60)
        if tokens < 1:
            _buckets[kid] = (tokens, now)
            return False, max(1, int((1 - tokens) * 60 / PER_MINUTE) + 1), 0
        _buckets[kid] = (tokens - 1, now)
        return True, 0, int(tokens - 1)


# Audit log (AS9): JSON lines, 5 files of 1 MB ----------------------------------------------------------------------

def audit(data_dir, what, **details):
    folder = os.path.join(data_dir, "logs")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "audit.jsonl")
    try:
        if os.path.getsize(path) > 1_000_000:
            for i in range(4, 0, -1):
                if os.path.exists(f"{path}.{i}"):
                    os.replace(f"{path}.{i}", f"{path}.{i + 1}")
            os.replace(path, f"{path}.1")
    except OSError:
        pass
    line = json.dumps({"time": _iso(_now()), "what": what, **{k: v for k, v in details.items() if not SECRET_NAMES.search(k)}})
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "a", encoding="utf-8") as f:
        f.write(line + "\n")


# Answers ------------------------------------------------------------------------------------------------------

def scrub(value):
    """Removes anything that looks like a secret from an answer taken from Starboard's own data (AS7)."""
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if not SECRET_NAMES.search(str(k))}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def page(items, query):
    """Cursor paging (A7): limit 1 to 200 (50 by default) and an opaque cursor. Returns (items, next_cursor)."""
    try:
        limit = int((query.get("limit") or ["50"])[0])
    except ValueError:
        raise ValueError("limit must be a whole number from 1 to 200") from None
    if not 1 <= limit <= 200:
        raise ValueError("limit must be a whole number from 1 to 200")
    cursor = (query.get("cursor") or [""])[0]
    start = 0
    if cursor:
        try:
            start = int(base64.urlsafe_b64decode(cursor.encode() + b"==").decode().removeprefix("o:"))
        except (ValueError, UnicodeDecodeError):
            raise ValueError("That cursor is not one Starboard gave") from None
    chunk = items[start:start + limit]
    nxt = base64.urlsafe_b64encode(f"o:{start + limit}".encode()).decode().rstrip("=") if start + limit < len(items) else None
    return chunk, nxt


def app_item(s):
    """An app on the dashboard, allow-listed (AS7)."""
    return {"id": s["id"], "name": s["name"], "type": s["type"], "group": s.get("group") or "", "enabled": s.get("enabled", True),
            "url": s.get("link") or s.get("url") or "", "api_key_set": bool(s.get("api_key"))}


def request_id(given):
    return given if given and re.match(r"^[A-Za-z0-9._-]{1,64}$", given) else uuid.uuid4().hex


def etag(raw):
    return 'W/"' + hashlib.sha256(raw).hexdigest()[:20] + '"'


def spec():
    with open(SPEC, encoding="utf-8") as f:
        return json.load(f)


# Events (A15): a ring of the last 200, kept in memory, and the streams that read it -------------------------------
# Published by plugin_life.emit (apps going down and up; with a stream open, new items, finished downloads and
# playback starting, from the checks the plug-in clock already makes) and by the watch's alerts. Each event has the
# scope a key needs to hear it, the same as the plug-in permission that covers it.

EVENT_SCOPES = {"app.down": "apps", "app.up": "apps", "item.added": "media", "playback.started": "media",
                "download.finished": "downloads", "alert.raised": "system", "alert.cleared": "system"}
_events = collections.deque(maxlen=200)
_event_cond = threading.Condition()
_event_state = {"seq": 0, "streams": 0}


def publish(event, data=None):
    """Adds one event to the ring and wakes the streams. Cheap: nothing is sent when no stream is open."""
    scope = EVENT_SCOPES.get(event)
    if not scope:
        return
    with _event_cond:
        _event_state["seq"] += 1
        _events.append({"specversion": "1.0", "id": str(_event_state["seq"]), "type": "starboard." + event,
                        "source": "/api/v1/events", "time": _iso(_now()), "scope": scope, "data": scrub(data or {})})
        _event_cond.notify_all()


def streams_open():
    return _event_state["streams"]


def _scoped(k, scope):
    """True when key k may read what needs `scope`. No scopes means everything only for keys people make themselves.
    A plug-in's key reads exactly what was approved (P8), so a plug-in with no read permission reads nothing,
    however old its key (DASH-330 review)."""
    if not scope:
        return True
    exact = str(k.get("name", "")).startswith("Plug-in: ") or scope in EXPLICIT_SCOPES
    return not (k.get("scopes") or exact) or scope in (k.get("scopes") or [])


def _stream(h, k, base):
    """GET /api/v1/events: text/event-stream until the client goes, or an hour. Returns False when 8 are open."""
    from .server import SECURITY_HEADERS
    with _event_cond:
        if _event_state["streams"] >= MAX_STREAMS:
            return False
        _event_state["streams"] += 1
        last = _event_state["seq"]
    try:
        try:
            given = int(h.headers.get("Last-Event-ID") or -1)
        except ValueError:
            given = -1
        if 0 <= given <= last:
            last = given  # resume: what is still in the ring after that id comes first
        clock = getattr(h.app, "plugin_clock", None)
        if clock:
            clock.ensure()  # new items, finished downloads and playback are checked while a stream is open
        h.close_connection = True
        h.send_response(200)
        for name, value in SECURITY_HEADERS.items():
            h.send_header(name, value)
        for name, value in {**base, "Content-Type": "text/event-stream; charset=utf-8", "Connection": "close",
                            "X-Accel-Buffering": "no"}.items():
            h.send_header(name, value)
        h.end_headers()
        h.wfile.write(b"retry: 10000\n: open\n\n")
        h.wfile.flush()
        end = time.monotonic() + STREAM_SECONDS
        while time.monotonic() < end:
            with _event_cond:
                _event_cond.wait_for(lambda: _event_state["seq"] > last, timeout=KEEP_ALIVE)
                fresh = [e for e in _events if int(e["id"]) > last]
                last = _event_state["seq"]
            out = "".join(f"id: {e['id']}\nevent: {e['type']}\ndata: "
                          + json.dumps({n: v for n, v in e.items() if n != "scope"}, separators=(",", ":")) + "\n\n"
                          for e in fresh if _scoped(k, e["scope"]))
            h.wfile.write((out or ": keep-alive\n\n").encode())
            h.wfile.flush()
    except OSError:
        pass  # the client went away
    finally:
        with _event_cond:
            _event_state["streams"] -= 1
    return True


# Idempotency-Key (A11) ----------------------------------------------------------------------------------------------

def _remembered(where):
    with _lock:
        found = _done.get(where)
        if found and time.time() - found[0] < 86400:
            return found
        _done.pop(where, None)
        return None


def _remember(where, status, raw):
    with _lock:
        _done[where] = (time.time(), status, raw)
        while len(_done) > IDEMPOTENCY_KEEP:
            _done.popitem(last=False)


# Routes: (pattern, scope, how long the answer stays fresh in seconds, handler) -----------------------------------
# Each handler is given (handler, match, query) and returns the body. Handlers use the same functions and caches as
# server.py's own answers, so the API and the pages always agree.

def _next(token):
    return base64.urlsafe_b64encode(token.encode()).decode().rstrip("=")


def _month_calendar(cfg, month):
    """The month view, as the Coming up page asks for it: its own saved answer, at most 3 months kept."""
    from . import services
    start = month - dt.timedelta(days=7)
    end = (month + dt.timedelta(days=32)).replace(day=1) + dt.timedelta(days=7)
    key = f"calendar-month-{month:%Y-%m}"
    with services._cache_lock:
        months = sorted(k for k in services._cache if k.startswith("calendar-month-") and k != key)
    if len(months) >= 3:
        services.forget(*months[:len(months) - 2])
    return services.cached(key, 600, lambda: services.calendar(cfg.data["services"], start=start, end=end))


def _reelix(h):
    from . import library
    reelix = library.reelix_of(h.app.config.data["services"])
    if not reelix:
        raise NotReady("Add Reelix in Settings, Manage apps, with its key")
    return reelix


def routes():
    from . import activity, containers, library, services, stack, sysinfo

    def root(h, m, q):
        return {"api_version": API_VERSION, "starboard_version": h.app.version,
                "links": {"openapi": "/api/v1/openapi.json", "me": "/api/v1/me", "apps": "/api/v1/apps", "events": "/api/v1/events", "mcp": "/api/v1/mcp"},
                "deprecations": deprecations.public()}

    def me(h, m, q):
        return public(h.api_key)

    def apps(h, m, q):
        items, nxt = page([app_item(s) for s in h.app.config.data["services"]], q)
        return {"items": items, "next_cursor": nxt}

    def app_one(h, m, q):
        s = h.app.config.service(m.group(1))
        if not s:
            raise LookupError("No app with that id")
        return app_item(s)

    def status(h, m, q):
        cfg = h.app.config
        rows = services.cached("status", 15, lambda: services.status_all(cfg.data["services"]))
        rows = [{k: v for k, v in r.items() if k != "check_every"} for r in rows]  # the dashboard's own detail (DASH-66)
        items, nxt = page(scrub(rows), q)
        return {"items": items, "next_cursor": nxt}

    def health(h, m, q):
        cfg = h.app.config
        out = services.cached("health", 300, lambda: services.health(cfg.data["services"], stack.chosen_keys(h.app.data_dir), h.app.data_dir))
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"items": items, "errors": scrub(out.get("errors") or []), "next_cursor": nxt}

    def downloads(h, m, q):
        cfg = h.app.config
        out = services.cached("queue", 10, lambda: services.queue(cfg.data["services"]))
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"items": items, "errors": scrub(out.get("errors") or []), "next_cursor": nxt}

    def download_issues(h, m, q):  # DASH-434 (API 1.3.0): asked only when called, at most every 10 seconds
        from . import queue_issues
        out = queue_issues.export(h.app)
        return {"generated_at": out["generated_at"], "count": out["count"], "apps_asked": out["apps_asked"],
                "items": scrub(out["items"]), "errors": scrub(out["errors"]), "markdown": out["markdown"]}

    def recent(h, m, q):
        cfg = h.app.config
        out = services.cached("recent", 300, lambda: services.recent(cfg.data["services"]))
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"items": items, "next_cursor": nxt}

    def playing(h, m, q):
        cfg = h.app.config
        out = services.cached("jellyfin", 20, lambda: services.jellyfin(cfg.data["services"]))
        return {"configured": bool(out.get("configured")), "items": scrub(out.get("playing") or [])}

    def system(h, m, q):
        snap = sysinfo.snapshot(h.app.disks)
        return {k: scrub(snap.get(k)) for k in ("cpus", "load", "memory", "disks", "uptime_seconds") if k in snap}

    # Added in 1.1.0 (DASH-274, DASH-246): the other read rows of the capabilities list.

    def calendar(h, m, q):
        cfg = h.app.config
        month = (q.get("month") or [""])[0]
        if month:
            try:
                first = dt.date.fromisoformat(month + "-01") if re.match(r"^\d{4}-\d{2}$", month) else None
            except ValueError:
                first = None
            if not first:
                raise ValueError("Send the month as YYYY-MM, such as 2026-11")
            out = _month_calendar(cfg, first)
        else:
            days = cfg.data["upcoming_days"]
            out = services.cached(f"calendar-{days}", 600, lambda: services.calendar(cfg.data["services"], days))
        rows = scrub(out.get("items") or [])
        if not cfg.data["show_posters"]:
            rows = [{**r, "image": ""} for r in rows]
        items, nxt = page(rows, q)
        return {"items": items, "errors": scrub(out.get("errors") or []), "next_cursor": nxt}

    def requests(h, m, q):
        cfg = h.app.config
        pending = (q.get("pending") or [""])[0] in ("true", "1")
        out = services.cached(f"requests-{pending}", 20, lambda: services.requests(cfg.data["services"], pending))
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"configured": bool(out.get("configured")), "pending": int(out.get("pending") or 0), "items": items, "next_cursor": nxt}

    def transfer(h, m, q):
        cfg = h.app.config
        out = services.cached("transfer", 5, lambda: services.transfer(cfg.data["services"]))
        vpn = [{k: v for k, v in r.items() if k != "ip"} for r in scrub(out.get("vpn") or [])]  # not the address
        return {"clients": scrub(out.get("clients") or []), "vpn": vpn, "errors": scrub(out.get("errors") or [])}

    def download_hours(h, m, q):
        return scrub(h.app.schedule.status())

    def history(h, m, q):
        cfg = h.app.config
        which = (q.get("which") or ["all"])[0]
        if which not in activity.FILTERS:
            raise ValueError("Choose which from all, grabbed, imported or failed")
        number = 1
        cursor = (q.get("cursor") or [""])[0]
        if cursor:
            try:
                number = int(base64.urlsafe_b64decode(cursor.encode() + b"==").decode().removeprefix("p:"))
            except (ValueError, UnicodeDecodeError):
                raise ValueError("That cursor is not one Starboard gave") from None
            if not 1 <= number <= 10000:
                raise ValueError("That cursor is not one Starboard gave")
        _reelix(h)
        out = services.cached(f"history-{which}-{number}", 60, lambda: activity.history(cfg.data["services"], which, number, cfg.data))
        more = out["page"] * out["page_size"] < out["total"]
        return {"items": scrub(out["items"]), "next_cursor": _next(f"p:{number + 1}") if more else None}

    def library_overview(h, m, q):
        cfg = h.app.config
        reelix = _reelix(h)
        library.used(cfg.data_dir, "", lambda: library.reelix_of(cfg.data["services"]))
        for t in library.TABS:  # tabs never opened yet are built in the background, as the page does
            if not os.path.exists(library._path(cfg.data_dir, t)):
                library._background(cfg.data_dir, reelix, t)
        return scrub(library.overview(cfg.data_dir, reelix))

    def library_search(h, m, q):
        cfg = h.app.config
        words = (q.get("q") or [""])[0].strip()
        if not 1 <= len(words) <= 120:
            raise ValueError("Send q, from 1 to 120 letters")
        reelix = _reelix(h)
        items, nxt = page(scrub(library.search_library(cfg.data_dir, words, reelix=reelix)), q)
        return {"items": items, "next_cursor": nxt}

    def library_status(h, m, q):
        return library.status(h.app.config.data_dir)

    def uptime(h, m, q):
        cfg = h.app.config
        rows = [{"id": app_id, **row} for app_id, row in h.app.watch.uptime(cfg.data["services"]).items()]
        items, nxt = page(scrub(rows), q)
        return {"enabled": bool(cfg.data["watch"]["enabled"]), "items": items, "next_cursor": nxt}

    def app_updates(h, m, q):
        cfg = h.app.config
        out = services.cached("app-updates", 600, lambda: services.app_updates(cfg.data["services"]))
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"items": items, "errors": scrub(out.get("errors") or []), "next_cursor": nxt}

    def numbers(h, m, q):
        cfg = h.app.config
        found = services.cached("numbers", 60, lambda: services.numbers(cfg.data["services"]))
        items, nxt = page(scrub([{"id": app_id, "parts": parts} for app_id, parts in found.items()]), q)
        return {"items": items, "next_cursor": nxt}

    def container_list(h, m, q):
        if not containers.available():
            return {"available": False, "items": [], "next_cursor": None}
        out = containers.apps(h.app.config.data["services"])
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"available": True, "checked_at": out.get("checked_at"), "restored": bool(out.get("restored")), "items": items, "next_cursor": nxt}

    def version(h, m, q):
        cfg = h.app.config
        return {"current": h.app.version, "latest": h.app.latest_release(), "repo": h.app.repo,
                "since": (cfg.data.get("version_since") or {}).get("since")}

    def system_history(h, m, q):
        hours = {"1": 1, "6": 6, "24": 24}.get((q.get("hours") or ["1"])[0])
        if not hours:
            raise ValueError("Choose hours from 1, 6 or 24")
        hist = h.app.history
        return {"hours": hours, "interval": hist.INTERVAL if hist else int(h.app.config.data["performance"].get("history_every", 300)),
                "points": hist.get(hours) if hist else []}

    def log_entries(h, m, q):
        """Starboard's own log, newest first, for an AI assistant or a script (DASH-76): with the report's redaction on
        top of what each line had taken out when written (addresses, hosts, emails, keys, the site's and computer's
        names). Only for keys that ticked Logs."""
        import socket
        from . import logs
        level = (q.get("level") or ["all"])[0]
        if level not in ("all", "problems"):
            raise ValueError("Choose level from all or problems")
        words = [h.app.config.data.get("site_name", ""), socket.gethostname()]
        rows = [{"time": _iso(dt.datetime.fromtimestamp(e.get("t") or 0, dt.timezone.utc).replace(microsecond=0)),
                 "level": e.get("level", ""), "area": e.get("area", ""), "message": logs.redact(e.get("message", ""), words)[:2000]}
                for e in h.app.log.read(level, (q.get("q") or [""])[0][:100], limit=1000)]
        items, nxt = page(rows, q)
        return {"items": items, "next_cursor": nxt}

    def log_limits(h, m, q):
        """The log limits, what the logs take now and the apps' own limit from Docker (DASH-451)."""
        from . import app_logs, logs
        return logs.limits_answer(h.app, app_logs.limits())

    def update_list(h, m, q):
        """What can be updated (DASH-424), from what Starboard already knows: nothing is fetched to answer."""
        from . import update_runs
        items, nxt = page(scrub(update_runs.targets(h.app)), q)
        running = next((r for r in update_runs.recent(h.app) if r["state"] == "running"), None)
        return {"items": items, "running": update_runs.public(running) if running else None, "next_cursor": nxt}

    def update_all_plan(h, m, q):
        """What Install all updates would do now (DASH-454): in order, and what is held back for the owner."""
        from . import update_batch
        return update_batch.plan(h.app)

    def update_runs_list(h, m, q):
        from . import update_runs
        items, nxt = page([update_runs.public(r) for r in update_runs.recent(h.app)], q)
        return {"items": items, "next_cursor": nxt}

    def update_run(h, m, q):
        from . import update_runs
        return update_runs.public(update_runs.get(h.app, m.group(1)))

    def backup_copies_get(h, m, q):  # DASH-452 (API 1.6.0): where copies go, the last copy and the last Test connection
        from . import backup_copies
        p = backup_copies.public(h.app.data_dir)
        places = [{k: d.get(k) for k in ("id", "title", "kind", "kind_words", "enabled", "where", "where_words", "service", "keep", "keep_settings",
                                          "status", "tested", "state_word", "shape")} for d in p.get("destinations") or []]
        from . import settings_zip
        return scrub({**{k: p.get(k) for k in ("kind", "where", "where_words", "service", "keep", "status", "tested")},
                      "destinations": places, "safe": p.get("safe"), "settings_zip": settings_zip.overview(h.app.data_dir)})

    def extras(h, m, q):
        rows = [{k: r.get(k) for k in ("key", "title", "what", "enabled", "started", "finished", "state", "summary", "needs")}
                for r in h.app.jobs.status().get("jobs") or [] if r.get("key") in EXTRA_JOBS]
        return {"items": scrub(rows)}

    return [
        (r"^/api/v1/?$", None, 3600, root),
        (r"^/api/v1/me$", None, 60, me),
        (r"^/api/v1/apps$", "apps", 60, apps),
        (r"^/api/v1/apps/([A-Za-z0-9_-]{1,64})$", "apps", 60, app_one),
        (r"^/api/v1/status$", "apps", 15, status),
        (r"^/api/v1/health$", "apps", 300, health),
        (r"^/api/v1/downloads$", "downloads", 10, downloads),
        (r"^/api/v1/downloads/issues$", "downloads", 10, download_issues),
        (r"^/api/v1/recent$", "media", 300, recent),
        (r"^/api/v1/playing$", "media", 20, playing),
        (r"^/api/v1/system$", "system", 10, system),
        (r"^/api/v1/calendar$", "media", 600, calendar),
        (r"^/api/v1/requests$", "requests", 20, requests),
        (r"^/api/v1/transfer$", "downloads", 5, transfer),
        (r"^/api/v1/download-hours$", "downloads", 30, download_hours),
        (r"^/api/v1/history$", "downloads", 60, history),
        (r"^/api/v1/library$", "library", 60, library_overview),
        (r"^/api/v1/library/search$", "library", 60, library_search),
        (r"^/api/v1/library/status$", "library", 60, library_status),
        (r"^/api/v1/uptime$", "apps", 60, uptime),
        (r"^/api/v1/app-updates$", "apps", 600, app_updates),
        (r"^/api/v1/numbers$", "apps", 60, numbers),
        (r"^/api/v1/containers$", "apps", 60, container_list),
        (r"^/api/v1/version$", "system", 3600, version),
        (r"^/api/v1/system/history$", "system", 60, system_history),
        (r"^/api/v1/extras$", "media", 30, extras),
        (r"^/api/v1/backup/copies$", "system", 30, backup_copies_get),
        (r"^/api/v1/logs$", "logs", 30, log_entries),
        (r"^/api/v1/logs/limits$", "logs", 30, log_limits),
        (r"^/api/v1/updates$", "updates", 30, update_list),
        (r"^/api/v1/updates/all$", "updates", 60, update_all_plan),
        (r"^/api/v1/updates/runs$", "updates", 5, update_runs_list),
        (r"^/api/v1/updates/runs/([0-9a-f]{12})$", "updates", 2, update_run),
        (r"^/api/v1/events$", None, 0, None),  # the event stream: answered by _stream, each event by its own scope
    ]


# Alerts from a plug-in (API 1.8.0, plug-in API 1.17) -----------------------------------------------------------------
# The route's "scope" is PLUGIN_ONLY: not a key scope anyone ticks, but "the plug-in's own key, while the plug-in is
# active and was approved alerts:send". Any other key gets 404 (AS6), as for a scope it does not have.

PLUGIN_ONLY = "plugin"
ALERT_KEY = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
ALERT_LEVELS = ("problem", "warning", "info")
ALERTS_AN_HOUR = 30
_raised = {}  # plug-in id -> times of its new alerts in the last hour


def plugin_of_key(data_dir, k, permission):
    """{id, name} of the active plug-in whose own key `k` is and whose approved permissions include `permission`, or
    None. The key is known by the id kept in the plug-in's state.json when it was added (or given a new key)."""
    if not str(k.get("name", "")).startswith("Plug-in: "):
        return None
    from . import plugins_admin
    for p in plugins_admin.basics(data_dir):
        if p["state"] != "enabled":
            continue
        where = plugins_admin.folder(data_dir, p["id"])
        st = plugins_admin._read_kept(os.path.join(where, "state.json"), {}) or {}
        if st.get("key_id") != k["id"]:
            continue
        m = plugins_admin._read_kept(os.path.join(where, "manifest.json"), {}) or {}
        return {"id": p["id"], "name": p["name"] or p["id"]} if permission in (m.get("permissions") or []) else None
    return None


def _one_line(b, name, most, required=False):
    value = b.get(name)
    if value is None or value == "":
        if required:
            raise ValueError(f"Send {name}, up to {most} characters")
        return ""
    if not isinstance(value, str) or len(value) > most:
        raise ValueError(f"{name} must be words, up to {most} characters")
    return value


def plugin_alert(app, plugin, b):
    """Raises or clears one of a plug-in's alerts through Starboard's watch, so it is sent once until cleared, to the
    same channel, as the same alert.raised and alert.cleared events and in the same log. True when it was sent."""
    key = b.get("key")
    if not isinstance(key, str) or not ALERT_KEY.match(key):
        raise ValueError("Send key, 1 to 80 letters, numbers, dots, colons, underscores or hyphens, such as check-router")
    state = b.get("state")
    if state not in ("raised", "cleared"):
        raise ValueError("Send state: raised or cleared")
    title = _one_line(b, "title", 120, required=state == "raised")
    if re.search(r"[\x00-\x1f\x7f]", title):
        raise ValueError("title must be one line, with no line breaks")
    message = re.sub(r"[\x00-\x09\x0b-\x1f\x7f]", " ", _one_line(b, "message", 500))
    level = b.get("level", "problem")
    if level not in ALERT_LEVELS:
        raise ValueError("Send level: problem, warning or info")
    watch = app.watch
    full = f"plugin:{plugin['id']}:{key}"
    with watch.lock:
        if not watch.settings().get("enabled"):  # alerts are off, as they are for Starboard's own
            if state == "cleared":
                watch.state["alerted"].pop(full, None)
                watch._save()
            return False
        if state == "cleared":
            sent = watch.clear(full, title or f"All clear from {plugin['name']}", f"{plugin['name']}: {message or key}")
        elif full in watch.state["alerted"]:
            return False  # already raised: not sent again, and not counted
        else:
            now = time.monotonic()
            with _lock:
                times = [t for t in _raised.get(plugin["id"], []) if now - t < 3600]
                if len(times) >= ALERTS_AN_HOUR:
                    _raised[plugin["id"]] = times
                    raise RateLimited(f"Up to {ALERTS_AN_HOUR} new alerts an hour for each plug-in", int(3600 - (now - times[0])) + 1)
                _raised[plugin["id"]] = times + [now]
            sent = watch.alert(full, title, f"{plugin['name']}: {message}" if message else plugin["name"], level)
        watch._save()
    return bool(sent)


EXTRA_JOBS = ("livetv", "import", "defaults", "listening")
QUEUE_ACTIONS = ("remove", "block", "block-search", "import", "ignore")


# Writes: (pattern, method, scope, handler), each needing the manage right. A handler is given (handler, match,
# query, body) and returns (status, body). These are the everyday actions of the pages (the "manage" rows of
# STARBOARD-CAPABILITIES-2026-11-09.md) that call only apps already set up and change no setting.

def actions():
    from . import containers, library, logs, services, watch

    def download_action(h, m, q, b):
        cfg = h.app.config
        service = cfg.service(str(b.get("app_id", "")))
        action = str(b.get("action", ""))
        if action not in QUEUE_ACTIONS:
            raise ValueError("Choose action from remove, block, block-search, import or ignore")
        if not str(b.get("id", "")).isdigit():
            raise ValueError("Send id, the download's id from /api/v1/downloads")
        radio = next((r for r in services.reelix_native(cfg.data["services"]) if service and r["id"] == service["id"]), None)
        if not service or (service["type"] not in ("sonarr", "radarr", "lidarr", "readarr") and not radio):
            raise LookupError("No download app with that app_id")
        if radio:
            services.radio_queue_action(radio, int(b["id"]), action)
        else:
            services.queue_action(service, int(b["id"]), action, cfg.data["services"])
        logs.event("info", "downloads", f"{action} for a download in {service['name']}, by the API key {h.api_key['name']}")
        from . import queue_issues
        queue_issues.note_action(h.app.data_dir, service["id"], b["id"], action, f"by the API key {h.api_key['name']}")
        return 200, {"ok": True}

    def hours_action(h, m, q, b):
        action = str(b.get("action", ""))
        if action not in ("resume", "pause", "follow"):
            raise ValueError("Choose action from resume, pause or follow")
        return 200, scrub(h.app.schedule.act(action))

    def request_action(h, m, q, b):
        services.request_action(h.app.config.data["services"], m.group(1), m.group(2), str(b.get("reason") or "")[:500])
        services.forget()
        logs.event("info", "requests", f"Request {m.group(1)}: {m.group(2)}, by the API key {h.api_key['name']}")
        return 200, {"ok": True}

    def library_refresh(h, m, q, b):
        tab = str(b.get("tab", ""))
        if tab not in library.TABS:
            raise ValueError("Choose tab from " + ", ".join(library.TABS))
        library._background(h.app.config.data_dir, _reelix(h), tab)
        return 202, {"accepted": True, "status": "/api/v1/library/status"}

    def containers_check(h, m, q, b):
        if not containers.available():
            return 200, {"available": False, "items": []}
        out = containers.check(h.app.config.data["services"])
        return 200, {"available": True, "checked_at": out.get("checked_at"), "restored": False, "items": scrub(out.get("items") or [])}

    def alerts_test(h, m, q, b):
        cfg = h.app.config
        watch.send(cfg.data["watch"]["channel"], f"Test from {cfg.data['site_name']}", "Alerts from Starboard reach you here.", "info")
        return 200, {"ok": True}

    def update_start(h, m, q, b):
        """Starts an update (DASH-424): only to the version Starboard already knows, never from an address."""
        from . import update_runs
        from . import services
        try:
            run = update_runs.start(h.app, str(b.get("target") or ""), by=f"api:{h.api_key['name']}")
        except update_runs.Busy as e:
            raise Conflict(str(e), "update_running") from None
        except update_runs.Refused as e:
            raise Conflict(str(e), "cannot_update") from None
        except OSError as e:  # the plug-in's new manifest could not be read from its catalogue
            raise services.ServiceError(f"The new version could not be read: {e}") from None
        logs.event("info", "updates", f"Update of {run['name']} to {run['to']} started by the API key {h.api_key['name']}")
        return 202, {"accepted": True, "run": update_runs.public(run), "status": f"/api/v1/updates/runs/{run['id']}"}

    def update_rollback(h, m, q, b):
        from . import update_runs
        try:
            run = update_runs.rollback(h.app, str(b.get("target") or ""), by=f"api:{h.api_key['name']}")
        except update_runs.Busy as e:
            raise Conflict(str(e), "update_running") from None
        except update_runs.Refused as e:
            raise Conflict(str(e), "cannot_update") from None
        logs.event("info", "updates", f"Roll back of {run['name']} to {run['to']} started by the API key {h.api_key['name']}")
        return 202, {"accepted": True, "run": update_runs.public(run), "status": f"/api/v1/updates/runs/{run['id']}"}

    def log_limits_set(h, m, q, b):
        """Changes the log limits (DASH-451) and what is shown (DASH-534): keep_days, max_mb, show_lines and alerts_only,
        from the same choices as the page."""
        from .config import ConfigError
        wanted = {k: b[k] for k in ("keep_days", "max_mb", "show_lines", "alerts_only") if k in b}
        if not wanted:
            raise ValueError("Send keep_days, max_mb, show_lines or alerts_only")
        try:
            h.app.config.update_general({"logs": wanted})
        except ConfigError as e:
            raise ValueError(str(e)) from None
        logs.event("info", "settings", f"Log limits changed by the API key {h.api_key['name']}: "
                   + ", ".join(f"{k} {v}" for k, v in sorted(wanted.items())))
        pruned = h.app.log.prune()
        return 200, {**logs.limits_answer(h.app), "removed": pruned["removed"], "freed": pruned["freed"]}

    def log_delete(h, m, q, b):
        """Delete all logs (DASH-451): the same as the page's Delete all logs, so confirm must be true."""
        if b.get("confirm") is not True:
            raise ValueError("Send confirm: true to delete all logs")
        out = logs.delete_all(h.app, f"the API key {h.api_key['name']}")
        return 200, {**out, "summary": h.app.log.summary()}

    def update_all(h, m, q, b):
        """Install all updates (DASH-454): every waiting update as one batch, one at a time in a safe order, each with
        its own copy, check and way back. targets: only these of the plan (what the caller looked at)."""
        from . import update_batch, update_runs
        targets = b.get("targets")
        if targets is not None and not (isinstance(targets, list) and all(isinstance(t, str) for t in targets) and len(targets) <= 200):
            raise ValueError("targets must be a list of targets from GET /api/v1/updates/all")
        try:
            run = update_batch.start(h.app, by=f"api:{h.api_key['name']}", targets=targets)
        except update_runs.Busy as e:
            raise Conflict(str(e), "update_running") from None
        except update_runs.Refused as e:
            raise Conflict(str(e), "cannot_update") from None
        logs.event("info", "updates", f"Install all updates started by the API key {h.api_key['name']}")
        return 202, {"accepted": True, "run": update_runs.public(run), "status": f"/api/v1/updates/runs/{run['id']}"}

    def copies_test(h, m, q, b):
        """Test connection (DASH-452, API 1.6.0): as the page's button; at most 2 minutes."""
        from . import backup_copies
        places = [d for d in backup_copies.destinations(h.app.data_dir) if d["enabled"]]
        if not places:
            raise NotReady("Copies off this computer are not set up")
        results = {}
        for d in places:  # one failing never stops the others
            try:
                results[d["id"]] = backup_copies.test(h.app.data_dir, d["id"])
            except backup_copies.CopyError as e:
                results[d["id"]] = {"ok": False, "error": str(e)}
        first = results[places[0]["id"]]
        if len(places) == 1 and first.get("error") and "running already" in first["error"]:
            raise Conflict(first["error"], "cannot_test")
        logs.event("info", "backup", f"Test connection by the API key {h.api_key['name']}: "
                   + ", ".join(f"{backup_copies.title_of(d)} {'connected' if (results[d['id']] or {}).get('ok') else 'not connected'}" for d in places))
        return 200, {"ok": all((r or {}).get("ok") for r in results.values()), "tested": scrub(first),
                     "places": scrub([{"id": d["id"], "title": backup_copies.title_of(d), "tested": results[d["id"]]} for d in places])}

    def settings_copy(h, m, q, b):
        """Copy the server's settings zip to every place that is activated, encrypted (API 1.9.0). The server's own backup job
        calls this after it has written the zip; the file is named, never a path."""
        from . import settings_zip
        try:
            got = settings_zip.start(h.app.data_dir, str((b or {}).get("name") or "") or None)
        except settings_zip.ZipError as e:
            raise Conflict(str(e), "cannot_copy") from None
        logs.event("info", "backup", f"Server settings copy started by the API key {h.api_key['name']}")
        return 202, {"accepted": True, "status": "/api/v1/backup/copies", "settings_zip": scrub(got)}

    def extra_run(h, m, q, b):
        h.app.jobs.run_soon(m.group(1), force=True)
        return 202, {"accepted": True, "status": "/api/v1/extras"}

    def plugin_alerts(h, m, q, b):
        """A plug-in's alert (API 1.8.0, plug-in API 1.17): raised or cleared, through Starboard's own alerts."""
        return 200, {"ok": True, "sent": plugin_alert(h.app, h.api_plugin, b)}

    return [
        (r"^/api/v1/downloads/actions$", "POST", "downloads", download_action),
        (r"^/api/v1/download-hours$", "POST", "downloads", hours_action),
        (r"^/api/v1/requests/(\d{1,10})/(approve|decline)$", "POST", "requests", request_action),
        (r"^/api/v1/library/refresh$", "POST", "library", library_refresh),
        (r"^/api/v1/containers/check$", "POST", "apps", containers_check),
        (r"^/api/v1/alerts/test$", "POST", "system", alerts_test),
        (r"^/api/v1/backup/copies/test$", "POST", "system", copies_test),
        (r"^/api/v1/backup/settings-copy$", "POST", "system", settings_copy),
        (r"^/api/v1/extras/(livetv|import|defaults|listening)/run$", "POST", "media", extra_run),
        (r"^/api/v1/updates$", "POST", "updates", update_start),
        (r"^/api/v1/updates/rollback$", "POST", "updates", update_rollback),
        (r"^/api/v1/logs/limits$", "POST", "logs", log_limits_set),
        (r"^/api/v1/logs/delete$", "POST", "logs", log_delete),
        (r"^/api/v1/updates/all$", "POST", "updates", update_all),
        (r"^/api/v1/plugin/alerts$", "POST", PLUGIN_ONLY, plugin_alerts),  # the plug-in's own key (API 1.8.0)
    ]


def handle(h, method, path):
    """Answers one /api/v1 request on the server's handler `h`."""
    from . import services
    rid = request_id(h.headers.get("X-Request-Id"))
    base = {"X-Request-Id": rid, "Cache-Control": "no-store"}

    def problem(status, code, title, detail="", extra=None):
        body = {"type": PROBLEM + code, "title": title, "status": status, "detail": detail or title, "instance": rid, "code": code}
        h.send(status, json.dumps(body).encode(), "application/problem+json", {**base, **(extra or {})})

    going = deprecations.entry(method, path)  # DASH-603: a feature that is going says so on every answer, and one that is gone says 410
    if going:
        base.update(deprecations.headers(going))
        if going["removed"]:
            return problem(410, "gone", "This address has been removed", going["replacement"] or "It was removed after its notice period")
    if path == "/api/v1/openapi.json" and method == "GET":
        raw = json.dumps(spec()).encode()
        return h.send(200, raw, "application/json", {**base, "Cache-Control": "public, max-age=3600", "ETag": etag(raw)})
    mcp = path == "/api/v1/mcp"  # AI assistants (DASH-464): JSON-RPC over POST, answered by mcp.py after the key checks
    if mcp and method != "POST":
        return problem(405, "method_not_allowed", "This address takes POST only", extra={"Allow": "POST"})
    writes = [] if mcp else [a for a in actions() if re.match(a[0], path)]
    if method != "GET" and not mcp and not any(a[1] == method for a in writes):
        allow = ", ".join(sorted({a[1] for a in writes})) or "GET"
        return problem(405, "method_not_allowed", f"This address takes {allow} only", extra={"Allow": allow})
    address = h.client_address_text()
    k = find_key(h.app.data_dir, h.headers.get("Authorization"))
    if not k:
        if not h.app.limits.attempt(address):
            return problem(429, "too_many_attempts", "Too many refused keys from this address. Wait 15 minutes", extra={"Retry-After": "900"})
        audit(h.app.data_dir, "key_refused", address=address, path=path[:100])
        return problem(401, "key_needed", "Send a Starboard API key as Authorization: Bearer sb_...",
                       extra={"WWW-Authenticate": 'Bearer realm="starboard"'})
    ok, wait, left = take_token(k["id"])
    rate = {"RateLimit-Policy": f'"per-key";q={PER_MINUTE};w=60', "RateLimit": f'"per-key";r={left};t={wait}'}
    if not ok:
        return problem(429, "rate_limited", f"Up to {PER_MINUTE} requests a minute for each key", extra={**rate, "Retry-After": str(wait)})
    note_use(h.app.data_dir, k)
    h.api_key = k
    if mcp:
        from . import mcp as mcp_server
        return mcp_server.handle(h, k, base, rate, problem)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(h.path).query)
    if method != "GET":
        return _write(h, k, method, path, query, writes, base, rate, problem)
    if path == "/api/v1/events":
        if not _stream(h, k, base):
            return problem(503, "too_many_streams", f"Up to {MAX_STREAMS} event streams at once. Close one, or try again later",
                           extra={"Retry-After": "60"})
        return None
    for pattern, scope, fresh, fn in routes():
        m = re.match(pattern, path)
        if not m or not fn:
            continue
        if not _scoped(k, scope):
            return problem(404, "not_found", "Nothing here for this key")  # AS6: 404, not 403
        try:
            body = fn(h, m, query)
        except LookupError as e:
            return problem(404, "not_found", str(e))
        except ValueError as e:
            return problem(400, "bad_request", str(e))
        except NotReady as e:
            return problem(409, "not_set_up", str(e))
        except services.ServiceError as e:
            return problem(502, "app_failed", "An app did not answer", str(e)[:300])
        raw = json.dumps(body, separators=(",", ":"), default=str).encode()
        tag = etag(raw)
        headers = {**base, **rate, "ETag": tag, "Cache-Control": f"private, max-age={fresh}"}
        if body.get("next_cursor") if isinstance(body, dict) else False:
            keep = "&".join(f"{urllib.parse.quote(n)}={urllib.parse.quote(v[0])}" for n, v in query.items() if n not in ("cursor",))
            headers["Link"] = f'<{path}?{keep + "&" if keep else ""}cursor={body["next_cursor"]}>; rel="next"'
        if tag in [t.strip() for t in (h.headers.get("If-None-Match") or "").split(",")]:
            return h.send(304, b"", "application/json", headers)
        return h.send(200, raw, "application/json", headers)
    return problem(404, "not_found", "No such route in version 1 of the API")


def _write(h, k, method, path, query, writes, base, rate, problem):
    """One write: the key's scope, then its right, then the body, then the action, with an audit line (AS9)."""
    from . import services
    pattern, _, scope, fn = next(a for a in writes if a[1] == method)
    if scope == PLUGIN_ONLY:  # the one write a plug-in's read-only key may do (API 1.8.0)
        h.api_plugin = plugin_of_key(h.app.data_dir, k, "alerts:send")
        if not h.api_plugin:
            return problem(404, "not_found", "Nothing here for this key")
    elif not _scoped(k, scope):
        return problem(404, "not_found", "Nothing here for this key")
    elif k["right"] != "manage":
        return problem(403, "right_needed", "This key only reads. Make a key that may read and manage, in Settings, Security, API keys")
    idem = (h.headers.get("Idempotency-Key") or "").strip()
    if idem and not re.match(r"^[A-Za-z0-9._:-]{1,100}$", idem):
        return problem(400, "bad_request", "Idempotency-Key must be 1 to 100 letters, numbers, dots, dashes or colons")
    where = (k["id"], method, path, idem)
    if idem:
        found = _remembered(where)
        if found:
            return h.send(found[1], found[2], "application/json", {**base, **rate, "Idempotent-Replayed": "true"})
    try:
        body = h.body()
    except ValueError as e:
        large = "too large" in str(e)
        return problem(413 if large else 400, "too_large" if large else "bad_request",
                       "Send a JSON object of up to 64 KB" if large else "Send a JSON object, such as {}")
    status, code, out, extra = 500, "", None, None
    try:
        status, out = fn(h, re.match(pattern, path), query, body)
    except LookupError as e:
        status, code, title = 404, "not_found", str(e)
    except ValueError as e:
        status, code, title = 400, "bad_request", str(e)
    except NotReady as e:
        status, code, title = 409, "not_set_up", str(e)
    except Conflict as e:
        status, code, title = 409, e.code, str(e)
    except RateLimited as e:
        status, code, title, extra = 429, "rate_limited", str(e), {"Retry-After": str(e.wait)}
    except services.ServiceError as e:
        status, code, title = 502, "app_failed", "An app did not answer: " + str(e)[:300]
    audit(h.app.data_dir, "api_write", key_id=k["id"], method=method, path=path[:100], status=status)
    if code:
        return problem(status, code, title, extra=extra)
    raw = json.dumps(out, separators=(",", ":"), default=str).encode()
    if idem:
        _remember(where, status, raw)
    return h.send(status, raw, "application/json", {**base, **rate})
