"""Talking to the apps: status, search, add, queue, calendar and health.

API keys stay on the server. Every call goes to an address an administrator saved in Settings.
"""

import collections
import datetime as dt
import base64
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import logs, posters
from .config import SERVICE_TYPES

TIMEOUT = 8

# The last checks of each app, in memory only: about 40 KB for 20 apps. Lost on restart, which is fine.
RECENT = collections.defaultdict(lambda: collections.deque(maxlen=20))
DOWN_SINCE = {}  # app id: when it first stopped answering, cleared when it answers again
FIRST_SEEN = {}  # (app id, message): when an app's own health warning was first seen


class _KeepKeysHome(urllib.request.HTTPRedirectHandler):
    """Follows a redirect, but never carries an app's key to a different server."""
    SECRET = ("authorization", "x-api-key", "x-emby-token", "x-plex-token")

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            old_host = urllib.parse.urlsplit(req.full_url)
            new_host = urllib.parse.urlsplit(newurl)
            if (old_host.scheme, old_host.hostname, old_host.port) != (new_host.scheme, new_host.hostname, new_host.port):
                for name in list(new.headers):
                    if name.lower() in self.SECRET:
                        del new.headers[name]
                if "apikey=" in newurl.lower() or "token=" in newurl.lower():
                    return None  # a key in the address itself: do not follow
        return new


# Every request Starboard makes goes through this opener.
urllib.request.install_opener(urllib.request.build_opener(_KeepKeysHome))
USER_AGENT = "Starboard"
class _LazyPool:
    """A thread pool that starts its threads only when the first job arrives, and never more than 6."""
    _pool = None

    def __getattr__(self, name):
        if _LazyPool._pool is None:
            _LazyPool._pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="apps")
        return getattr(_LazyPool._pool, name)


POOL = _LazyPool()


class ServiceError(Exception):
    status = None  # the app's HTTP status, when it answered with an error


# Shared answers ----------------------------------------------------------------
# Every open tab and device shares one answer per kind for a short time, and only one request per kind runs at
# a time, so five open tabs ask Sonarr once, not five times. "Check again" passes fresh=True.

_cache = {}
_cache_lock = threading.Lock()
_flight = {}


def cached(key, seconds, fn, fresh=False):
    with _cache_lock:
        hit = _cache.get(key)
        if hit and not fresh and time.monotonic() - hit[0] < seconds:
            return hit[1]
        flight = _flight.setdefault(key, threading.Lock())
    with flight:  # a second caller waits for the first one's answer instead of asking again
        with _cache_lock:
            hit = _cache.get(key)
            if hit and time.monotonic() - hit[0] < (0.5 if fresh else seconds):
                return hit[1]
        value = fn()
        with _cache_lock:
            _cache[key] = (time.monotonic(), value)
        return value


def forget(*keys):
    """Drops the shared answers named, or all of them."""
    with _cache_lock:
        for k in keys or list(_cache):
            _cache.pop(k, None)


def _api(service, path, params=None, method="GET", body=None, timeout=TIMEOUT):
    base = service["url"].rstrip("/") + SERVICE_TYPES[service["type"]]["api"]
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if service.get("api_key"):
        headers["X-Api-Key"] = service["api_key"]
        if service["type"] == "audiobookshelf":
            headers["Authorization"] = f"Bearer {service['api_key']}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
            raw = resp.read(8_000_000)
            logs.detail("apps", f"{service['name']} {method} {path} {resp.status} in {round((time.time() - started) * 1000)} ms")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        logs.detail("apps", f"{service['name']} {method} {path} answered {e.code} in {round((time.time() - started) * 1000)} ms")
        detail = ""
        try:
            payload = json.loads(e.read(20000))
            if isinstance(payload, list) and payload:
                detail = payload[0].get("errorMessage", "")
            elif isinstance(payload, dict):
                detail = payload.get("message", "")
        except ValueError:
            pass
        if e.code in (401, 403):
            raise ServiceError(f"{service['name']} refused the API key") from None
        err = ServiceError(detail or f"{service['name']} answered with error {e.code}")
        err.status = e.code
        raise err from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logs.detail("apps", f"{service['name']} {method} {path} not reached: {e}")
        raise ServiceError(f"Cannot reach {service['name']}") from None
    except ValueError:
        raise ServiceError(f"{service['name']} sent something that is not JSON") from None


def _searchable(services):
    return [s for s in services if s.get("enabled", True) and SERVICE_TYPES[s["type"]]["searchable"]]


def _arrs(services):
    return [s for s in services if s.get("enabled", True) and s["type"] in ("sonarr", "radarr", "lidarr", "readarr")]


# Status ------------------------------------------------------------------

# Download clients ---------------------------------------------------------
# qBittorrent (5.2 or later) takes its API key as a bearer token and form posts; SABnzbd takes the key in the query.

