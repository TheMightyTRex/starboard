"""Bring in media already on disk (DASH-186): films and series in a library folder that Reelix does not know yet,
for a new install whose media was never run by Radarr or Sonarr. Uses Reelix's own library import with Starboard's
manager key (Reelix's "manage library" permission, so no admin password): list the folders, look up the best match
for each in batches of 25, then import the ones you keep. Nothing is downloaded or moved: Reelix adds each film or
series for the folder it is already in and scans its files. Books, audiobooks and music use Reelix's book and music
import (DASH-282), by author or artist folder."""
import os
import json
import urllib.error
import urllib.parse
import urllib.request

KINDS = {"movie": "films", "series": "tv"}
# Books and audiobooks (DASH-282): Reelix keeps their folders apart (/bookrootfolders) and imports by author, matched
# on Open Library. Each author follows only the books already there ("existing"), so bringing in a folder never makes
# Reelix want everything that author wrote.
BOOK_KINDS = {"audiobook": "audiobooks", "ebook": "books"}
BOOK_MONITOR = "existing"
# Music (DASH-282): Reelix keeps music folders apart too (/musicrootfolders) and imports by artist, matched on
# MusicBrainz. Each artist follows only the albums already there, as books do.
MUSIC_TAB = "music"
MUSIC_MONITOR = "existing"
BATCH = 25


class ImportError_(Exception):
    pass


def _reelix(cfg):
    s = next((x for x in cfg.data["services"] if x.get("icon") == "reelix" and x["type"] == "link" and x.get("api_key")), None)
    if not s:
        raise ImportError_("Reelix is not on your apps with its key yet")
    return s["url"].rstrip("/") + "/api/v1", s["api_key"]


def _call(cfg, method, path, body=None, timeout=60):
    base, key = _reelix(cfg)
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Api-Key": key, "Accept": "application/json", "Content-Type": "application/json",
                                          "User-Agent": "Starboard", "X-Reelix-Request": "1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # Reelix's address from Starboard's own apps  # nosec B310
            raw = r.read(20_000_000)
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read(4000)).get("message")
        except ValueError:
            message = None
        raise ImportError_(message or f"Reelix answered {e.code}") from None
    except (urllib.error.URLError, OSError):
        raise ImportError_("Starboard could not reach Reelix") from None
    return json.loads(raw) if raw else None


LEFT_OUT = "import-left-out.json"  # folders the person chose to leave out (owner, 10 November 2026)


def left_out(cfg):
    import json
    try:
        with open(os.path.join(cfg.data_dir, LEFT_OUT), encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, ValueError, TypeError):
        return set()


def leave_out(cfg, paths):
    """Remembers folders the person left out, so Still to set up and the note stop counting them."""
    import json
    keep = sorted((left_out(cfg) | {str(p) for p in paths or [] if isinstance(p, str)}))[-2000:]
    tmp = os.path.join(cfg.data_dir, LEFT_OUT + ".new")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(keep, f)
    os.replace(tmp, os.path.join(cfg.data_dir, LEFT_OUT))
    return len(keep)


def _folder_path(u):
    return u.get("path") if isinstance(u, dict) else str(u)


def _book_tab(tab):
    return tab in BOOK_KINDS.values()


def folders(cfg, tab):
    """The library folders for films or series, each with how many sub-folders Reelix does not know yet (less the
    ones the person left out)."""
    skip = left_out(cfg)
    if tab == MUSIC_TAB:
        return [{"id": f["id"], "path": f["path"],
                 "waiting": len([u for u in f.get("unmapped_folders") or [] if _folder_path(u) not in skip])}
                for f in _call(cfg, "GET", "/musicrootfolders") or [] if f.get("kind", "music") == "music" and f.get("accessible", True)]
    if _book_tab(tab):
        kind = {v: k for k, v in BOOK_KINDS.items()}[tab]
        return [{"id": f["id"], "path": f["path"],
                 "waiting": len([u for u in f.get("unmapped_folders") or [] if _folder_path(u) not in skip])}
                for f in _call(cfg, "GET", "/bookrootfolders") or [] if f.get("kind") == kind and f.get("accessible", True)]
    want = {v: k for k, v in KINDS.items()}.get(tab)
    if not want:
        return []
    return [{"id": f["id"], "path": f["path"],
             "waiting": len([u for u in f.get("unmapped_folders") or [] if _folder_path(u) not in skip])}
            for f in _call(cfg, "GET", "/rootfolders") or [] if f.get("media_kind") == want and f.get("accessible", True)]


