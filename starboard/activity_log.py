"""Activity, History, Across apps (DASH-68): what was added, what failed and what was upgraded across the apps,
newest first, small and capped. A first step towards the weekly summary saying what was added (N8).

Nothing runs for it. Each entry is written by work Starboard already does:
- an update that finished or failed (update_runs, self_update), as "upgraded" or "failed";
- an alert for a problem (Watch.alert: an app that stopped answering, a disk, a backup), as "failed";
- an app or plug-in added in Starboard, as "added";
- what Reelix, Sonarr, Radarr, Lidarr and Readarr added, upgraded or could not download, read from their own history
  only when the Across apps page is opened (one small page each, the same reads History and Recently finished make).

One file, data/activity-history.jsonl: one short JSON line per entry, never more than CAP entries (the oldest go
first) and each text cut short: usually under 100 KB, never more than half a megabyte. Personal details are removed as
in Starboard's log.
At rest it costs nothing: no thread, no timer, and the file is read only when the page or the weekly summary asks.
"""

import datetime as dt
import json
import os
import threading
import time

from . import logs

CAP = 500        # entries kept; the help states this number (docs/help/topics/check-what-happened-across-your-apps.md)
SLACK = 100      # the file is rewritten to CAP only once it holds CAP + SLACK lines, so most writes are one append
PAGE = 50
KINDS = ("added", "failed", "upgraded")
WORDS = {"added": "Added", "failed": "Failed", "upgraded": "Upgraded"}
TONES = {"added": "success", "failed": "danger", "upgraded": "info"}
FILE = "activity-history.jsonl"
CLEARED = ".cleared"  # beside the file: when Delete history was last used
LIMITS = {"app": 60, "what": 200, "detail": 300, "key": 120}

_lock = threading.Lock()
_state = {"dir": None, "lines": None}  # the running app's data folder, and how many lines the file holds


def start(data_dir):
    """Names the data folder, so any module can write with note(). Opens nothing."""
    with _lock:
        _state.update(dir=data_dir, lines=None)


def _path(data_dir):
    return os.path.join(data_dir, FILE)


def _read(data_dir):
    """Every entry, oldest first. A line that cannot be read is left out."""
    out = []
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if isinstance(e, dict) and e.get("kind") in KINDS:
                    out.append(e)
    except OSError:
        pass
    return out


def _write_all(data_dir, entries):
    tmp = _path(data_dir) + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        f.writelines(json.dumps(e, separators=(",", ":"), ensure_ascii=False) + "\n" for e in entries)
    os.replace(tmp, _path(data_dir))


def _entry(kind, app, what, detail="", when=None, key=""):
    if kind not in KINDS:
        raise ValueError("Choose added, failed or upgraded")
    clean = lambda text, n: " ".join(logs.redact(text or "").split())[:n]  # noqa: E731  one line, nothing personal
    e = {"t": int(when if when is not None else time.time()), "kind": kind, "app": clean(app, LIMITS["app"]),
         "what": clean(what, LIMITS["what"])}
    if detail:
        e["detail"] = clean(detail, LIMITS["detail"])
    if key:
        e["key"] = str(key)[:LIMITS["key"]]
    return e


def record(data_dir, kind, app, what, detail="", when=None, key=""):
    """Adds one entry. With a key, an entry that is already there is not added again. True when it was written."""
    return bool(record_many(data_dir, [(kind, app, what, detail, when, key)]))


