"""Dispatcharr from Starboard (DASH-228): nobody opens Dispatcharr's own pages.

Dispatcharr is an add-on in Install apps for paid IPTV, backup streams or full channel control (DASH-222); Starboard's
own Live TV stays the Live TV of every install. When the person adds it, Starboard:

- makes its admin (POST /api/accounts/initialize-superuser/) with the same name and password as every other app
  (DASH-234), signs in (/api/accounts/token/) and makes an API key for itself (/api/accounts/api-keys/generate/);
- adds the person's IPTV source when they give one: a playlist address, or an Xtream Codes server with a user name
  and password (/api/m3u/accounts/), and a guide address (/api/epg/sources/, XMLTV);
- turns the playlist's streams into channels when asked (/api/channels/channels/from-stream/bulk/), because
  Dispatcharr's tuner offers channels only, never raw streams;
- adds Dispatcharr to Jellyfin as an HDHomeRun tuner (http://dispatcharr:9191/hdhr) with its guide
  (http://dispatcharr:9191/output/epg), linked to each other, over Jellyfin's own API.

Each step is safe to run again: what is already there is left alone or updated, never added twice. Dispatcharr is
kept on Starboard's apps as a link with the key Starboard made (no new kind of app). Nothing here runs on a timer:
only when the person opens Settings, Apps, Dispatcharr or saves on it (lightweight rule).
"""
import urllib.error
import urllib.parse

from . import app_setup, livetv_jellyfin

ADMIN = app_setup.ADMIN
PLAYLIST = "Starboard playlist"
GUIDE = "Starboard guide"
INSIDE = "http://dispatcharr:9191"  # Dispatcharr as Jellyfin reaches it on the stack Install apps wrote
TUNER_NAME = "Dispatcharr"
MOST_CHANNELS = 1000  # Make channels takes the first 1000 streams; more slows Jellyfin's guide (decided: recommended)
KINDS = ("m3u", "xc")
OPENER = None  # the example server and the tests answer for Dispatcharr and Jellyfin here; None is the real network


class DispatcharrError(Exception):
    pass


# Where Dispatcharr is ----------------------------------------------------------------------------------------------

def service(cfg):
    """Dispatcharr on Starboard's apps: a link with the icon dispatcharr (as Install apps and Search add it)."""
    return next((s for s in cfg.data["services"] if (s.get("icon") or s.get("type")) == "dispatcharr" and s.get("url")), None)


def address(cfg, data_dir):
    """Dispatcharr's address for Starboard: the one on its apps, or the port Install apps gave it."""
    s = service(cfg)
    if s:
        return s["url"].rstrip("/")
    from . import stack
    return stack.app_url(data_dir, "dispatcharr", 9191)


def inside_address(cfg, data_dir):
    """Dispatcharr as Jellyfin reaches it: by name on the stack when Install apps installed both, otherwise the
    address Starboard uses (an app someone installed themselves)."""
    from . import stack
    keys = set(stack.chosen_keys(data_dir) or [])
    if {"dispatcharr", "jellyfin"} <= keys:
        return INSIDE
    return address(cfg, data_dir)


def jellyfin(cfg):
    jf = next((s for s in cfg.data["services"] if s.get("type") == "jellyfin" and s.get("url") and s.get("api_key")), None)
    return jf


def _key_headers(key):
    return {"X-API-Key": key}


def _call(base, method, path, body=None, headers=None, opener=None):
    try:
        return app_setup._call(base, method, path, body, headers=headers, opener=opener or OPENER)
    except app_setup.AppSetupError as e:
        raise DispatcharrError(str(e)) from None


# First run ---------------------------------------------------------------------------------------------------------

def first_run(base, password, user=ADMIN, opener=None):
    """Makes Dispatcharr's admin when it has none, signs in and returns (a key for Starboard, lines of what was done,
    {}), in the shape of app_setup's other first runs. Raises app_setup.AppSetupError, so a Dispatcharr still
    starting is tried again by app_setup._when_ready."""
    opener = opener or OPENER
    done = []
    first = app_setup._call(base, "GET", "/api/accounts/initialize-superuser/", opener=opener) or {}
    if not first.get("superuser_exists"):
        try:
            app_setup._call(base, "POST", "/api/accounts/initialize-superuser/",
                            {"username": user, "password": password, "email": ""}, opener=opener)
        except app_setup.AppSetupError as e:
            if str(e).startswith("403"):
                raise app_setup.AppSetupError("Dispatcharr lets its admin be made only from some addresses, and not from "
                                              "Starboard's. Make the admin in Dispatcharr, then add its API key in Settings, "
                                              "Apps, Manage apps") from None
            raise
        done.append(f"Set up Dispatcharr with the account {user} and your Starboard password")
    try:
        token = (app_setup._call(base, "POST", "/api/accounts/token/", {"username": user, "password": password}, opener=opener) or {}).get("access")
    except app_setup.AppSetupError as e:
        if any(str(e).startswith(c) for c in ("400", "401", "403")):
            raise app_setup.AppSetupError("Dispatcharr was set up before with another account, so Starboard cannot sign in. "
                                          "Add Dispatcharr's API key in Settings, Apps, Manage apps") from None
        raise
    if not token:
        raise app_setup.AppSetupError("Dispatcharr did not give Starboard a sign-in")
    auth = {"Authorization": f"Bearer {token}"}
    key = (app_setup._call(base, "GET", "/api/accounts/api-keys/", headers=auth, opener=opener) or {}).get("key")
    if not key:
        key = (app_setup._call(base, "POST", "/api/accounts/api-keys/generate/", {}, headers=auth, opener=opener) or {}).get("key")
    if not key:
        raise app_setup.AppSetupError("Dispatcharr did not make an API key for Starboard")
    return key, done, {}


