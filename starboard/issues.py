"""Activity, Requests, Issues (DASH-208): problems people report with a film or series in Reelix (no sound, wrong
subtitles and so on), with the thread of comments, Comment, Resolve and Reopen. Read and changed through Reelix's
own routes with Starboard's manager key."""
from . import services

TYPES = {"video": "Picture", "audio": "Sound", "subtitles": "Subtitles", "other": "Something else"}


def _reelix(all_services):
    found = services.reelix_native(all_services)
    if not found:
        raise ValueError("Add Reelix in Settings, Manage apps, with its key, to see issues")
    return found[0]


def _slim(i):
    where = ""
    if i.get("season") is not None:
        where = f"Season {i['season']}" + (f", episode {i['episode']}" if i.get("episode") is not None else "")
    return {"id": i["id"], "title": i.get("title") or "Untitled", "year": i.get("year"), "kind": "Film" if i.get("kind") == "movie" else "Series",
            "type": TYPES.get(i.get("issue_type"), "Something else"), "open": i.get("status") == "open", "where": where,
            "message": i.get("message") or "", "by": (i.get("reported_by") or {}).get("display_name", ""),
            "when": i.get("created_at") or "", "comments": int(i.get("comment_count") or 0),
            "thread": [{"by": (c.get("user") or {}).get("display_name", ""), "message": c.get("message") or "", "when": c.get("created_at") or ""}
                       for c in i.get("comments") or []]}


def listing(all_services, status="open"):
    if status not in ("open", "resolved", "all"):
        raise ValueError("Choose Open, Resolved or All")
    r = _reelix(all_services)
    page = services._api(r, "/issues", {"status": status, "page_size": 50}) or {}
    try:
        counts = services._api(r, "/issues/count") or {}
    except services.ServiceError:
        counts = {}
    return {"items": [_slim(i) for i in page.get("items") or []], "open": int(counts.get("open") or 0), "total": int(page.get("total") or 0)}


def one(all_services, issue_id):
    return _slim(services._api(_reelix(all_services), f"/issues/{int(issue_id)}") or {})


def act(all_services, issue_id, action, message=""):
    """comment, resolve or reopen. Returns the issue as it is now."""
    r = _reelix(all_services)
    if action == "comment":
        text = str(message or "").strip()
        if not text:
            raise ValueError("Type a comment first")
        found = services._api(r, f"/issues/{int(issue_id)}/comments", method="POST", body={"message": text[:4000]})
    elif action in ("resolve", "reopen"):
        found = services._api(r, f"/issues/{int(issue_id)}/{action}", method="POST")
    else:
        raise ValueError("Choose Comment, Resolve or Reopen")
    return _slim(found) if isinstance(found, dict) and found.get("id") else one(all_services, issue_id)
