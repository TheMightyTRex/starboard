"""First runs of the apps Install apps starts, done by Starboard over each app's own API, so nobody opens their pages
(DASH-179, DASH-180, DASH-234). Each step is safe to run again: an app already set up is signed in to and only what
is missing is added.

- Jellyfin: the start-up wizard (/Startup/*), the Films, Series and Music libraries, and an API key for Starboard.
- Audiobookshelf: the root user (/init), the Audiobooks, Books and Radio libraries, and an API key for Starboard.

One admin for every app (DASH-234): the same name ("admin") and the Starboard password, as Reelix already has. The
password is used for these calls only and never kept; Starboard keeps each app's API key, as it does today.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

ADMIN = "admin"
KEY_NAME = "Starboard"
TIMEOUT = 20

# (kind of media chosen, Jellyfin's library name, collection type, folder inside Jellyfin)
JELLYFIN_LIBRARIES = [("movies", "Films", "movies", "/data/media/movies"), ("tv", "Series", "tvshows", "/data/media/tv"),
                      ("music", "Music", "music", "/data/media/music")]
# (kind of media chosen, Audiobookshelf's library name, media type, folder inside Audiobookshelf)
ABS_LIBRARIES = [("audiobooks", "Audiobooks", "book", "/media/audiobooks"), ("ebooks", "Books", "book", "/media/books"),
                 ("radio", "Radio", "podcast", "/media/radio")]


class AppSetupError(Exception):
    pass


def _call(base, method, path, body=None, headers=None, opener=None):
    """One request; returns the parsed answer (or the text), raising AppSetupError with the app's words on failure."""
    data = json.dumps(body).encode() if body is not None else None
    h = {"Accept": "application/json", "User-Agent": "Starboard", **(headers or {})}
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method, headers=h)
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=TIMEOUT) as r:  # an app's address on this computer, from the stack  # nosec B310
            raw = r.read()
    except urllib.error.HTTPError as e:
        words = e.read()[:300].decode("utf-8", "replace").strip()
        raise AppSetupError(f"{e.code} from {method} {path}" + (f": {words}" if words else "")) from None
    except (urllib.error.URLError, OSError) as e:
        raise AppSetupError(f"no answer at {base}: {getattr(e, 'reason', e)}") from None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw.decode("utf-8", "replace")


# Jellyfin -------------------------------------------------------------------------------------------------------

def _jf_auth(token=None):
    words = 'MediaBrowser Client="Starboard", Device="Starboard", DeviceId="starboard-setup", Version="1"'
    return {"Authorization": words + (f', Token="{token}"' if token else "")}


def jellyfin_first_run(base, password, groups, country="GB", user=ADMIN, opener=None):
    """Finishes Jellyfin's start-up wizard when it has not run, signs in, adds the libraries for what was chosen and
    returns (API key, lines of what was done)."""
    done = []
    info = _call(base, "GET", "/System/Info/Public", opener=opener) or {}
    if not info.get("StartupWizardCompleted"):
        _call(base, "POST", "/Startup/Configuration", {"UICulture": "en-GB", "MetadataCountryCode": country,
                                                        "PreferredMetadataLanguage": "en"}, opener=opener)
        _call(base, "GET", "/Startup/User", opener=opener)  # makes the first user, which the next call names
        _call(base, "POST", "/Startup/User", {"Name": user, "Password": password}, opener=opener)
        _call(base, "POST", "/Startup/RemoteAccess", {"EnableRemoteAccess": True, "EnableAutomaticPortMapping": False}, opener=opener)
        _call(base, "POST", "/Startup/Complete", opener=opener)
        done.append(f"Set up Jellyfin with the account {user} and your Starboard password")
    try:
        signed = _call(base, "POST", "/Users/AuthenticateByName", {"Username": user, "Pw": password}, headers=_jf_auth(), opener=opener) or {}
    except AppSetupError as e:
        raise AppSetupError("Jellyfin was set up before with another account, so Starboard cannot sign in. Add Jellyfin's "
                            f"API key in Settings, Apps, Manage apps ({e})") from None
    token = signed.get("AccessToken")
    if not token:
        raise AppSetupError("Jellyfin did not give Starboard a sign-in")
    auth = _jf_auth(token)
    have = _call(base, "GET", "/Library/VirtualFolders", headers=auth, opener=opener) or []
    paths = {p for f in have for p in (f.get("Locations") or [])}
    names = {f.get("Name") for f in have}
    for kind, name, collection, folder in JELLYFIN_LIBRARIES:
        if kind not in groups or folder in paths or name in names:
            continue
        query = urllib.parse.urlencode({"name": name, "collectionType": collection, "refreshLibrary": "false"})
        _call(base, "POST", f"/Library/VirtualFolders?{query}", {"LibraryOptions": {"PathInfos": [{"Path": folder}]}},
              headers=auth, opener=opener)
        done.append(f"Added the {name} library to Jellyfin")
    key = _jf_key(base, auth, opener)
    return key, done, {}


def _jf_key(base, auth, opener):
    def find():
        items = (_call(base, "GET", "/Auth/Keys", headers=auth, opener=opener) or {}).get("Items") or []
        return next((i.get("AccessToken") for i in items if i.get("AppName") == KEY_NAME and i.get("AccessToken")), None)
    key = find()
    if not key:
        _call(base, "POST", f"/Auth/Keys?{urllib.parse.urlencode({'app': KEY_NAME})}", headers=auth, opener=opener)
        key = find()
    if not key:
        raise AppSetupError("Jellyfin did not make an API key for Starboard")
    return key


