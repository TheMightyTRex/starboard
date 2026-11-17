"""Copy issues for an AI helper (DASH-434): every download in the queue that needs attention or failed, with all
its details, as Markdown with a short prompt at the top, ready to paste into a chat with an AI helper.

Owner, 14 November 2026: "For activity > Downloads > Queue - I want an export of the issues with detailed
information so I can paste them in here and get them to be looked at automatically."

- Gathered only when asked (the button on Activity, Downloads, Queue, or GET /api/v1/downloads/issues): one call to
  each app's queue, nothing on a timer (lightweight rule). The everyday queue (services.queue) stays as small as
  it was; this asks for the fuller records only here.
- Reelix's own queue (/api/v1/queue) is read when Starboard has Reelix's key, for its ids, indexer and paths; its
  Sonarr-style addresses are then skipped, so nothing shows twice. Sonarr, Radarr, Lidarr and Readarr are read
  from their /queue as before.
- Never a key, password, token, private address or a full download address: every text goes through clean(),
  paths through path(), and the keys and passwords Starboard knows are taken out wherever they appear.
- What Starboard already tried: the queue actions from the page and the API, Choose the episode, and how long the
  watch has seen it needing attention. Kept in DATA/queue-tried.json, the newest 200, for 14 days.
"""
import datetime as dt
import ipaddress
import json
import os
import re
import threading
import time
import urllib.parse

from . import logs, services

TRIED_FILE = "queue-tried.json"
TRIED_KEEP = 200
TRIED_DAYS = 14
MAX_MESSAGES = 30
_lock = threading.Lock()

ARR_PROBLEM_STATES = {"failed", "failedPending", "importBlocked"}
REELIX_FAILED = {"failed_pending", "failed"}
ACTION_WORDS = {
    "remove": "Removed it from the queue and the download client",
    "block": "Removed it and blocked this release",
    "block-search": "Blocked this release and asked for a search for another",
    "import": "Asked Reelix to try the import again",
    "ignore": "Asked Reelix to ignore it (the files stay where they are)",
}
ID_FIELDS = (("movieId", "film"), ("seriesId", "series"), ("episodeId", "episode"), ("seasonNumber", "season number"),
             ("artistId", "artist"), ("albumId", "album"), ("authorId", "author"), ("bookId", "book"))
# The first folder of a path an app sees inside its container that is a media or download folder. Anything else
# (a home folder, /config, /root, a Windows drive) is left out of the export.
MEDIA_ROOTS = {"data", "downloads", "download", "media", "mnt", "tv", "movies", "films", "music", "books", "audiobooks",
               "radio", "podcasts", "comics", "complete", "completed", "incomplete", "intermediate", "storage", "pool",
               "srv", "share", "shares", "usenet", "torrents", "library"}
KINDS = {"sonarr": "episode", "radarr": "film", "lidarr": "album", "readarr": "book",
         "movie": "film", "series": "episode", "book": "book", "album": "album", "radio_episode": "radio episode"}

PROMPT = """You are helping me fix downloads on my home media server. Starboard (https://github.com/TheMightyTRex/starboard) is the dashboard. Reelix (or Sonarr, Radarr, Lidarr or Readarr) finds each release and imports it into the library, and a download client such as qBittorrent, NZBGet or SABnzbd fetches it.

Here is every download in Starboard's queue (Activity, Downloads, Queue) that needs attention or failed. For each one:

1. Diagnose the issue from its state and its messages.
2. Say the most likely cause.
3. Say the fix to try first, in Starboard or Reelix, naming the page and the button. In Starboard: Activity, Downloads, Queue, then select the download's name for Try the import again, Ignore, Choose the episode, Find another or Remove; or Settings, Reelix, Download apps for Repair.
4. Say what to check if that does not work.

Group downloads that share a cause and say so once. Ask me before suggesting anything that deletes files. Paths are as the apps see them inside their containers. Keys, passwords, tokens and private addresses have been taken out."""


# Taking secrets and private details out ---------------------------------------------------------------------

