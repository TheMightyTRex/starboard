"""A plug-in's own screen for a custom setting (DASH-149 part three, 11 November 2026): the plug-in describes a managed
list as data, and Starboard draws it in its own design system. No plug-in code reaches the page.

The plug-in's `choices` path answers GET with:
  {"type": "list", "title": text, "intro": text,
   "add": {"label": text, "hint": text, "placeholder": text} (optional),
   "items": [{"id": text, "title": text, "detail": text, "state": ok|warning|problem|off|unknown, "group": text,
              "on": true|false (optional), "address": text (optional), "actions": [test, toggle, remove, up, down],
              "choice": {"label": text, "value": text, "options": [[value, words], ...]} (optional, 12 November 2026)}],
   "bulk": [{"id": text, "label": text, "kind": text, "on": number, "total": number,
             "active": true|false (optional), "hint": text (optional)}] (optional, DASH-359)}
and POST with {"action": add|test|test_all|toggle|remove|up|down|choose|bulk, "id": text, "value": text}, answering the same shape
with "said", a sentence. "bulk" activates (value "on") or deactivates (value "off") a whole set of items at once: Starboard
draws one switch per set, grouped by its kind in the order given. A switch is active when all of its items are, or as
"active" says (a whole source that can be stopped); "hint" replaces the words "3 of 5 active" under it.
Starboard keeps only these fields, cuts every text, and calls the plug-in with its own key."""
import json
import re
import urllib.error
import urllib.request

MAX_BYTES = 512 * 1024
ACTIONS = ("add", "test", "test_all", "toggle", "remove", "up", "down", "choose", "bulk")
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


def _bulk(sets):
    """Switches for whole sets of items (DASH-359): up to 60, each with how many of its items are active."""
    out = []
    for b in sets[:60] if isinstance(sets, list) else []:
        if isinstance(b, dict) and b.get("id") and b.get("label"):
            total = _count(b.get("total"))
            out.append({"id": _text(b["id"], 120), "label": _text(b["label"], 60), "kind": _text(b.get("kind"), 40),
                        "on": min(_count(b.get("on")), total), "total": total,
                        "active": b["active"] if isinstance(b.get("active"), bool) else None, "hint": _text(b.get("hint"), 160)})
    return out


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
    items = []
    for it in data["items"][:1000]:  # Live TV's channels (DASH-313): 546 found on the owner's server
        if not isinstance(it, dict) or not it.get("id"):
            continue
        items.append({"id": _text(it["id"], 600), "title": _text(it.get("title"), 120), "detail": _text(it.get("detail"), 200),
                      "state": it.get("state") if it.get("state") in STATES else "unknown", "group": _text(it.get("group"), 40),
                      "on": bool(it.get("on", True)), "address": _text(it.get("address"), 500),
                      "actions": [a for a in it.get("actions") or [] if a in ACTIONS], "choice": _choice(it.get("choice"))})
    out = {"type": "list", "title": _text(data.get("title"), 80), "intro": _text(data.get("intro"), 400), "items": items,
           "add": {**{k: _text(add.get(k), 120) for k in ("label", "hint", "placeholder")}, "file": _file(add.get("file"))} if add else None,
           "bulk": _bulk(data.get("bulk"))}
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


def upload(data_dir, pid, key, name, length, stream):
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
        conn.putrequest("POST", f"{s['choices']}/file?name={urllib.parse.quote(_text(name, 120))}")
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
        body = {"action": body["action"], "id": _text(body.get("id"), 600), "value": _text(body.get("value"), 500)}
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
