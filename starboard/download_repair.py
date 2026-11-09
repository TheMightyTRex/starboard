"""Reelix's download apps, checked against what Starboard set up (DASH-257). After the move the owner had to type
NZBGet's address, user and password into Reelix by hand, from data/stack/.env. Settings, Reelix, Download apps now
says when one does not match and offers Repair, which writes the address, user and password Starboard made up.
Only the apps Install apps installed are checked; one added by hand is left alone."""
from . import stack


def wanted(data_dir):
    """{implementation: settings Reelix should have} for the download apps in data/stack."""
    keys = set(stack.chosen_keys(data_dir) or [])
    vpn = "gluetun" in keys
    out = {}
    if "qbittorrent" in keys:
        pw = stack.qbittorrent_password(data_dir)
        out["qbittorrent"] = {"host": "gluetun" if vpn else "qbittorrent", "port": 8080,
                              **({"username": "admin", "password": pw} if pw else {})}
    if "nzbget" in keys and stack.nzbget_key(data_dir):
        user, _, pw = stack.nzbget_key(data_dir).partition(":")
        out["nzbget"] = {"host": "gluetun" if vpn else "nzbget", "port": 6789, "username": user, "password": pw}
    if "sabnzbd" in keys and stack.sabnzbd_key(data_dir):
        out["sabnzbd"] = {"host": "gluetun" if vpn else "sabnzbd", "port": stack.SABNZBD_PORT, "api_key": stack.sabnzbd_key(data_dir)}
    return out


def needs(data_dir, items):
    """The names of Reelix's download apps whose address, port or user differ from Starboard's set-up. Passwords and
    keys come back masked, so a wrong one shows only when Test fails; Repair writes them anyway."""
    want = wanted(data_dir)
    out = []
    for c in items:
        w = want.get(c.get("implementation"))
        have = c.get("settings") or {}
        if w and any(str(have.get(k)) != str(v) for k, v in w.items() if k in ("host", "port", "username")):
            out.append(c.get("name") or c.get("implementation"))
    return out


def repair(reelix, data_dir):
    """Writes Starboard's address, user and password into each matching download app in Reelix. Returns lines."""
    want = wanted(data_dir)
    _, items = reelix.call("GET", "/downloadclients")
    done = []
    for c in items or []:
        w = want.get(c.get("implementation"))
        if not w:
            continue
        body = {f: c.get(f) for f in ("implementation", "name", "enabled", "priority", "tags")}
        body["settings"] = {**(c.get("settings") or {}), **w}
        reelix.call("PUT", f"/downloadclients/{c['id']}", body)
        done.append(f"Repaired {c.get('name')} in Reelix")
    return done or ["Reelix has none of the download apps Starboard installed"]
