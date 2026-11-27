"""Features of the public API that are going (DASH-603): the list in deprecations.json, empty until something is deprecated.

A route in the list answers as before but every answer carries `Deprecation` (RFC 9745, since when), `Sunset` (RFC 8594, the
earliest day it may stop) and a `Link` to what replaces it. Once an entry is marked `removed`, the route answers 410 gone with a
Link to the replacement. `GET /api/v1/` lists every entry, so an outside tool can warn its own owner. Nothing runs at rest: the
file is read once, the first time a request is checked, and an empty list costs one empty loop.

An entry: {"method": "GET", "path": "/api/v1/old", "deprecated": "2027-01-15", "sunset": "2028-01-15",
           "replacement": "Use /api/v1/new", "link": "https://.../api-changelog.md#...", "removed": false}
`path` is a regular expression matched against the whole path. Removing a route needs the notice in the compatibility policy.
"""
import datetime as dt
import email.utils
import json
import os
import re

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
                if not isinstance(e, dict) or e["method"] not in ("GET", "POST", "PUT", "DELETE", "*"):
                    continue
                re.compile(e["path"])
                _day(e["deprecated"])
                _day(e["sunset"])
                out.append({"method": e["method"], "path": e["path"], "deprecated": e["deprecated"], "sunset": e["sunset"],
                            "replacement": str(e.get("replacement") or "")[:200], "link": str(e.get("link") or "")[:300],
                            "removed": bool(e.get("removed"))})
            except (KeyError, ValueError, re.error):
                continue
        _items = out
    return _items


def entry(method, path):
    for e in items():
        if e["method"] in (method, "*") and re.fullmatch(e["path"], path):
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
    return [{k: e[k] for k in ("method", "path", "deprecated", "sunset", "replacement", "removed")} for e in items()]
