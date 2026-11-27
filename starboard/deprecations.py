"""Features of the public API that are going (DASH-603): the list in deprecations.json, empty until something is deprecated.

A route in the list answers as before but every answer carries `Deprecation` (RFC 9745, since when), `Sunset` (RFC 8594, the
earliest day it may stop) and a `Link` to what replaces it. Once an entry is marked `removed`, the route answers 410 gone with a
Link to the replacement. `GET /api/v1/` lists every entry, so an outside tool can warn its own owner. Nothing runs at rest: the
file is read once, the first time a request is checked, and an empty list costs one empty loop.

A route entry: {"method": "GET", "path": "/api/v1/old", "deprecated": "2027-01-15", "sunset": "2028-01-15",
                "replacement": "Use /api/v1/new", "link": "https://.../api-changelog.md#...", "removed": false}
`path` is a regular expression matched against the whole path. Removing a route needs the notice in the compatibility policy.
A manifest entry names a part of a plug-in's manifest instead of a route: {"manifest": "permission:jellyfin:key", "deprecated": ...,
"sunset": ..., "replacement": ...}. The part is `field:`, `permission:`, `card:`, `setting:`, `event:` or `container:` and a name.

Who still uses it (DASH-603): each call to a deprecated route is counted for the key that made it (calls and the last day), in memory,
and saved to `api-retiring.json` in the data folder at most once an hour and only when something was counted. Plug-ins that use a
deprecated manifest part are found from their manifests when asked. It never leaves this computer.
"""
import datetime as dt
import email.utils
import json
import os
import re
import threading
import time

MANIFEST_KINDS = ("field", "permission", "card", "setting", "event", "container")
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deprecations.json")
_items = None


def _day(text):
    return dt.datetime.strptime(str(text), "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)


def items():
    """The valid entries; a broken one is left out, never a reason for a request to fail."""
    global _items
    if _items is None:
        try:
            with open(PATH, encoding="utf-8") as f:
                raw = json.load(f).get("items") or []
        except (OSError, ValueError):
            raw = []
        out = []
        for e in raw if isinstance(raw, list) else []:
            try:
                if not isinstance(e, dict):
                    continue
                _day(e["deprecated"])
                _day(e["sunset"])
                common = {"deprecated": e["deprecated"], "sunset": e["sunset"], "replacement": str(e.get("replacement") or "")[:200],
                          "link": str(e.get("link") or "")[:300], "removed": bool(e.get("removed"))}
                if "manifest" in e:
                    kind, _, name = str(e["manifest"]).partition(":")
                    if kind not in MANIFEST_KINDS or not name:
                        continue
                    out.append({"manifest": f"{kind}:{name}", **common})
                    continue
                if e["method"] not in ("GET", "POST", "PUT", "DELETE", "*"):
                    continue
                re.compile(e["path"])
                out.append({"method": e["method"], "path": e["path"], **common})
            except (KeyError, ValueError, re.error):
                continue
        _items = out
    return _items


def entry(method, path):
    for e in items():
        if "path" in e and e["method"] in (method, "*") and re.fullmatch(e["path"], path):
            return e
    return None


def headers(e):
    """Deprecation, Sunset and Link for an entry."""
    out = {"Deprecation": f"@{int(_day(e['deprecated']).timestamp())}",
           "Sunset": email.utils.format_datetime(_day(e["sunset"]), usegmt=True)}
    if e["link"].startswith("https://"):
        out["Link"] = f'<{e["link"]}>; rel="deprecation"'
    return out


def public():
    """What GET /api/v1/ lists: {method, path, deprecated, sunset, replacement, removed} for each entry."""
    return [{k: e[k] for k in ("method", "path", "manifest", "deprecated", "sunset", "replacement", "removed") if k in e} for e in items()]


# Who still uses it ------------------------------------------------------------------------------------------------------------------
_lock = threading.Lock()
_used = {}  # (entry's route, key id) -> [calls, last day]
_saved_at = 0.0
_dirty = False
SAVE_EVERY = 3600
FILE = "api-retiring.json"


def note_use(data_dir, key_id, e, now=None):
    """Counts one call to a deprecated route for the key that made it; saves at most once an hour."""
    global _saved_at, _dirty
    now = now or time.time()
    day = dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime("%Y-%m-%d")
    with _lock:
        row = _used.setdefault((f"{e['method']} {e['path']}", str(key_id)), [0, day])
        row[0] += 1
        row[1] = day
        _dirty = True
        if now - _saved_at < SAVE_EVERY:
            return
        _saved_at = now
        _dirty = False
        data = {f"{r}|{k}": v for (r, k), v in _used.items()}
    try:
        with open(os.path.join(data_dir, FILE), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def routes_in_use(data_dir):
    """[{route, key, calls, last}] from this run and the saved file, the most recent day for each key and route."""
    seen = {}
    try:
        with open(os.path.join(data_dir, FILE), encoding="utf-8") as f:
            for k, v in (json.load(f) or {}).items():
                seen[k] = list(v)
    except (OSError, ValueError, AttributeError):
        pass
    with _lock:
        for (r, k), v in _used.items():
            old = seen.get(f"{r}|{k}", [0, ""])
            seen[f"{r}|{k}"] = [max(old[0], v[0]), max(old[1], v[1])]
    out = []
    for k, v in sorted(seen.items()):
        route, _, key = k.rpartition("|")
        out.append({"route": route, "key": key, "calls": v[0], "last": v[1]})
    return out


def for_manifest(manifest):
    """The parts of a plug-in's manifest that are going: [{what, deprecated, sunset, replacement, removed}], in plain words."""
    if not isinstance(manifest, dict):
        return []
    cs = [c for c in manifest.get("containers") or [] if isinstance(c, dict)]
    have = {"field": set(manifest), "permission": set(manifest.get("permissions") or []),
            "card": {c.get("type") for c in manifest.get("cards") or [] if isinstance(c, dict)},
            "setting": {c.get("type") for c in manifest.get("settings") or [] if isinstance(c, dict)},
            "event": set(manifest.get("events") or []), "container": {k for c in cs for k in c}}
    words = {"field": "the manifest field", "permission": "the permission", "card": "the card type", "setting": "the setting type",
             "event": "the event", "container": "the container option"}
    out = []
    for e in items():
        if "manifest" in e:
            kind, _, name = e["manifest"].partition(":")
            if name in have.get(kind, ()):
                out.append({"what": f"{words[kind]} {name}", "deprecated": e["deprecated"], "sunset": e["sunset"],
                            "replacement": e["replacement"], "removed": e["removed"]})
    return out


def warning_sentence(w):
    """One plain sentence for a plug-in's page or the tester."""
    day = dt.datetime.strptime(w["sunset"], "%Y-%m-%d").strftime("%-d %B %Y")
    tail = f" {w['replacement']}" if w["replacement"] else ""
    if w["removed"]:
        return f"It uses {w['what']}, which has been removed.{tail}"
    return f"It uses {w['what']}, which is going. It stops working after {day}.{tail} Ask its maker for an update."