def _in_library(cfg, kind):
    """{tmdb_id: (title, folder)} of what Reelix already has, so a folder matched to one is shown as such."""
    path = "/movies" if kind == "movie" else "/series"
    try:
        got = _call(cfg, "GET", f"{path}?page_size=5000", timeout=60) or {}
    except ImportError_:
        return {}
    rows = got.get("items", []) if isinstance(got, dict) else got
    return {r["tmdb_id"]: (r.get("title") or "", os.path.basename(str(r.get("path") or "")))
            for r in rows if isinstance(r, dict) and r.get("tmdb_id")}


def _slim(c, have=None):
    have = have or {}
    return {"path": c["folder"]["path"], "name": c["folder"]["name"], "title": c.get("parsed_title"), "year": c.get("parsed_year"),
            "files": c.get("file_count", 0), "size": c.get("size", 0), "problem": c.get("lookup_error"),
            "matches": [{"tmdb_id": m.get("tmdb_id"), "title": m.get("title"), "year": m.get("year"),
                         "already": have[m["tmdb_id"]][1] if m.get("tmdb_id") in have else None}
                        for m in (c.get("suggestions") or [])[:5] if m.get("tmdb_id")]}


def _slim_book(c, have):
    """A book folder for the dialog: the author Reelix guessed, and Open Library's authors to choose from. `sure`
    (ticked) when the first match has exactly the folder's name and at least three times the works of any other
    author of that name (Open Library keeps small duplicates); two real David Wongs (24 and 14 works) wait for a
    person to choose."""
    fold = lambda t: " ".join(str(t or "").lower().replace(".", " ").split())  # noqa: E731
    sugg = c.get("suggestions") or []
    same = [m for m in sugg if fold(m.get("name")) == fold(c.get("guessed_author") or c.get("folder"))]
    best = max(same, key=lambda m: m.get("work_count") or 0) if same else None
    others = [m.get("work_count") or 0 for m in same if m is not best]
    sure = bool(best) and best is sugg[0] and all((best.get("work_count") or 0) >= 3 * max(n, 1) for n in others)
    return {"sure": sure,"path": c["path"], "name": c.get("folder") or os.path.basename(c["path"]), "title": c.get("guessed_author"),
            "year": None, "files": c.get("file_count", 0), "size": c.get("size", 0), "problem": c.get("lookup_error"),
            "matches": book_matches(c.get("suggestions") or [])}


def _short(text, most):
    """`text` with spaces tidied, cut at a word to at most `most` characters, with an ellipsis when cut."""
    text = " ".join(str(text or "").split())
    if len(text) <= most:
        return text
    cut = text[:most - 1].rsplit(" ", 1)[0].rstrip(" ,;:.(")
    return f"{cut}…"


def book_matches(sugg):
    """Open Library's authors as drop-down options that read well (owner, 13 November 2026: the names displayed
    badly): the name tidied and kept short, then how many works and the best known one, short; an author listed
    twice with no works is left out."""
    out, seen = [], set()
    for m in sugg:
        if not m.get("openlibrary_id"):
            continue
        name = _short(m.get("name"), 60)
        folded = name.lower().replace(".", "")
        works = m.get("work_count") or 0
        if folded in seen and not works:
            continue  # the same name again, with nothing to tell it apart
        seen.add(folded)
        detail = ", ".join(x for x in (
            (f"{works} work" if works == 1 else f"{works} works") if works else "no works listed",
            f"best known for {_short(m['top_work'], 45)}" if m.get("top_work") else "") if x)
        out.append({"id": m["openlibrary_id"], "title": name, "year": None, "detail": detail,
                    "already": "your library" if m.get("author_id") else None})
        if len(out) == 5:
            break
    return out


