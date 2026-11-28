"""The example plug-in for plug-in API 1.26 (28 November 2026): "Page parts example", answered here, in the example server's
process, with made-up data. It shows every part a plug-in page may use: the shared wizard (new and Run again), a sentence
with selects, media cards with a preview that plays only when pressed, rows behind Show more settings, a preview pane and
the desktop notice. The same answers are the model for a real plug-in (docs/help/developers/plugin-api-reference.md,
"Pages made of the shared parts"). Nothing is fetched and no container starts."""
import base64
import math
import struct

PREV = {
    "quiet": {"lines": ["Next: Comedy hour"], "corner": "Example TV", "strip": [{"label": "Title clip", "seconds": 5, "kind": "title"}],
              "caption": "Quiet: a short title clip, then the next programme.", "total": "About 10 seconds"},
    "classic": {"lines": ["Example TV", "Next: Comedy hour"], "corner": "Example TV",
                "strip": [{"label": "Title clip", "seconds": 6, "kind": "title"}, {"label": "Clip", "seconds": 30, "kind": "clip"}, {"label": "Music", "seconds": 24, "kind": "music"}],
                "caption": "Classic TV: a title clip, a clip with quiet music, then the next programme.", "total": "About 1 minute"},
    "busy": {"lines": ["Example TV", "Next: Comedy hour"], "corner": "Example TV",
             "strip": [{"label": "Title clip", "seconds": 6, "kind": "title"}, {"label": "Clip", "seconds": 30, "kind": "clip"}, {"label": "Clip", "seconds": 30, "kind": "clip"}, {"label": "Music", "seconds": 40, "kind": "music"}],
             "caption": "Busy: a title clip, two clips and music, then the next programme.", "total": "About 2 minutes"}}
STATE = {"style": "quiet", "often": "2", "clips": ["c1"], "channels": "all", "ran": False, "gaps": {"idents": "one", "clips": "2", "music": "quiet"}, "tick": {"c1": True, "c2": False, "c3": False}}
CLIPS = [("c1", "Station title", "Short title clip", "0:01", "audio"), ("c2", "Corner clip", "Clip", "0:01", "audio"), ("c3", "Evening music", "Music", "0:01", "audio")]


def _tone():
    rate = 8000
    data = bytes(int(128 + 60 * math.sin(2 * math.pi * 440 * i / rate) * (1 - i / rate)) for i in range(rate))
    return b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate, 1, 8) + b"data" + struct.pack("<I", len(data)) + data


def _frame(color):
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 90'><rect width='160' height='90' fill='{color}'/><circle cx='80' cy='45' r='18' fill='white' opacity='.8'/></svg>"
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def wizard():
    again = STATE["ran"]
    cur = lambda key, val: again and STATE[key] == val  # noqa: E731
    return {"type": "wizard", "title": "What plays between programmes", "mode": "again" if again else "new", "mode_label": "Run again for the Comedy channel" if again else "",
            "finish": "Save the changes" if again else "Start the breaks", "preview": {"title": "What a break plays like"},
            "steps": [
                {"id": "style", "title": "Style", "question": "What should play between programmes?", "hint": "Pick the style that fits. You can change it later.",
                 "options": [{"id": k, "label": n, "hint": h, "current": cur("style", k), "recommended": k == "classic", "checked": STATE["style"] == k, "preview": PREV[k]}
                             for k, n, h in (("quiet", "Quiet", "A short title clip and straight on."), ("classic", "Classic TV", "A title clip, a clip and music."), ("busy", "Busy", "Two clips and music between programmes."))]},
                {"id": "often", "title": "Things in a break", "question": "How many things play in each break?", "hint": "Each break picks this many from the ones you chose.",
                 "options": [{"id": k, "label": n, "current": cur("often", k), "recommended": k == "2", "checked": STATE["often"] == k} for k, n in (("1", "One thing"), ("2", "Two things"), ("3", "Three things"))]},
                {"id": "clips", "title": "Clips", "question": "Which clips should play?", "kind": "media", "optional": True,
                 "hint": "Tick the ones you want. Play preview plays a few seconds, and only when you press it.",
                 "options": [{"id": i, "label": n, "hint": h, "checked": i in STATE["clips"], "current": again and i in STATE["clips"],
                              "media": {"kind": k, "length": ln, "preview": True, "thumb_path": True}} for i, n, h, ln, k in CLIPS]},
                {"id": "channels", "title": "Channels", "question": "Which channels use this?", "optional": True, "hint": "A channel can have its own later.",
                 "options": [{"id": "all", "label": "Every channel", "hint": "Comedy, Drama and Films all use it.", "current": cur("channels", "all"), "recommended": True, "checked": STATE["channels"] == "all"},
                             {"id": "comedy", "label": "Comedy only", "hint": "The other channels keep their own.", "current": cur("channels", "comedy"), "checked": STATE["channels"] == "comedy"}]}]}


