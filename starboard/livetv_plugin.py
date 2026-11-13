"""The Live TV plug-in's own program (DASH-285): run by Starboard's own image in the plug-in's container,
`python -m starboard.livetv_plugin`. It does what Starboard's Live TV job did: once an hour it refreshes the guides
that are due, rebuilds a channel list when its source changed (or weekly), whitens logos, and adds the lists and
guides to Jellyfin (livetv.py, livetv_jellyfin.py, unchanged). Starboard itself still serves the logos and the Pluto
TV links to Jellyfin at the same addresses as before, from the same Live TV folder, so Jellyfin sees no change.

Its settings come from /run/starboard/settings.json (Settings, Plug-ins, Live TV), Jellyfin's address and key from
/run/starboard/jellyfin.json. It answers on port 8080:
  GET  /health   200 while it runs
  GET  /card     the dashboard card: {"state": "ok" | "warning" | "problem", "text": ...}
  POST /run      run now, every list rebuilt (Run Live TV now)
"""
import http.server
import json
import os
import threading
import time

from . import child

SETTINGS = os.environ.get("STARBOARD_PLUGIN_SETTINGS", "/run/starboard/settings.json")
JELLYFIN = os.environ.get("STARBOARD_PLUGIN_JELLYFIN", "/run/starboard/jellyfin.json")
STATUS = os.environ.get("STARBOARD_PLUGIN_STATUS", "/data/status.json")
EVERY = 3600
_wake = threading.Event()
_force = {"now": False}
_lock = threading.Lock()


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def status():
    return _read(STATUS, {})


def _save_status(**values):
    current = {**status(), **values}
    tmp = STATUS + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(current, f)
    os.replace(tmp, STATUS)


def run_once(force=False, build=None, connect=None, refresh=None):
    """One run: the files, then Jellyfin. Returns the sentence the card shows."""
    from . import livetv, livetv_jellyfin
    s = _read(SETTINGS, {})
    address = str(s.get("address") or "").rstrip("/")
    if not address:
        raise ValueError("Set the address Jellyfin uses to reach Starboard in Settings, Plug-ins, Live TV")
    guides = [os.path.join(livetv.folder() or "", g) for g in livetv_jellyfin.GUIDES]
    before = [_mtime(g) for g in guides]
    summary = (build or livetv.run)(address, bool(s.get("white_logos", True)), force=force)
    jf = _read(JELLYFIN, {})
    services = [{"type": "jellyfin", "url": jf["url"], "api_key": jf["api_key"]}] if jf.get("url") and jf.get("api_key") else []
    added = (connect or livetv_jellyfin.connect)(services, {"livetv_jellyfin_folder": s.get("jellyfin_folder") or ""}, "",
                                                 local_folder=livetv.folder(), host_path="", env={})
    if not added and [_mtime(g) for g in guides] != before:  # new guides: Jellyfin reads them now, not tomorrow
        added = (refresh or livetv_jellyfin.refresh_guide)(services)
    try:
        livetv.write_now(livetv.folder(), DATA)  # the On TV now card's next few hours (DASH-359)
    except (OSError, ValueError) as e:
        print(f"Live TV could not write what is on now: {e}", flush=True)
    return f"{summary} · {added}" if added else summary


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def now_card(now=None):
    """The On TV now card (DASH-359, owner 13 November 2026: option 5 on the dashboard): up to 8 channels in Jellyfin
    with what is on now and next, in number order, from the section chosen in Live TV's settings."""
    from . import livetv
    now = now or time.time()
    got = _read(os.path.join(DATA, livetv.NOW), {})
    want = str(_read(SETTINGS, {}).get("now_section") or "")
    items = []
    for cid, c in sorted((got.get("channels") or {}).items(), key=lambda kv: int(kv[1].get("number") or 0)):
        if want and c.get("section") != want:
            continue
        progs = c.get("programmes") or []
        cur = next((p for p in progs if p[0] <= now < p[1]), None)
        if not cur:
            continue
        nxt = next((p for p in progs if p[0] >= cur[1]), None)
        items.append({"channel": c["name"], "number": str(c.get("number") or ""), "now": cur[2], "start": cur[0], "stop": cur[1],
                      **({"next": nxt[2], "next_start": nxt[0]} if nxt else {})})
        if len(items) == 8:
            break
    if not got:
        note = "Nothing yet: it fills after Live TV's next run."
    elif not items:
        note = f"Nothing on now in {want}." if want else "No programmes now: the guides may not cover this hour."
    else:
        note = want or ""
    return {"items": items, "note": note}


