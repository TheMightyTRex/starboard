"""Listening progress into Audiobookshelf: where each person is in each audiobook, from Plex, Jellyfin, Emby or
another Audiobookshelf (Settings, Apps, Audiobookshelf).

1. Read it into data/imports/listening.json (one list of books per account):
   - a Plex server, with its token: the token owner's account, from music libraries that hold audiobooks;
   - a Jellyfin or Emby server, with an API key: every user, from audiobooks in a Books library;
   - another Audiobookshelf, with an admin API key: every user.
   A book in several files (Plex albums, Jellyfin folders) becomes one position: the earlier files' lengths plus
   the place in the current file.
2. Match each account to an Audiobookshelf user (the same name is matched for you).
3. Apply: each book is matched by ASIN, then ISBN, then title and author, then its folder. Progress a person
   already has in Audiobookshelf is never changed, and each book is written once (data/imports/listening-applied.json).
   Books that do not match are listed, so you can fix their details or wait for them to be scanned in.

Audiobookshelf keeps progress per person, so Starboard uses the admin API key from Manage apps to make a key that
acts as each person for a few minutes, writes their progress with it, and deletes it straight after.
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request

from .migrate import _all_items, _load, _mb, _save, folder
from .services import USER_AGENT, ServiceError, _fetch

KEY_NAME = "Starboard listening progress"
KEY_SECONDS = 900  # the key acting as one person ends by itself after 15 minutes, even if deleting it fails


# Audiobookshelf ----------------------------------------------------------------------------

def _abs(service, path, method="GET", body=None, key=None, timeout=60):
    headers = {"Authorization": f"Bearer {key or service.get('api_key', '')}", "Accept": "application/json", "User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(service["url"].rstrip("/") + "/api" + path, data=data, headers=headers, method=method)
    return _fetch(service, req, timeout)


def abs_app(services):
    return next((s for s in services if s["type"] == "audiobookshelf" and s.get("enabled", True) and s.get("url") and s.get("api_key")), None)


def abs_users(service):
    return [u for u in (_abs(service, "/users") or {}).get("users") or [] if u.get("isActive", True)]


def abs_books(service):
    """Every book in every book library, a page of 200 at a time."""
    out = []
    for lib in (_abs(service, "/libraries") or {}).get("libraries") or []:
        if lib.get("mediaType", "book") != "book":
            continue
        page = 0
        while True:
            q = urllib.parse.urlencode({"limit": 200, "page": page, "minified": 1})
            r = _abs(service, f"/libraries/{lib['id']}/items?{q}") or {}
            items = r.get("results") or []
            for it in items:
                media = it.get("media") or {}
                meta = media.get("metadata") or {}
                out.append({"id": it["id"], "title": meta.get("title") or "", "author": meta.get("authorName") or "",
                            "asin": meta.get("asin") or "", "isbn": meta.get("isbn") or "", "folder": it.get("path") or "",
                            "duration_s": media.get("duration") or 0})
            page += 1
            if not items or page * 200 >= (r.get("total") or 0):
                break
    return out


# Reading progress ------------------------------------------------------------------------

def _book(tracks):
    """One position from the files of one book. Each track: order, duration_ms, position_ms, played, last (seconds)."""
    tracks = sorted(tracks, key=lambda t: t["order"])
    total = sum(t["duration_ms"] for t in tracks)
    current = max((t for t in tracks if t["position_ms"]), key=lambda t: t["last"] or 0, default=None)
    if current is None:
        played = [i for i, t in enumerate(tracks) if t["played"]]
        if not played:
            return None
        upto = played[-1]
        position = sum(t["duration_ms"] for t in tracks[:upto + 1])
    else:
        upto = tracks.index(current)
        position = sum(t["duration_ms"] for t in tracks[:upto]) + current["position_ms"]
    finished = all(t["played"] for t in tracks) or (current is None and upto == len(tracks) - 1)
    last = max((t["last"] or 0) for t in tracks) or None
    return {"position_s": round(position / 1000, 1), "duration_s": round(total / 1000, 1), "finished": finished,
            "finished_at": last if finished else None, "updated": last}


def _folder_of(path):
    path = (path or "").replace("\\", "/")
    return path.rsplit("/", 1)[0] if re.search(r"\.[A-Za-z0-9]{2,5}$", path) else path


def read_plex(url, token):
    """The token owner's progress, from Plex music libraries that hold audiobooks (an album is a book)."""
    service = {"name": "Plex", "url": url}

    def get(path, start=None):
        params = {"X-Plex-Token": token}
        if start is not None:
            params.update({"X-Plex-Container-Start": start, "X-Plex-Container-Size": 2000})
        sep = "&" if "?" in path else "?"
        req = urllib.request.Request(f"{url.rstrip('/')}{path}{sep}{urllib.parse.urlencode(params)}",
                                     headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        return (_fetch(service, req, 180) or {}).get("MediaContainer") or {}

    sections = [s for s in get("/library/sections").get("Directory") or [] if s.get("type") == "artist"
                and (re.search(r"book", s.get("title", ""), re.I) or re.search(r"audnexus|audiobook", s.get("agent", ""), re.I))]
    if not sections:
        raise ValueError("No Plex library looks like audiobooks. Its name needs the word book, or it needs the Audnexus agent")
    owner = (get("/myplex/account") or {}).get("username") or "Plex"
    albums = {}
    for section in sections:
        start = 0
        while True:
            page = get(f"/library/sections/{section['key']}/all?type=10", start).get("Metadata") or []
            for t in page:
                part = ((t.get("Media") or [{}])[0].get("Part") or [{}])[0]
                albums.setdefault(t.get("parentRatingKey"), {"title": t.get("parentTitle") or "", "author": t.get("grandparentTitle") or "",
                                                            "folder": _folder_of(part.get("file")), "tracks": []})["tracks"].append(
                    {"order": ((t.get("parentIndex") or 1), (t.get("index") or 0)), "duration_ms": t.get("duration") or 0,
                     "position_ms": t.get("viewOffset") or 0, "played": bool(t.get("viewCount")), "last": t.get("lastViewedAt")})
            start += len(page)
            if len(page) < 2000:
                break
    entries = []
    for a in albums.values():
        pos = _book(a["tracks"])
        if pos:
            entries.append({"title": a["title"], "author": a["author"], "asin": "", "isbn": "", "folder": a["folder"], **pos})
    return {owner: entries} if entries else {}


def _iso_seconds(value):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:32]).timestamp() if value else None
    except ValueError:
        return None


