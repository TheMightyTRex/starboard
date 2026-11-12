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
    return f"{summary} · {added}" if added else summary


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


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
            said = run_once(force=force)  # first: the finish time is taken after the run
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
    return out


def channels_screen(said=""):
    """Every channel by section, active or inactive, for the plug-in's Channels screen in Starboard (DASH-313), with
    a switch for each whole list, then every channel at once, each region and each section (DASH-359)."""
    from . import livetv
    hidden = livetv.hidden_ids(DATA)
    from . import livetv_own
    own = {x["id"]: x.get("name", "") for x in livetv_own.sources(DATA)}
    chans = livetv.all_channels(livetv.folder())
    rows = []
    for c in sorted(chans, key=lambda c: int(c.get("number") or 0)):
        on = c["id"] not in hidden
        rows.append({"id": c["id"], "title": f"{c['number']} {c['name']}", "group": c.get("section") or "Other",
                     "detail": " · ".join(x for x in (SOURCES.get(c.get("list")) or own.get(c.get("source"), "Your lists"), _region(c)) if x),
                     "state": "ok" if on else "off", "on": on, "actions": ["toggle"]})
    bulk = _lists(chans, hidden)
    if rows:
        bulk.append({"id": "all", "label": "Every channel", "kind": "Channels", "on": sum(1 for r in rows if r["on"]), "total": len(rows)})
    bulk += [{"id": x["id"], "label": x["label"], "kind": x["kind"], "on": sum(1 for i in x["ids"] if i not in hidden), "total": len(x["ids"])}
             for x in _sets(chans)]
    out = {"type": "list", "title": "Channels", "items": rows, "bulk": bulk,
           "intro": f"{sum(1 for r in rows if r['on'])} of {len(rows)} channels are in Jellyfin."}
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


def _list_switch(name, on):
    from . import livetv, livetv_jellyfin
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
    from . import livetv
    if body.get("action") == "bulk":
        return _bulk(body)
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
        rows.append({"id": x["id"], "title": x.get("name") or x["url"], "group": "Channel lists" if x.get("kind") == "list" else "Guides",
                     "detail": x.get("said", ""), "address": "Uploaded file" if x["url"].startswith("file:") else x["url"], "state": "off" if not on else x.get("state", "ok"),
                     "on": on, "actions": ["toggle", "test", "remove"]})
    out = {"type": "list", "title": "Lists and guides", "items": rows,
           "add": {"label": "Add a list or guide", "placeholder": "https://example.com/channels.m3u",
                   "hint": "The address of an M3U playlist, a JSON channel list or an XMLTV guide (.xml or .xml.gz).",
                   "file": {"label": "Or choose a file", "accept": ".m3u,.m3u8,.json,.xml,.gz",
                            "hint": "An M3U, JSON or XMLTV file from this computer, up to 60 MB. Starboard keeps a copy."}},
           "intro": (f"{sum(1 for r in rows if r['on'])} of {len(rows)} active. Channels from your lists are tested, then go into "
                     "Jellyfin as one more tuner, grouped under each list's name; guides fill in their programmes.") if rows
           else "None yet. Channels from your lists are tested, then go into Jellyfin as one more tuner, grouped under each list's name."}
    if said:
        out["said"] = said
    return out


def sources_upload(name, stream, length):
    from . import livetv_own
    item = livetv_own.add_file(DATA, name, stream, length)
    _rebuild()
    what = "Channel list" if item["kind"] == "list" else "Guide"
    return sources_screen(f"{what} added from {item['name']}: {item['said']}. It is tested and added to Jellyfin in a few minutes")


def _rebuild():
    with _lock:
        _force["now"] = True
    _wake.set()


def sources_act(body, fetch=None):
    from . import livetv, livetv_jellyfin, livetv_own
    action, sid = body.get("action"), str(body.get("id") or "")
    if action == "add":
        item = livetv_own.add(DATA, str(body.get("value") or ""), fetch)
        _rebuild()
        what = "Channel list" if item["kind"] == "list" else "Guide"
        return sources_screen(f"{what} added: {item['said']}. It is tested and added to Jellyfin in a few minutes")
    if action == "test_all":
        return sources_screen("; ".join(f"{x['name']}: {_test(x, fetch)}" for x in livetv_own.sources(DATA))[:200] or "Nothing to test")
    items = livetv_own.sources(DATA)
    item = next((x for x in items if x["id"] == sid), None)
    if not item:
        raise ValueError("Not one of your lists or guides")
    if action == "test":
        return sources_screen(f"{item['name']}: {_test(item, fetch)}")
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
            name = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("name", [""])[0]
            try:
                return self.answer(200, sources_upload(name, self.rfile, int(self.headers.get("Content-Length") or 0)))
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
    threading.Thread(target=loop, name="livetv", daemon=True).start()
    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()  # inside its own container  # nosec B104


if __name__ == "__main__":
    main()