_URL = re.compile(r"(?i)\b(?:https?|ftp|udp|wss?)://[^\s\"'<>)\]]+")
_MAGNET = re.compile(r"(?i)\bmagnet:\?[^\s\"'<>]+")
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b(?::\d{1,5}\b)?")
_IPV6 = re.compile(r"(?i)\[?(?<![\w:.])[0-9a-f:]*:[0-9a-f:]*:[0-9a-f:.]*(?![\w:])\]?(?::\d{1,5}\b)?")
_LOCAL_HOST = re.compile(r"(?i)\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:local|lan|home|internal|localdomain|home\.arpa|ts\.net|intranet)\b(?::\d{1,5})?")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_KEYED = re.compile(r"(?i)\b(api[_-]?key|apikey|access[_-]?key|token|passkey|password|passwd|pass|secret|auth|authorization|"
                    r"cookie|session|sid|x-api-key|nzbkey|rsskey|torrent_pass|uid|key)(\s*[=:]\s*|\"\s*:\s*\")([^\s&,;\"']+)")
_KEYED_PATH = re.compile(r"(?i)/(api[_-]?key|apikey|passkey|token|rsskey|nzbkey)/([^\s/?&\"']+)")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{6,}")
_HOME = re.compile(r"(/home/|/Users/|/root/?)([^/\s\"']*)")
_WINDOWS_USER = re.compile(r"(?i)\b([A-Z]:\\Users\\)[^\\\s\"']+")
_PRIVATE_SECRET = "[removed]"


def _url_words(m):
    raw = m.group(0)
    try:
        u = urllib.parse.urlsplit(raw)
        host = (u.hostname or "").lower()
    except ValueError:
        return "[address removed]"
    if not host or _private_host(host):
        return "[private address]"
    return f"{u.scheme}://{host}/[rest of the address removed]" if (u.path not in ("", "/") or u.query or u.username) else f"{u.scheme}://{host}"


def _is_ip(text):
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False


def _private_host(host):
    if host in ("localhost",) or "." not in host or _is_ip(host):
        return True
    return bool(_LOCAL_HOST.fullmatch(host))


def clean(text, secrets=()):
    """One line of text from an app, with keys, passwords, tokens, private addresses, email addresses, the user
    name in home folders and full download addresses taken out. Release names, app names and media paths stay."""
    text = str(text if text is not None else "")
    for s in sorted({str(x) for x in secrets if x and len(str(x)) >= 4}, key=len, reverse=True):
        text = text.replace(s, _PRIVATE_SECRET)
    text = _MAGNET.sub("[magnet link removed]", text)
    text = _URL.sub(_url_words, text)
    text = _BEARER.sub(lambda m: f"{m.group(1)} {_PRIVATE_SECRET}", text)
    text = _KEYED.sub(lambda m: f"{m.group(1)}{m.group(2)}{_PRIVATE_SECRET}", text)
    text = _KEYED_PATH.sub(lambda m: f"/{m.group(1)}/{_PRIVATE_SECRET}", text)
    text = _EMAIL.sub("[email removed]", text)
    text = _LOCAL_HOST.sub("[private address]", text)
    text = _IPV4.sub(lambda m: "[address removed]" if _is_ip(m.group(0).split(":")[0]) else m.group(0), text)
    text = _IPV6.sub(lambda m: "[address removed]" if _is_ip(re.sub(r"^\[|\](?::\d+)?$", "", m.group(0))) else m.group(0), text)
    text = _HOME.sub(lambda m: m.group(1) + ("[user]" if m.group(2) else ""), text)
    text = _WINDOWS_USER.sub(lambda m: m.group(1) + "[user]", text)
    return text.strip()[:2000]


def path(value, secrets=()):
    """A path an app gave, as it sees it inside its container, when it is in a media or download folder; None
    otherwise, so a home folder or the app's settings folder never leaves the server."""
    value = str(value or "").strip()
    if not value:
        return None
    first = value.replace("\\", "/").lstrip("/").split("/", 1)[0].lower()
    if not value.startswith("/") or first not in MEDIA_ROOTS:
        return None
    return clean(value, secrets)