def save_key(cfg, base, key):
    """Keeps Dispatcharr on Starboard's apps with its key: the link already there, or a new one."""
    current = service(cfg)
    if current:
        cfg.upsert_service({**current, "api_key": key})
    else:
        cfg.upsert_service({"name": "Dispatcharr", "type": "link", "icon": "dispatcharr", "url": base, "api_key": key})


def connect(cfg, data_dir, password, opener=None):
    """Settings, Apps, Dispatcharr, Connect: the first run with the Starboard password (already checked by the
    server), then the key kept. Returns lines of what was done."""
    base = address(cfg, data_dir)
    if not base:
        raise DispatcharrError("Dispatcharr is not installed. Add it in Settings, Apps, Your install, Add-ons")
    try:
        key, done, _ = first_run(base, password, opener=opener)
    except app_setup.AppSetupError as e:
        raise DispatcharrError(str(e)) from None
    save_key(cfg, base, key)
    return done + ["Starboard keeps Dispatcharr's key, so you never sign in to Dispatcharr"]


# What is there -----------------------------------------------------------------------------------------------------

def _app(cfg):
    s = service(cfg)
    if not s or not s.get("api_key"):
        raise ValueError("Starboard has no key for Dispatcharr yet")
    return s["url"].rstrip("/"), _key_headers(s["api_key"])


def _list(answer):
    """A list from Dispatcharr: some routes page their answers ({count, results}), some do not."""
    if isinstance(answer, dict):
        return answer.get("results") or []
    return answer if isinstance(answer, list) else []


def _count(base, headers, path, opener):
    answer = _call(base, "GET", path, headers=headers, opener=opener)
    if isinstance(answer, dict) and "count" in answer:
        return int(answer.get("count") or 0)
    return len(_list(answer))


def _mine(base, headers, opener):
    playlists = _list(_call(base, "GET", "/api/m3u/accounts/", headers=headers, opener=opener))
    guides = _list(_call(base, "GET", "/api/epg/sources/", headers=headers, opener=opener))
    playlist = next((p for p in playlists if p.get("name") == PLAYLIST), None)
    guide = next((g for g in guides if g.get("name") == GUIDE), None)
    others = [p.get("name") for p in playlists if p.get("name") != PLAYLIST] + \
             [g.get("name") for g in guides if g.get("name") != GUIDE and g.get("source_type") != "dummy"]
    return playlist, guide, [o for o in others if o]


def _jellyfin_state(cfg, data_dir, opener):
    """{connected, tuner, guide} as Jellyfin has them; connected is None when there is no Jellyfin to ask."""
    jf = jellyfin(cfg)
    if not jf:
        return {"connected": None, "tuner": False, "guide": False}
    inside = inside_address(cfg, data_dir)
    try:
        options = livetv_jellyfin._call(jf["url"], jf["api_key"], "GET", "/System/Configuration/livetv", opener=opener or OPENER) or {}
    except (urllib.error.URLError, OSError, ValueError):
        return {"connected": None, "tuner": False, "guide": False}
    tuner = any(str(t.get("Url") or "").rstrip("/") == f"{inside}/hdhr" for t in options.get("TunerHosts") or [])
    guide = any(str(g.get("Path") or "") == f"{inside}/output/epg" for g in options.get("ListingProviders") or [])
    return {"connected": tuner and guide, "tuner": tuner, "guide": guide}


