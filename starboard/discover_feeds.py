"""Discover by area (owner, 12 November 2026: "a menu 2 item for each area, Films, TV, Music, Radio, Books and
Audiobooks, with different discovery feeds"). Every feed is Reelix's own Discover (TMDB for films and series, Open
Library for books, ListenBrainz for music, BBC Sounds, Apple Podcasts and Podcast Index for radio), so nothing new is
called from Starboard. Each row is fetched when the page shows it and kept for an hour, and every card says whether
you already have it, so Add is only offered for what you do not.

  GET /api/library/discover?tab=films           the rows (and genres for films and TV)

Films and TV also offer a row for each of TMDB's genres (DASH-395, owner, 13 November 2026: "For discover rows - I
want to add more options - like comedy, sci fi etc."). They come from the same genre list as the chips, start
unticked in Settings, and, like every row, are asked for only when the page shows them and kept for an hour.
Radio does the same with the genres every radio source shares (DASH-396, owner, 13 November 2026: "Do you have the
same options for TV, books, audio books and Radio"). Books and audiobooks have every subject Reelix offers already
(Reelix allows only its nine Open Library subjects, BOOK_DISCOVER_ROWS); music has no genre source in Reelix.
  GET /api/library/discover-row?tab=films&row=  one row's cards
  GET /api/library/discover-radio-search?q=&stations=1&feeds=1  radio search across every source (DASH-339)
"""
import json
import os
import re
import urllib.parse

from . import services

ROWS = {
    "films": [("trending-movies", "Trending this week"), ("popular-movies", "Popular"), ("now-playing", "In cinemas now"),
              ("upcoming", "Coming soon"), ("top-rated-movies", "Top rated")],
    "tv": [("trending-series", "Trending this week"), ("popular-series", "Popular"), ("airing-today", "On today"),
           ("on-the-air", "On this week"), ("top-rated-series", "Top rated")],
    "music": [("new-releases", "New releases"), ("popular-week", "Popular this week"), ("popular-month", "Popular this month")],
    "books": [("trending", "Trending this week"), ("subject-fantasy", "Fantasy"), ("subject-science_fiction", "Science fiction"),
              ("subject-mystery", "Mystery"), ("subject-thriller", "Thriller"), ("subject-romance", "Romance"),
              ("subject-horror", "Horror"), ("subject-historical_fiction", "Historical fiction"),
              ("subject-young_adult_fiction", "Young adult"), ("subject-biography", "Biography")],
}
ROWS["audiobooks"] = ROWS["books"]
KEEP = 3600
HAVE = ("available", "partially_available", "partially", "in_library")
WANTED = ("requested", "processing", "pending", "approved", "wanted", "monitored")


def _api(reelix, path, params=None):
    return services.cached(f"discover:{path}:{sorted((params or {}).items())}", KEEP,
                           lambda: services._api(reelix, path, params, timeout=25))


def tidy(name):
    """TMDB's genre names in sentence case, without ampersands: "Science Fiction" is Science fiction, "Sci-Fi &
    Fantasy" is Sci-fi and fantasy, "TV Movie" keeps TV."""
    words = str(name or "").replace("&", "and").split()
    keep = lambda w: w.isupper() and len(w) > 1  # noqa: E731  (TV, not a)
    return " ".join([w if keep(w) else w[:1].upper() + w[1:].lower() for w in words[:1]] + [w if keep(w) else w.lower() for w in words[1:]])


