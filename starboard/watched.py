"""Watched or not watched, from Jellyfin (DASH-276): each film, episode, season and series in the Library shows
whether you have watched it, with Mark as watched and Mark as not watched. Starboard has one sign-in, so "you" is
one Jellyfin user: the one chosen in Settings, Jellyfin (Your Jellyfin user), or else Jellyfin's first admin, which
is the account Starboard made when it set Jellyfin up. Items are matched by their TMDB id, as Reelix knows them."""
import re
import urllib.parse

from . import migrate, services

ID_RE = re.compile(r"^[0-9a-f]{32}$")


def _server(cfg):
    """The adapter of the media server in use when it is not Jellyfin (DASH-566): Plex and Emby answer through their own
    adapters. (None, False) with no media server in use, so nothing is drawn; (None, True) for Jellyfin, handled below."""
    from . import mediaserver
    one = mediaserver.active(cfg.data)
    if one is None:
        return None, False
    return (None, True) if one.id == "jellyfin" else (one, True)


def _who(cfg, one):
    wanted = str((cfg.data.get("extras") or {}).get("media_user") or "")
    return services.cached(f"ms-who-{one.id}", 600, lambda: one.watched_user(cfg.data["services"], wanted))


def _jf(cfg):
    return migrate.jellyfin_app(cfg.data["services"])


def user(cfg, jf=None):
    """(id, name) of the Jellyfin user Starboard shows watched status for, or None."""
    jf = jf or _jf(cfg)
    if not jf:
        return None
    users = services.cached("jellyfin-users", 600, lambda: migrate._mb(jf, "/Users", timeout=10) or [])
    want = (cfg.data.get("extras") or {}).get("jellyfin_user", "")
    found = next((u for u in users if u.get("Name") == want), None) if want else None
    found = found or next((u for u in users if (u.get("Policy") or {}).get("IsAdministrator")), None) or (users[0] if users else None)
    return (found["Id"], found["Name"]) if found else None


def _find(jf, uid, kind, tmdb):
    q = urllib.parse.urlencode({"userId": uid, "Recursive": "true", "IncludeItemTypes": kind,
                                "AnyProviderIdEquals": f"Tmdb.{tmdb}", "Fields": "ProviderIds", "Limit": 5, "enableImages": "false"})
    items = (migrate._mb(jf, f"/Items?{q}", timeout=10) or {}).get("Items") or []
    # Jellyfin's match on provider ids is loose on some versions: keep only the exact TMDB id.
    return next((i for i in items if str((i.get("ProviderIds") or {}).get("Tmdb", "")) == str(tmdb)), None)


def film(cfg, tmdb):
    """{"id", "watched"} for a film, or None when Jellyfin is not set up or does not have it."""
    one, on = _server(cfg)
    if not on:
        return None
    if one:
        if "watched" not in one.capabilities or not tmdb:
            return None
        try:
            who = _who(cfg, one)
            return one.watched_film(cfg.data["services"], who, tmdb) if who else None
        except (services.ServiceError, ValueError):
            return None
    jf = _jf(cfg)
    who = user(cfg, jf) if jf and tmdb else None
    if not who:
        return None
    try:
        it = _find(jf, who[0], "Movie", tmdb)
    except services.ServiceError:
        return None
    return {"id": it["Id"], "watched": bool((it.get("UserData") or {}).get("Played")), "user": who[1]} if it else None


def series(cfg, tmdb):
    """{"id", "episodes": {(season, episode): {"id", "watched"}}} for a series, or None."""
    one, on = _server(cfg)
    if not on:
        return None
    if one:
        if "watched" not in one.capabilities or not tmdb:
            return None
        try:
            who = _who(cfg, one)
            return one.watched_series(cfg.data["services"], who, tmdb) if who else None
        except (services.ServiceError, ValueError):
            return None
    jf = _jf(cfg)
    who = user(cfg, jf) if jf and tmdb else None
    if not who:
        return None
    try:
        s = _find(jf, who[0], "Series", tmdb)
        if not s:
            return None
        q = urllib.parse.urlencode({"userId": who[0], "Fields": "UserData", "enableImages": "false"})
        eps = (migrate._mb(jf, f"/Shows/{s['Id']}/Episodes?{q}", timeout=15) or {}).get("Items") or []
    except services.ServiceError:
        return None
    out = {}
    for e in eps:
        if e.get("ParentIndexNumber") is not None and e.get("IndexNumber") is not None:
            out[(int(e["ParentIndexNumber"]), int(e["IndexNumber"]))] = {"id": e["Id"], "watched": bool((e.get("UserData") or {}).get("Played"))}
    return {"id": s["Id"], "episodes": out, "user": who[1]}


def mark(cfg, ids, watched):
    """Marks Jellyfin items (a film, episodes, or a season's or series' own item) watched or not, for the user."""
    one, on = _server(cfg)
    if one or not on:
        if not one or "watched" not in one.capabilities:
            raise ValueError("The media server in use cannot mark things as watched through Starboard")
        who = _who(cfg, one)
        if not who:
            raise ValueError(f"Add {one.name} with its {'token' if one.id == 'plex' else 'key'} in Settings, Manage apps, to show what you have watched")
        ids = [i for i in ids or [] if isinstance(i, str)][:500]
        if not ids:
            raise ValueError("Nothing to mark")
        return one.mark(cfg.data["services"], who, ids, watched)
    jf = _jf(cfg)
    who = user(cfg, jf) if jf else None
    if not who:
        raise ValueError("Add Jellyfin with its API key in Settings, Manage apps, to show what you have watched")
    ids = [i for i in ids or [] if isinstance(i, str) and ID_RE.match(i)][:500]
    if not ids:
        raise ValueError("Nothing to mark")
    for i in ids:
        migrate._mb(jf, f"/UserPlayedItems/{i}?{urllib.parse.urlencode({'userId': who[0]})}", "POST" if watched else "DELETE", timeout=15)
    return len(ids)
