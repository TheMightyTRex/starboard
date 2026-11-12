"""Titles a move into Reelix could not match, held until they do (DASH-253, 13 November 2026).

When Reelix's migrator cannot add a film or series (no TMDB key yet, or TMDB did not know the id), the title would
otherwise be lost: Radarr and Sonarr stop at the takeover. Starboard keeps each one here with the ids Radarr and Sonarr
had for it (TMDB, TVDB, IMDb), in data/stack/reelix-waiting.json, and tries again:

- when a TMDB key is added (Settings, Reelix, or the set-up's Films and series step);
- on a schedule, every six hours, while the list has anything in it;
- when the person chooses Try again on Settings, Your install.

Each try adds the title to Reelix with Reelix's manager key (library.add), with search off, as the move did. A title
that is added, or that Reelix already has, leaves the list. A title with only an IMDb id cannot be added this way and
waits for Add by hand.

Lightweight: one thread, asleep on an event. With an empty list it sleeps until something is added; it never polls.
"""
import json
import os
import threading
import time

from . import stack

FILE = "reelix-waiting.json"
EVERY = 6 * 3600  # seconds between tries while the list has titles in it
KINDS = {"movie": "films", "series": "tv"}
# Why Reelix's migrator did not add a title, when the reason is the match (not a folder or profile it did not move).
MATCH_WORDS = ("tmdb", "tvdb", "match")

_lock = threading.Lock()
_wake = threading.Event()
_thread = None


def _path(data_dir):
    return os.path.join(stack.folder(data_dir), FILE)


def read(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, list) else []
    except (OSError, ValueError):
        return []


def _write(data_dir, items):
    os.makedirs(stack.folder(data_dir), mode=0o700, exist_ok=True)
    with open(_path(data_dir) + ".new", "w", encoding="utf-8") as f:
        json.dump(items, f, indent=1)
    os.replace(_path(data_dir) + ".new", _path(data_dir))


def is_unmatched(item):
    """A film or series the migrator skipped, or failed to add, because of its match."""
    return item.get("category") in KINDS and any(w in str(item.get("why") or "").lower() for w in MATCH_WORDS)


def entry(source, item, ids):
    """One waiting title: its kind, name, the ids its old app had, why it did not move, and where it came from."""
    return {"kind": item["category"], "title": item.get("name") or "Untitled", "source": source,
            "key": item.get("key") or "", "why": item.get("why") or "", "tmdb": ids.get("tmdb") or None,
            "tvdb": ids.get("tvdb") or None, "imdb": ids.get("imdb") or None, "added": time.time(), "tries": 0,
            "last_try": None, "last_error": ""}


def hold(data_dir, entries):
    """Adds titles to the list (a title already there by its old app's key is not added twice) and wakes the retry."""
    if not entries:
        return 0
    with _lock:
        items = read(data_dir)
        have = {(i["source"], i["key"]) for i in items if i.get("key")}
        new = [e for e in entries if not e.get("key") or (e["source"], e["key"]) not in have]
        _write(data_dir, items + new)
    _wake.set()
    return len(new)


def forget(data_dir, index_key):
    """Takes one title off the list (the person added it by hand)."""
    with _lock:
        items = read(data_dir)
        kept = [i for i in items if f"{i['source']}|{i['key']}" != index_key]
        _write(data_dir, kept)
    return len(items) - len(kept)


def add_key(item):
    """The key library.add takes for a waiting title, or None when it has no id Reelix adds by."""
    if item["kind"] == "movie" and item.get("tmdb"):
        return "films", f"tmdb:{int(item['tmdb'])}"
    if item["kind"] == "series" and item.get("tvdb"):
        return "tv", f"tvdb:{int(item['tvdb'])}"
    if item["kind"] == "series" and item.get("tmdb"):
        return "tv", f"tmdb:{int(item['tmdb'])}"
    return None


def try_again(data_dir, reelix, add=None):
    """Tries each waiting title once. Returns {"added": n, "waiting": n}. `add(kind, key)` adds one (library.add)."""
    if add is None:
        from . import library

        def add(kind, key):
            return library.add(data_dir, reelix, kind, key, {"search": False})
    with _lock:
        items = read(data_dir)
    added, kept = 0, []
    for n, item in enumerate(items):
        target = add_key(item)
        if not target:
            item["last_error"] = "No TMDB or TVDB id: add it by hand"
            kept.append(item)
            continue
        item["tries"] = int(item.get("tries") or 0) + 1
        item["last_try"] = time.time()
        try:
            add(*target)
            added += 1
            continue
        except Exception as e:  # noqa: BLE001  any answer but success keeps the title waiting
            text = str(e)
            if "already" in text.lower() or "exists" in text.lower():
                added += 1
                continue
            item["last_error"] = text[:200]
            kept.append(item)
            if "tmdb" in text.lower() and ("configur" in text.lower() or "key" in text.lower()):
                kept += items[n + 1:]  # no TMDB key yet: none of the rest can match either, so they wait for one
                break
    with _lock:
        now = read(data_dir)  # titles held while this ran stay
        tried = {(i["source"], i["key"]) for i in items}
        _write(data_dir, kept + [i for i in now if (i["source"], i["key"]) not in tried])
    return {"added": added, "waiting": len(kept)}


def nudge():
    """Something changed that may make titles match (a TMDB key was added): try again now."""
    _wake.set()


def start(data_dir, get_reelix):
    """The background retry: asleep while the list is empty, otherwise a try every six hours or when nudged."""
    global _thread
    if _thread and _thread.is_alive():
        return

    def loop():
        while True:
            waiting = bool(read(data_dir))
            _wake.wait(EVERY if waiting else None)
            _wake.clear()
            if not read(data_dir):
                continue
            reelix = get_reelix()
            if not reelix:
                continue
            try:
                try_again(data_dir, reelix)
            except Exception:  # noqa: BLE001  the next try is in six hours
                pass
    _thread = threading.Thread(target=loop, name="reelix-waiting", daemon=True)
    _thread.start()