def _fetch(service, req, timeout):
    where = f"{service['name']} {req.get_method()} {urllib.parse.urlsplit(req.full_url).path}"  # no query: it can hold the key
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
            raw = resp.read(8_000_000)
            logs.detail("apps", f"{where} {resp.status} in {round((time.time() - started) * 1000)} ms")
    except urllib.error.HTTPError as e:
        logs.detail("apps", f"{where} answered {e.code}")
        if e.code in (401, 403):
            raise ServiceError(f"{service['name']} refused the API key") from None
        raise ServiceError(f"{service['name']} answered with error {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ServiceError(f"Cannot reach {service['name']}") from None
    try:
        return json.loads(raw) if raw[:1] in (b"[", b"{") else raw.decode("utf-8", "replace")
    except ValueError:
        raise ServiceError(f"{service['name']} sent something that is not JSON") from None


def qbit(service, path, data=None, timeout=TIMEOUT):
    req = urllib.request.Request(service["url"].rstrip("/") + "/api/v2/" + path,
                                 data=urllib.parse.urlencode(data).encode() if data is not None else None,
                                 headers={"Authorization": f"Bearer {service.get('api_key', '')}", "User-Agent": USER_AGENT})
    return _fetch(service, req, timeout)


def sab(service, mode, timeout=TIMEOUT, **params):
    """One SABnzbd API call. SABnzbd 4 and later answer on /api (with no URL base, /sabnzbd/api only redirects);
    older ones and those with the URL base /sabnzbd answer on /sabnzbd/api, which is tried second."""
    query = urllib.parse.urlencode({"apikey": service.get("api_key", ""), "output": "json", "mode": mode, **params})
    base = service["url"].rstrip("/")
    result, error = None, None
    for path in ("/api", "/sabnzbd/api"):
        req = urllib.request.Request(f"{base}{path}?{query}", headers={"User-Agent": USER_AGENT})
        try:
            result = _fetch(service, req, timeout)
        except ServiceError as e:
            if str(e).startswith("Cannot reach"):
                raise  # nothing answers at all: the other path will not either
            error = error or e
            continue
        if isinstance(result, (dict, list)):
            break
    else:
        if error:
            raise error
    result = result if isinstance(result, (dict, list)) else {}
    if isinstance(result, dict) and result.get("error"):
        raise ServiceError(f"{service['name']}: {result['error']}")
    return result


def nzbget(service, method, params=None, timeout=TIMEOUT):
    """One NZBGet JSON-RPC call; the API key field holds "user:password" (NZBGet's ControlUsername and ControlPassword)."""
    user, _, password = (service.get("api_key") or "").partition(":")
    body = json.dumps({"method": method, "params": params or [], "id": 1}).encode()
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(service["url"].rstrip("/") + "/jsonrpc", data=body,
                                 headers={"Authorization": f"Basic {token}", "Content-Type": "application/json",
                                          "User-Agent": USER_AGENT})
    result = _fetch(service, req, timeout)
    if not isinstance(result, dict):
        raise ServiceError(f"{service['name']} sent something that is not JSON")
    if result.get("error"):
        raise ServiceError(f"{service['name']}: {(result['error'] or {}).get('message', result['error'])}")
    return result.get("result")


def check(service):
    started = time.monotonic()
    kind = service["type"]
    try:
        if kind in ("sonarr", "radarr", "lidarr", "readarr", "prowlarr"):
            info = _api(service, "/system/status", timeout=5)
            version = info.get("version", "")
        elif kind == "bazarr":
            info = _api(service, "/system/status", timeout=5)
            version = (info.get("data") or {}).get("bazarr_version", "")
        elif kind == "qbittorrent":
            version = str(qbit(service, "app/version", timeout=5)).strip()
        elif kind == "nzbget":
            version = str(nzbget(service, "version", timeout=5) or "")
        elif kind == "sabnzbd":
            version = sab(service, "version", timeout=5).get("version", "")
            sab(service, "queue", timeout=5, limit=0)  # "version" works without a key; this one does not
        elif kind == "seerr":
            version = (_api(service, "/status", timeout=5) or {}).get("version", "")
        elif kind == "gluetun":
            v = vpn_one(service)
            if not v["running"]:
                raise ServiceError(f"The VPN is {v['status'] or 'not connected'}")
            version = ""
        elif kind == "audiobookshelf":
            req = urllib.request.Request(service["url"].rstrip("/") + "/status", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as resp:  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
                version = json.loads(resp.read(200000)).get("serverVersion", "")
            if service.get("api_key"):
                _api(service, "/libraries", timeout=5)  # an API key that is wrong shows as a problem
        elif kind == "jellyfin":
            req = urllib.request.Request(service["url"].rstrip("/") + "/System/Info/Public", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as resp:  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
                version = json.loads(resp.read(200000)).get("Version", "")
        else:
            req = urllib.request.Request(service["url"], headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=5):  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
                    pass
            except urllib.error.HTTPError as e:
                if e.code >= 500:
                    raise ServiceError(f"{service['name']} answered with error {e.code}") from None
            version = ""
        return _record(service, {"id": service["id"], "state": "up", "version": version,
                                 "ms": round((time.monotonic() - started) * 1000)})
    except (ServiceError, urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        message = str(e) if isinstance(e, ServiceError) else f"Cannot reach {service['name']}"
        return _record(service, {"id": service["id"], "state": "down", "message": message})


def _record(service, result):
    """Keeps the last 20 checks of a saved app and when it stopped answering."""
    sid = service.get("id")
    if sid:
        now = time.time()
        RECENT[sid].append({"t": round(now), "state": result["state"], "ms": result.get("ms"), "message": result.get("message", "")})
        if result["state"] == "down":
            result["down_since"] = DOWN_SINCE.setdefault(sid, now)
        else:
            DOWN_SINCE.pop(sid, None)
    return result


def status_one(services, service_id):
    """Checks one app and puts its answer into the shared status, so every page sees it."""
    rows = status_all(services, only=service_id)
    with _cache_lock:
        hit = _cache.get("status")
        if hit and rows:
            _cache["status"] = (hit[0], [rows[0] if r["id"] == service_id else r for r in hit[1]])
    return rows


def recent_checks(service_id):
    return list(reversed(RECENT.get(service_id, [])))


def status_all(services, only=None):
    """Every enabled app's state; only: one app id, checked on its own (Check again in its slide-out)."""
    enabled = [s for s in services if s.get("enabled", True) and (only is None or s["id"] == only)]
    by_id = {s["id"]: s for s in services}
    checked = [s for s in enabled if s.get("url")]
    results = {r["id"]: r for r in POOL.map(check, checked)}
    out = []
    for s in enabled:
        if s["id"] in results:
            out.append(results[s["id"]])
            continue
        target = by_id.get(s.get("follows") or "")
        if target and target.get("url"):
            r = results.get(target["id"]) or check(target)
            follow = {"id": s["id"], "state": r["state"], "follows": target["name"]}
            if r["state"] == "down":
                follow["message"] = f"{target['name']} is not responding"
            out.append(follow)
        else:
            out.append({"id": s["id"], "state": "unknown"})
    return out


def _reach(url):
    """Any answer from the outside address counts as reachable, even "sign in first"."""
    started = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=6):  # outside addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
            pass
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            return {"reachable": False, "message": f"Answered with error {e.code}"}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        reason = getattr(e, "reason", e)
        return {"reachable": False, "message": "Not reachable" if not str(reason) else f"Not reachable ({str(reason)[:80]})"}
    return {"reachable": True, "ms": round((time.monotonic() - started) * 1000)}


def outside_all(services):
    """Checks each app's outside address from the server. Some routers cannot reach their own outside address
    from inside the home network, so a failure here is worth checking from a phone on mobile data."""
    from .watch import cert_days_left  # one more TLS handshake for https:// addresses, only when checked

    def one(s):
        out = dict(_reach(s["outside_link"]), id=s["id"])
        if out["reachable"] and s["outside_link"].startswith("https://"):
            out["cert_days"] = cert_days_left(s["outside_link"])
        return out

    targets = [s for s in services if s.get("enabled", True) and s.get("outside_link")]
    return list(POOL.map(one, targets))


def _update_one(service):
    items = _api(service, "/update") or []
    installed = next((i for i in items if i.get("installed")), None)
    newest = items[0] if items else None
    available = bool(newest and not newest.get("installed") and newest.get("installable", True)
                      and installed and newest.get("version") != installed.get("version"))
    return {
        "id": service["id"],
        "installed": (installed or {}).get("version"),
        "latest": (newest or {}).get("version"),
        "available": available,
        "released": (newest or {}).get("releaseDate"),
    }


def app_updates(services):
    """What each app says about its own updates. Sonarr, Radarr, Lidarr, Readarr and Prowlarr report this;
    for the others only the running version is known."""
    targets = [s for s in services if s.get("enabled", True) and s["type"] in ("sonarr", "radarr", "lidarr", "readarr", "prowlarr")]
    futures = [(s, POOL.submit(_update_one, s)) for s in targets]
    rows, errors = [], []
    for service, future in futures:
        try:
            rows.append(future.result(timeout=TIMEOUT + 2))
        except Exception as e:
            errors.append({"service": service["id"], "message": str(e) if isinstance(e, ServiceError) else f"Cannot reach {service['name']}"})
    return {"items": rows, "errors": errors}


# Search ------------------------------------------------------------------

LOOKUP = {
    "sonarr": "/series/lookup",
    "radarr": "/movie/lookup",
    "lidarr": "/artist/lookup",
    "readarr": "/author/lookup",
}


def _image(item, cover_type):
    for image in item.get("images") or []:
        if image.get("coverType") == cover_type:
            url = image.get("remoteUrl") or image.get("url") or ""
            if url.startswith("https://"):
                return url
    remote = item.get("remotePoster") or ""
    return remote if remote.startswith("https://") else ""


def normalise(service, item):
    kind = service["type"]
    if kind == "sonarr":
        key, title, year = f"tvdb:{item.get('tvdbId')}", item.get("title"), item.get("year")
        detail = f"{item.get('network') or ''} · {item.get('statistics', {}).get('seasonCount') or len(item.get('seasons') or [])} seasons".strip(" ·")
        image = _image(item, "poster")
    elif kind == "radarr":
        key, title, year = f"tmdb:{item.get('tmdbId')}", item.get("title"), item.get("year")
        detail = item.get("studio") or ""
        image = _image(item, "poster")
    elif kind == "lidarr":
        key, title, year = f"lidarr:{item.get('foreignArtistId')}", item.get("artistName"), None
        detail = item.get("disambiguation") or item.get("artistType") or ""
        image = _image(item, "poster")
    else:
        key, title, year = f"readarr:{item.get('foreignAuthorId')}", item.get("authorName"), None
        detail = item.get("disambiguation") or ""
        image = _image(item, "poster")
    overview = (item.get("overview") or "").strip()
    return {
        "service": service["id"],
        "service_name": service["name"],
        "kind": SERVICE_TYPES[kind]["kind"],
        "key": key,
        "title": title or "Untitled",
        "year": year or None,
        "detail": detail,
        "overview": overview[:400] + ("…" if len(overview) > 400 else ""),
        "image": image,
        "in_library": bool(item.get("id")),
        "slug": item.get("titleSlug") or item.get("foreignArtistId") or item.get("foreignAuthorId") or "",
    }


def search(services, query):
    query = query.strip()[:120]
    if len(query) < 2:
        return {"results": [], "errors": []}

    def one(service):
        items = _api(service, LOOKUP[service["type"]], {"term": query}) or []
        return [normalise(service, i) for i in items[:20]]

    targets = _searchable(services)
    futures = [(s, POOL.submit(one, s)) for s in targets]
    results, errors = [], []
    for service, future in futures:
        try:
            results.extend(future.result(timeout=TIMEOUT + 2))
        except Exception as e:  # one app failing must not hide the others
            message = str(e) if isinstance(e, ServiceError) else "it did not answer"
            errors.append({"service": service["id"], "message": f"{service['name']} could not search: {message}"})
    q = query.lower()
    # Exact titles first, then titles that start with the words, then the apps' own order.
    results.sort(key=lambda r: (r["title"].lower() != q, not r["title"].lower().startswith(q)))
    return {"results": results, "errors": errors}


def options(service):
    """Quality profiles, root folders and metadata profiles for the Add dialog."""
    out = {
        "quality_profiles": [{"id": p["id"], "name": p["name"]} for p in _api(service, "/qualityprofile") or []],
        "root_folders": [{"path": r["path"], "free": r.get("freeSpace")} for r in _api(service, "/rootfolder") or []],
        "metadata_profiles": [],
    }
    if service["type"] in ("lidarr", "readarr"):
        out["metadata_profiles"] = [{"id": p["id"], "name": p["name"]} for p in _api(service, "/metadataprofile") or []]
    return out


def _find(service, key):
    """Look the item up again on the server, so the browser cannot inject fields."""
    items = _api(service, LOOKUP[service["type"]], {"term": key}) or []
    prefix, _, value = key.partition(":")
    field = {"tvdb": "tvdbId", "tmdb": "tmdbId", "lidarr": "foreignArtistId", "readarr": "foreignAuthorId"}[prefix]
    for item in items:
        if str(item.get(field)) == value:
            return item
    raise ServiceError("That item was not found again; search once more")


def add(service, key, choice):
    if service["type"] not in LOOKUP:
        raise ServiceError("This app cannot add items")
    item = _find(service, key)
    if item.get("id"):
        raise ServiceError(f"Already in {service['name']}")
    quality = choice.get("quality_profile_id") or service.get("quality_profile_id")
    root = choice.get("root_folder") or service.get("root_folder")
    meta = choice.get("metadata_profile_id") or service.get("metadata_profile_id")
    search_now = bool(choice.get("search", service.get("search_on_add", True)))
    if not quality or not root:
        opts = options(service)
        quality = quality or (opts["quality_profiles"][0]["id"] if opts["quality_profiles"] else None)
        root = root or (opts["root_folders"][0]["path"] if opts["root_folders"] else None)
        if service["type"] in ("lidarr", "readarr") and not meta and opts["metadata_profiles"]:
            meta = opts["metadata_profiles"][0]["id"]
    if not quality or not root:
        raise ServiceError(f"Set up a quality profile and root folder in {service['name']} first")
    body = dict(item)
    body.update({"qualityProfileId": int(quality), "rootFolderPath": root, "monitored": True})
    kind = service["type"]
    if kind == "sonarr":
        body.update({"seasonFolder": True, "addOptions": {"monitor": "all", "searchForMissingEpisodes": search_now}})
        path = "/series"
    elif kind == "radarr":
        body.update({"minimumAvailability": "released", "addOptions": {"searchForMovie": search_now}})
        path = "/movie"
    elif kind == "lidarr":
        body.update({"metadataProfileId": int(meta or 1), "addOptions": {"monitor": "all", "searchForMissingAlbums": search_now}})
        path = "/artist"
    else:
        body.update({"metadataProfileId": int(meta or 1), "addOptions": {"monitor": "all", "searchForMissingBooks": search_now}})
        path = "/author"
    added = _api(service, path, method="POST", body=body)
    return {"title": normalise(service, added or item)["title"], "service_name": service["name"]}


# Downloads, calendar and health ----------------------------------------

IMPORT_STATES = {"importPending", "importing", "imported", "failedPending", "failed", "importBlocked"}


def _queue_state(record):
    """The download client's own state (so a paused client shows Paused), except while importing."""
    tracked = record.get("trackedDownloadState") or ""
    if tracked in IMPORT_STATES:
        return tracked
    return record.get("status") or tracked or ""


def _queue_one(service):
    params = {"pageSize": 100, "includeUnknownSeriesItems": "true"}
    if service["type"] == "sonarr":
        params["includeSeries"] = "true"
        params["includeEpisode"] = "true"
    page = _api(service, "/queue", params) or {}
    rows = []
    for r in page.get("records", []):
        size = r.get("size") or 0
        left = r.get("sizeleft") or 0
        rows.append({
            "id": r.get("id"),
            "service": service["id"],
            "service_name": service["name"],
            "download_id": r.get("downloadId") or "",
            "added": r.get("added") or "",
            "title": r.get("title") or "Unknown",
            "status": _queue_state(r),
            "problem": r.get("trackedDownloadStatus") in ("warning", "error"),
            "messages": [m for s in r.get("statusMessages") or [] for m in s.get("messages") or []][:20],
            "progress": round((size - left) / size * 100, 1) if size else 0,
            "size": size,
            "time_left": r.get("timeleft") or "",
            "client": r.get("downloadClient") or "",
        })
    return rows


def _calendar_one(service, start, end):
    """One app's releases between two dates, with the item's id in the app and a short overview."""
    params = {"start": start.isoformat(), "end": end.isoformat(), "unmonitored": "false"}
    kind = service["type"]
    if kind == "sonarr":
        params["includeSeries"] = "true"
    elif kind == "lidarr":
        params["includeArtist"] = "true"
    elif kind == "readarr":
        params["includeAuthor"] = "true"
    items = _api(service, "/calendar", params) or []
    out = []
    for i in items:
        # Posters come from the app's own small copies, through Starboard (see posters.py).
        if kind == "sonarr":
            title = (i.get("series") or {}).get("title", "")
            detail = f"S{i.get('seasonNumber', 0):02d}E{i.get('episodeNumber', 0):02d} · {i.get('title', '')}"
            when = i.get("airDateUtc")
            have = i.get("hasFile")
            image = posters.address(service, "series", i.get("seriesId"))
        elif kind == "radarr":
            title, detail = i.get("title", ""), "Film"
            when = i.get("digitalRelease") or i.get("physicalRelease") or i.get("inCinemas")
            have = i.get("hasFile")
            image = posters.address(service, "movie", i.get("id"))
        elif kind == "lidarr":
            title, detail = (i.get("artist") or {}).get("artistName", ""), i.get("title", "")
            when, have = i.get("releaseDate"), (i.get("statistics") or {}).get("percentOfTracks") == 100
            image = posters.address(service, "album", i.get("id"))
        else:
            title, detail = i.get("title", ""), (i.get("author") or {}).get("authorName", "")
            when, have = i.get("releaseDate"), (i.get("statistics") or {}).get("bookFileCount", 0) > 0
            image = posters.address(service, "book", i.get("id"))
        if when:
            overview = ((i.get("series") or {}).get("overview") if kind == "sonarr" else None) or i.get("overview") or ""
            item = i.get("seriesId") if kind == "sonarr" else i.get("artistId") if kind == "lidarr" else i.get("authorId") if kind == "readarr" else i.get("id")
            slug = ((i.get("series") or i.get("artist") or i.get("author") or {}).get("titleSlug") if kind != "radarr" else i.get("titleSlug")) or ""
            out.append({"service": service["id"], "service_name": service["name"], "title": title, "detail": detail, "when": when,
                        "have": bool(have), "image": image, "item_id": item, "slug": slug,
                        "overview": overview[:300] + ("…" if len(overview) > 300 else "")})
    return out


def _gather(services, fn):
    futures = [(s, POOL.submit(fn, s)) for s in services]
    rows, errors = [], []
    for service, future in futures:
        try:
            rows.extend(future.result(timeout=TIMEOUT + 2))
        except Exception as e:
            errors.append({"service": service["id"], "message": str(e) if isinstance(e, ServiceError) else f"Cannot reach {service['name']}"})
    return rows, errors


def queue(services):
    # Reelix's radio (its own API, as a "link") is asked at the same time as the other apps.
    rows, errors = _gather(_arrs(services) + reelix_native(services),
                           lambda s: _radio_queue_one(s) if s["type"] == "link" else _queue_one(s))
    return {"items": rows, "errors": errors}


QUEUE_ACTIONS = {
    "remove": {"removeFromClient": "true", "blocklist": "false"},
    "block": {"removeFromClient": "true", "blocklist": "true", "skipRedownload": "true"},
    "block-search": {"removeFromClient": "true", "blocklist": "true", "skipRedownload": "false"},
}


def queue_action(service, item_id, action):
    """Removes one queue item from its app and download client; block also blocklists that release, and
    block-search then looks for another."""
    if action not in QUEUE_ACTIONS:
        raise ServiceError("Choose remove, block or block-search")
    _api(service, f"/queue/{int(item_id)}", QUEUE_ACTIONS[action], method="DELETE")
    forget("queue")


# Reelix radio -------------------------------------------------------------------
# Radio has no Sonarr-style address in Reelix, so it is read from Reelix's own API (/api/v1) with the manager key
# that Install apps gave Starboard. Reelix is found from its entries: the "Reelix" link entry (its address is the
# base), or an entry at a compatible address (base/radarr and so on). Rows carry the link entry's name, so they open
# in Reelix like any other row.

COMPAT_SUFFIXES = ("/radarr", "/sonarr", "/readarr", "/lidarr")
RADIO_SHOWS = 20  # followed shows read for Coming up, newest first: one small call each, every 10 minutes at most
_TRACKED = {"import_pending": "importPending", "importing": "importing", "failed_pending": "failedPending"}
_CLIENT = {"post_processing": "importing", "warning": "downloading"}


def reelix_native(services):
    """Each Reelix server once: {"id", "name", "url" (its /api/v1), "api_key", "link"}. Needs a saved key."""
    found = {}
    entries = [s for s in services if s.get("enabled", True) and s.get("icon") == "reelix"]
    for s in entries:
        url = str(s.get("url", "")).rstrip("/")
        base = next((url[:-len(x)] for x in COMPAT_SUFFIXES if url.endswith(x)), url) if s["type"] != "link" else url
        if not base:
            continue
        here = found.setdefault(base, {"id": s["id"], "name": "Reelix", "type": "link", "url": base + "/api/v1",
                                       "api_key": "", "link": s.get("link") or base})
        if s["type"] == "link":  # the link entry names the rows, so they open Reelix itself
            here.update({"id": s["id"], "name": s.get("name") or "Reelix", "link": s.get("link") or base})
        here["api_key"] = here["api_key"] or s.get("api_key", "")
    return [r for r in found.values() if r["api_key"]]


def _without_radio(fn):
    """A Reelix from before radio (or a full version without it) answers 404: no radio rows, and no error."""
    def run(*args):
        try:
            return fn(*args)
        except ServiceError as e:
            if e.status == 404:
                return []
            raise
    return run


@_without_radio
def _radio_calendar_one(reelix, start, end):
    page = _api(reelix, "/radio/shows", {"followed": "true", "sort": "refreshed", "dir": "desc", "page": 1,
                                         "page_size": RADIO_SHOWS}) or {}
    first, last = start.isoformat(), (end + dt.timedelta(days=1)).isoformat()
    out = []
    shows, failed = (page.get("items") or [])[:RADIO_SHOWS], []
    for show in shows:
        try:
            episodes = (_api(reelix, f"/radio/shows/{int(show['id'])}/episodes") or {}).get("episodes") or []
        except ServiceError as e:  # one busy or missing show: the others still show
            failed.append(e)
            continue
        for e in episodes:
            when = e.get("first_broadcast") or ""
            if not (first <= when[:10] < last) or not e.get("monitored", True):
                continue
            number = f"Series {e['series_number']}, episode {e['number']}" if e.get("series_number") and e.get("number") \
                else f"Episode {e['number']}" if e.get("number") else ""
            overview = e.get("synopsis") or ""
            out.append({"service": reelix["id"], "service_name": reelix["name"], "kind": "radio",
                        "title": show.get("title", ""), "detail": " · ".join(x for x in (number, e.get("title", "")) if x),
                        "when": when, "have": e.get("status") == "in_library", "image": "", "item_id": show["id"],
                        "slug": str(int(show["id"])), "overview": overview[:300] + ("…" if len(overview) > 300 else "")})
    if failed and len(failed) == len(shows):
        raise failed[0]
    return out


@_without_radio
def _radio_queue_one(reelix):
    page = _api(reelix, "/queue", {"page": 1, "page_size": 0}) or {}
    rows = []
    for r in page.get("items") or []:
        media = r.get("media") or {}
        if media.get("kind") != "radio_episode":
            continue
        size = r.get("size") or 0
        eta = r.get("eta_secs")
        status = _TRACKED.get(r.get("state") or "") or _CLIENT.get(r.get("client_state") or "", r.get("client_state") or r.get("state") or "")
        rows.append({
            "id": r.get("id"), "service": reelix["id"], "service_name": reelix["name"], "kind": "radio",
            "download_id": r.get("download_id") or "", "added": r.get("added") or "",
            "title": " · ".join(x for x in (media.get("subtitle"), media.get("title")) if x) or r.get("title") or "Unknown",
            "status": status, "problem": r.get("client_state") == "warning" or bool(r.get("messages") and r.get("state") != "downloading"),
            "messages": [str(m) for m in r.get("messages") or []][:20],
            "progress": round(float(r.get("progress") or 0) * 100, 1), "size": size,
            "time_left": f"{eta // 86400}.{eta % 86400 // 3600:02d}:{eta % 3600 // 60:02d}:{eta % 60:02d}" if isinstance(eta, int) else "",
            "client": r.get("download_client") or "",
        })
    return rows


def radio_queue_action(reelix, item_id, action):
    """Queue actions for a radio download, through Reelix's own queue (the same three as the other apps)."""
    if action not in QUEUE_ACTIONS:
        raise ServiceError("Choose remove, block or block-search")
    params = {"remove_from_client": "true", "blocklist": "true" if action != "remove" else "false",
              "skip_redownload": "true" if action == "block" else "false"}
    _api(reelix, f"/queue/{int(item_id)}", params, method="DELETE")
    forget("queue")


def calendar(services, days=14, start=None, end=None):
    """From yesterday for days, or from start to end (dates; at most 62 days, for a month view)."""
    if start and end:
        end = min(end, start + dt.timedelta(days=62))
    else:
        start = dt.date.today() - dt.timedelta(days=1)
        end = start + dt.timedelta(days=days + 1)
    rows, errors = _gather(_arrs(services) + reelix_native(services),
                           lambda s: _radio_calendar_one(s, start, end) if s["type"] == "link" else _calendar_one(s, start, end))
    rows.sort(key=lambda r: r["when"])
    return {"items": rows, "errors": errors}


def _health_one(service):
    now = time.time()
    out = []
    for h in _api(service, "/health") or []:
        message = h.get("message", "")
        out.append({"service": service["id"], "service_name": service["name"], "level": h.get("type", "warning"), "message": message,
                    "first_seen": FIRST_SEEN.setdefault((service["id"], message), now), "wiki": h.get("wikiUrl") or ""})
    seen = {(service["id"], h["message"]) for h in out}
    for key in [k for k in FIRST_SEEN if k[0] == service["id"] and k not in seen]:
        FIRST_SEEN.pop(key, None)  # gone: forget it, so it is new if it comes back
    return out


# Where in Starboard each of Reelix's own checks is put right (DASH-160), by the check's source.
REELIX_FIX = {"indexers": ("Sites to search", "/settings-reelix.html#rx-indexers"),
              "download_clients": ("Download apps", "/settings-reelix.html#rx-downloadclients"),
              "media_servers": ("Media servers", "/settings-reelix.html#rx-mediaservers"),
              "root_folders": ("Your install", "/settings-install.html"),
              "data_dir": ("Your install", "/settings-install.html"),
              "database": ("Your install", "/settings-install.html")}


def _reelix_health_one(reelix):
    """Reelix's own checks (/api/v1/system/health with the manager key). Its Sonarr- and Radarr-style health routes
    always answer an empty list (demonzoned/Reelix#74), so they are never asked (DASH-176)."""
    now = time.time()
    out = []
    for c in (_api(reelix, "/system/health") or {}).get("checks") or []:
        level = c.get("level") or "warning"
        if level == "ok":
            continue
        message = c.get("message", "")
        where = REELIX_FIX.get(c.get("source", ""))
        out.append({"service": reelix["id"], "service_name": reelix["name"], "level": "error" if level == "error" else "warning",
                    "message": message, "source": c.get("source", ""), "first_seen": FIRST_SEEN.setdefault((reelix["id"], message), now),
                    "wiki": "", "fix": {"label": where[0], "href": where[1]} if where else None})
    seen = {(reelix["id"], h["message"]) for h in out}
    for key in [k for k in FIRST_SEEN if k[0] == reelix["id"] and k not in seen]:
        FIRST_SEEN.pop(key, None)
    return out


def health(services):
    targets = [s for s in services if s.get("enabled", True) and s["type"] in ("sonarr", "radarr", "lidarr", "readarr", "prowlarr")
               and s.get("icon") != "reelix"]
    rows, errors = _gather(targets, _health_one)
    more, more_errors = _gather(reelix_native(services), _reelix_health_one)
    return {"items": rows + more, "errors": errors + more_errors}


# Finished downloads --------------------------------------------------------------
# The newest imports from each app's history (one small page each), for Downloads, Finished this week.

IMPORTED = {"sonarr": (3, {"includeSeries": "true", "includeEpisode": "true"}), "radarr": (3, {"includeMovie": "true"}),
            "lidarr": (8, {"includeArtist": "true", "includeAlbum": "true"}), "readarr": (8, {"includeAuthor": "true", "includeBook": "true"})}


def _recent_one(service, cutoff):
    event, extra = IMPORTED[service["type"]]
    page = _api(service, "/history", {"page": 1, "pageSize": 25, "sortKey": "date", "sortDirection": "descending",
                                      "eventType": event, **extra}) or {}
    out = []
    for r in page.get("records") or []:
        when = r.get("date") or ""
        if when[:10] < cutoff:
            continue
        kind = service["type"]
        if kind == "sonarr":
            ep = r.get("episode") or {}
            title = (r.get("series") or {}).get("title", "")
            detail = f"S{ep.get('seasonNumber', 0):02d}E{ep.get('episodeNumber', 0):02d} · {ep.get('title', '')}" if ep else ""
        elif kind == "radarr":
            title, detail = (r.get("movie") or {}).get("title", ""), "Film"
        elif kind == "lidarr":
            title, detail = (r.get("artist") or {}).get("artistName", ""), (r.get("album") or {}).get("title", "")
        else:
            title, detail = (r.get("book") or {}).get("title", ""), (r.get("author") or {}).get("authorName", "")
        out.append({"service_name": service["name"], "title": title or r.get("sourceTitle", ""), "detail": detail,
                    "when": when, "quality": ((r.get("quality") or {}).get("quality") or {}).get("name", "")})
    return out


def recent(services, days=7):
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    rows, errors = _gather(_arrs(services), lambda s: _recent_one(s, cutoff))
    rows.sort(key=lambda r: r["when"], reverse=True)
    return {"items": rows[:60], "errors": errors}


# Jellyfin ---------------------------------------------------------------------------
# Version, updates, restart needed, Live TV, who is watching and what was added, with Jellyfin's API key.

def _jf(service, path, timeout=TIMEOUT):
    req = urllib.request.Request(service["url"].rstrip("/") + path, headers={
        "Authorization": f'MediaBrowser Token="{service.get("api_key", "")}"', "Accept": "application/json", "User-Agent": USER_AGENT})
    return _fetch(service, req, timeout)


def jellyfin(services):
    found = [s for s in services if s["type"] == "jellyfin" and s.get("enabled", True) and s.get("api_key")]
    if not found:
        return {"configured": False}
    s = found[0]
    info = _jf(s, "/System/Info")
    out = {"configured": True, "name": s["name"], "version": info.get("Version", ""),
           "update": bool(info.get("HasUpdateAvailable")), "restart": bool(info.get("HasPendingRestart")),
           "playing": [], "added": [], "channels": None, "guide": None}
    try:
        out["channels"] = (_jf(s, "/LiveTv/Channels?limit=0") or {}).get("TotalRecordCount")
        guide = next((t for t in _jf(s, "/ScheduledTasks") or [] if t.get("Key") == "RefreshGuide"), None)
        if guide:
            last = guide.get("LastExecutionResult") or {}
            out["guide"] = {"state": guide.get("State", ""), "finished": last.get("EndTimeUtc"), "result": last.get("Status", "")}
    except ServiceError:
        pass  # no Live TV
    for sess in _jf(s, "/Sessions?activeWithinSeconds=900") or []:
        item = sess.get("NowPlayingItem")
        if not item:
            continue
        play = sess.get("PlayState") or {}
        trans = sess.get("TranscodingInfo") or {}
        length = item.get("RunTimeTicks") or 0
        out["playing"].append({
            "user": sess.get("UserName", ""), "device": sess.get("DeviceName", ""), "client": sess.get("Client", ""),
            "title": item.get("Name", ""), "series": item.get("SeriesName", ""), "type": item.get("Type", ""),
            "paused": bool(play.get("IsPaused")),
            "progress": round((play.get("PositionTicks") or 0) / length * 100) if length else None,
            "transcoding": bool(trans) and not trans.get("IsVideoDirect", True),
            "reason": ", ".join(trans.get("TranscodeReasons") or [])[:120],
        })
    latest = _jf(s, "/Items?SortBy=DateCreated&SortOrder=Descending&Recursive=true&Limit=12"
                    "&IncludeItemTypes=Movie,Episode,MusicAlbum,AudioBook,Book&Fields=DateCreated") or {}
    for item in latest.get("Items") or []:
        out["added"].append({"title": item.get("Name", ""), "series": item.get("SeriesName", ""), "type": item.get("Type", ""),
                             "when": item.get("DateCreated", ""), "year": item.get("ProductionYear")})
    return out


# Download speeds and the VPN ---------------------------------------------------------

def _speed(n):
    n = float(n or 0)
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if n < 1000 or unit == "GB/s":
            return f"{n:.0f} {unit}" if unit == "B/s" else f"{n:.1f} {unit}"
        n /= 1000


def _gluetun(service, path):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if service.get("api_key"):
        headers["X-API-Key"] = service["api_key"]
    return _fetch(service, urllib.request.Request(service["url"].rstrip("/") + path, headers=headers), 5)


def vpn_one(service):
    try:
        status = _gluetun(service, "/v1/vpn/status")
    except ServiceError:
        status = _gluetun(service, "/v1/openvpn/status")  # Gluetun before 3.40
    out = {"name": service["name"], "running": (status or {}).get("status") == "running", "status": (status or {}).get("status", "")}
    try:
        ip = _gluetun(service, "/v1/publicip/ip") or {}
        out.update(ip=ip.get("public_ip", ""), country=ip.get("country", ""), city=ip.get("city", ""))
    except ServiceError:
        pass
    for path in ("/v1/portforward", "/v1/openvpn/portforwarded"):
        try:
            out["port"] = (_gluetun(service, path) or {}).get("port") or None
            break
        except ServiceError:
            continue
    return out


def transfer(services):
    """Speeds from qBittorrent and SABnzbd, and the VPN's state from Gluetun, for the top of Downloads."""
    on = [s for s in services if s.get("enabled", True) and s.get("url")]
    out = {"clients": [], "vpn": [], "errors": []}

    def one(s):
        if s["type"] == "qbittorrent" and s.get("api_key"):
            t = qbit(s, "transfer/info") or {}
            return "clients", {"name": s["name"], "kind": "torrent", "down": t.get("dl_info_speed", 0), "up": t.get("up_info_speed", 0),
                               "down_text": _speed(t.get("dl_info_speed")), "up_text": _speed(t.get("up_info_speed"))}
        if s["type"] == "nzbget" and s.get("api_key"):
            st = nzbget(s, "status") or {}
            groups = nzbget(s, "listgroups", [0]) or []
            down = float(st.get("DownloadRate") or 0)
            left = int(st.get("RemainingSizeMB") or 0)
            return "clients", {"name": s["name"], "kind": "usenet", "down": down, "down_text": _speed(down),
                               "paused": bool(st.get("DownloadPaused")), "left": f"{left / 1024:.1f} GB" if left else "",
                               "count": len(groups)}
        if s["type"] == "sabnzbd" and s.get("api_key"):
            q = (sab(s, "queue", limit=0) or {}).get("queue") or {}
            down = float(q.get("kbpersec") or 0) * 1000
            return "clients", {"name": s["name"], "kind": "usenet", "down": down, "down_text": _speed(down),
                               "paused": bool(q.get("paused")), "left": q.get("sizeleft", ""), "count": int(q.get("noofslots") or 0)}
        if s["type"] == "gluetun":
            return "vpn", vpn_one(s)
        return None

    targets = [s for s in on if s["type"] in ("qbittorrent", "sabnzbd", "nzbget", "gluetun")]
    for s, f in [(s, POOL.submit(one, s)) for s in targets]:
        try:
            r = f.result(timeout=TIMEOUT + 2)
            if r:
                out[r[0]].append(r[1])
        except Exception as e:
            out["errors"].append({"service": s["id"], "message": str(e) if isinstance(e, ServiceError) else f"Cannot reach {s['name']}"})
    return out


# Small numbers for the app cards ----------------------------------------------------------
# A few words per app, such as "3 in the queue · 120 wanted". One small request per app, shared for a minute.

def _numbers_one(s, queue_counts, speeds, playing):
    kind = s["type"]
    parts = []
    if kind in ("sonarr", "radarr", "lidarr", "readarr"):
        n = queue_counts.get(s["name"], 0)
        if n:
            parts.append(f"{n} in the queue")
        path = "/wanted/missing"
        wanted = (_api(s, path, {"page": 1, "pageSize": 1, "monitored": "true"}) or {}).get("totalRecords")
        if wanted is not None:
            parts.append(f"{wanted} wanted")
    elif kind == "prowlarr":
        indexers = _api(s, "/indexer") or []
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        failing = [i for i in _api(s, "/indexerstatus") or [] if (i.get("disabledTill") or "") > now]
        parts.append(f"{len(indexers)} indexers" + (f", {len(failing)} failing" if failing else ""))
    elif kind in ("qbittorrent", "sabnzbd", "nzbget") and s["name"] in speeds:
        c = speeds[s["name"]]
        if c.get("paused"):
            parts.append("Paused")
        elif c["down"] or c.get("up"):
            parts.append(f"Downloading {c['down_text']}" + (f", sending {c['up_text']}" if c.get("up") else ""))
        else:
            parts.append("Idle")
    elif kind == "jellyfin" and playing is not None:
        parts.append(f"{playing} playing" if playing else "Nobody playing")
    return parts


def numbers(services):
    on = [s for s in services if s.get("enabled", True) and s.get("url")]
    kinds = {s["type"] for s in on}
    queue_counts, speeds, playing = {}, {}, None
    if kinds & {"sonarr", "radarr", "lidarr", "readarr"}:
        for item in cached("queue", 10, lambda: queue(services))["items"]:
            queue_counts[item["service_name"]] = queue_counts.get(item["service_name"], 0) + 1
    if kinds & {"qbittorrent", "sabnzbd", "nzbget"}:
        speeds = {c["name"]: c for c in cached("transfer", 5, lambda: transfer(services))["clients"]}
    if "jellyfin" in kinds:
        try:
            j = cached("jellyfin", 20, lambda: jellyfin(services))
            playing = len(j["playing"]) if j.get("configured") else None
        except ServiceError:
            playing = None
    targets = [s for s in on if s["type"] in ("sonarr", "radarr", "lidarr", "readarr", "prowlarr", "qbittorrent", "sabnzbd", "nzbget", "jellyfin")]
    out = {}
    for s, f in [(s, POOL.submit(_numbers_one, s, queue_counts, speeds, playing)) for s in targets]:
        try:
            parts = f.result(timeout=TIMEOUT + 2)
        except Exception:
            continue
        if parts:
            out[s["id"]] = parts
    return out


# Requests from Seerr (or Jellyseerr, Overseerr) ----------------------------------------
# The newest requests, with their titles. A title costs one request to Seerr the first time; Starboard keeps
# up to 500 titles in memory so later loads cost nothing.

REQUEST_STATUS = {1: ("Waiting for approval", "warning"), 2: ("Approved", "info"), 3: ("Declined", "muted"),
                  4: ("Failed", "danger"), 5: ("Completed", "success")}
MEDIA_STATUS = {2: "Requested", 3: "Downloading", 4: "Partly available", 5: "Available", 6: "Deleted"}
_titles = {}


def _seerr(service, path, method="GET"):
    return _api(dict(service, type="seerr"), path, method=method)


def _title(service, kind, tmdb):
    key = (service["id"], kind, tmdb)
    if key not in _titles:
        try:
            d = _seerr(service, f"/{'movie' if kind == 'movie' else 'tv'}/{tmdb}") or {}
            _titles[key] = {"title": d.get("title") or d.get("name") or f"TMDB {tmdb}",
                            "year": (d.get("releaseDate") or d.get("firstAirDate") or "")[:4]}
        except ServiceError:
            return {"title": f"TMDB {tmdb}", "year": ""}
        if len(_titles) > 500:
            _titles.pop(next(iter(_titles)))
    return _titles[key]


def requests(services, pending_only=False):
    found = [s for s in services if s["type"] == "seerr" and s.get("enabled", True) and s.get("api_key")]
    if not found:
        return {"configured": False, "items": [], "pending": 0}
    s = found[0]
    page = _seerr(s, f"/request?take=30&skip=0&sort=added&filter={'pending' if pending_only else 'all'}") or {}
    items = []
    for r in page.get("results") or []:
        media = r.get("media") or {}
        kind = media.get("mediaType") or r.get("type")
        info = _title(s, kind, media.get("tmdbId"))
        words, tone = REQUEST_STATUS.get(r.get("status"), ("Unknown", "muted"))
        items.append({"id": r["id"], "kind": "Film" if kind == "movie" else "Series", **info,
                      "seasons": [x.get("seasonNumber") for x in r.get("seasons") or []],
                      "status": words, "tone": tone, "pending": r.get("status") == 1,
                      "media": MEDIA_STATUS.get(media.get("status"), ""),
                      "by": (r.get("requestedBy") or {}).get("displayName", ""), "when": r.get("createdAt", "")})
    counts = _seerr(s, "/request/count") or {}
    return {"configured": True, "name": s["name"], "link": s.get("link") or s["url"], "items": items,
            "pending": counts.get("pending", sum(i["pending"] for i in items))}


def request_action(services, request_id, action):
    s = next((s for s in services if s["type"] == "seerr" and s.get("enabled", True) and s.get("api_key")), None)
    if not s:
        raise ServiceError("No Seerr app with an API key is set up")
    _seerr(s, f"/request/{int(request_id)}/{'approve' if action == 'approve' else 'decline'}", method="POST")
