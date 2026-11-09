"""What is left to set up (DASH-185): a short checklist on the first screen and at the end of both set-ups, like
Reelix's own. Each item says what it is for, links to the Starboard place that does it, and goes once done; the
list goes once everything is done. Worked out only when a page asks, and kept for 5 minutes (lightweight rule).

Where each answer comes from: Reelix's own health checks (sites to search, download apps), read with Starboard's
manager key; the Usenet app's own settings (a news server); Starboard's dashboard (Jellyfin and Audiobookshelf
with their keys); and what Starboard's set-up did, kept in data/stack/setup-state.json (the TMDB key, media servers
connected to Reelix, radio), because Reelix shows those only to its admin."""
import json
import os
import threading
import time

from . import services, stack

STATE_FILE = "setup-state.json"
KEEP = 300
_cache = {}
_lock = threading.Lock()


def record(data_dir, **values):
    """Notes what the set-up or Settings did (tmdb, media_servers, radio), for the checklist."""
    path = os.path.join(stack.folder(data_dir), STATE_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            current = json.load(f)
    except (OSError, ValueError):
        current = {}
    current.update(values)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(current, f)
    forget()


def recorded(data_dir):
    try:
        with open(os.path.join(stack.folder(data_dir), STATE_FILE), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def forget():
    with _lock:
        _cache.clear()


def _reelix_health(svcs):
    """Reelix's health checks, read with the manager key (Reelix answers 503 with the same list when one is an
    error); None when Reelix is not on the dashboard or does not answer."""
    import urllib.error
    import urllib.request
    reelix = next((s for s in svcs if s.get("icon") == "reelix" and s["type"] == "link" and s.get("api_key")), None)
    if not reelix:
        return None
    req = urllib.request.Request(reelix["url"].rstrip("/") + "/api/v1/system/health",
                                 headers={"X-Api-Key": reelix["api_key"], "Accept": "application/json", "User-Agent": "Starboard"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:  # Reelix's address from Starboard's own set-up  # nosec B310
            raw = r.read(200000)
    except urllib.error.HTTPError as e:
        if e.code != 503:
            return None
        raw = e.read(200000)
    except (urllib.error.URLError, OSError):
        return None
    try:
        body = json.loads(raw)
    except ValueError:
        return None
    return body.get("checks") or [] if isinstance(body, dict) else None


def _usenet_server(svcs):
    """True when the Usenet app has a news server, False when not, None when there is no Usenet app to ask."""
    for s in svcs:
        if not (s.get("enabled", True) and s.get("api_key")):
            continue
        try:
            if s["type"] == "nzbget":
                cfg = {o.get("Name"): o.get("Value") for o in services.nzbget(s, "config") or []}
                return any(v for k, v in cfg.items() if k.startswith("Server") and k.endswith(".Host"))
            if s["type"] == "sabnzbd":
                return bool((services.sab(s, "get_config", section="servers").get("config") or {}).get("servers"))
        except services.ServiceError:
            return None
    return None


def items(cfg, data_dir):
    """[{key, title, why, href, done}] for what applies to this install; done ones are kept so pages can count, and
    one whose app could not be asked is left out."""
    keys = set(stack.chosen_keys(data_dir) or [])
    if not keys:
        return []
    svcs = cfg.data["services"]
    state = recorded(data_dir)
    groups = set(stack.chosen_groups(data_dir) or [])
    has = lambda kind: any(s["type"] == kind and s.get("api_key") for s in svcs)  # noqa: E731
    out = []
    if "reelix" in keys:
        health = _reelix_health(svcs)
        msgs = {c.get("source"): c.get("message", "") for c in health or [] if c.get("level") in ("warning", "error")}
        out.append({"key": "sites", "title": "Add a site to search", "why": "Reelix needs at least one site to find releases.",
                    "href": "/settings-reelix.html#rx-indexers-h", "done": None if health is None else "No indexers" not in msgs.get("indexers", "")})
        out.append({"key": "download", "title": "Connect a download app", "why": "Reelix hands what it finds to a download app.",
                    "href": "/settings-reelix.html#rx-downloadclients-h",
                    "done": None if health is None else "No download clients" not in msgs.get("download_clients", "")})
        out.append({"key": "tmdb", "title": "Add a TMDB key", "why": "Reelix finds films and series far better with a free TMDB key.",
                    "href": "/settings-reelix.html", "done": bool(state.get("tmdb"))})
    if keys & {"nzbget", "sabnzbd"}:
        server = _usenet_server(svcs)
        out.append({"key": "usenet", "title": "Add your Usenet provider's server", "why": "The Usenet app downloads nothing without one.",
                    "href": "/install-apps.html", "done": server})
    if "jellyfin" in keys:
        out.append({"key": "jellyfin", "title": "Finish Jellyfin's set-up", "why": "Starboard makes Jellyfin's admin and libraries.",
                    "href": "/settings-jellyfin.html", "done": has("jellyfin")})
    if "audiobookshelf" in keys:
        out.append({"key": "audiobookshelf", "title": "Finish Audiobookshelf's set-up", "why": "Starboard makes its admin and libraries.",
                    "href": "/settings-audiobookshelf.html", "done": has("audiobookshelf")})
    if "reelix" in keys and keys & {"jellyfin", "audiobookshelf"}:
        out.append({"key": "mediaservers", "title": "Connect Reelix to your media servers", "why": "New files then show in them at once.",
                    "href": "/settings-reelix.html#rx-mediaservers-h", "done": bool(state.get("media_servers"))})
    if "reelix" in keys and "radio" in groups and "audiobookshelf" in keys:
        out.append({"key": "radio", "title": "Point Reelix's radio at Audiobookshelf", "why": "Radio shows then play in Audiobookshelf.",
                    "href": "/settings-reelix.html", "done": bool(state.get("radio"))})
    return [i for i in out if i["done"] is not None]  # one Starboard could not ask is left out, not guessed


def left(cfg, data_dir):
    """{items, left}: cached for 5 minutes."""
    with _lock:
        hit = _cache.get("left")
        if hit and time.time() - hit[0] < KEEP:
            return hit[1]
    out = items(cfg, data_dir)
    result = {"items": out, "left": sum(1 for i in out if not i["done"])}
    with _lock:
        _cache["left"] = (time.time(), result)
    return result