def card():
    st = status()
    if not st:
        return {"state": "warning", "text": "Not run yet. It runs within the hour, or select Run Live TV now."}
    when = time.strftime("%H:%M on %d %b", time.localtime(st.get("finished") or st.get("started") or 0))
    if st.get("state") == "running":
        return {"state": "ok", "text": "Running now: refreshing guides and testing channels."}
    if st.get("state") == "failed":
        return {"state": "problem", "text": f"Last run failed at {when}: {st.get('summary', '')}"[:160]}
    return {"state": "ok", "text": f"Last run at {when}: {st.get('summary', '')}"[:160]}


def loop(stop=None):
    while not (stop and stop.is_set()):
        with _lock:
            force, _force["now"] = _force["now"], False
        try:
            _save_status(state="running", started=time.time())
            with _build_lock:  # not while a list just added is being tested
                # In a short-lived process, so the guide's memory goes back to the system when it ends (DASH-79)
                said = child.run("livetv-plugin", {"force": force}, timeout=3 * 3600)  # the finish time is taken after the run
            _save_status(state="done", finished=time.time(), summary=said)
        except Exception as e:  # recorded for the card and the plug-in's section; the next run tries again
            try:
                _save_status(state="failed", finished=time.time(), summary=str(e)[:300])
            except OSError as again:  # its folder cannot be written: said in its log, and it keeps running
                print(f"Live TV could not save its status: {again}; the run said: {e}", flush=True)
        _wake.wait(EVERY)
        _wake.clear()


DATA = os.path.dirname(STATUS)


SOURCES = {"channels.m3u": "Free-TV", "samsung.m3u": "Samsung TV Plus", "pluto.m3u": "Pluto TV"}


def _region(c):
    """UK or US. Lists from before DASH-359 did not save it: Free-TV and Pluto TV are UK only; Samsung is unknown."""
    return c.get("region") or ("UK" if c.get("list") in ("channels.m3u", "pluto.m3u") else "")


def _sets(chans):
    """The bulk sets of channels (DASH-359, owner 12 November 2026): each region and each section, with the ids in it.
    Whole lists (sources) have their own switches, which stop the list itself: see _lists."""
    from . import livetv
    sets = []
    for kind, key, order in (("Regions", _region, ["UK", "US"]),
                             ("Sections", lambda c: c.get("section") or "Other", [b for b, _ in livetv.BLOCKS])):
        found = {}
        for c in chans:
            k = key(c)
            if k:
                found.setdefault(k, []).append(c["id"])
        for name in sorted(found, key=lambda n: (order.index(n) if n in order else len(order), n)):
            sets.append({"id": f"{kind.lower()}:{name}", "label": name, "kind": kind, "ids": found[name]})
    return sets


