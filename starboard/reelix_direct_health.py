"""Reelix's direct downloads in Starboard's Reelix health (DASH-218, with DASH-176): a broken yt-dlp, a missing FFmpeg,
an expired Spotify sign-in or YouTube downloads that keep failing show on Apps and System with what to do.

Reelix keeps /downloads/health, /downloads/settings and the direct download queue behind its admin password (checked
against Reelix 0.8.7 and the fork's f2b5196, routes/direct.rs), and Starboard keeps only the manager key, so it cannot
ask in the background. What it can do:
- remember what Reelix said each time the admin password is used for YouTube and Spotify (Settings, Reelix) or the
  From a link queue (Activity, Downloads), in DATA/reelix-direct-health.json, and show those problems until the next
  look, for at most a week;
- ask /downloads/health with the manager key as well, when direct downloads were on at the last look, so a Reelix that
  lets a manager read it (a Reelix change, written in the DASH-218 task row) is used at once;
- read Reelix's own health checks for direct downloads, should Reelix add them to /system/health (services.REELIX_FIX).
Nothing here asks Reelix more often than Starboard's health check already does (once in 5 minutes, when a page asks).
"""
import json
import os
import re
import time

FILE = "reelix-direct-health.json"
KEEP_FOR = 7 * 86400  # a look older than this is not shown: it may be long put right
UPDATE = {"label": "Apps, Updates", "href": "/apps-updates.html"}  # shown as "Put it right in Apps, Updates"
SPOTIFY = {"label": "YouTube and Spotify", "href": "/settings-reelix.html#rx-direct-h"}
# What a failed YouTube download says when YouTube changed and the tools in Reelix are out of date.
YOUTUBE_BROKE = re.compile(r"yt-dlp|sign in to confirm|http error 403|unable to extract|nsig|po token|player response|rustypipe", re.I)


def _path(data_dir):
    return os.path.join(data_dir, FILE)


def read(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            out = json.load(f)
        return out if isinstance(out, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(data_dir, record):
    tmp = _path(data_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f)
    os.replace(tmp, _path(data_dir))


def record(data_dir, state=None, queue=None, now=None):
    """Keeps what Reelix said with the admin password: `state` from reelix_direct.state, `queue` from its queue()."""
    if not data_dir or (state is None and queue is None):
        return
    old = read(data_dir)
    rec = dict(old)
    rec["at"] = now or time.time()
    if state is not None:
        sp = state.get("spotify") or {}
        rec.update(on=bool(state.get("on")), tools=[{"tool": str(t.get("tool") or ""), "ok": bool(t.get("ok"))} for t in state.get("tools") or []],
                   spotify_connected=bool(sp.get("connected")), spotify_problem=str(sp.get("problem") or "")[:300],
                   spotify_was_connected=bool(old.get("spotify_was_connected") or sp.get("connected")))
    if queue is not None:
        failed = [str(d.get("message") or "")[:300] for d in queue.get("items") or []
                  if d.get("state") == "failed" and d.get("source", "youtube") == "youtube"]
        rec["youtube_failed"] = [m for m in failed if YOUTUBE_BROKE.search(m)][-3:]
    try:
        _write(data_dir, rec)
    except OSError:
        pass  # health is a help, never a reason for a change to fail


def problems(rec, live=None, now=None):
    """[{level, message, fix}] for Starboard's Reelix health. `live`: /downloads/health's list when Reelix gave it."""
    now = now or time.time()
    if not rec or not rec.get("on") or now - float(rec.get("at") or 0) > KEEP_FOR:
        return []
    tools = [{"tool": str(t.get("tool") or ""), "ok": bool(t.get("available"))} for t in live] if live is not None else rec.get("tools") or []
    out = []
    for t in tools:
        name = t["tool"].lower()
        if t["ok"]:
            continue
        if "yt-dlp" in name or "youtube" in name:
            out.append({"level": "error", "message": "YouTube downloads cannot start: Reelix cannot run yt-dlp. A newer Reelix brings a working one", "fix": UPDATE})
        elif "ffmpeg" in name:
            out.append({"level": "warning", "message": "YouTube and Spotify downloads cannot be converted: Reelix cannot run FFmpeg", "fix": UPDATE})
        elif "spotify session" in name:
            if rec.get("spotify_was_connected"):
                out.append({"level": "warning", "message": "Spotify is no longer connected: Reelix's Spotify sign-in has run out. Spotify links wait until you connect it again", "fix": SPOTIFY})
        elif "spotify" in name:
            out.append({"level": "warning", "message": "Spotify downloads cannot start: Reelix's Spotify client is not working", "fix": UPDATE})
    if rec.get("spotify_problem") and not any(p["fix"] is SPOTIFY for p in out):
        out.append({"level": "warning", "message": f"Spotify: {rec['spotify_problem'].rstrip('.')}", "fix": SPOTIFY})
    if rec.get("youtube_failed") and not any(p["fix"] is UPDATE and "yt-dlp" in p["message"] for p in out):
        out.append({"level": "warning", "message": f"YouTube downloads are failing ({rec['youtube_failed'][-1].rstrip('.')}). YouTube changes often; a newer Reelix usually puts it right",
                    "fix": UPDATE})
    return out


def wanted(data_dir):
    """True when the last look said direct downloads are on, so the manager key's /downloads/health is worth asking."""
    rec = read(data_dir) if data_dir else {}
    return bool(rec.get("on")) and time.time() - float(rec.get("at") or 0) <= KEEP_FOR
