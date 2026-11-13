"""Search the sites directly (DASH-213): a free search across the sites Reelix searches, and Get this one.

Reelix's own Search page does the same (GET /indexers/search, POST /releases/grab with the release's own link, which
Reelix calls a raw grab). Both need only Reelix's Manage library right, so Starboard's manager key is enough and no
password is asked. A raw grab is not tied to a film or an episode: the download is followed in the queue, and Reelix
waits for someone to say what it is when it finishes (Activity, Downloads).

The release links (which can hold a private site's key) stay on the server: the browser gets the results without
them and a token, and Get this one sends the token and the row's number back. The last few searches are kept in
memory for 30 minutes, then dropped (lightweight rule). 13 November 2026.
"""
import secrets
import threading
import time

from . import services

KINDS = {"all": "basic", "films": "movie", "tv": "tv", "books": "book", "music": "music"}
KEEP_FOR = 1800  # seconds a search's results can still be got
KEEP_AT_MOST = 5  # searches kept at once
SHOWN = 100  # results asked of Reelix
FLAGS = {"freeleech": "Free to download", "halfleech": "Half counts", "double_upload": "Double upload", "internal": "Site's own release",
         "scene": "Scene", "nuked": "Nuked", "free_upload_slot": "Free upload slot"}
_kept = {}
_lock = threading.Lock()


def _reelix(svcs):
    found = services.reelix_native(svcs)
    if not found:
        raise ValueError("Reelix is not on your dashboard with its key. Add it in Settings, Manage apps")
    return found[0]


def _forget_old(now):
    for k in [k for k, (t, _) in _kept.items() if now - t > KEEP_FOR]:
        del _kept[k]
    while len(_kept) >= KEEP_AT_MOST:
        del _kept[min(_kept, key=lambda k: _kept[k][0])]


def search(svcs, q, kind="all", site=None):
    q = " ".join(str(q or "").split())
    if len(q) < 2 or len(q) > 200:
        raise ValueError("Type at least 2 letters to search for")
    if kind not in KINDS:
        raise ValueError("Choose what to search for from the list")
    params = {"q": q, "kind": KINDS[kind], "limit": SHOWN}
    if site not in (None, "", "all"):
        try:
            params["ids"] = str(int(site))
        except (TypeError, ValueError):
            raise ValueError("Choose a site from the list") from None
    reelix = _reelix(svcs)
    try:
        answer = services._api(reelix, "/indexers/search", params, timeout=90) or {}
    except services.ServiceError as e:
        raise ValueError(f"Reelix could not search: {e}") from None
    releases = [r for r in answer.get("releases") or [] if isinstance(r, dict) and r.get("guid") and r.get("indexer_id") is not None]
    rows = []
    for i, r in enumerate(releases):
        rows.append({"n": i, "title": str(r.get("title") or ""), "site": str(r.get("indexer") or ""), "site_id": r.get("indexer_id"),
                     "protocol": "usenet" if r.get("protocol") == "usenet" else "torrent", "size": r.get("size"),
                     "seeders": r.get("seeders"), "peers": r.get("peers"), "grabs": r.get("grabs"), "published": r.get("publish_date"),
                     "flags": [FLAGS[f] for f in r.get("indexer_flags") or [] if f in FLAGS], "info_url": _safe_url(r.get("info_url")),
                     "can_get": bool(r.get("download_url") or r.get("magnet_url"))})
    outcome = [{"id": o.get("indexer_id"), "name": str(o.get("name") or ""), "count": int(o.get("count") or 0),
                "seconds": round((o.get("elapsed_ms") or 0) / 1000, 1), "error": str(o.get("error") or "")}
               for o in answer.get("indexers") or [] if isinstance(o, dict)]
    now = time.time()
    token = secrets.token_urlsafe(12)
    with _lock:
        _forget_old(now)
        _kept[token] = (now, releases)
    return {"token": token, "q": q, "kind": kind, "results": rows, "sites": outcome}


def _safe_url(url):
    """A release's page on its site, for a link: only http and https, never a magnet or a script."""
    url = str(url or "")
    return url if url.startswith(("https://", "http://")) and len(url) < 2000 else ""


def grab(svcs, token, n):
    with _lock:
        _forget_old(time.time())
        kept = _kept.get(str(token or ""))
    if not kept:
        raise ValueError("These results are too old to get from. Search again")
    try:
        r = kept[1][int(n)]
    except (TypeError, ValueError, IndexError):
        raise ValueError("Choose a result from the list") from None
    link = r.get("download_url") or r.get("magnet_url")
    if not link:
        raise ValueError("This site gave no link to download it with")
    body = {"guid": str(r["guid"]), "indexer_id": int(r["indexer_id"]), "download_url": link, "title": str(r.get("title") or "")}
    try:
        out = services._api(_reelix(svcs), "/releases/grab", method="POST", body=body, timeout=60) or {}
    except services.ServiceError as e:
        raise ValueError(f"Reelix did not get it: {e}") from None
    services.forget("queue")
    client = out.get("download_client") or "the download app"
    return {"done": f"Sent to {client}", "title": body["title"], "client": client, "queue_id": out.get("queue_id")}


def route(handler, method, path):
    """GET /api/reelix/sites/search?q=&kind=&site= and POST /api/reelix/sites/grab {token, n}."""
    import urllib.parse
    from . import logs
    svcs = handler.app.config.data["services"]
    try:
        if path == "/api/reelix/sites/search" and method == "GET":
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(handler.path).query))
            return handler.json(200, search(svcs, q.get("q"), q.get("kind") or "all", q.get("site")))
        if path == "/api/reelix/sites/grab" and method == "POST":
            body = handler.body()
            out = grab(svcs, body.get("token"), body.get("n"))
            logs.event("info", "reelix", f"Search the sites: {out['done'].lower()}: {out['title']}")
            return handler.json(200, out)
    except ValueError as e:
        return handler.error(400, str(e))
    return handler.error(404, "Not found")