def sentence():
    g = STATE["gaps"]
    return {"type": "sentence", "title": "What plays between programmes", "intro": "Change a word in the sentence. It is saved at once.",
            "preview": {"title": "What a break plays like", **PREV["classic"]},
            "parts": ["Between programmes, play ", {"id": "idents", "label": "Short title clips", "value": g["idents"], "options": [["one", "a short title clip"], ["none", "no title clip"]]},
                      ", then ", {"id": "clips", "label": "Clips", "value": g["clips"], "options": [["1", "1 clip"], ["2", "2 clips"], ["3", "3 clips"]]},
                      ", with ", {"id": "music", "label": "Music", "value": g["music"], "options": [["quiet", "quiet music"], ["none", "no music"]]}, ", on every channel."]}


def library():
    items = [{"id": i, "title": n, "detail": h, "on": STATE["tick"][i], "actions": ["toggle"], "media": {"kind": k, "length": ln, "preview": True, "thumb_path": True}} for i, n, h, ln, k in CLIPS]
    items += [{"id": "fit", "title": "How a clip fills the screen", "detail": "Fit, so nothing is cut off", "more": True, "actions": []},
              {"id": "inside", "title": "Where breaks go inside a programme", "detail": "Only for long programmes", "more": True, "actions": []}]
    return {"type": "list", "title": "Clips and music", "intro": "Tick the ones the channels may use.", "layout": "media", "desktop_only": True,
            "more_switch": {"label": "Show more settings", "hint": "Fit and breaks inside a programme"}, "items": items}


def call(key, body=None):
    if body is not None:
        act = body.get("action")
        if act == "wizard":
            a = body.get("answers") or {}
            STATE["style"], STATE["often"] = a.get("style", STATE["style"]), a.get("often", STATE["often"])
            STATE["clips"] = a.get("clips") if isinstance(a.get("clips"), list) else STATE["clips"]
            STATE["channels"] = a.get("channels", STATE["channels"])
            STATE["ran"] = True
            return {**wizard(), "said": "Saved the breaks. This is example data, so nothing changed."}
        if act == "choose" and key == "sentence":
            STATE["gaps"][body.get("id")] = body.get("value")
            return {**sentence(), "said": "Saved"}
        if act == "toggle":
            STATE["tick"][body.get("id")] = not STATE["tick"].get(body.get("id"), False)
            return {**library(), "said": "Saved"}
    return {"setup": wizard, "sentence": sentence, "library": library}[key]()


def media(query):
    if query.get("kind") == "thumb":
        colour = {"c1": "#2a78d6", "c2": "#c1531f", "c3": "#2f7d4a"}.get(query.get("id"), "#666")
        return "image/svg+xml", _frame(colour).split(",", 1)[1] and base64.b64decode(_frame(colour).split(",", 1)[1])
    return "audio/wav", _tone()