def known_secrets(all_services, data_dir=None):
    """Every key and password Starboard holds for the apps, to take out wherever an app repeats one back."""
    out = set()
    for s in all_services or []:
        key = str(s.get("api_key") or "")
        if key:
            out.add(key)
            out.update(p for p in key.split(":") if len(p) >= 4)  # NZBGet's "user:password"
    if data_dir:
        from . import stack
        for fn in ("qbittorrent_password", "nzbget_key", "sabnzbd_key"):
            try:
                v = getattr(stack, fn)(data_dir)
            except Exception:  # noqa: BLE001 - a missing stack folder is fine
                v = ""
            if v:
                out.add(str(v))
                out.update(p for p in str(v).split(":") if len(p) >= 4)
    return out


# What Starboard already tried ------------------------------------------------------------------------------

def _tried_path(data_dir):
    return os.path.join(data_dir, TRIED_FILE)


def _tried_load(data_dir):
    try:
        with open(_tried_path(data_dir), encoding="utf-8") as f:
            rows = json.load(f).get("items", [])
    except (OSError, ValueError):
        return []
    since = time.time() - TRIED_DAYS * 86400
    return [r for r in rows if isinstance(r, dict) and r.get("at", 0) >= since]


def note_tried(data_dir, what, app_id="", item_id=None, download_id="", title=""):
    """Writes down one thing Starboard did about a download, for the export. Never fails the action itself."""
    if not data_dir:
        return
    entry = {"at": round(time.time()), "what": str(what)[:300], "app_id": str(app_id or ""),
             "id": str(item_id) if item_id is not None else "", "download_id": str(download_id or "")[:200], "title": str(title or "")[:300]}
    try:
        with _lock:
            rows = _tried_load(data_dir) + [entry]
            tmp = _tried_path(data_dir) + ".new"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"items": rows[-TRIED_KEEP:]}, f)
            os.replace(tmp, _tried_path(data_dir))
    except OSError as e:
        logs.event("warning", "downloads", f"Could not note what was tried: {e}")


def note_action(data_dir, app_id, item_id, action, by="from the Downloads page"):
    """A queue action from the page or the API, with the download's id and name from the last queue Starboard read
    (no new call to the app)."""
    row = {}
    with services._cache_lock:
        hit = services._cache.get("queue")
    for r in (hit[1] or {}).get("items", []) if hit else []:
        if str(r.get("service")) == str(app_id) and str(r.get("id")) == str(item_id):
            row = r
            break
    note_tried(data_dir, f"{ACTION_WORDS.get(action, action)}, {by}", app_id, item_id, row.get("download_id", ""), row.get("title", ""))


def _tried_for(rows, item):
    out = []
    for r in rows:
        same_download = item["download_client_ids"].get("download_id") and r.get("download_id") == item["download_client_ids"]["download_id"]
        same_row = r.get("id") and r["id"] == str(item["ids"].get("queue")) and r.get("app_id") in item["_app_ids"]
        same_title = r.get("title") and r["title"] == item["title"]
        if same_download or same_row or same_title:
            out.append({"at": _iso(r["at"]), "what": r["what"]})
    return out


# Gathering --------------------------------------------------------------------------------------------------

