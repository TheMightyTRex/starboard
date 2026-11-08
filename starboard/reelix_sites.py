"""Sites to search (DASH-155), searches through the VPN (DASH-133) and Jellyfin and Audiobookshelf in Reelix (DASH-156).

Used by both set-ups (the browser's Install apps and the terminal set-up ask the same question, in the same place)
and by Settings, Reelix. The set-ups run before Reelix does, so they offer a short list of Reelix's built-in public
sites (below, checked against Reelix's own list by tests/test_reelix_settings.py) and your own Torznab or Newznab
address. Nothing is added unless the person chooses it. Settings, Reelix offers every site Reelix knows.

Searches through the VPN: in the old stack Prowlarr ran inside Gluetun, so its searches left through the VPN. Reelix
runs on its own (so the library and the pages answer when the VPN is down), and sends only its searches through
Gluetun's HTTP proxy (http://gluetun:8888), as on the owner's server since 8 November 2026. When the VPN is down,
searches fail rather than leave from the home address. Gluetun's proxy is turned on in the stack (stack.APPS).
8 November 2026.
"""
import json
import os
import re
import urllib.parse

from . import reelix_setup

# Reelix's built-in public sites offered in the set-ups: general, English-language, no account needed, from
# web/reelix-sites.json (the browser set-up reads the same file). Each is (Reelix's implementation id, its name, what
# it lists). None is ticked unless the person ticks it.
def _read_list():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "reelix-sites.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_LIST = _read_list()
SUGGESTED = [(s["id"], s["name"], s["lists"]) for s in _LIST["sites"]]
WORDS = _LIST["words"]  # the step's words, the same in both set-ups
SUGGESTED_IDS = {s[0] for s in SUGGESTED}
OWN_KINDS = {"torznab": "Torznab (torrents)", "newznab": "Newznab (Usenet)"}
PROXY = {"kind": "http", "host": "gluetun", "port": 8888}
FLARESOLVERR = "http://gluetun:8191"
# Inside the stack, Reelix reaches the media servers by their names, on their own ports (not the ones on this computer).
MEDIA_SERVERS = {"jellyfin": ("Jellyfin", 8096), "audiobookshelf": ("Audiobookshelf", 80)}
_ID = re.compile(r"^definition:[A-Za-z0-9._-]{1,80}$")


def clean_choice(sites):
    """The sites chosen, checked: {"builtin": [ids], "own": [{"kind", "url", "api_key", "name"}]}. Raises ValueError
    with the problem. An empty choice is allowed: nothing is added."""
    sites = sites if isinstance(sites, dict) else {}
    builtin = []
    for i in sites.get("builtin") or []:
        i = str(i)
        if not _ID.match(i):
            raise ValueError(f"{i[:60]} is not one of Reelix's sites")
        if i not in builtin:
            builtin.append(i)
    own = []
    for o in sites.get("own") or []:
        if not isinstance(o, dict):
            continue
        kind = str(o.get("kind") or "torznab")
        if kind not in OWN_KINDS:
            raise ValueError("Choose Torznab or Newznab")
        url = str(o.get("url") or "").strip()
        if not url:
            continue
        parts = urllib.parse.urlparse(url)
        if parts.scheme not in ("http", "https") or not parts.netloc or any(c in url for c in " \n\r\t"):
            raise ValueError("Enter the site's address, starting http:// or https://")
        name = str(o.get("name") or "").strip() or parts.hostname or "My site"
        own.append({"kind": kind, "url": url[:2000], "api_key": str(o.get("api_key") or "").strip()[:500], "name": name[:100]})
    return {"builtin": builtin[:60], "own": own[:10]}


def describe(choice):
    """The chosen sites in words, for the Check step of both set-ups (never the key)."""
    names = {i: n for i, n, _ in SUGGESTED}
    words = [names.get(i, i.split(":", 1)[-1]) for i in choice.get("builtin") or []]
    words += [f"{o['name']} ({'Newznab' if o['kind'] == 'newznab' else 'Torznab'})" for o in choice.get("own") or []]
    return ", ".join(words) or "None yet: add them later in Settings, Reelix"


def _defaults(fields):
    return {f["name"]: f["default"] for f in fields if "default" in f and f.get("default") is not None}