def state(cfg, data_dir, opener=None):
    """What Settings, Apps, Dispatcharr shows. installed False: not installed; connected False: no key yet."""
    s = service(cfg)
    base = address(cfg, data_dir)
    if not base:
        return {"installed": False, "connected": False}
    if not s or not s.get("api_key"):
        return {"installed": True, "connected": False, "address": base}
    base, headers = _app(cfg)
    playlist, guide, others = _mine(base, headers, opener)
    streams = channels = 0
    if playlist:
        streams = _count(base, headers, f"/api/channels/streams/?m3u_account={int(playlist['id'])}&page_size=1", opener)
    channels = _count(base, headers, "/api/channels/channels/?page_size=1", opener)
    source = None
    if playlist:
        source = {"kind": "xc" if playlist.get("account_type") == "XC" else "m3u", "url": playlist.get("server_url") or "",
                  "username": playlist.get("username") or "", "max_streams": int(playlist.get("max_streams") or 0),
                  "status": playlist.get("status") or "", "message": playlist.get("last_message") or ""}
    return {"installed": True, "connected": True, "address": base, "source": source,
            "guide": {"url": guide.get("url") or "", "status": guide.get("status") or "", "message": guide.get("last_message") or ""} if guide else None,
            "streams": streams, "channels": channels, "most_channels": MOST_CHANNELS, "others": others,
            "jellyfin": _jellyfin_state(cfg, data_dir, opener)}


# Saving the IPTV source ---------------------------------------------------------------------------------------------

def _address(value, what):
    value = str(value or "").strip()
    if not value:
        return ""
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc or len(value) > 2000 or any(c.isspace() for c in value):
        raise ValueError(f"Type the {what} as a full address, starting http:// or https://")
    return value


def check_choice(choice):
    """The person's IPTV source, checked: {kind, url, username, password, guide, max_streams}."""
    if not isinstance(choice, dict):
        raise ValueError("Type your IPTV source")
    kind = choice.get("kind") or "m3u"
    if kind not in KINDS:
        raise ValueError("Choose Playlist address or Xtream Codes")
    url = _address(choice.get("url"), "playlist address" if kind == "m3u" else "server address")
    if not url:
        raise ValueError("Type your playlist address" if kind == "m3u" else "Type your IPTV server's address")
    username = str(choice.get("username") or "").strip()[:200]
    password = str(choice.get("password") or "")[:200]
    if kind == "xc" and not username:
        raise ValueError("Type the user name your IPTV provider gave you")
    try:
        most = int(choice.get("max_streams") or 0)
    except (TypeError, ValueError):
        raise ValueError("Streams at once is a number from 0 to 50") from None
    if not 0 <= most <= 50:
        raise ValueError("Streams at once is a number from 0 to 50")
    return {"kind": kind, "url": url, "username": username if kind == "xc" else "", "password": password if kind == "xc" else "",
            "guide": _address(choice.get("guide"), "guide address"), "max_streams": most}


def save(cfg, data_dir, choice, opener=None):
    """Adds or updates the person's playlist and guide in Dispatcharr, then adds Dispatcharr to Jellyfin. Returns
    {state, done}. A blank password on an Xtream Codes source keeps the one Dispatcharr has."""
    c = check_choice(choice)
    base, headers = _app(cfg)
    playlist, guide, _ = _mine(base, headers, opener)
    done = []
    fields = {"name": PLAYLIST, "server_url": c["url"], "account_type": "XC" if c["kind"] == "xc" else "STD",
              "max_streams": c["max_streams"], "is_active": True}
    if c["kind"] == "xc":
        fields["username"] = c["username"]
        if c["password"] or not playlist:
            fields["password"] = c["password"]
    if playlist:
        _call(base, "PATCH", f"/api/m3u/accounts/{int(playlist['id'])}/", fields, headers=headers, opener=opener)
        done.append("Updated your IPTV playlist in Dispatcharr")
    else:
        playlist = _call(base, "POST", "/api/m3u/accounts/", fields, headers=headers, opener=opener) or {}
        done.append("Added your IPTV playlist to Dispatcharr")
    if playlist.get("id") is not None:
        try:  # Dispatcharr reads a new playlist by itself; this asks it to read a changed one now
            _call(base, "POST", f"/api/m3u/refresh/{int(playlist['id'])}/", {}, headers=headers, opener=opener)
        except DispatcharrError:
            pass
    if c["guide"]:
        g = {"name": GUIDE, "source_type": "xmltv", "url": c["guide"], "is_active": True}
        if guide:
            _call(base, "PATCH", f"/api/epg/sources/{int(guide['id'])}/", g, headers=headers, opener=opener)
            done.append("Updated your guide in Dispatcharr")
        else:
            _call(base, "POST", "/api/epg/sources/", g, headers=headers, opener=opener)
            done.append("Added your guide to Dispatcharr")
    line = connect_jellyfin(cfg, data_dir, max_streams=c["max_streams"], opener=opener)
    if line:
        done.append(line)
    from . import setup_left
    setup_left.record(data_dir, dispatcharr=True)  # Still to set up: done
    return {"state": state(cfg, data_dir, opener), "done": done}