def read_media_server(url, api_key, name="Jellyfin"):
    """Every user's progress, from audiobooks in a Jellyfin or Emby Books library. Files that share an album are one book."""
    service = {"name": name, "url": url, "api_key": api_key}
    accounts = {}
    for user in _mb(service, "/Users") or []:
        books = {}
        for it in _all_items(service, f"/Users/{user['Id']}/Items", {"Recursive": "true", "IncludeItemTypes": "AudioBook",
                                                                     "Fields": "ProviderIds,Path", "EnableImages": "false"}):
            ud = it.get("UserData") or {}
            author = it.get("AlbumArtist") or ", ".join(it.get("Artists") or [])
            key = ("album", it.get("ParentId"), it["Album"]) if it.get("Album") else ("item", it["Id"])
            ids = {k.lower(): v for k, v in (it.get("ProviderIds") or {}).items()}
            b = books.setdefault(key, {"title": it.get("Album") or it.get("Name") or "", "author": author,
                                       "asin": ids.get("audible") or ids.get("asin") or "", "isbn": ids.get("isbn") or "",
                                       "folder": _folder_of(it.get("Path")), "tracks": []})
            b["tracks"].append({"order": ((it.get("ParentIndexNumber") or 1), (it.get("IndexNumber") or 0), it.get("Name") or ""),
                                "duration_ms": int((it.get("RunTimeTicks") or 0) / 10000),
                                "position_ms": int((ud.get("PlaybackPositionTicks") or 0) / 10000),
                                "played": bool(ud.get("Played")), "last": _iso_seconds(ud.get("LastPlayedDate"))})
        entries = []
        for b in books.values():
            pos = _book(b.pop("tracks"))
            if pos:
                entries.append({**b, **pos})
        if entries:
            accounts[user["Name"]] = entries
    return accounts


