"""Posters and covers for Coming up, from your own apps, kept in the data folder.

Sonarr, Radarr, Lidarr and Readarr keep small copies of every poster (250 pixels wide). The server fetches
each one once, with the app's API key, and keeps it in data/posters for a week. Browsers only load posters
from Starboard, so no image site sees them, and the posters still show when the internet is down.

An app with no picture route, such as Reelix (DASH-65): the item's own image addresses, then Reelix's own API, then
TMDB through the app's lookup, each at the image site's small size (TMDB w185). With none, the page shows its
placeholder (the app's icon), and the item is left alone for an hour.
"""

import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

KINDS = {  # Starboard's name -> (app type, path under the app's API)
    "series": ("sonarr", "/api/v3/mediacover/{id}/poster-250.jpg"),
    "movie": ("radarr", "/api/v3/mediacover/{id}/poster-250.jpg"),
    "album": ("lidarr", "/api/v1/mediacover/album/{id}/cover-250.jpg"),
    "book": ("readarr", "/api/v1/mediacover/book/{id}/cover-250.jpg"),
}
KEEP = 7 * 86400
MAX_FILES = 400
MAX_BYTES = 400_000
_lock = threading.Lock()


def address(service, kind, item_id):
    """The address a page uses for this poster, or "" when the app keeps none."""
    if kind not in KINDS or KINDS[kind][0] != service["type"] or not str(item_id).isdigit():
        return ""
    return f"/api/posters/{service['id']}/{kind}/{item_id}"


def get(service, kind, item_id, folder):
    """(bytes, content type) or None."""
    if kind not in KINDS or KINDS[kind][0] != service["type"] or not re.match(r"^\d{1,10}$", str(item_id)):
        return None
    os.makedirs(folder, mode=0o700, exist_ok=True)
    path = os.path.join(folder, f"{service['id']}-{kind}-{item_id}.jpg")
    try:
        if time.time() - os.path.getmtime(path) < KEEP:
            with open(path, "rb") as f:
                return f.read(), "image/jpeg"
    except OSError:
        pass
    if _missing.get(path, 0) > time.monotonic():  # no picture anywhere when last asked (DASH-65)
        return None
    url = service["url"].rstrip("/") + KINDS[kind][1].format(id=item_id)
    req = urllib.request.Request(url, headers={"X-Api-Key": service.get("api_key", ""), "User-Agent": "Starboard"})
    data = None
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
            if (resp.headers.get("Content-Type") or "").startswith("image/"):
                data = resp.read(MAX_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError):
        data = None
    if data is None or len(data) > MAX_BYTES:
        # No picture route (Reelix, DASH-65): the item's own image addresses, then Reelix's own API, then TMDB through
        # the app's lookup. With none, the page draws its placeholder, and the app is not asked again for an hour.
        item = _app_json(service, ITEMS[kind][0].format(id=int(item_id)))
        item = item if isinstance(item, dict) else {}
        data = _from_item(service, kind, item) or _from_reelix(service, kind, item_id) or _from_tmdb(service, kind, item)
        if data is None or len(data) > MAX_BYTES:
            if len(_missing) >= MISSING_MAX:
                _missing.clear()
            _missing[path] = time.monotonic() + MISSING_KEEP
            return None
        _missing.pop(path, None)
    with _lock:
        tmp = path + ".tmp"
        with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        _prune(folder)
    return data, "image/jpeg"


# Fallbacks (DASH-65) -------------------------------------------------------------------------------------
ITEMS = {  # Starboard's name -> (the item under the app's API, the picture's coverType)
    "series": ("/api/v3/series/{id}", "poster"),
    "movie": ("/api/v3/movie/{id}", "poster"),
    "album": ("/api/v1/album/{id}", "cover"),
    "book": ("/api/v1/book/{id}", "cover"),
}
MISSING_KEEP = 3600  # seconds an item with no picture anywhere is left alone
MISSING_MAX = 500  # at most this many are remembered (about 60 KB), in memory only
_missing = {}  # the picture's file path: time.monotonic() until which it is not looked for again


