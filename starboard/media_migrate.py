"""Moving to another media server: what is carried across, and the doing of it (DASH-587, owner, 26 November 2026).

The wizard (mediaserver_switch.py) says what would happen and changes nothing. This module reads both servers for that
plan (`preview`) and, once a person has confirmed, does it (`run`), in this order, each part on its own so one that
fails does not stop the next, and each saying what it did in words:

  libraries  the old server's libraries are added to the new one, from the same folders (nothing is copied or moved);
             "own" mode adds Films, Series and Music from Starboard's own media folder instead, for a person with no
             old server to read
  users      each person is made in the new server, with a long random password nobody sees, so nobody can sign in
             until the owner sets one in that server's own dashboard (Plex: not possible, accounts belong to plex.tv)
  history    what was watched and where each person stopped, read from the old server and written into the new one:
             Jellyfin through the existing import (migrate.py, with Keep applying), Emby person by person, Plex for the
             account that owns the token only
  switch     last, `mediaserver.choose`: it asks the new server to answer first and keeps the old one for 24 hours

Nothing is deleted from either server, and the person's files are never touched: the libraries read the same folders
(Plex and Emby mount them read only when Starboard installs them). It is imported only when the wizard is used."""

import os
import secrets
import time
import urllib.parse
from datetime import datetime, timezone

from . import mediaserver, migrate, services

PARTS = ("libraries", "users", "history", "keep")
NAMES = {"libraries": "Libraries", "users": "People", "history": "What was watched", "keep": "Keep applying", "switch": "The switch"}

# Library kinds each server can be given by Starboard, and Plex's agent and scanner for each (the current ones).
MB_TYPES = ("movies", "tvshows", "music", "books", "homevideos", "musicvideos", "mixed")
PLEX_KINDS = {"movies": ("movie", "tv.plex.agents.movie", "Plex Movie"), "tvshows": ("show", "tv.plex.agents.series", "Plex TV Series"),
              "music": ("artist", "tv.plex.agents.music", "Plex Music")}
PLEX_SECTIONS = {"movie": "movies", "show": "tvshows", "artist": "music", "photo": "photos"}
KIND_WORDS = {"movies": "films", "tvshows": "series", "music": "music", "books": "books", "homevideos": "home videos",
              "musicvideos": "music videos", "mixed": "mixed", "photos": "photos"}

# Starboard's own media folders (app_setup.JELLYFIN_LIBRARIES): the name, the kind and the folder inside the media folder.
OWN_LIBRARIES = (("Films", "movies", "movies"), ("Series", "tvshows", "tv"), ("Music", "music", "music"))


def _one(server_id):
    cls = mediaserver.ADAPTERS.get(server_id)
    if cls is None:
        raise LookupError("Starboard does not have that media server")
    return cls()


# Reading ---------------------------------------------------------------------------------------------------------------

def read_libraries(one, services_list):
    """A server's libraries with their folders: [{"name", "type", "folders"}]. Raises ServiceError in words."""
    svc = one._service(services_list)
    if one.id == "plex":
        from .mediaservers import plex
        rows = plex._list(one._send(svc, "GET", "/library/sections"), "Directory")
        return [{"name": str(d.get("title") or ""), "type": PLEX_SECTIONS.get(d.get("type"), "mixed"),
                 "folders": [str(p["path"]) for p in d.get("Location") or [] if isinstance(p, dict) and p.get("path")]} for d in rows]
    rows = one._send(svc, "GET", "/Library/VirtualFolders") or []
    return [{"name": str(r.get("Name") or ""), "type": str(r.get("CollectionType") or "mixed"),
             "folders": [str(p) for p in r.get("Locations") or []]} for r in rows if isinstance(r, dict)]


def read_users(one, services_list):
    """The names of a server's people. Plex's own system accounts have no name and are left out by the adapter."""
    return [u["name"] for u in one.users(services_list) if u.get("name")]


def own_libraries(data_dir, inside, exists=os.path.isdir, host=None):
    """The libraries Starboard's own media folder gives: [{"name", "type", "folders"}] for each of Films, Series and Music
    whose folder is there and has something in it. `inside` is the media folder as the new server sees it. When the
    media folder on this computer is not known (Install apps did not set it) the three are offered, to be checked."""
    host = host if host is not None else _host_media(data_dir)
    out = []
    for name, kind, sub in OWN_LIBRARIES:
        if host and (not exists(f"{host}/{sub}") or not _has_files(f"{host}/{sub}")):
            continue
        out.append({"name": name, "type": kind, "folders": [f"{inside.rstrip('/')}/{sub}"]})
    return out


