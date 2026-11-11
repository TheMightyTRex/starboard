"""A plug-in's own screen for a custom setting (DASH-149 part three, 11 November 2026): the plug-in describes a managed
list as data, and Starboard draws it in its own design system. No plug-in code reaches the page.

The plug-in's `choices` path answers GET with:
  {"type": "list", "title": text, "intro": text,
   "add": {"label": text, "hint": text, "placeholder": text} (optional),
   "items": [{"id": text, "title": text, "detail": text, "state": ok|warning|problem|off|unknown, "group": text,
              "on": true|false (optional), "address": text (optional), "actions": [test, toggle, remove, up, down]}]}
and POST with {"action": add|test|test_all|toggle|remove|up|down, "id": text, "value": text}, answering the same shape
with "said", a sentence. Starboard keeps only these fields, cuts every text, and calls the plug-in with its own key."""
import json
import urllib.error
import urllib.request

MAX_BYTES = 256 * 1024
ACTIONS = ("add", "test", "test_all", "toggle", "remove", "up", "down")
STATES = ("ok", "warning", "problem", "off", "unknown")


def _text(v, limit):
    return str(v or "")[:limit]


def clean(data):
    """Only the fields Starboard draws, every text cut to size; anything else is dropped."""
    if not isinstance(data, dict) or data.get("type") != "list" or not isinstance(data.get("items"), list):
        raise ValueError("The plug-in's screen is not a list Starboard can draw")
    add = data.get("add") if isinstance(data.get("add"), dict) else None
    items = []
    for it in data["items"][:300]:
        if not isinstance(it, dict) or not it.get("id"):
            continue
        items.append({"id": _text(it["id"], 600), "title": _text(it.get("title"), 120), "detail": _text(it.get("detail"), 200),
                      "state": it.get("state") if it.get("state") in STATES else "unknown", "group": _text(it.get("group"), 40),
                      "on": bool(it.get("on", True)), "address": _text(it.get("address"), 500),
                      "actions": [a for a in it.get("actions") or [] if a in ACTIONS]})
    out = {"type": "list", "title": _text(data.get("title"), 80), "intro": _text(data.get("intro"), 400), "items": items,
           "add": {k: _text(add.get(k), 120) for k in ("label", "hint", "placeholder")} if add else None}
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
    except OSError as e:
        raise ValueError(f"No answer from {m.get('name', pid)}: {e}") from None
    if len(raw) > MAX_BYTES:
        raise ValueError("The answer is too large")
    return clean(json.loads(raw))