# Audiobookshelf --------------------------------------------------------------------------------------------------

def audiobookshelf_first_run(base, password, groups, user=ADMIN, opener=None):
    """Makes Audiobookshelf's root user when it has none, signs in, adds the libraries for what was chosen and
    returns (API key, lines of what was done). The key needs Audiobookshelf 2.26 or later."""
    done = []
    status = _call(base, "GET", "/status", opener=opener) or {}
    if status.get("isInit") is False:
        _call(base, "POST", "/init", {"newRoot": {"username": user, "password": password}}, opener=opener)
        done.append(f"Set up Audiobookshelf with the account {user} and your Starboard password")
    try:
        signed = _call(base, "POST", "/login", {"username": user, "password": password}, opener=opener) or {}
    except AppSetupError as e:
        raise AppSetupError("Audiobookshelf was set up before with another account, so Starboard cannot sign in. Add "
                            f"Audiobookshelf's API key in Settings, Apps, Manage apps ({e})") from None
    who = signed.get("user") or {}
    token = who.get("accessToken") or who.get("token")
    if not token:
        raise AppSetupError("Audiobookshelf did not give Starboard a sign-in")
    auth = {"Authorization": f"Bearer {token}"}
    have = (_call(base, "GET", "/api/libraries", headers=auth, opener=opener) or {}).get("libraries") or []
    paths = {f.get("fullPath") for lib in have for f in (lib.get("folders") or [])}
    names = {lib.get("name") for lib in have}
    for kind, name, media_type, folder in ABS_LIBRARIES:
        if kind not in groups or folder in paths or name in names:
            continue
        _call(base, "POST", "/api/libraries", {"name": name, "mediaType": media_type, "folders": [{"fullPath": folder}]},
              headers=auth, opener=opener)
        done.append(f"Added the {name} library to Audiobookshelf")
    made = (_call(base, "POST", "/api/api-keys", {"name": KEY_NAME, "userId": who.get("id"), "isActive": True},
                  headers=auth, opener=opener) or {}).get("apiKey") or {}
    key = made.get("apiKey")
    if not key:
        raise AppSetupError("Audiobookshelf did not make an API key for Starboard: it needs version 2.26 or later")
    libraries = (_call(base, "GET", "/api/libraries", headers=auth, opener=opener) or {}).get("libraries") or []
    radio = next((lib for lib in libraries if lib.get("mediaType") == "podcast"
                  and any(f.get("fullPath") == "/media/radio" for f in lib.get("folders") or [])), None)
    return key, done, {"radio_library": radio.get("id") if radio else None}


# Together --------------------------------------------------------------------------------------------------------

def country_from_tz(tz):
    """GB for Europe/London; otherwise None, which leaves Jellyfin's own default."""
    return {"Europe/London": "GB", "Europe/Dublin": "IE"}.get(tz or "")


def first_runs(cfg, data_dir, password, groups, log=lambda line: None, opener=None, found=None):
    """Jellyfin's and Audiobookshelf's first runs, when Install apps installed them, and their keys saved on the
    dashboard so Reelix can be connected to them (DASH-156). Returns lines of what was done; a problem is a line too,
    never a stop, so the rest of the set-up carries on."""
    from . import stack
    done = []
    keys = stack.chosen_keys(data_dir) or []
    apps = [("jellyfin", "Jellyfin", 8096, jellyfin_first_run), ("audiobookshelf", "Audiobookshelf", 80, audiobookshelf_first_run)]
    for key, name, inside, run in apps:
        if key not in keys:
            continue
        base = stack.app_url(data_dir, key, inside)
        if not base:
            continue
        try:
            extra = {"country": country_from_tz(os.environ.get("TZ")) or "GB"} if key == "jellyfin" else {}
            api_key, lines, more = run(base, password, groups, opener=opener, **extra)
        except AppSetupError as e:
            done.append(f"{name} is not set up yet: {e}")
            continue
        done += lines
        if found is not None:
            found.update(more)
        _save_key(cfg, key, name, base, api_key)
        log(f"{name} ready")
    return done


def _save_key(cfg, kind, name, base, api_key):
    current = next((s for s in cfg.data["services"] if s.get("type") == kind), None)
    if current:
        cfg.upsert_service({**current, "api_key": api_key, "url": current.get("url") or base})
    else:
        cfg.upsert_service({"name": name, "type": kind, "url": base, "api_key": api_key})


def radio_settings(reelix_admin, found, country="GB"):
    """Points Reelix's radio at Audiobookshelf's Radio library (DASH-181): the library, the folder as each app sees
    it, and the country and language searches prefer. Leaves the rest of Reelix's radio settings as they are."""
    library = (found or {}).get("radio_library")
    if not library:
        return []
    _, current = reelix_admin.call("GET", "/radio/settings")
    settings = {**(current or {}), "abs_library_id": library, "abs_library_folder": "/media/radio",
                "library_folder": "/data/media/radio", "country": (current or {}).get("country") or country,
                "language": (current or {}).get("language") or "en"}
    reelix_admin.call("PUT", "/radio/settings", settings)
    return ["Reelix's radio goes into Audiobookshelf's Radio library"]
