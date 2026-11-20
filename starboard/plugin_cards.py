"""Plug-in cards on the dashboard (DASH-149): a plug-in declares a card (stat, list, status, guide or sparkline) and a path on its
main container; Starboard asks that path at most once a minute whatever the number of people looking, checks the
answer's shape, cuts long text, and draws the card itself. A card's text is never treated as HTML.

The answers, by type:
  stat    {"value": 42, "label": "titles", "note": "3 added today"}
  list    {"items": [{"title": "Dune", "detail": "Added today", "link": "https://..."}]}   (10 at most)
  status  {"state": "ok" | "warning" | "problem", "text": "Up to date"}
  guide   {"items": [{"channel": "Kestrel Sport", "number": "601", "now": "Football Extra", "start": 1794..., "stop": 1794...,
                      "next": "Darts", "next_start": 1794...}], "note": "..."}   (12 at most; times are Unix seconds)
  sparkline {"series": [{"title": "Router", "points": [12.5, 14, null, 15], "unit": "ms", "detail": "Average 13 ms"}],
             "note": "..."}   (API 1.17: 8 series at most, each 1 to 96 points, a number of 0 or more or null for a gap)

Any answer may also carry (plug-in API 1.14):
  refresh_seconds  how soon the dashboard asks again, 10 to 3600
  status           a word from STATUSES, shown as a chip in the card's grey band (DASH-428, design 2)
  status_label     its own words for that chip, up to 24 characters; the chip's colour still comes from status
  updated          when what it shows last changed, in Unix seconds; without it, the band says when Starboard asked
"""
import json
import math
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


def refresh_seconds(value):
    """A card's own refresh time (plug-in API 1.14): a whole number of seconds held to 10 to 3600, so no plug-in can
    make the dashboard ask more often than every 10 seconds; None when it says nothing or nothing usable."""
    from .plugins import REFRESH_MAX, REFRESH_MIN
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(max(REFRESH_MIN, min(value, REFRESH_MAX)))


# The card band's status chip (API 1.14, DASH-428): each status, its words and its chip's tone in the design system
# (success, info, neutral, muted, warning, danger). Words and a shape, never colour alone.
STATUSES = {
    "ok": ("OK", "success"), "done": ("Done", "success"), "ready": ("Ready", "success"), "protected": ("Protected", "success"),
    "working": ("Working", "info"), "converting": ("Converting", "info"), "scanning": ("Scanning", "info"),
    "updating": ("Updating", "info"), "running": ("Running", "info"),
    "waiting": ("Waiting", "neutral"), "idle": ("Idle", "neutral"), "scheduled": ("Scheduled", "neutral"),
    "paused": ("Paused", "muted"), "inactive": ("Inactive", "muted"),
    "warning": ("Warning", "warning"), "needs_setup": ("Needs setting up", "warning"),
    "problem": ("Problem", "danger"), "failed": ("Failed", "danger"), "stopped": ("Stopped", "danger"),
}
STATUS_LABEL_MAX = 24


def band(data, problems=None):
    """The band's status and time from an answer (API 1.14): {status, status_label, tone, updated}, only what it gave.
    An unknown status is left out (and said in `problems`, for the tester), never guessed."""
    out = {}
    status = data.get("status")
    if status is not None:
        if status in STATUSES:
            words, tone = STATUSES[status]
            label = _text(data.get("status_label"), STATUS_LABEL_MAX) if data.get("status_label") else ""
            out.update(status=status, status_label=label or words, tone=tone)
        elif problems is not None:
            problems.append(f"status must be one of {', '.join(STATUSES)}")
    elif data.get("status_label") and problems is not None:
        problems.append("status_label needs a status, which sets the chip's colour")
    upd = data.get("updated")
    if isinstance(upd, (int, float)) and not isinstance(upd, bool) and 946684800 <= upd <= time.time() + 300:
        out["updated"] = int(upd)
    elif upd is not None and problems is not None:
        problems.append("updated must be a time in Unix seconds, not in the future")
    return out