def _lists(chans, hidden):
    """One switch per list (owner, 12 November 2026: deactivate the original list in full, a switch for each of the
    others). Inactive: the list is not fetched at all and its channels leave Jellyfin."""
    from . import livetv
    off = livetv.lists_off(DATA)
    out = []
    for name, (label, playlist, _) in livetv.LISTS.items():
        ids = [c["id"] for c in chans if c.get("list") == playlist]
        on = sum(1 for i in ids if i not in hidden)
        out.append({"id": f"lists:{name}", "label": label, "kind": "Lists", "on": on, "total": len(ids), "active": name not in off,
                    "hint": "Inactive: not fetched, and none of its channels are in Jellyfin" if name in off
                    else f"Active: {on} of {len(ids)} channels in Jellyfin" if ids else "Active: its channels arrive at the next run"})
    # Each of the owner's own channel lists too, beside them (owner, 13 November 2026: "I would expect it to show under
    # free tv, samsung etc. with a toggle"): the same switch as its Activate or Deactivate in Your lists and guides.
    from . import livetv_own
    for x in livetv_own.sources(DATA):
        if x.get("kind") != "list":
            continue
        ids = [c["id"] for c in chans if c.get("list") == livetv_own.PLAYLIST and c.get("source") == x["id"]]
        on = sum(1 for i in ids if i not in hidden)
        active = x.get("on", True)
        out.append({"id": f"lists:own:{x['id']}", "label": x.get("name") or x["url"], "kind": "Lists", "on": on, "total": len(ids), "active": active,
                    "hint": "Inactive: none of its channels are in Jellyfin" if not active
                    else f"Your list. Active: {on} of {len(ids)} channels in Jellyfin" if ids else "Your list. Active: its channels arrive once it is tested"})
    return out


def _list_key(c):
    """Which list a channel came from: freetv, samsung or pluto, own:<id> for one of the owner's own lists, or other."""
    from . import livetv, livetv_own
    for key, (_, playlist, _) in livetv.LISTS.items():
        if c.get("list") == playlist:
            return key
    if c.get("list") == livetv_own.PLAYLIST:
        return f"own:{c['source']}" if c.get("source") else "own"
    return "other"


def _section(c):
    return c.get("section") or "Other"


def _ordered(values, order):
    return sorted(set(values), key=lambda n: (order.index(n) if n in order else len(order), n))


def _in(chans, sid):
    """The channels in one sub menu's set, such as in:samsung|r=US|s=News, or None when it is not one."""
    parts = sid[3:].split("|")
    want = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
    if not parts[0] or set(want) - {"r", "s"}:
        return None
    return [c for c in chans if _list_key(c) == parts[0] and ("r" not in want or _region(c) == want["r"])
            and ("s" not in want or _section(c) == want["s"])]


def _list_title(key, own):
    from . import livetv
    if key in livetv.LISTS:
        return livetv.LISTS[key][0]
    if key.startswith("own:"):
        return own.get(key[4:]) or "Your lists"
    return "Your lists" if key == "own" else "Other"


def _set_name(chans, sid, own):
    parts = sid[3:].split("|")
    return ", ".join([_list_title(parts[0], own)] + [p.split("=", 1)[1] or "Region not known" for p in parts[1:]])


def _tree(chans, hidden, own):
    """Sub menus (DASH-361, owner 12 November 2026: "simplify the channels with sub menus"): a menu for each list,
    split by region when a list has more than one, then by section, so no one screen holds every channel. Returns
    the menus, a switch for every channel in each of them, and where each channel goes."""
    from . import livetv
    off = livetv.lists_off(DATA)
    keys = list(livetv.LISTS) + _ordered((_list_key(c) for c in chans), list(livetv.LISTS))
    keys = list(dict.fromkeys(keys))
    menus, sets, place = [], [], {}
    count = lambda cs: {"on": sum(1 for c in cs if c["id"] not in hidden), "total": len(cs)}
    for key in keys:
        title, lid = _list_title(key, own), f"in:{key}"
        mine = [c for c in chans if _list_key(c) == key]
        menus.append({"id": lid, "title": title, "group": "Your lists" if key.startswith("own") else "Lists",
                      **({"active": False, "detail": "Inactive: not fetched, and none of its channels are in Jellyfin"} if key in off else
                         {"detail": "Its channels arrive at the next run"} if not mine else {})})
        if not mine:
            continue
        sets.append({"id": lid, "label": f"Every channel in {title}", "kind": "", "menu": lid, **count(mine)})
        regions = _ordered((_region(c) for c in mine), ["UK", "US"])
        for r in regions if len(regions) > 1 else [None]:
            parent, here = lid, mine
            if r is not None:
                parent, here = f"{lid}|r={r}", [c for c in mine if _region(c) == r]
                menus.append({"id": parent, "title": r or "Region not known", "group": "Regions", "parent": lid})
                sets.append({"id": parent, "label": f"Every channel in {r or 'this region'}", "kind": "", "menu": parent, **count(here)})
            sections = _ordered((_section(c) for c in here), [b for b, _ in livetv.BLOCKS])
            if len(sections) < 2:
                place.update({c["id"]: parent for c in here})
                continue
            for name in sections:
                sid, these = f"{parent}|s={name}", [c for c in here if _section(c) == name]
                menus.append({"id": sid, "title": name, "group": "Sections", "parent": parent})
                sets.append({"id": sid, "label": f"Every channel in {name}", "kind": "", "menu": sid, **count(these)})
                place.update({c["id"]: sid for c in these})
    return menus, sets, place