def read_abs(url, api_key):
    """Every user's progress from another Audiobookshelf, with an admin API key."""
    service = {"name": "Audiobookshelf", "url": url, "api_key": api_key}
    books = {b["id"]: b for b in abs_books(service)}
    accounts = {}
    for user in abs_users(service):
        progress = (_abs(service, f"/users/{user['id']}") or {}).get("mediaProgress") or []
        entries = []
        for p in progress:
            b = books.get(p.get("libraryItemId"))
            if not b or p.get("episodeId") or not (p.get("currentTime") or p.get("isFinished")):
                continue
            entries.append({"title": b["title"], "author": b["author"], "asin": b["asin"], "isbn": b["isbn"], "folder": b["folder"],
                            "position_s": round(p.get("currentTime") or 0, 1), "duration_s": round(p.get("duration") or b["duration_s"] or 0, 1),
                            "finished": bool(p.get("isFinished")), "finished_at": (p.get("finishedAt") or 0) / 1000 or None,
                            "updated": (p.get("lastUpdate") or 0) / 1000 or None})
        if entries:
            accounts[user["username"]] = entries
    return accounts


# Keeping it ----------------------------------------------------------------------------------

def _paths(data_dir):
    d = folder(data_dir)
    return {k: os.path.join(d, f"listening{s}.json") for k, s in
            (("progress", ""), ("mapping", "-mapping"), ("applied", "-applied"), ("result", "-result"))}


def save_progress(data_dir, source, accounts):
    p = _paths(data_dir)
    _save(p["progress"], {"source": source, "imported": time.time(), "accounts": accounts})
    mapping = _load(p["mapping"], {})
    _save(p["mapping"], {name: mapping.get(name, "") for name in accounts})