def rows(reelix, tab):
    """The page's rows; films and TV also get their genres (as chips, and as rows that start hidden), radio its
    categories."""
    if tab in ("films", "tv"):
        kind = "movie" if tab == "films" else "tv"
        got = _api(reelix, f"/discover/genres/{kind}") or []
        genres = [{"id": f"genre/{kind}/{int(g['id'])}", "title": tidy(g.get("name"))}
                  for g in got if isinstance(g, dict) and str(g.get("id", "")).isdigit() and g.get("name")]
        genres.sort(key=lambda g: g["title"].lower())
        return {"rows": [{"id": r, "title": t} for r, t in ROWS[tab]] + [dict(g, genre=True) for g in genres], "genres": genres}
    if tab == "radio":
        # DASH-339: the shared genres (every source at once) as chips, the BBC's stations in a picker by group,
        # and each source's own categories under More categories (Reelix RFX-93, 94).
        got = _api(reelix, "/discover/genres/radio") or {}
        clean = lambda xs: [{"id": str(x.get("id")), "title": str(x.get("name") or ""), "source": str(x.get("provider_name") or ""),  # noqa: E731
                             "group": str(x.get("group") or "")} for x in xs or [] if isinstance(x, dict) and x.get("id")]
        cats = clean(got.get("categories"))
        shared = [c for c in cats if c["id"].startswith("all-genre-")]
        stations = [c for c in cats if c["group"].startswith("BBC stations")]
        more = [c for c in cats if c not in shared and c not in stations]
        # DASH-396: each shared genre is also a row, unticked until chosen in Settings, as films' genres are. Only the
        # shared ones (one list for every source); a source's own categories stay under More categories.
        genre_rows = [{"id": c["id"], "title": c["title"], "genre": True} for c in sorted(shared, key=lambda c: c["title"].lower())]
        return {"rows": clean(got.get("rows")) + genre_rows, "genres": shared or more, "stations": stations, "more": more if shared else []}
    if tab in ROWS:
        return {"rows": [{"id": r, "title": t} for r, t in ROWS[tab]], "genres": []}
    raise ValueError("Choose a Library tab")


# Which rows each area shows and in what order (DASH-303, owner, 10 November 2026: "Add settings for which rows
# Discover shows and their order"). Kept for the account on the server, beside the Library views; a row Reelix no
# longer has is dropped, a new one comes at the end.
def _layout_path(data_dir):
    return os.path.join(data_dir, "library", "discover-layout.json")