def clean(card_type, data, strict=False):
    """The answer reduced to what Starboard draws, or ValueError saying what is wrong (the tester uses this too, with
    `strict`, so a status Starboard does not know is reported rather than left out). Any card may add
    refresh_seconds, status, status_label and updated (API 1.14)."""
    if not isinstance(data, dict):
        raise ValueError("The answer must be a JSON object")
    out = _clean(card_type, data)
    every = refresh_seconds(data.get("refresh_seconds"))
    if every:
        out["refresh_seconds"] = every
    problems = [] if strict else None
    out.update(band(data, problems))
    if problems:
        raise ValueError("; ".join(problems))
    return out


def _clean(card_type, data):
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
    if card_type == "guide":  # what is on now, one row a channel (API 1.8, DASH-359)
        items = data.get("items")
        if not isinstance(items, list):
            raise ValueError("A guide card needs items, a list")
        out = []
        for it in items[:12]:
            if not isinstance(it, dict) or not it.get("channel"):
                raise ValueError("Each item in a guide card needs a channel")
            times = {k: it[k] for k in ("start", "stop", "next_start") if isinstance(it.get(k), (int, float)) and not isinstance(it.get(k), bool)}
            out.append({"channel": _text(it["channel"], 80), "number": _text(it.get("number"), 8), "now": _text(it.get("now"), 120),
                        "next": _text(it.get("next"), 120), **times})
        return {"items": out, "note": _text(data.get("note"), 120)}
    if card_type == "sparkline":  # a small line for each series, such as response times (API 1.17)
        series = data.get("series")
        if not isinstance(series, list) or not series:
            raise ValueError("A sparkline card needs series, a list")
        out = []
        for s in series[:SPARK_SERIES]:
            if not isinstance(s, dict) or not s.get("title"):
                raise ValueError("Each series in a sparkline card needs a title")
            points = s.get("points")
            if not isinstance(points, list) or not 1 <= len(points) <= SPARK_POINTS:
                raise ValueError(f"Each series in a sparkline card needs points: a list of 1 to {SPARK_POINTS} numbers")
            if not all(p is None or (isinstance(p, (int, float)) and not isinstance(p, bool) and math.isfinite(p) and p >= 0) for p in points):
                raise ValueError("Each point in a sparkline card must be a number of 0 or more, or null for a gap")
            unit = _text(s.get("unit"), 8)
            out.append({"title": _text(s["title"], 80), "points": points, "unit": unit, "detail": _text(s.get("detail"), 120),
                        "summary": spark_summary(points, unit)})
        return {"series": out, "note": _text(data.get("note"), 120)}
    raise ValueError("Cards are stat, list, status, guide or sparkline")


SPARK_SERIES, SPARK_POINTS = 8, 96  # a sparkline card shows 8 series at most, each of 1 to 96 points (API 1.17)


def _figure(value, unit):
    """A number as people read it, rounded to what matters (1,500, 15, 12.5, 0.25), with its unit."""
    v = round(value) if value >= 100 else round(value, 1) if value >= 10 else round(value, 2)
    words = f"{v:,.0f}" if v == int(v) else f"{v:,}".rstrip("0").rstrip(".")
    return words + ("" if not unit else unit if unit == "%" else f" {unit}")


def spark_summary(points, unit=""):
    """What a sparkline shows, in words for everyone and screen readers (API 1.17): the latest point, the lowest and
    the highest, such as "Now 15 ms, lowest 12.5 ms, highest 15 ms". "Latest" when the last point is a gap."""
    known = [p for p in points if p is not None]
    if not known:
        return "No readings yet"
    first = "Now" if points[-1] is not None else "Latest"
    return f"{first} {_figure(known[-1], unit)}, lowest {_figure(min(known), unit)}, highest {_figure(max(known), unit)}"


