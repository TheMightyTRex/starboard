"""First runs of the apps Install apps starts, done by Starboard over each app's own API, so nobody opens their pages
(DASH-179, DASH-180, DASH-234). Each step is safe to run again: an app already set up is signed in to and only what
is missing is added.

- Jellyfin: the start-up wizard (/Startup/*), the Films, Series and Music libraries, and an API key for Starboard.
- Audiobookshelf: the root user (/init), the Audiobooks, Books and Radio libraries, and an API key for Starboard.
- Jellystat: its admin (/auth/createuser), Jellyfin's address and key (/auth/configSetup) and a key for Starboard
  (DASH-227).

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


def jellyfin_first_run(base, password, groups, country="GB", user=ADMIN, opener=None, graphics=None):
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
    if graphics in ("intel", "amd"):
        done += _jf_graphics(base, auth, graphics, opener)
    key = _jf_key(base, auth, opener)
    return key, done, {}


def _jf_graphics(base, auth, vendor, opener):
    """Hardware conversion with the graphics chip (DASH-82): Intel Quick Sync or AMD's VA-API, on the device Install
    apps passed through. Left alone when someone has already chosen a kind of hardware conversion."""
    current = _call(base, "GET", "/System/Configuration/encoding", headers=auth, opener=opener) or {}
    if current.get("HardwareAccelerationType") not in (None, "", "none"):
        return []
    kind = "qsv" if vendor == "intel" else "vaapi"
    _call(base, "POST", "/System/Configuration/encoding",
          {**current, "HardwareAccelerationType": kind, "VaapiDevice": "/dev/dri/renderD128", "EnableHardwareEncoding": True,
           "HardwareDecodingCodecs": ["h264", "hevc", "mpeg2video", "vc1", "vp8", "vp9", "av1"]}, headers=auth, opener=opener)
    return [f"Jellyfin converts video with the {'Intel' if vendor == 'intel' else 'AMD'} graphics chip"]


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


# Jellystat -------------------------------------------------------------------------------------------------------

def _keccak512(data):
    """Keccak-512 as CryptoJS.SHA3 makes it: Jellystat's own page sends the password this way, so Starboard must too.
    It is the Keccak before NIST's SHA-3 (padding 0x01, not 0x06), which hashlib does not offer."""
    rate, rounds = 72, 24
    rc = []
    r = 1
    for _ in range(rounds):
        c = 0
        for j in range(7):
            r = ((r << 1) ^ (0x71 if r & 0x80 else 0)) & 0xFF
            if r & 2:
                c |= 1 << ((1 << j) - 1)
        rc.append(c)
    rot = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
    mask = (1 << 64) - 1

    def rol(v, n):
        return ((v << n) | (v >> (64 - n))) & mask if n else v

    def permute(a):
        for rnd in range(rounds):
            c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
            d = [c[(x - 1) % 5] ^ rol(c[(x + 1) % 5], 1) for x in range(5)]
            a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
            b = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    b[y][(2 * x + 3 * y) % 5] = rol(a[x][y], rot[x][y])
            a = [[b[x][y] ^ (~b[(x + 1) % 5][y] & b[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
            a[0][0] ^= rc[rnd]
        return a

    msg = bytearray(data) + b"\x01"
    msg += b"\x00" * (-len(msg) % rate)
    msg[-1] |= 0x80
    state = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        block = msg[off:off + rate]
        for i in range(rate // 8):
            state[i % 5][i // 5] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        state = permute(state)
    out = b"".join(state[i % 5][i // 5].to_bytes(8, "little") for i in range(25))
    return out[:64].hex()


def jellystat_first_run(base, password, jellyfin_key, user=ADMIN, jellyfin_inside="http://jellyfin:8096", opener=None):
    """Makes Jellystat's admin when it has none, gives it Jellyfin's address (as Jellystat reaches it, inside the
    stack) and key, and returns (a Jellystat key for Starboard, lines of what was done)."""
    done = []
    hashed = _keccak512(password.encode())
    state = (_call(base, "GET", "/auth/isConfigured", opener=opener) or {}).get("state", 0)
    if not state:
        _call(base, "POST", "/auth/createuser", {"username": user, "password": hashed}, opener=opener)
        done.append(f"Set up Jellystat with the account {user} and your Starboard password")
    try:
        token = (_call(base, "POST", "/auth/login", {"username": user, "password": hashed}, opener=opener) or {}).get("token")
    except AppSetupError as e:
        raise AppSetupError("Jellystat was set up before with another account, so Starboard cannot sign in. Add "
                            f"Jellystat's API key in Settings, Apps, Manage apps ({e})") from None
    if not token:
        raise AppSetupError("Jellystat did not give Starboard a sign-in")
    auth = {"Authorization": f"Bearer {token}"}
    if (_call(base, "GET", "/auth/isConfigured", opener=opener) or {}).get("state", 0) < 2:
        if not jellyfin_key:
            raise AppSetupError("Jellyfin is not set up yet, so Jellystat has nothing to read")
        _call(base, "POST", "/auth/configSetup", {"JF_HOST": jellyfin_inside, "JF_API_KEY": jellyfin_key}, headers=auth, opener=opener)
        done.append("Connected Jellystat to Jellyfin")

    def find():
        keys = _call(base, "GET", "/api/keys", headers=auth, opener=opener) or []
        return next((k.get("key") for k in keys if isinstance(k, dict) and k.get("name") == KEY_NAME and k.get("key")), None)
    key = find()
    if not key:
        _call(base, "POST", "/api/keys", {"name": KEY_NAME}, headers=auth, opener=opener)
        key = find()
    if not key:
        raise AppSetupError("Jellystat did not make an API key for Starboard")
    return key, done, {}


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
    jellyfin_key = None
    for key, name, inside, run in apps:
        if key not in keys:
            continue
        base = stack.app_url(data_dir, key, inside)
        if not base:
            continue
        try:
            extra = {"country": country_from_tz(os.environ.get("TZ")) or "GB",
                     "graphics": stack.env_values(data_dir).get("GRAPHICS_VENDOR")} if key == "jellyfin" else {}
            api_key, lines, more = run(base, password, groups, opener=opener, **extra)
        except AppSetupError as e:
            done.append(f"{name} is not set up yet: {e}")
            continue
        done += lines
        if found is not None:
            found.update(more)
        _save_key(cfg, key, name, base, api_key)
        if key == "jellyfin":
            jellyfin_key = api_key
        log(f"{name} ready")
    # Jellystat, in the Full install (DASH-227): after Jellyfin, whose key it needs.
    base = stack.app_url(data_dir, "jellystat", 3000) if "jellystat" in keys else None
    if base:
        jellyfin_key = jellyfin_key or next((s.get("api_key") for s in cfg.data["services"] if s.get("type") == "jellyfin"), None)
        try:
            api_key, lines, _ = jellystat_first_run(base, password, jellyfin_key, opener=opener)
            done += lines
            _save_key(cfg, "jellystat", "Jellystat", base, api_key)
            log("Jellystat ready")
        except AppSetupError as e:
            done.append(f"Jellystat is not set up yet: {e}")
    # The download apps' sign-ins, made up by Install apps (DASH-184): saved on the dashboard so Downloads, download
    # hours and Reelix all use the same details, and shown on Apps behind the Starboard password.
    # qBittorrent answers Starboard with an API key (qBittorrent 5.2 and later), made here with its sign-in; Gluetun's
    # control server with the key Install apps made up (DASH-233).
    downloads = [("qbittorrent", "qBittorrent", 8080, lambda base: qbittorrent_key(base, stack.qbittorrent_password(data_dir), opener)
                  if stack.qbittorrent_password(data_dir) else None),
                 ("nzbget", "NZBGet", 6789, lambda base: stack.nzbget_key(data_dir)),
                 ("sabnzbd", "SABnzbd", stack.SABNZBD_PORT, lambda base: stack.sabnzbd_key(data_dir)),
                 ("slskd", "Soulseek (slskd)", 5030, lambda base: stack.slskd_key(data_dir)),
                 ("gluetun", "Gluetun", 8000, lambda base: stack.env_values(data_dir).get("GLUETUN_API_KEY"))]
    for key, name, inside, secret in downloads:
        base = stack.app_url(data_dir, key, inside) if key in keys else None
        if not base:
            continue
        try:
            value = secret(base)
        except AppSetupError as e:
            done.append(f"{name} is not on your apps with its key yet: {e}")
            continue
        if value:
            _save_key(cfg, key, name, base, value)
            done.append(f"Added {name} to your apps, with its key")
    return done


def qbittorrent_key(base, password, opener=None):
    """Signs in to qBittorrent with the sign-in Install apps made up and makes an API key for Starboard (qBittorrent
    5.2 and later); None from an older qBittorrent, which has no API keys."""
    import http.cookiejar
    jar = opener or urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def post(path, form=None):
        req = urllib.request.Request(f"{base}/api/v2/{path}", data=urllib.parse.urlencode(form or {}).encode(),
                                     headers={"Referer": base, "User-Agent": "Starboard"})
        with jar.open(req, timeout=15) as r:  # qBittorrent on this computer, from the stack Starboard wrote  # nosec B310
            return r.status, r.read(4000).decode("utf-8", "replace")
    try:
        status, text = post("auth/login", {"username": "admin", "password": password})
        if not (status == 204 or (status == 200 and "Ok" in text)):
            raise AppSetupError("it did not accept the sign-in Starboard made up")
        status, text = post("app/rotateAPIKey")
        return (json.loads(text) or {}).get("apiKey") or None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # qBittorrent before 5.2
        raise AppSetupError(f"it answered {e.code}") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise AppSetupError("Starboard could not reach it") from None


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


# Bazarr -----------------------------------------------------------------------------------------------------------

def bazarr_connect(base, bazarr_key, reelix_key, opener=None):
    """Points Bazarr's Sonarr and Radarr connections at Reelix's Sonarr- and Radarr-style addresses, by its name on
    the stack, with Starboard's manager key (DASH-182). Bazarr's own key is the one Install apps made up."""
    fields = {"settings-general-use_sonarr": "true", "settings-general-use_radarr": "true"}
    for kind in ("sonarr", "radarr"):
        fields.update({f"settings-{kind}-ip": "reelix", f"settings-{kind}-port": "7700", f"settings-{kind}-base_url": f"/{kind}",
                       f"settings-{kind}-apikey": reelix_key, f"settings-{kind}-ssl": "false"})
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(base.rstrip("/") + "/api/system/settings", data=data, method="POST",
                                 headers={"X-API-KEY": bazarr_key, "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Starboard"})
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=60) as r:  # Bazarr's address on this computer  # nosec B310
            r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AppSetupError("Bazarr has its own settings from before, with another API key. Connect it to Reelix in Bazarr, "
                                "Settings, Sonarr and Radarr: host reelix, port 7700, base URL /sonarr or /radarr") from None
        raise AppSetupError(f"Bazarr said {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        # Bazarr saves first and then tests the connection, which can take longer than the wait: read it back.
        if not _bazarr_points_at_reelix(base, bazarr_key, opener):
            raise AppSetupError(f"no answer from Bazarr: {getattr(e, 'reason', e)}") from None
    return ["Connected Bazarr to Reelix, for subtitles"]


def _bazarr_points_at_reelix(base, bazarr_key, opener=None):
    try:
        settings = _call(base, "GET", "/api/system/settings", headers={"X-API-KEY": bazarr_key}, opener=opener) or {}
    except AppSetupError:
        return False
    return all((settings.get(k) or {}).get("ip") == "reelix" for k in ("sonarr", "radarr"))
