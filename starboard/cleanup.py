"""System, Clean up (DASH-77): what Starboard moved aside or left behind, and the holding folder.

Owner rule: Starboard never deletes anything for good by itself. It moves things aside (a removed plug-in goes to
data/plugins/.removed), and this page lists them with their sizes. The person moves what they do not need to the
holding folder (data/holding), from where each can be put back, or deleted for good by the person, after a danger
dialog that says it cannot be undone and the Starboard password.

What is left over:
- removed plug-ins, in data/plugins/.removed;
- (old saved copies of the settings are not listed: Starboard keeps those of the last versions chosen in Settings,
  Updates, Restore and removes older ones itself, DASH-109);
- a full backup's work folder left by one that did not finish (data/backup-work), when no backup is running;
- update.sh's backups (backups/ beside data/, seen only when Starboard runs without Docker) beyond the number
  update.sh keeps (the same setting, backup_keep_versions, 5 unless changed).

Sizes are read only when the page asks, never in the background. Each item is named to the browser by an id made
from its path, and the path is found again from the id on this computer, so a request can never name a path.
"""

import hashlib
import json
import os
import shutil
import time

HOLDING = "holding"
SIZE_LIMIT = 200_000  # files counted at most for one item; the size then says "at least"


def _size(path):
    """Bytes in a file or folder (links not followed), and whether the count stopped at SIZE_LIMIT files."""
    if os.path.islink(path) or os.path.isfile(path):
        try:
            return os.lstat(path).st_size, False
        except OSError:
            return 0, False
    total, seen, stack = 0, 0, [path]
    while stack:
        here = stack.pop()
        try:
            with os.scandir(here) as entries:
                for e in entries:
                    seen += 1
                    if seen > SIZE_LIMIT:
                        return total, True
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total, False


def _id(path):
    return hashlib.sha256(os.path.realpath(path).encode()).hexdigest()[:16]


def _item(path, kind, what, data_dir):
    size, more = _size(path)
    try:
        when = os.lstat(path).st_mtime
    except OSError:
        when = 0
    shown = os.path.relpath(path, os.path.dirname(os.path.abspath(data_dir)))
    return {"id": _id(path), "kind": kind, "what": what, "path": shown, "size": size, "at_least": more, "when": when,
            "movable": _same_disk(path, data_dir)}


def _same_disk(path, data_dir):
    try:
        return os.lstat(path).st_dev == os.stat(data_dir).st_dev
    except OSError:
        return False


def _candidates(data_dir, backup_running=False):
    """(path, kind, what) for everything left over, newest first within each kind."""
    out = []
    removed = os.path.join(data_dir, "plugins", ".removed")
    if os.path.isdir(removed) and not os.path.islink(removed):
        for name in sorted(os.listdir(removed), reverse=True):
            out.append((os.path.join(removed, name), "plugin", f"A removed plug-in: {name.rsplit('-', 2)[0] or name}"))
    work = os.path.join(data_dir, "backup-work")
    if os.path.isdir(work) and not os.path.islink(work) and not backup_running:
        out.append((work, "work", "What a full backup that did not finish left behind"))
    updates = os.path.join(os.path.dirname(os.path.abspath(data_dir)), "backups")
    if os.path.isdir(updates) and not os.path.islink(updates):
        names = sorted((n for n in os.listdir(updates) if not n.startswith(".")), reverse=True)
        for name in names[_keep_updates(data_dir):]:
            out.append((os.path.join(updates, name), "update", "A backup update.sh made before an update"))
    return out


def _keep_updates(data_dir):
    """How many update.sh backups update.sh keeps: Settings, Updates, Restore's choice (DASH-109), 5 unless changed."""
    try:
        with open(os.path.join(data_dir, "config.json"), encoding="utf-8") as f:
            n = json.load(f).get("backup_keep_versions", 5)
        return n if isinstance(n, int) and 1 <= n <= 50 else 5
    except (OSError, ValueError):
        return 5


