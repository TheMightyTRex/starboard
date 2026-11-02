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
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            if not (resp.headers.get("Content-Type") or "").startswith("image/"):
                return None
            data = resp.read(MAX_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError):
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


def _prune(folder):
    """Keeps the newest MAX_FILES posters, so the folder stays a few megabytes."""
    files = [os.path.join(folder, n) for n in os.listdir(folder) if n.endswith(".jpg")]
    if len(files) <= MAX_FILES:
        return
    files.sort(key=os.path.getmtime)
    for old in files[:len(files) - MAX_FILES]:
        try:
            os.remove(old)
        except OSError:
            pass