def scan_books(cfg, root_id, start=0):
    """One page of book or audiobook folders (author folders), each with Open Library's best authors."""
    root_id = int(root_id)
    listed = _call(cfg, "GET", f"/bookimport/scan?{urllib.parse.urlencode({'root_folder_id': root_id, 'lookup': 'false'})}", timeout=120) or []
    skip = left_out(cfg)
    listed = [c for c in listed if c["path"] not in skip]
    page = listed[int(start):int(start) + BATCH]
    matched = _call(cfg, "POST", "/bookimport/match", {"root_folder_id": root_id, "paths": [c["path"] for c in page]}, timeout=180) if page else []
    return {"total": len(listed), "start": int(start), "items": [_slim_book(c, None) for c in matched or []]}


def run_books(cfg, root_id, items):
    """Adds the kept author folders, each following only the books already there. Returns {added, errors}."""
    root_id = int(root_id)
    keep = [{"path": str(i["path"]), "openlibrary_id": str(i["id"])} for i in items or []
            if isinstance(i, dict) and i.get("id") and str(i["id"]).startswith("OL")]
    if not keep:
        raise ImportError_("Choose a match for at least one folder")
    # Reelix needs a quality profile of the folder's own kind: an audiobook folder an audiobook profile, a book folder
    # an ebook profile (owner's server, 11 November 2026: without one every author was refused).
    kind = next((f.get("kind") for f in _call(cfg, "GET", "/bookrootfolders") or [] if f.get("id") == root_id), "audiobook")
    profiles = _call(cfg, "GET", f"/qualityprofiles?kind={'audiobook' if kind == 'audiobook' else 'ebook'}") or []
    if not profiles:
        raise ImportError_(f"Reelix has no {'audiobook' if kind == 'audiobook' else 'ebook'} quality profile. Add one in Reelix first")
    field = "audio_quality_profile_id" if kind == "audiobook" else "quality_profile_id"
    body = {"root_folder_id": root_id, "items": [{**i, "monitor": BOOK_MONITOR, field: profiles[0]["id"]} for i in keep]}
    out = _call(cfg, "POST", "/bookimport", body, timeout=300) or {}
    return {"added": len(out.get("added") or []), "errors": [{"path": e.get("path"), "message": e.get("message")} for e in out.get("errors") or []]}


def _slim_artist(c):
    """An artist folder for the dialog: MusicBrainz's artists to choose from, with what tells two of the same name
    apart (MusicBrainz's own note, group or person, country). `sure` (ticked) when the first match has exactly the
    folder's name and no other match has it; two bands called Nirvana wait for a person to choose."""
    fold = lambda t: " ".join(str(t or "").lower().replace(".", " ").split())  # noqa: E731
    sugg = [m for m in c.get("suggestions") or [] if m.get("musicbrainz_id")]
    name = fold(c.get("guessed_artist") or c.get("folder"))
    same = [m for m in sugg if fold(m.get("name")) == name]
    sure = len(same) == 1 and same[0] is sugg[0] and not sugg[0].get("artist_id")
    words = {"Group": "band", "Person": "person", "Orchestra": "orchestra", "Choir": "choir"}
    return {"sure": sure, "path": c["path"], "name": c.get("folder") or os.path.basename(c["path"]), "title": c.get("guessed_artist"),
            "year": None, "files": c.get("file_count", 0), "size": c.get("size", 0), "problem": c.get("lookup_error"),
            "matches": [{"id": m["musicbrainz_id"], "title": m.get("name"), "year": None,
                         "detail": ", ".join(x for x in (m.get("disambiguation") or "", words.get(m.get("artist_type"), ""),
                                                         m.get("country") or "") if x),
                         "already": "your library" if m.get("artist_id") else None}
                        for m in sugg[:5]]}


