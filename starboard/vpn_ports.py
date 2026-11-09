"""Port forwarding through the VPN (DASH-233): when Gluetun forwards a port (Private Internet Access, Proton VPN,
Perfect Privacy, PrivateVPN), qBittorrent listens on that port, so others in a torrent can connect to it and
downloads are faster. Gluetun's port can change each time the VPN connects, so Starboard checks every 10 minutes
(a background job, only while both apps are set up with their keys) and changes qBittorrent's listening port when
it differs. Gluetun's own up command would need qBittorrent to let anything on the VPN in without signing in."""
import json

from . import logs, services, stack


def apps(cfg):
    on = [s for s in cfg.data["services"] if s.get("enabled", True) and s.get("api_key")]
    gluetun = next((s for s in on if s["type"] == "gluetun"), None)
    qbit = next((s for s in on if s["type"] == "qbittorrent"), None)
    return gluetun, qbit


def wanted(cfg, data_dir):
    gluetun, qbit = apps(cfg)
    return bool(gluetun and qbit and stack.env_values(data_dir).get("VPN_PORT_FORWARDING") == "on")


def sync(cfg):
    """Returns what it did, in words."""
    gluetun, qbit = apps(cfg)
    if not (gluetun and qbit):
        return "Gluetun or qBittorrent is not set up with its key"
    port = (services._gluetun(gluetun, "/v1/portforward") or {}).get("port") or 0
    if not port:
        return "The VPN has not forwarded a port yet"
    now = (services.qbit(qbit, "app/preferences") or {}).get("listen_port")
    if now == port:
        return f"qBittorrent listens on the forwarded port, {port}"
    services.qbit(qbit, "app/setPreferences", {"json": json.dumps({"listen_port": port, "random_port": False})})
    logs.event("info", "vpn", f"qBittorrent now listens on the VPN's forwarded port, {port}")
    return f"qBittorrent now listens on the forwarded port, {port} (was {now})"