def _host_media(data_dir):
    try:
        from . import plugins_admin as pa
        return pa.media_host_dir(data_dir) if data_dir else None
    except Exception:  # noqa: BLE001  the plan still reads; it only cannot say which folders exist
        return None


def _has_files(path):
    try:
        with os.scandir(path) as entries:
            return next(entries, None) is not None
    except OSError:
        return False


def _inside(data_dir, target_id, svc):
    """The media folder as the new server's container sees it (/data/media when Starboard installed it)."""
    from . import plugin_libraries
    try:
        return plugin_libraries.media_inside(data_dir, {"container": svc.get("container") or target_id})
    except Exception:  # noqa: BLE001
        return plugin_libraries.DEFAULT_INSIDE


# Planning ----------------------------------------------------------------------------------------------------------------

def can_add(target_id, kind):
    """Whether Starboard can add a library of this kind to that server."""
    if target_id == "plex":
        return kind in PLEX_KINDS
    return kind in MB_TYPES


def plan_libraries(wanted, have, target_id):
    """Each library to carry across: [{"name", "type", "folders", "action": "add" | "exists" | "skip", "why"}]."""
    names = {x["name"].lower() for x in have}
    folders = {f.rstrip("/") for x in have for f in x["folders"]}
    out = []
    for lib in wanted:
        row = {**lib, "action": "add", "why": ""}
        if not lib["name"] or not lib["folders"]:
            row.update(action="skip", why="It has no folder to read")
        elif not can_add(target_id, lib["type"]):
            row.update(action="skip", why=f"Starboard cannot add {KIND_WORDS.get(lib['type'], lib['type'])} libraries to {mediaserver.ADAPTERS[target_id].name}")
        elif lib["name"].lower() in names or any(f.rstrip("/") in folders for f in lib["folders"]):
            row.update(action="exists", why="The new media server has it already")
        out.append(row)
    return out


def plan_users(wanted, have, target_id):
    """Each person to carry across: [{"name", "action": "add" | "exists" | "cannot", "why"}]."""
    names = {n.lower() for n in have}
    out = []
    for name in wanted:
        if target_id == "plex":
            out.append({"name": name, "action": "cannot", "why": "Plex accounts belong to plex.tv: invite them from Plex"})
        elif name.lower() in names:
            out.append({"name": name, "action": "exists", "why": "The new media server has this person already"})
        else:
            out.append({"name": name, "action": "add", "why": ""})
    return out


def history_how(source_id, target_id):
    """What can be done about watched state between these two, in words, and whether it can be done at all."""
    src = mediaserver.ADAPTERS[source_id].name if source_id else "the old media server"
    if target_id == "jellyfin":
        return {"can": True, "says": f"Read from {src} for every person, copied into Jellyfin by its watch history import. Films and episodes that are not in Jellyfin yet are applied every hour while Keep applying is on"
                + (". Plex gives only the account that owns the token" if source_id == "plex" else "")}
    if target_id == "emby":
        return {"can": True, "says": f"Read from {src} and marked in Emby for each person with the same name. Run it again when Emby has scanned its libraries"
                + (". Plex gives only the account that owns the token" if source_id == "plex" else "")}
    if target_id == "plex":
        return {"can": True, "says": f"Read from {src} and marked in Plex for the account that owns the token only (Plex keeps each person's state in their own plex.tv account). "
                "Watched dates become today. Run it again when Plex has scanned its libraries"}
    return {"can": False, "says": "There is no media server to write it to"}


