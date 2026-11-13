"""Radio library review and add a show from a link, in Settings, Radio (DASH-212).

- Your podcast library: what Audiobookshelf's Radio library holds that Reelix has not matched (GET /radio/library/review):
  podcasts no followed show covers (brought in on Library, Radio, radio_import.py) and episode files matched to no
  episode, grouped by podcast. A file of a followed show can be matched to one of that show's episodes by hand
  (PUT /radio/episodes/{id}/file). Read the library again asks Reelix to read it now (POST /command,
  RescanRadioLibrary).
- Add a show from a link: the show behind a BBC Sounds page, an Apple Podcasts page or a feed address, with its newest
  episodes (GET /radio/preview?link=, which saves nothing), then Follow (POST /radio/shows with the link).

Every call needs only Reelix's Manage library right, so Starboard's manager key is enough (radio_import._call).
13 November 2026.
"""
import datetime as dt
import re
import urllib.parse

from . import radio_import

FOLLOW = {"all": "Every episode", "from_now_on": "New episodes", "none": "Only what you have"}
SHOWS_PAGE = 200


def _call(cfg, method, path, body=None, timeout=60):
    return radio_import._call(cfg, method, path, body, timeout)


def _shows_by_item(cfg):
    """{Audiobookshelf item id: (show id, title)} for every show Reelix has, a page at a time."""
    out = {}
    for page in range(1, 50):
        answer = _call(cfg, "GET", f"/radio/shows?{urllib.parse.urlencode({'page': page, 'page_size': SHOWS_PAGE})}") or {}
        items = (answer.get("items") or []) if isinstance(answer, dict) else list(answer)
        total = int(answer.get("total") or 0) if isinstance(answer, dict) else len(items)
        for s in items:
            if isinstance(s, dict) and s.get("abs_item_id"):
                out[str(s["abs_item_id"])] = (s.get("id"), s.get("title") or "")
        if len(items) < SHOWS_PAGE or page * SHOWS_PAGE >= total:
            break
    return out


def review(cfg):
    r = _call(cfg, "GET", "/radio/library/review") or {}
    files = r.get("unmatched_files") or []
    shows = _shows_by_item(cfg) if files else {}
    groups = {}
    for f in files:
        key = str(f.get("abs_item_id") or "")
        g = groups.setdefault(key, {"key": key, "podcast": f.get("item_title") or "Untitled", "files": 0, "size": 0,
                                    "show_id": None, "show": ""})
        g["files"] += 1
        g["size"] += int(f.get("size") or 0)
        if key in shows:
            g["show_id"], g["show"] = shows[key]
    waiting = r.get("unmatched_shows") or []
    return {"read": bool(r.get("synced_at")), "synced_at": r.get("synced_at"),
            "shows_waiting": len(waiting), "shows_waiting_files": sum(int(s.get("file_count") or 0) for s in waiting),
            "groups": sorted(groups.values(), key=lambda g: (-g["files"], g["podcast"].lower())), "files": len(files)}


def _label(e):
    s, n = e.get("series_number"), e.get("number")
    num = f"S{s:02d}E{n:02d}" if s is not None and n is not None else f"Episode {n}" if n is not None else ""
    when = ""
    try:
        d = dt.date.fromisoformat(str(e.get("first_broadcast") or "")[:10])
        when = f"{d.day} {d.strftime('%B %Y')}"
    except ValueError:
        pass
    return " · ".join(x for x in (num, e.get("title") or "Untitled", when) if x)


def files(cfg, key):
    """One podcast's unmatched files, and the episodes they could be matched to (its show's episodes with no file)."""
    key = str(key or "")
    r = _call(cfg, "GET", "/radio/library/review") or {}
    mine = [f for f in r.get("unmatched_files") or [] if str(f.get("abs_item_id") or "") == key]
    if not mine:
        raise ValueError("Reelix has no unmatched files for that podcast now. Load the page again")
    show = _shows_by_item(cfg).get(key)
    episodes = []
    if show and show[0] is not None:
        data = _call(cfg, "GET", f"/radio/shows/{int(show[0])}/episodes") or {}
        episodes = [{"id": e["id"], "label": _label(e)} for e in data.get("episodes") or []
                    if isinstance(e, dict) and e.get("id") is not None and not e.get("file_id") and e.get("status") != "in_library"]
    return {"key": key, "podcast": mine[0].get("item_title") or "Untitled", "show_id": show[0] if show else None, "show": show[1] if show else "",
            "files": [{"id": f.get("id"), "title": f.get("title") or "Untitled", "season": f.get("season"), "episode": f.get("episode"),
                       "published": f.get("published_at"), "seconds": f.get("duration_secs"), "size": f.get("size"), "path": f.get("path") or ""}
                      for f in mine],
            "episodes": episodes}