def _iso(epoch):
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(when):
    try:
        t = dt.datetime.fromisoformat(str(when).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def age_words(added, now):
    t = _parse(added) if added else None
    if not t:
        return ""
    s = max(0, int((now - t).total_seconds()))
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"  # noqa: E731
    d, h, m = s // 86400, s % 86400 // 3600, s % 3600 // 60
    if d:
        return f"{plural(d, 'day')} {plural(h, 'hour')}"
    if h:
        return f"{plural(h, 'hour')} {plural(m, 'minute')}"
    return plural(m, "minute") if m else "less than a minute"


def _base(url):
    url = str(url or "").rstrip("/")
    return next((url[:-len(x)] for x in services.COMPAT_SUFFIXES if url.endswith(x)), url)


def _arr_issue(r):
    tracked = r.get("trackedDownloadState") or ""
    status = (r.get("status") or "").lower()
    flag = r.get("trackedDownloadStatus") or ""
    if not (flag in ("warning", "error") or tracked in ARR_PROBLEM_STATES or status in ("failed", "warning") or r.get("errorMessage")):
        return None
    return "Failed" if tracked.startswith("failed") or status == "failed" or flag == "error" else "Needs attention"


def _arr_rows(service, secrets):
    params = {"pageSize": 250, "includeUnknownSeriesItems": "true"}
    if service["type"] == "sonarr":
        params.update(includeSeries="true", includeEpisode="true")
    page = services._api(service, "/queue", params) or {}
    out = []
    for r in page.get("records", []):
        word = _arr_issue(r)
        if not word:
            continue
        size, left = r.get("size") or 0, r.get("sizeleft") or 0
        messages = []
        for s in r.get("statusMessages") or []:
            for m in s.get("messages") or []:
                head = s.get("title") or ""
                messages.append(f"{head}: {m}" if head and head != r.get("title") else str(m))
        if r.get("errorMessage"):
            messages.insert(0, str(r["errorMessage"]))
        what = ""
        if service["type"] == "sonarr":
            series, ep = (r.get("series") or {}).get("title", ""), r.get("episode") or {}
            if series:
                what = f"{series} S{int(ep.get('seasonNumber') or r.get('seasonNumber') or 0):02d}E{int(ep.get('episodeNumber') or 0):02d}" + (f" · {ep['title']}" if ep.get("title") else "")
        quality = ((r.get("quality") or {}).get("quality") or {}).get("name", "")
        ids = {"queue": r.get("id")}
        ids.update({word_: r[k] for k, word_ in ID_FIELDS if r.get(k) not in (None, 0, "")})
        out.append({
            "app": service["name"], "app_id": service["id"], "app_type": service["type"], "reelix": service.get("icon") == "reelix",
            "kind": KINDS.get(service["type"], ""), "what": clean(what, secrets),
            "title": clean(r.get("title") or "Unknown", secrets), "status": word,
            "app_state": {k: v for k, v in (("status", r.get("status") or ""), ("tracked_state", r.get("trackedDownloadState") or ""),
                                              ("tracked_status", r.get("trackedDownloadStatus") or "")) if v},
            "messages": [clean(m, secrets) for m in messages][:MAX_MESSAGES],
            "size": size, "progress": round((size - left) / size * 100, 1) if size else 0, "time_left": r.get("timeleft") or "",
            "added": r.get("added") or "", "indexer": clean(r.get("indexer") or "", secrets), "protocol": r.get("protocol") or "",
            "quality": quality, "download_client": clean(r.get("downloadClient") or "", secrets),
            "download_client_ids": {k: v for k, v in (("download_id", clean(r.get("downloadId") or "", secrets)),) if v},
            "paths": {k: v for k, v in (("output", path(r.get("outputPath"), secrets)),) if v},
            "ids": ids, "_app_ids": {service["id"]},
        })
    return out


def _reelix_issue(r):
    state, client = r.get("state") or "", r.get("client_state") or ""
    if state in REELIX_FAILED or client == "failed":
        return "Failed"
    if client == "warning" or (r.get("messages") and state != "downloading"):
        return "Needs attention"
    return None


def _reelix_rows(reelix, app_ids, secrets):
    page = services._api(reelix, "/queue", {"page": 1, "page_size": 0}) or {}
    out = []
    for r in page.get("items") or []:
        word = _reelix_issue(r)
        if not word:
            continue
        media = r.get("media") or {}
        eps = r.get("episodes") or []
        what = " · ".join(x for x in (media.get("subtitle"), media.get("title")) if x)
        if media.get("year") and media.get("kind") == "movie":
            what += f" ({media['year']})"
        if eps:
            what += " " + ", ".join(f"S{int(e.get('season_number') or 0):02d}E{int(e.get('episode_number') or 0):02d}" for e in eps[:10])
        ids = {"queue": r.get("id")}
        if media.get("kind"):
            ids[KINDS.get(media["kind"], media["kind"])] = media.get("id")
        if media.get("show_id"):
            ids["radio show"] = media["show_id"]
        if eps:
            ids["episodes"] = [e.get("id") for e in eps]
        quality = ((r.get("quality") or {}).get("quality") or {}).get("name", "") if isinstance(r.get("quality"), dict) else ""
        size = r.get("size") or 0
        eta = r.get("eta_secs")
        out.append({
            "app": reelix["name"], "app_id": reelix["id"], "app_type": "reelix", "reelix": True,
            "kind": KINDS.get(media.get("kind", ""), media.get("kind", "")), "what": clean(what.strip(), secrets),
            "title": clean(r.get("title") or "Unknown", secrets), "status": word,
            "app_state": {k: v for k, v in (("state", r.get("state") or ""), ("client_state", r.get("client_state") or "")) if v},
            "messages": [clean(m, secrets) for m in r.get("messages") or []][:MAX_MESSAGES],
            "size": size, "progress": round(float(r.get("progress") or 0) * 100, 1),
            "time_left": f"{eta // 86400}.{eta % 86400 // 3600:02d}:{eta % 3600 // 60:02d}:{eta % 60:02d}" if isinstance(eta, int) else "",
            "added": r.get("added") or "", "indexer": clean(r.get("indexer") or "", secrets), "protocol": str(r.get("protocol") or ""),
            "quality": quality, "download_client": clean(r.get("download_client") or "", secrets),
            "download_client_ids": {k: v for k, v in (("download_id", clean(r.get("download_id") or "", secrets)),
                                                       ("client_id_in_reelix", r.get("download_client_id"))) if v not in (None, "")},
            "paths": {k: v for k, v in (("output", path(r.get("output_path"), secrets)),) if v},
            "can_manual_import": bool(r.get("can_manual_import")),
            "ids": ids, "_app_ids": app_ids,
        })
    return out


def gather(all_services, data_dir=None, stuck_since=None, now=None):
    """Every download that needs attention or failed, from each app's queue, asked once now.
    Returns {"generated_at", "count", "apps_asked", "items", "errors"}."""
    now = now or dt.datetime.now(dt.timezone.utc)
    secrets = known_secrets(all_services, data_dir)
    natives = services.reelix_native(all_services)
    native_bases = {n["url"][:-len("/api/v1")]: n for n in natives}
    app_ids = {n["id"]: {s["id"] for s in all_services if s.get("icon") == "reelix" and _base(s.get("url")) == b} | {n["id"]}
               for b, n in native_bases.items()}
    arrs = [s for s in services._arrs(all_services) if not (s.get("icon") == "reelix" and _base(s.get("url")) in native_bases)]
    asked = arrs + natives
    rows, errors = services._gather(asked, lambda s: _reelix_rows(s, app_ids[s["id"]], secrets) if s["type"] == "link" else _arr_rows(s, secrets))
    tried = _tried_load(data_dir) if data_dir else []
    stuck = stuck_since or {}
    for item in rows:
        item["age"] = age_words(item["added"], now)
        item["tried"] = _tried_for(tried, item)
        seen = [v for k, v in stuck.items() if k.split("|", 1)[-1] == item["title"]]
        if seen:
            item["tried"].insert(0, {"at": _iso(min(seen)), "what": "The watch has found it needing attention since then (alerts for stuck downloads are active)"})
        item.pop("_app_ids", None)
    rows.sort(key=lambda i: (i["status"] != "Failed", i["app"].lower(), i["title"].lower()))
    return {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "count": len(rows), "apps_asked": len(asked),
            "items": rows, "errors": [{**e, "message": clean(e.get("message", ""), secrets)} for e in errors]}


# Markdown ---------------------------------------------------------------------------------------------------

def _size(n):
    if not n:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    n = float(n)
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.1f} {units[i]}" if i >= 3 else f"{n:.0f} {units[i]}"


