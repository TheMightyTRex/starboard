"""Held downloads (DASH-210): releases Reelix found but is holding back, because a delay profile waits for a better
release or for the preferred kind of download (GET /pending). Get it now sends one to the download app at once
(POST /pending/{id}/grab); Remove drops it (DELETE /pending/{id}), and Reelix may find it again at its next search.
All three need only Reelix's Manage library right, so Starboard's manager key is enough and no password is asked.
Asked only while Activity, Downloads is open (lightweight rule)."""
from . import services

REASONS = {"delay": "Waiting for the delay to pass", "preferred_protocol": "Waiting for the preferred kind of download"}


def _reelix(svcs):
    found = services.reelix_native(svcs)
    return found[0] if found else None


def _what(media, episodes):
    """What a held release is for, in words: "Harbour Lights (2019), S02E03" or "Made-up Author: A Book"."""
    if not isinstance(media, dict):
        return ""
    title = str(media.get("title") or "")
    if media.get("year"):
        title += f" ({media['year']})"
    if media.get("subtitle"):
        title = f"{media['subtitle']}: {title}"
    eps = [f"S{int(e.get('season_number') or 0):02d}E{int(e.get('episode_number') or 0):02d}" for e in episodes or [] if isinstance(e, dict)]
    if eps:
        title += ", " + (eps[0] if len(eps) == 1 else f"{eps[0]} to {eps[-1]}")
    return title


def _slim(p):
    quality = p.get("quality") or {}
    return {"id": p.get("id"), "release": str(p.get("title") or ""), "what": _what(p.get("media"), p.get("episodes")),
            "quality": str(quality.get("quality") or "") if isinstance(quality, dict) else "", "site": str(p.get("indexer") or ""),
            "protocol": str(p.get("protocol") or ""), "reason": REASONS.get(p.get("reason"), "Held back by a delay profile"),
            "added": p.get("added"), "release_at": p.get("release_at")}


def listing(svcs):
    """{available, items}: every held release, the one Reelix lets go first at the top."""
    reelix = _reelix(svcs)
    if not reelix:
        return {"available": False, "items": []}
    rows = services._api(reelix, "/pending", timeout=20) or []
    items = [_slim(p) for p in rows if isinstance(p, dict) and isinstance(p.get("id"), int)]
    return {"available": True, "items": sorted(items, key=lambda i: str(i.get("release_at") or ""))}


def grab(svcs, pid):
    reelix = _reelix(svcs)
    if not reelix:
        raise ValueError("Reelix is not on your dashboard with its key. Add it in Settings, Manage apps")
    out = services._api(reelix, f"/pending/{int(pid)}/grab", method="POST", timeout=60) or {}
    client = out.get("download_client") or "the download app"
    return {"said": f"Sent to {client}", "client": client}


def remove(svcs, pid):
    reelix = _reelix(svcs)
    if not reelix:
        raise ValueError("Reelix is not on your dashboard with its key. Add it in Settings, Manage apps")
    services._api(reelix, f"/pending/{int(pid)}", method="DELETE", timeout=30)
    return {"said": "Removed"}


def route(handler, method, path):
    """GET /api/held, POST /api/held/{id}/grab, DELETE /api/held/{id}."""
    from . import logs
    svcs = handler.app.config.data["services"]
    parts = path.strip("/").split("/")  # api, held[, id[, grab]]
    try:
        if parts == ["api", "held"] and method == "GET":
            return handler.json(200, listing(svcs))
        if len(parts) == 4 and parts[3] == "grab" and parts[2].isdigit() and method == "POST":
            out = grab(svcs, parts[2])
            logs.event("info", "downloads", f"Held download {parts[2]} sent to {out['client']}")
            return handler.json(200, out)
        if len(parts) == 3 and parts[2].isdigit() and method == "DELETE":
            out = remove(svcs, parts[2])
            logs.event("info", "downloads", f"Held download {parts[2]} removed")
            return handler.json(200, out)
    except ValueError as e:
        return handler.error(400, str(e))
    except services.ServiceError as e:
        return handler.error(getattr(e, "status", 502) if getattr(e, "status", 0) in (404, 503) else 502, str(e))
    return handler.error(404, "Not found")