def left_over(data_dir, backup_running=False):
    return [_item(p, k, w, data_dir) for p, k, w in _candidates(data_dir, backup_running)]


def _holding_dir(data_dir):
    return os.path.join(data_dir, HOLDING)


def holding(data_dir):
    """What is in the holding folder, newest first, each with where it came from."""
    folder = _holding_dir(data_dir)
    out = []
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder), reverse=True):
        path = os.path.join(folder, name)
        if name.endswith(".from.json") or os.path.islink(path):
            continue
        note = _note(path)
        item = _item(path, note.get("kind", "other"), note.get("what", "Moved here by hand"), data_dir)
        item.update({"from": note.get("from", ""), "held": note.get("held", item["when"])})
        out.append(item)
    return out


def _note(path):
    try:
        with open(path + ".from.json", encoding="utf-8") as f:
            note = json.load(f)
        return note if isinstance(note, dict) else {}
    except (OSError, ValueError):
        return {}


def summary(data_dir, backup_running=False):
    left, held = left_over(data_dir, backup_running), holding(data_dir)
    return {"left_over": left, "holding": held, "left_over_size": sum(i["size"] for i in left),
            "holding_size": sum(i["size"] for i in held), "holding_path": os.path.join(os.path.basename(os.path.abspath(data_dir)), HOLDING)}


def hold(data_dir, ids, backup_running=False):
    """Moves the chosen left-over items to the holding folder, with a note of where each came from. Returns what moved."""
    wanted = set(ids or [])
    if not wanted:
        raise ValueError("Choose what to move to the holding folder")
    folder = _holding_dir(data_dir)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    moved = []
    for path, kind, what in _candidates(data_dir, backup_running):
        if _id(path) not in wanted:
            continue
        if not _same_disk(path, data_dir):
            continue  # moving it would copy it to another disk: left where it is, and said on the page
        stamp = time.strftime("%Y-%m-%d-%H%M%S")
        target = os.path.join(folder, f"{stamp}-{os.path.basename(path)}")
        n = 1
        while os.path.lexists(target):
            n += 1
            target = os.path.join(folder, f"{stamp}-{n}-{os.path.basename(path)}")
        os.rename(path, target)
        with open(target + ".from.json", "w", encoding="utf-8") as f:
            json.dump({"from": path, "kind": kind, "what": what, "held": time.time()}, f)
        moved.append(what)
    if not moved:
        raise ValueError("Nothing was moved: the list has changed. Look again")
    return moved


def _held_path(data_dir, item_id):
    folder = _holding_dir(data_dir)
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not name.endswith(".from.json") and not os.path.islink(path) and _id(path) == item_id:
                return path
    raise ValueError("That is not in the holding folder any more. Look again")


def put_back(data_dir, item_id):
    """Moves one item from the holding folder back where it came from, if that place is free."""
    path = _held_path(data_dir, item_id)
    origin = _note(path).get("from", "")
    base = os.path.dirname(os.path.abspath(data_dir))
    real = os.path.realpath(origin) if origin else ""
    if not origin or not (real == base or real.startswith(base + os.sep)):
        raise ValueError("Starboard does not know where this came from. Move it back by hand")
    if os.path.lexists(origin):
        raise ValueError("Something with the same name is there now, so it was left in the holding folder")
    os.makedirs(os.path.dirname(origin), exist_ok=True)
    os.rename(path, origin)
    try:
        os.remove(path + ".from.json")
    except OSError:
        pass
    return origin


def delete_for_good(data_dir, item_id):
    """Deletes one item in the holding folder for good. Only ever called after the person confirmed it in the danger
    dialog with their password: Starboard never calls it by itself."""
    path = _held_path(data_dir, item_id)
    size, _ = _size(path)
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    try:
        os.remove(path + ".from.json")
    except OSError:
        pass
    return size
