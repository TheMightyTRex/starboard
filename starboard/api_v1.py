"""Starboard's public API, version 1 (DASH-274): /api/v1/, for other apps, scripts, AI assistants and plug-ins.
Read only first. Rules from starboard/DEVELOPER-BEST-PRACTICE-2026-11-09.md (A1 to A19, AS1 to AS18):

- Its own keys, separate from the browser's session (AS1): sb_read_<id>_<secret>, shown once, stored as SHA-256
  (AS2, AS3), sent only as "Authorization: Bearer" (AS4); a right ("read" for now) and optional scopes (AS5);
  optional expiry, last used at most once a minute, revoke (AS8); an audit line for each change and each refused
  key (AS9); refused keys count towards the sign-in lockout per address (AS10). No cookies, so no CSRF and no CORS.
- Answers: JSON, snake_case, RFC 3339 times; errors as RFC 9457 problem details (A6); lists with limit and an
  opaque cursor (A7); weak ETags and 304 (A9) with Cache-Control matching how often the answer changes; a token
  bucket per key, 120 a minute, with Retry-After and RateLimit headers (A13); X-Request-Id on every answer (A18).
- Never a secret in an answer (AS7): app keys show as set or not set.
- Described in starboard/openapi.json, served at /api/v1/openapi.json; a test fails when a route and the
  description differ (A4, AS17).
"""
import base64
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

API_VERSION = "1.0.0"
KEYS_FILE = "api-keys.json"
RIGHTS = ("read",)  # "manage" and "admin" come with the first write routes
SCOPES = ("apps", "downloads", "media", "system")
PER_MINUTE = 120
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "openapi.json")
PROBLEM = "https://github.com/TheMightyTRexUK/starboard/blob/main/docs/api/errors.md#"
SECRET_NAMES = re.compile(r"(api_?key|token|password|secret|cookie|authorization)", re.I)
_lock = threading.Lock()
_buckets = {}
_used = {}


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
        raise ValueError("Keys can only read for now")
    scopes = sorted({str(s) for s in (scopes or [])})
    if any(s not in SCOPES for s in scopes):
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


# Routes: (pattern, scope, how long the answer stays fresh in seconds, handler) -----------------------------------
# Each handler is given (handler, match, query) and returns (status, body). Handlers live in server.py's own
# answers, so the API and the pages always agree.

def routes():
    from . import services, stack, sysinfo

    def root(h, m, q):
        return {"api_version": API_VERSION, "starboard_version": h.app.version,
                "links": {"openapi": "/api/v1/openapi.json", "me": "/api/v1/me", "apps": "/api/v1/apps"}}

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
        items, nxt = page(scrub(rows), q)
        return {"items": items, "next_cursor": nxt}

    def health(h, m, q):
        cfg = h.app.config
        out = services.cached("health", 300, lambda: services.health(cfg.data["services"], stack.chosen_keys(h.app.data_dir)))
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"items": items, "errors": scrub(out.get("errors") or []), "next_cursor": nxt}

    def downloads(h, m, q):
        cfg = h.app.config
        out = services.cached("queue", 10, lambda: services.queue(cfg.data["services"]))
        items, nxt = page(scrub(out.get("items") or []), q)
        return {"items": items, "errors": scrub(out.get("errors") or []), "next_cursor": nxt}

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

    return [
        (r"^/api/v1/?$", None, 3600, root),
        (r"^/api/v1/me$", None, 60, me),
        (r"^/api/v1/apps$", "apps", 60, apps),
        (r"^/api/v1/apps/([A-Za-z0-9_-]{1,64})$", "apps", 60, app_one),
        (r"^/api/v1/status$", "apps", 15, status),
        (r"^/api/v1/health$", "apps", 300, health),
        (r"^/api/v1/downloads$", "downloads", 10, downloads),
        (r"^/api/v1/recent$", "media", 300, recent),
        (r"^/api/v1/playing$", "media", 20, playing),
        (r"^/api/v1/system$", "system", 10, system),
    ]


def handle(h, method, path):
    """Answers one /api/v1 request on the server's handler `h`."""
    rid = request_id(h.headers.get("X-Request-Id"))
    base = {"X-Request-Id": rid, "Cache-Control": "no-store"}

    def problem(status, code, title, detail="", extra=None):
        body = {"type": PROBLEM + code, "title": title, "status": status, "detail": detail or title, "instance": rid, "code": code}
        h.send(status, json.dumps(body).encode(), "application/problem+json", {**base, **(extra or {})})

    if path == "/api/v1/openapi.json" and method == "GET":
        raw = json.dumps(spec()).encode()
        return h.send(200, raw, "application/json", {**base, "Cache-Control": "public, max-age=3600", "ETag": etag(raw)})
    if method != "GET":
        return problem(405, "method_not_allowed", "Version 1 of the API only reads for now", extra={"Allow": "GET"})
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
    query = urllib.parse.parse_qs(urllib.parse.urlparse(h.path).query)
    for pattern, scope, fresh, fn in routes():
        m = re.match(pattern, path)
        if not m:
            continue
        if scope and k.get("scopes") and scope not in k["scopes"]:
            return problem(404, "not_found", "Nothing here for this key")  # AS6: 404, not 403
        try:
            body = fn(h, m, query)
        except LookupError as e:
            return problem(404, "not_found", str(e))
        except ValueError as e:
            return problem(400, "bad_request", str(e))
        raw = json.dumps(body, separators=(",", ":"), default=str).encode()
        tag = etag(raw)
        headers = {**base, **rate, "ETag": tag, "Cache-Control": f"private, max-age={fresh}"}
        if body.get("next_cursor") if isinstance(body, dict) else False:
            headers["Link"] = f'<{path}?cursor={body["next_cursor"]}>; rel="next"'
        if tag in [t.strip() for t in (h.headers.get("If-None-Match") or "").split(",")]:
            return h.send(304, b"", "application/json", headers)
        return h.send(200, raw, "application/json", headers)
    return problem(404, "not_found", "No such route in version 1 of the API")
