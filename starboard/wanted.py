"""Wanted (DASH-207): what Reelix follows but does not have yet (Missing), and what it has below the quality wanted
(Below the quality wanted), for films and for episodes, with Search for the ticked ones and Search all. Read from
Reelix's own lists with Starboard's manager key, a page at a time. Books and albums have lists of their own in
Reelix; this covers films and series."""
from . import services

WHICH = {"missing": "/wanted/missing", "cutoff": "/wanted/cutoff"}
KINDS = ("movie", "episode")
PAGE = 50


def _reelix(all_services):
    found = services.reelix_native(all_services)
    if not found:
        raise ValueError("Add Reelix in Settings, Manage apps, with its key, to see what is wanted")
    return found[0]


def listing(all_services, which, kind, page=1):
    if which not in WHICH or kind not in KINDS:
        raise ValueError("Choose Missing or Below the quality wanted, and films or episodes")
    r = _reelix(all_services)
    answer = services._api(r, WHICH[which], {"kind": kind, "page": max(1, int(page)), "page_size": PAGE, "sort": "date", "dir": "desc"}) or {}
    out = []
    for w in answer.get("items") or []:
        se = f"S{w['season_number']:02d}E{w['episode_number']:02d}" if w.get("season_number") is not None and w.get("episode_number") is not None else ""
        out.append({"id": w["id"], "series_id": w.get("series_id"), "title": w.get("title") or "Untitled", "year": w.get("year"),
                    "detail": " · ".join(x for x in (se, w.get("episode_title") or "") if x),
                    "date": w.get("date") or "", "quality": w.get("quality") or "", "cutoff": w.get("cutoff") or "",
                    "href": f"/library-film.html?id={w['movie_id']}" if w.get("movie_id") else
                            f"/library-tv-show.html?id={w['series_id']}" if w.get("series_id") else ""})
    return {"items": out, "total": int(answer.get("total") or 0), "page": int(answer.get("page") or page), "page_size": PAGE}


def detail(all_services, kind, item_id, series_id=None):
    """One wanted film or episode, for its slide-out (DASH-305): picture, story, length, genres, the quality wanted, and
    what Reelix last did for it (grabbed, failed, imported)."""
    if kind not in KINDS:
        raise ValueError("Choose a film or an episode")
    r = _reelix(all_services)
    item_id = int(item_id)
    if kind == "movie":
        m = services._api(r, f"/movies/{item_id}") or {}
        out = {"title": m.get("title"), "year": m.get("year"), "overview": m.get("overview") or "",
               "poster": (m.get("images") or {}).get("poster") or "", "runtime": m.get("runtime_minutes"),
               "genres": m.get("genres") or [], "profile_id": m.get("quality_profile_id"), "href": f"/library-film.html?id={item_id}",
               "releases": {"tab": "films", "id": item_id}}
        hist = services._api(r, "/history", {"movie_id": item_id, "page_size": 6}) or {}
    else:
        if not str(series_id or "").isdigit():
            raise ValueError("Say which series the episode is in")
        s = services._api(r, f"/series/{int(series_id)}") or {}
        eps = services._api(r, f"/series/{int(series_id)}/episodes") or []
        eps = eps.get("items", eps) if isinstance(eps, dict) else eps
        e = next((x for x in eps if x.get("id") == item_id), {})
        e.setdefault("series_id", int(series_id))
        se = f"S{int(e.get('season_number', 0)):02d}E{int(e.get('episode_number', 0)):02d}" if e.get("episode_number") is not None else ""
        out = {"title": f"{s.get('title') or 'Series'}, {se} {e.get('title') or ''}".strip(), "year": s.get("year"),
               "overview": e.get("overview") or s.get("overview") or "", "poster": (s.get("images") or {}).get("poster") or "",
               "runtime": e.get("runtime_minutes") or s.get("runtime_minutes"), "genres": s.get("genres") or [],
               "aired": e.get("air_date") or e.get("air_date_utc") or "", "profile_id": s.get("quality_profile_id"),
               "href": f"/library-tv-show.html?id={e.get('series_id')}" if e.get("series_id") else "",
               "releases": {"tab": "tv", "id": e.get("series_id"), "scope": "episode", "episode": item_id}}
        hist = services._api(r, "/history", {"episode_id": item_id, "page_size": 6}) or {}
    profiles = {p["id"]: p.get("name") for p in services._api(r, "/qualityprofiles") or []}
    out["profile"] = profiles.get(out.pop("profile_id"), "")
    words = {"grabbed": "Sent to the download app", "imported": "Brought in", "download_failed": "Download failed",
             "import_failed": "Could not be brought in", "deleted": "File deleted"}
    out["history"] = [{"when": str(h.get("date") or "")[:16].replace("T", " "), "what": words.get(h.get("event_type"), str(h.get("event_type") or "")),
                       "release": (h.get("source_title") or "")[:120]} for h in (hist.get("items") or [])[:6]]
    return out


def search(all_services, which, kind, ids=None):
    """Searches the ticked ones now, or every one on the list when ids is empty. Returns a sentence."""
    if which not in WHICH or kind not in KINDS:
        raise ValueError("Choose Missing or Below the quality wanted, and films or episodes")
    r = _reelix(all_services)
    ids = [int(i) for i in ids or [] if str(i).isdigit()][:500]
    if ids:
        services._api(r, "/search", method="POST", body={"kind": kind, "ids": ids})
        return f"Reelix is searching for {len(ids)} {'film' if kind == 'movie' and len(ids) == 1 else 'films' if kind == 'movie' else 'episode' if len(ids) == 1 else 'episodes'} now"
    services._api(r, "/search", method="POST", body={"kind": which, "ids": [], "media": kind})
    return "Reelix is searching for everything on this list now. It goes a few at a time, so the sites are not overloaded"