def preview(data, source_id, target_id, mode, data_dir=None):
    """What the move would carry across, read from both servers (GET only; nothing is changed). Never raises for a
    server that does not answer: that part says why in `problem`."""
    saved = (data or {}).get("services") or []
    out = {"libraries": [], "users": [], "history": None, "problem": "", "inside": ""}
    if not target_id or mode == "fresh":
        return out
    new = _one(target_id)
    new_svc = new.find_service(saved)
    if not new_svc:
        out["problem"] = f"{new.name} is not set up yet, so Starboard cannot read what it has"
        return out
    try:
        have_libs = read_libraries(new, saved)
        have_users = read_users(new, saved)
    except services.ServiceError as e:
        out["problem"] = str(e)
        return out
    if mode == "own":
        out["inside"] = _inside(data_dir, target_id, new_svc)
        wanted = own_libraries(data_dir, out["inside"])
        out["libraries"] = plan_libraries(wanted, have_libs, target_id)
        return out
    if not source_id or source_id == target_id:
        out["problem"] = "There is no old media server to read from"
        return out
    old = _one(source_id)
    if not old.find_service(saved):
        out["problem"] = f"{old.name} is not set up, so there is nothing to read from it"
        return out
    try:
        out["libraries"] = plan_libraries(read_libraries(old, saved), have_libs, target_id)
        out["users"] = plan_users(read_users(old, saved), have_users, target_id)
    except services.ServiceError as e:
        out["problem"] = str(e)
        return out
    out["history"] = history_how(source_id, target_id)
    return out


# Doing -------------------------------------------------------------------------------------------------------------------

def add_library(one, svc, lib):
    """One library into the new server, from its folders."""
    if one.id == "plex":
        kind, agent, scanner = PLEX_KINDS[lib["type"]]
        query = [("name", lib["name"]), ("type", kind), ("agent", agent), ("scanner", scanner), ("language", "en-US")]
        query += [("location", f) for f in lib["folders"]]
        one._send(svc, "POST", "/library/sections?" + urllib.parse.urlencode(query))
        return
    query = {"name": lib["name"], "refreshLibrary": "false"}
    if lib["type"] != "mixed":
        query["collectionType"] = lib["type"]
    one._send(svc, "POST", "/Library/VirtualFolders?" + urllib.parse.urlencode(query),
              {"LibraryOptions": {"PathInfos": [{"Path": f} for f in lib["folders"]]}})


def add_user(one, svc, name):
    """One person into Jellyfin or Emby, with a long random password nobody sees (the owner sets a real one in that
    server's dashboard, Users)."""
    password = secrets.token_urlsafe(24)
    if one.id == "jellyfin":
        one._send(svc, "POST", "/Users/New", {"Name": name, "Password": password})
        return
    made = one._send(svc, "POST", "/Users/New", {"Name": name})
    uid = (made or {}).get("Id") if isinstance(made, dict) else None
    if uid:
        one._send(svc, "POST", f"/Users/{uid}/Password", {"Id": uid, "NewPw": password})


def _run_libraries(one, svc, rows, step):
    added = []
    for lib in rows:
        if lib["action"] != "add":
            step["items"].append({"name": lib["name"], "state": "kept" if lib["action"] == "exists" else "skipped", "why": lib["why"]})
            continue
        try:
            add_library(one, svc, lib)
            added.append(lib["name"])
            step["items"].append({"name": lib["name"], "state": "done", "why": ""})
        except services.ServiceError as e:
            step["items"].append({"name": lib["name"], "state": "failed", "why": f"{e}. Check that {one.name} can reach {', '.join(lib['folders'])}"})
    if added:
        try:
            one.refresh([svc])  # asks it to scan the new folders
        except (services.ServiceError, KeyError):
            step["items"].append({"name": "Scan", "state": "skipped", "why": f"{one.name} will scan on its own schedule"})
    failed = sum(i["state"] == "failed" for i in step["items"])
    step["said"] = (f"Added {len(added)} {'library' if len(added) == 1 else 'libraries'} to {one.name}" if added else f"No library needed adding to {one.name}") \
        + (f"; {failed} could not be added" if failed else "")
    step["state"] = "partly" if failed and added else "failed" if failed else "done"


def _run_users(one, svc, rows, step):
    made = 0
    for u in rows:
        if u["action"] != "add":
            step["items"].append({"name": u["name"], "state": "kept" if u["action"] == "exists" else "skipped", "why": u["why"]})
            continue
        try:
            add_user(one, svc, u["name"])
            made += 1
            step["items"].append({"name": u["name"], "state": "done", "why": ""})
        except services.ServiceError as e:
            step["items"].append({"name": u["name"], "state": "failed", "why": str(e)})
    failed = sum(i["state"] == "failed" for i in step["items"])
    step["said"] = (f"Made {made} {'person' if made == 1 else 'people'} in {one.name}. Each has a password nobody knows: set one in {one.name}'s dashboard under Users" if made
                    else f"Nobody needed making in {one.name}") + (f"; {failed} could not be made" if failed else "")
    step["state"] = "partly" if failed and made else "failed" if failed else "done"