def channels_screen(said=""):
    """The plug-in's Channels screen in Starboard (DASH-313). Since 13 November 2026 (DASH-359, owner: "Build option 1
    with 2 in the accordions"): sections that fold, in Jellyfin's number order, each with its own switch and a table
    to sort and select from, filtered by list, region and state. The switches for whole lists, every channel and each
    region stay at the top. The sub menus of DASH-361 (`in:` sets) still work for the bulk action."""
    from . import livetv, livetv_own
    hidden = livetv.hidden_ids(DATA)
    own = {x["id"]: x.get("name", "") for x in livetv_own.sources(DATA)}
    chans = livetv.all_channels(livetv.folder())
    rows = []
    for c in sorted(chans, key=lambda c: int(c.get("number") or 0)):
        on = c["id"] not in hidden
        where = SOURCES.get(c.get("list")) or own.get(c.get("source")) or "Your lists"
        rows.append({"id": c["id"], "title": f"{c['number']} {c['name']}", "group": _section(c),
                     "cells": {"number": str(c.get("number") or ""), "name": c["name"], "list": where, "region": _region(c) or "Not known"},
                     "state": "ok" if on else "off", "on": on, "actions": ["toggle"]})
    bulk = _lists(chans, hidden)
    if rows:
        bulk.append({"id": "all", "label": "Every channel", "kind": "Channels", "on": sum(1 for r in rows if r["on"]), "total": len(rows)})
    for x in _sets(chans):
        b = {"id": x["id"], "label": x["label"], "kind": x["kind"], "on": sum(1 for i in x["ids"] if i not in hidden), "total": len(x["ids"])}
        bulk.append({**b, "fold": x["label"], "kind": ""} if x["kind"] == "Sections" else b)
    out = {"type": "list", "title": "Channels", "items": rows, "bulk": bulk, "layout": "folds",
           "columns": [{"key": "number", "label": "No.", "type": "number"}, {"key": "name", "label": "Channel"},
                       {"key": "list", "label": "List"}, {"key": "region", "label": "Region"}],
           "filters": [{"key": "list", "label": "List"}, {"key": "region", "label": "Region"}],
           "notices": livetv_own.notices(DATA),
           "intro": f"{sum(1 for r in rows if r['on'])} of {len(rows)} channels are in Jellyfin, in sections numbered as Jellyfin shows them."}
    if said:
        out["said"] = said
    return out


def _services():
    jf = _read(JELLYFIN, {})
    return [{"type": "jellyfin", "url": jf["url"], "api_key": jf["api_key"]}] if jf.get("url") and jf.get("api_key") else []


def _apply(hidden_before, hidden_after):
    """Saves the hidden channels. Back on: the lists are built again. Off: taken out now and Jellyfin told."""
    from . import livetv, livetv_jellyfin
    livetv.save_hidden(DATA, hidden_after)
    if hidden_before - hidden_after:
        with _lock:
            _force["now"] = True
        _wake.set()
        return "back"
    if hidden_after - hidden_before:
        livetv.drop_hidden(livetv.folder(), hidden_after)
        livetv_jellyfin.refresh_guide(_services())
        return "gone"
    return ""


