"""Moving to Jellyfin: watch history from Plex, Emby or another Jellyfin, and defaults for every Jellyfin user.

Watch history (Settings, Apps, Jellyfin, Import watch history):
1. Read it from one of these, into data/imports/history.json (one list of films and episodes per account):
   - a Plex database file (com.plexapp.plugins.library.db), uploaded or put in data/imports: every account;
   - a Plex server, with its token: the token owner's account;
   - an Emby or Jellyfin server, with an API key: every user;
   - a history file Starboard (or the old launcher) wrote before.
2. Match each account to a Jellyfin user (the same name is matched for you).
3. Apply: films by TMDB or IMDb ID, episodes by their show's TVDB, TMDB or IMDb ID with season and episode.
   Watched becomes watched (with the original date); part-watched becomes a resume point. Each item is applied
   once (data/imports/applied.json), so a change made in Jellyfin later stays. With Keep applying on, it runs
   every hour, so history lands as the media arrives.

User defaults: every hour, each Jellyfin user (new ones too) gets the defaults below, unless they chose
something else themselves.

Jellyfin is reached with the API key of the Jellyfin app in Manage apps.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .services import ServiceError, USER_AGENT, _fetch

DEFAULT_PREFS = {"landing-livetv": "guide"}  # Live TV opens on the Guide tab
DEFAULT_WORDS = {"landing-livetv": "Live TV opens on the Guide"}


def folder(data_dir):
    path = os.path.join(data_dir, "imports")
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path, data):
    tmp = path + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None


# Jellyfin (and Emby, which speaks the same language) ----------------------------------------

def _mb(service, path, method="GET", body=None, timeout=120):
    # Newer Jellyfin takes the key only in Authorization; Emby takes X-Emby-Token. Both are sent.
    key = service.get("api_key", "")
    headers = {"Authorization": f'MediaBrowser Token="{key}"', "X-Emby-Token": key,
               "Accept": "application/json", "User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(service["url"].rstrip("/") + path, data=data, headers=headers, method=method)
    return _fetch(service, req, timeout)


def _all_items(service, path, params):
    """Every item from an /Items query, a page of 1,000 at a time, so a big library never arrives in one reply."""
    out, start = [], 0
    while True:
        q = urllib.parse.urlencode({**params, "StartIndex": start, "Limit": 1000})
        page = _mb(service, f"{path}?{q}") or {}
        items = page.get("Items") or []
        out.extend(items)
        start += len(items)
        if not items or start >= (page.get("TotalRecordCount") or 0):
            return out


def jellyfin_app(services):
    return next((s for s in services if s["type"] == "jellyfin" and s.get("enabled", True) and s.get("url") and s.get("api_key")), None)


def jellyfin_users(service):
    return [u["Name"] for u in _mb(service, "/Users") or []]


def _norm(ids):
    return {k.lower(): str(v) for k, v in (ids or {}).items() if k.lower() in ("tmdb", "imdb", "tvdb") and v}


# Reading history ---------------------------------------------------------------------------

def read_plex_db(path):
    """Every account's history from a copy of Plex's database. Opened read-only."""
    import sqlite3  # loaded only for this import
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    q = lambda s, *a: db.execute(s, a).fetchall()
    ids = {}
    for mid, tag in q("select tg.metadata_item_id, t.tag from taggings tg join tags t on t.id = tg.tag_id where t.tag_type = 314"):
        m = re.match(r"(tmdb|imdb|tvdb)://(.+)", tag or "")
        if m:
            ids.setdefault(mid, {})[m[1]] = m[2]
    for mid, guid in q("select id, guid from metadata_items where metadata_type in (1, 2)"):  # older Plex agents
        m = re.match(r"com\.plexapp\.agents\.(imdb|themoviedb|thetvdb)://([^/?]+)", guid or "")
        if m:
            ids.setdefault(mid, {}).setdefault({"imdb": "imdb", "themoviedb": "tmdb", "thetvdb": "tvdb"}[m[1]], m[2])
    items = {mid: (typ, title, year, idx, parent, guid) for mid, typ, title, year, idx, parent, guid in
             q('select id, metadata_type, title, year, "index", parent_id, guid from metadata_items where metadata_type in (1,2,3,4)')}
    by_guid = {}
    for mid, v in items.items():
        if v[0] in (1, 4):
            by_guid.setdefault(v[5], mid)
    duration = dict(q("select metadata_item_id, max(duration) from media_items group by metadata_item_id"))
    accounts = {}
    for aid, name in q("select id, name from accounts where name != ''"):
        entries = []
        for guid, count, offset, last in q("select guid, view_count, view_offset, last_viewed_at from metadata_item_settings "
                                           "where account_id = ? and (view_count > 0 or view_offset > 0)", aid):
            mid = by_guid.get(guid)
            if mid is None:
                continue
            typ, title, year, idx, parent, _ = items[mid]
            e = {"watched": (count or 0) > 0, "plays": count or 0, "last_watched": _iso(last),
                 "position_ms": offset or 0, "duration_ms": duration.get(mid) or 0}
            if typ == 1:
                e.update(type="movie", title=title, year=year, ids=ids.get(mid, {}))
            else:
                season = items.get(parent)
                show = items.get(season[4]) if season else None
                if not show:
                    continue
                e.update(type="episode", show=show[1], show_year=show[2], season=season[3], episode=idx, title=title,
                         ids=ids.get(season[4], {}))
            entries.append(e)
        if entries:
            accounts[name] = entries
    db.close()
    return accounts


def read_plex_server(url, token):
    """The token owner's history from a running Plex server."""
    service = {"name": "Plex", "url": url}

    def get(path):
        sep = "&" if "?" in path else "?"
        req = urllib.request.Request(f"{url.rstrip('/')}{path}{sep}X-Plex-Token={urllib.parse.quote(token)}",
                                     headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        return (_fetch(service, req, 180) or {}).get("MediaContainer") or {}

    def guids(m):
        out = {}
        for g in m.get("Guid") or []:
            k, _, v = (g.get("id") or "").partition("://")
            if k in ("tmdb", "imdb", "tvdb") and v:
                out[k] = v
        return out

    entries = []
    owner = (get("/myplex/account") or {}).get("username") or "Plex"
    for section in get("/library/sections").get("Directory") or []:
        if section.get("type") == "movie":
            for m in get(f"/library/sections/{section['key']}/all?type=1&includeGuids=1").get("Metadata") or []:
                if m.get("viewCount") or m.get("viewOffset"):
                    entries.append({"type": "movie", "title": m.get("title"), "year": m.get("year"), "ids": guids(m),
                                    "watched": bool(m.get("viewCount")), "plays": m.get("viewCount", 0),
                                    "last_watched": _iso(m.get("lastViewedAt")), "position_ms": m.get("viewOffset", 0),
                                    "duration_ms": m.get("duration", 0)})
        elif section.get("type") == "show":
            shows = {m["ratingKey"]: m for m in get(f"/library/sections/{section['key']}/all?type=2&includeGuids=1").get("Metadata") or []}
            for m in get(f"/library/sections/{section['key']}/all?type=4").get("Metadata") or []:
                if not (m.get("viewCount") or m.get("viewOffset")):
                    continue
                show = shows.get(m.get("grandparentRatingKey")) or {}
                entries.append({"type": "episode", "show": m.get("grandparentTitle"), "show_year": show.get("year"),
                                "season": m.get("parentIndex"), "episode": m.get("index"), "title": m.get("title"),
                                "ids": guids(show), "watched": bool(m.get("viewCount")), "plays": m.get("viewCount", 0),
                                "last_watched": _iso(m.get("lastViewedAt")), "position_ms": m.get("viewOffset", 0),
                                "duration_ms": m.get("duration", 0)})
    return {owner: entries} if entries else {}


def read_media_server(url, api_key, name="Emby"):
    """Every user's history from an Emby or Jellyfin server."""
    service = {"name": name, "url": url, "api_key": api_key}
    accounts = {}
    for user in _mb(service, "/Users") or []:
        uid = user["Id"]
        seen = {}
        for flt in ("IsPlayed", "IsResumable"):
            for it in _all_items(service, f"/Users/{uid}/Items", {"Recursive": "true", "IncludeItemTypes": "Movie,Episode", "Filters": flt,
                                                                  "Fields": "ProviderIds,SeriesId,ProductionYear", "EnableImages": "false"}):
                seen[it["Id"]] = it
        series = {}
        wanted = sorted({i["SeriesId"] for i in seen.values() if i.get("SeriesId")})
        for start in range(0, len(wanted), 100):
            q = urllib.parse.urlencode({"Ids": ",".join(wanted[start:start + 100]), "Fields": "ProviderIds,ProductionYear"})
            for s in (_mb(service, f"/Users/{uid}/Items?{q}") or {}).get("Items") or []:
                series[s["Id"]] = s
        entries = []
        for it in seen.values():
            ud = it.get("UserData") or {}
            e = {"watched": bool(ud.get("Played")), "plays": ud.get("PlayCount", 0), "last_watched": ud.get("LastPlayedDate"),
                 "position_ms": int((ud.get("PlaybackPositionTicks") or 0) / 10000), "duration_ms": int((it.get("RunTimeTicks") or 0) / 10000)}
            if it.get("Type") == "Movie":
                e.update(type="movie", title=it.get("Name"), year=it.get("ProductionYear"), ids=_norm(it.get("ProviderIds")))
            else:
                s = series.get(it.get("SeriesId")) or {}
                e.update(type="episode", show=it.get("SeriesName") or s.get("Name"), show_year=s.get("ProductionYear"),
                         season=it.get("ParentIndexNumber"), episode=it.get("IndexNumber"), title=it.get("Name"),
                         ids=_norm(s.get("ProviderIds")))
            entries.append(e)
        if entries:
            accounts[user["Name"]] = entries
    return accounts


MAX_HISTORY_FILE = 80 * 1024 * 1024  # reading one takes about 4.5 times its size, within the 512 MB limit in compose


def read_file(path):
    if os.path.getsize(path) > MAX_HISTORY_FILE:
        raise ValueError("That history file is larger than 80 MB")
    data = _load(path, None)
    if not isinstance(data, dict) or not isinstance(data.get("accounts"), dict):
        raise ValueError("This is not a watch history file")
    return data["accounts"]


# Keeping it ----------------------------------------------------------------------------------

def save_history(data_dir, source, accounts):
    d = folder(data_dir)
    if os.path.exists(os.path.join(d, "result.json")):
        os.replace(os.path.join(d, "result.json"), os.path.join(d, "result-before.json"))  # the list was for the old history
    _save(os.path.join(d, "history.json"), {"source": source, "imported": datetime.now(timezone.utc).isoformat(), "accounts": accounts})
    mapping = _load(os.path.join(d, "mapping.json"), {})
    for name in accounts:
        mapping.setdefault(name, "")
    _save(os.path.join(d, "mapping.json"), {k: v for k, v in mapping.items() if k in accounts})


def status(data_dir, services):
    d = folder(data_dir)
    history = _load(os.path.join(d, "history.json"), {})
    mapping = _load(os.path.join(d, "mapping.json"), {})
    applied = _load(os.path.join(d, "applied.json"), {})
    jf = jellyfin_app(services)
    users = []
    if jf:
        try:
            users = jellyfin_users(jf)
        except ServiceError:
            users = []
    lower = {u.lower(): u for u in users}
    accounts = []
    for name, entries in (history.get("accounts") or {}).items():
        if not isinstance(entries, list):
            continue
        entries = [e for e in entries if isinstance(e, dict)]
        target = mapping.get(name, "")
        accounts.append({"name": name, "films": sum(e["type"] == "movie" for e in entries),
                         "episodes": sum(e["type"] == "episode" for e in entries),
                         "jellyfin_user": target, "suggested": lower.get(name.lower(), ""),
                         "applied": len(applied.get(target, [])) if target else 0})
    accounts.sort(key=lambda a: -(a["films"] + a["episodes"]))
    return {"source": history.get("source"), "imported": history.get("imported"), "accounts": accounts,
            "jellyfin_users": users, "jellyfin": bool(jf), "last": _load(os.path.join(d, "result.json"), None)}


def set_mapping(data_dir, mapping):
    d = folder(data_dir)
    known = (_load(os.path.join(d, "history.json"), {}).get("accounts") or {}).keys()
    current = _load(os.path.join(d, "mapping.json"), {})
    for k, v in mapping.items():
        if k in known:
            current[k] = str(v or "")[:100]
    _save(os.path.join(d, "mapping.json"), current)


def apply(data_dir, services):
    """Applies the history to Jellyfin. Returns a sentence."""
    jf = jellyfin_app(services)
    if not jf:
        raise ValueError("Add Jellyfin with its API key in Manage apps first")
    d = folder(data_dir)
    history = (_load(os.path.join(d, "history.json"), {}).get("accounts")) or {}
    mapping = _load(os.path.join(d, "mapping.json"), {})
    applied = _load(os.path.join(d, "applied.json"), {})
    users = {u["Name"].lower(): u["Id"] for u in _mb(jf, "/Users") or []}
    marked = resumed = 0
    unmatched = []
    for account, jf_name in mapping.items():
        uid = users.get((jf_name or "").lower())
        if not uid or account not in history:
            continue
        done = set(applied.get(jf_name, []))
        found = set()  # history entries that matched an item, applied now or before
        movies, episodes = {}, {}
        for e in history[account]:
            for k in ("tmdb", "imdb", "tvdb"):
                v = (e.get("ids") or {}).get(k)
                if not v:
                    continue
                if e["type"] == "movie":
                    movies[(k, str(v))] = e
                else:
                    episodes[(k, str(v), e.get("season"), e.get("episode"))] = e
        items = _all_items(jf, "/Items", {"userId": uid, "recursive": "true", "includeItemTypes": "Movie,Episode",
                                          "fields": "ProviderIds,UserData,SeriesId", "enableImages": "false"})
        series = {}  # every show's IDs, 100 shows a request, so episodes applied before are still known as found
        wanted = sorted({i["SeriesId"] for i in items if i.get("SeriesId")})
        for start in range(0, len(wanted), 100):
            q = urllib.parse.urlencode({"userId": uid, "ids": ",".join(wanted[start:start + 100]), "fields": "ProviderIds", "enableImages": "false"})
            for s in (_mb(jf, f"/Items?{q}") or {}).get("Items") or []:
                series[s["Id"]] = _norm(s.get("ProviderIds"))
        for it in items:
            if it["Type"] == "Movie":
                match = next((movies[(k, v)] for k, v in _norm(it.get("ProviderIds")).items() if (k, v) in movies), None)
            elif it.get("SeriesId"):
                s, ep = it.get("ParentIndexNumber"), it.get("IndexNumber")
                match = next((episodes[(k, v, s, ep)] for k, v in series.get(it["SeriesId"], {}).items() if (k, v, s, ep) in episodes), None)
            else:
                match = None
            if not match:
                continue
            found.add(id(match))
            if it["Id"] in done:
                continue
            ud = it.get("UserData") or {}
            if match["watched"] and not ud.get("Played"):
                qs = urllib.parse.urlencode({"userId": uid, **({"datePlayed": match["last_watched"]} if match.get("last_watched") else {})})
                _mb(jf, f"/UserPlayedItems/{it['Id']}?{qs}", "POST")
                marked += 1
            elif not match["watched"] and match.get("position_ms") and not ud.get("Played") and not ud.get("PlaybackPositionTicks"):
                _mb(jf, f"/UserItems/{it['Id']}/UserData?userId={uid}", "POST",
                    {"PlaybackPositionTicks": int(match["position_ms"]) * 10000,
                     **({"LastPlayedDate": match["last_watched"]} if match.get("last_watched") else {})})
                resumed += 1
            done.add(it["Id"])
        applied[jf_name] = sorted(done)
        for e in history[account]:
            if id(e) not in found:
                unmatched.append({"account": account, "title": _title(e)})
    _save(os.path.join(d, "applied.json"), applied)
    _save(os.path.join(d, "result.json"), {"finished": datetime.now(timezone.utc).isoformat(), "marked": marked, "resumed": resumed,
                                           "unmatched": unmatched[:300], "unmatched_count": len(unmatched)})
    return f"Marked {marked} as watched and set {resumed} resume points; {len(unmatched)} not in Jellyfin yet"


def _title(e):
    if e.get("type") == "episode":
        return f"{e.get('show') or 'Unknown show'} S{int(e.get('season') or 0):02d}E{int(e.get('episode') or 0):02d}"
    return f"{e.get('title') or 'Unknown film'}" + (f" ({e['year']})" if e.get("year") else "")


# User defaults -----------------------------------------------------------------------------

def ensure_defaults(services, prefs=DEFAULT_PREFS):
    jf = jellyfin_app(services)
    if not jf:
        raise ValueError("Add Jellyfin with its API key in Manage apps first")
    changed = []
    for u in _mb(jf, "/Users") or []:
        path = f"/DisplayPreferences/usersettings?userId={u['Id']}&client=emby"
        current = _mb(jf, path) or {}
        custom = current.get("CustomPrefs") or {}
        missing = {k: v for k, v in prefs.items() if not custom.get(k)}
        if missing:
            custom.update(missing)
            current["CustomPrefs"] = custom
            _mb(jf, path, "POST", current)
            changed.append(u["Name"])
    return f"Set defaults for {', '.join(changed)}" if changed else "Every user already has the defaults"


def detect_jellyfin():
    """Jellyfin on this computer, for set-up: its address and version, or None."""
    for url in ("http://127.0.0.1:8096", "http://localhost:8096"):
        try:
            req = urllib.request.Request(f"{url}/System/Info/Public", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=3) as r:  # a fixed local address  # nosec B310
                info = json.loads(r.read(100000))
            if info.get("ProductName", "").lower().startswith("jellyfin") or info.get("Version"):
                return {"url": url, "version": info.get("Version", ""), "name": info.get("ServerName", "Jellyfin")}
        except (OSError, ValueError):
            continue
    return None

