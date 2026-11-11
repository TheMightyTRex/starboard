"""Discover, On demand history (owner, 11 November 2026, DASH-324): what you started watching in On demand, with Add to
wanted, which adds the film or series to Reelix (and searches for it) so it comes into your own library.

The history comes from the On demand plug-in (GET /api/history, with the plug-in's own key); whether each title is
already in your library comes from Reelix's lookup by IMDb number, kept for an hour."""
import json
import urllib.error
import urllib.parse
import urllib.request

from . import services

PID = "on-demand"


def _plugin(data_dir, method, path):
    from . import plugin_cards, plugins_admin
    listing = {p["id"]: p for p in plugins_admin.listing(data_dir)}
    if listing.get(PID, {}).get("state") != "enabled":
        raise LookupError("Add On demand in Settings, Plug-ins, and activate it, to see what you watched there")
    m = plugins_admin._read(f"{plugins_admin.folder(data_dir, PID)}/manifest.json", {}) or {}
    main = m["containers"][0]
    try:
        with open(f"{plugins_admin.folder(data_dir, PID)}/key", encoding="utf-8") as f:
            key = f.read().strip()
    except OSError:
        key = ""
    req = urllib.request.Request(f"http://{plugin_cards._host(PID, main)}:{int(main.get('port') or 80)}{path}", method=method,
                                 headers={"Accept": "application/json", "User-Agent": "Starboard", "X-Api-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:  # the plug-in's own container  # nosec B310
            return json.loads(r.read(512 * 1024) or b"{}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ValueError(f"On demand did not answer: {e}") from None


def _lookup(reelix, kind, imdb):
    """(tmdb key, in your library, Reelix id) for an IMDb number, or (None, False, None)."""
    def ask():
        rows = services._api(reelix, f"/{'movies' if kind == 'movie' else 'series'}/lookup?{urllib.parse.urlencode({'term': f'imdb:{imdb}'})}") or []
        r = rows[0] if rows else {}
        return (f"tmdb:{r['tmdb_id']}" if r.get("tmdb_id") else None, bool(r.get("in_library")), r.get("library_id"))
    return services.cached(f"od-lookup-{kind}-{imdb}", 3600, ask)


def listing(data_dir, reelix, kind="all"):
    items = (_plugin(data_dir, "GET", "/api/history") or {}).get("items") or []
    out = []
    for it in items[:200]:
        k = "movie" if it.get("type") == "movie" else "series"
        if kind in ("movie", "series") and k != kind:
            continue
        imdb = str(it.get("id") or "")
        key, have, lib_id = (None, False, None)
        if reelix and imdb.startswith("tt"):
            try:
                key, have, lib_id = _lookup(reelix, k, imdb)
            except services.ServiceError:
                pass
        out.append({"id": imdb, "kind": k, "title": str(it.get("name") or imdb)[:200], "year": str(it.get("year") or "")[:4],
                    "poster": it.get("poster") if str(it.get("poster", "")).startswith("https://") else "",
                    "first": it.get("first_played") or "", "last": it.get("last_played") or "", "episode": it.get("last_episode") or "",
                    "key": key, "in_library": have,
                    "href": (f"/library-film.html?id={lib_id}" if k == "movie" else f"/library-tv-show.html?id={lib_id}") if have and lib_id else ""})
    return {"items": out, "total": len(items)}


def want(data_dir, reelix, kind, imdb):
    """Adds the title to Reelix with its first quality profile and folder, searching for it now."""
    from . import library
    if kind not in ("movie", "series") or not str(imdb).startswith("tt"):
        raise ValueError("Choose a film or series from the history")
    key, have, _ = _lookup(reelix, kind, imdb)
    if have:
        return {"said": "It is already in your library"}
    if not key:
        raise ValueError("Reelix could not find it by its IMDb number")
    done = library.add(data_dir, reelix, "films" if kind == "movie" else "tv", key, {"search": True})
    services.forget(f"od-lookup-{kind}-{imdb}")
    return {"said": f"Added {done.get('title') or 'it'} to your wanted list; Reelix is searching for it"}


def forget(data_dir, imdb):
    _plugin(data_dir, "DELETE", f"/api/history?{urllib.parse.urlencode({'id': imdb})}")
    return {"said": "Taken out of your On demand history"}
