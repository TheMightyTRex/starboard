"""Health and idle stop for every plug-in (DASH-357). Before this, `health` was a Docker health check only for
plug-ins built into Starboard, and `start: when_needed` with `idle_stop_minutes` only wrote a label nobody read.

Health: Starboard asks each active plug-in's health path itself, on the plug-in's own network, when Settings,
Plug-ins is opened (at most once a minute per plug-in, two seconds each, all at once). Nothing is polled in between,
so it costs nothing while nobody looks.

Idle stop: the main (first) container, when it has `start: when_needed`, is stopped once Starboard has not called
it and its network has been quiet for `idle_stop_minutes` (15 when left out), so something else streaming from it,
such as Jellyfin, keeps it running. A thread does this only while such a plug-in is active, waking each minute. The
next call Starboard makes to it (a card, a button, an event, a job, its own screen) starts it again first and waits
up to 20 seconds for it to answer. Only that container: Starboard cannot know when another one is needed, or start
it again, so `when_needed` on any other container is a tester warning and it runs always. Which container is
resting is kept in state.json, so a restart of Starboard still knows to start it.
"""
import concurrent.futures
import os
import socket
import threading
import time
import urllib.error
import urllib.request

from . import logs, plugins_admin as pa

DATA_DIR = None  # set by the server at start; plugin_cards._host has no data folder of its own
HEALTH_EVERY = 60
WAKE_WAIT = 20
_health = {}  # pid -> (checked at, "ok" or the reason)
_last_used = {}  # pid -> when Starboard last called it
_lock = threading.Lock()
_started = time.time()


def _manifest(data_dir, pid):
    return pa._read(os.path.join(pa.folder(data_dir, pid), "manifest.json"), {}) or {}


def _state(data_dir, pid):
    return pa._read(os.path.join(pa.folder(data_dir, pid), "state.json"), {}) or {}


def resting(data_dir, pid):
    return list(_state(data_dir, pid).get("resting") or [])


def _set_resting(data_dir, pid, names):
    st = _state(data_dir, pid)
    st["resting"] = sorted(set(names))
    pa._write(os.path.join(pa.folder(data_dir, pid), "state.json"), st)


def _idle(c):
    return c.get("start") == "when_needed"


# Health -------------------------------------------------------------------------------------------------------

def _ask(pid, main, path):
    from . import plugin_cards
    url = f"http://{plugin_cards._host(pid, main, wake=False)}:{int(main.get('port') or 80)}{path}"
    try:
        with urllib.request.build_opener().open(urllib.request.Request(url, headers={"User-Agent": "Starboard"}), timeout=2) as r:  # nosec B310
            return "ok" if 200 <= r.status < 300 else f"Its health check answered {r.status}"
    except urllib.error.HTTPError as e:
        return f"Its health check answered {e.code}"
    except (TimeoutError, socket.timeout):
        return "Its health check did not answer within 2 seconds"
    except OSError as e:  # urllib wraps a time-out in URLError
        if isinstance(getattr(e, "reason", None), (TimeoutError, socket.timeout)):
            return "Its health check did not answer within 2 seconds"
        return "Starboard could not reach it"


def health(data_dir, listing):
    """{pid: "ok" or why not} for active plug-ins with a health path that are not resting. Cached a minute."""
    now, todo, out = time.time(), [], {}
    for p in listing:
        if p.get("state") != "enabled":
            continue
        m = _manifest(data_dir, p["id"])
        main = (m.get("containers") or [None])[0]
        if not m.get("health") or not main or main.get("name") in resting(data_dir, p["id"]):
            continue
        with _lock:
            seen = _health.get(p["id"])
        if seen and now - seen[0] < HEALTH_EVERY:
            out[p["id"]] = seen[1]
        else:
            todo.append((p["id"], main, m["health"]))
    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(todo))) as pool:
            for (pid, *_), said in zip(todo, pool.map(lambda t: _ask(*t), todo)):
                out[pid] = said
                with _lock:
                    _health[pid] = (now, said)
    return out


# Idle stop ----------------------------------------------------------------------------------------------------

_waking = {}  # pid -> lock, so cards asking at once start it only once


