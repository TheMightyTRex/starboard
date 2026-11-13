"""Taking over apps someone already runs from their own Compose file (DASH-151, 8 November 2026).

A server set up by hand before Starboard has its apps in its own Compose file, with its own folder layout. Install
apps leaves those apps out, and Settings, Your install cannot change them. This module moves them into Starboard's
stack (data/stack, project media-stack) without losing anything, and can put them back:

- Each app's settings are copied, never moved, from the old folders into Starboard's settings folder. The old
  folders are never written to, so going back always finds them as they were.
- What the app relies on is kept: paths to media it already uses (Jellyfin's /media, say), devices such as /dev/dri
  for hardware transcoding, extra ports, its own settings in the environment, its image (a pinned qBittorrent stays
  pinned), and whether it runs through the VPN. These go in data/stack/kept.json (secret values in .env), so later
  changes in Your install keep them too (stack.build, stack.read_keep).
- The apps Reelix replaces (Radarr, Sonarr and the others), and SABnzbd when NZBGet takes its place, are stopped and
  removed once their contents have moved (reelix_move.py moves them into Reelix; usenet_move.py moves SABnzbd's
  servers). Their settings folders stay.
- Before anything stops, the rollback point: every image in use is tagged starboard-rollback/<name>:<time>, the old
  Compose files and Starboard's own set-up files are copied into data/stack/takeover, and a small override file pins
  the old Compose file to those images. Roll back stops the taken-over apps and starts the old ones from the old
  Compose file, exactly as they were.

Apps the chosen install does not have, apps that are stopped, and containers that did not come from a Compose file
are left as they are.
"""
import json
import os
import re
import shutil
import threading
import time
import urllib.parse

from . import containers, stack, tasklist

# Container names that mean a catalogue app under another name.
ALIASES = {"readarr": "bookshelf", "jellyseerr": "seerr", "overseerr": "seerr"}
# Images that say which app a container is whatever it is called: Seerr, and Overseerr and Jellyseerr, which merged
# into Seerr in 2026 (ghcr.io/seerr-team/seerr, fallenbagel/jellyseerr, sctx/overseerr, linuxserver/overseerr).
IMAGE_KEYS = {"seerr": "seerr", "jellyseerr": "seerr", "overseerr": "seerr"}
# Values whose names look secret go in .env (mode 600), never in compose.yaml.
_SECRET = re.compile(r"(PASS|KEY|TOKEN|SECRET|CREDENTIAL)", re.I)
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SAFE_HOST_PATH = re.compile(r"^/[A-Za-z0-9._/@+-]{0,300}$")
SYSTEM_SOURCES = ("/var/run/docker.sock", "/run/docker.sock", "/etc/localtime", "/etc/timezone", "/dev/")
RECORD = "takeover"  # folder inside data/stack


def _db_services():
    return {a["db"]["service"]: k for k, a in stack.APPS.items() if a.get("db")}


def catalogue_key(name, image=""):
    """The catalogue key (stack.APPS, or a database service) a container name stands for, or None. A container with
    another name is still known by its image where IMAGE_KEYS says so."""
    name = ALIASES.get(name, name)
    if name in stack.APPS or name in _db_services():
        return name
    last = str(image or "").split("@", 1)[0].rsplit("/", 1)[-1]  # seerr:latest from ghcr.io/seerr-team/seerr:latest
    return IMAGE_KEYS.get(last.split(":", 1)[0].lower())


def _inspect(name):
    return containers.docker("GET", f"/containers/{urllib.parse.quote(name, safe='')}/json")


def _image_env(image_id):
    try:
        info = containers.docker("GET", f"/images/{urllib.parse.quote(image_id, safe='')}/json")
    except containers.DockerError:
        return {}
    return dict(e.split("=", 1) for e in ((info or {}).get("Config") or {}).get("Env") or [] if "=" in e)


def found():
    """Containers on this computer from Compose files other than Starboard's, each with the catalogue app it is."""
    if not containers.available():
        return []
    out = []
    for c in containers.docker("GET", "/containers/json?all=1") or []:
        name = c["Names"][0].lstrip("/")
        labels = c.get("Labels") or {}
        if labels.get("com.docker.compose.project") == stack.PROJECT or labels.get("starboard.updater") or \
                labels.get("com.docker.compose.service") == "starboard":
            continue
        key = catalogue_key(name, c.get("Image"))
        if not key:
            continue
        out.append({"name": name, "key": key, "running": c.get("State") == "running",
                    "project": labels.get("com.docker.compose.project"),
                    "service": labels.get("com.docker.compose.service"),
                    "folder": labels.get("com.docker.compose.project.working_dir"),
                    "files": [f for f in (labels.get("com.docker.compose.project.config_files") or "").split(",") if f]})
    return out


def _under(path, root):
    return bool(root) and (path == root or path.startswith(root.rstrip("/") + "/"))


def _expand(template, cfg, data):
    return template.replace(stack.CFG, cfg).replace(stack.DATA, data)


def _spec(key):
    """(volumes, environment) Starboard writes for a catalogue key or database service."""
    if key in stack.APPS:
        a = stack.APPS[key]
        return a.get("volumes") or [], a.get("env") or {}
    app = stack.APPS[_db_services()[key]]
    return [app["db"]["volume"]], app["db"]["env"]


