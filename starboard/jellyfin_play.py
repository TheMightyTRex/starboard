"""Play in Jellyfin (DASH-480): a Play link beside each film and episode in the Library that opens it in Jellyfin's
web player, in a new tab.

The address is the one the owner gave Starboard for people's browsers: the Jellyfin app's "Address to open in your
browser" at home, and its "Outside address" away from home. Never the address Starboard itself uses (such as
http://127.0.0.1:8096 or http://host.docker.internal:8096), which a browser on another computer cannot open. With no
address for browsers, the Library says where to add one instead of showing a link that fails.

Jellyfin's ids come from what the Library already reads:
- an item page asks Jellyfin for the film or series once already, for watched or not (watched.py), and keeps the id;
- the Films wall keeps each film's Jellyfin id in its index, found while the index is built (library.build_and_write,
  in its short-lived process) with one paged list of Jellyfin's films, matched by TMDB id, then IMDb id.
So no row asks Jellyfin anything, and nothing runs while nobody uses the Library.

The link opens the item's page in Jellyfin's web app (<address>/web/#/details?id=<id>), whose Play button starts it.
Jellyfin 10.11 and 12 have no address that starts playing: their #/video page only shows what is playing already,
and goes back when nothing is (checked on 10.11.11 and 12.4).
"""

import ipaddress
import json
import os
import re
import urllib.parse

# Hosts only Starboard or a container can reach: never shown to a browser.
INSIDE_HOSTS = {"localhost", "host.docker.internal", "gateway.docker.internal", "jellyfin", "0.0.0.0"}
ID_RE = re.compile(r"^[0-9a-f]{32}$")


def for_browsers(url):
    """True when url is an address a browser on another computer could open (not loopback or a container's name)."""
    try:
        host = (urllib.parse.urlsplit(str(url or "")).hostname or "").lower()
    except ValueError:
        return False
    if not host or host in INSIDE_HOSTS or host.endswith(".docker.internal"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (ip.is_loopback or ip.is_unspecified or ip.is_link_local)


def app(services):
    """The Jellyfin app Starboard reads, or None."""
    return next((s for s in services or [] if s.get("type") == "jellyfin" and s.get("enabled", True)
                 and s.get("url") and s.get("api_key")), None)


def address(services):
    """What the browser needs to make Play links: {"app": the Jellyfin app's id, "home": its address for browsers at
    home or "", "outside": its outside address or ""}. "home" and "outside" both empty means none is set yet, and
    the page says where to add one. None when Starboard has no Jellyfin app with a key."""
    jf = app(services)
    if not jf:
        return None
    clean = lambda u: str(u or "").strip().rstrip("/") if for_browsers(u) else ""  # noqa: E731
    return {"app": jf.get("id", ""), "home": clean(jf.get("link")), "outside": clean(jf.get("outside_link"))}


def web_link(base, item_id):
    """The address that opens an item in Jellyfin's web app."""
    return f"{base.rstrip('/')}/web/#/details?id={item_id}"


def _saved_app(data_dir):
    """The Jellyfin app from the settings file, read only (the running Starboard owns it), for the index build's
    short-lived process."""
    try:
        with open(os.path.join(data_dir, "config.json"), encoding="utf-8") as f:
            return app(json.load(f).get("services"))
    except (OSError, ValueError, AttributeError):
        return None


def film_ids(jf):
    """{("tmdb", id) or ("imdb", id): Jellyfin id} for every film in Jellyfin: one list, 1,000 films a page, with only
    the provider ids (no pictures or watched data)."""
    from . import migrate
    out = {}
    params = {"Recursive": "true", "IncludeItemTypes": "Movie", "Fields": "ProviderIds", "EnableImages": "false",
              "EnableUserData": "false", "EnableTotalRecordCount": "true"}
    for page in migrate._item_pages(jf, "/Items", params):
        for it in page:
            jid = str(it.get("Id") or "")
            if not ID_RE.match(jid):
                continue
            ids = {k.lower(): str(v) for k, v in (it.get("ProviderIds") or {}).items() if v}
            for kind in ("tmdb", "imdb"):
                if ids.get(kind):
                    out.setdefault((kind, ids[kind]), jid)
    return out


def film_ids_for_index(data_dir):
    """film_ids() for the Library's index build, or {} when there is no Jellyfin or it does not answer (the index is
    still written; the wall shows no Play links until the next build)."""
    jf = _saved_app(data_dir)
    if not jf:
        return {}
    from . import logs, services
    try:
        return film_ids(jf)
    except (services.ServiceError, OSError, ValueError) as e:
        logs.detail("library", f"Jellyfin's films not read for Play links: {e}")
        return {}


def match(ids, tmdb=None, imdb=None):
    """The Jellyfin id for a film from film_ids(), by TMDB id then IMDb id, or ""."""
    return (tmdb and ids.get(("tmdb", str(tmdb)))) or (imdb and ids.get(("imdb", str(imdb)))) or ""