# Watched state ---------------------------------------------------------------------------------------------------------

def read_history(data_dir, source_id, source_svc):
    """Everyone's history from the old server, kept in data/imports/history.json as the import page keeps it."""
    if source_id == "plex":
        accounts = migrate.read_plex_server(source_svc["url"], source_svc["api_key"])
        label = "Plex server"
    else:
        accounts = migrate.read_media_server(source_svc["url"] + ("/emby" if source_id == "emby" else ""), source_svc["api_key"],
                                             mediaserver.ADAPTERS[source_id].name)
        label = mediaserver.ADAPTERS[source_id].name
    migrate.save_history(data_dir, label, accounts)
    return accounts


def _ticks(ms):
    return int(ms) * 10000


def _emby_date(iso):
    """Emby wants the date played as yyyyMMddHHmmss."""
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
    except ValueError:
        return ""


def _wanted_maps(entries):
    movies, episodes = {}, {}
    for e in entries:
        for k in ("tmdb", "imdb", "tvdb"):
            v = (e.get("ids") or {}).get(k)
            if not v:
                continue
            if e.get("type") == "movie":
                movies[(k, str(v))] = e
            else:
                episodes[(k, str(v), e.get("season"), e.get("episode"))] = e
    return movies, episodes


def apply_to_emby(svc, accounts, base_prefix="/emby"):
    """Marks what was watched in Emby for each person who has the same name there. Returns {marked, resumed, unmatched}.
    Nothing already watched is touched, so running it again is safe."""
    base = dict(svc, url=svc["url"].rstrip("/") + base_prefix)
    users = {u["Name"].lower(): u["Id"] for u in migrate._mb(base, "/Users") or []}
    marked = resumed = 0
    unmatched = []
    for name, entries in accounts.items():
        uid = users.get(name.lower())
        if not uid:
            unmatched.append({"account": name, "title": "Nobody called this in Emby"})
            continue
        movies, episodes = _wanted_maps([e for e in entries if isinstance(e, dict)])
        found, series, asked = set(), {}, set()
        for items in migrate._item_pages(base, f"/Users/{uid}/Items", {"Recursive": "true", "IncludeItemTypes": "Movie,Episode",
                                                                       "Fields": "ProviderIds,UserData,SeriesId", "EnableImages": "false"}):
            wanted = sorted({i["SeriesId"] for i in items if i.get("SeriesId")} - asked)
            asked.update(wanted)
            for start in range(0, len(wanted), 100):
                q = urllib.parse.urlencode({"Ids": ",".join(wanted[start:start + 100]), "Fields": "ProviderIds", "EnableImages": "false"})
                for s in (migrate._mb(base, f"/Users/{uid}/Items?{q}") or {}).get("Items") or []:
                    series[s["Id"]] = migrate._norm(s.get("ProviderIds"))
            for it in items:
                match = migrate._match(it, movies, episodes, series)
                if not match:
                    continue
                found.add(id(match))
                ud = it.get("UserData") or {}
                if match.get("watched") and not ud.get("Played"):
                    date = _emby_date(match.get("last_watched"))
                    migrate._mb(base, f"/Users/{uid}/PlayedItems/{it['Id']}" + (f"?DatePlayed={date}" if date else ""), "POST")
                    marked += 1
                elif not match.get("watched") and match.get("position_ms") and not ud.get("Played") and not ud.get("PlaybackPositionTicks"):
                    migrate._mb(base, f"/Users/{uid}/Items/{it['Id']}/UserData", "POST", {"PlaybackPositionTicks": _ticks(match["position_ms"])})
                    resumed += 1
        unmatched += [{"account": name, "title": migrate._title(e)} for e in entries if isinstance(e, dict) and id(e) not in found]
    return {"marked": marked, "resumed": resumed, "unmatched": unmatched}


def _plex_guids(m):
    out = {}
    for g in m.get("Guid") or []:
        k, _, v = str(g.get("id") or "").partition("://")
        if k in ("tmdb", "imdb", "tvdb") and v:
            out[k] = v
    return out