def _bulk(body):
    from . import livetv
    want = str(body.get("value") or "")
    if want not in ("on", "off"):
        raise ValueError("Choose Activate or Deactivate")
    chans = livetv.all_channels(livetv.folder())
    sid = str(body.get("id") or "")
    if sid.startswith("lists:"):
        return _list_switch(sid[6:], want == "on")
    if sid == "all":
        name, ids = "Every channel", {c["id"] for c in chans}
    elif sid.startswith("in:"):  # one sub menu's channels (DASH-361)
        found = _in(chans, sid)
        if not found:
            raise ValueError("Not one of the lists, regions or sections")
        from . import livetv_own
        name, ids = _set_name(chans, sid, {x["id"]: x.get("name", "") for x in livetv_own.sources(DATA)}), {c["id"] for c in found}
    else:
        found = next((x for x in _sets(chans) if x["id"] == sid), None)
        if not found:
            raise ValueError("Not one of the lists, regions or sections")
        name, ids = found["label"], set(found["ids"])
    hidden = livetv.hidden_ids(DATA)
    after = hidden - ids if want == "on" else hidden | ids
    done = _apply(hidden, after)
    n = len(ids)
    what = f"{name}: {n} {'channel' if n == 1 else 'channels'}"
    if want == "on":
        return channels_screen(f"{what} activated; the lists are being rebuilt, which takes a few minutes" if done
                               else f"{what} already active")
    return channels_screen(f"{what} deactivated; Jellyfin drops them at its guide refresh, starting now" if done
                           else f"{what} already inactive")


def _own_switch(sid, on):
    """One of the owner's own lists, activated or deactivated from Channels (DASH-359)."""
    from . import livetv, livetv_jellyfin, livetv_own
    items = livetv_own.sources(DATA)
    x = next((x for x in items if x["id"] == sid and x.get("kind") == "list"), None)
    if not x:
        raise ValueError("Not one of the lists")
    if on == x.get("on", True):
        return channels_screen(f"{x['name']} is already {'active' if on else 'inactive'}")
    x["on"] = on
    livetv_own.save(DATA, items)
    if on:  # tested again on its own, with its notice
        livetv_own._update(DATA, sid, progress={"done": 0, "total": 0}, seen_result=None)
        threading.Thread(target=_quick, args=(sid,), name="livetv-add", daemon=True).start()
        return channels_screen(f"{x['name']} activated: its channels are being tested; this page shows how far it has got")
    gone = livetv_own.drop(livetv.folder(), sid)
    livetv_jellyfin.refresh_guide(_services())
    return channels_screen(f"{x['name']} deactivated: its {gone} {'channel leaves' if gone == 1 else 'channels leave'} Jellyfin now")


def _list_switch(name, on):
    from . import livetv, livetv_jellyfin
    if name.startswith("own:"):
        return _own_switch(name[4:], on)
    if name not in livetv.LISTS:
        raise ValueError("Not one of the lists")
    label = livetv.LISTS[name][0]
    off = livetv.lists_off(DATA)
    if on == (name not in off):
        return channels_screen(f"{label} is already {'active' if on else 'inactive'}")
    livetv.save_lists_off(DATA, off - {name} if on else off | {name})
    if on:
        with _lock:
            _force["now"] = True
        _wake.set()
        return channels_screen(f"{label} activated: its channels arrive in a few minutes, once it is fetched and tested")
    gone = livetv.empty_list(livetv.folder(), name)
    livetv_jellyfin.refresh_guide(_services())
    return channels_screen(f"{label} deactivated: not fetched, and its {gone} {'channel leaves' if gone == 1 else 'channels leave'} Jellyfin now")


