"""App icons for the cards, from the dashboard-icons collection (github.com/homarr-labs/dashboard-icons).

The server fetches each icon once and keeps a copy in the data folder, so browsers only ever load icons from
Starboard itself and the cards still have icons when the internet is down. An icon can be:
- a name from the collection, such as "sonarr" (the default is the app's name, lowercased);
- an https:// address of an SVG or PNG;
- a file you put in data/icons/, such as data/icons/myapp.svg, named by the same name.
"""

import hashlib
import os
import re
import threading
import time
import urllib.error
import urllib.request

CDN = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons"
MAX_BYTES = 300_000
RETRY_MISSING_AFTER = 86400
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
TYPES = {".svg": "image/svg+xml", ".png": "image/png"}

# Names that differ from the app's name in the collection. Seerr (Overseerr and Jellyseerr merged in 2026) has its own
# icon there now, so it is no longer shown as Jellyseerr's.
ALIASES = {"qbittorrent": "qbittorrent", "sabnzbd": "sabnzbd", "old-launcher": ""}

_lock = threading.Lock()


def default_name(service):
    slug = re.sub(r"[^a-z0-9]+", "-", service.get("name", "").lower()).strip("-")
    return ALIASES.get(slug, slug)


def source(service):
    """What to fetch: ("name", slug) or ("url", address), or None for no icon."""
    value = (service.get("icon") or "").strip()
    if value.startswith("https://"):
        return ("url", value)
    if value:
        return ("name", value.lower()) if NAME_RE.match(value.lower()) else None
    slug = default_name(service)
    return ("name", slug) if slug and NAME_RE.match(slug) else None


def reelix_base(service):
    """The running Reelix's own address from one of its cards (http://reelix:7700 from http://reelix:7700/radarr)."""
    from .services import COMPAT_SUFFIXES
    url = str(service.get("url") or "").rstrip("/")
    if not url.startswith(("http://", "https://")):
        return ""
    return next((url[:-len(x)] for x in COMPAT_SUFFIXES if url.endswith(x)), url)


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Starboard"})
    with urllib.request.urlopen(req, timeout=8) as resp:  # the icon collection's https address, an icon address checked to start with https://, or Reelix's own logo on its saved address  # nosec B310
        if resp.status != 200:
            return None
        data = resp.read(MAX_BYTES + 1)
        return data if len(data) <= MAX_BYTES else None


def _looks_like(data, ext):
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    head = data[:2000].lower()
    return b"<svg" in head


def get(service, folder, fetch=True):
    """Returns (bytes, content type) or None. fetch=False: only icons already saved or put in the folder."""
    src = source(service)
    if not src:
        return None
    kind, value = src
    key = value if kind == "name" else "url-" + hashlib.sha256(value.encode()).hexdigest()[:24]
    if kind == "name" and value == "reelix":
        key = "reelix-own"  # Reelix's own logo (DASH-255): a "missing" marker saved before 0.13.1 does not hold it back
    os.makedirs(folder, mode=0o700, exist_ok=True)
    with _lock:
        for ext, ctype in TYPES.items():
            path = os.path.join(folder, key + ext)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    return f.read(), ctype
        missing = os.path.join(folder, key + ".missing")
        if not fetch:
            return None
        if os.path.exists(missing) and time.time() - os.path.getmtime(missing) < RETRY_MISSING_AFTER:
            return None
        if kind == "name":
            candidates = [(f"{CDN}/svg/{value}.svg", ".svg"), (f"{CDN}/png/{value}.png", ".png")]
            if value == "reelix":
                # The collection has no Reelix (DASH-255): its own logo, from the running Reelix, kept like the others.
                base = reelix_base(service)
                if base:
                    candidates.insert(0, (base + "/logo.png", ".png"))
        else:
            ext = ".png" if value.lower().split("?")[0].endswith(".png") else ".svg"
            candidates = [(value, ext)]
        for url, ext in candidates:
            try:
                data = _fetch(url)
            except (urllib.error.URLError, OSError, ValueError):
                data = None
            if data and _looks_like(data, ext):
                path = os.path.join(folder, key + ext)
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                return data, TYPES[ext]
        with open(missing, "w"):
            pass
        return None
