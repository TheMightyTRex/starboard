"""Activity, History (DASH-159): what Reelix found, downloaded, moved into the library and removed, newest first, and
the refused list (Reelix's blocklist: releases it will not download again), with Take off the list. Read from
Reelix's own routes with Starboard's manager key, a page at a time."""
from . import services

EVENTS = {"grabbed": "Sent to the download app", "imported": "Added to your library", "download_failed": "Download failed",
          "import_failed": "Could not be added", "file_deleted": "File deleted", "renamed": "Renamed", "ignored": "Ignored"}
TONES = {"imported": "success", "grabbed": "info", "download_failed": "danger", "import_failed": "danger", "file_deleted": "muted",
         "renamed": "muted", "ignored": "muted"}
FILTERS = {"all": None, "grabbed": "grabbed", "imported": "imported", "failed": "download_failed"}
PAGE = 50


def _reelix(all_services):
    found = services.reelix_native(all_services)
    if not found:
        raise ValueError("Add Reelix in Settings, Manage apps, with its key, to see its history")
    return found[0]


def _what(media, episode):
    if not media:
        return ""
    title = media.get("title") or ""
    if episode:
        return f"{title} S{int(episode.get('season_number') or 0):02d}E{int(episode.get('episode_number') or 0):02d}"
    return f"{title} ({media['year']})" if media.get("year") else title


def _href(media):
    kind, i = (media or {}).get("kind"), (media or {}).get("id")
    return {"movie": f"/library-film.html?id={i}", "series": f"/library-tv-show.html?id={i}"}.get(kind, "") if i else ""


def history(all_services, which="all", page=1):
    if which not in FILTERS:
        raise ValueError("Choose All, Sent, Added or Failed")
    params = {"page": max(1, int(page)), "page_size": PAGE}
    if FILTERS[which]:
        params["event_type"] = FILTERS[which]
    answer = services._api(_reelix(all_services), "/history", params) or {}
    out = []
    for h in answer.get("items") or []:
        q = (h.get("quality") or {}).get("quality") or ""
        data = h.get("data") or {}
        out.append({"id": h["id"], "event": EVENTS.get(h.get("event_type"), h.get("event_type") or ""), "tone": TONES.get(h.get("event_type"), "muted"),
                    "date": h.get("date") or "", "what": _what(h.get("media"), h.get("episode")), "href": _href(h.get("media")),
                    "release": h.get("source_title") or "", "quality": q if isinstance(q, str) else "",
                    "where": h.get("indexer") or h.get("download_client") or "",
                    "message": str(data.get("message") or data.get("reason") or "")[:300]})
    return {"items": out, "total": int(answer.get("total") or 0), "page": params["page"], "page_size": PAGE}


def refused(all_services, page=1):
    answer = services._api(_reelix(all_services), "/blocklist", {"page": max(1, int(page)), "page_size": PAGE}) or {}
    items = answer.get("items") if isinstance(answer, dict) else answer
    out = []
    for b in items or []:
        q = (b.get("quality") or {}).get("quality") or ""
        out.append({"id": b["id"], "what": _what(b.get("media"), None), "href": _href(b.get("media")), "release": b.get("source_title") or "",
                    "quality": q if isinstance(q, str) else "", "where": b.get("indexer") or "", "message": b.get("message") or "",
                    "date": b.get("date") or ""})
    total = int(answer.get("total") or len(out)) if isinstance(answer, dict) else len(out)
    return {"items": out, "total": total, "page": int(page), "page_size": PAGE}


def take_off(all_services, item_id):
    """Takes one release off the refused list, so Reelix may download it again."""
    services._api(_reelix(all_services), f"/blocklist/{int(item_id)}", method="DELETE")
    return "Taken off the refused list. Reelix may download it again"
