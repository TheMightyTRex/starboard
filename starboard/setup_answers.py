"""The set-up's TMDB key, language of releases and Usenet server answers (DASH-178, DASH-189, DASH-183, DASH-247,
DASH-248): checked, tested, kept until the apps run, then written into Reelix and the Usenet app. Nobody opens
Reelix's, NZBGet's or SABnzbd's own pages for them.

The words are in web/setup-answers.json, which the browser set-up reads too, so both set-ups ask the same.
The Usenet password and the TMDB key wait in data/stack (only Starboard's user can read the files) until they are
written into the apps, then the files are removed.
"""
import json
import os
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(HERE, "web", "setup-answers.json"), encoding="utf-8") as _f:
    WORDS = json.load(_f)
LANGUAGES = [c["value"] for c in WORDS["language"]["choices"]]
USENET_FILE = "usenet-server.json"
HOST_RE = re.compile(r"^(?=.{1,253}$)([A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}$")


# TMDB --------------------------------------------------------------------------------------------------------------

def clean_tmdb(value):
    """A TMDB read access token (a long token starting eyJ) or API key (32 letters and numbers), or "" for none."""
    v = str(value or "").strip()
    if not v:
        return ""
    if re.fullmatch(r"[0-9a-f]{32}", v) or re.fullmatch(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+", v):
        return v
    raise ValueError("That does not look like a TMDB key. Paste the API Read Access Token or the API key from themoviedb.org, Settings, API")


def test_tmdb(value, opener=None):
    """Asks TMDB whether it accepts the key. Returns True, or raises ValueError with what TMDB said."""
    v = clean_tmdb(value)
    if not v:
        raise ValueError("Paste a TMDB key first")
    url = "https://api.themoviedb.org/3/configuration"
    headers = {"Accept": "application/json", "User-Agent": "Starboard"}
    if v.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {v}"
    else:
        url += "?" + urllib.parse.urlencode({"api_key": v})
    try:
        with (opener or urllib.request.build_opener()).open(urllib.request.Request(url, headers=headers), timeout=10) as r:  # TMDB's fixed https address  # nosec B310
            r.read(2000)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise ValueError("TMDB did not accept that key. Check you copied all of it") from None
        raise ValueError(f"TMDB answered {e.code}. Try again in a moment") from None
    except (urllib.error.URLError, OSError):
        raise ValueError("Starboard could not reach TMDB. Check this computer is online") from None


def tmdb_settings(value, current):
    """Reelix's /settings/metadata with the key in the right field, keeping the rest as it is."""
    v = clean_tmdb(value)
    out = dict(current or {})
    if v.startswith("eyJ"):
        out["tmdb_read_token"] = v
    elif v:
        out["tmdb_api_key"] = v
    return out


# Language of releases ----------------------------------------------------------------------------------------------

def clean_language(value):
    v = "" if value is None else str(value)
    if v not in LANGUAGES:
        raise ValueError("Choose English, the film's or series' own language, or any language")
    return v


def apply_language(reelix_admin, value):
    """Sets the required language on Reelix's film and series profiles (its own setting on each quality profile)."""
    lang = clean_language(value) or None
    _, profiles = reelix_admin.call("GET", "/qualityprofiles")
    changed = 0
    for p in profiles or []:
        if p.get("family", "video") != "video" or p.get("language") == lang:
            continue
        reelix_admin.call("PUT", f"/qualityprofiles/{p['id']}", {**p, "language": lang})
        changed += 1
    words = {"English": "English", "Original": "each film's or series' own language", None: "any language"}[lang]
    return [f"Reelix gets films and series in {words}"] if changed or lang else []


# Usenet server ------------------------------------------------------------------------------------------------------

def clean_usenet(server):
    """{host, port, ssl, username, password, connections} checked, or None when no server was typed."""
    s = server or {}
    host = str(s.get("host") or "").strip().lower()
    if not host:
        return None
    if not HOST_RE.match(host):
        raise ValueError("Type the server's address, such as news.example.com")
    use_ssl = bool(s.get("ssl", True))
    try:
        port = int(s.get("port") or (563 if use_ssl else 119))
        connections = int(s.get("connections") or 8)
    except (TypeError, ValueError):
        raise ValueError("The port and connections are numbers") from None
    if not 1 <= port <= 65535:
        raise ValueError("The port is a number from 1 to 65535, usually 563")
    if not 1 <= connections <= 100:
        raise ValueError("Connections is a number from 1 to 100")
    user = str(s.get("username") or "").strip()
    password = str(s.get("password") or "")
    if any(c in user + password for c in "\r\n") or len(user) > 200 or len(password) > 200:
        raise ValueError("The user name or password has a line break or is too long")
    return {"host": host, "port": port, "ssl": use_ssl, "username": user, "password": password, "connections": connections}


def test_usenet(server, timeout=10):
    """Signs in to the news server the way a Usenet app would (NNTP AUTHINFO). Returns True, or raises ValueError."""
    s = clean_usenet(server)
    if not s:
        raise ValueError("Type the server's address first")
    try:
        raw = socket.create_connection((s["host"], s["port"]), timeout=timeout)
    except OSError:
        raise ValueError(f"Starboard could not reach {s['host']} on port {s['port']}. Check the address and port") from None
    try:
        conn = ssl.create_default_context().wrap_socket(raw, server_hostname=s["host"]) if s["ssl"] else raw
        f = conn.makefile("rwb")

        def say(line):
            f.write(line.encode() + b"\r\n")
            f.flush()
            return f.readline(512).decode("utf-8", "replace").strip()
        greeting = f.readline(512).decode("utf-8", "replace").strip()
        if not greeting.startswith(("200", "201")):
            raise ValueError(f"The server did not greet Starboard as a news server ({greeting[:60]})")
        if s["username"]:
            first = say(f"AUTHINFO USER {s['username']}")
            if first.startswith("381"):
                first = say(f"AUTHINFO PASS {s['password']}")
            if not first.startswith("281"):
                raise ValueError("The server did not accept the user name and password")
        say("QUIT")
        return True
    except ssl.SSLError:
        raise ValueError("The encrypted connection did not work. Check the port (usually 563) or try without encryption") from None
    except OSError:
        raise ValueError("The server stopped answering. Try again, or check the port") from None
    finally:
        try:
            raw.close()
        except OSError:
            pass


def save_usenet(data_dir, server):
    """Keeps the server until the Usenet app runs (only Starboard's user can read the file)."""
    from . import stack
    s = clean_usenet(server)
    target = os.path.join(stack.folder(data_dir), USENET_FILE)
    if not s:
        try:
            os.remove(target)
        except FileNotFoundError:
            pass
        return
    os.makedirs(os.path.dirname(target), mode=0o700, exist_ok=True)
    with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(s, f)


def apply_usenet(data_dir, opener=None):
    """Writes the saved server into NZBGet (its settings, through its own API) or SABnzbd (its API), then removes the
    file. Returns lines of what was done; a problem is a line too, and the file stays for the next try."""
    from . import reelix_setup, stack, usenet_move
    path = os.path.join(stack.folder(data_dir), USENET_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            s = clean_usenet(json.load(f))
    except (OSError, ValueError):
        return []
    if not s:
        return []
    keys = stack.chosen_keys(data_dir) or []
    sab = {"host": s["host"], "port": s["port"], "ssl": "1" if s["ssl"] else "0", "username": s["username"],
           "password": s["password"], "connections": s["connections"], "enable": "1", "displayname": s["host"]}
    try:
        if "nzbget" in keys:
            rpc = reelix_setup.nzbget_rpc(stack.nzbget_key(data_dir), base=stack.app_url(data_dir, "nzbget", 6789) or "http://127.0.0.1:6789", opener=opener)
            usenet_move.write_to_nzbget(rpc, [sab])
            app = "NZBGet"
        elif "sabnzbd" in keys and stack.sabnzbd_key(data_dir):
            base = stack.app_url(data_dir, "sabnzbd", stack.SABNZBD_PORT) or f"http://127.0.0.1:{stack.SABNZBD_PORT}"
            fields = {"mode": "set_config", "section": "servers", "name": s["host"], "host": s["host"], "port": s["port"],
                      "ssl": sab["ssl"], "username": s["username"], "password": s["password"], "connections": s["connections"],
                      "enable": "1", "apikey": stack.sabnzbd_key(data_dir), "output": "json"}
            req = urllib.request.Request(f"{base}/api?{urllib.parse.urlencode(fields)}", headers={"User-Agent": "Starboard"})
            with (opener or urllib.request.build_opener()).open(req, timeout=20) as r:  # SABnzbd's address on this computer  # nosec B310
                r.read(2000)
            app = "SABnzbd"
        else:
            return []
    except (reelix_setup.ReelixError, OSError, ValueError) as e:
        return [f"Your Usenet server is not in the Usenet app yet ({e}). Starboard tries again next time it sets up the apps"]
    try:
        os.remove(path)
    except OSError:
        pass
    return [f"Added your Usenet server to {app}"]


# NordVPN's WireGuard key (DASH-233) ----------------------------------------------------------------------------------

NORDVPN_ADDRESS = "10.5.0.2/32"  # the same WireGuard address for every NordVPN account (Gluetun's wiki, NordVPN)


def nordvpn_key(token, opener=None):
    """NordVPN's WireGuard (NordLynx) private key from an access token made in the account's Nord Account page,
    Services, NordVPN, Manual setup. Returns (key, address), or raises ValueError in words."""
    import base64
    t = str(token or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9]{20,128}", t):
        raise ValueError("Paste the access token from Nord Account, NordVPN, Manual setup")
    auth = base64.b64encode(f"token:{t}".encode()).decode()
    req = urllib.request.Request("https://api.nordvpn.com/v1/users/services/credentials",
                                 headers={"Authorization": f"Basic {auth}", "Accept": "application/json", "User-Agent": "Starboard"})
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=15) as r:  # NordVPN's fixed https address  # nosec B310
            data = json.loads(r.read(20000))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ValueError("NordVPN did not accept that token. Make a new one and paste all of it") from None
        raise ValueError(f"NordVPN answered {e.code}. Try again in a moment") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise ValueError("Starboard could not reach NordVPN. Check this computer is online") from None
    key = (data or {}).get("nordlynx_private_key")
    if not key:
        raise ValueError("NordVPN did not send a WireGuard key for this account")
    return key, NORDVPN_ADDRESS