def config_base(infos, keys):
    """The folder that holds the old settings folders: the common parent of the folders the apps mount where
    Starboard mounts their settings. Mounts under it are settings, so they are copied; None when there is none."""
    sources = []
    for name, info in infos.items():
        vols, _ = _spec(keys[name])
        places = {v.split(":")[1] for v in vols if v.startswith(stack.CFG)}
        sources += [m["Source"] for m in info.get("Mounts") or [] if m.get("Destination") in places and m.get("Source")]
    if not sources:
        return None
    base = os.path.commonpath(sources)
    if len(sources) == 1:  # one app: its own folder's parent, so a sibling folder of the same app is included
        base = os.path.dirname(base)
    return base if base not in ("/", "/home", "/mnt", "/srv", "/opt", "/var") else None


def keep_for(key, name, info, image_env, cfg, data, base, globals_, owner_names, vpn_bindings=None):
    """What app `key` (container `name`, inspected as `info`) keeps when Starboard takes it over, and which folders
    are copied. Returns (keep, copies, shared): copies are (old folder, new folder); shared are folders the new app
    uses in place (neither settings nor media Starboard knows), listed so the person knows going back does not
    restore them."""
    vols, app_env = _spec(key)
    starboard = {v.split(":")[1]: v.split(":")[0] for v in vols}
    keep = {"volumes": [], "devices": [], "ports": [], "env": {}, "vars": {}}
    mode = ((info.get("HostConfig") or {}).get("NetworkMode") or "")
    copies, shared = [], []
    image = (info.get("Config") or {}).get("Image") or ""
    default_image = stack.APPS[key]["image"] if key in stack.APPS else stack.APPS[_db_services()[key]]["db"]["image"]
    if image and image != default_image and not image.startswith("sha256:") and key != "reelix":
        keep["image"] = image
    host = info.get("HostConfig") or {}
    mode = host.get("NetworkMode") or ""
    if key in stack.APPS and not stack.APPS[key].get("gluetun"):
        owner = owner_names.get(mode.split(":", 1)[1], "") if mode.startswith("container:") else ""
        vpn = owner == "gluetun"
        if vpn != bool(stack.APPS[key].get("vpn")):
            keep["vpn"] = vpn
    for d in host.get("Devices") or []:
        on, inside = d.get("PathOnHost", ""), d.get("PathInContainer", "")
        if on and inside and on != "/dev/net/tun":
            keep["devices"].append(on if on == inside else f"{on}:{inside}")
    inside_ports = {p.split(":", 1)[1] for p in (stack.APPS.get(key) or {}).get("ports", [])}
    # Each port keeps the number it has now (owner, 8 November 2026: Jellyfin and Audiobookshelf stay where people
    # and devices know them). An app through the VPN publishes its ports on Gluetun's container.
    bindings = (vpn_bindings or {}) if mode.startswith("container:") else (host.get("PortBindings") or {})
    port_map = {}
    for label in inside_ports:
        port, _, proto = label.partition("/")
        hostport = next((b.get("HostPort") for b in bindings.get(f"{port}/{proto or 'tcp'}") or []
                         if str(b.get("HostPort", "")).isdigit()), None)
        if hostport:
            port_map[label] = int(hostport)
    if port_map:
        keep["port_map"] = port_map
    # A port the app did not publish before stays unpublished (qBittorrent's 6881 when the VPN forwards a port).
    unpublished = sorted(label for label in inside_ports if label not in port_map)
    if unpublished and (port_map or bindings):
        keep["unpublished"] = unpublished
    for inside, binds in (host.get("PortBindings") or {}).items():
        port, _, proto = inside.partition("/")
        label = port + ("/udp" if proto == "udp" else "")
        if label in inside_ports or key == "gluetun":
            continue
        for b in binds or []:
            if str(b.get("HostPort", "")).isdigit():
                keep["ports"].append(f"{b['HostPort']}:{label}")
    for m in info.get("Mounts") or []:
        src, dst = m.get("Source") or m.get("Name") or "", m.get("Destination") or ""
        if not src or not dst:
            continue
        ro = "" if m.get("RW", True) else ":ro"
        if m.get("Type") == "volume":
            keep["volumes"].append(f"{m.get('Name')}:{dst}{ro}")  # a named Docker volume: used in place
            shared.append(m.get("Name"))
            continue
        if not _SAFE_HOST_PATH.match(src) or not _SAFE_HOST_PATH.match(dst):
            raise ValueError(f"{name} uses a folder Starboard cannot handle safely ({src}). Take it over by hand")
        if dst in starboard and starboard[dst].startswith(stack.CFG):
            copies.append((src, _expand(starboard[dst], cfg, data)))
        elif dst in starboard:
            if src != _expand(starboard[dst], cfg, data):
                keep["volumes"].append(f"{src}:{dst}{ro}")
        elif _under(src, base):
            # A settings folder Starboard has no place for: its own folder next to the app's, never inside it
            # (the app's folder may be what the app mounts, as Wizarr's database is).
            place = f"{key}-kept/" + (re.sub(r"[^A-Za-z0-9._-]+", "_", dst.strip("/")) or "root")
            copies.append((src, f"{cfg}/{place}"))
            keep["volumes"].append(f"{stack.CFG}/{place}:{dst}{ro}")
        else:
            keep["volumes"].append(f"{src}:{dst}{ro}")
            if not (_under(src, data) or any(src == s or src.startswith(s) for s in SYSTEM_SOURCES)):
                shared.append(src)
    env = dict(e.split("=", 1) for e in (info.get("Config") or {}).get("Env") or [] if "=" in e)
    for k, v in env.items():
        if image_env.get(k) == v or k in ("PATH", "HOME", "HOSTNAME"):
            continue
        if k in ("PUID", "PGID", "TZ") and globals_.get(k) == v:
            continue
        theirs = app_env.get(k)
        if key == "gluetun" and k in stack.VPN_ENV:
            continue  # the VPN details go in through Starboard's own VPN fields (vpn_choice)
        if isinstance(theirs, str) and re.fullmatch(r"\$\{([A-Z0-9_]+)\}", theirs):
            var = theirs[2:-1]
            if var in ("PUID", "PGID", "TZ", "CONFIG_DIR", "DATA_DIR"):
                continue
            _check_secret(name, k, v)
            keep["vars"][var] = v
            continue
        if theirs == v:
            continue
        if _SECRET.search(k):
            _check_secret(name, k, v)
            keep["env"][k] = {"var": re.sub(r"[^A-Z0-9_]", "_", f"KEPT_{key}_{k}".upper()), "value": v}
        else:
            keep["env"][k] = {"value": v}
    keep = {f: v for f, v in keep.items() if v not in ([], {})}
    return keep, copies, shared