def apply_to_plex(one, svc, accounts, owner=""):
    """Marks what was watched in Plex for the account that owns the token only. `accounts` are matched to it by the
    owner's name, or, when no name matches and there is one account, that one. Returns {marked, resumed, unmatched, who}."""
    from .mediaservers import plex
    names = list(accounts)
    pick = next((n for n in names if owner and n.lower() == owner.lower()), None) or (names[0] if len(names) == 1 else None)
    if pick is None:
        return {"marked": 0, "resumed": 0, "unmatched": [], "who": "",
                "problem": "Plex can take the history of one person only, and none of these names matches the owner of the Plex token"}
    movies, episodes = _wanted_maps([e for e in accounts[pick] if isinstance(e, dict)])
    found, marked, resumed = set(), 0, 0

    def mark(key, entry):
        nonlocal marked, resumed
        found.add(id(entry))
        if entry.get("watched"):
            one._send(svc, "GET", f"/:/scrobble?identifier=com.plexapp.plugins.library&key={urllib.parse.quote(str(key))}")
            marked += 1
        elif entry.get("position_ms"):
            one._send(svc, "GET", f"/:/progress?identifier=com.plexapp.plugins.library&key={urllib.parse.quote(str(key))}&time={int(entry['position_ms'])}&state=stopped")
            resumed += 1

    for section in plex._list(one._send(svc, "GET", "/library/sections"), "Directory"):
        sk = urllib.parse.quote(str(section.get("key") or ""))
        if section.get("type") == "movie":
            for m in plex._list(one._send(svc, "GET", f"/library/sections/{sk}/all?type=1&includeGuids=1"), "Metadata"):
                if m.get("viewCount") or m.get("viewOffset"):
                    continue  # already watched or part watched in Plex: left as it is
                hit = next((movies[(k, v)] for k, v in _plex_guids(m).items() if (k, v) in movies), None)
                if hit:
                    mark(m.get("ratingKey"), hit)
        elif section.get("type") == "show":
            shows = {s.get("ratingKey"): _plex_guids(s) for s in plex._list(one._send(svc, "GET", f"/library/sections/{sk}/all?type=2&includeGuids=1"), "Metadata")}
            for m in plex._list(one._send(svc, "GET", f"/library/sections/{sk}/all?type=4"), "Metadata"):
                if m.get("viewCount") or m.get("viewOffset"):
                    continue
                ids = shows.get(m.get("grandparentRatingKey")) or {}
                hit = next((episodes[(k, v, m.get("parentIndex"), m.get("index"))] for k, v in ids.items() if (k, v, m.get("parentIndex"), m.get("index")) in episodes), None)
                if hit:
                    mark(m.get("ratingKey"), hit)
    unmatched = [{"account": pick, "title": migrate._title(e)} for e in accounts[pick] if isinstance(e, dict) and id(e) not in found]
    return {"marked": marked, "resumed": resumed, "unmatched": unmatched, "who": pick}


def _run_history(cfg, data_dir, source_id, one, saved, step, keep, again=False):
    """Reads the old server's history (or uses the one kept, when `again`) and writes it into the new one."""
    svc = one._service(saved)
    path = os.path.join(migrate.folder(data_dir), "history.json")
    if again and os.path.exists(path):
        accounts = migrate.read_file(path)
    else:
        old = _one(source_id)
        accounts = read_history(data_dir, source_id, old._service(saved))
    total = sum(len(v) for v in accounts.values())
    if not total:
        step["said"] = "The old media server has no watched history to carry across"
        step["state"] = "done"
        return
    if one.id == "jellyfin":
        users = {u["name"].lower(): u["name"] for u in one.users(saved)}
        mapping = {a: users[a.lower()] for a in accounts if a.lower() in users}
        migrate.set_mapping(data_dir, mapping)
        said = migrate.apply(data_dir, saved)
        for a in accounts:
            if a not in mapping:
                step["items"].append({"name": a, "state": "skipped", "why": "Nobody has this name in Jellyfin yet"})
        if keep:
            with cfg.lock:
                cfg.data["extras"]["import_keep"] = True
                cfg.save()
            said += ". Keep applying is on, so the rest follows as Jellyfin finds the media"
        step["said"] = said
        step["state"] = "done"
        return
    if one.id == "emby":
        got = apply_to_emby(svc, accounts)
    else:
        owner = ""
        try:
            from .mediaservers import plex  # noqa: F401
            owner = str(((one._send(svc, "GET", "/myplex/account") or {}).get("MediaContainer") or {}).get("username") or "")
        except services.ServiceError:
            owner = ""
        got = apply_to_plex(one, svc, accounts, owner)
        if got.get("problem"):
            step["said"], step["state"] = got["problem"], "failed"
            return
    step["items"] += [{"name": f"{u['account']}: {u['title']}", "state": "skipped", "why": "Not in the new media server yet"} for u in got["unmatched"][:50]]
    step["said"] = (f"Marked {got['marked']} as watched and set {got['resumed']} resume points in {one.name}; {len(got['unmatched'])} are not there yet. "
                    "Run this again when it has scanned its libraries" + (f". Only {got['who']}'s history can go into Plex" if one.id == "plex" else ""))
    step["state"] = "done"