def scan_music(cfg, root_id, start=0):
    """One page of artist folders, each with MusicBrainz's best artists."""
    root_id = int(root_id)
    listed = _call(cfg, "GET", f"/musicimport/scan?{urllib.parse.urlencode({'root_folder_id': root_id, 'lookup': 'false'})}", timeout=120) or []
    skip = left_out(cfg)
    listed = [c for c in listed if c["path"] not in skip]
    page = listed[int(start):int(start) + BATCH]
    matched = _call(cfg, "POST", "/musicimport/match", {"root_folder_id": root_id, "paths": [c["path"] for c in page]}, timeout=180) if page else []
    return {"total": len(listed), "start": int(start), "items": [_slim_artist(c) for c in matched or []]}


def run_music(cfg, root_id, items):
    """Adds the kept artist folders, each following only the albums already there, with Reelix's first music quality
    profile and first metadata profile. Returns {added, errors}."""
    root_id = int(root_id)
    keep = [{"path": str(i["path"]), "musicbrainz_id": str(i["id"])} for i in items or []
            if isinstance(i, dict) and i.get("id") and len(str(i["id"])) == 36 and str(i["id"]).count("-") == 4]
    if not keep:
        raise ImportError_("Choose a match for at least one folder")
    profiles = _call(cfg, "GET", "/qualityprofiles?kind=music") or []
    if not profiles:
        raise ImportError_("Reelix has no music quality profile. Add one in Reelix first")
    metadata = _call(cfg, "GET", "/metadataprofiles") or []
    if not metadata:
        raise ImportError_("Reelix has no music metadata profile. Add one in Reelix first")
    body = {"root_folder_id": root_id, "items": [{**i, "monitor": MUSIC_MONITOR, "quality_profile_id": profiles[0]["id"],
                                                  "metadata_profile_id": metadata[0]["id"]} for i in keep]}
    out = _call(cfg, "POST", "/musicimport", body, timeout=300) or {}
    return {"added": len(out.get("added") or []), "errors": [{"path": e.get("path"), "message": e.get("message")} for e in out.get("errors") or []]}


def scanner(tab):
    """The scan and the run for a Library tab: films and series, books and audiobooks, or music."""
    if tab == MUSIC_TAB:
        return scan_music, run_music
    if _book_tab(tab):
        return scan_books, run_books
    return scan, run


def scan(cfg, root_id, start=0):
    """One page of folders (25), each with Reelix's best matches, and how many there are in all."""
    root_id = int(root_id)
    listed = _call(cfg, "GET", f"/libraryimport/scan?{urllib.parse.urlencode({'root_folder_id': root_id, 'lookup': 'false'})}") or []
    skip = left_out(cfg)
    listed = [c for c in listed if c["folder"]["path"] not in skip]
    page = listed[int(start):int(start) + BATCH]
    matched = _call(cfg, "POST", "/libraryimport/match", {"root_folder_id": root_id, "paths": [c["folder"]["path"] for c in page]}) if page else []
    kind = next((c.get("media_kind") for c in matched or [] if c.get("media_kind")), None) or \
        next((f.get("media_kind") for f in _call(cfg, "GET", "/rootfolders") or [] if f.get("id") == root_id), "series")
    have = _in_library(cfg, kind) if matched else {}
    return {"total": len(listed), "start": int(start), "items": [_slim(c, have) for c in matched or []]}


def run(cfg, root_id, items):
    """Imports the kept folders with Reelix's first film and series quality profile. Returns {added, errors}."""
    root_id = int(root_id)
    keep = [{"path": str(i["path"]), "tmdb_id": int(i["tmdb_id"])} for i in items or [] if i.get("tmdb_id")]
    if not keep:
        raise ImportError_("Choose a match for at least one folder")
    profiles = [p for p in _call(cfg, "GET", "/qualityprofiles") or [] if p.get("family", "video") == "video"]
    if not profiles:
        raise ImportError_("Reelix has no film and series quality profile")
    body = {"root_folder_id": root_id, "search_on_add": False,
            "items": [{**i, "quality_profile_id": profiles[0]["id"]} for i in keep]}
    out = _call(cfg, "POST", "/libraryimport", body, timeout=300) or {}
    return {"added": len(out.get("added") or []), "errors": [{"path": e.get("path"), "message": e.get("message")} for e in out.get("errors") or []]}