def match(cfg, file_id, episode_id):
    try:
        file_id, episode_id = int(file_id), int(episode_id)
    except (TypeError, ValueError):
        raise ValueError("Choose an episode from the list") from None
    e = _call(cfg, "PUT", f"/radio/episodes/{episode_id}/file", {"file_id": file_id}) or {}
    return {"done": f"Matched to {e.get('title') or 'the episode'}"}


def rescan(cfg):
    out = _call(cfg, "POST", "/command", {"name": "RescanRadioLibrary", "show_ids": []}) or {}
    return {"done": "Reelix is reading the library again" if out.get("job_id") is not None else "Reelix is reading the library already"}


_LINK = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.I)


def _link(link):
    link = str(link or "").strip()
    if not _LINK.match(link) or len(link) > 2000:
        raise ValueError("Paste the whole address of the show's page or feed, starting with https://")
    return link


def _https(url):
    url = str(url or "")
    return url if url.startswith("https://") and len(url) < 2000 else ""


def preview(cfg, link):
    link = _link(link)
    p = _call(cfg, "GET", f"/radio/preview?{urllib.parse.urlencode({'link': link})}", timeout=60) or {}
    s = p.get("show") or {}
    return {"link": link, "title": s.get("title") or "Untitled", "from": s.get("broadcaster") or s.get("station_name") or s.get("author") or "",
            "about": (s.get("synopsis") or "")[:600], "picture": _https(s.get("artwork_url")), "page": _https(s.get("web_url")),
            "episodes": int(p.get("episode_count") or 0), "series": int(p.get("series_count") or 0), "first": p.get("first_broadcast"),
            "show_id": s.get("show_id"), "latest": [{"title": e.get("title") or "Untitled", "when": e.get("first_broadcast"), "seconds": e.get("duration_secs")}
                                                     for e in p.get("latest_episodes") or [] if isinstance(e, dict)][:10],
            "follow": [{"value": k, "label": v} for k, v in FOLLOW.items()]}


def add(cfg, link, follow="all"):
    link = _link(link)
    if follow not in FOLLOW:
        raise ValueError("Choose what Reelix gets for this show")
    body = {"link": link, "follow": follow, "monitored": True}
    roots = _call(cfg, "GET", "/radio/rootfolders") or []
    root = next((r.get("id") for r in roots if isinstance(r, dict) and r.get("accessible", True)), None)
    if root is not None:
        body["root_folder_id"] = root
    show = _call(cfg, "POST", "/radio/shows", body) or {}
    searched = False
    if follow != "none" and str(show.get("id", "")).isdigit():
        try:  # as the radio import does: look for what is missing now, not at Reelix's next scheduled search
            _call(cfg, "POST", f"/radio/shows/{int(show['id'])}/search", {})
            searched = True
        except ValueError:
            pass
    title = show.get("title") or "The show"
    return {"done": f"{title} added" + (". Reelix is looking for its episodes" if searched else ""), "show_id": show.get("id"), "title": title}


def route(handler, method, path):
    """/api/radio/review (GET), /api/radio/review/files?key= (GET), /api/radio/review/match (POST),
    /api/radio/review/rescan (POST), /api/radio/preview?link= (GET), /api/radio/add-link (POST)."""
    from . import logs
    cfg = handler.app.config
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(handler.path).query))
    try:
        if method == "GET" and path == "/api/radio/review":
            return handler.json(200, review(cfg))
        if method == "GET" and path == "/api/radio/review/files":
            return handler.json(200, files(cfg, q.get("key")))
        if method == "GET" and path == "/api/radio/preview":
            return handler.json(200, preview(cfg, q.get("link")))
        if method == "POST" and path in ("/api/radio/review/match", "/api/radio/review/rescan", "/api/radio/add-link"):
            body = handler.body()
            if path.endswith("/match"):
                out = match(cfg, body.get("file"), body.get("episode"))
            elif path.endswith("/rescan"):
                out = rescan(cfg)
            else:
                out = add(cfg, body.get("link"), str(body.get("follow") or "all"))
            logs.event("info", "library", f"Radio: {out['done']}")
            return handler.json(200, out)
    except ValueError as e:
        return handler.error(400, str(e))
    return handler.error(404, "Not found")