def channels_act(body):
    from . import livetv, livetv_own
    if body.get("action") == "bulk":
        return _bulk(body)
    if body.get("action") == "bulk_ids":  # the channels ticked in a table (DASH-359)
        want = str(body.get("value") or "")
        if want not in ("on", "off"):
            raise ValueError("Choose Activate or Deactivate")
        known = {c["id"] for c in livetv.all_channels(livetv.folder())}
        ids = {str(i) for i in body.get("ids") or []} & known
        if not ids:
            raise ValueError("Tick at least one channel")
        hidden = livetv.hidden_ids(DATA)
        _apply(hidden, hidden - ids if want == "on" else hidden | ids)
        n = len(ids)
        return channels_screen(f"{n} {'channel' if n == 1 else 'channels'} " + ("activated; the lists are being rebuilt, which takes a few minutes" if want == "on"
                               else "deactivated; Jellyfin drops them at its guide refresh, starting now"))
    if body.get("action") == "dismiss":
        livetv_own.dismiss(DATA, str(body.get("id") or ""))
        return channels_screen()
    if body.get("action") != "toggle":
        raise ValueError("Channels can be activated or deactivated")
    cid = str(body.get("id") or "")
    known = {c["id"]: c for c in livetv.all_channels(livetv.folder())}
    if cid not in known:
        raise ValueError("Not one of the channels")
    hidden = livetv.hidden_ids(DATA)
    name = known[cid]["name"]
    if cid in hidden:  # back on: the lists are built again, with it
        _apply(hidden, hidden - {cid})
        return channels_screen(f"{name} activated: the lists are being rebuilt, which takes a few minutes")
    _apply(hidden, hidden | {cid})
    return channels_screen(f"{name} deactivated; Jellyfin drops it at its guide refresh, starting now")


def sources_screen(said=""):
    """The owner's own lists and guides (DASH-359): each address its own row, with Activate or Deactivate, Test
    and Remove; Add takes an M3U playlist, a JSON channel list or an XMLTV guide."""
    from . import livetv_own
    rows = []
    for x in livetv_own.sources(DATA):
        on = x.get("on", True)
        is_list = x.get("kind") == "list"
        has = bool(x.get("guide"))
        where = lambda u: "uploaded file" if u.startswith("file:") else u
        guide = (f"Guide: {where(x['guide'])}" + (f", {x['guide_said']}" if x.get("guide_said") else "")) if has else "Guide: none yet" if is_list else ""
        rows.append({"id": x["id"], "title": x.get("name") or x["url"], "group": "Channel lists" if is_list else "Guides",
                     "detail": " · ".join(v for v in (x.get("said", ""), guide) if v),
                     "address": "Uploaded file" if x["url"].startswith("file:") else x["url"], "state": "off" if not on else x.get("state", "ok"),
                     "on": on, "actions": ["toggle", "test"] + (["attach"] if is_list else []) + (["detach"] if has else []) + ["remove"],
                     **({"attach": {"label": "Change guide" if has else "Add guide", "field": f"Guide for {x.get('name')}",
                                    "hint": "The address of an XMLTV guide (.xml or .xml.gz), or choose a file. Its programmes fill this list's channels, matched by channel id or, failing that, by name.",
                                    "placeholder": "https://example.com/guide.xml.gz", "accept": ".xml,.gz",
                                    "value": "" if not has or x["guide"].startswith("file:") else x["guide"]}} if is_list else {})})
    out = {"type": "list", "title": "Lists and guides", "items": rows, "notices": livetv_own.notices(DATA),
           "add": {"label": "Add a list or guide", "placeholder": "https://example.com/channels.m3u",
                   "hint": "The address of an M3U playlist, a JSON channel list or an XMLTV guide (.xml or .xml.gz). Live TV is for a short, chosen list: up to 2,000 channels each.",
                   "file": {"label": "Or choose a file", "accept": ".m3u,.m3u8,.json,.xml,.gz",
                            "hint": "An M3U, JSON or XMLTV file from this computer, up to 60 MB. Starboard keeps a copy."}},
           "intro": (f"{sum(1 for r in rows if r['on'])} of {len(rows)} active. Channels from your lists are tested, then go into "
                     "Jellyfin as one more tuner, grouped under each list's name; guides fill in their programmes.") if rows
           else "None yet. Channels from your lists are tested, then go into Jellyfin as one more tuner, grouped under each list's name."}
    if said:
        out["said"] = said
    return out