# The whole move ----------------------------------------------------------------------------------------------------------

def run(cfg, data_dir, source_id, target_id, mode, parts, added, state, switch=True):
    """Does what a person confirmed, filling `state` as it goes (the page reads it): {"state", "steps": [...], "said"}.
    Each part is on its own; one that fails whole stops the switch, so a person is never moved on a half-made server.
    `added` is the ids of the media server plug-ins that are added and in use, as `mediaserver.choose` wants them."""
    if mode not in ("own", "migrate", "fresh"):
        raise ValueError("Choose how to switch: import your own media, migrate, or start fresh")
    one = _one(target_id) if target_id else None
    if source_id == target_id and mode != "own":
        raise ValueError("That media server is already in use")
    state.update({"state": "running", "steps": [], "said": "", "started": time.time(), "to": target_id, "from": source_id})
    saved = cfg.data["services"]
    parts = [p for p in parts if p in PARTS]
    if mode == "fresh" or not one:
        parts = []
    if mode == "own":
        parts = ["libraries"]
    if mode == "migrate" and not source_id:
        parts = []
    hard = False
    if parts:
        plan = preview(cfg.data, source_id, target_id, mode, data_dir)
        if plan["problem"]:
            state["steps"].append({"part": "libraries", "title": NAMES["libraries"], "state": "failed", "said": plan["problem"], "items": []})
            hard = True
            parts = []
        svc = one.find_service(saved) if one else None
        if "libraries" in parts:
            step = {"part": "libraries", "title": NAMES["libraries"], "state": "running", "said": "", "items": []}
            state["steps"].append(step)
            _run_libraries(one, svc, plan["libraries"], step)
            hard = hard or step["state"] == "failed"
        if "users" in parts and one.id != "plex":
            step = {"part": "users", "title": NAMES["users"], "state": "running", "said": "", "items": []}
            state["steps"].append(step)
            _run_users(one, svc, plan["users"], step)
            hard = hard or step["state"] == "failed"
        elif "users" in parts:
            state["steps"].append({"part": "users", "title": NAMES["users"], "state": "skipped", "items": [],
                                   "said": "Plex accounts belong to plex.tv, so Starboard cannot make them. Invite each person from Plex"})
        if "history" in parts:
            step = {"part": "history", "title": NAMES["history"], "state": "running", "said": "", "items": []}
            state["steps"].append(step)
            try:
                _run_history(cfg, data_dir, source_id, one, saved, step, "keep" in parts)
            except (services.ServiceError, ValueError, OSError) as e:
                step["state"], step["said"] = "failed", f"Could not carry the history across: {e}"
            hard = hard or step["state"] == "failed"
    if hard:
        state.update(state="failed", said="Nothing was switched. What was added to the new media server stays there, and nothing was removed from either. "
                     "Fix what the steps say, then start again: anything already there is kept, not made twice")
        return state
    if switch and one is not None:
        step = {"part": "switch", "title": NAMES["switch"], "state": "running", "said": "", "items": []}
        state["steps"].append(step)
        try:
            got = mediaserver.choose(cfg, target_id, added)
            step["said"], step["state"] = got["said"], "done"
        except (ValueError, LookupError) as e:
            step["said"], step["state"] = str(e), "failed"
            state.update(state="failed", said=f"The libraries and people are in {one.name}, but it was not switched: {e}")
            return state
    state.update(state="done", said="Done. " + ("The old media server stays added, and you can go back to it for 24 hours." if source_id and source_id != target_id else ""))
    state["finished"] = time.time()
    return state
