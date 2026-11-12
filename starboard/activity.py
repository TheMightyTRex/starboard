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


KEEP_CHOICES = (0, 7, 30, 90, 365)  # days; 0 keeps everything


def _cutoff(prefs):
    """The oldest moment History shows: the keep choice, or the last Delete history, whichever is later (ISO text)."""
    import datetime as dt
    keep = int((prefs or {}).get("history_keep_days") or 0)
    cleared = str((prefs or {}).get("history_cleared_at") or "")
    edges = [cleared] if cleared else []
    if keep:
        edges.append((dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=keep)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return max(edges) if edges else ""


def delete_history(all_services, prefs, now_iso):
    """Delete history: asks Reelix to delete when it can; Starboard hides what came before now either way. Returns
    the words to show."""
    try:
        services._api(_reelix(all_services), "/history", {"before": now_iso}, method="DELETE")
        deleted = True
    except services.ServiceError:
        deleted = False  # Reelix cannot delete yet (RFX-105): hidden here instead
    prefs["history_cleared_at"] = now_iso
    return ("History deleted" if deleted else
            "History cleared here. Reelix keeps its own copy until it can delete history (planned)")


def history(all_services, which="all", page=1, prefs=None):
    if which not in FILTERS:
        raise ValueError("Choose All, Sent, Added or Failed")
    params = {"page": max(1, int(page)), "page_size": PAGE}
    if FILTERS[which]:
        params["event_type"] = FILTERS[which]
    answer = services._api(_reelix(all_services), "/history", params) or {}
    out = []
    cutoff = _cutoff(prefs)
    older = False
    for h in answer.get("items") or []:
        if cutoff and str(h.get("date") or "") < cutoff:
            older = True  # newest first: everything after this is older too
            continue
        q = (h.get("quality") or {}).get("quality") or ""
        data = h.get("data") or {}
        out.append({"id": h["id"], "event": EVENTS.get(h.get("event_type"), h.get("event_type") or ""), "tone": TONES.get(h.get("event_type"), "muted"),
                    "date": h.get("date") or "", "what": _what(h.get("media"), h.get("episode")), "href": _href(h.get("media")),
                    "release": h.get("source_title") or "", "quality": q if isinstance(q, str) else "",
                    "where": h.get("indexer") or h.get("download_client") or "",
                    "message": str(data.get("message") or data.get("reason") or "")[:300]})
    total = (params["page"] - 1) * PAGE + len(out) if older else int(answer.get("total") or 0)
    return {"items": out, "total": total, "page": params["page"], "page_size": PAGE,
            "keep_days": int((prefs or {}).get("history_keep_days") or 0), "cleared_at": (prefs or {}).get("history_cleared_at") or ""}


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
