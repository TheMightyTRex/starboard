"""Plug-in cards on the dashboard (DASH-149): a plug-in declares a card (stat, list or status) and a path on its
main container; Starboard asks that path at most once a minute whatever the number of people looking, checks the
answer's shape, cuts long text, and draws the card itself. A card's text is never treated as HTML.

The answers, by type:
  stat    {"value": 42, "label": "titles", "note": "3 added today"}
  list    {"items": [{"title": "Dune", "detail": "Added today", "link": "https://..."}]}   (10 at most)
  status  {"state": "ok" | "warning" | "problem", "text": "Up to date"}
"""
import json
import re
import threading
import time
import urllib.request

KEEP = 60
TIMEOUT = 3
MAX_BYTES = 64 * 1024
_cache = {}
_lock = threading.Lock()


def _text(value, limit):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value))[:limit].strip() if value is not None else ""


def clean(card_type, data):
    """The answer reduced to what Starboard draws, or ValueError saying what is wrong (the tester uses this too)."""
    if not isinstance(data, dict):
        raise ValueError("The answer must be a JSON object")
    if card_type == "stat":
        v = data.get("value")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise ValueError("A stat card needs a number in value")
        return {"value": v, "label": _text(data.get("label"), 40), "note": _text(data.get("note"), 80)}
    if card_type == "list":
        items = data.get("items")
        if not isinstance(items, list):
            raise ValueError("A list card needs items, a list")
        out = []
        for it in items[:10]:
            if not isinstance(it, dict) or not it.get("title"):
                raise ValueError("Each item in a list card needs a title")
            link = str(it.get("link") or "")
            out.append({"title": _text(it["title"], 80), "detail": _text(it.get("detail"), 120),
                        "link": link if re.match(r"^https?://[^\s\"'<>]{1,500}$", link) else ""})
        return {"items": out}
    if card_type == "status":
        if data.get("state") not in ("ok", "warning", "problem"):
            raise ValueError("A status card needs state: ok, warning or problem")
        return {"state": data["state"], "text": _text(data.get("text"), 160)}
    raise ValueError("Cards are stat, list or status")


def _host(pid, main):
    """Where Starboard reaches a plug-in's main container: by name when Docker's names resolve here; when Starboard
    uses the computer's own network (they do not), at the container's address on its own network."""
    import socket
    name = "gluetun" if main.get("network") == "vpn" else f"plugin-{pid}-{main['name']}"
    try:
        socket.gethostbyname(name)
        return name
    except OSError:
        pass
    from . import containers
    try:
        nets = (containers.docker("GET", f"/containers/{name}/json").get("NetworkSettings") or {}).get("Networks") or {}
    except containers.DockerError:
        return name
    own = nets.get(f"plugin-{pid}") or next(iter(nets.values()), {})
    return own.get("IPAddress") or name


def available(data_dir):
    """Cards from active plug-ins, for Edit dashboard: [{id, title, type, format, plugin}]."""
    from . import plugins_admin
    out = []
    for p in plugins_admin.listing(data_dir):
        if p["state"] != "enabled":
            continue
        m = plugins_admin._read(f"{plugins_admin.folder(data_dir, p['id'])}/manifest.json", {}) or {}
        for i, c in enumerate(m.get("cards") or []):
            cid = c.get("id") or str(i)
            out.append({"id": f"plugin:{p['id']}:{cid}", "title": c.get("title") or p["name"], "type": c["type"],
                        "format": c.get("format", "number"), "plugin": p["name"]})
    return out


def answer(data_dir, pid, cid, opener=None):
    """One card's checked answer, kept for a minute: {type, format, data} or {type, problem}."""
    from . import plugins_admin
    key = (pid, cid)
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < KEEP:
            return hit[1]
    m = plugins_admin._read(f"{plugins_admin.folder(data_dir, pid)}/manifest.json", {}) or {}
    cards = {(c.get("id") or str(i)): c for i, c in enumerate(m.get("cards") or [])}
    card = cards.get(cid)
    if not card or not m.get("containers"):
        raise LookupError("No such card")
    main = m["containers"][0]
    url = f"http://{_host(pid, main)}:{int(main.get('port') or 80)}{card['path']}"
    out = {"type": card["type"], "format": card.get("format", "number")}
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Starboard"})
        with (opener or urllib.request.build_opener()).open(req, timeout=TIMEOUT) as r:  # the plug-in's own container  # nosec B310
            raw = r.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("The answer is larger than 64 KB")
        out["data"] = clean(card["type"], json.loads(raw))
    except (OSError, ValueError) as e:
        out["problem"] = f"No answer from {m.get('name', pid)}" + (f": {e}" if isinstance(e, ValueError) else "")
    with _lock:
        _cache[key] = (time.time(), out)
    return out


def action(data_dir, pid, aid, opener=None):
    """Runs one of a plug-in's buttons: a POST to its path on the plug-in's main container. {said}."""
    from . import plugins_admin
    m = plugins_admin._read(f"{plugins_admin.folder(data_dir, pid)}/manifest.json", {}) or {}
    act = next((a for a in m.get("actions") or [] if (a.get("id") or "") == aid), None)
    if not act or not m.get("containers"):
        raise LookupError("No such button")
    main = m["containers"][0]
    req = urllib.request.Request(f"http://{_host(pid, main)}:{int(main.get('port') or 80)}{act['path']}", data=b"", method="POST",
                                 headers={"Accept": "application/json", "User-Agent": "Starboard"})
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=10) as r:  # the plug-in's own container  # nosec B310
            raw = r.read(MAX_BYTES)
        said = (json.loads(raw) or {}).get("said") if raw[:1] == b"{" else ""
    except (OSError, ValueError) as e:
        raise ValueError(f"{m.get('name', pid)} did not answer: {e}") from None
    return {"said": _text(said or f"{act['label']}: started", 160)}
