"""The media server contract (DASH-565, design/media-server-plugins.md): what Starboard asks of a media server, and the
one place that is filled by whichever media server is active. Jellyfin is the first, and the default, so nothing a
person sees changes.

A media server is an adapter: a small class with the calls below. Starboard asks the active one for its name, status,
libraries, what is playing, what was added, users, a refresh and a sign-in check, and draws only the capabilities it
offers (no empty panel and no disabled button). The adapters here run in Starboard's own process and are imported only
when asked for, so a server that is not active costs no memory. A media server plug-in (Plex and Emby are next,
DASH-566) fills the same slot.

The active one is `extras.media_server`; when it is not set it is "jellyfin", so an existing install needs no
migration, and an older Starboard ignores the key. Nothing is written until a person chooses another server."""

from . import services

DEFAULT = "jellyfin"

# What a media server may offer beyond the nine required calls; a page draws a part only when it is listed.
CAPABILITIES = ("play", "watched", "restart", "own_plugins", "conversion_test", "live_tv", "libraries_add", "first_run",
                "history_import", "user_defaults", "metadata_folder", "detect", "updates")
REQUIRED = ("describe", "status", "libraries", "playing", "recent", "refresh", "users", "sign_in_check", "keys_needed")


class MediaServer:
    """The contract. Each call takes the saved services (Settings, Apps) and answers plain data; one that cannot be
    answered raises services.ServiceError with a sentence for people."""

    id = ""
    name = ""
    service_type = ""  # the entry in the saved services that holds its address and key
    capabilities = ()
    page = ""  # its own settings page, when it has one

    def describe(self):
        return {"id": self.id, "name": self.name, "kind": "media-server", "page": self.page, "capabilities": list(self.capabilities)}

    def status(self, services_list):
        raise NotImplementedError

    def libraries(self, services_list):
        raise NotImplementedError

    def playing(self, services_list):
        raise NotImplementedError

    def recent(self, services_list, limit=12):
        raise NotImplementedError

    def refresh(self, services_list):
        raise NotImplementedError

    def users(self, services_list):
        raise NotImplementedError

    def sign_in_check(self, services_list):
        raise NotImplementedError

    def keys_needed(self):
        raise NotImplementedError

    def legacy_status(self, services_list):
        """The answer the dashboard and System have always had from GET /api/jellyfin (its own words for each part)."""
        raise NotImplementedError


class Jellyfin(MediaServer):
    id = "jellyfin"
    name = "Jellyfin"
    service_type = "jellyfin"
    page = "/settings-jellyfin.html"
    capabilities = ("play", "watched", "restart", "own_plugins", "conversion_test", "live_tv", "libraries_add", "first_run",
                    "history_import", "user_defaults", "metadata_folder", "detect", "updates")

    def _service(self, services_list):
        found = [s for s in services_list or [] if isinstance(s, dict) and s.get("type") == self.service_type
                 and s.get("enabled", True) and s.get("api_key") and s.get("url")]
        if not found:
            raise services.ServiceError(f"{self.name} is not set up yet. Add it with its API key in Settings, Apps")
        return found[0]

    def _send(self, service, method, path):
        import urllib.request
        req = urllib.request.Request(service["url"].rstrip("/") + path, method=method, headers={
            "Authorization": f'MediaBrowser Token="{service.get("api_key", "")}"', "Accept": "application/json", "User-Agent": services.USER_AGENT})
        return services._fetch(service, req, services.TIMEOUT)

    def legacy_status(self, services_list):
        return services.jellyfin(services_list)

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
                "update_available": bool(got.get("update")), "restart_needed": bool(got.get("restart")),
                "playing": len(got.get("playing") or []), "why": ""}

    def libraries(self, services_list):
        rows = self._send(self._service(services_list), "GET", "/Library/VirtualFolders") or []
        return [{"id": str(r.get("ItemId") or r.get("Name") or ""), "name": str(r.get("Name") or ""),
                 "type": str(r.get("CollectionType") or "mixed"), "count": None}
                for r in rows if isinstance(r, dict)]

    def playing(self, services_list):
        return [{"user": p["user"], "title": p["title"], "kind": p["type"], "device": p["device"], "converting": p["transcoding"],
                 "progress": p["progress"]} for p in self.legacy_status(services_list).get("playing") or []]

    def recent(self, services_list, limit=12):
        rows = self.legacy_status(services_list).get("added") or []
        return [{"title": r["title"], "kind": r["type"], "added": r["when"], "link": None} for r in rows[:max(0, int(limit))]]

    def refresh(self, services_list):
        self._send(self._service(services_list), "POST", "/Library/Refresh")
        return {"asked": True}

    def users(self, services_list):
        rows = self._send(self._service(services_list), "GET", "/Users") or []
        return [{"id": str(r.get("Id") or ""), "name": str(r.get("Name") or ""),
                 "admin": bool((r.get("Policy") or {}).get("IsAdministrator"))} for r in rows if isinstance(r, dict)]

    def sign_in_check(self, services_list):
        try:
            info = self._send(self._service(services_list), "GET", "/System/Info")
        except services.ServiceError as e:
            return {"ok": False, "why": str(e)}
        return {"ok": True, "why": "", "name": (info or {}).get("ServerName") or self.name, "version": (info or {}).get("Version", "")}

    def keys_needed(self):
        return [{"what": "API key", "where": "Dashboard, API keys", "kept": "Settings, Apps"}]


ADAPTERS = {Jellyfin.id: Jellyfin}


def active_id(data):
    """The id of the active media server from the settings (`extras.media_server`): "jellyfin" when it is not set, or
    "" for none. An id this Starboard does not have is treated as none, never as an error."""
    extras = (data or {}).get("extras") or {}
    chosen = extras.get("media_server") if isinstance(extras, dict) else None
    if chosen is None or chosen == "":
        return DEFAULT if chosen is None else ""
    return chosen if isinstance(chosen, str) and chosen in ADAPTERS else ""


def active(data):
    """The active adapter, or None when there is no media server."""
    cls = ADAPTERS.get(active_id(data))
    return cls() if cls else None


def state(data):
    """What GET /api/media-server answers, from the settings alone (nothing is asked of the server): the active
    one, whether it is set up, and the ones this Starboard has."""
    one = active(data)
    saved = (data or {}).get("services") or []
    have = bool(one and any(isinstance(s, dict) and s.get("type") == one.service_type and s.get("enabled", True) and s.get("api_key") for s in saved))
    return {"active": one.id if one else "", "name": one.name if one else "", "configured": have,
            "capabilities": list(one.capabilities) if one else [], "page": one.page if one else "",
            "available": [{"id": c.id, "name": c.name, "page": c.page} for c in ADAPTERS.values()]}


def status_for_pages(data):
    """The answer of GET /api/jellyfin: the active adapter's, as the pages have always had it. With no media server
    (or one this Starboard does not know) there is nothing configured."""
    one = active(data)
    if one is None:
        return {"configured": False}
    return one.legacy_status((data or {}).get("services") or [])


def in_use(data, pid):
    """True when the plug-in `pid` is the media server in use (the active one). A media server plug-in that is in use
    cannot be deactivated or removed: choose another one, or none, first (Settings, Media server)."""
    return bool(pid) and active_id(data) == pid
