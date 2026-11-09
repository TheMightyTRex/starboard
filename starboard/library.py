"""The Library: what Reelix holds, as walls of covers with an A to Z list, item pages and Search (DASH-163, DASH-162).

Reelix's list answers are large (every film with its files and details), so Starboard keeps its own slim index:
one file per tab in data/library/<tab>.json with only what a wall needs (id, title, sort key, letter, year, a
small poster address, one status word and one count). The index is read from disk for each request and never
held in memory. It is built in pages of 500, refreshed when a tab is opened and the index is older than five
minutes, and every 30 minutes while the Library has been used in the last hour. Nothing runs when nobody uses
the Library.

Item pages ask Reelix for one item at a time, kept for 60 seconds. Posters are fetched by the server only from
the image sites Reelix uses (TMDB, Open Library, Cover Art Archive) or from Reelix itself, at a small size, and
kept in data/posters/library (7 days, at most 400 files), so the browser never contacts an image site.
"""

import datetime as dt
import gc
import hashlib
import json
import os
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from . import logs, services

TABS = ("films", "tv", "music", "radio", "books", "audiobooks")
PAGE = 250  # items per request while building: about 0.35 MB of Reelix's answer, far under the 8 MB read cap,
# and small enough that reading it costs little memory (each Reelix list request costs about the same at any size)
STALE = 300  # a tab opened with an index older than this is refreshed in the background
REFRESH = 1800  # while in use, every 30 minutes
IN_USE = 3600  # the Library counts as in use for an hour after it was last opened
ITEM_SECONDS = 60
WALL_MAX = 200  # at most this many covers in one answer
LABELS = {"films": "Films", "tv": "TV", "music": "Music", "radio": "Radio", "books": "Books", "audiobooks": "Audiobooks"}
NOUNS = {"films": ("film", "films"), "tv": ("series", "series"), "music": ("artist", "artists"),
         "radio": ("show", "shows"), "books": ("book", "books"), "audiobooks": ("audiobook", "audiobooks")}
STATUS = {  # Storyarr's status words: label and tone
    "in_library": ("In library", "success"),
    "partly": ("Partly in library", "info"),
    "wanted": ("Wanted", "warning"),
    "not_released": ("Not released", "muted"),
    "not_monitored": ("Not wanted", "muted"),
    "downloading": ("Downloading", "info"),
    "searching": ("Searching", "info"),
}
CHIPS = {  # filter chips for each tab: key, label
    "films": [("released", "Released"), ("coming", "Coming soon"), ("missing", "Missing")],
    "tv": [("continuing", "Continuing"), ("ended", "Ended"), ("missing", "Missing episodes")],
    "music": [("complete", "Complete"), ("missing", "Missing tracks")],
    "radio": [("in_library", "Has episodes"), ("wanted", "Wanted")],
    "books": [("in_library", "In library"), ("wanted", "Wanted"), ("not_released", "Not released")],
    "audiobooks": [("in_library", "In library"), ("wanted", "Wanted"), ("not_released", "Not released")],
}
GROUPS = {"films": "Collection", "tv": "Network", "radio": "Station", "books": "Series", "audiobooks": "Series",
          "books-authors": "Author", "audiobooks-authors": "Author"}
IMAGE_HOSTS = ("image.tmdb.org", "covers.openlibrary.org", "coverartarchive.org")
POSTER_KEEP = 7 * 86400
POSTER_FILES = 400
POSTER_BYTES = 400_000
_locks = {tab: threading.Lock() for tab in TABS}
_one_build = threading.Lock()  # one tab is built at a time, so opening Search does not read six lists at once
_building = set()
_state = {"used": 0.0, "tabs": {}, "thread": None, "errors": {}}
_state_lock = threading.Lock()


# Letters and sort keys -------------------------------------------------------------------------------------

def fold(text):
    """Lower case, accents folded: 'Émile' -> 'emile'."""
    return "".join(c for c in unicodedata.normalize("NFD", str(text or "")) if unicodedata.category(c) != "Mn").lower()


def sort_key(title, given=""):
    """The title as it sorts: no leading The, A or An, accents folded, no leading punctuation."""
    key = fold(given or title).strip()
    key = re.sub(r"^(the|a|an)\s+", "", key)
    return re.sub(r"^[^\w]+", "", key)


def letter(key):
    first = key[:1].upper()
    return first if "A" <= first <= "Z" else "#"


# Posters ---------------------------------------------------------------------------------------------------

def small(url, size="wall"):
    """The same picture at a small size: TMDB w185 on walls and w342 on pages, Open Library -M."""
    if not isinstance(url, str) or not url:
        return ""
    url = re.sub(r"/t/p/(w\d+|original)/", "/t/p/w185/" if size == "wall" else "/t/p/w342/", url)
    url = re.sub(r"-L\.jpg$", "-M.jpg", url)
    return url


def poster_allowed(url, reelix_base=""):
    """Only https from the image sites Reelix uses, or Reelix's own address (an image it serves itself)."""
    try:
        u = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if u.username or u.password:
        return False
    if u.scheme == "https" and (u.hostname or "").lower() in IMAGE_HOSTS:
        return True
    if reelix_base:
        r = urllib.parse.urlsplit(reelix_base)
        return (u.scheme, u.hostname, u.port) == (r.scheme, r.hostname, r.port) and u.scheme in ("http", "https")
    return False


