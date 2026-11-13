"""A plug-in's own screen for a custom setting (DASH-149 part three, 11 November 2026): the plug-in describes a managed
list as data, and Starboard draws it in its own design system. No plug-in code reaches the page.

The plug-in's `choices` path answers GET with:
  {"type": "list", "title": text, "intro": text,
   "add": {"label": text, "hint": text, "placeholder": text} (optional),
   "items": [{"id": text, "title": text, "detail": text, "state": ok|warning|problem|off|unknown, "group": text,
              "on": true|false (optional), "address": text (optional), "actions": [test, toggle, remove, up, down],
              "choice": {"label": text, "value": text, "options": [[value, words], ...]} (optional, 12 November 2026)}],
   "bulk": [{"id": text, "label": text, "kind": text, "on": number, "total": number,
             "active": true|false (optional), "hint": text (optional), "menu": text (optional, API 1.7)}] (optional, DASH-359),
   "menus": [{"id": text, "title": text, "detail": text, "group": text, "parent": text, "active": true|false}]
            (optional, plug-in API 1.7, DASH-361)}
and POST with {"action": add|test|test_all|toggle|remove|up|down|choose|bulk, "id": text, "value": text}, answering the same shape
with "said", a sentence. "bulk" activates (value "on") or deactivates (value "off") a whole set of items at once: Starboard
draws one switch per set, grouped by its kind in the order given. A switch is active when all of its items are, or as
"active" says (a whole source that can be stopped); "hint" replaces the words "3 of 5 active" under it.
"menus" (plug-in API 1.7) splits a long list into sub menus: Starboard draws the menus without a parent as rows that open,
and each opened menu shows its own sub menus, the bulk switches and items whose "menu" names it, with a back link.
A parent comes before its sub menus, at most four levels deep; anything else is left out. Items and switches without a
known "menu" stay on the first level, so a screen without menus is drawn as before.
"readonly": true (plug-in API 1.11, DASH-402) with "layout": "folds" draws each section's table to be read only: no tick
boxes, no State column, no Activate buttons and no Active or Inactive filter, for figures such as watch statistics.
Starboard keeps only these fields, cuts every text, and calls the plug-in with its own key."""
import json
import re
import urllib.error
import urllib.request

MAX_BYTES = 2 * 1024 * 1024  # Live TV on the owner's server: 1,616 channels, about 420 KB (13 November 2026)
ACTIONS = ("add", "test", "test_all", "toggle", "remove", "up", "down", "choose", "bulk", "bulk_ids", "attach", "detach", "dismiss")
TONES = ("info", "success", "warning", "danger")
MAX_IDS = 1000
MAX_ITEMS = 4000
STATES = ("ok", "warning", "problem", "off", "unknown")


def _text(v, limit):
    return str(v or "")[:limit]


def _choice(c):
    """A small choice on a row, such as a catalogue's weight: up to 12 options, each [value, words]."""
    if not isinstance(c, dict) or not isinstance(c.get("options"), list):
        return None
    opts = [[_text(o[0], 40), _text(o[1], 40)] for o in c["options"][:12] if isinstance(o, (list, tuple)) and len(o) == 2]
    if not opts:
        return None
    value = _text(c.get("value"), 40)
    return {"label": _text(c.get("label"), 40), "value": value if any(o[0] == value for o in opts) else opts[0][0], "options": opts}


def _count(v):
    try:
        return max(0, min(int(v), 100000))
    except (TypeError, ValueError):
        return 0


MAX_MENUS = 200
MAX_DEPTH = 4


def _menus(raw):
    """Sub menus (plug-in API 1.7, DASH-361): up to 200, each after its parent, at most four levels deep."""
    out, depth = [], {}
    for m in raw[:MAX_MENUS] if isinstance(raw, list) else []:
        if not isinstance(m, dict) or not m.get("id") or not m.get("title"):
            continue
        mid, parent = _text(m["id"], 120), _text(m.get("parent"), 120)
        if mid in depth or (parent and depth.get(parent, MAX_DEPTH) >= MAX_DEPTH):
            continue  # a repeat, a parent not given first, or too deep: never a loop
        depth[mid] = depth[parent] + 1 if parent else 1
        out.append({"id": mid, "title": _text(m["title"], 80), "detail": _text(m.get("detail"), 200), "group": _text(m.get("group"), 40),
                    "parent": parent, "active": m["active"] if isinstance(m.get("active"), bool) else None})
    return out


def _in_menu(thing, known):
    """{"menu": id} when the thing names a known menu (API 1.7), else nothing: it stays on the first level."""
    menu = _text(thing.get("menu"), 120)
    return {"menu": menu} if menu and menu in known else {}