def sources_upload(name, stream, length, sid=""):
    from . import livetv_own
    if sid:  # a guide file for one channel list (DASH-359)
        listed = livetv_own.set_guide_file(DATA, sid, name, stream, length)
        _guides_now()
        return sources_screen(f"Guide added to {listed}: its programmes arrive in a few minutes")
    item = livetv_own.add_file(DATA, name, stream, length)
    return _added(item)


def _added(item):
    """A list just added is tested at once on its own, with its progress on the screen (DASH-359); a guide is read."""
    from . import livetv_own
    if item["kind"] == "list":
        found = int(item.get("found") or 0)
        livetv_own._update(DATA, item["id"], progress={"done": 0, "total": found})  # the notice shows at once
        threading.Thread(target=_quick, args=(item["id"],), name="livetv-add", daemon=True).start()
        return sources_screen(f"Channel list added: {item['said']}. Testing them now; this page shows how far it has got")
    _guides_now()
    return sources_screen(f"Guide added: its programmes arrive in a few minutes")


_build_lock = threading.Lock()  # one build at a time: the hourly run, a list just added, a guide just added


def _quick(sid):
    """Tests one list just added, numbers it in with the rest and tells Jellyfin, without fetching the other lists."""
    from . import livetv, livetv_jellyfin, livetv_own
    s = _read(SETTINGS, {})
    with _build_lock:
        try:
            d = livetv.folder()
            livetv_own.build(d, DATA, only=sid)
            livetv.number_and_logos(d, str(s.get("address") or "").rstrip("/"), bool(s.get("white_logos", True)), livetv.hidden_ids(DATA))
            livetv.mark_built("own", livetv_own.fingerprint(DATA))
            livetv_jellyfin.connect(_services(), {"livetv_jellyfin_folder": s.get("jellyfin_folder") or ""}, "", local_folder=d, host_path="", env={})
            livetv_jellyfin.refresh_guide(_services())
            livetv.write_now(d, DATA)
        except Exception as e:  # kept on the list for its notice
            livetv_own._update(DATA, sid, progress=None, result={"added": 0, "total": 0, "text": f"It stopped: {str(e)[:160]}"})


def _guides_now():
    from . import livetv, livetv_jellyfin, livetv_own

    def work():
        with _build_lock:
            try:
                livetv_own.guide(livetv.folder(), DATA)
                livetv_jellyfin.refresh_guide(_services())
                livetv.write_now(livetv.folder(), DATA)
            except Exception as e:  # the next hourly run tries again
                print(f"Live TV could not read the guides: {e}", flush=True)
    threading.Thread(target=work, name="livetv-guides", daemon=True).start()


def _rebuild():
    with _lock:
        _force["now"] = True
    _wake.set()