def _check_secret(name, var, value):
    if "'" in value or "\n" in value or "\r" in value:
        raise ValueError(f"{name}'s {var} has a ' mark or a line break, which Starboard's .env file cannot hold. "
                         "Change it, or take this app over by hand")


def vpn_choice(info, image_env):
    """Starboard's VPN fields from the old Gluetun's settings (its own values, then its image's defaults)."""
    env = {**image_env, **dict(e.split("=", 1) for e in (info.get("Config") or {}).get("Env") or [] if "=" in e)}
    out = {field: env.get(name, "") for name, field in stack.VPN_ENV.items()}
    out["type"] = (out.get("type") or "wireguard").lower()
    return out


def existing_vpn(with_secrets=False):
    """The VPN details of a Gluetun already running on this computer outside Starboard's own apps (DASH-132), so the
    set-up can offer to use them instead of asking again. Without with_secrets, only what the set-up shows: its name,
    provider, connection and countries, never the key or password. None when there is none or Docker cannot say."""
    try:
        for c in found():
            if c["key"] != "gluetun" or not c["running"]:
                continue
            info = _inspect(c["name"])
            v = vpn_choice(info, _image_env(info.get("Image", "")))
            if not v.get("provider"):
                continue
            secret = v.get("wireguard_private_key") if v["type"] == "wireguard" else v.get("openvpn_password")
            if with_secrets:
                return {**v, "name": c["name"]}
            return {"name": c["name"], "provider": v["provider"], "type": v["type"], "countries": v.get("countries", ""),
                    "complete": bool(secret)}
    except containers.DockerError:
        return None
    return None


def fill_vpn(choice):
    """A set-up answer of "use my current Gluetun's VPN" becomes its details, read here so the key never goes through
    the browser or the terminal."""
    want = (choice.get("vpn") or {}).get("use_existing")
    if not want:
        return choice
    v = existing_vpn(with_secrets=True)
    if not v or v["name"] != want:
        raise ValueError("Starboard could not read your current Gluetun's VPN details. Type them instead")
    return {**choice, "vpn": {k: v.get(k, "") for k in stack.VPN_ENV.values()}}


def _globals(infos):
    for info in infos.values():
        env = dict(e.split("=", 1) for e in (info.get("Config") or {}).get("Env") or [] if "=" in e)
        if env.get("PUID"):
            return {k: env.get(k) for k in ("PUID", "PGID", "TZ")}
    return {}


