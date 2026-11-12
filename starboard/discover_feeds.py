"""Discover by area (owner, 12 November 2026: "a menu 2 item for each area, Films, TV, Music, Radio, Books and
Audiobooks, with different discovery feeds"). Every feed is Reelix's own Discover (TMDB for films and series, Open
Library for books, ListenBrainz for music, BBC Sounds, Apple Podcasts and Podcast Index for radio), so nothing new is
called from Starboard. Each row is fetched when the page shows it and kept for an hour, and every card says whether
you already have it, so Add is only offered for what you do not.

  GET /api/library/discover?tab=films           the rows (and genres for films and TV)
  GET /api/library/discover-row?tab=films&row=  one row's cards
  GET /api/library/discover-radio-search?q=&stations=1&feeds=1  radio search across every source (DASH-339)
"""
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


def rows(reelix, tab):
    """The page's rows; films and TV also get their genres, radio its categories."""
    if tab in ("films", "tv"):
        genres = _api(reelix, f"/discover/genres/{'movie' if tab == 'films' else 'tv'}") or []
        return {"rows": [{"id": r, "title": t} for r, t in ROWS[tab]],
                "genres": [{"id": f"genre/{'movie' if tab == 'films' else 'tv'}/{int(g['id'])}", "title": str(g.get("name") or "")}
                           for g in genres if isinstance(g, dict) and str(g.get("id", "")).isdigit()]}
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
        return {"rows": clean(got.get("rows")), "genres": shared or more, "stations": stations, "more": more if shared else []}
    if tab in ROWS:
        return {"rows": [{"id": r, "title": t} for r, t in ROWS[tab]], "genres": []}
    raise ValueError("Choose a Library tab")


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