def used(pid, main):
    """Called before each call Starboard makes to a plug-in: notes the time and starts it again if it was resting.
    Returns quietly when it cannot (the call itself then says the plug-in did not answer)."""
    _last_used[pid] = time.time()
    data_dir = DATA_DIR
    if not data_dir:
        return
    with _lock:
        lock = _waking.setdefault(pid, threading.Lock())
    with lock:
        try:
            names = resting(data_dir, pid)
        except (OSError, ValueError):
            return
        if not names:
            return
        ok, text = pa._compose_run(data_dir, pid, "up -d " + " ".join(f"plugin-{pid}-{n}" for n in names))
        if not ok:
            logs.event("warning", "plug-ins", f"{pid} could not be started again: {text.strip()[-160:]}")
            return
        _set_resting(data_dir, pid, [])
        logs.event("info", "plug-ins", f"Started {pid} again: it was needed")
        from . import plugin_cards
        port, until = int(main.get("port") or 80), time.time() + WAKE_WAIT
        while time.time() < until:
            try:
                with socket.create_connection((plugin_cards._host(pid, main, wake=False), port), timeout=1):
                    return
            except OSError:
                time.sleep(0.5)


_traffic = {}  # pid -> (bytes in and out last read, when they last moved)
QUIET_BYTES = 16 * 1024  # less than this in a minute is a health check, not someone using it


def _moved(pid, main, now):
    """When the main container's network last moved by more than QUIET_BYTES. Unknown counts as now (busy), so a
    container Starboard cannot read never rests."""
    from . import containers
    try:
        nets = containers.docker("GET", f"/containers/plugin-{pid}-{main['name']}/stats?stream=false&one-shot=true", timeout=5).get("networks") or {}
        if not nets:  # on the VPN it shares Gluetun's network and Docker gives no figures: never rest it
            return now
        total = sum(int(n.get("rx_bytes", 0)) + int(n.get("tx_bytes", 0)) for n in nets.values())
    except (containers.DockerError, ValueError, AttributeError):
        return now
    before, at = _traffic.get(pid, (None, _started))
    if before is None or total - before > QUIET_BYTES or total < before:
        at = now if before is not None else at
    _traffic[pid] = (total, at)
    return at


def rest_idle(data_dir, now=None, moved=None):
    """Stops the main container of each active plug-in that has start: when_needed, once Starboard has not called
    it and its network has been quiet for its idle_stop_minutes."""
    now = now or time.time()
    moved = moved or _moved
    stopped = []
    for p in pa.listing(data_dir):
        if p.get("state") != "enabled":
            continue
        main = (_manifest(data_dir, p["id"]).get("containers") or [None])[0]
        if not main or not _idle(main) or resting(data_dir, p["id"]):
            continue
        quiet = 60 * int(main.get("idle_stop_minutes") or 15)
        if now - _last_used.get(p["id"], _started) < quiet or now - moved(p["id"], main, now) < quiet:
            continue
        ok, text = pa._compose_run(data_dir, p["id"], f"stop plugin-{p['id']}-{main['name']}")
        if ok:
            _set_resting(data_dir, p["id"], [main["name"]])
            _traffic.pop(p["id"], None)
            stopped.append(p["id"])
            logs.event("info", "plug-ins", f"{p['name']} is resting: nothing used it for {quiet // 60} minutes")
        else:
            logs.event("warning", "plug-ins", f"{p['id']} could not rest: {text.strip()[-160:]}")
    return stopped


def wanted(data_dir):
    """True while an active plug-in's main container has start: when_needed."""
    return any(p.get("state") == "enabled" and _idle((_manifest(data_dir, p["id"]).get("containers") or [{}])[0])
               for p in pa.listing(data_dir))


class Watcher:
    """The idle-stop thread: runs only while wanted(), wakes each minute."""

    def __init__(self, data_dir):
        self.data_dir, self.thread = data_dir, None
        self._lock = threading.Lock()

    def ensure(self):
        with self._lock:
            if self.thread is None and wanted(self.data_dir):
                self.thread = threading.Thread(target=self._loop, name="plugin-idle", daemon=True)
                self.thread.start()

    def _loop(self):
        while True:
            with self._lock:
                if not wanted(self.data_dir):
                    self.thread = None
                    return
            try:
                rest_idle(self.data_dir)
            except Exception as e:  # noqa: BLE001 - one bad plug-in never stops the others resting
                logs.event("warning", "plug-ins", f"Idle plug-ins not checked: {e}")
            time.sleep(60)