def _code(text):
    text = str(text).replace("`", "'")
    return f"`{text}`"


def markdown(result, version=""):
    """The export as Markdown: the prompt, then one section for each download."""
    n = result["count"]
    when = _parse(result["generated_at"])
    stamp = when.strftime("%-d %B %Y at %H:%M UTC") if when else result["generated_at"]
    lines = ["# Download issues from Starboard", ""]
    if not n:
        lines += [f"Nothing in the queue needs attention or failed ({stamp})."]
        if result["errors"]:
            lines += ["", "These apps did not answer, so their downloads are not included:", ""]
            lines += [f"- {e['message']}" for e in result["errors"]]
        return "\n".join(lines) + "\n"
    apps = sorted({i["app"] for i in result["items"]})
    lines += [PROMPT, "", "---", "",
              f"Gathered on {stamp}{f' by Starboard {version}' if version else ''}: {n} {'download' if n == 1 else 'downloads'} "
              f"from {len(apps)} {'app' if len(apps) == 1 else 'apps'} ({', '.join(apps)})."]
    if result["errors"]:
        lines += ["", "These apps did not answer, so their downloads are not included:", ""]
        lines += [f"- {e['message']}" for e in result["errors"]]
    for number, i in enumerate(result["items"], 1):
        lines += ["", f"## {number}. {i['title']}", ""]
        app_type = "Reelix" if i["app_type"] == "reelix" else i["app_type"].capitalize()
        lines.append(f"- **Starboard says:** {i['status']}")
        kind_words = ", ".join(x for x in ("" if i["app"] == app_type else app_type, "inside Reelix" if i["reelix"] and i["app_type"] != "reelix" else "") if x)
        lines.append(f"- **App:** {i['app']}" + (f" ({kind_words})" if kind_words else ""))
        if i["what"] or i["kind"]:
            lines.append(f"- **What it is:** {', '.join(x for x in (i['kind'], i['what']) if x)}")
        if i["app_state"]:
            lines.append("- **The app's own state:** " + ", ".join(f"{k.replace('_', ' ')} {_code(v)}" for k, v in i["app_state"].items()))
        if i["messages"]:
            lines.append("- **Messages:**")
            lines += [f"  - {m}" for m in i["messages"]]
        else:
            lines.append("- **Messages:** none (the app flagged it without a message)")
        facts = [f"**Size:** {_size(i['size']) or 'not known'}", f"**Progress:** {i['progress']:g}%"]
        if i["time_left"]:
            facts.append(f"**Time left:** {i['time_left']}")
        lines.append("- " + " · ".join(facts))
        if i["added"]:
            lines.append(f"- **Added:** {i['added']}" + (f" ({i['age']} ago)" if i["age"] else ""))
        source = [f"**Indexer:** {i['indexer'] or 'not known'}"]
        if i["protocol"]:
            source.append(f"**Protocol:** {i['protocol']}")
        if i["quality"]:
            source.append(f"**Quality:** {i['quality']}")
        lines.append("- " + " · ".join(source))
        ids = i["download_client_ids"]
        id_words = {"download_id": "download id", "client_id_in_reelix": "the client's id in Reelix"}
        lines.append(f"- **Download client:** {i['download_client'] or 'not known'}"
                     + (" · **Download client ids:** " + ", ".join(f"{id_words.get(k, k)} {_code(v)}" for k, v in ids.items()) if ids else ""))
        lines.append("- **Paths, inside the container:** " + (", ".join(f"{k} {_code(v)}" for k, v in i["paths"].items())
                                                               if i["paths"] else "none given, or outside the media folders"))
        label = "Reelix ids" if i["reelix"] else f"Ids in {i['app']}"
        lines.append(f"- **{label}:** " + ", ".join(f"{k} {', '.join(map(str, v)) if isinstance(v, list) else v}" for k, v in i["ids"].items()))
        if i.get("can_manual_import"):
            lines.append("- **Reelix says:** it can be imported by hand")
        if i["tried"]:
            lines.append("- **What Starboard already tried:**")
            lines += [f"  - {t['at']}: {t['what']}" for t in i["tried"]]
        else:
            lines.append("- **What Starboard already tried:** nothing yet")
    return "\n".join(lines) + "\n"


def export(app, fresh=False):
    """The answer for the page and the API: the items and the Markdown. Asked at most every 10 seconds."""
    cfg = app.config
    watch_state = getattr(getattr(app, "watch", None), "state", None) or {}

    def build():
        out = gather(cfg.data["services"], app.data_dir, dict(watch_state.get("stuck_since") or {}))
        out["markdown"] = markdown(out, getattr(app, "version", ""))
        return out
    return services.cached("queue-issues", 10, build, fresh)
