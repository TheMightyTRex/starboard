"""Locations (DASH-310, settings pattern 4, approved 12 November 2026): one picker for every folder setting.

A folder setting belongs to an app, and each app sees the computer's folders under its own path: Reelix sees the
media folder as /data. The picker shows the folder in words with its free space, Browse opens the computer's folders
where this folder is (or where the app's own folders are), and the chosen folder goes back to the app as the app
sees it. Set automatically gives the right folder for that setting. The typed path stays, under Advanced.

App "host" is the computer itself (Starboard's own folders); "reelix" is the Reelix container, read from its mounts.
"""
import urllib.parse

from . import folders

# The folder Set automatically gives each setting, as the app sees it.
SUGGEST = {
    "reelix": {"movies": "/data/media/movies", "tv": "/data/media/tv", "ebooks": "/data/media/books",
               "audiobooks": "/data/media/audiobooks", "music": "/data/media/music", "radio": "/data/media/radio",
               "direct": "/data/downloads/direct", "downloads": "/data/downloads"},
}
NAMES = {"reelix": "Reelix", "jellyfin": "Jellyfin", "host": "Starboard"}
# Folders not offered: Reelix's own settings folder. Jellyfin's /config is offered, for its Live TV folder.
# Where each app's own folders start, for the words when Starboard cannot read its mounts.
TOP = {"reelix": "/data", "jellyfin": "/"}
# Folder names said in the app's words.
NICE = {"movies": "Films", "tv": "Series"}
SKIP = {"reelix": ("/config", "/app/config"), "jellyfin": ()}


def mounts_of(app, inspect=None, data_dir=None):
    """[(host folder, the app's folder)] longest first; the computer itself for "host"; [] when the app is not there.
    "plugin:<id>" is a plug-in's media folders (API 1.3): the media folder, or one folder in it, as /media."""
    if app == "host":
        return [("/", "/")]
    if app.startswith("plugin:"):
        return _plugin_mounts(app[7:], data_dir)
    if app not in SKIP:
        raise ValueError("Starboard does not know that app's folders")
    from . import containers
    if inspect is None:
        if not containers.available():
            return []
        def inspect(name):
            return containers.docker("GET", f"/containers/{urllib.parse.quote(name, safe='')}/json")
    try:
        info = inspect(app) or {}
    except Exception:  # not running, or Docker refused: typing still works
        return []
    out = [(m.get("Source", ""), m.get("Destination", "")) for m in info.get("Mounts") or []
           if m.get("Type") == "bind" and m.get("Source") and m.get("Destination") not in SKIP[app]]
    return sorted(out, key=lambda m: -len(m[1]))


def _plugin_mounts(pid, data_dir):
    import json
    import os
    import re
    from . import plugins, stack
    if not data_dir or not re.match(r"^[a-z0-9][a-z0-9-]{0,39}$", pid or ""):
        raise ValueError("Starboard does not know that plug-in")
    try:
        with open(os.path.join(data_dir, "plugins", pid, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        raise ValueError("Starboard does not know that plug-in") from None
    media = (stack.env_values(data_dir).get("DATA_DIR") or "").rstrip("/")
    if not media:
        return []
    return sorted(((f"{media}/media" + inside[len("/media"):], inside) for inside in plugins.media_mounts(manifest)), key=lambda m: -len(m[1]))


def _under(path, top):
    return top == "/" or path == top or path.startswith(top.rstrip("/") + "/")


def to_host(path, mounts):
    for host, inside in sorted(mounts, key=lambda m: -len(m[1])):
        if _under(path, inside):
            rest = path[len(inside.rstrip("/")):] if inside != "/" else path
            return (host.rstrip("/") + rest) if host != "/" else (rest or "/")
    return None


def to_app(path, mounts):
    for host, inside in sorted(mounts, key=lambda m: -len(m[0])):
        if _under(path, host):
            rest = path[len(host.rstrip("/")):] if host != "/" else path
            return (inside.rstrip("/") + rest) if inside != "/" else (rest or "/")
    return None


def words(path, mounts):
    """The folder in words: Media, Music, Direct for /data/media/music/direct, after the app's own top folder."""
    top = next((inside for _, inside in sorted(mounts, key=lambda m: -len(m[1])) if _under(path, inside)), "/")
    rest = path[len(top.rstrip("/")):] if top != "/" else path
    parts = [p for p in rest.split("/") if p]
    if not parts:
        return "The whole media folder" if top != "/" else path
    def nice(p):
        p = NICE.get(p.lower(), p).replace("-", " ").replace("_", " ")
        return p[:1].upper() + p[1:]
    return ", ".join(nice(p) for p in parts)


def describe(app, path, setting="", read=None, mounts=None, host_defaults=None, data_dir=None):
    """{path, host, words, free, exists, ok, lines, suggest, start, mounts}: what the picker shows for one folder."""
    if mounts is None:
        mounts = mounts_of(app, data_dir=data_dir)
    suggest = SUGGEST.get(app, {}).get(setting, "")
    if app == "host" and host_defaults:
        suggest = host_defaults.get(setting, "")
    name = NAMES.get(app, "The plug-in" if app.startswith("plugin:") else app)
    out = {"app": app, "path": path, "host": None, "words": "", "free": None, "exists": None, "ok": True, "lines": [],
           "suggest": suggest, "mounts": [{"host": h, "app": a} for h, a in mounts], "can_browse": bool(mounts)}
    start = [h for h, a in mounts if a not in ("/",)]
    out["start"] = start[0] if start else ""
    if not mounts:
        out["lines"].append(f"Starboard cannot see where {name} keeps its folders, so Browse is off. Type the folder under Advanced.")
    path = (path or "").strip()
    if not path:
        out["words"] = "Not set"
        return out
    try:
        clean = folders.tidy(path)
    except ValueError as e:
        return {**out, "ok": False, "lines": [str(e)]}
    out["path"] = clean
    out["words"] = words(clean, mounts or [("", TOP.get(app, "/media" if app.startswith("plugin:") else "/"))])
    host = to_host(clean, mounts) if mounts else None
    if mounts and host is None:
        tops = ", ".join(a for _, a in mounts)
        return {**out, "ok": False, "lines": [f"{name} cannot see that folder. Choose one inside {tops}."]}
    out["host"] = host
    if host and folders.allowed(host):
        out["start"] = host
        got = (read or folders._read)(host)
        out["exists"] = got.get("exists")
        out["free"] = got.get("free")
        if got.get("why"):
            out["lines"].append(got["why"])
        elif got.get("exists") is False:
            out["lines"].append("This folder is made when it is first used.")
            if got.get("made_in"):
                out["start"] = got["made_in"]
    return out


def chosen(app, host_path, mounts=None, data_dir=None):
    """A folder chosen in Browse (as the computer sees it), given back as the app sees it."""
    if mounts is None:
        mounts = mounts_of(app, data_dir=data_dir)
    inside = to_app(folders.tidy(host_path), mounts)
    if inside is None:
        tops = ", ".join(h for h, _ in mounts) or "its folders"
        raise ValueError(f"{NAMES.get(app, app)} cannot see that folder. Choose one inside {tops}.")
    return inside
