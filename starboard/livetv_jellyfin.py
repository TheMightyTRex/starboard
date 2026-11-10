"""Live TV without the hand steps (DASH-229): after Starboard builds the channel lists and guides, it adds them to
Jellyfin itself, as M3U tuners and XMLTV guides, over Jellyfin's API (/LiveTv/TunerHosts, /LiveTv/ListingProviders).
Safe to run again: a file Jellyfin already has is left alone, so a person's own tuners and guides stay as they are.

Jellyfin reads the files from its own side of the folder, so Starboard works out the path Jellyfin sees: the folder
the person typed in Settings, Apps, Jellyfin, or, for an Install apps stack, the Live TV folder inside Jellyfin's
settings folder (CONFIG_DIR/jellyfin is /config for Jellyfin). The FFmpeg wrapper from DASH-169 is not touched.
"""
import json
import os
import posixpath
import urllib.error
import urllib.request

from . import livetv

PLAYLISTS = [("channels.m3u", "Free-TV"), ("samsung.m3u", "Samsung TV Plus"), ("pluto.m3u", "Pluto TV")]
GUIDES = ["guide.xml", "guide-samsung.xml", "guide-pluto.xml"]
TIMEOUT = 20


def jellyfin_folder(extras, data_dir, host_path=None, env=None):
    """The Live TV folder as Jellyfin sees it, or None when Starboard cannot tell."""
    given = str((extras or {}).get("livetv_jellyfin_folder") or "").strip().rstrip("/")
    if given:
        return given
    host = (host_path if host_path is not None else os.environ.get("STARBOARD_LIVETV_PATH") or "").rstrip("/")
    if not host:
        return None
    if env is None:
        from . import stack
        env = stack.env_values(data_dir) or {}
    config_dir = (env.get("CONFIG_DIR") or "").rstrip("/")
    data = (env.get("DATA_DIR") or "").rstrip("/")
    for prefix, inside in ((f"{config_dir}/jellyfin", "/config"), (f"{data}/media", "/data/media")):
        if prefix.startswith("/") and len(prefix) > 1 and (host == prefix or host.startswith(prefix + "/")):
            return posixpath.join(inside, host[len(prefix):].lstrip("/")).rstrip("/")
    return None


def _call(base, key, method, path, body=None, opener=None):
    data = json.dumps(body).encode() if body is not None else None
    # Newer Jellyfin (10.11 and later) takes the key only in Authorization; older versions and Emby in X-Emby-Token.
    headers = {"Authorization": f'MediaBrowser Token="{key}"', "X-Emby-Token": key, "Accept": "application/json", "User-Agent": "Starboard"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method, headers=headers)
    with (opener or urllib.request.build_opener()).open(req, timeout=TIMEOUT) as r:  # Jellyfin from the dashboard  # nosec B310
        raw = r.read()
    return json.loads(raw) if raw else None


def folder_from_jellyfin(services, opener=None):
    """The Live TV folder as Jellyfin sees it, read from the tuners Jellyfin already has for Starboard's lists, so a
    move never adds the same lists again under another path. None when Jellyfin has none, or does not answer."""
    jf = next((s for s in services or [] if s.get("type") == "jellyfin" and s.get("url") and s.get("api_key")), None)
    if not jf:
        return None
    try:
        options = _call(jf["url"], jf["api_key"], "GET", "/System/Configuration/livetv", opener=opener) or {}
    except (urllib.error.URLError, OSError, ValueError):
        return None
    names = {n for n, _ in PLAYLISTS}
    for t in options.get("TunerHosts") or []:
        url = str(t.get("Url") or "")
        if posixpath.basename(url) in names and url.startswith("/"):
            return posixpath.dirname(url)
    return None


def _refresh(jf, opener=None):
    tasks = _call(jf["url"], jf["api_key"], "GET", "/ScheduledTasks?isHidden=false", opener=opener) or []
    task = next((t.get("Id") for t in tasks if t.get("Key") == "RefreshGuide"), None)
    if task:
        _call(jf["url"], jf["api_key"], "POST", f"/ScheduledTasks/Running/{task}", opener=opener)
    return bool(task)


def refresh_guide(services, opener=None):
    """Asks Jellyfin to read the guides again, after new ones were written (owner, 10 November 2026: Jellyfin kept
    the morning's guide until its own daily refresh). Returns a sentence, or "" when there is no Jellyfin."""
    jf = next((s for s in services if s.get("type") == "jellyfin" and s.get("api_key") and s.get("url")), None)
    if not jf:
        return ""
    try:
        return "Jellyfin: reading the new guides" if _refresh(jf, opener) else ""
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"Jellyfin: no answer ({getattr(e, 'reason', e)})"


def connect(services, extras, data_dir, local_folder=None, opener=None, host_path=None, env=None):
    """Adds the playlists and guides that exist to Jellyfin. Returns a short line, or "" when nothing changed."""
    jf = next((s for s in services or [] if s.get("type") == "jellyfin" and s.get("url") and s.get("api_key")), None)
    if not jf:
        return "Jellyfin: add its API key in Settings, Apps to add the channels to Jellyfin by itself"
    inside = jellyfin_folder(extras, data_dir, host_path=host_path, env=env)
    if not inside:
        return "Jellyfin: type the Live TV folder as Jellyfin sees it in Settings, Apps, Jellyfin, so Starboard can add the channels"
    here = local_folder or livetv.folder()
    try:
        options = _call(jf["url"], jf["api_key"], "GET", "/System/Configuration/livetv", opener=opener) or {}
        tuners = {t.get("Url") for t in options.get("TunerHosts") or []}
        guides = {g.get("Path") for g in options.get("ListingProviders") or []}
        added = 0
        for name, label in PLAYLISTS:
            path = f"{inside}/{name}"
            if path in tuners or not os.path.exists(os.path.join(here, name)):
                continue
            _call(jf["url"], jf["api_key"], "POST", "/LiveTv/TunerHosts",
                  {"Type": "m3u", "Url": path, "FriendlyName": label, "TunerCount": 0, "ImportFavoritesOnly": False,
                   "AllowHWTranscoding": True, "EnableStreamLooping": False, "IgnoreDts": True}, opener=opener)
            added += 1
        for name in GUIDES:
            path = f"{inside}/{name}"
            if path in guides or not os.path.exists(os.path.join(here, name)):
                continue
            _call(jf["url"], jf["api_key"], "POST", "/LiveTv/ListingProviders?validateListings=false&validateLogin=false",
                  {"Type": "xmltv", "Path": path, "EnableAllTuners": True}, opener=opener)
            added += 1
        if not added:
            return ""
        _refresh(jf, opener)
        return f"Jellyfin: added {added} channel {'list or guide' if added == 1 else 'lists and guides'} and started its guide refresh"
    except urllib.error.HTTPError as e:
        return f"Jellyfin: did not take the channels ({e.code}); add them by hand as Help, Set up Live TV says"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"Jellyfin: no answer ({getattr(e, 'reason', e)})"
