"""Speed limits for the download apps, from Starboard (DASH-578): qBittorrent and NZBGet.

Their own web pages are hard to use with a keyboard or a screen reader, and a speed limit is the thing people change most
(slow the downloads while the family streams, speed them up at night). Starboard asks each app only when the page is open
and when a person changes a limit; nothing runs in the background.

- qBittorrent (WebUI API v2): `app/preferences` has `dl_limit` and `up_limit` in KiB a second (0 or -1 mean none),
  `app/setPreferences` changes them, `transfer/speedLimitsMode` says whether its alternative limits are on and
  `transfer/toggleSpeedLimitsMode` switches them. The alternative limits themselves stay in qBittorrent.
- NZBGet (JSON-RPC): `status` has `DownloadLimit` in bytes a second (0 is none), and `rate` sets it in KiB a second.
SABnzbd is left out: its limit may be a percentage of a line speed set elsewhere, so a figure here could mislead.
"""

import json

from . import services
from .services import ServiceError

KINDS = ("qbittorrent", "nzbget")
MOST = 10_000_000  # KiB a second: a speed no home line reaches, so a typing slip is refused


def clients(all_services):
    return [s for s in all_services if s.get("enabled", True) and s.get("url") and s.get("api_key") and s["type"] in KINDS]


def _none(value):
    """qBittorrent says -1 or 0 for no limit."""
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def read(service):
    """{id, name, kind, down, up, alt}: limits in KiB a second, 0 for none. `up` and `alt` are None for NZBGet."""
    if service["type"] == "qbittorrent":
        prefs = services.qbit(service, "app/preferences") or {}
        mode = str(services.qbit(service, "transfer/speedLimitsMode") or "0").strip()
        return {"id": service["id"], "name": service["name"], "kind": "torrent", "down": _none(prefs.get("dl_limit")),
                "up": _none(prefs.get("up_limit")), "alt": mode == "1"}
    status = services.nzbget(service, "status") or {}
    return {"id": service["id"], "name": service["name"], "kind": "usenet", "down": _none(status.get("DownloadLimit")) // 1024,
            "up": None, "alt": None}


def _limit(body, key, label):
    value = body.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MOST:
        raise ValueError(f"{label}: give a whole number of kilobytes a second from 0 to {MOST:,}. 0 means no limit")
    return value


def apply(service, body):
    """Sets what the body names (down, up, alt) and returns the limits as read back. Raises ValueError for a bad value
    and ServiceError when the app does not answer."""
    if service["type"] == "qbittorrent":
        change = {}
        if "down" in body:
            change["dl_limit"] = _limit(body, "down", "Download limit")
        if "up" in body:
            change["up_limit"] = _limit(body, "up", "Upload limit")
        if "alt" in body and not isinstance(body["alt"], bool):
            raise ValueError("Alternative speed limits: send true or false")
        if not change and "alt" not in body:
            raise ValueError("Send down, up or alt")
        if change:
            services.qbit(service, "app/setPreferences", {"json": json.dumps(change)})
        if "alt" in body:
            now = str(services.qbit(service, "transfer/speedLimitsMode") or "0").strip() == "1"
            if now != body["alt"]:  # a toggle: ask only when it must change, so a repeat does nothing
                services.qbit(service, "transfer/toggleSpeedLimitsMode", {})
    else:
        if "up" in body or "alt" in body:
            raise ValueError(f"{service['name']} has a download limit only")
        services.nzbget(service, "rate", [_limit(body, "down", "Download limit")])
    services.forget("transfer")
    return read(service)


def words(row):
    """What changed, for the log."""
    now = f"download {row['down']} KB/s" if row["down"] else "download no limit"
    if row["up"] is not None:
        now += f", upload {row['up']} KB/s" if row["up"] else ", upload no limit"
    if row["alt"]:
        now += ", alternative limits on"
    return now


__all__ = ["clients", "read", "apply", "words", "ServiceError"]