def _app_json(service, path):
    """A small JSON answer from the app's own API, or None."""
    import json
    req = urllib.request.Request(service["url"].rstrip("/") + path,
                                 headers={"X-Api-Key": service.get("api_key", ""), "User-Agent": "Starboard", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
            return json.loads(resp.read(512 * 1024) or b"null")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _picture(url):
    """A picture from one of the image sites the Library uses, at its small size, or None."""
    from . import library
    url = library.small(url)
    if not library.poster_allowed(url):
        return None
    try:
        with library._image_opener.open(urllib.request.Request(url, headers={"User-Agent": "Starboard", "Accept": "image/*"}), timeout=8) as resp:  # checked  # nosec B310
            data = resp.read(MAX_BYTES + 1) if (resp.headers.get("Content-Type") or "").startswith("image/") else None
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return data if data and len(data) <= MAX_BYTES else None


def _own_picture(service, url):
    """A picture the app serves itself (an address starting with "/"), asked for with its key, or None."""
    if not url.startswith("/") or url.startswith("//"):
        return None
    base = urllib.parse.urlsplit(service["url"])
    req = urllib.request.Request(f"{base.scheme}://{base.netloc}{url}", headers={"X-Api-Key": service.get("api_key", ""), "User-Agent": "Starboard"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # the app's own address, as above  # nosec B310
            data = resp.read(MAX_BYTES + 1) if (resp.headers.get("Content-Type") or "").startswith("image/") else None
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return data if data and len(data) <= MAX_BYTES else None


def _from_item(service, kind, item):
    """The item's own image addresses: those on an image site first, at the small size, then the app's own copy."""
    images = [i for i in item.get("images") or [] if isinstance(i, dict) and i.get("coverType") == ITEMS[kind][1]]
    addresses = [i.get(k) for k in ("remoteUrl", "url") for i in images if isinstance(i.get(k), str) and i.get(k)]
    for url in dict.fromkeys(a for a in addresses if not a.startswith("/")):
        data = _picture(url)
        if data:
            return data
    for url in dict.fromkeys(a for a in addresses if a.startswith("/")):
        data = _own_picture(service, url)
        if data:
            return data
    return None


def _from_tmdb(service, kind, item):
    """TMDB's poster through the app's own lookup, by the item's TMDB or TVDB number (films and series)."""
    if kind == "movie" and str(item.get("tmdbId") or "").isdigit():
        found = _app_json(service, f"/api/v3/movie/lookup/tmdb?tmdbId={int(item['tmdbId'])}")
    elif kind == "series" and str(item.get("tvdbId") or "").isdigit():
        found = _app_json(service, f"/api/v3/series/lookup?term=tvdb%3A{int(item['tvdbId'])}")
    else:
        return None
    found = found[0] if isinstance(found, list) and found else found
    if not isinstance(found, dict):
        return None
    addresses = [found.get("remotePoster")] + [i.get("remoteUrl") for i in found.get("images") or []
                                               if isinstance(i, dict) and i.get("coverType") == "poster"]
    for url in dict.fromkeys(a for a in addresses if isinstance(a, str) and a):
        data = _picture(url)
        if data:
            return data
    return None


NATIVE = {"movie": "movies", "series": "series"}


def _from_reelix(service, kind, item_id):
    """The poster Reelix's own API names for a film or series (its Radarr and Sonarr addresses have no mediacover),
    fetched through the Library's checked picture fetcher (image sites Reelix uses only)."""
    import json
    m = re.match(r"^(https?://[^/]+)/(radarr|sonarr)/?$", service.get("url", "").rstrip("/") + "/")
    if kind not in NATIVE or not m:
        return None
    req = urllib.request.Request(f"{m.group(1)}/api/v1/{NATIVE[kind]}/{int(item_id)}",
                                 headers={"X-Api-Key": service.get("api_key", ""), "User-Agent": "Starboard", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # the app's own address, as above  # nosec B310
            item = json.loads(resp.read(512 * 1024) or b"{}")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    poster = ((item.get("images") or {}).get("poster") if isinstance(item, dict) else "") or ""
    from . import library
    url = library.small(poster)
    if not library.poster_allowed(url):
        return None
    try:
        with library._image_opener.open(urllib.request.Request(url, headers={"User-Agent": "Starboard", "Accept": "image/*"}), timeout=8) as resp:  # checked  # nosec B310
            return resp.read(MAX_BYTES + 1) if (resp.headers.get("Content-Type") or "").startswith("image/") else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _prune(folder):
    """Keeps the newest MAX_FILES posters, so the folder stays a few megabytes."""
    from . import picture_cache
    picture_cache.maybe_sweep(os.path.dirname(folder))  # pictures unused for four weeks go
    files = [os.path.join(folder, n) for n in os.listdir(folder) if n.endswith(".jpg")]
    if len(files) <= MAX_FILES:
        return
    files.sort(key=os.path.getmtime)
    for old in files[:len(files) - MAX_FILES]:
        try:
            os.remove(old)
        except OSError:
            pass