class _ImagesOnly(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to another image site (Cover Art Archive sends pictures from archive.org)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = (urllib.parse.urlsplit(newurl).hostname or "").lower()
        if not newurl.startswith("https://") or not (host in IMAGE_HOSTS or host == "archive.org" or host.endswith(".archive.org")):
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_image_opener = urllib.request.build_opener(_ImagesOnly)


def poster(data_dir, url, reelix=None, size="wall"):
    """(bytes, content type) of a small poster, kept on disk, or None. url is the address from the index."""
    base = (reelix or {}).get("url", "").rsplit("/api/v1", 1)[0]
    url = small(url, size)
    if not poster_allowed(url, base):
        return None
    folder = os.path.join(data_dir, "posters", "library")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    path = os.path.join(folder, hashlib.sha256(url.encode()).hexdigest()[:32] + ".img")
    try:
        age = time.time() - os.path.getmtime(path)
        if age < POSTER_KEEP:
            with open(path, "rb") as f:
                raw = f.read()
            if not raw:  # the site had no picture: ask again only after a day
                if age < 86400:
                    return None
            else:
                kind, _, body = raw.partition(b"\n")
                return body, kind.decode()
    except (OSError, UnicodeDecodeError):
        pass
    headers = {"User-Agent": services.USER_AGENT, "Accept": "image/*"}
    own = base and url.startswith(base + "/api/v1/")
    if own:  # a picture Reelix serves itself (radio artwork) needs the key; it never leaves Reelix's address
        headers["X-Api-Key"] = reelix.get("api_key", "")
    req = urllib.request.Request(url, headers=headers)
    data = b""
    try:
        opener = urllib.request.build_opener() if own else _image_opener
        with opener.open(req, timeout=8) as resp:  # addresses checked by poster_allowed  # nosec B310
            kind = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
            if kind in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                data = resp.read(POSTER_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return None  # busy or refused: try again next time
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if not data or len(data) > POSTER_BYTES:
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb"):
            pass  # remembered as "no picture" for a day
        return None
    tmp = path + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
        f.write(kind.encode() + b"\n" + data)
    os.replace(tmp, path)
    _prune(folder)
    return data, kind


def _prune(folder):
    files = [os.path.join(folder, n) for n in os.listdir(folder) if n.endswith(".img")]
    if len(files) <= POSTER_FILES:
        return
    files.sort(key=os.path.getmtime)
    for old in files[:len(files) - POSTER_FILES]:
        try:
            os.remove(old)
        except OSError:
            pass


# Reading Reelix --------------------------------------------------------------------------------------------

def reelix_of(all_services):
    """The first Reelix with a saved key, or None."""
    found = services.reelix_native(all_services)
    return found[0] if found else None


def _pages(reelix, path, params=None):
    """Every item of a paged list, PAGE at a time; each page is turned into slim entries by the caller."""
    page = 1
    while True:
        answer = services._api(reelix, path, dict(params or {}, page=page, page_size=PAGE), timeout=30) or {}
        items = answer.get("items") or []
        yield items
        if len(items) < PAGE or page * PAGE >= int(answer.get("total") or 0):
            return
        page += 1


def _added(value):
    try:
        return int(dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return 0


def _entry(item_id, title, sort_title, year, image, status, count, added, filters, meta="", groups=()):
    key = sort_key(title, sort_title)
    return {"i": item_id, "t": title or "Untitled", "s": key, "l": letter(key), "y": year or None, "p": image or "",
            "w": status, "c": count, "a": added, "f": filters, "m": meta, "g": [g for g in groups if g]}


def _plural(n, one, many):
    return f"{n:,} {one if n == 1 else many}"


def _film(m):
    has = bool(m.get("has_file"))
    released = m.get("status") == "released" or has
    status = "in_library" if has else ("wanted" if released and m.get("monitored", True) else
                                       "not_released" if not released else "not_monitored")
    filters = ["released"] if released else ["coming"]
    if released and not has:
        filters.append("missing")
    coll = (m.get("collection") or {}).get("title") or ""
    return _entry(m["id"], m.get("title"), m.get("sort_title"), m.get("year"), (m.get("images") or {}).get("poster"),
                  status, "", _added(m.get("added")), filters, str(m.get("year") or ""), [coll])


def _series(s):
    st = s.get("statistics") or {}
    have, total = int(st.get("episode_file_count") or 0), int(st.get("episode_count") or 0)
    status = "in_library" if total and have >= total else "partly" if have else "wanted" if total else "not_released"
    filters = ["continuing" if s.get("status") in ("continuing", "upcoming") else "ended"]
    if have < total:
        filters.append("missing")
    years = str(s.get("year") or "")
    if s.get("status") == "ended" and (s.get("last_aired") or "")[:4] and (s.get("last_aired") or "")[:4] != years:
        years += f" to {s['last_aired'][:4]}"
    elif s.get("status") in ("continuing", "upcoming") and years:
        years += " to now"
    meta = " · ".join(x for x in (s.get("network") or "", years) if x)
    return _entry(s["id"], s.get("title"), s.get("sort_title"), s.get("year"), (s.get("images") or {}).get("poster"),
                  status, f"{have:,} of {total:,} episodes" if total else "", _added(s.get("added")), filters, meta,
                  [s.get("network") or ""])


def _book(b, fmt, today):
    has = bool(b.get(f"{fmt}_file"))
    if not has and not b.get(f"monitored_{fmt}"):
        return None  # not in this format at all
    released = not b.get("release_date") or b["release_date"] <= today
    status = "in_library" if has else "wanted" if released else "not_released"
    groups = [s.get("title") for s in b.get("series") or []]
    entry = _entry(b["id"], b.get("title"), b.get("sort_title"), b.get("year"), (b.get("images") or {}).get("poster"),
                   status, "", _added(b.get("added")), [status], b.get("author_name") or "", groups)
    entry["au"] = b.get("author_name") or ""
    return entry


def _artist(a):
    st = a.get("statistics") or {}
    have, total = int(st.get("track_file_count") or 0), int(st.get("track_count") or 0)
    status = "in_library" if total and have >= total else "partly" if have else "wanted"
    return _entry(a["id"], a.get("name"), a.get("sort_name"), None, (a.get("images") or {}).get("poster"), status,
                  _plural(int(st.get("album_count") or 0), "album", "albums"), _added(a.get("added")),
                  ["complete" if total and have >= total else "missing"], a.get("disambiguation") or a.get("country") or "")


def _show(r, base):
    st = r.get("statistics") or {}
    have, wanted = int(st.get("in_library_count") or 0), int(st.get("wanted_count") or 0)
    status = "in_library" if have and not wanted else "partly" if have else "wanted" if wanted else "not_released"
    filters = (["in_library"] if have else []) + (["wanted"] if wanted else [])
    art = f"{base}/api/v1/radio/shows/{int(r['id'])}/artwork" if r.get("has_artwork") else ""
    return _entry(r["id"], r.get("title"), r.get("sort_title"), (r.get("first_broadcast") or "")[:4] or None, art, status,
                  _plural(have, "episode", "episodes") if have else "", _added(r.get("added_at")), filters,
                  r.get("station_name") or "", [r.get("station_name") or ""])


def build(reelix, tab):
    """Reads one tab from Reelix and returns its slim entries, sorted A to Z."""
    out = []
    today = dt.date.today().isoformat()
    base = reelix["url"].rsplit("/api/v1", 1)[0]
    if tab == "films":
        for page in _pages(reelix, "/movies", {"sort": "title"}):
            out.extend(_film(m) for m in page)
    elif tab == "tv":
        for page in _pages(reelix, "/series", {"sort": "title"}):
            out.extend(_series(s) for s in page)
    elif tab in ("books", "audiobooks"):
        fmt = "ebook" if tab == "books" else "audiobook"
        for page in _pages(reelix, "/books"):
            out.extend(e for e in (_book(b, fmt, today) for b in page) if e)
    elif tab == "music":
        for page in _pages(reelix, "/artists", {"sort": "sort_name"}):
            out.extend(_artist(a) for a in page)
    elif tab == "radio":
        try:
            for page in _pages(reelix, "/radio/shows", {"followed": "true"}):
                out.extend(_show(r, base) for r in page)
        except services.ServiceError as e:
            if e.status != 404:  # a Reelix without radio: an empty tab
                raise
    out.sort(key=lambda e: (e["l"] != "#", e["s"], e["i"]))  # # first, then A to Z, as the letter row
    return out


def _give_back():
    """Hands the memory used while reading Reelix's lists back to the system (glibc keeps it otherwise). ctypes is
    loaded here, after the first build, not when Starboard starts, so an unused Library costs nothing at idle."""
    gc.collect()
    try:
        import ctypes  # noqa: PLC0415
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (ImportError, AttributeError, OSError):
        pass  # not glibc (such as Alpine's musl): the memory is still freed for Python to use again


def _path(data_dir, tab):
    return os.path.join(data_dir, "library", f"{tab}.json")


def _write(data_dir, tab, entries):
    folder = os.path.join(data_dir, "library")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    path = _path(data_dir, tab)
    tmp = path + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump({"built": int(time.time()), "items": entries}, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, path)


def refresh(data_dir, reelix, tab):
    """Builds one tab's index now. Only one build per tab runs at a time; a second caller waits for it."""
    with _locks[tab], _one_build:
        started = time.time()
        try:
            entries = build(reelix, tab)
        except services.ServiceError as e:
            with _state_lock:
                _state["errors"][tab] = str(e)
            raise
        _write(data_dir, tab, entries)
        count = len(entries)
        del entries
        _give_back()
        with _state_lock:
            _state["errors"].pop(tab, None)
        logs.detail("library", f"{LABELS[tab]} index: {count} items in {round((time.time() - started) * 1000)} ms")
        return count


def _refresh_quietly(data_dir, reelix, tab):
    try:
        refresh(data_dir, reelix, tab)
    except Exception as e:  # noqa: BLE001 - a background refresh must never stop the server; the error is shown on the page
        logs.detail("library", f"{LABELS[tab]} index not refreshed: {e}")
    finally:
        with _state_lock:
            _building.discard(tab)


def _background(data_dir, reelix, tab):
    with _state_lock:
        if tab in _building:
            return
        _building.add(tab)
    threading.Thread(target=_refresh_quietly, args=(data_dir, reelix, tab), daemon=True, name=f"library-{tab}").start()


def _keeper(data_dir, get_reelix):
    """Every few minutes while the Library is in use: rebuild the tabs used in the last hour every 30 minutes.
    Ends itself an hour after the Library was last opened, so nothing runs when nobody uses it."""
    while True:
        time.sleep(120)
        with _state_lock:
            idle = time.time() - _state["used"] > IN_USE
            tabs = [t for t, used in _state["tabs"].items() if time.time() - used < IN_USE]
            if idle:
                _state["thread"] = None
                return
        reelix = get_reelix()
        if not reelix:
            continue
        for tab in tabs:
            try:
                age = time.time() - os.path.getmtime(_path(data_dir, tab))
            except OSError:
                age = REFRESH
            if age >= REFRESH:
                _background(data_dir, reelix, tab)


def used(data_dir, tab, get_reelix):
    """Marks the Library as in use, and starts the keeper thread if it is not running."""
    with _state_lock:
        _state["used"] = time.time()
        if tab:
            _state["tabs"][tab] = time.time()
        if _state["thread"] is None:
            _state["thread"] = threading.Thread(target=_keeper, args=(data_dir, get_reelix), daemon=True, name="library-keeper")
            _state["thread"].start()


def load(data_dir, reelix, tab):
    """The tab's index: from disk, built first when there is none, refreshed in the background when stale."""
    path = _path(data_dir, tab)
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        age = None
    if age is None:
        refresh(data_dir, reelix, tab)
    elif age > STALE:
        _background(data_dir, reelix, tab)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def forget(data_dir):
    """Removes the index files, so the next visit builds them again (after Reelix changes)."""
    for tab in TABS:
        try:
            os.remove(_path(data_dir, tab))
        except OSError:
            pass


# Walls -----------------------------------------------------------------------------------------------------

def _card(tab, e):
    word = STATUS.get(e["w"], ("", "muted"))
    return {"id": e["i"], "title": e["t"], "meta": e.get("m", ""), "count": e.get("c", ""), "letter": e["l"],
            "status": word[0], "tone": word[1],
            "poster": f"/api/library/poster?tab={tab}&id={e['i']}" if e.get("p") else ""}


def wall(index, tab, q="", chip="", sort="az", group="", offset=0, limit=40, until="", by=""):
    """One page of a wall: the covers, the letters there are, the chips with counts and how many match."""
    items = index["items"]
    total = len(items)
    if group:
        g = group.lower()
        if by == "authors":
            items = [e for e in items if e.get("au", "").lower() == g]
        else:
            items = [e for e in items if any(x.lower() == g for x in e.get("g") or [])]
    if q:
        words = fold(q).split()
        items = [e for e in items if all(w in fold(e["t"]) or w in fold(e.get("m", "")) for w in words)]
    counts = {key: sum(1 for e in items if key in e["f"]) for key, _ in CHIPS.get(tab, [])}
    if chip:
        items = [e for e in items if chip in e["f"]]
    if sort == "added":
        items = sorted(items, key=lambda e: -(e.get("a") or 0))
    elif sort == "year":
        items = sorted(items, key=lambda e: -(int(e.get("y") or 0)))
    letters = sorted({e["l"] for e in items}) if sort == "az" else []
    if until and sort == "az":  # the A to Z list: start the page at the letter's first title
        rank = (lambda x: "" if x == "#" else x)  # # sorts before A
        offset = next((n for n, e in enumerate(items) if rank(e["l"]) >= rank(until)), len(items))
    limit = min(limit, WALL_MAX)
    page = items[offset:offset + limit]
    return {"items": [_card(tab, e) for e in page], "offset": offset, "shown": len(items), "total": total,
            "letters": letters, "built": index.get("built"),
            "chips": [{"key": k, "label": label, "count": counts[k]} for k, label in CHIPS.get(tab, [])]}


def groups(index, tab, kind=""):
    """The groups of a tab (collections, networks, stations, book series, authors) with how many items each."""
    found = {}
    for e in index["items"]:
        names = [e.get("au", "")] if kind == "authors" else e.get("g") or []
        for name in names:
            if name:
                g = found.setdefault(name.lower(), {"name": name, "count": 0, "have": 0, "poster": ""})
                g["count"] += 1
                g["have"] += e["w"] == "in_library"
                if not g["poster"] and e.get("p"):
                    g["poster"] = f"/api/library/poster?tab={tab}&id={e['i']}"
    out = sorted(found.values(), key=lambda g: sort_key(g["name"]))
    for g in out:
        g["letter"] = letter(sort_key(g["name"]))
    return out


def find(index, item_id):
    return next((e for e in index["items"] if e["i"] == item_id), None)


# Item pages ------------------------------------------------------------------------------------------------

def _minutes(n):
    if not n:
        return ""
    h, m = divmod(int(n), 60)
    return f"{h} h {m} min" if h else f"{m} min"


def _date(text):
    try:
        d = dt.date.fromisoformat(str(text)[:10])
        return f"{d.day} {d:%B} {d.year}"
    except ValueError:
        return ""


def _row(number, title, when, status, poster="", href="", note="", **extra):
    word = STATUS.get(status, ("", "muted"))
    return {"number": number, "title": title or "Untitled", "date": _date(when) if when else "", "status": word[0],
            "tone": word[1], "poster": poster, "href": href, "note": note, **extra}


def _queue(reelix):
    """What Reelix is downloading now: {("movie", id) or ("episode", id)}, for Downloading on item pages."""
    try:
        answer = services._api(reelix, "/queue", timeout=10) or []
    except services.ServiceError:
        return set()
    items = answer.get("items") if isinstance(answer, dict) else answer
    out = set()
    for q in items or []:
        media = q.get("media") or {}
        if media.get("kind") == "movie":
            out.add(("movie", media.get("id")))
        for ep in q.get("episodes") or []:
            out.add(("episode", ep.get("id")))
    return out


def _open(reelix, path):
    return {"label": "Open in Reelix", "href": reelix["link"].rstrip("/") + path}


def _seasons(seasons):
    """Episodes grouped by season, numbered seasons first, then Specials (season 0). The newest season opens; the
    page shows the others closed, so a long series is not one long list."""
    order = sorted(n for n in seasons if n) + ([0] if 0 in seasons else [])
    newest = max((n for n in seasons if n), default=0)
    out = []
    for n in order:
        rows = seasons[n]
        have = sum(1 for r in rows if r["status"] == STATUS["in_library"][0])
        wanted = sum(1 for r in rows if r.get("can_get"))
        jf = [r for r in rows if r.get("jf")]
        out.append({"heading": f"Season {n}" if n else "Specials", "season": n, "missing": wanted,
                    "watched": {"watched": all(r["watched"] for r in jf), "ids": [r["jf"] for r in jf]} if jf else None,
                    "meta": f"{have:,} of {len(rows):,} in your library", "open": n == newest, "rows": rows})
    return out


def item(data_dir, reelix, tab, item_id, cfg=None):
    """One item's page: header, facts and its list (episodes, reading order, albums, collection). With cfg, films and
    series also say what you have watched, from Jellyfin (watched.py, DASH-276)."""
    from . import watched as _watched
    item_id = int(item_id)
    today = dt.date.today().isoformat()
    poster = f"/api/library/poster?tab={tab}&id={item_id}&size=page"
    if tab == "films":
        m = services._api(reelix, f"/movies/{item_id}") or {}
        e = _film(m)
        facts = [("Year", m.get("year")), ("Length", _minutes(m.get("runtime_minutes"))), ("Certificate", m.get("certification")),
                 ("Studio", m.get("studio")), ("Genres", ", ".join(m.get("genres") or [])),
                 ("In cinemas", _date(m.get("in_cinemas"))), ("Digital release", _date(m.get("digital_release"))),
                 ("Quality", ((m.get("movie_file") or {}).get("quality_name") or "")),
                 ("Collection", (m.get("collection") or {}).get("title"))]
        downloading = ("movie", item_id) in _queue(reelix)
        out = {"title": m.get("title"), "meta": [x for x in (str(m.get("year") or ""), _minutes(m.get("runtime_minutes")),
                                                             m.get("certification") or "") if x],
               "overview": m.get("overview") or "", "status": "downloading" if downloading else e["w"], "progress": None,
               "open": _open(reelix, f"/movies/{item_id}"),
               # DASH-276, DASH-206: what Starboard can do with it here.
               "can": {"get": not m.get("has_file") and not downloading, "follow": bool(m.get("monitored")), "delete": True,
                       "has_file": bool(m.get("has_file"))}}
        w = _watched.film(cfg, m.get("tmdb_id")) if cfg else None
        out["watched"] = {"watched": w["watched"], "ids": [w["id"]], "user": w["user"]} if w else None
        lists = []
        coll = m.get("collection") or {}
        if coll.get("id"):
            found = next((c for c in services.cached("library-collections", 600, lambda: services._api(reelix, "/collections") or [])
                          if c.get("id") == coll["id"]), None)
            if found:
                rows = [_row(str(x.get("year") or ""), x.get("title"), "", "in_library" if x.get("has_file") else
                             "wanted" if x.get("movie_id") else "not_monitored",
                             href=f"/library-film.html?id={x['movie_id']}" if x.get("movie_id") else "",
                             note="" if x.get("movie_id") else "Not in your library") for x in found.get("movies") or []]
                lists.append({"key": "collection", "label": "Collection", "heading": found.get("title"), "rows": rows})
    elif tab == "tv":
        s = services._api(reelix, f"/series/{item_id}") or {}
        episodes = services._api(reelix, f"/series/{item_id}/episodes") or []
        e = _series(s)
        st = s.get("statistics") or {}
        have, total = int(st.get("episode_file_count") or 0), int(st.get("episode_count") or 0)
        rows, seasons = [], {}
        busy = _queue(reelix)
        w = _watched.series(cfg, s.get("tmdb_id")) if cfg else None
        seen = (w or {}).get("episodes") or {}
        for ep in sorted(episodes, key=lambda x: (x.get("season_number") or 0, x.get("episode_number") or 0)):
            aired = ep.get("air_date") or ""
            status = "in_library" if ep.get("has_file") else "downloading" if ("episode", ep.get("id")) in busy else \
                "not_released" if (not aired or aired > today) else "wanted" if ep.get("monitored", True) else "not_monitored"
            jf = seen.get((int(ep.get("season_number") or 0), int(ep.get("episode_number") or 0)))
            row = _row(f"E{ep.get('episode_number', 0)}", ep.get("title"), aired, status, id=ep.get("id"),
                       can_get=status in ("wanted", "not_monitored"),
                       watched=jf["watched"] if jf else None, jf=jf["id"] if jf else None)
            rows.append(row)
            seasons.setdefault(int(ep.get("season_number") or 0), []).append(row)
        out = {"title": s.get("title"), "meta": [x for x in (s.get("network") or "", e["m"].split(" · ")[-1] if e["m"] else "",
                                                             {"continuing": "Continuing", "ended": "Ended", "upcoming": "Coming soon"}.get(s.get("status"), ""))
                                                 if x],
               "overview": s.get("overview") or "", "status": e["w"],
               "progress": {"have": have, "total": total, "text": f"{have:,} of {total:,} episodes in your library"} if total else None,
               "open": _open(reelix, f"/series/{item_id}"),
               "can": {"get": any(r.get("can_get") for r in rows), "follow": bool(s.get("monitored")), "delete": True,
                       "has_file": have > 0}}
        have_jf = [r for r in rows if r.get("jf")]
        out["watched"] = {"watched": bool(have_jf) and all(r["watched"] for r in have_jf), "ids": [r["jf"] for r in have_jf],
                          "user": w["user"]} if have_jf else None
        facts = [("Network", s.get("network")), ("First aired", _date(s.get("first_aired"))), ("Last aired", _date(s.get("last_aired"))),
                 ("Next airing", _date(s.get("next_airing"))), ("Seasons", st.get("season_count")),
                 ("Genres", ", ".join(s.get("genres") or [])), ("Certificate", s.get("certification"))]
        lists = [{"key": "episodes", "label": "Episodes", "heading": "Episodes", "rows": rows, "groups": _seasons(seasons)}]
    elif tab in ("books", "audiobooks"):
        b = services._api(reelix, f"/books/{item_id}") or {}
        fmt = "ebook" if tab == "books" else "audiobook"
        e = _book(b, fmt, today) or _entry(item_id, b.get("title"), "", b.get("year"), "", "not_monitored", "", 0, [])
        both = [label for key, label in (("ebook_file", "ebook"), ("audiobook_file", "audiobook")) if b.get(key)]
        out = {"title": b.get("title"), "meta": [x for x in (b.get("author_name") or "", str(b.get("year") or "")) if x],
               "overview": b.get("overview") or "", "status": e["w"], "progress": None,
               "open": _open(reelix, f"/books/book/{item_id}")}
        f = b.get(f"{fmt}_file") or {}
        facts = [("Author", b.get("author_name")), ("Published", _date(b.get("release_date"))), ("Pages", b.get("page_count")),
                 ("In your library as", " and ".join(both) or "Neither yet"), ("Narrated by", (b.get("audiobook_file") or {}).get("narrator")),
                 ("Quality", f.get("quality_name")), ("ISBN", b.get("isbn13"))]
        lists = []
        try:
            index = load(data_dir, reelix, tab)
        except (OSError, ValueError, services.ServiceError):
            index = {"items": []}
        by_id = {x["i"]: x for x in index["items"]}
        allseries = services.cached("library-bookseries", 600, lambda: services._api(reelix, "/bookseries") or [])
        for link in b.get("series") or []:
            found = next((x for x in allseries if x.get("id") == link.get("id")), None)
            if not found:
                continue
            rows, have = [], 0
            for position, book_id in found.get("books") or []:
                x = by_id.get(book_id)
                have += bool(x and x["w"] == "in_library")
                rows.append(_row(f"Book {position}" if position else "", x["t"] if x else "Not in this format",
                                 "", x["w"] if x else "not_monitored",
                                 href=f"/library-{'book' if tab == 'books' else 'audiobook'}.html?id={book_id}" if x else ""))
            lists.append({"key": f"series-{found['id']}", "label": "Reading order", "heading": found.get("title"), "rows": rows})
            if out["progress"] is None and rows:
                out["progress"] = {"have": have, "total": len(rows), "text": f"{have:,} of {len(rows):,} books in your library"}
    elif tab == "music":
        a = services._api(reelix, f"/artists/{item_id}") or {}
        albums = (services._api(reelix, "/albums", {"artist_id": item_id, "page_size": 0}) or {}).get("items") or []
        e = _artist(a)
        st = a.get("statistics") or {}
        have, total = int(st.get("track_file_count") or 0), int(st.get("track_count") or 0)
        rows = []
        for al in albums:
            ast = al.get("statistics") or {}
            h, t = int(ast.get("track_file_count") or 0), int(ast.get("track_count") or 0)
            released = not al.get("release_date") or al["release_date"] <= today
            rows.append(_row(str(al.get("release_date") or "")[:4], al.get("title"), "",
                             "in_library" if t and h >= t else "partly" if h else "wanted" if released else "not_released",
                             note=f"{h} of {t} tracks" if t else ""))
        out = {"title": a.get("name"), "meta": [x for x in (a.get("artist_type") or "", a.get("country") or "",
                                                            _plural(len(albums), "album", "albums")) if x],
               "overview": a.get("overview") or "", "status": e["w"],
               "progress": {"have": have, "total": total, "text": f"{have:,} of {total:,} tracks in your library"} if total else None,
               "open": _open(reelix, f"/music/artists/{item_id}")}
        facts = [("Type", a.get("artist_type")), ("Country", a.get("country")), ("Genres", ", ".join(a.get("genres") or []))]
        lists = [{"key": "albums", "label": "Albums", "heading": "Albums", "rows": rows}]
    elif tab == "radio":
        r = services._api(reelix, f"/radio/shows/{item_id}") or {}
        data = services._api(reelix, f"/radio/shows/{item_id}/episodes") or {}
        base = reelix["url"].rsplit("/api/v1", 1)[0]
        e = _show(r, base)
        series_no = {x.get("id"): x.get("number") for x in data.get("series") or []}
        st = r.get("statistics") or {}
        rows = []
        for ep in sorted(data.get("episodes") or [], key=lambda x: str(x.get("first_broadcast") or ""), reverse=True):
            sn, en = series_no.get(ep.get("series_id")), ep.get("number")
            number = f"S{sn} E{en}" if sn and en else f"E{en}" if en else ""
            rows.append(_row(number, ep.get("title"), ep.get("first_broadcast"), ep.get("status") or "not_released"))
        have, count = int(st.get("in_library_count") or 0), int(st.get("episode_count") or 0)
        out = {"title": r.get("title"), "meta": [x for x in (r.get("station_name") or "", r.get("author") or "",
                                                             _plural(count, "episode", "episodes") if count else "") if x],
               "overview": r.get("synopsis") or "", "status": e["w"],
               "progress": {"have": have, "total": count, "text": f"{have:,} of {count:,} episodes in your library"} if count else None,
               "open": _open(reelix, f"/radio/shows/{item_id}"),
               "listen": {"label": "Listen in Audiobookshelf", "href": r["abs_web_url"]} if str(r.get("abs_web_url") or "").startswith(("http://", "https://")) else None}
        facts = [("Station", r.get("station_name")), ("Presented by", r.get("author")),
                 ("Following", {"all": "Every episode", "from_now_on": "New episodes", "none": "Not following"}.get(r.get("follow"), "")),
                 ("Series", st.get("series_count")), ("Episodes", count), ("Wanted", st.get("wanted_count"))]
        lists = [{"key": "episodes", "label": "Episodes", "heading": "Episodes, newest first", "rows": rows}]
    else:
        raise ValueError("No such Library tab")
    word = STATUS.get(out.pop("status"), ("", "muted"))
    out.update({"id": item_id, "tab": tab, "status": word[0], "tone": word[1], "poster": poster if e.get("p") else "",
                "facts": [{"label": k, "value": str(v)} for k, v in facts if v not in (None, "", 0)], "lists": lists})
    out.setdefault("listen", None)
    return out


# Changing things from the Library (DASH-276, DASH-206) --------------------------------------------------------

ACTIONS = ("get", "follow", "unfollow", "delete")


def act(reelix, tab, item_id, action, scope="item", season=None, episode=None, delete_files=False):
    """Get it (follow and search now), follow, stop following or delete, for a film, or a series, one of its seasons or
    one episode. Uses Reelix's own routes with Starboard's manager key. Returns a sentence of what was done."""
    item_id = int(item_id)
    if action not in ACTIONS:
        raise ValueError("Choose Get it, Follow, Stop following or Delete")
    on = action in ("get", "follow")
    if tab == "films":
        if action == "delete":
            services._api(reelix, f"/movies/{item_id}", {"delete_files": "true" if delete_files else "false"}, method="DELETE")
            return "Deleted from your library" + (", with its files" if delete_files else "; its files stay")
        services._api(reelix, f"/movies/{item_id}", method="PUT", body={"monitored": on})
        if action == "get":
            services._api(reelix, "/search", method="POST", body={"kind": "movie", "ids": [item_id]})
            return "Reelix is searching for it now"
        return "Reelix follows it" if on else "Reelix no longer follows it"
    if tab == "tv":
        if action == "delete":
            services._api(reelix, f"/series/{item_id}", {"delete_files": "true" if delete_files else "false"}, method="DELETE")
            return "Deleted from your library" + (", with its files" if delete_files else "; its files stay")
        if scope == "episode":
            ep = int(episode)
            services._api(reelix, "/episodes/monitor", method="PUT", body={"episode_ids": [ep], "monitored": on})
            if action == "get":
                services._api(reelix, "/search", method="POST", body={"kind": "episode", "ids": [ep]})
        elif scope == "season":
            n = int(season)
            services._api(reelix, "/seasons/monitor", method="PUT", body={"series_id": item_id, "season_number": n, "monitored": on})
            if action == "get":
                services._api(reelix, "/search", method="POST", body={"kind": "season", "ids": [item_id], "season": n})
        else:
            services._api(reelix, f"/series/{item_id}", method="PUT", body={"monitored": on})
            if action in ("get", "unfollow"):  # the whole series: every season follows the series
                episodes = services._api(reelix, f"/series/{item_id}/episodes") or []
                for n in sorted({int(e.get("season_number") or 0) for e in episodes if e.get("season_number")}):
                    services._api(reelix, "/seasons/monitor", method="PUT", body={"series_id": item_id, "season_number": n, "monitored": on})
            if action == "get":
                services._api(reelix, "/search", method="POST", body={"kind": "series", "ids": [item_id]})
        what = {"episode": "this episode", "season": f"season {season}", "item": "the series"}.get(scope, "it")
        if action == "get":
            return f"Reelix is searching for {what} now"
        return f"Reelix follows {what}" if on else f"Reelix no longer follows {what}"
    raise ValueError("Changing these from the Library comes later; open it in Reelix for now")


# Choose a download (DASH-159) ---------------------------------------------------------------------------------

def releases(reelix, tab, item_id, scope="item", season=None, episode=None):
    """What Reelix finds on its sites for a film, a season or an episode, best first, each with whether Reelix would
    take it and why not. An interactive search: it asks every site, so it can take a minute."""
    params = {}
    if tab == "films":
        params["movie_id"] = int(item_id)
    elif tab == "tv" and scope == "episode":
        params["episode_id"] = int(episode)
    elif tab == "tv" and scope == "season":
        params.update(series_id=int(item_id), season=int(season))
    else:
        raise ValueError("Choose a film, a season or an episode")
    found = services._api(reelix, "/releases", params, timeout=120) or []
    out = []
    for r in sorted(found, key=lambda x: (not x.get("accepted"), x.get("rank") or 9999))[:40]:
        q = (r.get("quality") or {}).get("quality") or ""
        out.append({"guid": r.get("guid"), "indexer_id": r.get("indexer_id"), "title": r.get("title") or "", "site": r.get("indexer") or "",
                    "protocol": r.get("protocol") or "", "size": r.get("size") or 0, "age_minutes": r.get("age_minutes"),
                    "seeders": r.get("seeders"), "quality": q if isinstance(q, str) else str(q),
                    "languages": [x.get("name") if isinstance(x, dict) else str(x) for x in r.get("languages") or []][:3],
                    "score": r.get("format_score") or 0, "accepted": bool(r.get("accepted")),
                    "why_not": [x.get("reason") for x in r.get("rejections") or [] if x.get("reason")][:3]})
    return out


def grab(reelix, guid, indexer_id, force=False):
    """Sends one release to the download app, as Get this one; force takes one Reelix would have turned down."""
    if not guid or not str(indexer_id).isdigit():
        raise ValueError("Choose a release from the list")
    services._api(reelix, "/releases/grab", method="POST", body={"guid": str(guid)[:2000], "indexer_id": int(indexer_id), "force": bool(force)},
                  timeout=60)
    return "Sent to the download app. It shows in Downloads in a moment"


# Search ----------------------------------------------------------------------------------------------------

def search_library(data_dir, q, limit=8):
    """The Library first: up to limit matches per tab from the indexes already built, best first."""
    words = fold(q).split()
    if not words:
        return []
    out = []
    for tab in TABS:
        try:
            with open(_path(data_dir, tab), encoding="utf-8") as f:
                items = json.load(f)["items"]
        except (OSError, ValueError, KeyError):
            continue
        hits = [e for e in items if all(w in fold(e["t"]) or w in fold(e.get("m", "")) for w in words)]
        whole = " ".join(words)
        hits.sort(key=lambda e: (fold(e["t"]) != whole, not e["s"].startswith(whole), e["s"]))
        if hits:
            out.append({"tab": tab, "label": LABELS[tab], "count": len(hits), "items": [_card(tab, e) for e in hits[:limit]]})
    return out


def overview(data_dir):
    """Before anything is typed: recently added across the Library, then each tab with its count."""
    recent, tabs = [], []
    for tab in TABS:
        try:
            with open(_path(data_dir, tab), encoding="utf-8") as f:
                items = json.load(f)["items"]
        except (OSError, ValueError, KeyError):
            tabs.append({"tab": tab, "label": LABELS[tab], "count": None})
            continue
        tabs.append({"tab": tab, "label": LABELS[tab], "count": len(items), "noun": NOUNS[tab]})
        newest = sorted(items, key=lambda e: -(e.get("a") or 0))[:12]
        recent.extend((e.get("a") or 0, tab, e) for e in newest)
    recent.sort(key=lambda x: -x[0])
    return {"recent": [dict(_card(tab, e), tab=tab) for _, tab, e in recent[:12]], "tabs": tabs}


LOOKUPS = {  # kind: (path, query name, Starboard's label)
    "films": ("/movies/lookup", "term"),
    "tv": ("/series/lookup", "term"),
    "books": ("/books/lookup", "term"),
    "music": ("/artists/lookup", "term"),
    "radio": ("/radio/search", "q"),
}


def _lookup_one(reelix, kind, q):
    path, name = LOOKUPS[kind]
    items = services._api(reelix, path, {name: q}, timeout=15) or []
    rows = []
    for x in items[:12]:
        if kind in ("films", "tv"):
            key = f"tmdb:{x.get('tmdb_id')}" if x.get("tmdb_id") else f"tvdb:{x.get('tvdb_id')}" if x.get("tvdb_id") else ""
            rows.append({"key": key, "title": x.get("title"), "year": x.get("year"), "detail": "",
                         "image": x.get("poster") or "", "overview": (x.get("overview") or "")[:300],
                         "library_id": x.get("library_id") if x.get("in_library") else None})
        elif kind == "books":
            rows.append({"key": f"olw:{x.get('openlibrary_work_id')}", "title": x.get("title"), "year": x.get("year"),
                         "detail": x.get("author_name") or "", "image": x.get("cover") or "", "overview": "",
                         "library_id": x.get("book_id")})
        elif kind == "music":
            rows.append({"key": f"mb:{x.get('musicbrainz_id')}", "title": x.get("name"), "year": None,
                         "detail": " · ".join(y for y in (x.get("artist_type") or "", x.get("country") or "", x.get("disambiguation") or "") if y),
                         "image": x.get("image") or "", "overview": "", "library_id": x.get("artist_id")})
        else:
            rows.append({"key": f"radio:{x.get('provider')}:{x.get('external_id')}", "title": x.get("title"), "year": None,
                         "detail": " · ".join(y for y in (x.get("station_name") or "", x.get("author") or "") if y),
                         "image": "", "overview": (x.get("synopsis") or "")[:300], "library_id": x.get("show_id")})
    for r in rows:  # pictures come through Starboard, like the Library's own
        r["image"] = f"/api/library/lookup-poster?src={urllib.parse.quote(small(r['image']), safe='')}" if poster_allowed(small(r["image"])) else ""
        r["kind"] = kind
    return [r for r in rows if r["key"] and not r["key"].endswith(":None")]


def lookup(reelix, q, only=""):
    """Not in your library: Reelix's own lookups, for one kind (the page asks for each kind on its own, so a slow
    one does not hold up the others) or every kind at once. One kind failing does not hide the others."""
    q = q.strip()[:120]
    if len(q) < 2:
        return {"groups": [], "errors": []}
    kinds = [only] if only in LOOKUPS else list(LOOKUPS)
    one = lambda kind: services.cached(f"library-lookup-{kind}-{fold(q)}", 300, lambda: _lookup_one(reelix, kind, q))  # noqa: E731
    futures = [(kind, services.POOL.submit(one, kind)) for kind in kinds]
    groups_out, errors = [], []
    for kind, future in futures:
        try:
            rows = future.result(timeout=25)
        except services.ServiceError as e:
            if e.status == 503:
                errors.append({"kind": kind, "message": f"Reelix cannot look up {LABELS[kind].lower()} until it has a TMDB key."})
            elif e.status != 404:
                errors.append({"kind": kind, "message": f"Reelix could not look up {LABELS[kind].lower()}: {e}"})
            continue
        except Exception:  # noqa: BLE001 - one kind failing must not hide the others
            errors.append({"kind": kind, "message": f"Reelix did not answer for {LABELS[kind].lower()}."})
            continue
        rows = [r for r in rows if not r["library_id"]]
        if rows:
            groups_out.append({"kind": kind, "label": LABELS[kind], "items": rows})
    return {"groups": groups_out, "errors": errors}


def add_options(reelix, kind):
    """What the Add slide-out offers: quality profiles and folders for that kind."""
    if kind in ("films", "tv"):
        profiles = services._api(reelix, "/qualityprofiles", {"kind": "video"}) or []
        folders = [f for f in services._api(reelix, "/rootfolders") or [] if f.get("media_kind") == ("movie" if kind == "films" else "series")]
    elif kind == "books":
        profiles = services._api(reelix, "/qualityprofiles", {"kind": "ebook"}) or []
        folders = services._api(reelix, "/bookrootfolders") or []
    elif kind == "music":
        profiles = services._api(reelix, "/qualityprofiles", {"kind": "music"}) or []
        folders = services._api(reelix, "/musicrootfolders") or []
    else:
        return {"profiles": [], "folders": []}
    return {"profiles": [{"id": p["id"], "name": p.get("name", "")} for p in profiles],
            "folders": [{"id": f["id"], "path": f.get("path", ""), "free": f.get("free_space")} for f in folders
                        if f.get("kind", "") != "audiobook"]}


def add(data_dir, reelix, kind, key, choice):
    """Adds one thing to Reelix (or follows a radio show). The key comes from a lookup; nothing else is passed through."""
    search = bool(choice.get("search", True))
    profile = choice.get("profile_id")
    folder = choice.get("folder_id")
    if kind in ("films", "tv", "books", "music") and (not profile or not folder):
        opts = add_options(reelix, kind)
        profile = profile or (opts["profiles"][0]["id"] if opts["profiles"] else None)
        folder = folder or (opts["folders"][0]["id"] if opts["folders"] else None)
        if not profile or not folder:
            raise services.ServiceError("Reelix has no folder for this kind yet. Add one in Settings, Reelix")
    prefix, _, value = key.partition(":")
    if kind == "films" and prefix == "tmdb" and value.isdigit():
        body = {"tmdb_id": int(value), "quality_profile_id": int(profile), "root_folder_id": int(folder), "monitor": "movie_only",
                "minimum_availability": "released", "tags": [], "search_on_add": search}
        done = services._api(reelix, "/movies", method="POST", body=body)
        title = (done or {}).get("title")
    elif kind == "tv" and prefix in ("tmdb", "tvdb") and value.isdigit():
        body = {f"{prefix}_id": int(value), "quality_profile_id": int(profile), "root_folder_id": int(folder), "monitor": "all",
                "series_type": "standard", "season_folder": True, "monitor_new_items": "all", "tags": [], "search_on_add": search}
        done = services._api(reelix, "/series", method="POST", body=body)
        title = (done or {}).get("title")
    elif kind == "books" and prefix == "olw" and re.match(r"^OL\d+W$", value):
        formats = [f for f in choice.get("formats") or ["ebook", "audiobook"] if f in ("ebook", "audiobook")] or ["ebook"]
        body = {"openlibrary_work_id": value, "formats": formats, "quality_profile_id": int(profile), "root_folder_id": int(folder),
                "tags": [], "search_on_add": search}
        done = services._api(reelix, "/books", method="POST", body=body)
        title = (done or {}).get("title")
    elif kind == "music" and prefix == "mb" and re.match(r"^[0-9a-f-]{36}$", value):
        body = {"musicbrainz_id": value, "quality_profile_id": int(profile), "metadata_profile_id": 1, "root_folder_id": int(folder),
                "monitored": True, "monitor": "all", "monitor_new_items": "all", "tags": [], "search_on_add": search}
        done = services._api(reelix, "/artists", method="POST", body=body)
        title = (done or {}).get("name")
    elif kind == "radio" and prefix == "radio":
        provider, _, external = value.partition(":")
        if not re.match(r"^[a-z0-9_]{1,20}$", provider) or not external or len(external) > 500:
            raise ValueError("That show cannot be followed")
        follow = choice.get("follow") if choice.get("follow") in ("all", "from_now_on") else "all"
        done = services._api(reelix, "/radio/shows", method="POST", body={"provider": provider, "external_id": external,
                                                                          "follow": follow, "monitored": True, "tags": []})
        title = (done or {}).get("title")
    else:
        raise ValueError("That cannot be added")
    tab = {"films": "films", "tv": "tv", "books": "books", "music": "music", "radio": "radio"}[kind]
    _background(data_dir, reelix, tab)  # so it shows on the wall soon
    if kind == "books":
        _background(data_dir, reelix, "audiobooks")
    return {"title": title or "It", "tab": tab}


# Saved views -----------------------------------------------------------------------------------------------
# The account's default way to show each tab (sort, Covers or List, size, chip), saved on the server so it follows
# the account to every browser. Reset in Settings, General.

VIEW_KEYS = {"sort": ("az", "added", "year"), "layout": ("covers", "list"), "size": ("small", "medium", "large"), "chip": None}


def _views_path(data_dir):
    return os.path.join(data_dir, "library", "views.json")


def views(data_dir):
    try:
        with open(_views_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_view(data_dir, tab, view):
    if tab not in TABS:
        raise ValueError("No such Library tab")
    clean = {}
    for k, allowed in VIEW_KEYS.items():
        v = view.get(k)
        if v is None or v == "":
            continue
        if allowed is None:
            if k == "chip" and v in [c for c, _ in CHIPS.get(tab, [])]:
                clean[k] = v
        elif v in allowed:
            clean[k] = v
    data = views(data_dir)
    data[tab] = clean
    os.makedirs(os.path.dirname(_views_path(data_dir)), mode=0o700, exist_ok=True)
    tmp = _views_path(data_dir) + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, _views_path(data_dir))
    return data


def reset_views(data_dir):
    try:
        os.remove(_views_path(data_dir))
    except OSError:
        pass
    return {}


def status(data_dir):
    """For Settings: how big each index is and when it was built."""
    out = []
    for tab in TABS:
        try:
            st = os.stat(_path(data_dir, tab))
            out.append({"tab": tab, "label": LABELS[tab], "bytes": st.st_size, "built": int(st.st_mtime)})
        except OSError:
            out.append({"tab": tab, "label": LABELS[tab], "bytes": 0, "built": None})
    with _state_lock:
        errors = dict(_state["errors"])
    return {"tabs": out, "errors": errors}


# Requests --------------------------------------------------------------------------------------------------

def _q(h):
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(h.path).query).items()}


def _int(value, default, low, high):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def handle(h, method, path):
    """Every /api/library request (the server has signed the browser in already)."""
    cfg = h.app.config
    data_dir = cfg.data_dir
    q = _q(h)
    get_reelix = lambda: reelix_of(cfg.data["services"])  # noqa: E731
    if path == "/api/library/views" and method == "GET":
        return h.json(200, {"views": views(data_dir)})
    if path == "/api/library/views" and method == "POST":
        b = h.body()
        return h.json(200, {"views": save_view(data_dir, str(b.get("tab", "")), b.get("view") or {})})
    if path == "/api/library/views" and method == "DELETE":
        return h.json(200, {"views": reset_views(data_dir)})
    if path == "/api/library/lookup-poster" and method == "GET":
        found = poster(data_dir, q.get("src", "")) if cfg.data["show_posters"] else None
        if not found:
            return h.send(404, b"", "text/plain; charset=utf-8", {"Cache-Control": "private, max-age=3600"})
        return h.send(200, found[0], found[1], {"Cache-Control": "private, max-age=604800"})
    reelix = get_reelix()
    if not reelix:
        return h.error(409, "Add Reelix in Settings, Manage apps, with its key, to see your library", reelix=False)
    tab = q.get("tab", "")
    if path == "/api/library/overview" and method == "GET":
        used(data_dir, "", get_reelix)
        for t in TABS:  # tabs never opened yet are built in the background, so the counts fill in
            if not os.path.exists(_path(data_dir, t)):
                _background(data_dir, reelix, t)
        return h.json(200, overview(data_dir))
    if path == "/api/library/search" and method == "GET":
        used(data_dir, "", get_reelix)
        return h.json(200, {"library": search_library(data_dir, q.get("q", "")[:120])})
    if path == "/api/library/lookup" and method == "GET":
        return h.json(200, lookup(reelix, q.get("q", ""), q.get("kind", "")))
    if path == "/api/library/add-options" and method == "GET":
        if q.get("kind") not in LOOKUPS:
            return h.error(400, "Choose films, tv, books, music or radio")
        return h.json(200, add_options(reelix, q["kind"]))
    if path == "/api/library/add" and method == "POST":
        b = h.body()
        kind, key = str(b.get("kind", "")), str(b.get("key", ""))[:600]
        if kind not in LOOKUPS:
            return h.error(400, "Choose films, tv, books, music or radio")
        done = add(data_dir, reelix, kind, key, b.get("options") or {})
        logs.event("info", "library", f"Added {str(done['title'])[:80]} to Reelix from Search")
        return h.json(200, done)
    if path == "/api/library/status" and method == "GET":
        return h.json(200, status(data_dir))
    if tab not in TABS:
        return h.error(400, "Choose a Library tab")
    if path == "/api/library/refresh" and method == "POST":
        refresh(data_dir, reelix, tab)
        return h.json(200, {"ok": True})
    if path == "/api/library/poster" and method == "GET":
        found = None
        if cfg.data["show_posters"]:
            try:
                with open(_path(data_dir, tab), encoding="utf-8") as f:
                    e = find(json.load(f), _int(q.get("id"), 0, 0, 10 ** 12))
            except (OSError, ValueError):
                e = None
            if e and e.get("p"):
                found = poster(data_dir, e["p"], reelix, "page" if q.get("size") == "page" else "wall")
        if not found:
            return h.send(404, b"", "text/plain; charset=utf-8", {"Cache-Control": "private, max-age=3600"})
        return h.send(200, found[0], found[1], {"Cache-Control": "private, max-age=86400"})
    used(data_dir, tab, get_reelix)
    if path == "/api/library/wall" and method == "GET":
        index = load(data_dir, reelix, tab)
        sort = q.get("sort") if q.get("sort") in ("az", "added", "year") else "az"
        until = q.get("until", "") if re.match(r"^[A-Z#]$", q.get("until", "")) else ""
        out = wall(index, tab, q.get("q", "")[:120], q.get("chip", ""), sort, q.get("group", "")[:200],
                   _int(q.get("offset"), 0, 0, 10 ** 6), _int(q.get("limit"), 40, 1, WALL_MAX), until,
                   "authors" if q.get("by") == "authors" else "")
        with _state_lock:
            out["error"] = _state["errors"].get(tab, "")
            out["refreshing"] = tab in _building
        out["view"] = views(data_dir).get(tab, {})
        return h.json(200, out)
    if path == "/api/library/groups" and method == "GET":
        index = load(data_dir, reelix, tab)
        return h.json(200, {"groups": groups(index, tab, "authors" if q.get("by") == "authors" else ""),
                            "label": GROUPS.get(f"{tab}-authors" if q.get("by") == "authors" else tab, "Group")})
    if path == "/api/library/watched" and method == "POST":
        from . import watched as _watched
        b = h.body()
        item_id = _int(b.get("id"), 0, 1, 10 ** 12)
        try:
            n = _watched.mark(cfg, b.get("ids"), bool(b.get("watched")))
        except ValueError as e:
            return h.error(400, str(e))
        except services.ServiceError as e:
            return h.error(502, f"Jellyfin said no: {e}")
        services.forget(f"library-item-{tab}-{item_id}")
        said = ("Marked as watched" if b.get("watched") else "Marked as not watched") + (f" ({n} episodes)" if n > 1 else "")
        return h.json(200, {"said": said, "item": item(data_dir, reelix, tab, item_id, cfg)})
    if path in ("/api/library/releases", "/api/library/grab"):
        try:
            if method == "GET":
                return h.json(200, {"releases": releases(reelix, tab, _int(q.get("id"), 0, 1, 10 ** 12), q.get("scope", "item"),
                                                          q.get("season"), q.get("episode"))})
            b = h.body()
            said = grab(reelix, b.get("guid"), b.get("indexer_id"), bool(b.get("force")))
            logs.event("info", "library", f"Chose a download: {str(b.get('title', ''))[:120]}")
            services.forget("queue")
            return h.json(200, {"said": said})
        except ValueError as e:
            return h.error(400, str(e))
        except services.ServiceError as e:
            return h.error(502, f"Reelix said no: {e}")
    if path == "/api/library/act" and method == "POST":
        b = h.body()
        item_id = _int(b.get("id"), 0, 1, 10 ** 12)
        try:
            said = act(reelix, tab, item_id, str(b.get("action", "")), str(b.get("scope") or "item"), b.get("season"),
                       b.get("episode"), bool(b.get("delete_files")))
        except ValueError as e:
            return h.error(400, str(e))
        except services.ServiceError as e:
            return h.error(502, f"Reelix said no: {e}")
        logs.event("info", "library", f"{tab} {item_id}: {said}")
        services.forget(f"library-item-{tab}-{item_id}")
        if b.get("action") in ("delete",):
            _background(data_dir, reelix, tab)  # the wall loses it
        return h.json(200, {"said": said, "item": None if b.get("action") == "delete" else item(data_dir, reelix, tab, item_id, cfg)})
    if path == "/api/library/item" and method == "GET":
        item_id = _int(q.get("id"), 0, 0, 10 ** 12)
        return h.json(200, services.cached(f"library-item-{tab}-{item_id}", ITEM_SECONDS,
                                           lambda: item(data_dir, reelix, tab, item_id, cfg)))
    return h.error(404, "Not found")