def plan(data_dir, install="full", usenet="nzbget", config_dir=None, media_dir=None, check=None, keep_apps=()):
    """What taking over the apps found here means, for one of stack.INSTALLS. Nothing changes. `keep_apps` are apps
    taken over although the install does not have them (Seerr, when the person keeps it beside Reelix: DASH-192).

    Returns {take, replace, leave, new, choice, keep, copies, shared, sab, warnings}: `take` are the containers that
    become Starboard's, `replace` the ones stopped because Reelix or NZBGet takes their place, `leave` the ones left as
    they are (with why), `new` the apps installed fresh, and `choice` what stack.build writes."""
    if not containers.available():
        raise ValueError("Starboard needs Docker access to take over your apps")
    now = stack.current_choice(data_dir)
    spec = stack.install_choice(install, check=check, usenet=usenet)
    extra = [k for k in keep_apps if k in stack.APPS]
    wanted = set(spec["apps"]) | set(extra) | {stack.APPS[k]["db"]["service"] for k in spec["apps"] if stack.APPS[k].get("db")}
    usenet = spec["usenet"]
    have = set(now["apps"]) if now else set()
    take, replace, leave = [], [], []
    for c in found():
        key = c["key"]
        if key in have or (key in _db_services() and _db_services()[key] in have):
            leave.append({**c, "why": "Starboard runs it already"})
        elif not c["running"]:
            leave.append({**c, "why": "stopped, so left as it is"})
        elif not (c["project"] and c["folder"] and c["files"] and c["service"]):
            leave.append({**c, "why": "not started from a Compose file, so Starboard could not put it back"})
        elif key in wanted:
            take.append(c)
        elif key in stack.REPLACED_BY_REELIX:
            replace.append({**c, "by": "Reelix"})
        elif key in stack.USENET_APPS and key != usenet:
            replace.append({**c, "by": stack.APPS[usenet]["name"]})
        else:
            leave.append({**c, "why": f"not part of {spec['name']}"})
    if not take and not replace:
        raise ValueError("Starboard found no apps here to take over")
    infos = {c["name"]: _inspect(c["name"]) for c in take}
    keys = {c["name"]: c["key"] for c in take}
    owners = {}
    for c in containers.docker("GET", "/containers/json?all=1") or []:
        owners[c["Id"]] = c["Names"][0].lstrip("/")
    glob = _globals(infos)
    cfg = stack.clean_folder((now or {}).get("config_dir") or config_dir, "settings folder")
    data = stack.clean_folder((now or {}).get("data_dir") or media_dir, "media folder")
    base = config_base(infos, keys)
    if base and (_under(cfg, base) or _under(base, cfg)):
        raise ValueError(f"Choose a settings folder outside {base}: that is where your apps keep their settings now, and "
                         "Starboard copies them from there")
    keep, copies, shared, warnings, copy_apps = {}, [], [], [], []
    vpn_bindings = {}
    for c in found():
        if c["key"] == "gluetun" and c["running"]:
            vpn_bindings = ((_inspect(c["name"]).get("HostConfig") or {}).get("PortBindings") or {})
    for c in take:
        info = infos[c["name"]]
        k, cp, sh = keep_for(c["key"], c["name"], info, _image_env(info.get("Image", "")), cfg, data, base, glob, owners,
                             vpn_bindings)
        keep[c["key"]] = k
        copies += cp
        label = f"{stack.APPS[c['key']]['name']}'s settings" if c["key"] in stack.APPS else f"{stack.APPS[_db_services()[c['key']]]['name']}'s database"
        copy_apps += [label] * len(cp)
        shared += [f"{c['name']}: {s}" for s in sh]
    targets = [new for _, new in copies]
    for src, _ in copies:  # a copy never lands in, or contains, a folder it copies from
        if _under(cfg, src) or _under(src, cfg) or any(_under(t, src) for t in targets):
            raise ValueError(f"Choose a settings folder outside {base or src}: your apps keep their settings there now, "
                             "and Starboard copies them from there")
    if len(set(targets)) != len(targets):
        raise ValueError("Two apps would copy their settings into the same folder. Take them over by hand")
    choice = {**(now or {}), "config_dir": cfg, "data_dir": data,
              "puid": int((now or {}).get("puid") or glob.get("PUID") or 1000),
              "pgid": int((now or {}).get("pgid") or glob.get("PGID") or 1000),
              "tz": (now or {}).get("tz") or glob.get("TZ") or "Etc/UTC",
              "reelix_edition": (now or {}).get("reelix_edition") or spec["reelix_edition"]}
    choice["apps"], _ = stack.with_needs(sorted(have | set(spec["apps"]) | set(extra)))
    choice["keep"] = {**((now or {}).get("keep") or {}), **keep}
    if "gluetun" in choice["apps"] and not (now or {}).get("vpn"):
        g = next((c for c in take if c["key"] == "gluetun"), None)
        if g:
            choice["vpn"] = vpn_choice(infos[g["name"]], _image_env(infos[g["name"]].get("Image", "")))
        else:
            warnings.append("Gluetun is new, so Starboard needs your VPN details: add them in Install apps first")
    own = set(stack.compose_ports(data_dir))
    for c in take:
        for binds in ((infos[c["name"]].get("HostConfig") or {}).get("PortBindings") or {}).values():
            own.update(int(b["HostPort"]) for b in binds or [] if str(b.get("HostPort", "")).isdigit())
    choice["own_ports"] = sorted(own)
    sab = next((c for c in replace if c["key"] == "sabnzbd"), None) if usenet == "nzbget" else None
    if shared:
        warnings.append("These folders are used in place, not copied, so going back does not restore them: " + "; ".join(shared))
    names = {k: a["name"] for k, a in stack.APPS.items()}
    names.update({svc: f"{stack.APPS[app]['name']}'s database" for svc, app in _db_services().items()})
    return {"install": spec["key"], "install_name": spec["name"], "usenet": usenet,
            "take": [{"name": c["name"], "key": c["key"], "app": names.get(c["key"], c["key"])} for c in take],
            "replace": [{"name": c["name"], "key": c["key"], "app": names.get(c["key"], c["name"]), "by": c["by"]} for c in replace],
            "leave": [{"name": c["name"], "why": c["why"]} for c in leave],
            "new": [names[k] for k in choice["apps"] if k not in have and k not in keys.values()],
            "choice": choice, "copies": copies, "copy_apps": copy_apps, "warnings": warnings, "sab": bool(sab),
            "containers": take + replace, "config_base": base}


def summary(p):
    """The plan without the parts that hold secrets or internal detail, for the page."""
    return {k: p[k] for k in ("install", "install_name", "usenet", "take", "replace", "leave", "new", "warnings", "sab",
                              "config_base")} | {
        "copies": [{"from": a, "to": b} for a, b in p["copies"]],
        "settings_folder": p["choice"]["config_dir"], "media_folder": p["choice"]["data_dir"],
        "kept": {k: {f: (sorted(v) if f in ("env", "vars") else v) for f, v in keep.items()}
                 for k, keep in p["choice"]["keep"].items()}}


# The rollback point and going back ------------------------------------------------------------------------------

def record_folder(data_dir):
    return os.path.join(stack.folder(data_dir), RECORD)


def read_record(data_dir):
    try:
        with open(os.path.join(record_folder(data_dir), "record.json"), encoding="utf-8") as f:
            rec = json.load(f)
        return rec if isinstance(rec, dict) and rec.get("containers") else None
    except (OSError, ValueError):
        return None


def rollback_override(entries):
    """A Compose override pinning each old service to the image it ran when Starboard took over."""
    lines = ["# Written by Starboard when it took over these apps: the images they ran then, so going back starts",
             "# exactly those versions.", "services:"]
    for e in entries:
        lines += [f"  {e['service']}:", f"    image: {e['rollback_image']}"]
    return "\n".join(lines) + "\n"