def add_sites(reelix, choice):
    """Adds the chosen sites to Reelix, each tested once (a failed test is said, not fatal). Sites Reelix has
    already are left as they are. Returns what was done, in words."""
    if not choice.get("builtin") and not choice.get("own"):
        return []
    _, schemas = reelix.call("GET", "/indexers/schema", timeout=60)
    by_id = {(e.get("schema") or {}).get("implementation"): e.get("schema") or {} for e in schemas or []}
    _, have = reelix.call("GET", "/indexers")
    have = have or []
    done = []
    wanted = [(i, by_id.get(i), {}) for i in choice.get("builtin") or []]
    for o in choice.get("own") or []:
        settings = {"base_url": o["url"]}
        if o.get("api_key"):
            settings["api_key"] = o["api_key"]
        wanted.append((o["kind"], by_id.get(o["kind"]), settings, o["name"]))
    for entry in wanted:
        impl, schema, settings = entry[0], entry[1], entry[2]
        name = entry[3] if len(entry) > 3 else (schema or {}).get("name", impl)
        if not schema:
            done.append(f"{impl.split(':', 1)[-1]} is not in this Reelix's list of sites, so it was not added")
            continue
        if impl.startswith("definition:") and any(h.get("implementation") == impl for h in have):
            continue
        if not impl.startswith("definition:") and any((h.get("settings") or {}).get("base_url") == settings.get("base_url") for h in have):
            continue
        body = {"implementation": impl, "name": name, "enabled": True, "priority": 25, "tags": [],
                "settings": {**_defaults(schema.get("fields") or []), **settings}}
        try:
            _, made = reelix.call("POST", "/indexers", body)
        except reelix_setup.ReelixError as e:
            why = str(e)
            if "blocked address" in why:
                why = ("Reelix does not reach addresses on your own network unless you allow it. Activate Addresses on "
                       "your network in Settings, Reelix, Sites to search, then add it again")
            done.append(f"{name} was not added: {why}")
            continue
        try:
            _, result = reelix.call("POST", f"/indexers/{made['id']}/test", {}, timeout=60, ok=(200, 400, 422))
            ok = bool((result or {}).get("ok"))
            done.append(f"Added {name}" + ("" if ok else f" (its test did not pass yet: {(result or {}).get('message') or 'no answer'})"))
        except (reelix_setup.ReelixError, KeyError, TypeError):
            done.append(f"Added {name}")
    return done


# Searches through the VPN ------------------------------------------------------------------------------------------

def vpn_available(data_dir):
    """Gluetun is in Starboard's stack, so Reelix's searches can go through it."""
    from . import stack
    try:
        return "gluetun" in (stack.chosen_keys(data_dir) or [])
    except (OSError, ValueError):
        return False


def _flaresolverr_here(data_dir):
    from . import stack
    try:
        return "flaresolverr" in (stack.chosen_keys(data_dir) or [])
    except (OSError, ValueError):
        return False


def through_vpn(settings):
    p = (settings or {}).get("proxy") or {}
    return p.get("host") == PROXY["host"] and int(p.get("port") or 0) == PROXY["port"]


def search_state(reelix, data_dir):
    """Reelix's search settings, as Starboard shows them: through the VPN or not, FlareSolverr, and how often."""
    _, s = reelix.call("GET", "/settings/indexers")
    s = s or {}
    proxy = s.get("proxy") or None
    return {"vpn_available": vpn_available(data_dir), "through_vpn": through_vpn(s),
            "proxy": f"{proxy.get('kind', 'http')}://{proxy.get('host')}:{proxy.get('port')}" if proxy else None,
            "flaresolverr": s.get("flaresolverr_url") or None, "rss_minutes": s.get("rss_interval_minutes"),
            "allow_private": bool(s.get("allow_private_addresses"))}


def set_private(reelix, on):
    """Lets Reelix reach addresses on your own network (your own Torznab or Newznab site at home), or not. Off by
    default in Reelix, so a site cannot point it at the other apps on this computer."""
    _, s = reelix.call("GET", "/settings/indexers")
    reelix.call("PUT", "/settings/indexers", {**(s or {}), "allow_private_addresses": bool(on)})
    return "Reelix may reach addresses on your network" if on else "Reelix reaches only addresses on the internet"


def set_vpn(reelix, data_dir, on):
    """Sends Reelix's searches through Gluetun's proxy (and FlareSolverr through Gluetun when it is installed), or
    stops doing so. Private addresses are allowed while on, because Gluetun is one."""
    _, s = reelix.call("GET", "/settings/indexers")
    s = dict(s or {})
    if on:
        s["proxy"] = dict(PROXY)
        s["allow_private_addresses"] = True
        if _flaresolverr_here(data_dir) and not s.get("flaresolverr_url"):
            s["flaresolverr_url"] = FLARESOLVERR
    else:
        s["proxy"] = None
    reelix.call("PUT", "/settings/indexers", s)
    return "Reelix searches through the VPN" if on else "Reelix searches from this computer's own address"


