"""Plex as a media server (DASH-566). Plex answers in its own shapes, so each answer is turned into the contract's here.
The address and token are kept in Settings, Manage apps, as an app of the kind Plex; the token is sent in the
X-Plex-Token header, never in an address, so it does not reach a log."""
import datetime as dt
import re
import urllib.parse
import urllib.request

from .. import mediaserver, services

TYPES = {"movie": "Movie", "episode": "Episode", "track": "Audio", "album": "MusicAlbum", "show": "Series", "season": "Season",
         "artist": "MusicArtist", "clip": "Video"}
KEY_RE = re.compile(r"^[0-9]{1,12}$")
PAGE = 500  # items a page, when reading a section
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
    page = mediaserver.PAGE
    capabilities = ("play", "watched")  # DASH-566: Play links and Watched; the rest are Jellyfin's so far (limits)
    limits = {
        "restart": "Plex has no restart in its documented API; Starboard restarts its container from Settings, Manage apps",
        "own_plugins": "Plex retired its plug-ins in 2018, so there is nothing to list or update",
        "conversion_test": "Starboard's test of video conversion runs against Jellyfin's ffmpeg only",
        "live_tv": "Starboard sets up Live TV channels in Jellyfin only; Plex's Live TV and DVR need Plex Pass and are set up in Plex",
        "libraries_add": "Plug-ins that fill a library fill Jellyfin's only",
        "first_run": "Plex needs a claim token from your Plex account (valid for 4 minutes), which only you can make, so Starboard cannot do the first set-up",
        "history_import": "Importing watch history is into Jellyfin only; the move wizard cannot write watched state into Plex",
        "user_defaults": "Plex users and their rights are held by plex.tv, so Starboard cannot set defaults for them",
        "metadata_folder": "Plex's metadata folder is set when its container is made",
        "detect": "Starboard finds Plex when you search for new apps",
        "updates": "Starboard updates Plex's container through Ready to update; it cannot read Plex's own update flag",
    }

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

    # Play and Watched (DASH-566). Plex has no search by TMDB id, so Starboard reads each film and show section once, with
    # their guids, and keeps the id list for ten minutes. The watched state is the owner's, whose token Starboard holds.
    def play_info(self, services_list):
        found = self.find_service(services_list)
        if not found:
            return {}
        box = (self._send(dict(found, api_key=""), "GET", "/identity") or {}).get("MediaContainer")
        return {"server_id": str((box or {}).get("machineIdentifier") or "")} if isinstance(box, dict) else {}

    def play_link(self, base, item_id, server_id=""):
        """Opens the item's page in Plex's web app, whose Play button starts it."""
        if not KEY_RE.match(str(item_id)) or not server_id or not re.match(r"^[0-9a-fA-F]{8,64}$", server_id):
            return ""
        return f"{base.rstrip('/')}/web/index.html#!/server/{server_id}/details?key=" + urllib.parse.quote(f"/library/metadata/{item_id}", safe="")

    def _all(self, found, section):
        start = 0
        while True:
            q = urllib.parse.urlencode({"includeGuids": 1, "X-Plex-Container-Start": start, "X-Plex-Container-Size": PAGE})
            got = self._send(found, "GET", f"/library/sections/{urllib.parse.quote(section)}/all?{q}")
            rows = _list(got, "Metadata")
            yield from rows
            start += len(rows)
            total = ((got or {}).get("MediaContainer") or {}).get("totalSize") if isinstance(got, dict) else None
            if not rows or start >= (total or 0):
                return

    def _guids(self, row):
        out = {}
        for g in row.get("Guid") or []:
            m = re.match(r"^(tmdb|imdb)://([A-Za-z0-9]+)$", str(g.get("id") if isinstance(g, dict) else ""))
            if m:
                out[m.group(1)] = m.group(2)
        return out

    def _index(self, services_list, kind):
        """{("tmdb"|"imdb", id): ratingKey} for the films ("movie") or shows ("show") Plex has."""
        found = self._service(services_list)

        def read():
            out = {}
            for d in _list(self._send(found, "GET", "/library/sections"), "Directory"):
                if d.get("type") == kind and KEY_RE.match(str(d.get("key") or "")):
                    for row in self._all(found, str(d["key"])):
                        rk = str(row.get("ratingKey") or "")
                        if KEY_RE.match(rk):
                            for k, v in self._guids(row).items():
                                out.setdefault((k, v), rk)
            return out
        return services.cached(f"plex-index-{kind}-{found.get('id', '')}", 600, read)

    def film_ids(self, services_list):
        return self._index(services_list, "movie")

    def watched_user(self, services_list, wanted=""):
        found = self._service(services_list)
        name = str((self._identity(found) or {}).get("myPlexUsername") or "") or "the Plex owner"
        return ("owner", name)

    def _one(self, found, rating_key):
        rows = _list(self._send(found, "GET", f"/library/metadata/{rating_key}"), "Metadata")
        return rows[0] if rows else None

    def watched_film(self, services_list, who, tmdb):
        found = self._service(services_list)
        rk = self._index(services_list, "movie").get(("tmdb", str(tmdb)))
        row = self._one(found, rk) if rk else None
        return {"id": rk, "watched": bool(row.get("viewCount")), "user": who[1]} if row else None

    def watched_series(self, services_list, who, tmdb):
        found = self._service(services_list)
        rk = self._index(services_list, "show").get(("tmdb", str(tmdb)))
        if not rk:
            return None
        out = {}
        for e in _list(self._send(found, "GET", f"/library/metadata/{rk}/allLeaves"), "Metadata"):
            if e.get("parentIndex") is not None and e.get("index") is not None and KEY_RE.match(str(e.get("ratingKey") or "")):
                out[(int(e["parentIndex"]), int(e["index"]))] = {"id": str(e["ratingKey"]), "watched": bool(e.get("viewCount"))}
        return {"id": rk, "episodes": out, "user": who[1]}

    def mark(self, services_list, who, ids, watched):
        found = self._service(services_list)
        for i in ids:
            if not KEY_RE.match(str(i)):
                raise ValueError("That is not an item Plex knows")
            self._send(found, "GET", f"/:/{'scrobble' if watched else 'unscrobble'}?" + urllib.parse.urlencode({"key": i, "identifier": "com.plexapp.plugins.library"}))
        services.forget(f"plex-index-movie-{found.get('id', '')}")
        return len(ids)