def make_record(data_dir, p, stamp, tag=None):
    """Saves the rollback point: tags each image, copies Starboard's own set-up files, and writes record.json and one
    override file per old Compose project. Returns the record."""
    folder_ = record_folder(data_dir)
    if os.path.exists(os.path.join(folder_, "record.json")):
        raise ValueError("Starboard took over apps here before, and that can still be rolled back. Roll it back, or "
                         "clear it in Settings, Your install, before taking over again")
    os.makedirs(os.path.join(folder_, "stack-before"), mode=0o700, exist_ok=True)
    for name in ("compose.yaml", ".env", stack.KEEP_FILE):
        src = os.path.join(stack.folder(data_dir), name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(folder_, "stack-before", name))
    tag = tag or (lambda image_id, repo, t: containers.docker(
        "POST", f"/images/{urllib.parse.quote(image_id, safe='')}/tag?repo={urllib.parse.quote(repo, safe='')}&tag={t}"))
    entries = []
    for c in p["containers"]:
        info = _inspect(c["name"])
        repo = "starboard-rollback/" + re.sub(r"[^a-z0-9._-]", "-", c["name"].lower())
        tag(info["Image"], repo, stamp)
        entries.append({"name": c["name"], "key": c["key"], "project": c["project"], "service": c["service"],
                        "folder": c["folder"], "files": c["files"], "image": (info.get("Config") or {}).get("Image"),
                        "image_id": info["Image"], "rollback_image": f"{repo}:{stamp}",
                        # Its settings folders, so a replaced app's can go to the holding folder later (DASH-191).
                        "settings": settings_folders(info)})
    projects = sorted({e["project"] for e in entries})
    for proj in projects:
        with open(os.path.join(folder_, f"rollback-{proj}.yaml"), "w", encoding="utf-8") as f:
            f.write(rollback_override([e for e in entries if e["project"] == proj]))
    record = {"made": time.time(), "stamp": stamp, "containers": entries, "copies": p["copies"],
              "had_stack": os.path.exists(os.path.join(folder_, "stack-before", "compose.yaml")),
              "install": p["install"]}
    with os.fdopen(os.open(os.path.join(folder_, "record.json"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(record, f, indent=1)
    return record


def settings_folders(info):
    """The host folders a container mounts as its settings (/config, /app/config)."""
    return [m["Source"] for m in info.get("Mounts") or [] if m.get("Type") == "bind" and m.get("Source")
            and m.get("Destination") in ("/config", "/app/config") and _SAFE_HOST_PATH.match(m["Source"])]


PROGRESS = "takeover-progress"  # in data/stack: the helper writes the id of each step as it starts it (DASH-252)


def _mark(progress, task_id):
    return f"echo {containers._quote(task_id)} >> {containers._quote(progress)}" if progress else ":"


def takeover_tasks(p):
    """The steps of a takeover, in order, as the dialog lists them (DASH-252, DASH-254)."""
    items = [("record", "Save the way back"), ("stop", "Stop your old apps")]
    for i, (_, _) in enumerate(p["copies"]):
        owner = (p.get("copy_apps") or [""] * len(p["copies"]))[i]
        items.append((f"copy-{i}", f"Copy {owner}" if owner else "Copy settings"))
    items += [("remove", "Remove the old containers"), ("start", "Start your apps in Starboard")]
    if p.get("sab"):
        items.append(("usenet", "Move the Usenet servers into NZBGet"))
    if "reelix" in p["choice"]["apps"]:
        items.append(("reelix", "Connect Reelix to the download apps"))
    items.append(("dashboard", "Update your dashboard"))
    return items


def takeover_script(record, host_stack, cfg, data=None, folders=(), owner=(1000, 1000), progress=None):
    """The helper's script: stop the old apps, copy their settings, remove the old containers, start Starboard's
    stack. Until the old containers are removed, a failure starts them again and changes nothing else. With
    `progress`, each step writes its id there as it starts (takeover_tasks)."""
    q = containers._quote
    names = " ".join(q(e["name"]) for e in record["containers"])
    back = f"docker start {names} >/dev/null 2>&1; exit 1"
    lines = ["set -u", f"cd {q(host_stack)}",
             f"mkdir -p {q(host_stack)}/takeover/old"]
    for e in record["containers"]:  # the old Compose files, as they were
        for f in e["files"]:
            lines.append(f"cp -p {q(f)} {q(host_stack)}/takeover/old/{q(e['project'] + '--' + os.path.basename(f))} 2>/dev/null || true")
        lines.append(f"[ -f {q(e['folder'])}/.env ] && cp -p {q(e['folder'])}/.env {q(host_stack)}/takeover/old/{q(e['project'] + '--.env')} || true")
    lines.append(_mark(progress, "stop"))
    lines.append(f"echo 'Stopping the old apps'; docker stop -t 60 {names} || {{ {back}; }}")
    need = " ".join(q(a) for a, _ in record["copies"])
    if need:
        lines += [f"mkdir -p {q(cfg)}",
                  f"need=$(du -sk {need} | awk '{{s+=$1}} END {{print s+0}}'); free=$(df -Pk {q(cfg)} | awk 'NR==2 {{print $4}}')",
                  f"if [ \"$need\" -gt \"$free\" ]; then echo \"Not enough space: the settings need $need KB and {cfg} has $free KB\"; {back}; fi"]
    for i, (src, dst) in enumerate(record["copies"]):
        lines.append(_mark(progress, f"copy-{i}"))
        lines += [f"if [ -e {q(dst)} ] && [ -n \"$(ls -A {q(dst)} 2>/dev/null)\" ]; then echo {q('Already has files, so nothing was copied over it: ' + dst)}; {back}; fi",
                  f"mkdir -p {q(dst)} && cp -a {q(src.rstrip('/') + '/.')} {q(dst + '/')} && "
                  f"chown \"$(stat -c '%u:%g' {q(src)})\" {q(dst)} && chmod \"$(stat -c '%a' {q(src)})\" {q(dst)} "
                  f"|| {{ echo {q('Could not copy ' + src)}; {back}; }}"]
    uid, gid = int(owner[0]), int(owner[1])
    if folders:  # the folders new apps use, made and owned as Install apps does (stack._start)
        lines.append("mkdir -p " + " ".join(q(f) for f in folders) + " || true")
    lines.append(stack.ffmpeg_wrap_script(cfg, uid, gid) + " || echo 'Could not give Jellyfin the Live TV wrapper'")
    lines += [_mark(progress, "remove"),
              f"echo 'Removing the old containers (their settings folders and images stay)'; docker rm {names} || {{ {back}; }}",
              _mark(progress, "start"),
              f"docker compose -p {stack.PROJECT} --env-file .env -f compose.yaml up -d --remove-orphans 2>&1"]
    if data:  # as Install apps does (stack._start): the folders themselves, then each app's, not a database's
        lines.append(f"chown {uid}:{gid} {q(cfg)} {q(data)} || true")
        lines.append(f"for d in {q(cfg)}/* {q(data)}/media {q(data)}/downloads; do case \"$d\" in *-db) continue ;; esac; "
                     f"[ -d \"$d\" ] && chown {uid}:{gid} \"$d\"; done; true")
    return "\n".join(lines)


def rollback_tasks(record):
    """The steps of going back, in order, as the dialog lists them (DASH-252)."""
    items = [("files", "Put Starboard's set-up files back"), ("stop", "Stop the apps Starboard took over")]
    for proj in dict.fromkeys(e["project"] for e in record["containers"]):
        items.append((f"old-{proj}", f"Start your old apps from {proj}"))
    return items + [("aside", "Put the way back aside")]


def rollback_script(record, host_stack, progress=None):
    """The helper's script for going back: Starboard's set-up files as they were, Starboard's stack without the
    taken-over apps, then the old apps from their own Compose files on the images they ran."""
    q = containers._quote
    hs = q(host_stack)
    names = " ".join(q(e["name"]) for e in record["containers"])
    lines = ["set -u", f"cd {hs}", _mark(progress, "files")]
    if record.get("had_stack"):
        lines += [f"cp -p {hs}/takeover/stack-before/compose.yaml {hs}/compose.yaml",
                  f"cp -p {hs}/takeover/stack-before/.env {hs}/.env",
                  f"if [ -f {hs}/takeover/stack-before/{stack.KEEP_FILE} ]; then cp -p {hs}/takeover/stack-before/{stack.KEEP_FILE} {hs}/{stack.KEEP_FILE}; else rm -f {hs}/{stack.KEEP_FILE}; fi",
                  f"docker compose -p {stack.PROJECT} --env-file .env -f compose.yaml up -d --remove-orphans 2>&1"]
    else:
        lines += [f"docker compose -p {stack.PROJECT} --env-file .env -f compose.yaml down 2>&1",
                  f"mkdir -p {hs}/takeover/after && mv {hs}/compose.yaml {hs}/.env {hs}/takeover/after/ 2>/dev/null; rm -f {hs}/{stack.KEEP_FILE}"]
    lines.append(_mark(progress, "stop"))
    lines.append(f"docker rm -f {names} >/dev/null 2>&1 || true")  # any of the names Starboard's stack still holds
    by_project = {}
    for e in record["containers"]:
        by_project.setdefault((e["project"], e["folder"], tuple(e["files"])), []).append(e["service"])
    for (proj, folder_, files), services in by_project.items():
        fs = " ".join(f"-f {q(f)}" for f in files)
        lines.append(_mark(progress, f"old-{proj}"))
        lines.append(f"cd {q(folder_)} && docker compose -p {q(proj)} {fs} -f {hs}/takeover/rollback-{q(proj)}.yaml "
                     f"up -d --no-deps {' '.join(q(s) for s in services)} 2>&1")
    lines.append(_mark(progress, "aside"))
    lines.append(f"cd {hs} && mkdir -p {hs}/takeover-rolled-back && mv {hs}/takeover {hs}/takeover-rolled-back/$(date +%Y%m%d-%H%M%S)")
    return "\n".join(lines)


def binds_for(record, cfg, data=None):
    """The host folders the helper needs: Starboard's settings and media folders, the old settings folders (read only)
    and the old Compose folders."""
    out = [f"{d}:{d}" for d in (cfg, data) if d]
    for src, _ in record.get("copies") or []:
        out.append(f"{src}:{src}:ro")
    for e in record["containers"]:
        out.append(f"{e['folder']}:{e['folder']}")
        for f in e["files"]:
            if not _under(f, e["folder"]):
                out.append(f"{f}:{f}:ro")
    return list(dict.fromkeys(out))


# Running it ----------------------------------------------------------------------------------------------------

_lock = threading.Lock()
_job = {}
_tasks = tasklist.Tasks()


def job():
    with _lock:
        return dict(_job) | (_tasks.public() if _job else {})


def _run(kind, host_stack, script, binds, after=None, tasks=None, progress=None):
    """Runs the helper's script in the background. `tasks` (tasklist.Tasks) is what the dialog lists; `progress` is
    where Starboard reads the step the script has started (data/stack/takeover-progress), read every two seconds
    while it runs and never afterwards."""
    global _tasks
    with _lock:
        if _job and not _job.get("finished"):
            raise ValueError("Starboard is already changing your apps. Wait until it finishes")
        _job.clear()
        _job.update(kind=kind, started=time.time(), finished=False, ok=None, log="", notes=[])
        _tasks = tasks or tasklist.Tasks()
    if progress:
        try:
            os.remove(progress)
        except OSError:
            pass
    running = threading.Event()

    def watch():
        while not running.wait(2.0):
            _read_progress(progress)

    def go():
        ok, log = False, ""
        if progress:
            threading.Thread(target=watch, name=f"takeover-{kind}-progress", daemon=True).start()
        try:
            try:
                containers.docker("POST", f"/images/create?fromImage={urllib.parse.quote(containers.HELPER_IMAGE, safe='')}",
                                  raw=True, timeout=300)
            except containers.DockerError:
                pass
            code, log = containers._helper(host_stack, script, extra_binds=binds)
            ok = code == 0
        except containers.DockerError as e:
            log = str(e)
        running.set()
        if progress:
            _read_progress(progress)
        script_ids = [t["id"] for t in _tasks.public()["tasks"] if t["id"] not in AFTER_TASKS]
        if ok:
            for task_id in script_ids:
                if _tasks.state(task_id) in ("waiting", "working"):
                    _tasks.done(task_id)
        else:
            _tasks.stop_rest("Not started, because the step before it did not finish")
        notes = []
        if after:
            try:
                notes = after(ok) or []
            except Exception as e:  # noqa: BLE001  the follow-up never hides the result of the change itself
                notes = [f"The follow-up did not finish: {e}"]
        _tasks.finish_all()
        with _lock:
            _job.update(ok=ok, log=log[-6000:], notes=notes, finished=True, ended=time.time())
    threading.Thread(target=go, name=f"takeover-{kind}", daemon=True).start()
    return job()


AFTER_TASKS = ("usenet", "reelix", "dashboard")  # done by Starboard after the script, not by the script


def _read_progress(path):
    try:
        with open(path, encoding="utf-8") as f:
            tasklist.from_progress(_tasks, f.read(20000).splitlines())
    except OSError:
        pass


def start(data_dir, host_stack, p, after=None, stamp=None):
    """Takes over the apps in plan `p`: the rollback point, Starboard's set-up files, then the switch in the helper.
    If the switch fails before the old containers are removed, they start again and Starboard's files go back."""
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    tasks = tasklist.Tasks(takeover_tasks(p))
    tasks.start("record")
    record = make_record(data_dir, p, stamp)
    built = stack.build(p["choice"])
    own = stack.own_services(data_dir)
    if own:
        built = {**built, "compose": built["compose"].rstrip() + "\n" + "".join(own)}
    stack.write(data_dir, built)
    stack.save_keep(data_dir, p["choice"]["keep"])
    tasks.done("record")

    def finish(ok):
        if not ok:
            _restore_files(data_dir, record)
        return after(ok, tasks) if after else []
    c = p["choice"]
    progress = os.path.join(host_stack, PROGRESS)
    script = takeover_script(record, host_stack, c["config_dir"], c["data_dir"], built.get("folders") or [], (c["puid"], c["pgid"]),
                             progress=progress)
    return _run("takeover", host_stack, script, binds_for(record, c["config_dir"], c["data_dir"]), finish, tasks,
                os.path.join(stack.folder(data_dir), PROGRESS))


def _restore_files(data_dir, record):
    before = os.path.join(record_folder(data_dir), "stack-before")
    for name in ("compose.yaml", ".env", stack.KEEP_FILE):
        target = os.path.join(stack.folder(data_dir), name)
        if os.path.exists(os.path.join(before, name)):
            shutil.copy2(os.path.join(before, name), target)
        elif name != "compose.yaml" or not record.get("had_stack"):
            try:
                os.remove(target)
            except FileNotFoundError:
                pass
    # A failed takeover has no rollback point to keep: the old apps run again as they were.
    folder_ = record_folder(data_dir)
    shutil.move(folder_, folder_ + f"-failed-{record['stamp']}")


def roll_back(data_dir, host_stack, after=None):
    record = read_record(data_dir)
    if not record:
        raise ValueError("There is nothing to roll back")
    progress = os.path.join(host_stack, PROGRESS)
    return _run("rollback", host_stack, rollback_script(record, host_stack, progress), binds_for(record, None), after,
                tasklist.Tasks(rollback_tasks(record)), os.path.join(stack.folder(data_dir), PROGRESS))


def clear(data_dir):
    """Keeps the takeover for good: the rollback point is moved aside (nothing is deleted). The old settings folders
    and rollback images stay until the person removes them."""
    record = read_record(data_dir)
    if not record:
        raise ValueError("There is nothing to clear")
    folder_ = record_folder(data_dir)
    shutil.move(folder_, folder_ + f"-kept-{time.strftime('%Y%m%d-%H%M%S')}")
    return record


# Clearing away the apps Reelix replaced, once the takeover is kept (DASH-191) ------------------------------------

# Apps Reelix does the work of: offered to stop and remove once the person chose Keep it.
CLEAR_AWAY = ("prowlarr", "radarr", "sonarr", "bookshelf", "lidarr", "kapowarr", "profilarr", "decluttarr", "unpackerr")
HOLDING = "starboard-holding"  # beside the old settings folders; the person empties it (never deleted for good here)
CLEARED = "cleared.json"  # in data/stack: what was put in the holding folder, and when
_TOP = ("/", "/home", "/mnt", "/srv", "/opt", "/var", "/root", "/data")


def kept_records(data_dir):
    """The records of takeovers the person kept (Keep it moves the rollback point to takeover-kept-<time>)."""
    base = stack.folder(data_dir)
    out = []
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return out
    for name in names:
        if name.startswith(RECORD + "-kept-"):
            try:
                with open(os.path.join(base, name, "record.json"), encoding="utf-8") as f:
                    rec = json.load(f)
                if isinstance(rec, dict) and rec.get("containers"):
                    out.append(rec)
            except (OSError, ValueError):
                continue
    return out


def cleared(data_dir):
    try:
        with open(os.path.join(stack.folder(data_dir), CLEARED), encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, list) else []
    except (OSError, ValueError):
        return []


def holding_for(folder, name, stamp):
    """Where a settings folder goes: a starboard-holding folder beside the apps' settings folders, so the move stays
    on the same drive and is instant. None when the folder is too near the top of the computer to move safely."""
    folder = folder.rstrip("/")
    parent = os.path.dirname(folder)
    if os.path.basename(folder) in ("config", "data") and os.path.dirname(parent) not in _TOP:
        parent = os.path.dirname(parent)
    if parent in _TOP or not _SAFE_HOST_PATH.match(folder):
        return None
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{name}-{os.path.basename(folder)}" if os.path.basename(folder) in ("config", "data") else os.path.basename(folder))
    return f"{parent}/{HOLDING}/{stamp}/{label}"


def leftovers(data_dir, inspect=None):
    """What can be cleared away now: None until a takeover was kept; then the apps Reelix replaced that still have a
    container here (running or stopped, outside Starboard's own apps) or a settings folder Starboard recorded and
    has not put aside yet. Each with its name, app, whether it runs, and its settings folders."""
    kept = kept_records(data_dir)
    if not kept:
        return None
    inspect = inspect or _inspect
    done = {c.get("from") for c in cleared(data_dir)}
    out, seen = [], set()
    try:
        here = found() if containers.available() else []
    except containers.DockerError:
        here = []
    for c in here:
        if c["key"] in CLEAR_AWAY:
            try:
                folders = settings_folders(inspect(c["name"]))
            except containers.DockerError:
                folders = []
            out.append({"name": c["name"], "app": stack.APPS[c["key"]]["name"], "running": c["running"], "container": True,
                        "settings": [f for f in folders if f not in done]})
            seen.add(c["name"])
    for rec in kept:
        for e in rec["containers"]:
            folders = [f for f in e.get("settings") or [] if f not in done]
            if e.get("key") in CLEAR_AWAY and e["name"] not in seen and folders:
                out.append({"name": e["name"], "app": stack.APPS[e["key"]]["name"], "running": False, "container": False,
                            "settings": folders})
                seen.add(e["name"])
    return out


def clear_tasks(items):
    return [(f"app-{i}", f"Clear away {it['app']}") for i, it in enumerate(items)]


def clear_script(items, stamp, progress=None):
    """Stops and removes each container, then moves its settings folders into the holding folder. One app that
    cannot be cleared away does not stop the others; its line in the progress file says so."""
    q = containers._quote
    lines = ["set -u"]
    for i, it in enumerate(items):
        tid = f"app-{i}"
        lines.append(_mark(progress, tid))
        steps = []
        if it.get("container"):
            steps.append(f"docker stop -t 30 {q(it['name'])} >/dev/null 2>&1; docker rm {q(it['name'])} >/dev/null")
        for folder in it.get("settings") or []:
            dest = holding_for(folder, it["name"], stamp)
            if not dest:
                continue
            steps.append(f"{{ [ ! -e {q(folder)} ] || {{ mkdir -p {q(os.path.dirname(dest))} && mv {q(folder)} {q(dest)}; }}; }}")
        if steps:
            fail = _mark(progress, f"{tid} failed")
            lines.append(f"{{ {' && '.join(steps)}; }} || {{ echo {q('Could not clear away ' + it['app'])}; {fail}; }}")
    return "\n".join(lines)


def clear_away(data_dir, host_stack, names, after=None, stamp=None):
    """Clears away the chosen leftovers (container names) in the helper. Returns the job."""
    items = [it for it in leftovers(data_dir) or [] if it["name"] in set(names)]
    if not items:
        raise ValueError("Choose at least one app to clear away")
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    binds = []
    for it in items:
        for folder in it["settings"]:
            dest = holding_for(folder, it["name"], stamp)
            if dest:
                parent = dest.split(f"/{HOLDING}/")[0]
                binds.append(f"{parent}:{parent}")
    binds = list(dict.fromkeys(binds))
    tasks = tasklist.Tasks(clear_tasks(items) + [("dashboard", "Update your dashboard")])
    progress = os.path.join(host_stack, PROGRESS)

    def finish(ok):
        moved = cleared(data_dir)
        for i, it in enumerate(items):
            if tasks.state(f"app-{i}") == "failed":
                continue
            for folder in it["settings"]:
                dest = holding_for(folder, it["name"], stamp)
                if dest:
                    moved.append({"name": it["name"], "app": it["app"], "from": folder, "to": dest, "at": time.time()})
        with open(os.path.join(stack.folder(data_dir), CLEARED), "w", encoding="utf-8") as f:
            json.dump(moved, f, indent=1)
        return after(ok, items, tasks) if after else []
    return _run("clear", host_stack, clear_script(items, stamp, progress), binds, finish, tasks,
                os.path.join(stack.folder(data_dir), PROGRESS))
