"""Power hold (plug-in API 1.24, DASH-572): a plug-in that was approved power:hold, such as UPS and power, may ask
Starboard to hold its heavy automatic work while the computer runs on battery.

What a hold stops, while it lasts:
- the automatic starts of Starboard's own background jobs (Live TV, watch history, listening progress, and the
  automatic updates of Starboard, Reelix, apps and plug-ins), the scheduled backups and the scheduled jobs of other
  plug-ins;
- downloads, which are paused the way Download hours pauses them, even when Download hours is off.

What it never stops: anything a person starts themselves, and the jobs of a plug-in that may hold itself.

Every hold ends by itself after the minutes it was given (10 by default, 30 at most) unless the plug-in asks again, so
a plug-in that stops, crashes or loses its network cannot hold Starboard for ever. When a hold ends, whatever was due
starts at the next check, within a minute; downloads that Starboard paused start again at once. The hold lives in
memory only: after Starboard restarts, the plug-in asks again within a minute. It costs nothing while no plug-in asks.
"""

import threading
import time

from . import logs

DEFAULT_MINUTES = 10
MAX_MINUTES = 30
CHECK_EVERY = 60  # seconds a loop that waits for a hold to end looks again

_lock = threading.Lock()
_holds = {}  # plug-in id -> {"name", "reason", "since", "until"}
_wakers = []  # callables that wake the loops waiting on a hold
_changed = threading.Event()  # set whenever a hold starts or ends, for wait_released


def on_change(fn):
    """Registers a function called, with no arguments, whenever a hold starts or ends. It must be quick."""
    if fn not in _wakers:
        _wakers.append(fn)


def _wake():
    _changed.set()
    for fn in list(_wakers):
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - one loop that cannot be woken never stops the rest
            logs.event("warning", "power hold", f"A waiting job was not woken: {e}")


def _expire(now):
    """Drops the holds that ran out. Called with the lock held. Returns the names that ended."""
    ended = [pid for pid, h in _holds.items() if h["until"] <= now]
    names = [_holds.pop(pid)["name"] for pid in ended]
    return names


def clean_reason(reason):
    text = " ".join(str(reason or "").split())[:80]
    return text or "On battery"


def set_hold(plugin, on, reason="", minutes=None, now=None):
    """Starts, renews or ends one plug-in's hold. Returns what is held now: {"held", "reason", "until", "by"}."""
    now = time.time() if now is None else now
    if minutes is None:
        minutes = DEFAULT_MINUTES
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= MAX_MINUTES:
        raise ValueError(f"minutes must be a whole number from 1 to {MAX_MINUTES}")
    with _lock:
        ended = _expire(now)
        before = bool(_holds)
        if on:
            known = _holds.get(plugin["id"])
            _holds[plugin["id"]] = {"name": plugin["name"], "reason": clean_reason(reason),
                                    "since": known["since"] if known else now, "until": now + minutes * 60}
            started = known is None
        else:
            started = False
            if _holds.pop(plugin["id"], None) is not None:
                ended.append(plugin["name"])
        after = bool(_holds)
    for name in ended:
        logs.event("info", "power hold", f"{name}: hold ended")
    if started:
        logs.event("info", "power hold", f"{plugin['name']}: holding heavy jobs ({clean_reason(reason)})")
    if before != after or started or ended:
        _wake()
    return state(now)


def state(now=None):
    """{"held": bool, "reason", "until", "by"}: the hold that lasts longest, or {"held": False}."""
    now = time.time() if now is None else now
    with _lock:
        ended = _expire(now)
        top = max(_holds.items(), key=lambda kv: kv[1]["until"], default=None)
    for name in ended:
        logs.event("info", "power hold", f"{name}: hold ended, not renewed")
    if ended:
        _wake()
    if not top:
        return {"held": False}
    return {"held": True, "reason": top[1]["reason"], "until": int(top[1]["until"]), "by": top[1]["name"]}


def held(exempt=None):
    """True while a hold lasts. `exempt` is the id of a plug-in whose own work is never held by a hold: its own."""
    if not _holds:  # the usual case: no lock, no clock, nothing to do
        return False
    if exempt and set(_holds) <= {exempt}:
        return False
    return state()["held"]


def wait_released(event, step=5):
    """Blocks a loop while a hold lasts, looking every few seconds and at once when a hold starts or ends. True once
    nothing is held; False when `event`, the loop's own wake-up, was set first (the loop then works out what to do
    again, as it does for any other wake-up)."""
    while held():
        if event.is_set():
            return False
        _changed.wait(step)
        _changed.clear()
    return True


def reset():
    """For tests: no holds, no wakers."""
    with _lock:
        _holds.clear()
    del _wakers[:]
