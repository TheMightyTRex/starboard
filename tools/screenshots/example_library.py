"""A made-up Reelix library for the screenshots and journeys (the Library and Search, DASH-163 and DASH-162).

Nothing real: titles are made from word lists, and each poster is a small picture of two colours drawn here, served
from the made-up Reelix's own address so Starboard fetches it like a real poster. example_server.py answers with
answer(path, query) for GET and add(path, body) for POST under /reelix/api/v1.
"""
import datetime as dt
import os
import random
import struct
import zlib

rnd = random.Random(2026)
TODAY = dt.date.today()
WORDS_A = ["Harbour", "Northern", "Copper", "Midnight", "Quiet", "Paper", "Salt", "Winter", "Glass", "Small", "Tide",
           "Long", "Lantern", "Hidden", "Silver", "Wild", "Distant", "Golden", "Iron", "Velvet"]
WORDS_B = ["Street", "Line", "Valley", "Garden", "Coast", "Planets", "Marsh", "Map", "Orchard", "Hours", "Water",
           "Field", "Keepers", "Station", "Island", "River", "Signal", "Crossing", "Archive", "Bridge"]
PALETTE = [(31, 79, 102), (50, 58, 119), (19, 92, 46), (107, 47, 90), (138, 90, 31), (122, 46, 59), (47, 93, 80), (91, 63, 122)]


def _titles(n, seed):
    r = random.Random(seed)
    out, seen = [], set()
    while len(out) < n:
        t = f"{r.choice(['', '', 'The ', 'A '])}{r.choice(WORDS_A)} {r.choice(WORDS_B)}"
        if r.random() < 0.08:
            t = f"{r.randint(2, 99)} {r.choice(WORDS_B)}"
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def png(n, w=92, h=138):
    """A poster-shaped picture: two colours from the palette, top to bottom, with a lighter band."""
    top, bottom = PALETTE[n % len(PALETTE)], PALETTE[(n * 3 + 1) % len(PALETTE)]
    rows = []
    for y in range(h):
        t = y / (h - 1)
        c = [int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)]
        if h * 0.62 < y < h * 0.7:
            c = [min(255, v + 60) for v in c]
        rows.append(b"\x00" + bytes(c) * w)
    raw = zlib.compress(b"".join(rows))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


BASE = os.environ.get("EXAMPLE_REELIX_BASE", "")  # set by example_server: http://127.0.0.1:PORT/reelix


def _poster(n):
    return f"{BASE}/posters/{n}.png" if n % 7 else None  # a few have no poster, as in real libraries


def _added(n):
    return (dt.datetime(2026, 1, 1) + dt.timedelta(days=(n * 37) % 300)).isoformat() + "Z"


FILMS = []
for i, t in enumerate(_titles(64, 1), 1):
    year = 1975 + (i * 7) % 52
    status = "announced" if year > 2026 else "released"
    FILMS.append({"id": i, "title": t, "sort_title": "", "year": year, "status": status, "has_file": status == "released" and i % 5 != 0,
                  "monitored": True, "runtime_minutes": 85 + i % 70, "certification": ["U", "PG", "12A", "15"][i % 4],
                  "images": {"poster": _poster(i)}, "added": _added(i), "overview": "A made-up film for the preview.",
                  "studio": "Example Pictures", "genres": ["Drama"], "collection": {"id": 1, "title": "The Harbour Films"} if i in (3, 9, 27) else None})
