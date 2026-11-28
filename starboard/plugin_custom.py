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
An item's "restore" action (plug-in API 1.15, DASH-406) is drawn as a Put back button on its row, for something the
plug-in moved aside, such as a film Library clean-up moved to the holding folder; it POSTs {"action": "restore", "id"}.
Plug-in API 1.16 (19 November 2026, owner: "changes save without refreshing the whole page", "searches open up the
slider with the catalogue", "break the channels section into smaller cards"): Starboard sends X-Starboard-Can:
partial,picker,cards on every call, and a plug-in may then answer an action with "partial": {"menus": [ids]} and only
those menus and their items, which Starboard puts in place of the ones it has; give an item a "picker" with "pick" in
its actions, a slide-out with search, filters and tick boxes, which POSTs {"action": "browse", "id", "value": words,
"filter", "start"} for each page (answered {"type": "picker", "items", "total", "more"}) and {"action": "pick", "id",
"ids"} for the ticked ones; give an item an "image" ({"src": a PNG or JPEG data address of up to 64 KB, "alt"});
and send "layout": "cards" with "hints" ({group: sentence}) to draw each menu as a card
and each group of items as a card with its sentence. An older plug-in sends none of these and is drawn as before.
Plug-in API 1.25 (28 November 2026, owner: Create your own TV channel's settings redesign): Starboard sends
X-Starboard-Can: partial,picker,cards,wizard,sentence,media,more,desktop, and a plug-in may then answer with
  {"type": "wizard", ...}   the one shared wizard (docs/WIZARD.md), drawn from steps, one question each, with Check your
                            answers at the end; POST {"action": "wizard", "answers": {step: value or [values]}};
  {"type": "sentence", ...} a setting read as one sentence with a select in each gap; POST {"action": "choose", "id": gap, "value"};
  a list with "layout": "media" (items with "media": a picture and a short preview played only when pressed, fetched from
  the plug-in's own `<choices>/media` path through Starboard), "more_switch" with items marked "more" (Show more settings),
  "preview" (a picture or a drawing of styles, never video) and "desktop_only": true (a plain notice on narrow screens).
An older plug-in sends none of these and is drawn as before.
Starboard keeps only these fields, cuts every text, and calls the plug-in with its own key."""
import json
import re
import urllib.error
import urllib.request

MAX_BYTES = 2 * 1024 * 1024  # Live TV on the owner's server: 1,616 channels, about 420 KB (13 November 2026)
ACTIONS = ("add", "test", "test_all", "toggle", "remove", "up", "down", "choose", "bulk", "bulk_ids", "attach", "detach", "dismiss",
           "restore", "browse", "pick", "wizard")  # restore: API 1.15 (DASH-406), drawn as Put back; browse and pick: API 1.16, the picker; wizard: API 1.25
CAN = "partial,picker,cards,wizard,sentence,media,more,desktop"  # what this Starboard draws (API 1.16 and 1.25), sent to the plug-in in X-Starboard-Can
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
            "placeholder": _text(a.get("placeholder"), 120), "value": _text(a.get("value"), 500), "accept": f["accept"] if f else "",
            # API 1.16: the words for detach in the row's More menu, such as "Remove the logo", in place of "Remove guide"
            **({"detach_label": _text(a["detach_label"], 40)} if a.get("detach_label") else {})}


def _link(k):
    """A link on one item (API 1.12, DASH-410), such as a search for the title on another site. Starboard draws it as
    a link that opens in a new tab; only http and https addresses, so a script address can never be one."""
    if not isinstance(k, dict) or not isinstance(k.get("url"), str) or not re.match(r"^https?://[^\s<>\"]{1,490}$", k["url"]):
        return None
    return {"url": k["url"][:500], "label": _text(k.get("label"), 80) or "Open"}


def _picker(k):
    """A slide-out to choose several things (API 1.16), such as series and films from a library: its button's label, the
    slide-out's title, the search box's label, up to 8 filters ([value, words]) and the words on its Add button."""
    if not isinstance(k, dict) or not k.get("label"):
        return None
    filters = [[_text(f[0], 40), _text(f[1], 40)] for f in (k.get("filters") or [])[:8] if isinstance(f, (list, tuple)) and len(f) == 2 and f[0]]
    return {"label": _text(k["label"], 40), "title": _text(k.get("title"), 80) or _text(k["label"], 40), "search": _text(k.get("search"), 60) or "Search",
            "filters": filters, "submit": _text(k.get("submit"), 40) or "Add the ticked ones"}


def _image(k):
    """A small picture on one item (API 1.16), such as a channel's logo once uploaded: a PNG or JPEG as a data address
    of up to 64 KB, with its text alternative. Data only, so the page's policy never needs to reach the plug-in."""
    if not isinstance(k, dict) or not isinstance(k.get("src"), str) or not k.get("alt"):
        return None
    if len(k["src"]) > 64 * 1024 or not re.fullmatch(r"data:image/(png|jpeg);base64,[A-Za-z0-9+/]+={0,2}", k["src"]):
        return None
    return {"src": k["src"], "alt": _text(k["alt"], 120)}


def clean_picker(data):
    """A page of a picker (API 1.16): up to 200 rows, each {id, title, detail, on}; on is something already added."""
    if not isinstance(data, dict) or data.get("type") != "picker" or not isinstance(data.get("items"), list):
        raise ValueError("The plug-in's answer is not a list Starboard can show")
    items = [{"id": _text(it["id"], 600), "title": _text(it.get("title"), 120), "detail": _text(it.get("detail"), 200), "on": it.get("on") is True}
             for it in data["items"][:200] if isinstance(it, dict) and it.get("id")]
    return {"type": "picker", "items": items, "total": _count(data.get("total")), "start": _count(data.get("start")),
            "more": data.get("more") is True, "filter": _text(data.get("filter"), 40)}


def _file(f):
    """A file picker beside the add box (DASH-359): its label, hint and the file types it offers."""
    if not isinstance(f, dict):
        return None
    accept = ",".join(a for a in str(f.get("accept") or "").split(",") if re.fullmatch(r"\.[a-z0-9]{1,8}", a.strip().lower()))
    return {"label": _text(f.get("label"), 80) or "Or choose a file", "hint": _text(f.get("hint"), 200), "accept": accept}


def clean(data):
    """Only the fields Starboard draws, every text cut to size; anything else is dropped."""
    if isinstance(data, dict) and data.get("type") == "wizard":  # API 1.25
        return clean_wizard(data)
    if isinstance(data, dict) and data.get("type") == "sentence":  # API 1.25
        return clean_sentence(data)
    if not isinstance(data, dict) or data.get("type") != "list" or not isinstance(data.get("items"), list):
        raise ValueError("The plug-in's page is not a list Starboard can draw")
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
                      # API 1.12 (DASH-410): the plug-in's own words for the state, such as "Added", shown in its colour
                      **({"state_label": _text(it["state_label"], 30)} if _text(it.get("state_label"), 30) else {}),
                      "actions": [a for a in it.get("actions") or [] if a in ACTIONS], "choice": _choice(it.get("choice")),
                      **_in_menu(it, known),
                      **({"cells": {c["key"]: _text((it.get("cells") or {}).get(c["key"]), 80) for c in columns}} if columns else {}),
                      **({"attach": _attach(it["attach"])} if _attach(it.get("attach")) else {}),
                      **({"link": _link(it["link"])} if _link(it.get("link")) else {}),
                      **({"image": _image(it["image"])} if _image(it.get("image")) else {}),
                      **({"picker": _picker(it["picker"])} if _picker(it.get("picker")) and "pick" in (it.get("actions") or []) else {}),
                      # API 1.25: a media card's picture and short preview, and a row shown only when Show more settings is on
                      **({"media": _media(it["media"])} if _media(it.get("media")) else {}), **({"more": True} if it.get("more") is True else {})})
    out = {"type": "list", "title": _text(data.get("title"), 80), "intro": _text(data.get("intro"), 400), "items": items,
           "add": {**{k: _text(add.get(k), 120) for k in ("label", "hint", "placeholder")}, "file": _file(add.get("file")),
                   # API 1.12 (DASH-410): only the file picker, for a plug-in that takes files and never addresses
                   **({"file_only": True} if add.get("file_only") is True and _file(add.get("file")) else {})} if add else None,
           "bulk": _bulk(data.get("bulk"), known)}
    if menus:
        out["menus"] = menus
    # An answer for some menus only (API 1.16): Starboard puts these menus and their items in place of its own.
    part = data.get("partial")
    if isinstance(part, dict) and isinstance(part.get("menus"), list):
        out["partial"] = {"menus": [_text(m, 120) for m in part["menus"][:MAX_MENUS] if m]}
    if data.get("layout") == "cards":  # API 1.16: each menu and each group of items on a card of its own
        out["layout"] = "cards"
    if data.get("layout") == "media":  # API 1.25: items with a media object drawn as media cards in option cards
        out["layout"] = "media"
    if isinstance(data.get("more_switch"), dict):  # API 1.25: Show more settings, for the items marked "more"
        out["more_switch"] = {"label": _text(data["more_switch"].get("label"), 60) or "Show more settings", "hint": _text(data["more_switch"].get("hint"), 160)}
    if _preview(data.get("preview")):  # API 1.25
        out["preview"] = _preview(data["preview"])
    if data.get("desktop_only") is True:  # API 1.25
        out["desktop_only"] = True
    if isinstance(data.get("hints"), dict):
        out["hints"] = {_text(k, 40): _text(v, 200) for k, v in list(data["hints"].items())[:40] if k and v}
    if columns:
        out.update(layout="folds", columns=columns, filters=_filters(data.get("filters"), columns))
        if data.get("readonly") is True:  # API 1.11 (DASH-402): figures to read, with no ticks, states or buttons
            out["readonly"] = True
    if _notices(data.get("notices")):
        out["notices"] = _notices(data.get("notices"))
    if data.get("said"):
        out["said"] = _text(data["said"], 200)
    return out


# ---- Plug-in API 1.25 (28 November 2026): the shared wizard, a sentence, media cards, more rows, a preview, a desktop notice ----
STEP_KINDS = ("choice", "multi", "media", "number", "text", "select")
MEDIA_TYPES = ("image/png", "image/jpeg", "image/webp", "video/mp4", "video/webm", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/x-wav")
MAX_MEDIA = 8 * 1024 * 1024  # a short preview, never a whole film
MAX_STEPS = 30
MAX_OPTIONS = 200
PREVIEW_KINDS = ("title", "clip", "music", "other")
ID = re.compile(r"[a-z][a-z0-9_-]{0,40}")


def _preview(p):
    """A preview (API 1.25): a picture or a drawing made of styles, never video: up to 3 lines of text, a corner label, a strip of
    up to 12 parts with their seconds, a caption said once after a change and a total in words."""
    if not isinstance(p, dict):
        return None
    strip = [{"label": _text(x.get("label"), 30), "seconds": max(1, min(_count(x.get("seconds")), 600)), "kind": x.get("kind") if x.get("kind") in PREVIEW_KINDS else "other"}
             for x in (p.get("strip") or [])[:12] if isinstance(x, dict) and x.get("label")]
    out = {"title": _text(p.get("title"), 60), "lines": [_text(t, 80) for t in (p.get("lines") or [])[:3] if t], "corner": _text(p.get("corner"), 30),
           "strip": strip, "caption": _text(p.get("caption"), 200), "total": _text(p.get("total"), 60)}
    if _image(p.get("image")):
        out["image"] = _image(p["image"])
    return out if any(out.get(k) for k in ("lines", "corner", "strip", "caption", "image", "title")) else None


def _media(m):
    """A media card's picture and preview (API 1.25): `thumb` is a small PNG or JPEG data address (up to 64 KB), or `thumb_path`
    true to fetch it, once, through Starboard from the plug-in's own media path; `preview` true when a short clip is there to
    play, only when pressed."""
    if not isinstance(m, dict):
        return None
    out = {"kind": "audio" if m.get("kind") == "audio" else "video", "length": _text(m.get("length"), 10), "preview": m.get("preview") is True,
           "thumb_path": m.get("thumb_path") is True and not _image(m.get("thumb"))}
    if _image(m.get("thumb")):
        out["thumb"] = _image(m["thumb"])
    return out


def _step_option(o, kind):
    if not isinstance(o, dict) or o.get("id") in (None, ""):
        return None
    out = {"id": _text(o["id"], 120), "label": _text(o.get("label"), 120), "hint": _text(o.get("hint"), 200), "current": o.get("current") is True,
           "recommended": o.get("recommended") is True, "checked": o.get("checked") is True}
    if _preview(o.get("preview")):
        out["preview"] = _preview(o["preview"])
    if kind == "media" and _media(o.get("media")):
        out["media"] = _media(o["media"])
    return out


def _unique(ids, one):
    return one not in ids and not ids.add(one)


def clean_wizard(data):
    """The one shared wizard drawn from a plug-in's steps (API 1.25): up to 30 steps, each a question with up to 200 options, an
    optional preview on each option, and `mode: "again"` for a set-up run a second time (options marked `current`)."""
    steps, seen = [], set()
    for st in (data.get("steps") or [])[:MAX_STEPS] if isinstance(data.get("steps"), list) else []:
        if not isinstance(st, dict) or not ID.fullmatch(str(st.get("id") or "")) or not _unique(seen, st["id"]):
            continue
        kind = st.get("kind") if st.get("kind") in STEP_KINDS else "choice"
        opts = [x for x in (_step_option(o, kind) for o in (st.get("options") or [])[:MAX_OPTIONS] if isinstance(st.get("options"), list)) if x]
        step = {"id": st["id"], "title": _text(st.get("title"), 40) or _text(st.get("question"), 40), "question": _text(st.get("question"), 160),
                "hint": _text(st.get("hint"), 300), "kind": kind, "optional": st.get("optional") is True, "required": st.get("required") is True,
                "error": _text(st.get("error"), 160), "options": opts, "value": _text(st.get("value"), 500), "label": _text(st.get("label"), 60),
                "unit": _text(st.get("unit"), 20)}
        if kind in ("choice", "select", "media", "multi") and not opts:
            continue
        steps.append(step)
    if not steps:
        raise ValueError("The plug-in's wizard has no steps Starboard can draw")
    out = {"type": "wizard", "title": _text(data.get("title"), 80), "intro": _text(data.get("intro"), 400),
           "mode": "again" if data.get("mode") == "again" else "new", "mode_label": _text(data.get("mode_label"), 80),
           "finish": _text(data.get("finish"), 40) or "Finish", "review": _text(data.get("review"), 40), "steps": steps,
           "preview": {"title": _text((data.get("preview") or {}).get("title"), 60) or "Preview"} if isinstance(data.get("preview"), dict) else None}
    return _common(out, data)


def _sentence_parts(raw):
    parts = []
    for x in raw[:30] if isinstance(raw, list) else []:
        if isinstance(x, str):
            parts.append({"text": x[:120]})
        elif isinstance(x, dict) and x.get("text") is not None and not x.get("options"):
            parts.append({"text": _text(x["text"], 120)})
        elif isinstance(x, dict) and ID.fullmatch(str(x.get("id") or "")) and isinstance(x.get("options"), list):
            opts = [[_text(o[0], 120), _text(o[1], 60)] for o in x["options"][:12] if isinstance(o, (list, tuple)) and len(o) == 2 and o[0] != ""]
            if opts:
                value = _text(x.get("value"), 120)
                parts.append({"id": x["id"], "label": _text(x.get("label"), 40) or x["id"], "options": opts,
                              "value": value if any(o[0] == value for o in opts) else opts[0][0]})
    return parts


def clean_sentence(data):
    """A setting read as one sentence with a select in each gap (API 1.25): words and up to 12 gaps."""
    parts = _sentence_parts(data.get("parts"))
    if not any("id" in x for x in parts):
        raise ValueError("The plug-in's sentence has no gaps Starboard can draw")
    return _common({"type": "sentence", "title": _text(data.get("title"), 80), "intro": _text(data.get("intro"), 400), "parts": parts}, data)


def _common(out, data):
    """What every page type may carry (API 1.25): a preview, notices, a sentence said, and the desktop notice."""
    if _preview(data.get("preview")) and out.get("preview") is None:
        out["preview"] = _preview(data["preview"])
    if _notices(data.get("notices")):
        out["notices"] = _notices(data["notices"])
    if data.get("said"):
        out["said"] = _text(data["said"], 200)
    if data.get("desktop_only") is True:
        out["desktop_only"] = True
    return out


def clean_answers(raw):
    """The answers a wizard sends (API 1.25): up to 40 steps, each a text or up to 200 texts."""
    out = {}
    for k, v in list(raw.items())[:40] if isinstance(raw, dict) else []:
        if ID.fullmatch(str(k)):
            out[k] = [_text(x, 600) for x in v[:200] if isinstance(x, str)] if isinstance(v, list) else _text(v, 600)
    return out


def media(data_dir, pid, key, query, opener=None):
    """A picture or short preview for a media card or a wizard option (API 1.25), fetched from the plug-in's own `choices` path
    plus /media with its key: only a picture, a short video or a sound (up to 8 MB), whatever else it sends is refused.
    `query` may hold step, id and kind (thumb or preview). Returns (content type, bytes)."""
    import urllib.parse
    from . import plugin_cards, plugins_admin
    m, s = _setting(data_dir, pid, key)
    main = m["containers"][0]
    try:
        with open(f"{plugins_admin.folder(data_dir, pid)}/key", encoding="utf-8") as f:
            key_text = f.read().strip()
    except OSError:
        key_text = ""
    q = {k: _text(query.get(k), 600) for k in ("step", "id") if query.get(k)}
    q["kind"] = "thumb" if query.get("kind") == "thumb" else "preview"
    req = urllib.request.Request(f"http://{plugin_cards._host(pid, main)}:{int(main.get('port') or 80)}{s['choices']}/media?{urllib.parse.urlencode(q)}",
                                 headers={"Accept": "*/*", "User-Agent": "Starboard", "X-Api-Key": key_text, "X-Starboard-Can": CAN})
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=60) as r:  # the plug-in's own container  # nosec B310
            raw = r.read(MAX_MEDIA + 1)
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    except urllib.error.HTTPError as e:
        raise ValueError(f"{m.get('name', pid)} answered {e.code}") from None
    except OSError:
        raise ValueError(f"Starboard could not reach {m.get('name', pid)}. Check that it is active on State") from None
    if len(raw) > MAX_MEDIA:
        raise ValueError("That file is too large to preview")
    if ctype not in MEDIA_TYPES:
        raise ValueError("That is not a picture, a short video or a sound")
    return ctype, raw


def _setting(data_dir, pid, key):
    from . import plugins_admin
    m = plugins_admin._read(f"{plugins_admin.folder(data_dir, pid)}/manifest.json", {}) or {}
    s = next((x for x in m.get("settings") or [] if x.get("key") == key and x.get("type") == "custom"), None)
    if not s or not m.get("containers"):
        raise LookupError("No such page")
    return m, s


# A file streamed to a plug-in (DASH-359): up to 100 MB from 0.24.1 (owner, 19 November 2026: a TV channel holding
# slide of up to 90 MB). Each plug-in still refuses what is too big for it.
MAX_UPLOAD = 100 * 1024 * 1024
MAX_UPLOAD_WORDS = "Choose a file up to 100 MB"


def upload(data_dir, pid, key, name, length, stream, item=""):
    """A file chosen beside a screen's add box (DASH-359), streamed to the plug-in's `choices` path plus /file a
    piece at a time, so neither Starboard nor the browser's request is held in memory. Returns the cleaned list."""
    import http.client
    import urllib.parse
    from . import plugin_cards, plugins_admin
    m, s = _setting(data_dir, pid, key)
    if not 0 < length <= MAX_UPLOAD:
        raise ValueError(MAX_UPLOAD_WORDS)
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
                     ("User-Agent", "Starboard"), ("X-Api-Key", key_text), ("X-Starboard-Can", CAN)):
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
            raise ValueError("Not something this page does")
        ids = body.get("ids") if body["action"] in ("bulk_ids", "pick") else None
        browse = {"filter": _text(body.get("filter"), 40), "start": _count(body.get("start"))} if body["action"] == "browse" else {}
        body = {"action": body["action"], "id": _text(body.get("id"), 600), "value": _text(body.get("value"), 500), **browse,
                **({"ids": [_text(i, 600) for i in ids[:MAX_IDS] if isinstance(i, str)]} if isinstance(ids, list) else {}),
                **({"answers": clean_answers(body.get("answers"))} if body["action"] == "wizard" else {})}  # API 1.25: a wizard's answers
    main = m["containers"][0]
    try:
        with open(f"{plugins_admin.folder(data_dir, pid)}/key", encoding="utf-8") as f:
            key_text = f.read().strip()
    except OSError:
        key_text = ""
    req = urllib.request.Request(f"http://{plugin_cards._host(pid, main)}:{int(main.get('port') or 80)}{s['choices']}",
                                 data=json.dumps(body).encode() if body is not None else None, method="POST" if body is not None else "GET",
                                 headers={"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Starboard",
                                          "X-Api-Key": key_text, "X-Starboard-Can": CAN})
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
    got = json.loads(raw)
    return clean_picker(got) if body is not None and body.get("action") == "browse" else clean(got)
