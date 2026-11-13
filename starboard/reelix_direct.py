"""YouTube and Spotify in the full version of Reelix (DASH-216, DASH-217, DASH-126): Reelix's direct downloads,
switched on at set-up with the shared media folder (/data/downloads/direct) instead of Reelix's settings folder,
changed in Settings, Reelix, with Connect Spotify, and a page to paste a link, see what it holds, choose the format
and follow the queue. All of it is Reelix admin only, so Starboard asks for the password (reelix_admin.py)."""
import re
import urllib.parse

FOLDER = "/data/downloads/direct"
MODES = ("audio", "video")


def set_up(admin):
    """At set-up, for the full version: on, into the shared media folder. Returns lines."""
    _, s = admin.call("GET", "/downloads/settings")
    s = dict(s or {})
    if s.get("enabled") and s.get("output_dir") == FOLDER:
        return []
    admin.call("PUT", "/downloads/settings", {**s, "enabled": True, "output_dir": FOLDER})
    return [f"YouTube and Spotify downloads are on, into {FOLDER}"]


def state(reelix):
    _, s = reelix.call("GET", "/downloads/settings")
    _, health = reelix.call("GET", "/downloads/health")
    _, spotify = reelix.call("GET", "/downloads/spotify")
    s, spotify = s or {}, spotify or {}
    return {"on": bool(s.get("enabled")), "folder": s.get("output_dir") or "",
            "tools": [{"tool": h.get("tool"), "ok": bool(h.get("available")), "detail": h.get("detail") or ""} for h in health or []],
            "spotify": {"connected": bool(spotify.get("connected")), "user": spotify.get("username") or "",
                        "waiting": bool(spotify.get("pending")), "problem": spotify.get("error") or ""},
            "folder_warning": "" if (s.get("output_dir") or "").startswith("/data/") else
            "Downloads go into Reelix's settings folder. Choose a folder inside /data so they land with your media."}


def save(reelix, on, folder):
    folder = str(folder or "").strip().rstrip("/")
    if not re.match(r"^/data(/[A-Za-z0-9 ._()&+-]+)+$", folder):
        raise ValueError("Choose a folder inside /data, such as /data/downloads/direct or /data/media/music")
    _, s = reelix.call("GET", "/downloads/settings")
    reelix.call("PUT", "/downloads/settings", {**(s or {}), "enabled": bool(on), "output_dir": folder})
    return {**state(reelix), "done": "YouTube and Spotify settings saved"}


def spotify_start(reelix):
    _, out = reelix.call("POST", "/downloads/spotify/login")
    return {"url": (out or {}).get("auth_url", ""), "automatic": bool((out or {}).get("automatic"))}


def spotify_finish(reelix, address):
    address = str(address or "").strip()
    if not address.startswith(("http://", "https://")) or len(address) > 4000:
        raise ValueError("Paste the whole address the page went to after you agreed in Spotify")
    reelix.call("POST", "/downloads/spotify/login/finish", {"redirect_url": address})
    return {**state(reelix), "done": "Spotify is connected"}


def spotify_disconnect(reelix):
    reelix.call("POST", "/downloads/spotify/disconnect")
    return {**state(reelix), "done": "Spotify is disconnected"}


HOSTS = {"youtube.com": "youtube", "www.youtube.com": "youtube", "m.youtube.com": "youtube", "music.youtube.com": "youtube",
         "youtu.be": "youtube", "www.youtu.be": "youtube", "m.youtu.be": "youtube", "music.youtu.be": "youtube",
         "open.spotify.com": "spotify", "www.open.spotify.com": "spotify", "m.open.spotify.com": "spotify",
         "music.open.spotify.com": "spotify"}  # every host the address pattern below lets through


def _request(body):
    url = str((body or {}).get("url", "")).strip()
    if not re.match(r"^https://(www\.|m\.|music\.)?(youtube\.com|youtu\.be|open\.spotify\.com)/", url):
        raise ValueError("Paste a YouTube or Spotify link")
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host not in HOSTS:  # the exact host, never a look-alike such as open.spotify.com.example.net
        raise ValueError("Paste a YouTube or Spotify link")
    source = HOSTS[host]
    mode = body.get("mode") if body.get("mode") in MODES else "audio"
    return {"url": url, "source": source, "mode": "audio" if source == "spotify" else mode,
            "format": "mp3" if mode == "audio" else "mp4", "playlist": bool(body.get("playlist", True))}


def preview(reelix, body):
    _, out = reelix.call("POST", "/downloads/preview", _request(body), timeout=60)
    return {"title": (out or {}).get("title", ""), "items": (out or {}).get("items") or [], "more": bool((out or {}).get("truncated"))}


def queue(reelix):
    _, items = reelix.call("GET", "/downloads")
    return {"items": [{"id": d["id"], "url": (d.get("request") or {}).get("url", ""), "source": (d.get("request") or {}).get("source", ""),
                       "state": d.get("state", ""), "progress": d.get("progress"), "message": d.get("message") or ""}
                      for d in items or []]}


def start(reelix, body):
    reelix.call("POST", "/downloads", _request(body), ok=(200, 201, 202))
    return {**queue(reelix), "done": "Downloading"}


def change(reelix, item_id, action):
    if action not in ("cancel", "retry"):
        raise ValueError("Choose Cancel or Try again")
    reelix.call("POST", f"/downloads/{int(item_id)}/{action}", ok=(200, 202, 204))
    return {**queue(reelix), "done": "Cancelled" if action == "cancel" else "Trying again"}
