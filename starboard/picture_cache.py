"""The picture cache (owner, 12 November 2026: "are you caching the images? Remove old images after a period of time,
with a clear cache in the settings"). Every poster, cover and logo Starboard shows is fetched once by the server and
kept in data/posters, so browsers never call image sites. Pictures are fetched again after a week when shown; any
not shown for four weeks are removed; Settings, Performance shows the size and has Clear the picture cache.
Clearing only empties this cache: every picture comes back the next time a page shows it."""
import os
import time

UNUSED = 28 * 86400


def folder(data_dir):
    return os.path.join(data_dir, "posters")


def _files(data_dir):
    for root, _dirs, names in os.walk(folder(data_dir)):
        for n in names:
            yield os.path.join(root, n)


def stats(data_dir):
    count = size = 0
    oldest = None
    for p in _files(data_dir):
        try:
            st = os.stat(p)
        except OSError:
            continue
        count += 1
        size += st.st_size
        oldest = st.st_mtime if oldest is None else min(oldest, st.st_mtime)
    return {"pictures": count, "bytes": size, "oldest_days": int((time.time() - oldest) // 86400) if oldest else 0,
            "unused_days": UNUSED // 86400}


def sweep(data_dir, now=None):
    """Removes pictures not fetched or refreshed for four weeks. Returns how many."""
    now = now or time.time()
    gone = 0
    for p in list(_files(data_dir)):
        try:
            if now - os.path.getmtime(p) > UNUSED:
                os.remove(p)
                gone += 1
        except OSError:
            pass
    return gone


_last = {}


def maybe_sweep(data_dir):
    """At most once a day, whenever a new picture is saved: no thread of its own (lightweight rule)."""
    if time.time() - _last.get(data_dir, 0) > 86400:
        _last[data_dir] = time.time()
        sweep(data_dir)


def clear(data_dir):
    """Empties the cache (only picture files Starboard made; folders stay)."""
    gone = 0
    for p in list(_files(data_dir)):
        try:
            os.remove(p)
            gone += 1
        except OSError:
            pass
    return gone