def _bulk(sets, known=frozenset()):
    """Switches for whole sets of items (DASH-359): up to 60, or 400 on a screen with menus (API 1.7), each with how
    many of its items are active."""
    out = []
    for b in sets[:400 if known else 60] if isinstance(sets, list) else []:
        if isinstance(b, dict) and b.get("id") and b.get("label"):
            total = _count(b.get("total"))
            out.append({"id": _text(b["id"], 120), "label": _text(b["label"], 60), "kind": _text(b.get("kind"), 40),
                        "on": min(_count(b.get("on")), total), "total": total,
                        "active": b["active"] if isinstance(b.get("active"), bool) else None, "hint": _text(b.get("hint"), 160),
                        **_in_menu(b, known), **({"fold": _text(b["fold"], 40)} if b.get("fold") else {})})
    return out


def _columns(raw):
    """Folding sections with a table in each (plug-in API 1.8, DASH-359, owner 13 November 2026): up to 8 columns,
    each {key, label, type}; a number column sorts as numbers."""
    out = []
    for c in raw[:8] if isinstance(raw, list) else []:
        if isinstance(c, dict) and re.fullmatch(r"[a-z][a-z0-9_]{0,30}", str(c.get("key") or "")) and c.get("label"):
            out.append({"key": c["key"], "label": _text(c["label"], 30), "type": "number" if c.get("type") == "number" else "text"})
    return out


def _filters(raw, columns):
    """Filter chips (API 1.8): up to 4, each on one column's values; chips of one filter add up, filters narrow."""
    keys = {c["key"] for c in columns}
    return [{"key": f["key"], "label": _text(f.get("label"), 30)} for f in (raw[:4] if isinstance(raw, list) else [])
            if isinstance(f, dict) and f.get("key") in keys]


def _notices(raw):
    """Notices at the top of the screen (API 1.8): up to 5, such as a list being added and what came of it.
    `progress` (0 to 100) makes Starboard ask again every few seconds until it is gone."""
    out = []
    for n in raw[:5] if isinstance(raw, list) else []:
        if isinstance(n, dict) and n.get("title"):
            prog = n.get("progress")
            out.append({"id": _text(n.get("id"), 120), "tone": n.get("tone") if n.get("tone") in TONES else "info",
                        "title": _text(n["title"], 160), "text": _text(n.get("text"), 400),
                        "progress": max(0, min(int(prog), 100)) if isinstance(prog, (int, float)) and not isinstance(prog, bool) else None,
                        "dismiss": bool(n.get("dismiss"))})
    return out


def _attach(a):
    """Something added to one item, such as a guide for a channel list (API 1.8): an address or a file."""
    if not isinstance(a, dict) or not a.get("label"):
        return None
    f = _file({"accept": a.get("accept"), "label": "x"})
    return {"label": _text(a["label"], 40), "field": _text(a.get("field"), 80) or _text(a["label"], 40), "hint": _text(a.get("hint"), 200),
            "placeholder": _text(a.get("placeholder"), 120), "value": _text(a.get("value"), 500), "accept": f["accept"] if f else ""}


def _file(f):
    """A file picker beside the add box (DASH-359): its label, hint and the file types it offers."""
    if not isinstance(f, dict):
        return None
    accept = ",".join(a for a in str(f.get("accept") or "").split(",") if re.fullmatch(r"\.[a-z0-9]{1,8}", a.strip().lower()))
    return {"label": _text(f.get("label"), 80) or "Or choose a file", "hint": _text(f.get("hint"), 200), "accept": accept}


def clean(data):
    """Only the fields Starboard draws, every text cut to size; anything else is dropped."""
    if not isinstance(data, dict) or data.get("type") != "list" or not isinstance(data.get("items"), list):
        raise ValueError("The plug-in's screen is not a list Starboard can draw")
    add = data.get("add") if isinstance(data.get("add"), dict) else None
    menus = _menus(data.get("menus"))
    known = frozenset(m["id"] for m in menus)
    columns = _columns(data.get("columns")) if data.get("layout") == "folds" else []
    items = []
    for it in data["items"][:MAX_ITEMS]:  # Live TV's channels: 546 on the owner's server (DASH-313), 1,616 by 13 November 2026
        if not isinstance(it, dict) or not it.get("id"):
            continue
        items.append({"id": _text(it["id"], 600), "title": _text(it.get("title"), 120), "detail": _text(it.get("detail"), 200),
                      "state": it.get("state") if it.get("state") in STATES else "unknown", "group": _text(it.get("group"), 40),
                      "on": bool(it.get("on", True)), "address": _text(it.get("address"), 500),
                      "actions": [a for a in it.get("actions") or [] if a in ACTIONS], "choice": _choice(it.get("choice")),
                      **_in_menu(it, known),
                      **({"cells": {c["key"]: _text((it.get("cells") or {}).get(c["key"]), 80) for c in columns}} if columns else {}),
                      **({"attach": _attach(it["attach"])} if _attach(it.get("attach")) else {})})
    out = {"type": "list", "title": _text(data.get("title"), 80), "intro": _text(data.get("intro"), 400), "items": items,
           "add": {**{k: _text(add.get(k), 120) for k in ("label", "hint", "placeholder")}, "file": _file(add.get("file"))} if add else None,
           "bulk": _bulk(data.get("bulk"), known)}
    if menus:
        out["menus"] = menus
    if columns:
        out.update(layout="folds", columns=columns, filters=_filters(data.get("filters"), columns))
        if data.get("readonly") is True:  # API 1.11 (DASH-402): figures to read, with no ticks, states or buttons
            out["readonly"] = True
    if _notices(data.get("notices")):
        out["notices"] = _notices(data.get("notices"))
    if data.get("said"):
        out["said"] = _text(data["said"], 200)
    return out