def status(data_dir, services):
    p = _paths(data_dir)
    progress = _load(p["progress"], {})
    mapping = _load(p["mapping"], {})
    applied = _load(p["applied"], {})
    target = abs_app(services)
    users, problem = [], None
    if target:
        try:
            users = [u["username"] for u in abs_users(target)]
        except ServiceError as e:
            problem = str(e)
    lower = {u.lower(): u for u in users}
    accounts = []
    for name, entries in (progress.get("accounts") or {}).items():
        entries = [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []
        to = mapping.get(name, "")
        accounts.append({"name": name, "books": len(entries), "finished": sum(bool(e.get("finished")) for e in entries),
                         "abs_user": to, "suggested": lower.get(name.lower(), ""), "applied": len(applied.get(to, [])) if to else 0})
    accounts.sort(key=lambda a: -a["books"])
    return {"source": progress.get("source"), "imported": progress.get("imported"), "accounts": accounts, "abs_users": users,
            "abs": bool(target), "abs_problem": problem, "last": _load(p["result"], None),
            "abs_link": any(s["type"] == "link" and "audiobookshelf" in s.get("name", "").lower() for s in services)}


def set_mapping(data_dir, mapping):
    p = _paths(data_dir)
    known = (_load(p["progress"], {}).get("accounts") or {}).keys()
    current = _load(p["mapping"], {})
    for k, v in mapping.items():
        if k in known:
            current[k] = str(v or "")[:100]
    _save(p["mapping"], current)


# Matching and applying ---------------------------------------------------------------------

def _words(text):
    text = re.sub(r"[^a-z0-9 ]+", " ", str(text or "").lower())
    return re.sub(r"^(the|a|an) ", "", re.sub(r"\s+", " ", text).strip())


def _keys(book):
    """Every key a book can be matched on, strongest first."""
    keys = []
    if book.get("asin"):
        keys.append(("asin", str(book["asin"]).strip().upper()))
    isbn = re.sub(r"[^0-9Xx]", "", str(book.get("isbn") or ""))
    if len(isbn) in (10, 13):
        keys.append(("isbn", isbn.upper()))
    title = _words(book.get("title"))
    author = _words(re.split(r",|&| and |;", str(book.get("author") or ""))[0])
    if title:
        keys.append(("title", title, author))
        short = _words(str(book.get("title")).split(":")[0])
        if short and short != title:
            keys.append(("title", short, author))
    parts = [x for x in _folder_of(book.get("folder")).lower().split("/") if x]
    if len(parts) >= 2:
        keys.append(("folder", "/".join(parts[-2:])))
    return keys


class Index:
    def __init__(self, books):
        self.by_key = {}
        for b in books:
            for k in _keys(b):
                self.by_key.setdefault(k, b)

    def find(self, entry):
        return next((self.by_key[k] for k in _keys(entry) if k in self.by_key), None)


def _payload(entry, book):
    """Audiobookshelf's progress for one book. A position from a different edition is scaled to this one's length."""
    duration = book["duration_s"] or entry.get("duration_s") or 0
    position = entry.get("position_s") or 0
    if entry.get("duration_s") and duration and abs(entry["duration_s"] - duration) / duration > 0.02:
        position = position * duration / entry["duration_s"]
    position = min(position, duration) if duration else position
    out = {"libraryItemId": book["id"], "duration": duration, "currentTime": round(position, 1),
           "progress": round(position / duration, 4) if duration else 0, "isFinished": bool(entry.get("finished"))}
    if entry.get("finished"):
        out.update(currentTime=duration or position, progress=1)
        if entry.get("finished_at"):
            out["finishedAt"] = int(entry["finished_at"] * 1000)
    return out


def apply(data_dir, services):
    """Writes the progress into Audiobookshelf. Returns a sentence."""
    target = abs_app(services)
    if not target:
        raise ValueError("Add Audiobookshelf with an admin API key in Manage apps first")
    p = _paths(data_dir)
    progress = _load(p["progress"], {}).get("accounts") or {}
    mapping = _load(p["mapping"], {})
    applied = _load(p["applied"], {})
    users = {u["username"].lower(): u for u in abs_users(target)}
    index = Index(abs_books(target))
    written = kept = 0
    unmatched, problems = [], []
    for account, to in mapping.items():
        user = users.get((to or "").lower())
        if not user or account not in progress:
            continue
        done = set(applied.get(to, []))
        have = {m.get("libraryItemId") for m in (_abs(target, f"/users/{user['id']}") or {}).get("mediaProgress") or []
                if m.get("currentTime") or m.get("isFinished")}
        payloads = {}
        for e in progress[account]:
            book = index.find(e)
            if not book:
                unmatched.append({"account": account, "title": e.get("title", ""), "author": e.get("author", "")})
                continue
            if book["id"] in done or book["id"] in payloads:
                continue
            if book["id"] in have:
                kept += 1
                done.add(book["id"])
                continue
            payloads[book["id"]] = _payload(e, book)
        if payloads:
            try:
                _write_as(target, user, list(payloads.values()))
                written += len(payloads)
                done.update(payloads)
            except (ServiceError, ValueError) as e:
                problems.append(f"{to}: {e}")
        applied[to] = sorted(done)
    _save(p["applied"], applied)
    seen = set()
    unmatched = [u for u in unmatched if not ((u["account"], u["title"]) in seen or seen.add((u["account"], u["title"])))]
    sentence = f"Wrote {written} {'book' if written == 1 else 'books'}; kept {kept} that already had progress; {len(unmatched)} not found in Audiobookshelf"
    _save(p["result"], {"finished": time.time(), "written": written, "kept": kept, "unmatched": unmatched[:300],
                        "unmatched_count": len(unmatched), "problems": problems})
    if problems:
        raise ValueError(f"{sentence}. Could not write for {'; '.join(problems)}"[:300])
    return sentence


def _write_as(target, user, payloads):
    """Writes one person's progress with a key that acts as them, then deletes the key."""
    made = (_abs(target, "/api-keys", "POST", {"name": KEY_NAME, "userId": user["id"], "expiresIn": KEY_SECONDS, "isActive": True}) or {}).get("apiKey") or {}
    if not made.get("apiKey"):
        raise ValueError("Audiobookshelf did not make a key for this person. The API key in Manage apps must belong to an admin")
    try:
        for start in range(0, len(payloads), 100):
            _abs(target, "/me/progress/batch/update", "PATCH", payloads[start:start + 100], key=made["apiKey"])
    finally:
        try:
            _abs(target, f"/api-keys/{made['id']}", "DELETE")
        except ServiceError:
            pass  # it ends by itself after KEY_SECONDS
