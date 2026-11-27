"""Named capabilities for the optional parts of the plug-in API (API 1.21, DASH-603).

A version number says "this Starboard has the whole API up to here". An optional part, such as the media server slot or a first
sign-in, is better asked for by name: a plug-in says it needs a capability (it cannot work without it) or uses it if it is
there (it works either way and looks at `GET /api/v1/` to decide). Names are never reused or renamed once published.

    "capabilities": {"needs": ["first-sign-in"], "uses": ["sparkline-card"]}

`GET /api/v1/` answers `capabilities`, the names this Starboard has. A plug-in that needs one this Starboard does not have is not
added, and a catalogue version that needs one is not offered. Nothing here runs at rest: a constant and a short check.
"""
import re

# name -> what it is, in words, and the API version that brought it
CAPABILITIES = {
    "media-server-slot": ("Be Starboard's media server", "1.17"),
    "first-sign-in": ("A first password Starboard makes and shows once", "1.20"),
    "sparkline-card": ("The sparkline card", "1.17"),
    "guide-card": ("The guide card, what is on now", "1.8"),
    "alerts-send": ("Raise and clear alerts through Starboard", "1.17"),
    "partial-pages": ("Custom pages that save in place, choose several and come in cards", "1.16"),
    "api-socket": ("Starboard's API on a Unix socket in the run folder", "1.16"),
    "update-steps": ("Steps before and after an update, a health wait and settings that move with a version", "1.14"),
    "app-plugins": ("A whole app as a plug-in, with its own port, secrets and data", "1.13"),
    "schedule-setting": ("A setting that is a time of day, week or month, and a job that uses it", "1.14"),
}
NAME = re.compile(r"^[a-z][a-z0-9-]{1,39}$")


def names():
    return list(CAPABILITIES)


def problems(spec):
    """What is wrong with a manifest's capabilities, in words. An unknown name in `needs` is a problem (it cannot run here);
    one in `uses` is not (the plug-in copes without it)."""
    if spec is None:
        return []
    if not isinstance(spec, dict) or set(spec) - {"needs", "uses"}:
        return ["capabilities must be an object with needs and uses, each a list of names (API 1.21)"]
    out = []
    for key in ("needs", "uses"):
        got = spec.get(key, [])
        if not (isinstance(got, list) and len(got) <= 12 and all(isinstance(n, str) and NAME.match(n) for n in got)):
            out.append(f"capabilities.{key} must be up to 12 names such as first-sign-in")
    if not out:
        gone = [n for n in spec.get("needs", []) if n not in CAPABILITIES]
        if gone:
            out.append(f"It needs {', '.join(gone)}, which this Starboard does not have")
    return out


def missing(needed):
    """Which of these names this Starboard does not have."""
    return [n for n in needed or [] if n not in CAPABILITIES]
