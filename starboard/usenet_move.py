"""Moving Usenet settings from SABnzbd to NZBGet when Settings, Your install switches the Usenet app (7 November 2026).

SABnzbd keeps its news servers in /config/sabnzbd.ini, one [[name]] block under [servers]. Starboard reads that file
through Docker (as it reads API keys) before SABnzbd is stopped, and writes the same servers into NZBGet over its
JSON-RPC API (config, saveconfig, reload) once NZBGet answers. What moves: each server's address, port, user name,
password, connections, SSL, retention, whether it is on, and its priority. The queue and history do not move.
Passwords are read and written here only; they are never logged or shown.
"""
import io
import re
import tarfile
import urllib.parse

from . import containers


def parse_sab_servers(text):
    """The [[server]] blocks under [servers] in sabnzbd.ini, as dicts of their keys."""
    servers, current, in_servers = [], None, False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^\[[^\[\]]+\]$", line):  # a top-level section
            in_servers = line == "[servers]"
            current = None
            continue
        m = re.match(r"^\[\[(.+)\]\]$", line)
        if m:
            current = {"__section__": m.group(1)} if in_servers else None
            if current is not None:
                servers.append(current)
            continue
        if current is not None and "=" in line:
            k, v = line.split("=", 1)
            current[k.strip()] = v.strip()
    return servers


def _yes(v):
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def nzbget_server_options(servers):
    """NZBGet's ServerN.* options for SABnzbd's servers, numbered from 1 in SABnzbd's order."""
    out = []
    for i, s in enumerate(servers, 1):
        host = s.get("host") or s.get("__section__", "")
        if not host:
            continue
        out += [
            (f"Server{i}.Active", "yes" if _yes(s.get("enable", "1")) else "no"),
            (f"Server{i}.Name", s.get("displayname") or s.get("name") or host),
            (f"Server{i}.Level", str(int(s.get("priority") or 0))),
            (f"Server{i}.Host", host),
            (f"Server{i}.Port", str(int(s.get("port") or (563 if _yes(s.get("ssl", "0")) else 119)))),
            (f"Server{i}.Username", s.get("username", "")),
            (f"Server{i}.Password", s.get("password", "")),
            (f"Server{i}.Encryption", "yes" if _yes(s.get("ssl", "0")) else "no"),
            (f"Server{i}.Connections", str(int(s.get("connections") or 8))),
            (f"Server{i}.Retention", str(int(s.get("retention") or 0))),
        ]
    return out


def merged_config(current, server_options):
    """NZBGet's whole option list (as `config` returns it) with its servers replaced by `server_options`."""
    kept = [{"Name": o["Name"], "Value": o["Value"]} for o in current if not re.match(r"^Server\d+\.", o.get("Name", ""))]
    return kept + [{"Name": k, "Value": v} for k, v in server_options]


def read_sab_ini(container="sabnzbd"):
    """sabnzbd.ini from the running SABnzbd container, through Docker; None when it cannot be read."""
    if not containers.available():
        return None
    try:
        raw = containers.docker("GET", f"/containers/{container}/archive?path={urllib.parse.quote('/config/sabnzbd.ini')}",
                                raw=True, timeout=10)
        with tarfile.open(fileobj=io.BytesIO(raw[:2_000_000])) as tar:
            member = next((m for m in tar.getmembers() if m.isfile()), None)
            return tar.extractfile(member).read(1_000_000).decode("utf-8", "replace") if member else None
    except (containers.DockerError, tarfile.TarError, OSError):
        return None


def write_to_nzbget(rpc, servers):
    """Writes SABnzbd's servers into NZBGet through `rpc(method, params)`; returns how many moved."""
    options = nzbget_server_options(servers)
    if not options:
        return 0
    if rpc("saveconfig", [merged_config(rpc("config") or [], options)]):
        rpc("reload")
    return sum(1 for k, _ in options if k.endswith(".Host"))