# Jellyfin and Audiobookshelf ------------------------------------------------------------------------------------

def _key_of(services, kind):
    return next((s for s in services if s.get("type") == kind and s.get("api_key")), None)


def server_url(service, kind, data_dir):
    """The address Reelix uses: the app's name inside the stack when Starboard installed it (or when the dashboard
    reaches it on this computer, which a container cannot), else the dashboard's address for it."""
    from . import stack
    name, port = MEDIA_SERVERS[kind]
    try:
        here = kind in (stack.chosen_keys(data_dir) or [])
    except (OSError, ValueError):
        here = False
    url = str((service or {}).get("url") or "").rstrip("/")
    host = urllib.parse.urlparse(url).hostname or ""
    if here or not url or host in ("127.0.0.1", "localhost", "::1"):
        return f"http://{kind}:{port}"
    return url


def media_server_offers(services, data_dir, items):
    """For Jellyfin and Audiobookshelf: whether Starboard has its key, whether Reelix has it already, and where."""
    out = []
    for kind, (name, _) in MEDIA_SERVERS.items():
        svc = _key_of(services, kind)
        there = next((i for i in items if i.get("implementation") == kind), None)
        url = (there.get("settings") or {}).get("url") if there else (server_url(svc, kind, data_dir) if svc else None)
        out.append({"app": kind, "name": name, "has_key": bool(svc), "connected": bool(there),
                    "id": there.get("id") if there else None, "url": url, "error": there.get("error") if there else None})
    return out


def connect_media_servers(reelix, services, data_dir, only=None):
    """Connects Reelix to Jellyfin and Audiobookshelf with the keys Starboard already has, so new files show in them
    at once. One Reelix has already is left as it is. Returns what was done, in words."""
    if not any(_key_of(services, k) for k in MEDIA_SERVERS if not only or k == only):
        return []  # Starboard has neither key yet: Settings, Reelix, Media servers offers it once it has
    _, have = reelix.call("GET", "/mediaservers")
    have = have or []
    done = []
    for kind, (name, _) in MEDIA_SERVERS.items():
        if only and kind != only:
            continue
        svc = _key_of(services, kind)
        if not svc:
            continue
        if any(i.get("implementation") == kind for i in have):
            continue
        settings = {"url": server_url(svc, kind, data_dir), "api_key": svc["api_key"]}
        try:
            _, made = reelix.call("POST", "/mediaservers", {"implementation": kind, "name": name, "enabled": True,
                                                            "priority": 25, "tags": [], "settings": settings})
        except reelix_setup.ReelixError as e:
            done.append(f"{name} is not connected to Reelix yet ({e})")
            continue
        try:
            _, result = reelix.call("POST", f"/mediaservers/{made['id']}/test", {}, timeout=30, ok=(200, 400, 422))
            ok = bool((result or {}).get("ok"))
        except (reelix_setup.ReelixError, KeyError, TypeError):
            ok, result = False, {}
        done.append(f"Connected Reelix to {name}" + ("" if ok else f", but its test did not pass: {(result or {}).get('message') or 'no answer'}"))
    return done


def after_install(app, password, wait=True):
    """Install apps ran again with a Reelix that is set up already: once the apps have started, connects Reelix to
    Jellyfin and Audiobookshelf with the keys Starboard has, signing in with the password just checked (the same as
    Reelix's when Starboard set Reelix up). Says what happened in the log; a wrong password only says where to do it."""
    import threading
    import time
    from . import logs, reelix_admin, stack
    services = app.config.data["services"]
    base = stack.reelix_url(app.data_dir)
    if not base or not any(_key_of(services, k) for k in MEDIA_SERVERS):
        return None

    def run():
        began = time.time()
        while wait and not stack.job().get("finished"):
            if time.time() - began > 3600:
                return
            time.sleep(5)
        try:
            reelix_setup.wait_until_up(base, seconds=300)
            with reelix_admin.Visit(base, password) as reelix:
                done = connect_media_servers(reelix, services, app.data_dir)
            for line in done:
                logs.event("info", "install apps", line)
        except reelix_admin.WrongPassword:
            logs.event("info", "install apps", "Reelix's password is not the same as Starboard's, so Jellyfin and "
                       "Audiobookshelf were not connected to it. Connect them in Settings, Reelix, Media servers")
        except (reelix_setup.ReelixError, OSError, ValueError) as e:
            logs.event("warning", "install apps", f"Jellyfin and Audiobookshelf are not connected to Reelix yet ({e}). "
                       "Connect them in Settings, Reelix, Media servers")
    thread = threading.Thread(target=run, name="reelix-media-servers", daemon=True)
    thread.start()
    return thread
