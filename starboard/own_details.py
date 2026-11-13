"""Bring in a folder with your own details (DASH-322, owner, 11 November 2026): a folder on disk that no outside
source matches (a home video, a lecture series, a self-published audiobook, a radio programme listed nowhere) comes in
with the title, year, description, station and picture the person types.

Reelix cannot do this yet: every way in needs a TMDB, Open Library, MusicBrainz or radio source match. Reelix task
RFX-90 asks for one route, POST /api/v1/customitems (the exact shape is in that task's row). Starboard's side is
built behind a check: the choice "Use my own details" shows only when Reelix's own API description lists that
route, so nothing changes until a Reelix with it is installed. The check is asked at most once in ten minutes and
only when a Bring them in note is shown (lightweight rule).
"""
import base64
import re
import threading
import time

from . import media_import

ROUTE = "/api/v1/customitems"
CHECK_EVERY = 600  # seconds between asking Reelix whether it has the route
# Library tab -> what Reelix makes: books and audiobooks come in by author folder, music by artist folder.
KINDS = {"films": "movie", "tv": "series", "audiobooks": "author", "books": "author", "music": "artist", "radio": "radio_show"}
PICTURE_TYPES = ("image/png", "image/jpeg", "image/webp")
PICTURE_MAX = 5 * 1024 * 1024  # bytes, once decoded
_seen = {}  # Reelix address -> (checked at, has the route)
_lock = threading.Lock()


def _base(cfg):
    try:
        return media_import._reelix(cfg)[0]
    except media_import.ImportError_:
        return None


def available(cfg, now=None):
    """True when the Reelix on the apps lists POST /api/v1/customitems in its API description (RFX-90)."""
    base = _base(cfg)
    if not base:
        return False
    now = time.time() if now is None else now
    with _lock:
        hit = _seen.get(base)
        if hit and now - hit[0] < CHECK_EVERY:
            return hit[1]
    try:
        spec = media_import._call(cfg, "GET", "/openapi.json", timeout=20) or {}
        has = "post" in ((spec.get("paths") or {}).get(ROUTE) or {}) if isinstance(spec, dict) else False
    except (media_import.ImportError_, ValueError):
        has = False
    with _lock:
        _seen[base] = (now, has)
    return has


def forget():
    with _lock:
        _seen.clear()


def clean(tab, details):
    """The typed details, checked: {title, year, overview, station, image_url, image_data}. Raises ValueError."""
    if tab not in KINDS:
        raise ValueError("Your own details work for films, series, music, audiobooks, books and radio")
    d = details if isinstance(details, dict) else {}
    title = " ".join(str(d.get("title") or "").split())[:200]
    if not title:
        raise ValueError("Type a title")
    out = {"title": title}
    year = str(d.get("year") or "").strip()
    if year:
        if not re.fullmatch(r"\d{4}", year) or not 1800 <= int(year) <= 2100:
            raise ValueError(f"{title}: the year is four numbers, such as 2004")
        out["year"] = int(year)
    overview = str(d.get("overview") or "").strip()[:4000]
    if overview:
        out["overview"] = overview
    station = " ".join(str(d.get("station") or "").split())[:200]
    if station and KINDS[tab] == "radio_show":
        out["station"] = station
    url = str(d.get("image_url") or "").strip()
    if url:
        if not re.match(r"^https?://[^\s/]+", url) or len(url) > 2000:
            raise ValueError(f"{title}: the picture's address starts with https:// or http://")
        out["image_url"] = url
    data = str(d.get("image_data") or "")
    if data:
        m = re.fullmatch(r"data:(image/[a-z]+);base64,([A-Za-z0-9+/=\s]+)", data)
        if not m or m.group(1) not in PICTURE_TYPES:
            raise ValueError(f"{title}: the picture is a PNG, JPEG or WebP file")
        try:
            size = len(base64.b64decode(m.group(2), validate=False))
        except ValueError:
            raise ValueError(f"{title}: the picture could not be read") from None
        if size > PICTURE_MAX:
            raise ValueError(f"{title}: the picture is larger than 5 MB")
        out["image_data"] = data
    return out


def request(tab, root_id, item, details):
    """The body Starboard sends to Reelix's POST /api/v1/customitems for one folder (RFX-90)."""
    body = {"kind": KINDS[tab], **clean(tab, details), "monitored": False}
    if tab == "radio":
        body["abs_item_id"] = str(item.get("key") or "")
        if not body["abs_item_id"]:
            raise ValueError("Choose a show")
    else:
        body["root_folder_id"] = int(root_id)
        body["path"] = str(item.get("path") or "")
        if not body["path"]:
            raise ValueError("Choose a folder")
    return body


def add(cfg, tab, root_id, items):
    """Brings in each folder with its own details. Returns {added, errors} as the imports do."""
    added, errors = 0, []
    for item in items:
        where = item.get("path") or item.get("title") or item.get("key") or ""
        try:
            media_import._call(cfg, "POST", "/customitems", request(tab, root_id, item, item.get("own")), timeout=120)
            added += 1
        except (ValueError, TypeError, media_import.ImportError_) as e:
            errors.append({"path": where, "title": where, "message": str(e)})
    return {"added": added, "errors": errors}


def run(cfg, tab, root_id, items, matched_run):
    """The import's run with folders that have their own details taken out first: those go to Reelix's custom items
    (only when it has the route), the rest to `matched_run` as before. Returns {added, errors}."""
    items = [i for i in items or [] if isinstance(i, dict)]
    own = [i for i in items if isinstance(i.get("own"), dict)]
    rest = [i for i in items if not isinstance(i.get("own"), dict)]
    if own and not available(cfg):
        raise ValueError("This Reelix cannot bring in a folder with your own details yet")
    out = {"added": 0, "errors": []}
    if rest or not own:
        try:
            out = matched_run(rest)
        except media_import.ImportError_ as e:
            raise ValueError(str(e)) from None
    if own:
        mine = add(cfg, tab, root_id, own)
        out = {"added": out["added"] + mine["added"], "errors": out["errors"] + mine["errors"]}
    return out
