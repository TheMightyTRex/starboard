"""Emby as a media server (DASH-566). Emby and Jellyfin share their questions and answers, so most of this is the
shared MediaBrowser class: only the prefix, the key's header and the status differ. The address and key are kept in
Settings, Manage apps, as an app of the kind Emby."""
import re
import urllib.parse

from .. import mediaserver, services

ID_RE = re.compile(r"^[0-9A-Za-z]{1,40}$")


class Emby(mediaserver.MediaBrowser):
    id = "emby"
    name = "Emby"
    service_type = "emby"
    prefix = "/emby"
    page = mediaserver.PAGE
    capabilities = ("admin_libraries", "admin_tasks", "admin_activity", "admin_logs", "play", "watched", "updates")  # DASH-566: Play links and Watched; the rest are Jellyfin's so far (limits)
    limits = {
        "restart": "Emby's restart is in its own dashboard; Starboard restarts its container from Settings, Manage apps",
        "own_plugins": "Emby's own plug-ins are managed in Emby's dashboard, Plugins",
        "conversion_test": "Starboard's test of video conversion runs against Jellyfin's ffmpeg only",
        "live_tv": "Starboard sets up Live TV channels in Jellyfin only; Emby's Live TV needs Emby Premiere and is set up in Emby",
        "libraries_add": "Plug-ins that fill a library fill Jellyfin's only",
        "first_run": "Starboard makes Emby's first account and libraries only after you try it on a copy (not tried here)",
        "history_import": "Importing watch history is into Jellyfin only; the move wizard carries watched state to Emby",
        "user_defaults": "Defaults for every user are Jellyfin's only",
        "metadata_folder": "Moving the metadata folder is Jellyfin's only",
        "detect": "Starboard finds Emby when you search for new apps",
    }

    admin_coverage_rows = (
        ("Libraries: list, scan new and changed files, refresh everything", "starboard", "On this tab, under Administration.", ""),
        ("Libraries: add, rename or remove one, and change its folders and options", "later", "Not in Starboard yet. Use Emby's dashboard, Library.", "/web/index.html#!/dashboard"),
        ("People: their passwords", "later", "Starboard's change of an Emby password is built but stays hidden until it is tried on a real Emby. Use Emby's dashboard, Users.", "/web/index.html#!/users"),
        ("People: add or remove an account, their rights and the libraries they see", "later", "Not in Starboard yet. Use Emby's dashboard, Users.", "/web/index.html#!/users"),
        ("Scheduled tasks: read, and run now", "starboard", "On this tab, under Administration.", ""),
        ("Scheduled tasks: change when they run", "later", "Not in Starboard yet. Use Emby's dashboard, Scheduled Tasks.", "/web/index.html#!/scheduledtasks"),
        ("Activity and server logs", "starboard", "On this tab, under Administration.", ""),
        ("Video conversion", "server", "Hardware conversion needs Emby Premiere and is set in Emby's dashboard, Transcoding.", "/web/index.html#!/transcoding"),
        ("Remote access, ports and the network", "later", "Not in Starboard yet. Use Emby's dashboard, Network.", "/web/index.html#!/networking"),
        ("Emby's own plug-ins and their updates", "later", "Not in Starboard yet. Use Emby's dashboard, Plugins.", "/web/index.html#!/plugins"),
        ("Devices, sessions and API keys", "later", "Not in Starboard yet. Use Emby's dashboard, Devices and API Keys.", "/web/index.html#!/devices"),
        ("Server name, language and branding", "later", "Not in Starboard yet. Use Emby's dashboard, Settings.", "/web/index.html#!/dashboard"),
        ("Update the server", "starboard", "Ready to update changes its container and waits while anyone is watching.", ""),
        ("Live TV and recording", "server", "Needs Emby Premiere, and is set up in Emby's dashboard, Live TV.", "/web/index.html#!/livetv"),
        ("Backup of the server's own database", "no", "Emby has no way to do it through its interface. Starboard's backups copy its settings folder.", ""),
    )

    def public_version(self, service):
        """The version it tells anyone, with no key."""
        got = self._send(dict(service, api_key=""), "GET", "/System/Info/Public")
        return str(got.get("Version") or "") if isinstance(got, dict) else ""

    def check_key(self, service):
        """Asks for something only a key allows; raises ServiceError (the key was refused) when it does not answer."""
        self._send(service, "GET", "/System/Info")

    def _headers(self, service):
        return {"X-Emby-Token": service.get("api_key", ""), "Accept": "application/json", "User-Agent": services.USER_AGENT}

    def legacy_status(self, services_list):
        """The answer the dashboard and System draw (the same shape as Jellyfin's, without Live TV)."""
        found = self.find_service(services_list)
        if not found:
            return {"configured": False}
        info = self._send(found, "GET", "/System/Info") or {}
        out = {"configured": True, "name": found.get("name") or self.name, "version": info.get("Version", ""),
               "update": bool(info.get("HasUpdateAvailable")), "restart": bool(info.get("HasPendingRestart")),
               "can_restart": False, "playing": [], "added": [], "channels": None, "guide": None}
        for sess in self._send(found, "GET", "/Sessions?ActiveWithinSeconds=900") or []:
            item = sess.get("NowPlayingItem") if isinstance(sess, dict) else None
            if not item:
                continue
            play = sess.get("PlayState") or {}
            trans = sess.get("TranscodingInfo") or {}
            length = item.get("RunTimeTicks") or 0
            out["playing"].append({
                "user": sess.get("UserName", ""), "device": sess.get("DeviceName", ""), "client": sess.get("Client", ""),
                "title": item.get("Name", ""), "series": item.get("SeriesName", ""), "type": item.get("Type", ""),
                "paused": bool(play.get("IsPaused")),
                "progress": round((play.get("PositionTicks") or 0) / length * 100) if length else None,
                "transcoding": bool(trans) and not trans.get("IsVideoDirect", True),
                "reason": ", ".join(str(r) for r in trans.get("TranscodeReasons") or [])[:120]})
        latest = self._send(found, "GET", "/Items?SortBy=DateCreated&SortOrder=Descending&Recursive=true&Limit=12"
                                           "&IncludeItemTypes=Movie,Episode,MusicAlbum,AudioBook,Book&Fields=DateCreated") or {}
        for item in latest.get("Items") or []:
            out["added"].append({"title": item.get("Name", ""), "series": item.get("SeriesName", ""), "type": item.get("Type", ""),
                                 "when": item.get("DateCreated", ""), "year": item.get("ProductionYear")})
        return out

    def keys_needed(self):
        return [{"what": "API key", "where": "Emby's dashboard, Advanced, API keys", "kept": "Settings, Manage apps"}]

    # Play and Watched (DASH-566): the same questions as Jellyfin's, under /emby. Written from Emby's published API and tried
    # only against recorded answers (no real Emby was available).
    def play_info(self, services_list):
        found = self.find_service(services_list)
        if not found:
            return {}
        got = self._send(dict(found, api_key=""), "GET", "/System/Info/Public")
        return {"server_id": str(got.get("Id") or "")} if isinstance(got, dict) else {}

    def play_link(self, base, item_id, server_id=""):
        """Opens the item's page in Emby's web app, whose Play button starts it."""
        if not ID_RE.match(str(item_id)) or not server_id:
            return ""
        return f"{base.rstrip('/')}/web/index.html#!/item?id={urllib.parse.quote(str(item_id))}&serverId={urllib.parse.quote(server_id)}"

    def _pages(self, found, path, params):
        start = 0
        while True:
            page = self._send(found, "GET", f"{path}?{urllib.parse.urlencode({**params, 'StartIndex': start, 'Limit': 1000})}") or {}
            items = [i for i in page.get("Items") or [] if isinstance(i, dict)]
            if items:
                yield items
            start += len(items)
            if not items or start >= (page.get("TotalRecordCount") or 0):
                return

    def film_ids(self, services_list):
        out = {}
        for page in self._pages(self._service(services_list), "/Items", {"Recursive": "true", "IncludeItemTypes": "Movie", "Fields": "ProviderIds",
                                                                         "EnableImages": "false", "EnableUserData": "false"}):
            for it in page:
                iid = str(it.get("Id") or "")
                if not ID_RE.match(iid):
                    continue
                ids = {k.lower(): str(v) for k, v in (it.get("ProviderIds") or {}).items() if v}
                for kind in ("tmdb", "imdb"):
                    if ids.get(kind):
                        out.setdefault((kind, ids[kind]), iid)
        return out

    def watched_user(self, services_list, wanted=""):
        users = self._send(self._service(services_list), "GET", "/Users") or []
        users = [u for u in users if isinstance(u, dict) and u.get("Id")]
        found = next((u for u in users if u.get("Name") == wanted), None) if wanted else None
        found = found or next((u for u in users if (u.get("Policy") or {}).get("IsAdministrator")), None) or (users[0] if users else None)
        return (str(found["Id"]), str(found.get("Name") or "")) if found else None

    def _find(self, found, uid, kind, tmdb):
        q = urllib.parse.urlencode({"Recursive": "true", "IncludeItemTypes": kind, "AnyProviderIdEquals": f"tmdb.{tmdb}",
                                    "Fields": "ProviderIds", "Limit": 5, "EnableImages": "false"})
        items = (self._send(found, "GET", f"/Users/{urllib.parse.quote(uid)}/Items?{q}") or {}).get("Items") or []
        # The match on provider ids can be loose: keep only the exact TMDB id.
        return next((i for i in items if isinstance(i, dict) and str((i.get("ProviderIds") or {}).get("Tmdb", (i.get("ProviderIds") or {}).get("tmdb", ""))) == str(tmdb)), None)

    def watched_film(self, services_list, who, tmdb):
        it = self._find(self._service(services_list), who[0], "Movie", tmdb)
        return {"id": str(it["Id"]), "watched": bool((it.get("UserData") or {}).get("Played")), "user": who[1]} if it else None

    def watched_series(self, services_list, who, tmdb):
        found = self._service(services_list)
        s = self._find(found, who[0], "Series", tmdb)
        if not s:
            return None
        q = urllib.parse.urlencode({"UserId": who[0], "Fields": "UserData", "EnableImages": "false"})
        eps = (self._send(found, "GET", f"/Shows/{urllib.parse.quote(str(s['Id']))}/Episodes?{q}") or {}).get("Items") or []
        out = {}
        for e in eps:
            if isinstance(e, dict) and e.get("ParentIndexNumber") is not None and e.get("IndexNumber") is not None:
                out[(int(e["ParentIndexNumber"]), int(e["IndexNumber"]))] = {"id": str(e["Id"]), "watched": bool((e.get("UserData") or {}).get("Played"))}
        return {"id": str(s["Id"]), "episodes": out, "user": who[1]}

    def mark(self, services_list, who, ids, watched):
        found = self._service(services_list)
        for i in ids:
            if not ID_RE.match(str(i)):
                raise ValueError("That is not an item Emby knows")
            self._send(found, "POST" if watched else "DELETE", f"/Users/{urllib.parse.quote(who[0])}/PlayedItems/{urllib.parse.quote(str(i))}")
        return len(ids)