def layout(data_dir):
    try:
        with open(_layout_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _hidden(listed, saved):
    """The rows not to show: those saved as hidden, and a genre row (DASH-395) until it is ticked. A ticked row is in
    the saved order and not hidden, so a genre Reelix adds later starts hidden too."""
    saved = saved or {}
    order = set(x for x in saved.get("order") or [] if isinstance(x, str))
    return set(saved.get("hidden") or []) | {r["id"] for r in listed if r.get("genre") and r["id"] not in order}


def _ordered(listed, saved):
    order = [x for x in (saved or {}).get("order") or [] if isinstance(x, str)]
    rank = {rid: n for n, rid in enumerate(order)}
    return sorted(listed, key=lambda r: (r["id"] not in rank, rank.get(r["id"], 0)))


def arrange(listed, saved):
    """The rows in the saved order (rows not saved keep their place at the end), without the hidden ones."""
    hidden = _hidden(listed, saved)
    return [r for r in _ordered(listed, saved) if r["id"] not in hidden]


def describe(data_dir, listed, tab):
    """Settings' view of one area: every row with whether it shows, in the order the page shows them."""
    saved = layout(data_dir).get(tab) or {}
    hidden = _hidden(listed, saved)
    return {"tab": tab, "rows": [dict({"id": r["id"], "title": r["title"], "shown": r["id"] not in hidden}, **({"genre": True} if r.get("genre") else {}))
                                 for r in _ordered(listed, saved)],
            "changed": bool(saved)}


def _write_layout(data_dir, data):
    folder = os.path.join(data_dir, "library")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    path = _layout_path(data_dir)
    with open(os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(path + ".tmp", path)


def save_layout(data_dir, listed, tab, order, hidden):
    known = [r["id"] for r in listed]
    order = [x for x in order or [] if x in known]
    order += [x for x in known if x not in order]
    hidden = [x for x in hidden or [] if x in known]
    if len(hidden) >= len(known):
        raise ValueError("Keep at least one row")
    data = layout(data_dir)
    data[tab] = {"order": order, "hidden": hidden}
    _write_layout(data_dir, data)
    return describe(data_dir, listed, tab)


def reset_layout(data_dir, listed, tab):
    data = layout(data_dir)
    data.pop(tab, None)
    _write_layout(data_dir, data)
    return describe(data_dir, listed, tab)


def _state(x):
    a = str(x.get("availability") or "").lower()
    if x.get("library_id") or a in HAVE:
        return "have"
    if a in WANTED or x.get("request"):
        return "wanted"
    return ""


def _picture(url):
    from .library import poster_allowed, small
    url = small(url or "")
    return f"/api/library/lookup-poster?src={urllib.parse.quote(url, safe='')}" if url and poster_allowed(url) else ""


def row(reelix, tab, row_id):
    """One row's cards, in the same shape as Search's lookup rows, so the same Add slide-out adds them."""
    if not re.match(r"^[A-Za-z0-9_:/.-]{1,120}$", row_id or ""):
        raise ValueError("Not a Discover row")
    listed = rows(reelix, tab)
    known = {r["id"] for part in ("rows", "genres", "stations", "more") for r in listed.get(part, [])}
    if row_id not in known:
        raise ValueError("Not a Discover row")
    out = []
    if tab in ("films", "tv"):
        got = _api(reelix, f"/discover/{row_id}") or {}
        for x in (got.get("results") or [])[:20]:
            key = f"tmdb:{x['tmdb_id']}" if x.get("tmdb_id") else ""
            out.append({"key": key, "kind": tab, "title": x.get("title") or "", "year": x.get("year"),
                        "detail": "", "overview": (x.get("overview") or "")[:300], "image": _picture(x.get("poster")), "state": _state(x)})
    else:
        kind = {"music": "album", "books": "book", "audiobooks": "book", "radio": "radio"}[tab]
        got = _api(reelix, f"/discover/content/{kind}/{row_id}") or {}
        for x in (got.get("results") or [])[:20]:
            fid = str(x.get("foreign_id") or "")
            if tab == "music":  # Starboard adds the artist, so every album of theirs can come
                key = f"mb:{x['subtitle_id']}" if re.match(r"^[0-9a-f-]{36}$", str(x.get("subtitle_id") or "")) else ""
            elif tab in ("books", "audiobooks"):
                key = f"olw:{fid}" if re.match(r"^OL\d+W$", fid) else ""
            else:
                key = f"radio:{fid}" if ":" in fid else ""
            out.append({"key": key, "kind": "books" if tab == "audiobooks" else tab, "title": x.get("title") or "",
                        "year": x.get("year"), "detail": x.get("subtitle") or "", "overview": "",
                        "image": _picture(x.get("cover")), "state": _state(x), "audiobook": tab == "audiobooks"})
    return {"items": [c for c in out if c["key"] and c["title"]]}



def radio_search(reelix, q, from_stations=False, feeds_only=False):
    """Discover, Radio's search across every source switched on in Reelix (DASH-339), as cards: From radio
    stations keeps shows a broadcaster makes (Reelix RFX-101); Podcast feeds only keeps shows with a feed, the
    safest to follow."""
    q = str(q or "").strip()
    if len(q) < 2:
        raise ValueError("Type at least two letters")
    params = {"q": q[:100]}
    if from_stations:
        params["from_stations"] = "true"
    got = services._api(reelix, "/radio/search", params, timeout=25) or []
    out = []
    for x in got if isinstance(got, list) else []:
        if not isinstance(x, dict) or not x.get("provider") or not x.get("external_id"):
            continue
        if feeds_only and not x.get("feed_url"):
            continue
        parts = []
        for y in (x.get("broadcaster") or "", x.get("station_name") or "", x.get("author") or ""):
            if y and y.lower() not in (p.lower() for p in parts):  # "Times Radio" once, not twice
                parts.append(y)
        detail = " · ".join(parts)
        out.append({"key": f"radio:{x['provider']}:{x['external_id']}", "kind": "radio", "title": x.get("title") or "",
                    "year": None, "detail": detail, "overview": (x.get("synopsis") or "")[:300],
                    "image": _picture(x.get("artwork_url")), "state": "have" if x.get("show_id") else "",
                    "feed": bool(x.get("feed_url")), "broadcaster": x.get("broadcaster") or ""})
    # An older Reelix (before RFX-101) ignores from_stations and says no broadcaster: say so, rather than claim
    # every show is from a station.
    old_reelix = from_stations and isinstance(got, list) and got and not any(isinstance(x, dict) and "broadcaster" in x for x in got)
    if old_reelix:
        return {"items": [], "note": "Your Reelix cannot tell which shows come from radio stations yet. Update Reelix, or turn off From radio stations."}
    if from_stations:
        out = [c for c in out if c["broadcaster"]]
    return {"items": [c for c in out if c["title"]][:40]}
