"""Jellyfin libraries a plug-in fills (DASH-430, plug-in API 1.15). Owner, 14 November 2026: "turn off real-time
monitoring for the two On demand libraries only and have this as the standard setting when we install on demand plugin
- we might need to catch this for other plugins".

A plug-in names its libraries in jellyfin_libraries, each a folder inside a media folder it mounts. On every Turn on
(so after each install, update and Roll back too) Starboard adds any that Jellyfin does not have, with real-time
monitoring turned off unless the plug-in set realtime_monitor, and puts that choice back on one that has drifted.
Real-time monitoring makes Jellyfin watch every folder in a library, and each watch counts against the computer's
limit (found 14 November 2026: Jellyfin's watches used the limit up before Films and TV); a plug-in that adds files
itself tells Jellyfin to look instead. Removing the plug-in leaves the libraries in Jellyfin, as they are the person's
to keep or remove there. Nothing here stops a plug-in starting: a problem is kept in its state and logged."""
import os
import urllib.parse

from . import logs, plugins

DEFAULT_INSIDE = "/data/media"  # where Install apps mounts the media folder in Jellyfin


def jellyfin(services):
    """Jellyfin with its key from Starboard's apps, or None."""
    return next((s for s in services or [] if s.get("type") == "jellyfin" and s.get("api_key") and s.get("enabled", True)), None)


def media_inside(data_dir, service, inspect=None):
    """The media folder as Jellyfin sees it: from Jellyfin's own container, the mount holding Starboard's media folder
    (/data/media for Install apps, /media on a server set up by hand); /data/media when it cannot be read."""
    from . import containers
    from . import plugins_admin as pa
    host = pa.media_host_dir(data_dir)
    name = (service or {}).get("container") or "jellyfin"
    try:
        info = (inspect or (lambda n: containers.docker("GET", f"/containers/{urllib.parse.quote(n, safe='')}/json")))(name)
    except Exception:  # noqa: BLE001  Docker may be out of reach; the usual place is right for Install apps
        return DEFAULT_INSIDE
    best = None
    for m in (info or {}).get("Mounts") or []:
        src, dst = str(m.get("Source") or "").rstrip("/"), str(m.get("Destination") or "").rstrip("/")
        if host and src and (host == src or host.startswith(src + "/")) and (best is None or len(src) > len(best[0])):
            best = (src, dst)
    return (best[1] + host[len(best[0]):]) if best else DEFAULT_INSIDE


def _call(service, method, path, body=None, call=None):
    from . import app_setup
    # Jellyfin 12 with legacy authorisation off takes the key only in Authorization; older versions and Emby in
    # X-Emby-Token. Both are sent (DASH-458).
    key = service["api_key"]
    headers = {"Authorization": f'MediaBrowser Token="{key}"', "X-Emby-Token": key}
    if call:
        return call(method, path, body)
    return app_setup._call(service["url"], method, path, body, headers=headers)


def ensure(data_dir, pid, services, call=None, inspect=None):
    """Adds the plug-in's libraries Jellyfin does not have and keeps real-time monitoring as the plug-in wants it.
    Returns lines of what was done; records them, or the problem, in the plug-in's state."""
    from . import plugins_admin as pa
    where = pa.folder(data_dir, pid)
    m = pa._read(os.path.join(where, "manifest.json"), {}) or {}
    libs = [x for x in m.get("jellyfin_libraries") or [] if isinstance(x, dict)]
    if not libs or "jellyfin:libraries" not in (m.get("permissions") or []):
        return []
    service = jellyfin(services)
    done, kept = [], []
    try:
        if not service:
            raise ValueError("Starboard has no key for Jellyfin, so the libraries were not added. Connect Jellyfin in "
                             "Settings, Apps, then turn off and turn on the plug-in")
        inside = media_inside(data_dir, service, inspect).rstrip("/")
        have = _call(service, "GET", "/Library/VirtualFolders", call=call) or []
        for lib in libs:
            path = inside + "/" + lib["folder"].split("/", 1)[1]
            wanted = bool(lib.get("realtime_monitor", False))
            found = next((f for f in have if path in (f.get("Locations") or [])), None) or \
                next((f for f in have if str(f.get("Name", "")).lower() == lib["name"].lower()), None)
            if not found:
                q = {"name": lib["name"], "refreshLibrary": "false"}
                if plugins.LIBRARY_TYPES.get(lib["type"]):
                    q["collectionType"] = plugins.LIBRARY_TYPES[lib["type"]]
                _call(service, "POST", f"/Library/VirtualFolders?{urllib.parse.urlencode(q)}",
                      {"LibraryOptions": {"EnableRealtimeMonitor": wanted, "PathInfos": [{"Path": path}]}}, call=call)
                done.append(f"Added the library {lib['name']} to Jellyfin, with real-time monitoring "
                            + ("turned on" if wanted else "turned off"))
            else:
                opts = found.get("LibraryOptions") or {}
                if bool(opts.get("EnableRealtimeMonitor")) != wanted and found.get("ItemId"):
                    _call(service, "POST", "/Library/VirtualFolders/LibraryOptions",
                          {"Id": found["ItemId"], "LibraryOptions": {**opts, "EnableRealtimeMonitor": wanted}}, call=call)
                    done.append(f"Real-time monitoring {'turned on' if wanted else 'turned off'} for {found.get('Name')} in Jellyfin")
            kept.append({"name": lib["name"], "path": path, "realtime_monitor": wanted})
        problem = ""
    except Exception as e:  # noqa: BLE001  a library is a help, never a reason the plug-in cannot start
        problem = str(e)[:300]
        logs.event("warning", "plug-ins", f"{m.get('name', pid)}: its Jellyfin libraries were not checked: {problem}")
    st = pa._read(os.path.join(where, "state.json"), {}) or {}
    st["libraries"] = {"items": kept, "said": problem or ("; ".join(done) if done else "Jellyfin has them as the plug-in wants")}
    pa._write(os.path.join(where, "state.json"), st)
    for line in done:
        logs.event("info", "plug-ins", f"{m.get('name', pid)}: {line}")
    return done