SERIES = []
for i, t in enumerate(_titles(30, 2), 1):
    total = 6 + i % 20
    SERIES.append({"id": i, "title": t, "sort_title": "", "year": 2000 + i % 25, "status": "continuing" if i % 3 else "ended",
                   "network": ["BBC One", "Channel 4", "ITV1", "Sky Atlantic"][i % 4], "last_aired": f"{2001 + i % 25}-03-01",
                   "images": {"poster": _poster(i + 100)}, "added": _added(i + 3), "overview": "A made-up series for the preview.",
                   "statistics": {"episode_file_count": total if i % 4 else total // 2, "episode_count": total, "season_count": 2},
                   "first_aired": f"{2000 + i % 25}-01-10", "genres": ["Drama"]})
AUTHORS = ["Mara Ellison", "Owen Brightwater", "Lise Moreau", "Tomas Ferrand", "J. Okafor"]
BOOKS = []
for i, t in enumerate(_titles(40, 3), 1):
    BOOKS.append({"id": i, "title": t, "sort_title": "", "year": 1990 + i % 36, "release_date": f"{1990 + i % 36}-05-01",
                  "author_name": AUTHORS[i % 5], "images": {"poster": _poster(i + 200)}, "added": _added(i + 5),
                  "monitored_ebook": i % 3 != 0, "monitored_audiobook": i % 2 == 0, "ebook_file": {"id": i, "quality_name": "EPUB"} if i % 4 else None,
                  "audiobook_file": {"id": i, "narrator": "Sam Oduya"} if i % 6 == 0 else None, "overview": "A made-up book for the preview.",
                  "series": [{"id": 1, "title": "The Glass Harbour", "position": str(i // 4 + 1)}] if i % 4 == 0 else []})
ARTISTS = [{"id": i, "name": t, "sort_name": "", "images": {"poster": _poster(i + 300)}, "added": _added(i + 7), "country": "GB",
            "statistics": {"album_count": 1 + i % 4, "track_count": 10 + i, "track_file_count": 10 + i if i % 3 else 6}}
           for i, t in enumerate(_titles(20, 4), 1)]
SHOWS = [{"id": i, "title": t, "sort_title": "", "station_name": ["BBC Radio 4", "BBC Radio 4 Extra", "BBC 6 Music"][i % 3],
          "has_artwork": False, "added_at": _added(i + 9), "synopsis": "A made-up radio show for the preview.", "follow": "all",
          "statistics": {"in_library_count": 4 + i % 9, "wanted_count": i % 3, "episode_count": 6 + i % 9, "series_count": 2}}
         for i, t in enumerate(["The Example Hour", "Sample Science Weekly"] + _titles(10, 5), 1)]


def _paged(items, q):
    size = int(q.get("page_size", "0") or 0)
    page = int(q.get("page", "1") or 1)
    chosen = items[(page - 1) * size: page * size] if size else items
    return {"items": chosen, "total": len(items), "page": page, "page_size": size}


# Folders on disk that the made-up Reelix does not know yet (DASH-186), for Library, Bring them in.
ON_DISK = [("Arrival (2016)", "Arrival", 2016, 329865), ("The Farewell (2019)", "The Farewell", 2019, 565310),
           ("home movies", "home movies", None, None)]


def _candidate(name, title, year, tmdb, lookup):
    return {"folder": {"name": name, "path": f"/data/media/movies/{name}"}, "parsed_title": title, "parsed_year": year,
            "file_count": 1, "size": 4 * 10**9,
            "suggestions": [{"tmdb_id": tmdb, "title": title, "year": year}] if lookup and tmdb else [],
            "lookup_error": None}


def answer(path, q):
    """The made-up Reelix's answer for one GET, or None when this module does not know the path."""
    if path.startswith("/posters/"):
        return None
    if path == "/rootfolders":
        return [{"id": 1, "path": "/data/media/movies", "media_kind": "movie", "accessible": True,
                 "unmapped_folders": [{"name": n, "path": f"/data/media/movies/{n}"} for n, *_ in ON_DISK]}]
    if path == "/libraryimport/scan":
        return [_candidate(*f, lookup=False) for f in ON_DISK]
    if path == "/history":  # History (DASH-159)
        kinds = ["grabbed", "imported", "download_failed", "grabbed", "imported", "renamed"]
        rows = [{"id": n, "event_type": kinds[n % 6], "date": (TODAY - dt.timedelta(hours=5 * n)).isoformat() + "T12:00:00Z",
                 "media": {"kind": "movie", "id": FILMS[n]["id"], "title": FILMS[n]["title"], "year": FILMS[n]["year"]}, "episode": None,
                 "source_title": f"Made.Up.Release.{n}.1080p.WEB-DL", "quality": {"quality": "WEBDL-1080p"}, "indexer": "Example Torrents",
                 "data": {"message": "The download app stopped answering" if kinds[n % 6] == "download_failed" else ""}} for n in range(12)]
        if q.get("event_type"):
            rows = [r for r in rows if r["event_type"] == q["event_type"]]
        return {"items": rows, "total": len(rows), "page": 1, "page_size": 50}
    if path == "/blocklist":
        return {"items": [{"id": n, "media": {"kind": "movie", "id": FILMS[n]["id"], "title": FILMS[n]["title"], "year": FILMS[n]["year"]},
                           "source_title": f"Bad.Release.{n}.CAM", "quality": {"quality": "CAM"}, "indexer": "Example Torrents",
                           "message": "Fake file", "date": TODAY.isoformat() + "T09:00:00Z"} for n in range(2) if n not in CHANGED.get("unblocked", set())],
                "total": 2, "page": 1, "page_size": 50}
    if path == "/releases":  # Choose a download (DASH-159)
        return [{"guid": f"made-up-{n}", "indexer_id": 1 + n % 2, "indexer": ["Example Torrents", "Example Usenet"][n % 2],
                 "title": f"Made.Up.Release.{2020 + n}.1080p.WEB-DL", "protocol": ["torrent", "usenet"][n % 2], "size": (3 + n) * 10 ** 9,
                 "age_minutes": 60 * 24 * (n + 1), "seeders": None if n % 2 else 40 - 9 * n, "quality": {"quality": "WEBDL-1080p"},
                 "languages": [{"name": "English"}], "format_score": 10 - n, "accepted": n < 3, "rank": n,
                 "rejections": [] if n < 3 else [{"reason": "Not wanted in this profile: 720p", "kind": "permanent", "spec": "quality"}]}
                for n in range(5)]
    if path in ("/wanted/missing", "/wanted/cutoff"):  # Wanted (DASH-207)
        films = [f for f in FILMS if (not f["has_file"]) == (path == "/wanted/missing")][:12]
        if q.get("kind") == "episode":
            items = [{"kind": "episode", "id": 500 + n, "series_id": 8, "title": "43 Planets", "season_number": 2, "episode_number": n + 1,
                      "episode_title": f"{WORDS_A[n]} {WORDS_B[n]}", "date": (TODAY - dt.timedelta(days=7 * n)).isoformat(),
                      "quality": "SDTV" if path.endswith("cutoff") else None, "cutoff": "HD-1080p"} for n in range(6)]
        else:
            items = [{"kind": "movie", "id": f["id"], "movie_id": f["id"], "title": f["title"], "year": f["year"],
                      "date": f"{f['year']}-05-01", "quality": "HD-720p" if path.endswith("cutoff") else None, "cutoff": "HD-1080p"} for f in films]
        return {"items": items, "total": len(items), "page": 1, "page_size": 50}
    if path == "/movies":
        return _paged(FILMS, q)
    if path == "/series":
        return _paged(SERIES, q)
    if path == "/books":
        return _paged(BOOKS, q)
    if path == "/artists":
        return _paged(ARTISTS, q)
    if path == "/radio/shows" and q.get("page_size") != "20":  # Coming up asks for 20; the Library for every page
        return _paged(SHOWS, q)
    parts = path.strip("/").split("/")
    if len(parts) == 2 and parts[1].isdigit():
        found = {"movies": FILMS, "series": SERIES, "books": BOOKS, "artists": ARTISTS}.get(parts[0])
        if found:
            return next((x for x in found if x["id"] == int(parts[1])), {})
    if len(parts) == 3 and parts[:2] == ["radio", "shows"] and parts[2].isdigit():
        return next((x for x in SHOWS if x["id"] == int(parts[2])), {})
    if len(parts) == 3 and parts[0] == "series" and parts[2] == "episodes":
        s = next((x for x in SERIES if x["id"] == int(parts[1])), None)
        if not s:
            return []
        have = s["statistics"]["episode_file_count"]
        return [{"id": n, "season_number": 1 + n // 8, "episode_number": 1 + n % 8, "title": f"{WORDS_A[n % 20]} {WORDS_B[n % 19]}",
                 "air_date": (TODAY - dt.timedelta(days=(s["statistics"]["episode_count"] - n) * 7)).isoformat(),
                 "has_file": n < have, "monitored": CHANGED["episodes"].get(n, True)} for n in range(s["statistics"]["episode_count"])]
    if path == "/albums":
        a = int(q.get("artist_id", "1"))
        return {"items": [{"id": a * 10 + n, "title": f"{WORDS_A[(a + n) % 20]} {WORDS_B[n]}", "release_date": f"{2010 + n * 3}-06-01",
                           "statistics": {"track_count": 10, "track_file_count": 10 if n else 6}} for n in range(1 + a % 4)], "total": 1 + a % 4}
    if path == "/bookseries":
        return [{"id": 1, "title": "The Glass Harbour", "books": [[str(n + 1), (n + 1) * 4] for n in range(10)]}]
    if path == "/collections":
        return [{"id": 1, "title": "The Harbour Films", "movies": [{"title": FILMS[k - 1]["title"], "year": FILMS[k - 1]["year"], "movie_id": k,
                                                                     "has_file": FILMS[k - 1]["has_file"]} for k in (3, 9, 27)]
                 + [{"title": "Harbour Lights Returns", "year": 2027, "movie_id": None, "has_file": False}]}]
    if path in ("/movies/lookup", "/series/lookup"):
        term = q.get("term", "")
        return [{"tmdb_id": 9000 + n, "title": f"{term.title()} {['Rising', 'at Dawn', 'Returns'][n]}", "year": 2019 + n,
                 "overview": "A made-up result for the preview.", "poster": None, "in_library": False} for n in range(3)]
    if path == "/books/lookup":
        return [{"openlibrary_work_id": f"OL{900 + n}W", "title": f"The {q.get('term', '').title()} Book {n + 1}", "author_name": AUTHORS[n],
                 "year": 2001 + n, "cover": None} for n in range(2)]
    if path == "/artists/lookup":
        return [{"musicbrainz_id": "00000000-0000-4000-8000-000000000001", "name": f"{q.get('term', '').title()} Quartet",
                 "artist_type": "Group", "country": "GB"}]
    if path == "/radio/search":
        return [{"provider": "bbc", "external_id": "b000test", "title": f"{q.get('q', '').title()} Hour", "station_name": "BBC Radio 4",
                 "synopsis": "A made-up radio show for the preview."}]
    if path.startswith("/qualityprofiles"):
        return [{"id": 1, "name": "HD-1080p"}, {"id": 2, "name": "Ultra-HD"}]
    if path in ("/rootfolders",):
        return [{"id": 1, "path": "/data/media/movies", "media_kind": "movie", "free_space": 4 * 10 ** 12},
                {"id": 2, "path": "/data/media/series", "media_kind": "series", "free_space": 4 * 10 ** 12}]
    if path in ("/bookrootfolders", "/musicrootfolders"):
        return [{"id": 3, "path": "/data/media/books", "kind": "ebook", "free_space": 4 * 10 ** 12}]
    return None


CHANGED = {"episodes": {}}  # made-up changes from Library actions: episode id -> monitored


def change(method, path, body, q):
    """A made-up PUT or DELETE from Library actions (DASH-276, DASH-206): follow, stop following, delete."""
    parts = path.strip("/").split("/")
    if len(parts) == 2 and parts[1].isdigit() and parts[0] in ("movies", "series"):
        items = FILMS if parts[0] == "movies" else SERIES
        found = next((x for x in items if x["id"] == int(parts[1])), None)
        if not found:
            return None
        if method == "DELETE":
            items.remove(found)
            return {}
        found["monitored"] = bool((body or {}).get("monitored", found.get("monitored")))
        return found
    if path == "/episodes/monitor":
        for e in body.get("episode_ids") or []:
            CHANGED["episodes"][e] = bool(body.get("monitored"))
        return []
    if path == "/seasons/monitor":
        return {}
    if len(parts) == 2 and parts[0] == "blocklist" and parts[1].isdigit() and method == "DELETE":
        CHANGED.setdefault("unblocked", set()).add(int(parts[1]))
        return {}
    return None


def add(path, body):
    """A made-up add: answers as Reelix does, with the title."""
    if path == "/search":
        return {"queued": True}
    if path == "/releases/grab":
        return {"queue_id": 1, "download_client": "qBittorrent", "download_id": "made-up"}
    if path == "/libraryimport/match":
        return [_candidate(*f, lookup=True) for f in ON_DISK if f"/data/media/movies/{f[0]}" in body.get("paths", [])]
    if path == "/libraryimport":
        return {"added": list(range(len(body.get("items") or []))), "errors": []}
    title = {"/movies": "Added film", "/series": "Added series", "/books": "Added book", "/artists": "Added artist",
             "/radio/shows": "Added show"}.get(path)
    return {"id": 999, "title": title, "name": title} if title else None
