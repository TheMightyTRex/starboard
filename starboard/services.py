"""Talking to the apps: status, search, add, queue, calendar and health.

API keys stay on the server. Every call goes to an address an administrator saved in Settings.
"""

import datetime as dt
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import posters
from .config import SERVICE_TYPES

TIMEOUT = 8
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
    pass


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
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(8_000_000)
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
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
        raise ServiceError(detail or f"{service['name']} answered with error {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(8_000_000)
    except urllib.error.HTTPError as e:
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
    query = urllib.parse.urlencode({"apikey": service.get("api_key", ""), "output": "json", "mode": mode, **params})
    req = urllib.request.Request(f"{service['url'].rstrip('/')}/sabnzbd/api?{query}", headers={"User-Agent": USER_AGENT})
    result = _fetch(service, req, timeout)
    if isinstance(result, dict) and result.get("error"):
        raise ServiceError(f"{service['name']}: {result['error']}")
    return result


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
        elif kind == "sabnzbd":
            version = sab(service, "version", timeout=5).get("version", "")
            sab(service, "queue", timeout=5, limit=0)  # "version" works without a key; this one does not
        elif kind == "jellyfin":
            req = urllib.request.Request(service["url"].rstrip("/") + "/System/Info/Public", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as resp:
                version = json.loads(resp.read(200000)).get("Version", "")
        else:
            req = urllib.request.Request(service["url"], headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=5):
                    pass
            except urllib.error.HTTPError as e:
                if e.code >= 500:
                    raise ServiceError(f"{service['name']} answered with error {e.code}") from None
            version = ""
        return {"id": service["id"], "state": "up", "version": version,
                "ms": round((time.monotonic() - started) * 1000)}
    except (ServiceError, urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        message = str(e) if isinstance(e, ServiceError) else f"Cannot reach {service['name']}"
        return {"id": service["id"], "state": "down", "message": message}


def status_all(services):
    enabled = [s for s in services if s.get("enabled", True)]
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
        with urllib.request.urlopen(req, timeout=6):
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
    targets = [s for s in services if s.get("enabled", True) and s.get("outside_link")]
    results = POOL.map(lambda s: dict(_reach(s["outside_link"]), id=s["id"]), targets)
    return list(results)


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
            "service_name": service["name"],
            "title": r.get("title") or "Unknown",
            "status": _queue_state(r),
            "problem": r.get("trackedDownloadStatus") in ("warning", "error"),
            "messages": [m for s in r.get("statusMessages") or [] for m in s.get("messages") or []][:3],
            "progress": round((size - left) / size * 100, 1) if size else 0,
            "size": size,
            "time_left": r.get("timeleft") or "",
            "client": r.get("downloadClient") or "",
        })
    return rows


def _calendar_one(service, start, end):
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
            out.append({"service_name": service["name"], "title": title, "detail": detail, "when": when,
                        "have": bool(have), "image": image})
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
    rows, errors = _gather(_arrs(services), _queue_one)
    return {"items": rows, "errors": errors}


def calendar(services, days=14):
    start = dt.date.today() - dt.timedelta(days=1)
    end = start + dt.timedelta(days=days + 1)
    rows, errors = _gather(_arrs(services), lambda s: _calendar_one(s, start, end))
    rows.sort(key=lambda r: r["when"])
    return {"items": rows, "errors": errors}


def _health_one(service):
    return [{"service_name": service["name"], "level": h.get("type", "warning"), "message": h.get("message", "")}
            for h in _api(service, "/health") or []]


def health(services):
    targets = [s for s in services if s.get("enabled", True) and s["type"] in ("sonarr", "radarr", "lidarr", "readarr", "prowlarr")]
    rows, errors = _gather(targets, _health_one)
    return {"items": rows, "errors": errors}