def _setting(data_dir, pid, key):
    from . import plugins_admin
    m = plugins_admin._read(f"{plugins_admin.folder(data_dir, pid)}/manifest.json", {}) or {}
    s = next((x for x in m.get("settings") or [] if x.get("key") == key and x.get("type") == "custom"), None)
    if not s or not m.get("containers"):
        raise LookupError("No such screen")
    return m, s


MAX_UPLOAD = 60 * 1024 * 1024


def upload(data_dir, pid, key, name, length, stream, item=""):
    """A file chosen beside a screen's add box (DASH-359), streamed to the plug-in's `choices` path plus /file a
    piece at a time, so neither Starboard nor the browser's request is held in memory. Returns the cleaned list."""
    import http.client
    import urllib.parse
    from . import plugin_cards, plugins_admin
    m, s = _setting(data_dir, pid, key)
    if not 0 < length <= MAX_UPLOAD:
        raise ValueError("Choose a file up to 60 MB")
    main = m["containers"][0]
    try:
        with open(f"{plugins_admin.folder(data_dir, pid)}/key", encoding="utf-8") as f:
            key_text = f.read().strip()
    except OSError:
        key_text = ""
    conn = http.client.HTTPConnection(plugin_cards._host(pid, main), int(main.get("port") or 80), timeout=120)
    try:
        to = f"&id={urllib.parse.quote(_text(item, 120))}" if item else ""  # a file for one item, such as a list's guide (API 1.8)
        conn.putrequest("POST", f"{s['choices']}/file?name={urllib.parse.quote(_text(name, 120))}{to}")
        for h, v in (("Content-Type", "application/octet-stream"), ("Content-Length", str(length)), ("Accept", "application/json"),
                     ("User-Agent", "Starboard"), ("X-Api-Key", key_text)):
            conn.putheader(h, v)
        conn.endheaders()
        left = length
        while left:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                raise ValueError("The upload stopped before the end")
            conn.send(chunk)
            left -= len(chunk)
        r = conn.getresponse()
        raw = r.read(MAX_BYTES + 1)
    except OSError:
        raise ValueError(f"Starboard could not reach {m.get('name', pid)}. Check that it is active on State") from None
    finally:
        conn.close()
    if r.status == 404:
        raise ValueError(f"{m.get('name', pid)} does not take files")
    if r.status >= 400:
        try:
            said = (json.loads(raw or b"{}") or {}).get("error")
        except ValueError:
            said = None
        raise ValueError(_text(said, 200) or f"{m.get('name', pid)} answered {r.status}")
    if len(raw) > MAX_BYTES:
        raise ValueError("The answer is too large")
    return clean(json.loads(raw))


def call(data_dir, pid, key, body=None, opener=None):
    """GET (body None) or POST one action to the plug-in's screen; returns the cleaned list."""
    from . import plugin_cards, plugins_admin
    m, s = _setting(data_dir, pid, key)
    if body is not None:
        if body.get("action") not in ACTIONS:
            raise ValueError("Not something this screen does")
        ids = body.get("ids") if body["action"] == "bulk_ids" else None
        body = {"action": body["action"], "id": _text(body.get("id"), 600), "value": _text(body.get("value"), 500),
                **({"ids": [_text(i, 600) for i in ids[:MAX_IDS] if isinstance(i, str)]} if isinstance(ids, list) else {})}
    main = m["containers"][0]
    try:
        with open(f"{plugins_admin.folder(data_dir, pid)}/key", encoding="utf-8") as f:
            key_text = f.read().strip()
    except OSError:
        key_text = ""
    req = urllib.request.Request(f"http://{plugin_cards._host(pid, main)}:{int(main.get('port') or 80)}{s['choices']}",
                                 data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET",
                                 headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Starboard",
                                          "X-Api-Key": key_text})
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=60) as r:  # the plug-in's own container  # nosec B310
            raw = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        try:
            said = (json.loads(e.read(4096) or b"{}") or {}).get("error")
        except ValueError:
            said = None
        raise ValueError(_text(said, 200) or f"{m.get('name', pid)} answered {e.code}") from None
    except OSError as e:  # in words, not the system's own message (DASH-307)
        late = isinstance(getattr(e, "reason", e), TimeoutError)
        raise ValueError(f"{m.get('name', pid)} did not answer within a minute" if late else
                         f"Starboard could not reach {m.get('name', pid)}. Check that it is active on State") from None
    if len(raw) > MAX_BYTES:
        raise ValueError("The answer is too large")
    return clean(json.loads(raw))