def sources_act(body, fetch=None):
    from . import livetv, livetv_jellyfin, livetv_own
    action, sid = body.get("action"), str(body.get("id") or "")
    if action == "add":
        return _added(livetv_own.add(DATA, str(body.get("value") or ""), fetch))
    if action == "dismiss":
        livetv_own.dismiss(DATA, sid)
        return sources_screen()
    if action == "test_all":
        return sources_screen("; ".join(f"{x['name']}: {_test(x, fetch)}" for x in livetv_own.sources(DATA))[:200] or "Nothing to test")
    items = livetv_own.sources(DATA)
    item = next((x for x in items if x["id"] == sid), None)
    if not item:
        raise ValueError("Not one of your lists or guides")
    if action == "test":
        return sources_screen(f"{item['name']}: {_test(item, fetch)}")
    if action == "attach":
        listed = livetv_own.set_guide(DATA, sid, str(body.get("value") or ""), fetch)
        _guides_now()
        return sources_screen(f"Guide added to {listed}: its programmes arrive in a few minutes")
    if action == "detach":
        listed = livetv_own.remove_guide(DATA, sid)
        _guides_now()
        return sources_screen(f"Guide removed from {listed}")
    if action == "toggle":
        item["on"] = not item.get("on", True)
        livetv_own.save(DATA, items)
        if item["on"]:
            _rebuild()
            return sources_screen(f"{item['name']} activated: in Jellyfin in a few minutes, once it is tested")
        gone = livetv_own.drop(livetv.folder(), sid) if item["kind"] == "list" else 0
        if item["kind"] == "guide":
            _rebuild()
        livetv_jellyfin.refresh_guide(_services())
        return sources_screen(f"{item['name']} deactivated" + (f": its {gone} {'channel leaves' if gone == 1 else 'channels leave'} Jellyfin now" if gone else ""))
    if action == "remove":
        livetv_own.save(DATA, [x for x in items if x["id"] != sid])
        livetv_own.forget(DATA, item)
        if item["kind"] == "list":
            livetv_own.drop(livetv.folder(), sid)
            livetv_jellyfin.refresh_guide(_services())
        _rebuild()
        return sources_screen(f"{item['name']} removed")
    raise ValueError("Not something this screen does")


def _test(item, fetch=None):
    from . import livetv_own
    try:
        kind, chans = livetv_own.read(item["url"], fetch, DATA)
        return f"answers: {len(chans)} channels" if chans is not None else "answers: a guide"
    except Exception as e:  # said on the screen, in words
        return f"did not answer: {str(e)[:100]}"


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def answer(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            return self.answer(200, {"ok": True})
        if self.path == "/card":
            return self.answer(200, card())
        if self.path == "/now":
            return self.answer(200, now_card())
        if self.path == "/channels":
            return self.answer(200, channels_screen())
        if self.path == "/sources":
            return self.answer(200, sources_screen())
        return self.answer(404, {"error": "Not found"})

    def do_POST(self):
        if self.path == "/channels":
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return self.answer(200, channels_act(json.loads(self.rfile.read(n) or b"{}")))
            except (ValueError, KeyError) as e:
                return self.answer(400, {"error": str(e)})
        if self.path.startswith("/sources/file?"):  # an uploaded file, streamed here by Starboard (DASH-359)
            import urllib.parse
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            name, sid = q.get("name", [""])[0], q.get("id", [""])[0]
            try:
                return self.answer(200, sources_upload(name, self.rfile, int(self.headers.get("Content-Length") or 0), sid))
            except (ValueError, OSError) as e:
                self.close_connection = True  # the rest of the body may not have been read
                return self.answer(400, {"error": str(e)[:200]})
        if self.path == "/sources":
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return self.answer(200, sources_act(json.loads(self.rfile.read(n) or b"{}")))
            except (ValueError, KeyError) as e:
                return self.answer(400, {"error": str(e)})
            except OSError as e:  # the address did not answer
                return self.answer(400, {"error": f"That address did not answer: {getattr(e, 'reason', e)}"[:200]})
        if self.path == "/run":
            with _lock:
                _force["now"] = True
            _wake.set()
            return self.answer(202, {"said": "Live TV is running now. Testing every channel takes a few minutes."})
        return self.answer(404, {"error": "Not found"})


def main():
    child.ENABLED = os.environ.get("STARBOARD_CHILD_JOBS", "1") != "0"
    threading.Thread(target=loop, name="livetv", daemon=True).start()
    # Inside its own container. It checks for a shutdown every 5 seconds, not twice a second (nothing stops it but
    # the container ending), so an idle plug-in lets a small server's processor rest.
    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever(poll_interval=5)  # nosec B104


if __name__ == "__main__":
    main()
