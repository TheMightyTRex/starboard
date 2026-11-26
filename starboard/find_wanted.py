"""Find all wanted (owner, 26 November 2026): ask Reelix to search for everything a Library tab wants, without flooding the
sites. Starboard sends the searches itself, a few at a time, so it knows how far it has got and can stop.

The limits (the owner's, 26 November 2026), each one a number below:
  GROUP     10 searches in each group
  GAP       one group a minute
  MAX_RUN   at most 100 things in one run (the rest wait for the next run)
  RECENT    anything this run searched in the last 24 hours is left out
  REST      15 minutes after a run before the next
  one run at a time, and while Download hours pause downloads the run waits, then carries on

Films, TV, music, books and audiobooks use Reelix's own search for the ids (starboard/wanted.py, the same route as the
Wanted pages). Radio asks Reelix to search each followed show that has wanted episodes (POST /radio/shows/{id}/search),
because Reelix has no search for the whole of Radio."""
import json
import os
import threading
import time

from . import library, services, wanted

GROUP = 10
GAP = 60
MAX_RUN = 100
RECENT = 24 * 3600
REST = 15 * 60
HOURS_POLL = 30  # seconds between looks at Download hours while the run waits
MAX_PAGES = 10  # pages of 50 read to find what to search

KIND = {"films": "movie", "tv": "episode", "music": "album", "books": "ebook", "audiobooks": "audiobook"}
NOUN = {"films": ("film", "films"), "tv": ("episode", "episodes"), "music": ("album", "albums"),
        "books": ("book", "books"), "audiobooks": ("audiobook", "audiobooks"), "radio": ("episode", "episodes")}

_lock = threading.RLock()
_run = {}      # the run now, or the last one: state, tab, total, searched, started, next_at, said
_stop = threading.Event()
_last_end = 0.0


def _file(data_dir):
    return os.path.join(data_dir, "library", "find-wanted.json")


def _recent(data_dir):
    """{"kind:id": time} for what a run searched in the last 24 hours."""
    try:
        with open(_file(data_dir), encoding="utf-8") as f:
            seen = json.load(f)
    except (OSError, ValueError):
        return {}
    cut = time.time() - RECENT
    return {k: v for k, v in seen.items() if isinstance(v, (int, float)) and v >= cut}


