"""Posters and covers for Coming up, from your own apps, kept in the data folder.

Sonarr, Radarr, Lidarr and Readarr keep small copies of every poster (250 pixels wide). The server fetches
each one once, with the app's API key, and keeps it in data/posters for a week. Browsers only load posters
from Starboard, so no image site sees them, and the posters still show when the internet is down.
"""

import os
import re
import threading
import time
import urllib.error
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
    url = service["url"].rstrip("/") + KINDS[kind][1].format(id=item_id)
    req = urllib.request.Request(url, headers={"X-Api-Key": service.get("api_key", ""), "User-Agent": "Starboard"})
    data = None
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # app addresses are checked to be http(s) when saved (config.validate_service)  # nosec B310
            if (resp.headers.get("Content-Type") or "").startswith("image/"):
                data = resp.read(MAX_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError):
        data = None
    if data is None:  # Reelix (12 November 2026): no mediacover; its own API names the poster, fetched like the Library's
        data = _from_reelix(service, kind, item_id)
        if data is None:
            return None
    if len(data) > MAX_BYTES:
        return None
    with _lock:
        tmp = path + ".tmp"
        with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        _prune(folder)
    return data, "image/jpeg"


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
