"""Emby as a media server (DASH-566). Emby and Jellyfin share their questions and answers, so most of this is the
shared MediaBrowser class: only the prefix, the key's header and the status differ. The address and key are kept in
Settings, Manage apps, as an "Other app" with the icon emby."""
from .. import mediaserver, services


class Emby(mediaserver.MediaBrowser):
    id = "emby"
    name = "Emby"
    service_type = "link"
    service_icon = "emby"
    prefix = "/emby"
    page = ""  # no page of its own yet: its address and key are in Settings, Manage apps
    capabilities = ()  # read only for now

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
        return [{"what": "API key", "where": "Emby's dashboard, Advanced, API keys", "kept": "Settings, Manage apps, as an Other app with the icon emby"}]