def _host(pid, main, wake=True):
    """Where Starboard reaches a plug-in's main container: by name when Docker's names resolve here; when Starboard
    uses the computer's own network (they do not), at the container's address on its own network. `wake`: this is a
    real call, so a plug-in resting after idle stop is started first (DASH-357); a health check passes False."""
    import socket
    if wake:
        from . import plugin_watch
        plugin_watch.used(pid, main)
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
    """Cards from active plug-ins, for Edit dashboard and the card band (API 1.14): [{id, title, titles, type, format,
    plugin, plugin_id, logo}], logo being {url, alt} or None for the initials, and titles the card's title for each
    size it gave (API 1.15, DASH-443), only those that pass the manifest check."""
    from .plugins import card_title_problems
    from . import plugins_admin
    out = []
    for p in plugins_admin.basics(data_dir):  # only the active ones' manifests and logos are read
        if p["state"] != "enabled":
            continue
        m = plugins_admin._read_kept(f"{plugins_admin.folder(data_dir, p['id'])}/manifest.json", {}) or {}
        logo = plugins_admin.logo_info(data_dir, p["id"], m) if m.get("cards") else None
        for i, c in enumerate(m.get("cards") or []):
            cid = c.get("id") or str(i)
            titles = c.get("titles") if isinstance(c.get("titles"), dict) and not card_title_problems(c) else {}
            out.append({"id": f"plugin:{p['id']}:{cid}", "title": c.get("title") or p["name"], "titles": titles, "type": c["type"],
                        "format": c.get("format", "number"), "plugin": p["name"], "plugin_id": p["id"], "logo": logo})
    return out


def answer(data_dir, pid, cid, opener=None):
    """One card's checked answer, kept for a minute: {type, format, data} or {type, problem}."""
    from . import plugins_admin
    key = (pid, cid)
    m = plugins_admin._read_kept(f"{plugins_admin.folder(data_dir, pid)}/manifest.json", {}) or {}
    cards = {(c.get("id") or str(i)): c for i, c in enumerate(m.get("cards") or [])}
    card = cards.get(cid)
    keep = max(KEEP, 60 * int((card or {}).get("refresh_minutes") or 1))  # a card may ask to be read less often (DASH-330)
    with _lock:
        hit = _cache.get(key)
    # Its own time (API 1.14): the last answer's refresh_seconds, else the manifest's, never under 10 seconds.
    own = ((hit[1].get("refresh_seconds") if hit else None) or refresh_seconds((card or {}).get("refresh_seconds")))
    if own:
        keep = own
    if hit and time.time() - hit[0] < keep:
        return hit[1]
    if not card or not m.get("containers"):
        raise LookupError("No such card")
    main = m["containers"][0]
    url = f"http://{_host(pid, main)}:{int(main.get('port') or 80)}{card['path']}"
    out = {"type": card["type"], "format": card.get("format", "number"), "asked": int(time.time())}
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Starboard"})
        with (opener or urllib.request.build_opener()).open(req, timeout=TIMEOUT) as r:  # the plug-in's own container  # nosec B310
            raw = r.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("The answer is larger than 64 KB")
        out["data"] = clean(card["type"], json.loads(raw))
    except (OSError, ValueError) as e:
        out["problem"] = f"No answer from {m.get('name', pid)}" + (f": {e}" if isinstance(e, ValueError) else "")
    every = (out.get("data") or {}).pop("refresh_seconds", None) or refresh_seconds(card.get("refresh_seconds"))
    if every:
        out["refresh_seconds"] = every  # the dashboard asks again at this time, while the page is in view
    with _lock:
        _cache[key] = (time.time(), out)
    return out


def answers(data_dir, ids, opener=None):
    """Several cards' answers in one request (API 1.14): the dashboard asks for every card due at the same time
    together. {id: answer}, each id plugin:<plug-in>:<card>; a card that is not there answers its problem."""
    out = {}
    for full in list(dict.fromkeys(ids))[:24]:
        m = re.match(r"^plugin:([a-z0-9-]{3,40}):([A-Za-z0-9_-]{1,40})$", str(full))
        if not m:
            continue
        try:
            out[full] = answer(data_dir, m.group(1), m.group(2), opener)
        except LookupError as e:
            out[full] = {"type": "", "problem": str(e)}
    return out


def action(data_dir, pid, aid, opener=None):
    """Runs one of a plug-in's buttons: a POST to its path on the plug-in's main container. {said}."""
    from . import plugins_admin
    m = plugins_admin._read(f"{plugins_admin.folder(data_dir, pid)}/manifest.json", {}) or {}
    # A button without an id is known by its place, as the listing gives it (DASH-357: it never ran before).
    act = next((a for i, a in enumerate(m.get("actions") or []) if isinstance(a, dict) and (a.get("id") or str(i)) == aid), None)
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
