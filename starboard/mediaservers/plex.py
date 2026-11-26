"""Plex as a media server (DASH-566). Plex answers in its own shapes, so each answer is turned into the contract's here.
The address and token are kept in Settings, Manage apps, as an app of the kind Plex; the token is sent in the
X-Plex-Token header, never in an address, so it does not reach a log."""
import datetime as dt
import urllib.request

from .. import mediaserver, services

TYPES = {"movie": "Movie", "episode": "Episode", "track": "Audio", "album": "MusicAlbum", "show": "Series", "season": "Season",
         "artist": "MusicArtist", "clip": "Video"}
SECTIONS = {"movie": "movies", "show": "tvshows", "artist": "music", "photo": "photos"}


def _list(answer, key):
    """MediaContainer.<key> as a list of dicts, whatever Plex left out."""
    box = (answer or {}).get("MediaContainer") if isinstance(answer, dict) else None
    rows = (box or {}).get(key) if isinstance(box, dict) else None
    return [r for r in rows or [] if isinstance(r, dict)]


def _when(epoch):
    try:
        return dt.datetime.fromtimestamp(int(epoch), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


class Plex(mediaserver.MediaServer):
    id = "plex"
    name = "Plex"
    service_type = "plex"
    page = ""  # no page of its own yet: its address and token are in Settings, Manage apps
    capabilities = ()  # read only for now

    def _send(self, service, method, path):
        req = urllib.request.Request(service["url"].rstrip("/") + path, method=method, headers={
            "X-Plex-Token": service.get("api_key", ""), "Accept": "application/json", "X-Plex-Client-Identifier": "starboard",
            "X-Plex-Product": "Starboard", "User-Agent": services.USER_AGENT})
        return services._fetch(service, req, services.TIMEOUT)

    def public_version(self, service):
        """The version it tells anyone, with no token (/identity)."""
        got = self._send(dict(service, api_key=""), "GET", "/identity")
        box = got.get("MediaContainer") if isinstance(got, dict) else None
        return str(box.get("version") or "").split("-")[0] if isinstance(box, dict) else ""

    def check_key(self, service):
        """Asks for something only a token allows; raises ServiceError (the token was refused) when it does not answer."""
        self._send(service, "GET", "/library/sections")

    def _identity(self, found):
        box = (self._send(found, "GET", "/") or {}).get("MediaContainer") or {}
        return box if isinstance(box, dict) else {}

    def legacy_status(self, services_list):
        found = self.find_service(services_list)
        if not found:
            return {"configured": False}
        info = self._identity(found)
        out = {"configured": True, "name": found.get("name") or info.get("friendlyName") or self.name, "version": str(info.get("version") or "").split("-")[0],
               "update": False, "restart": False, "can_restart": False, "playing": [], "added": [], "channels": None, "guide": None}
        for item in _list(self._send(found, "GET", "/status/sessions"), "Metadata"):
            player = item.get("Player") or {}
            length = item.get("duration") or 0
            transcode = item.get("TranscodeSession") or {}
            out["playing"].append({
                "user": str((item.get("User") or {}).get("title") or ""), "device": str(player.get("title") or player.get("device") or ""),
                "client": str(player.get("product") or ""), "title": str(item.get("title") or ""),
                "series": str(item.get("grandparentTitle") or ""), "type": TYPES.get(item.get("type"), str(item.get("type") or "")),
                "paused": player.get("state") == "paused",
                "progress": round((item.get("viewOffset") or 0) / length * 100) if length else None,
                "transcoding": transcode.get("videoDecision") == "transcode" or transcode.get("audioDecision") == "transcode",
                "reason": ""})
        for item in _list(self._send(found, "GET", "/library/recentlyAdded?X-Plex-Container-Start=0&X-Plex-Container-Size=12"), "Metadata")[:12]:
            out["added"].append({"title": str(item.get("title") or ""), "series": str(item.get("grandparentTitle") or ""),
                                 "type": TYPES.get(item.get("type"), str(item.get("type") or "")), "when": _when(item.get("addedAt")),
                                 "year": item.get("year")})
        return out

    def status(self, services_list):
        try:
            got = self.legacy_status(services_list)
        except services.ServiceError as e:
            return {"configured": True, "up": False, "name": self.name, "version": "", "update_available": False,
                    "restart_needed": False, "playing": 0, "why": str(e)}
        if not got.get("configured"):
            return {"configured": False, "up": False, "name": self.name, "version": "", "update_available": False,
                    "restart_needed": False, "playing": 0, "why": ""}
        return {"configured": True, "up": True, "name": got.get("name") or self.name, "version": got.get("version", ""),
                "update_available": False, "restart_needed": False, "playing": len(got.get("playing") or []), "why": ""}

    def libraries(self, services_list):
        return [{"id": str(d.get("key") or ""), "name": str(d.get("title") or ""), "type": SECTIONS.get(d.get("type"), "mixed"), "count": None}
                for d in _list(self._send(self._service(services_list), "GET", "/library/sections"), "Directory")]

    def playing(self, services_list):
        return [{"user": p["user"], "title": p["title"], "kind": p["type"], "device": p["device"], "converting": p["transcoding"],
                 "progress": p["progress"]} for p in self.legacy_status(services_list).get("playing") or []]

    def recent(self, services_list, limit=12):
        rows = self.legacy_status(services_list).get("added") or []
        return [{"title": r["title"], "kind": r["type"], "added": r["when"], "link": None} for r in rows[:max(0, int(limit))]]

    def refresh(self, services_list):
        self._send(self._service(services_list), "GET", "/library/sections/all/refresh")
        return {"asked": True}

    def users(self, services_list):
        # The server's own accounts; the first, the owner, is its administrator.
        return [{"id": str(a.get("id") or ""), "name": str(a.get("name") or ""), "admin": str(a.get("id")) == "1"}
                for a in _list(self._send(self._service(services_list), "GET", "/accounts"), "Account") if a.get("name")]

    def sign_in_check(self, services_list):
        try:
            info = self._identity(self._service(services_list))
        except services.ServiceError as e:
            return {"ok": False, "why": str(e)}
        return {"ok": True, "why": "", "name": info.get("friendlyName") or self.name, "version": str(info.get("version") or "").split("-")[0]}

    def keys_needed(self):
        return [{"what": "Plex token", "where": "Plex's web app: open an item, Get info, View XML, and copy X-Plex-Token from the address",
                 "kept": "Settings, Manage apps"}]