def _remember(data_dir, tab, ids):
    seen = _recent(data_dir)
    now = time.time()
    seen.update({f"{tab}:{i}": now for i in ids})
    os.makedirs(os.path.dirname(_file(data_dir)), mode=0o700, exist_ok=True)
    fd = os.open(_file(data_dir), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(seen, f)


def _candidates(all_services, tab):
    """(everything wanted on the tab as a count, the ids a search covers, in Reelix's order). Radio's ids are shows."""
    if tab == "radio":
        reelix = library.reelix_of(all_services)
        if not reelix:
            raise ValueError("Add Reelix in Settings, Manage apps, with its key, to find what is wanted")
        total, ids = 0, []
        for page in library._pages(reelix, "/radio/shows", {"followed": "true"}):
            for show in page:
                n = int((show.get("statistics") or {}).get("wanted_count") or 0)
                if n and (show.get("follow") or "all") != "none":
                    total += n
                    ids.append(show["id"])
        return total, ids
    kind = KIND[tab]
    ids, total = [], 0
    for page in range(1, MAX_PAGES + 1):
        got = wanted.listing(all_services, "missing", kind, page)
        total = got["total"]
        ids += [w["id"] for w in got["items"]]
        if len(ids) >= total or not got["items"]:
            break
    return total, ids


def preview(all_services, data_dir, tab):
    """What a run would do, before anyone says yes: the count first, what is left out, how long it takes."""
    if tab not in NOUN:
        raise ValueError("Choose a Library tab")
    total, ids = _candidates(all_services, tab)
    seen = _recent(data_dir)
    fresh = [i for i in ids if f"{tab}:{i}" not in seen]
    todo = fresh[:MAX_RUN]
    units = len(todo)
    groups = -(-units // GROUP)
    one, many = NOUN[tab]
    return {"tab": tab, "noun": [one, many], "wanted": total, "units": "shows" if tab == "radio" else many,
            "left_out": len(ids) - len(fresh), "to_search": units, "more": max(0, len(fresh) - units),
            "minutes": max(1, round(max(0, groups - 1) * GAP / 60)) if units else 0,
            "group": GROUP, "gap": GAP, "max_run": MAX_RUN, "rest": max(0, int(_last_end + REST - time.time())),
            "run": status()}


def status():
    with _lock:
        out = dict(_run)
    if out.get("state") == "running" and out.get("next_at"):
        out["next_in"] = max(0, int(out["next_at"] - time.time()))
    return out


def stop():
    """Stops after the group that is going now. Nothing is undone."""
    with _lock:
        if _run.get("state") not in ("running", "waiting"):
            return status()
    _stop.set()
    return status()


def start(all_services, data_dir, tab, paused=lambda: False, sleep=time.sleep):
    """Starts a run in a thread and returns its state at once. One run at a time, and a rest after each."""
    global _last_end
    if tab not in NOUN:
        raise ValueError("Choose a Library tab")
    with _lock:
        if _run.get("state") in ("running", "waiting"):
            raise ValueError("A search for wanted things is running already")
        wait = int(_last_end + REST - time.time())
        if wait > 0:
            raise ValueError(f"The last search finished a moment ago. Try again in {max(1, round(wait / 60))} minutes")
        plan = preview(all_services, data_dir, tab)
        if not plan["to_search"]:
            raise ValueError("Nothing is wanted that has not been searched for in the last day")
        _, ids = _candidates(all_services, tab)
        seen = _recent(data_dir)
        todo = [i for i in ids if f"{tab}:{i}" not in seen][:MAX_RUN]
        _stop.clear()
        _run.clear()
        _run.update({"state": "running", "tab": tab, "noun": plan["noun"], "units": plan["units"], "total": len(todo),
                     "wanted": plan["wanted"], "searched": 0, "started": time.time(), "next_at": 0, "waiting_for_hours": False})
    threading.Thread(target=_work, args=(all_services, data_dir, tab, todo, paused, sleep), daemon=True).start()
    return status()


def _search(all_services, tab, ids):
    if tab == "radio":
        reelix = library.reelix_of(all_services)
        for show in ids:
            services._api(reelix, f"/radio/shows/{int(show)}/search", method="POST", body={})
    else:
        wanted.search(all_services, "missing", KIND[tab], ids)


def _nap(seconds, sleep):
    """Waits in short steps, so Stop is heard within a second or two."""
    end = time.time() + seconds
    while time.time() < end and not _stop.is_set():
        sleep(min(1, max(0, end - time.time())))


def _work(all_services, data_dir, tab, todo, paused, sleep):
    global _last_end
    state, said = "done", ""
    try:
        for n in range(0, len(todo), GROUP):
            while paused() and not _stop.is_set():  # Download hours: wait, then carry on
                with _lock:
                    _run["waiting_for_hours"] = True
                _nap(HOURS_POLL, sleep)
            with _lock:
                _run["waiting_for_hours"] = False
            if _stop.is_set():
                state = "stopped"
                break
            group = todo[n:n + GROUP]
            _search(all_services, tab, group)
            _remember(data_dir, tab, group)
            with _lock:
                _run["searched"] = n + len(group)
                more = n + GROUP < len(todo)
                _run["next_at"] = time.time() + GAP if more else 0
            if more:
                _nap(GAP, sleep)
    except (services.ServiceError, ValueError) as e:
        state, said = "failed", str(e)
    after = None
    try:
        after = _candidates(all_services, tab)[0]
    except (services.ServiceError, ValueError):
        pass
    with _lock:
        _run.update({"state": state, "said": said, "still_wanted": after, "next_at": 0, "ended": time.time()})
        _last_end = time.time()


def _reset_for_tests():
    global _last_end
    with _lock:
        _run.clear()
        _last_end = 0.0
    _stop.clear()