def record_many(data_dir, rows):
    """Adds several entries, each (kind, app, what, detail, when, key), with one read of the file at most. Returns
    how many were new."""
    new = [_entry(*r) for r in rows]
    if not new:
        return 0
    with _lock:
        keyed = any(e.get("key") for e in new)
        known = _state["lines"] if _state["dir"] == data_dir else None
        if keyed or known is None or known + len(new) > CAP + SLACK:
            entries = _read(data_dir)
            have = {e["key"] for e in entries if e.get("key")}
            new = [e for e in new if not e.get("key") or e["key"] not in have and not have.add(e["key"])]
            if not new:
                if _state["dir"] == data_dir:
                    _state["lines"] = len(entries)
                return 0
            if len(entries) + len(new) > CAP + SLACK:
                entries = sorted(entries + new, key=lambda e: e["t"])[-CAP:]
                _write_all(data_dir, entries)
                if _state["dir"] == data_dir:
                    _state["lines"] = len(entries)
                return len(new)
            known = len(entries)
        with open(os.open(_path(data_dir), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "a", encoding="utf-8") as f:
            f.writelines(json.dumps(e, separators=(",", ":"), ensure_ascii=False) + "\n" for e in new)
        if _state["dir"] == data_dir:
            _state["lines"] = known + len(new)
    return len(new)


def note(kind, app, what, detail="", key=""):
    """Writes to the running app's history, if there is one (tests and tools run without). Never raises: the history
    is a help, never a stop."""
    data_dir = _state["dir"]
    if not data_dir:
        return False
    try:
        return record(data_dir, kind, app, what, detail, key=key)
    except Exception as e:  # noqa: BLE001
        logs.event("warning", "history", f"The activity history was not written: {e}")
        return False


def listing(data_dir, which="all", page=1):
    """One page, newest first: {"items", "total", "page", "page_size", "cap", "counts"}."""
    if which != "all" and which not in KINDS:
        raise ValueError("Choose Everything, Added, Failed or Upgraded")
    page = max(1, int(page))
    entries = sorted(_read(data_dir), key=lambda e: e["t"], reverse=True)[:CAP]
    counts = {k: sum(1 for e in entries if e["kind"] == k) for k in KINDS}
    shown = [e for e in entries if which == "all" or e["kind"] == which]
    items = [{"when": dt.datetime.fromtimestamp(e["t"], dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": e["kind"],
              "event": WORDS[e["kind"]], "tone": TONES[e["kind"]], "app": e.get("app", ""), "what": e.get("what", ""),
              "detail": e.get("detail", "")} for e in shown[(page - 1) * PAGE:page * PAGE]]
    return {"items": items, "total": len(shown), "page": page, "page_size": PAGE, "cap": CAP, "counts": counts}


def week(data_dir, now=None, days=7):
    """How many of each kind in the last `days` days, for the weekly summary."""
    since = (now if now is not None else time.time()) - days * 86400
    out = dict.fromkeys(KINDS, 0)
    for e in _read(data_dir):
        if e["t"] >= since:
            out[e["kind"]] += 1
    return out


def clear(data_dir, now=None):
    """Delete history: empties the file and notes when, so the apps' older entries stay out. Returns how many went."""
    with _lock:
        gone = len(_read(data_dir))
        _write_all(data_dir, [])
        with open(os.open(_path(data_dir) + CLEARED, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            f.write(str(int(now if now is not None else time.time())))
        if _state["dir"] == data_dir:
            _state["lines"] = 0
    return gone


# What the apps did, read from their own history when the page is opened ---------------------------------

def _stamp(iso):
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return int(time.time())


REELIX_KINDS = {"imported": "added", "download_failed": "failed", "import_failed": "failed"}


def from_reelix(name, items):
    """Rows for record_many from the items activity.history() returns (Reelix's history, newest first)."""
    rows = []
    for h in items or []:
        kind = REELIX_KINDS.get(h.get("event_type"))
        if not kind:
            continue
        if kind == "added" and h.get("is_upgrade"):
            kind = "upgraded"
        what = h.get("what") or h.get("release") or ""
        detail = " · ".join(x for x in (h.get("quality"), h.get("message") if kind == "failed" else "") if x)
        rows.append((kind, name, what, detail, _stamp(h.get("date")), f"reelix:{h.get('id')}"))
    return rows


def from_recent(items):
    """Rows for record_many from services.recent() (what Sonarr, Radarr, Lidarr and Readarr added)."""
    return [("added", r.get("service_name", ""), " ".join(x for x in (r.get("title"), (r.get("detail") or "").split(" · ")[0]) if x and x != "Film"),
             r.get("quality", ""), _stamp(r.get("when")), f"arr:{r.get('service_name', '')}:{r.get('when', '')}:{r.get('title', '')}")
            for r in items or []]


def cleared_at(data_dir):
    """When Delete history was last used (seconds), or 0."""
    try:
        with open(_path(data_dir) + CLEARED, encoding="utf-8") as f:
            return int(f.read(20) or 0)
    except (OSError, ValueError):
        return 0


def gather(data_dir, all_services):
    """Folds in what the apps report, for the Across apps page. One small page from each app; an app that does not
    answer is named in the answer and nothing else changes. Nothing from before the last Delete history comes back."""
    from . import activity, services
    notes = []
    rows = []
    if services.reelix_native(all_services):
        try:
            reelix = activity._reelix(all_services)
            answer = services._api(reelix, "/history", {"page": 1, "page_size": PAGE}) or {}
            items = []
            for h in answer.get("items") or []:
                q, data = (h.get("quality") or {}).get("quality") or "", h.get("data") or {}
                items.append({"id": h.get("id"), "event_type": h.get("event_type"), "date": h.get("date") or "",
                              "what": activity._what(h.get("media"), h.get("episode")), "release": h.get("source_title") or "",
                              "quality": q if isinstance(q, str) else "", "is_upgrade": bool(data.get("is_upgrade")),
                              "message": str(data.get("message") or data.get("reason") or "")})
            rows += from_reelix(reelix.get("name") or "Reelix", items)
        except (services.ServiceError, ValueError) as e:
            notes.append(f"Reelix did not answer, so its newest entries are not here yet: {e}")
    others = [s for s in all_services if s.get("icon") != "reelix"]  # Reelix is read once, above
    if services._arrs(others):
        recent = services.recent(others)
        rows += from_recent(recent.get("items"))
        notes += [f"{e['message']}, so its newest entries are not here yet" for e in recent.get("errors") or []]
    edge = cleared_at(data_dir)
    rows = [r for r in rows if r[4] >= edge]
    record_many(data_dir, rows)
    return notes
