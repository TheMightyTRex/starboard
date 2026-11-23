"""Remove drop shadows (DASH-536): the one place that says what the setting is when nobody has answered it.

The answer is kept in config.json as "shadows_off" (None until answered, then True or False). A Lite install (Reelix
Lite, the route Starboard recommends) starts with the shadows off, because they cost a little processor on every
scroll; any other install starts with them on. The set-up (browser and terminal), the Settings page and the pages'
first paint all ask here, so they cannot disagree. Switching between Lite and the full Reelix changes only an
unanswered setting: an answer the person gave is never overwritten.
"""
import os

NOTE = "Drop shadows cost a little processor on every scroll; turning them off helps small and older computers"
_memo = {}


def default_off(reelix_edition):
    """The default for an install with this Reelix: "lite" starts with no shadows; "full" or no Reelix (None) keeps them."""
    return reelix_edition == "lite"


def installed_edition(data_dir):
    """"lite" or "full" for the Reelix Starboard runs now (the route recorded in data/stack), else None. The answer is
    remembered until the stack's files change, so asking on every page costs one stat call."""
    from . import stack
    files = [os.path.join(stack.folder(data_dir), n) for n in ("compose.yaml", ".env")]
    try:
        stamp = tuple((st.st_mtime_ns, st.st_size, st.st_ino) for st in map(os.stat, files))
    except OSError:
        stamp = None
    hit = _memo.get(data_dir)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        choice = stack.current_choice(data_dir) or {}
    except Exception:  # noqa: BLE001  an unreadable stack is no Reelix, so the shadows stay
        choice = {}
    edition = choice.get("reelix_edition") if "reelix" in (choice.get("apps") or []) else None
    _memo[data_dir] = (stamp, edition)
    return edition


def effective_off(data, data_dir):
    """Whether shadows are removed now: the person's answer, else the default for the install."""
    answer = data.get("shadows_off")
    if isinstance(answer, bool):
        return answer
    return default_off(installed_edition(data_dir))
