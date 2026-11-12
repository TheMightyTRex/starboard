"""TV network logos (DASH-264): each network's logo (BBC One, Channel 4, Netflix and the rest) for TV, Networks and
the series pages, shown in one colour so they look alike beside the covers (the page's CSS draws them black on light
designs and white on dark ones). Found once per network through Reelix's TMDB lookup of one of its series, kept in
data/library/network-logos.json for 30 days, and looked up in the background, a few at a time, so nothing waits.
A network with no logo gets a plain name tile."""
import json
import os
import threading
import time

from . import services

KEEP = 30 * 86400
PER_RUN = 40
_lock = threading.Lock()
_running = set()


def _path(data_dir):
    return os.path.join(data_dir, "library", "network-logos.json")


def known(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data_dir, data):
    os.makedirs(os.path.dirname(_path(data_dir)), exist_ok=True)
    tmp = _path(data_dir) + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, _path(data_dir))


def logo_of(data_dir, name):
    """The logo address for a network, or "" (none found, or not looked up yet)."""
    return (known(data_dir).get(name.lower()) or {}).get("url", "")


TONES = ("light", "dark", "solid", "invert", "boxed")
MEASURE = 2  # 2 (issues #12 and #13): light and dark ink together is "invert" or "boxed", on a black tile


def tone_of(data_dir, name):
    """How a network's logo looks, measured once by the first browser that shows it: "light" (white or pale on
    nothing), "dark", "solid" (it fills its square with its own background), "invert" (mostly pale paint with dark
    letters, such as Cinemax: shades reversed on a black tile), "boxed" (coloured paint with white letters, such as
    Sky Max: its own colours on a black tile), or "" (not measured yet, or measured by the older rule)."""
    e = known(data_dir).get(name.lower()) or {}
    t = e.get("tone", "")
    return t if t in TONES and (t != "solid" or e.get("v", 1) >= MEASURE) else ""


def set_tone(data_dir, name, tone):
    """Keeps a logo's tone for everyone, so it is never measured again (until its picture changes)."""
    if tone not in TONES:
        raise ValueError("A tone is light, dark, solid, invert or boxed")
    with _lock:
        data = known(data_dir)
        entry = data.get(name.lower())
        if not entry or not entry.get("url"):
            raise LookupError("No logo for that network")
        if entry.get("tone") != tone or entry.get("v", 1) < MEASURE:
            data[name.lower()] = {**entry, "tone": tone, "v": MEASURE}
            _save(data_dir, data)


def _look_up(reelix, series_id, name):
    s = services._api(reelix, f"/series/{int(series_id)}", timeout=15) or {}
    if not s.get("tmdb_id"):
        return ""
    media = services._api(reelix, f"/media/tv/{int(s['tmdb_id'])}", timeout=20) or {}
    companies = media.get("companies") or []
    match = next((c for c in companies if (c.get("name") or "").lower() == name.lower()), None) or (companies[0] if len(companies) == 1 else None)
    url = (match or {}).get("logo_url") or ""
    return url if url.startswith("https://image.tmdb.org/") else ""


def refresh(data_dir, reelix, index):
    """Looks up, in the background, the networks with no logo yet or an old answer (PER_RUN at a time)."""
    key = data_dir
    with _lock:
        if key in _running:
            return
        _running.add(key)

    def run():
        try:
            have = known(data_dir)
            now = time.time()
            first = {}
            for e in index.get("items") or []:
                for name in e.get("g") or []:
                    if name and name.lower() not in first:
                        first[name.lower()] = (name, e["i"])
            todo = [(n, i) for k, (n, i) in first.items() if now - (have.get(k) or {}).get("checked", 0) > KEEP][:PER_RUN]
            for name, series_id in todo:
                try:
                    have[name.lower()] = {"url": _look_up(reelix, series_id, name), "checked": now}
                except services.ServiceError:
                    continue
            if todo:
                _save(data_dir, have)
        finally:
            with _lock:
                _running.discard(key)

    threading.Thread(target=run, name="network-logos", daemon=True).start()