def make_channels(cfg, data_dir, opener=None):
    """Turns the playlist's streams into channels, up to MOST_CHANNELS: Dispatcharr's tuner offers only channels.
    Dispatcharr makes them in the background. Returns {done, state}."""
    base, headers = _app(cfg)
    playlist, _, _ = _mine(base, headers, opener)
    if not playlist:
        raise ValueError("Add your IPTV source first")
    have = _count(base, headers, "/api/channels/channels/?page_size=1", opener)
    if have:
        raise ValueError("Dispatcharr has channels already. Change them in Dispatcharr, Channels")
    answer = _call(base, "GET", f"/api/channels/streams/?m3u_account={int(playlist['id'])}&page_size={MOST_CHANNELS}",
                   headers=headers, opener=opener)
    ids = [int(s["id"]) for s in _list(answer) if isinstance(s, dict) and s.get("id") is not None][:MOST_CHANNELS]
    if not ids:
        raise ValueError("Dispatcharr has not read your playlist yet. Wait a minute, then try again")
    total = answer.get("count", len(ids)) if isinstance(answer, dict) else len(ids)
    _call(base, "POST", "/api/channels/channels/from-stream/bulk/", {"stream_ids": ids, "starting_channel_number": 0},
          headers=headers, opener=opener)
    done = [f"Dispatcharr is making {len(ids)} {'channel' if len(ids) == 1 else 'channels'}"
            + (f", the first {len(ids)} of {total} streams" if total > len(ids) else "")]
    line = connect_jellyfin(cfg, data_dir, max_streams=int(playlist.get("max_streams") or 0), opener=opener)
    if line:
        done.append(line)
    return {"done": done, "state": state(cfg, data_dir, opener)}


# Jellyfin ----------------------------------------------------------------------------------------------------------

def connect_jellyfin(cfg, data_dir, max_streams=0, opener=None):
    """Adds Dispatcharr to Jellyfin as an HDHomeRun tuner with Dispatcharr's guide linked to it, and starts
    Jellyfin's guide refresh. Returns a short line, or "" when Jellyfin already had both."""
    jf = jellyfin(cfg)
    if not jf:
        return "Jellyfin: add its API key in Settings, Apps, so Starboard can add Dispatcharr's channels to it"
    opener = opener or OPENER
    inside = inside_address(cfg, data_dir)
    tuner_url, guide_url = f"{inside}/hdhr", f"{inside}/output/epg"
    call = lambda method, path, body=None: livetv_jellyfin._call(jf["url"], jf["api_key"], method, path, body, opener=opener)  # noqa: E731
    try:
        options = call("GET", "/System/Configuration/livetv") or {}
        tuner = next((t for t in options.get("TunerHosts") or [] if str(t.get("Url") or "").rstrip("/") == tuner_url), None)
        added = []
        if not tuner:
            call("POST", "/LiveTv/TunerHosts", {"Type": "hdhomerun", "Url": tuner_url, "FriendlyName": TUNER_NAME,
                                               "TunerCount": max_streams, "ImportFavoritesOnly": False,
                                               "AllowHWTranscoding": True, "EnableStreamLooping": False})
            added.append("tuner")
            options = call("GET", "/System/Configuration/livetv") or {}
            tuner = next((t for t in options.get("TunerHosts") or [] if str(t.get("Url") or "").rstrip("/") == tuner_url), None)
        own = (tuner or {}).get("Id")
        want = {"EnableAllTuners": False, "EnabledTuners": [own]} if own else {"EnableAllTuners": True}
        guide = next((g for g in options.get("ListingProviders") or [] if g.get("Path") == guide_url), None)
        if not guide:
            call("POST", "/LiveTv/ListingProviders?validateListings=false&validateLogin=false", {"Type": "xmltv", "Path": guide_url, **want})
            added.append("guide")
        elif own and (guide.get("EnableAllTuners") or list(guide.get("EnabledTuners") or []) != [own]):
            call("POST", "/LiveTv/ListingProviders?validateListings=false&validateLogin=false", {**guide, **want})
            added.append("guide")
        if not added:
            return ""
        livetv_jellyfin._refresh(jf, opener)
        return ("Jellyfin: added Dispatcharr as a tuner, with its guide" if "tuner" in added
                else "Jellyfin: linked Dispatcharr's guide to its tuner") + ", and started its guide refresh"
    except urllib.error.HTTPError as e:
        return f"Jellyfin: did not take Dispatcharr's tuner ({e.code}). In Jellyfin, Live TV, add an HDHomeRun tuner at {tuner_url}"
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"Jellyfin: no answer ({getattr(e, 'reason', e)})"
