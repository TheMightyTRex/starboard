"""Bring in radio shows already on disk (owner, 10 November 2026): shows in Audiobookshelf's Radio library that Reelix
does not follow yet, found, matched to a show on Reelix's radio sources (BBC Sounds, Apple Podcasts, the Internet
Archive and the rest) and added, so Starboard's Radio tab and Coming up show them.

Two parts, as Reelix works:
- Connect (once, with the Reelix password, as Reelix keeps radio settings behind it): point Reelix's radio at
  Audiobookshelf's Radio library, with the folder as Audiobookshelf itself reports it (the owner's server uses /radio,
  a new install /media/radio), then ask Reelix to read that library now.
- Bring them in (Starboard's manager key): Reelix's review lists the library's shows that no followed show covers;
  each is searched by its title, the best match is offered, and the ticked ones are added. The owner chose to fill
  the gaps: every episode Reelix can find, old and new (follow "all"); the dialog offers the other two choices.
Nothing on disk is moved or renamed: Reelix matches the files already there to the show's episodes."""
import re
import unicodedata

from . import media_import

FOLLOW = ("all", "from_now_on", "none")
DEFAULT_FOLLOW = "all"  # the owner's choice, 10 November 2026: fill the gaps
BATCH = 15  # shows searched at a time: each is one search of Reelix's sources


def _call(cfg, method, path, body=None, timeout=60):
    try:
        return media_import._call(cfg, method, path, body, timeout)
    except media_import.ImportError_ as e:
        raise ValueError(str(e)) from None


def _fold(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"^(the|a|an) ", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def status(cfg):
    """{connected, synced_at, waiting, shows}: whether Reelix reads Audiobookshelf's Radio library, and how many shows
    in it no followed show covers yet."""
    review = _call(cfg, "GET", "/radio/library/review") or {}
    shows = _call(cfg, "GET", "/radio/shows") or {}
    count = shows.get("total", len(shows.get("items") or [])) if isinstance(shows, dict) else len(shows or [])
    return {"connected": bool(review.get("synced_at")), "synced_at": review.get("synced_at"),
            "waiting": len(review.get("unmatched_shows") or []), "shows": count}


def radio_library(abs_service, opener=None):
    """Audiobookshelf's Radio library: (id, folder as Audiobookshelf sees it), or None. A podcast library named Radio,
    or the one whose folder ends in /radio."""
    import json
    import urllib.request
    req = urllib.request.Request(abs_service["url"].rstrip("/") + "/api/libraries",
                                 headers={"Authorization": "Bearer " + abs_service["api_key"], "Accept": "application/json", "User-Agent": "Starboard"})
    with (opener or urllib.request.build_opener()).open(req, timeout=20) as r:  # Audiobookshelf's address from Starboard's apps  # nosec B310
        libraries = json.loads(r.read(2_000_000)).get("libraries", [])
    podcasts = [x for x in libraries if x.get("mediaType") == "podcast"]
    pick = next((x for x in podcasts if (x.get("name") or "").strip().lower() == "radio"), None) or \
        next((x for x in podcasts if any((f.get("fullPath") or "").rstrip("/").endswith("/radio") for f in x.get("folders") or [])), None)
    if not pick or not pick.get("folders"):
        return None
    return pick["id"], pick["folders"][0]["fullPath"].rstrip("/")


def connect(reelix_admin, cfg, opener=None):
    """Points Reelix's radio at Audiobookshelf's Radio library and starts reading it. Returns what was done."""
    from . import reelix_system
    abs_service = next((s for s in cfg.data["services"] if s.get("type") == "audiobookshelf" and s.get("api_key")), None)
    if not abs_service:
        raise ValueError("Add Audiobookshelf with its API key in Manage apps first")
    found = radio_library(abs_service, opener)
    if not found:
        raise ValueError("Audiobookshelf has no Radio podcast library. Add one in Audiobookshelf, then try again")
    library, abs_folder = found
    roots = reelix_admin.call("GET", "/radio/rootfolders")[1] or []
    folder = next((r["path"] for r in roots if r.get("accessible", True)), None)
    if not folder:
        raise ValueError("Reelix has no radio folder yet. Add one in Settings, Reelix, Folders")
    _, current = reelix_admin.call("GET", "/radio/settings")
    reelix_admin.call("PUT", "/radio/settings", {**(current or {}), "abs_library_id": library, "abs_library_folder": abs_folder,
                                                 "library_folder": folder})
    reelix_system.run_task(reelix_admin, "radio_library_sync")
    return {"done": [f"Reelix now reads Audiobookshelf's Radio library ({abs_folder}) and is reading it now"]}


def _best(title, hits):
    want = _fold(title)
    same = [h for h in hits if _fold(h.get("title")) == want]
    near = [h for h in hits if want and (want in _fold(h.get("title")) or _fold(h.get("title")) in want)]
    ordered = same + [h for h in near if h not in same] + [h for h in hits if h not in same and h not in near]
    return ordered


def scan(cfg, start=0):
    """One page of the library's shows that no followed show covers, each with Reelix's best matches."""
    review = _call(cfg, "GET", "/radio/library/review") or {}
    waiting = sorted(review.get("unmatched_shows") or [], key=lambda x: _fold(x.get("title")))
    page = waiting[int(start):int(start) + BATCH]
    import urllib.parse
    items = []
    for show in page:
        title = show.get("title") or ""
        try:
            hits = _call(cfg, "GET", f"/radio/search?{urllib.parse.urlencode({'q': title})}", timeout=30) or [] if title else []
            problem = None
        except ValueError as e:
            hits, problem = [], str(e)
        matches = [{"provider": h.get("provider"), "external_id": h.get("external_id"), "title": h.get("title"),
                    "station": h.get("station_name") or h.get("author") or "", "episodes": h.get("episode_count"),
                    "already": h.get("show_id")} for h in _best(title, hits)[:5] if h.get("provider") and h.get("external_id")]
        # Ticked only when the best match has the same title: a near one ("Night Train Hour" for "Night Train") waits
        # for a person to choose it.
        sure = bool(matches) and _fold(matches[0]["title"]) == _fold(title)
        items.append({"key": show.get("abs_item_id"), "title": title, "files": show.get("file_count", 0),
                      "matches": matches, "sure": sure, "problem": problem})
    return {"total": len(waiting), "start": int(start), "items": items}


def run(cfg, items, follow=DEFAULT_FOLLOW):
    """Adds each kept show from its chosen match, following `follow`. Returns {added, errors}."""
    if follow not in FOLLOW:
        raise ValueError("Choose what Reelix gets for each show")
    keep = [i for i in items or [] if isinstance(i, dict) and i.get("provider") and i.get("external_id")]
    if not keep:
        raise ValueError("Choose a match for at least one show")
    roots = _call(cfg, "GET", "/radio/rootfolders") or []
    root = next((r["id"] for r in roots if r.get("accessible", True)), None)
    added, errors = 0, []
    for i in keep[:200]:
        body = {"provider": str(i["provider"]), "external_id": str(i["external_id"]), "follow": follow, "monitored": True}
        if root is not None:
            body["root_folder_id"] = root
        try:
            _call(cfg, "POST", "/radio/shows", body)
            added += 1
        except ValueError as e:
            errors.append({"title": str(i.get("title") or i["external_id"]), "message": str(e)})
    return {"added": added, "errors": errors}
