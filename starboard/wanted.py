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
        out.append({"id": w["id"], "title": w.get("title") or "Untitled", "year": w.get("year"),
                    "detail": " · ".join(x for x in (se, w.get("episode_title") or "") if x),
                    "date": w.get("date") or "", "quality": w.get("quality") or "", "cutoff": w.get("cutoff") or "",
                    "href": f"/library-film.html?id={w['movie_id']}" if w.get("movie_id") else
                            f"/library-tv-show.html?id={w['series_id']}" if w.get("series_id") else ""})
    return {"items": out, "total": int(answer.get("total") or 0), "page": int(answer.get("page") or page), "page_size": PAGE}


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
