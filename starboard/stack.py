"""Install apps: the first-install guide that sets up a media server stack, in groups you tick.

Only when asked, and nothing runs in the background. Starboard writes a Compose file and a .env file into
data/stack, shows both, and starts them only when you press Start (with Docker access and your password).
Without Docker access it gives you the one command to run yourself. Images come from this list only; the
folders you choose are checked, and ports already in use move to the next free one.

Each app: name, groups, image, ports ("host:inside", host ports move when taken), volumes, environment, and
optional extras: "later" (needs its own settings file first, so it is left out of `up -d` until you add it),
"vpn" (runs through Gluetun when the VPN group is on), "db" (a database that comes with it), "notes".
"""

import json
import os
import re
import secrets
import socket
import threading
import time

from . import containers

GROUPS = [
    # key, name, what it is for, kind ("media", "core" or "extras"), on by default
    ("movies", "Movies", "Find, download and sort films", "media", True),
    ("tv", "TV", "Find, download and sort series", "media", True),
    ("music", "Music", "Albums and artists", "media", False),
    ("ebooks", "Ebooks", "Books to read", "media", False),
    ("audiobooks", "Audiobooks", "Books to listen to, with progress on every device", "media", False),
    ("radio", "Radio", "Radio shows and podcasts, followed in Reelix and played in Audiobookshelf", "media", False),
    ("comics", "Comics", "Comics and graphic novels", "media", False),
    ("watching", "Watching", "Play everything, with friends invited", "core", True),
    ("downloads", "Downloads", "The apps Reelix sends downloads to", "core", True),
    ("vpn", "VPN", "Send downloads through a VPN", "core", False),
    ("subtitles", "Subtitles", "Subtitles for films and series", "core", False),
    ("tidy", "Tidy-up", "Clear stuck downloads and old media, sync quality settings", "extras", False),
    ("livetv", "Live TV", "Free TV channels and guides", "extras", False),
    ("logs", "Logs", "Read every container's log in the browser", "extras", False),
    ("transcoding", "Transcoding", "Convert the library to save space", "extras", False),
]

LSIO = {"PUID": "${PUID}", "PGID": "${PGID}", "TZ": "${TZ}"}
CFG = "${CONFIG_DIR}"
DATA = "${DATA_DIR}"

# Storyarr is pinned to a version, so System, Apps, Updates offers each newer one (with a database backup first).
# STARBOARD_STORYARR_IMAGE chooses another image, or none to leave Storyarr out.
STORYARR_IMAGE = "ghcr.io/themightytrex/storyarr:v0.6.1"

# Reelix Lite (the fork's lite image of Reelix) is the one media manager for new installs (owner, 6 November 2026):
# films, series, books, audiobooks, music and radio, with its own sites to search and requests. STARBOARD_REELIX_IMAGE
# chooses another image (such as upstream's ghcr.io/mvanhare/reelix:latest).
REELIX_IMAGE = "ghcr.io/themightytrex/reelix:lite"
# The full version of Reelix adds YouTube and Spotify downloads (yt-dlp, Deno and Debian's full FFmpeg, about 600 MB
# more on disk). Lite is the default (owner, 6 November 2026); the full version is a choice, and Settings, Reelix
# switches between the two either way. The fork's full image comes first: it is built from the fork's main branch, so
# it has the same fixes as Lite (7 November 2026). Upstream's own image is the fallback. STARBOARD_REELIX_FULL_IMAGE
# chooses another.
REELIX_FULL_IMAGES = ["ghcr.io/themightytrex/reelix:full", "ghcr.io/demonzoned/reelix:latest"]
REELIX_EDITIONS = {
    "lite": {"name": "Reelix", "extra_mb": 0,
             "about": "Films, series, books, audiobooks, music and radio. The smaller download, for most servers."},
    "full": {"name": "Reelix with YouTube and Spotify downloads", "extra_mb": 600,
             "about": "Everything in Reelix, and downloads straight from YouTube and Spotify. About 600 MB more disk."},
}
_pullable = {}
# The apps Reelix replaces. They are no longer offered for new installs, but a stack written with them before still
# builds, so nothing someone already runs breaks.
REPLACED_BY_REELIX = {"radarr", "sonarr", "lidarr", "bookshelf", "prowlarr", "seerr", "profilarr", "decluttarr", "unpackerr",
                      "janitorr"}
APPS = {
    "reelix": {"name": "Reelix", "groups": ["movies", "tv", "music", "ebooks", "audiobooks", "radio"],
               "image": os.environ.get("STARBOARD_REELIX_IMAGE") or REELIX_IMAGE, "ports": ["7700:7700"],
               "volumes": [f"{CFG}/reelix:/config", f"{DATA}:/data"], "env": {**LSIO, "UMASK": "002"}, "memory": 60,
               "notes": "One app for films, series, books, audiobooks, music and radio, with requests and its own sites to search."},
    "radarr": {"name": "Radarr", "groups": ["movies"], "image": "lscr.io/linuxserver/radarr:latest",
               "ports": ["7878:7878"], "volumes": [f"{CFG}/radarr:/config", f"{DATA}:/data"], "env": LSIO, "memory": 200},
    "sonarr": {"name": "Sonarr", "groups": ["tv"], "image": "lscr.io/linuxserver/sonarr:latest",
               "ports": ["8989:8989"], "volumes": [f"{CFG}/sonarr:/config", f"{DATA}:/data"], "env": LSIO, "memory": 200},
    "lidarr": {"name": "Lidarr", "groups": ["music"], "image": "lscr.io/linuxserver/lidarr:latest",
               "ports": ["8686:8686"], "volumes": [f"{CFG}/lidarr:/config", f"{DATA}:/data"], "env": LSIO, "memory": 200},
    "bookshelf": {"name": "Bookshelf", "groups": ["ebooks"], "image": "ghcr.io/pennydreadful/bookshelf:softcover",
                  "ports": ["8787:8787"], "volumes": [f"{CFG}/bookshelf:/config", f"{DATA}:/data"], "env": LSIO, "memory": 200,
                  "notes": "A maintained version of Readarr."},
    "storyarr": {"name": "Storyarr", "groups": ["ebooks", "audiobooks"], "image": os.environ.get("STARBOARD_STORYARR_IMAGE") or STORYARR_IMAGE,
                 "ports": ["8000:8000"], "volumes": [f"{CFG}/storyarr:/config", f"{DATA}:/data"], "memory": 250,
                 "env": {**LSIO, "DB_HOST": "storyarr-db", "DB_PORT": "5432", "DB_NAME": "storyarr", "DB_USER": "storyarr",
                         "DB_PASSWORD": "${STORYARR_DB_PASSWORD}"},
                 "db": {"service": "storyarr-db", "image": "postgres:18", "volume": f"{CFG}/storyarr-db:/var/lib/postgresql",
                        "env": {"POSTGRES_DB": "storyarr", "POSTGRES_USER": "storyarr", "POSTGRES_PASSWORD": "${STORYARR_DB_PASSWORD}"},
                        "secret": "STORYARR_DB_PASSWORD"},
                 "default": False, "notes": "Ebooks and audiobooks in one place, with series and reading lists."},
    "audiobookshelf": {"name": "Audiobookshelf", "groups": ["audiobooks", "radio"], "image": "ghcr.io/advplyr/audiobookshelf:latest",
                       "ports": ["13378:80"], "env": {"TZ": "${TZ}"}, "memory": 150,
                       "volumes": [f"{CFG}/audiobookshelf/config:/config", f"{CFG}/audiobookshelf/metadata:/metadata", f"{DATA}/media:/media"]},
    "kapowarr": {"name": "Kapowarr", "groups": ["comics"], "image": "mrcas/kapowarr:latest", "ports": ["5656:5656"], "memory": 100,
                 "volumes": [f"{CFG}/kapowarr:/app/db", f"{DATA}/downloads/comics:/app/temp_downloads", f"{DATA}/media/comics:/comics-1"]},
    "jellyfin": {"name": "Jellyfin", "groups": ["watching"], "image": "lscr.io/linuxserver/jellyfin:latest",
                 "ports": ["8096:8096"], "volumes": [f"{CFG}/jellyfin:/config", f"{DATA}/media:/data/media"], "env": LSIO, "memory": 400},
    "seerr": {"name": "Seerr", "groups": ["watching"], "image": "ghcr.io/seerr-team/seerr:latest", "ports": ["5055:5055"],
              "volumes": [f"{CFG}/seerr:/app/config"], "env": {"TZ": "${TZ}"}, "memory": 200,
              "notes": "People ask for films and series; it sends them to Radarr and Sonarr."},
    "jellystat": {"name": "Jellystat", "groups": ["watching"], "image": "cyfershepard/jellystat:latest", "ports": ["3000:3000"],
                  "env": {"POSTGRES_USER": "jellystat", "POSTGRES_PASSWORD": "${JELLYSTAT_DB_PASSWORD}", "POSTGRES_IP": "jellystat-db",
                          "POSTGRES_PORT": "5432", "JWT_SECRET": "${JELLYSTAT_JWT_SECRET}", "TZ": "${TZ}"},
                  "volumes": [f"{CFG}/jellystat/backup:/app/backend/backup-data"], "memory": 200, "default": False,
                  "db": {"service": "jellystat-db", "image": "postgres:15.2", "volume": f"{CFG}/jellystat-db:/var/lib/postgresql/data",
                         "env": {"POSTGRES_DB": "jfstat", "POSTGRES_USER": "jellystat", "POSTGRES_PASSWORD": "${JELLYSTAT_DB_PASSWORD}"},
                         "secret": "JELLYSTAT_DB_PASSWORD", "secret2": "JELLYSTAT_JWT_SECRET"}},
    "wizarr": {"name": "Wizarr", "groups": ["watching"], "image": "ghcr.io/wizarrrr/wizarr:latest", "ports": ["5690:5690"],
               "volumes": [f"{CFG}/wizarr:/data/database"], "env": {"TZ": "${TZ}"}, "memory": 100, "default": False,
               "notes": "Invite friends to Jellyfin with a link."},
    "qbittorrent": {"name": "qBittorrent", "groups": ["downloads"], "image": "lscr.io/linuxserver/qbittorrent:latest",
                    "ports": ["8080:8080", "6881:6881", "6881:6881/udp"], "volumes": [f"{CFG}/qbittorrent:/config", f"{DATA}:/data"],
                    "env": {**LSIO, "WEBUI_PORT": "8080"}, "vpn": True, "memory": 150},
    # NZBGet is the default Usenet app (owner, 7 November 2026): written in C++, it uses far less memory and processor
    # than SABnzbd. Its sign-in is made up here (NZBGET_PASS in .env), so Starboard and Reelix can use it.
    "nzbget": {"name": "NZBGet", "groups": ["downloads"], "image": "lscr.io/linuxserver/nzbget:latest", "ports": ["6789:6789"],
               "volumes": [f"{CFG}/nzbget:/config", f"{DATA}:/data"],
               "env": {**LSIO, "NZBGET_USER": "starboard", "NZBGET_PASS": "${NZBGET_PASS}"}, "secrets": ["NZBGET_PASS"],
               "vpn": True, "memory": 40, "notes": "For Usenet, which needs a paid provider. Lighter than SABnzbd."},
    # SABnzbd listens on 8085, not its usual 8080: through the VPN it shares Gluetun's network with qBittorrent, which
    # has 8080. Its first settings file (sabnzbd_seed) sets that, the names Reelix reaches it by, the media folder
    # and an API key Starboard made up, so Starboard and Reelix can use it without reading its files.
    "sabnzbd": {"name": "SABnzbd", "groups": ["downloads"], "image": "lscr.io/linuxserver/sabnzbd:latest", "ports": ["8085:8085"],
                "volumes": [f"{CFG}/sabnzbd:/config", f"{DATA}:/data"], "env": LSIO, "vpn": True, "memory": 150, "default": False,
                "secrets": ["SABNZBD_API_KEY"],
                "notes": "For Usenet, in place of NZBGet. A choice in Full install and Everything."},
    "prowlarr": {"name": "Prowlarr", "groups": ["downloads"], "image": "lscr.io/linuxserver/prowlarr:latest", "ports": ["9696:9696"],
                 "volumes": [f"{CFG}/prowlarr:/config"], "env": LSIO, "vpn": True, "memory": 150,
                 "notes": "One list of sites to search, shared with every app."},
    "flaresolverr": {"name": "FlareSolverr", "groups": ["downloads"], "image": "ghcr.io/flaresolverr/flaresolverr:latest",
                     "ports": ["8191:8191"], "env": {"TZ": "${TZ}"}, "vpn": True, "memory": 300,
                     "notes": "Gets past browser checks on some search sites."},
    "unpackerr": {"name": "Unpackerr", "groups": ["downloads"], "image": "ghcr.io/hotio/unpackerr:latest",
                  "volumes": [f"{CFG}/unpackerr:/config", f"{DATA}:/data"], "env": LSIO, "memory": 50, "default": False, "later": True,
                  "notes": "Unpacks downloads. Needs the API keys of your apps in its settings file first."},
    "gluetun": {"name": "Gluetun", "groups": ["vpn"], "image": "qmcgaw/gluetun:v3", "memory": 50, "gluetun": True,
                "env": {"TZ": "${TZ}", "VPN_SERVICE_PROVIDER": "${VPN_SERVICE_PROVIDER}", "VPN_TYPE": "${VPN_TYPE}",
                        "WIREGUARD_PRIVATE_KEY": "${WIREGUARD_PRIVATE_KEY}", "WIREGUARD_ADDRESSES": "${WIREGUARD_ADDRESSES}",
                        "OPENVPN_USER": "${OPENVPN_USER}", "OPENVPN_PASSWORD": "${OPENVPN_PASSWORD}", "SERVER_COUNTRIES": "${SERVER_COUNTRIES}"},
                "volumes": [f"{CFG}/gluetun:/gluetun"], "notes": "Your VPN details go in the .env file, never in Starboard's settings."},
    "bazarr": {"name": "Bazarr", "groups": ["subtitles"], "image": "lscr.io/linuxserver/bazarr:latest", "ports": ["6767:6767"],
               "volumes": [f"{CFG}/bazarr:/config", f"{DATA}/media:/data/media"], "env": LSIO, "memory": 150},
    "decluttarr": {"name": "Decluttarr", "groups": ["tidy"], "image": "ghcr.io/manimatter/decluttarr:latest", "memory": 50,
                   "volumes": [f"{CFG}/decluttarr:/app/config"], "env": {"TZ": "${TZ}"}, "later": True,
                   "notes": "Removes stuck downloads. Needs a settings file with your apps' API keys first."},
    "profilarr": {"name": "Profilarr", "groups": ["tidy"], "image": "santiagosayshey/profilarr:latest", "ports": ["6868:6868"],
                  "volumes": [f"{CFG}/profilarr:/config"], "env": {"TZ": "${TZ}"}, "memory": 100,
                  "notes": "Shares quality settings between Radarr and Sonarr."},
    "janitorr": {"name": "Janitorr", "groups": ["tidy"], "image": "ghcr.io/schaka/janitorr:jvm-stable", "memory": 250, "later": True,
                 "volumes": [f"{CFG}/janitorr:/config", f"{DATA}:/data"], "default": False,
                 "notes": "Deletes media nobody watches. Needs application.yml in its settings folder first."},
    "dispatcharr": {"name": "Dispatcharr", "groups": ["livetv"], "image": "ghcr.io/dispatcharr/dispatcharr:latest",
                    "ports": ["9191:9191"], "volumes": [f"{CFG}/dispatcharr:/data"], "env": {"TZ": "${TZ}"}, "memory": 300},
    "dozzle": {"name": "Dozzle", "groups": ["logs"], "image": "amir20/dozzle:latest", "ports": ["9999:8080"], "memory": 30,
               "volumes": ["/var/run/docker.sock:/var/run/docker.sock:ro"], "notes": "Reads Docker's logs, so it sees every container."},
    "tdarr": {"name": "Tdarr", "groups": ["transcoding"], "image": "ghcr.io/haveagitgat/tdarr:latest", "ports": ["8265:8265", "8266:8266"],
              "volumes": [f"{CFG}/tdarr/server:/app/server", f"{CFG}/tdarr/configs:/app/configs", f"{CFG}/tdarr/logs:/app/logs",
                          f"{DATA}/media:/media", f"{CFG}/tdarr/cache:/temp"],
              "env": {**LSIO, "serverIP": "0.0.0.0", "serverPort": "8266", "webUIPort": "8265", "internalNode": "true", "nodeName": "starboard"},  # Tdarr's own setting inside its container  # nosec B104
              "memory": 500, "notes": "Uses a lot of processor time while it converts."},
}

# Folders made inside the data folder, so downloads and the library share one disk and moves are instant.
DATA_FOLDERS = {"movies": ["media/movies"], "tv": ["media/tv"], "music": ["media/music"], "ebooks": ["media/books"],
                "audiobooks": ["media/audiobooks"], "radio": ["media/radio"], "comics": ["media/comics", "downloads/comics"],
                "downloads": ["downloads/torrents", "downloads/usenet"]}

PROJECT = "media-stack"
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9._/-]{1,200}$")
_SYSTEM = ("/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/root", "/run", "/sbin", "/sys", "/usr", "/var/run", "/var/lib/docker",
           "/var/spool")
# Folders that hold others: fine to put media under, never to use (or hand to an app's user) themselves.
_TOP = ("/home", "/var", "/var/lib", "/opt", "/srv", "/mnt", "/media", "/tmp")  # nosec B108: folders refused, not used


def clean_folder(path, what):
    path = str(path or "").strip().rstrip("/")
    if not _SAFE_PATH.match(path) or "/../" in path + "/" or "/./" in path + "/" or "//" in path:
        raise ValueError(f"The {what} must be a full path such as /srv/media, with letters, numbers, dots, dashes and underscores")
    if path == "" or path in _TOP or any(path == s or path.startswith(s + "/") for s in _SYSTEM):
        raise ValueError(f"The {what} cannot be a system folder")
    if re.match(r"^/home/[^/]+$", path):  # a home folder itself: its owner's files, keys and settings
        raise ValueError(f"The {what} cannot be a home folder itself; use a folder inside it, such as {path}/media")
    return path


def _port_free(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) != 0


def defaults_for(app):
    return app.get("default", True)


def existing_media():
    """Host folders other containers already use for media or downloads (with Docker access): offered as the
    data folder, so new apps use your media where it is. Nothing is moved."""
    if not containers.available():
        return []
    found = {}
    try:
        for c in containers.docker("GET", "/containers/json?all=1"):
            name = c["Names"][0].lstrip("/")
            if (c.get("Labels") or {}).get("com.docker.compose.service") == "starboard":
                continue
            for m in c.get("Mounts") or []:
                src, dst = m.get("Source", ""), m.get("Destination", "")
                if m.get("Type") != "bind" or not _SAFE_PATH.match(src or ""):
                    continue
                if re.search(r"/(config|database|db|appdata|metadata)(/|$)", src, re.I):
                    continue  # an app's own settings, not media
                if re.search(r"^/(data|media|movies|tv|music|books|audiobooks|comics|downloads|library)(/|$)", dst):
                    found.setdefault(src, set()).add(name)
    except containers.DockerError:
        return []
    # Outermost folders only: a folder inside another one adds its apps to the outer one.
    outer = {}
    for path in sorted(found, key=len):
        top = next((o for o in outer if path.startswith(o + "/")), None)
        outer.setdefault(top or path, set()).update(found[path])
    return [{"path": p, "used_by": sorted(n)} for p, n in sorted(outer.items())]


def offered(replaced=False):
    """Apps with an image to install. STARBOARD_STORYARR_IMAGE=none leaves Storyarr out. The apps Reelix replaces are
    left out unless `replaced` (writing or checking a stack that has them already)."""
    return {k: a for k, a in APPS.items() if a["image"] and a["image"] != "none" and (replaced or k not in REPLACED_BY_REELIX)}


# What each app needs to work. A tuple means "one of these"; the first is added when none is chosen. A database that
# comes with an app (APPS[...]["db"]) is part of that app, so it is not listed. Both set-ups add these for you.
NEEDS = {
    "reelix": [("qbittorrent", "nzbget", "sabnzbd")],
    "kapowarr": [("qbittorrent", "nzbget", "sabnzbd")],
    "storyarr": [("qbittorrent", "nzbget", "sabnzbd")],
    "gluetun": [("qbittorrent", "nzbget", "sabnzbd")],
    "flaresolverr": ["reelix"],
    "bazarr": ["reelix"],
    "jellystat": ["jellyfin"],
    "wizarr": ["jellyfin"],
    "dispatcharr": ["jellyfin"],
}

# The three installs both set-ups offer first (owner, 7 November 2026, from the install choices page): Basics is
# built on Reelix Lite, Full install on the full Reelix, and All is everything. Disk health is the installer's own
# check, not an app. "Choose myself" keeps the groups and app-by-app ticks. NZBGet is the Usenet app in all three;
# Full install and Everything may use SABnzbd instead (USENET_APPS).
INSTALLS = {
    "basics": {"name": "Basics", "reelix_edition": "lite", "disk_health": False,
               "about": "Reelix Lite, Jellyfin, Audiobookshelf, subtitles, and torrent and Usenet downloads through a VPN.",
               "apps": ["reelix", "qbittorrent", "jellyfin", "audiobookshelf", "bazarr", "gluetun", "nzbget"],
               "usenet_choice": False},
    "full": {"name": "Full install", "reelix_edition": "full", "disk_health": True,
             "about": "Everything in Basics with the full Reelix (YouTube and Spotify downloads), plus disk health, "
                      "watch statistics, invites, live TV, logs, FlareSolverr and Tdarr.",
             "apps": ["reelix", "qbittorrent", "jellyfin", "audiobookshelf", "bazarr", "gluetun", "nzbget",
                      "flaresolverr", "jellystat", "wizarr", "dozzle", "dispatcharr", "tdarr"], "usenet_choice": True},
    "all": {"name": "Everything", "reelix_edition": "full", "disk_health": True,
            "about": "Every app Starboard offers, Storyarr and Kapowarr included.", "apps": None, "usenet_choice": True},
}
USENET_APPS = ("nzbget", "sabnzbd")


def with_needs(keys):
    """`keys` and everything they need (NEEDS), in catalogue order. Returns (keys, added)."""
    chosen = list(dict.fromkeys(keys))
    added = []
    i = 0
    while i < len(chosen):
        for need in NEEDS.get(chosen[i], []):
            options = need if isinstance(need, tuple) else (need,)
            if not any(o in chosen for o in options):
                chosen.append(options[0])
                added.append(options[0])
        i += 1
    order = list(APPS)
    return sorted(chosen, key=lambda k: order.index(k) if k in order else len(order)), added


def install_choice(key, installed_keys=(), check=None, usenet="nzbget"):
    """The apps, groups and answers for one of INSTALLS. Apps already running are left out. The full Reelix falls back
    to Lite when it cannot be downloaded, and says so. `usenet` picks NZBGet or SABnzbd where the install allows it."""
    if key not in INSTALLS:
        raise ValueError("Choose Basics, Full install or Everything")
    spec = INSTALLS[key]
    if usenet not in USENET_APPS or not spec["usenet_choice"]:
        usenet = "nzbget"
    apps = [k for k in (spec["apps"] or offered()) if k in offered()]
    if any(k in USENET_APPS for k in apps):  # one Usenet app: the chosen one
        apps = [k for k in apps if k not in USENET_APPS] + [usenet]
    apps, _ = with_needs(apps)
    edition, note = spec["reelix_edition"], ""
    if edition == "full":
        try:
            reelix_image("full", check)
        except ValueError:
            edition, note = "lite", "Reelix with YouTube and Spotify downloads cannot be downloaded at the moment, so this installs Reelix Lite. Switch later in Settings, Reelix."
    keys = [k for k in apps if k not in installed_keys]
    groups = sorted({g for k in keys for g in APPS[k]["groups"]})
    return {"key": key, "name": spec["name"], "about": spec["about"], "apps": keys, "groups": groups,
            "usenet": usenet, "usenet_choice": spec["usenet_choice"],
            "reelix_edition": edition, "disk_health": spec["disk_health"], "note": note,
            "memory": sum(APPS[k].get("memory", 100) for k in keys)}


def catalogue(installed_keys):
    """Groups and apps for the guide; apps found running are marked and left unticked."""
    apps = []
    for key, a in offered().items():
        ports = []
        for p in a.get("ports", []):
            host = int(p.split(":")[0])
            ports.append({"port": host, "free": key in installed_keys or _port_free(host)})
        apps.append({"key": key, "name": a["name"], "groups": a["groups"], "image": a["image"], "notes": a.get("notes", ""),
                     "default": defaults_for(a), "later": bool(a.get("later")), "memory": a.get("memory", 100),
                     "installed": key in installed_keys, "ports": ports})
    used = {g for a in apps for g in a["groups"]}  # a group with no app left (Tidy-up, now in Reelix) is not shown
    return {"groups": [{"key": k, "name": n, "about": t, "kind": kind, "default": d} for k, n, t, kind, d in GROUPS if k in used],
            "apps": apps, "needs": {k: [list(n) if isinstance(n, tuple) else [n] for n in v] for k, v in NEEDS.items()},
            "installs": [{"key": k, "name": v["name"], "about": v["about"], "recommended": k == "basics",
                          "usenet_choice": v["usenet_choice"]} for k, v in INSTALLS.items()]}


def _yaml_value(v):
    v = str(v)
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def compose_ports(data_dir):
    """The host ports data/stack/compose.yaml already maps. Writing that file again treats them as free: they are
    Starboard's own apps, which keep their ports instead of moving to the next one up."""
    try:
        with open(os.path.join(folder(data_dir), "compose.yaml"), encoding="utf-8") as f:
            return sorted({int(m) for m in re.findall(r'(?m)^\s+- "(\d{2,5}):\d{2,5}(?:/udp)?"', f.read())})
    except OSError:
        return []


def _next_free(port, used, own=()):
    while port in used or (port not in own and not _port_free(port)):
        port += 1
    used.add(port)
    return port


def can_download(ref, check=None):
    """Whether an image can be downloaded without signing in (asked of its registry; remembered for an hour)."""
    seen = _pullable.get(ref)
    if seen and time.time() - seen[1] < 3600:
        return seen[0]
    try:
        (check or containers.remote)(ref)
        ok = True
    except Exception:  # noqa: BLE001  any registry, network or parsing failure means it cannot be downloaded now
        ok = False
    _pullable[ref] = (ok, time.time())
    return ok


def reelix_image(edition, check=None):
    """The image for "lite" or "full". The full one is the first of REELIX_FULL_IMAGES that can be downloaded."""
    if edition not in REELIX_EDITIONS:
        raise ValueError("Choose Reelix or Reelix with YouTube and Spotify downloads")
    if edition == "lite":
        return APPS["reelix"]["image"]
    own = os.environ.get("STARBOARD_REELIX_FULL_IMAGE")
    for ref in [own] if own else REELIX_FULL_IMAGES:
        if can_download(ref, check):
            return ref
    raise ValueError("Reelix with YouTube and Spotify downloads cannot be downloaded at the moment. Choose Reelix for "
                     "now: you can switch later in Settings, Reelix")


def reelix_editions(check=None):
    """Both versions for the set-ups and Settings, with whether each can be downloaded now."""
    out = []
    for key, e in REELIX_EDITIONS.items():
        try:
            reelix_image(key, check)
            available = True
        except ValueError:
            available = False
        out.append({"key": key, **e, "available": available, "recommended": key == "lite"})
    return out


def edition_of(image):
    """"lite" or "full" for a Reelix image, or None for an image Starboard does not know."""
    if not image:
        return None
    if image == APPS["reelix"]["image"] or image.endswith(":lite") or "-lite" in image.rsplit(":", 1)[-1]:
        return "lite"
    if image in REELIX_FULL_IMAGES or image == os.environ.get("STARBOARD_REELIX_FULL_IMAGE") or "/reelix:" in image:
        return "full"
    return None


_REELIX_IMAGE_LINE = re.compile(r"^(  reelix:\n    image: )(\S+)$", re.M)


def reelix_in_stack(data_dir):
    """The image Reelix runs from in data/stack/compose.yaml, or None when Starboard did not install it."""
    try:
        with open(os.path.join(folder(data_dir), "compose.yaml"), encoding="utf-8") as f:
            m = _REELIX_IMAGE_LINE.search(f.read())
    except OSError:
        return None
    return m.group(2) if m else None


def _version(ref, check=None):
    """The (major, minor, patch) an image's version label gives, or None."""
    try:
        v = str(((check or containers.remote)(ref) or {}).get("version") or "")
    except Exception:  # noqa: BLE001  unknown is fine: the switch then goes ahead
        return None
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", v)
    return tuple(int(x) for x in m.groups()) if m else None


def switch_reelix(data_dir, edition, check=None):
    """Changes Reelix's image in data/stack/compose.yaml to the other version; the old file is kept next to it.
    Reelix keeps its settings folder, so its library, users and settings stay. Returns (old image, new image)."""
    path = os.path.join(folder(data_dir), "compose.yaml")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = _REELIX_IMAGE_LINE.search(text)
    if not m:
        raise ValueError("Reelix was not installed by Install apps, so Starboard cannot change it. Change its image in "
                         "your own Compose file instead")
    new = reelix_image(edition, check)
    if m.group(2) == new:
        raise ValueError("Reelix is that version already")
    # Reelix updates its database when a newer version starts, and an older one cannot read it after that. So the
    # switch waits when the other version is behind (Lite follows each release within a day).
    have, want = _version(m.group(2), check), _version(new, check)
    if have and want and want < have:
        raise ValueError(f"{REELIX_EDITIONS[edition]['name']} is on {'.'.join(map(str, want))} and you run "
                         f"{'.'.join(map(str, have))}. It cannot go back to an older version, so try again once it has "
                         "caught up, usually within a day")
    os.replace(path, path + f".before-{time.strftime('%Y%m%d-%H%M%S')}")
    keep_recent_copies(path)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644), "w", encoding="utf-8") as f:
        f.write(text[:m.start(2)] + new + text[m.end(2):])
    return m.group(2), new


def build(choice):
    """The Compose file and .env for the ticked apps. choice: {apps, config_dir, data_dir, puid, pgid, tz, vpn,
    reelix_edition ("lite", the default, or "full")}.
    Returns {compose, env, env_shown, folders, moved, later}."""
    keys = [k for k in choice.get("apps", []) if k in offered(replaced=True)]
    keys, _ = with_needs(keys)  # what the chosen apps need comes too
    if not keys:
        raise ValueError("Tick at least one app to install")
    config_dir = clean_folder(choice.get("config_dir"), "settings folder")
    data_dir = clean_folder(choice.get("data_dir"), "media folder")
    puid, pgid = int(choice.get("puid", 1000)), int(choice.get("pgid", 1000))
    if not (0 < puid < 65536 and 0 < pgid < 65536):
        raise ValueError("The user and group numbers must be between 1 and 65535")
    tz = str(choice.get("tz") or "Etc/UTC")
    if not re.match(r"^[A-Za-z0-9_+/-]{1,40}$", tz):
        raise ValueError("Choose a time zone such as Europe/London")
    vpn = "gluetun" in keys
    vpn_choice = choice.get("vpn") or {}
    env = {"PUID": str(puid), "PGID": str(pgid), "TZ": tz, "CONFIG_DIR": config_dir, "DATA_DIR": data_dir}
    shown = dict(env)
    if vpn:
        provider = str(vpn_choice.get("provider", "")).strip().lower()
        kind = str(vpn_choice.get("type", "wireguard")).strip().lower()
        if not re.match(r"^[a-z0-9 _-]{2,40}$", provider) or kind not in ("wireguard", "openvpn"):
            raise ValueError("Choose your VPN provider, and WireGuard or OpenVPN")
        vals = {"VPN_SERVICE_PROVIDER": provider, "VPN_TYPE": kind, "SERVER_COUNTRIES": str(vpn_choice.get("countries", ""))}
        # Only the fields for the chosen connection go in, and those are needed.
        needed = {"wireguard": {"WIREGUARD_PRIVATE_KEY": "WireGuard private key", "WIREGUARD_ADDRESSES": "WireGuard address"},
                  "openvpn": {"OPENVPN_USER": "OpenVPN user name", "OPENVPN_PASSWORD": "OpenVPN password"}}[kind]
        for f, label in needed.items():
            vals[f] = str(vpn_choice.get(f.lower(), "")).strip()
            if not vals[f]:
                raise ValueError(f"Enter the {label} from your VPN provider")
        for k, v in vals.items():
            if "\n" in v or "\r" in v or "'" in v or len(v) > 300:
                raise ValueError("A VPN detail has a line break or a ' mark, or is too long. Add it to the .env file by hand instead")
            env[k] = v
            shown[k] = "(hidden)" if v and k in ("WIREGUARD_PRIVATE_KEY", "OPENVPN_PASSWORD") else v
    used, moved, later = set(), [], []
    own_ports = set(choice.get("own_ports") or [])  # set by Starboard itself from the file it is replacing
    lines = ["# Written by Starboard's Install apps guide. Change it by hand if you like; Starboard does not overwrite",
             "# it unless you run the guide again. Your settings and secrets are in .env next to it.", "services:"]
    vpn_ports = []
    for key in keys:
        a = APPS[key]
        through_vpn = vpn and a.get("vpn")
        image = reelix_image(choice.get("reelix_edition") or "lite") if key == "reelix" else a["image"]
        lines += [f"  {key}:", f"    image: {image}", f"    container_name: {key}", "    restart: unless-stopped"]
        if a.get("later"):
            lines.append('    profiles: ["later"]  # needs its own settings file first: docker compose --profile later up -d')
            later.append(a["name"])
        if a.get("gluetun"):
            lines += ["    cap_add:", "      - NET_ADMIN", "    devices:", "      - /dev/net/tun:/dev/net/tun"]
        ports = []
        for p in a.get("ports", []):
            host, inside = p.split(":", 1)
            new = _next_free(int(host), used, own_ports) if "/udp" not in inside else int(host)
            if new != int(host):
                moved.append(f"{a['name']} uses port {new}, because {host} is taken")
            ports.append(f"{new}:{inside}")
        depends = (["gluetun"] if through_vpn else []) + ([a["db"]["service"]] if a.get("db") else [])
        if depends:
            lines += ["    depends_on:"] + [f"      - {d}" for d in depends]
        if through_vpn:
            lines.append('    network_mode: "service:gluetun"')
            vpn_ports += ports
        elif ports:
            lines.append("    ports:")
            lines += [f"      - {_yaml_value(p)}" for p in ports]
        if a.get("env"):
            lines.append("    environment:")
            lines += [f"      {k}: {_yaml_value(v)}" for k, v in a["env"].items()]
        if a.get("volumes"):
            lines.append("    volumes:")
            lines += [f"      - {_yaml_value(v)}" for v in a["volumes"]]
        db = a.get("db")
        for name in a.get("secrets", []):  # made up once per write; the app reads it from .env
            env[name] = secrets.token_hex(16) if name.endswith("_API_KEY") else secrets.token_urlsafe(18)
            shown[name] = "(made up for you)"
        if db:
            for s in ("secret", "secret2"):
                if db.get(s):
                    env[db[s]] = secrets.token_urlsafe(24)
                    shown[db[s]] = "(made up for you)"
            lines += [f"  {db['service']}:", f"    image: {db['image']}", f"    container_name: {db['service']}",
                      "    restart: unless-stopped", "    environment:"]
            lines += [f"      {k}: {_yaml_value(v)}" for k, v in db["env"].items()]
            lines += ["    volumes:", f"      - {_yaml_value(db['volume'])}"]
    if vpn and vpn_ports:
        i = lines.index("  gluetun:") + 1
        while i < len(lines) and lines[i].startswith("    "):
            i += 1
        lines[i:i] = ["    ports:  # apps that go through the VPN are reached on Gluetun's ports"] + [f"      - {_yaml_value(p)}" for p in vpn_ports]
    folders = [f"{config_dir}/{k}" for k in keys] + [f"{data_dir}/{f}" for g in {g for k in keys for g in APPS[k]["groups"]}
                                                     for f in DATA_FOLDERS.get(g, [])]
    env_text = "# Starboard's Install apps guide. Keep this file private: it holds passwords.\n" + \
        "".join(f"{k}={_env_value(v)}\n" for k, v in env.items())
    hooks = {k: before_update(APPS[k]) for k in keys if APPS[k].get("db")}
    return {"compose": "\n".join(lines) + "\n", "env": env_text, "env_shown": shown, "folders": sorted(set(folders)),
            "moved": moved, "later": later, "hooks": hooks}


def before_update(app):
    """A database backup that System, Apps, Updates runs before it changes this app (containers.py runs
    starboard-before-update/<service>.sh from the Compose folder). If the backup fails or is empty, the update stops."""
    db = app["db"]
    name = db["env"]["POSTGRES_DB"]
    return ("#!/bin/sh\n# Written by Starboard's Install apps: backs up the database before System, Apps, Updates changes the app.\n"
            "set -eu\nset -o pipefail\nmkdir -p starboard-before-update/backups\n"
            f"out=starboard-before-update/backups/{name}-db-$(date +%Y-%m-%d-%H%M).sql.gz\n"
            f"docker exec {db['service']} pg_dump -U {db['env']['POSTGRES_USER']} {name} | gzip > \"$out\"\n"
            "test -s \"$out\"\necho \"Database backed up to $out\"\n")


def _env_value(v):
    v = str(v)
    return v if re.match(r"^[A-Za-z0-9_./:@,+-]*$", v) else f"'{v}'"  # single quotes: taken as written


# Writing and starting -----------------------------------------------------------------------------------------

_lock = threading.Lock()
_job = {}


def folder(data_dir):
    return os.path.join(data_dir, "stack")


def app_url(data_dir, service, inner):
    """The address on this computer of a service Install apps wrote, from the port data/stack/compose.yaml maps to
    its `inner` port (on the service, or on Gluetun when it runs through the VPN); None when there is none."""
    try:
        with open(os.path.join(folder(data_dir), "compose.yaml"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    for name in (service, "gluetun"):
        block = re.search(rf"(?ms)^  {name}:\n(.*?)(?=^  \S|\Z)", text)
        port = re.search(rf'"(\d{{2,5}}):{inner}"', block.group(1)) if block else None
        if port:
            return f"http://127.0.0.1:{port.group(1)}"
    return None


KEEP_BEFORE = 10  # older copies of the set-up files that Starboard keeps in data/stack


def keep_recent_copies(target, keep=KEEP_BEFORE):
    """Removes all but the newest `keep` "<file>.before-<date>" copies, so changes do not pile them up."""
    folder_, name = os.path.split(target)
    old = sorted(f for f in os.listdir(folder_) if f.startswith(name + ".before-"))
    for f in old[:-keep] if keep else old:
        try:
            os.remove(os.path.join(folder_, f))
        except OSError:
            pass


def reelix_url(data_dir):
    """Reelix's address on this computer, from the port data/stack/compose.yaml maps to its 7700; None when Install
    apps did not install it. Never taken from the dashboard's entries, which a signed-in session can edit."""
    try:
        with open(os.path.join(folder(data_dir), "compose.yaml"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    block = re.search(r"(?ms)^  reelix:\n(.*?)(?=^  \S|\Z)", text)
    port = re.search(r'"(\d{2,5}):7700"', block.group(1)) if block else None
    return f"http://127.0.0.1:{port.group(1)}" if port else None


def env_values(data_dir):
    """The values in data/stack/.env, for Starboard's own use (NZBGet's sign-in)."""
    try:
        with open(os.path.join(folder(data_dir), ".env"), encoding="utf-8") as f:
            return {k: v.strip().strip("'\"") for k, v in (l.split("=", 1) for l in f.read().splitlines()
                                                         if "=" in l and not l.startswith("#"))}
    except OSError:
        return {}


def nzbget_key(data_dir):
    """NZBGet's sign-in as Starboard keeps it ("user:password"), when Install apps made it; else None."""
    pw = env_values(data_dir).get("NZBGET_PASS")
    return f"{APPS['nzbget']['env']['NZBGET_USER']}:{pw}" if pw else None


# Your install: what runs now, and changing it (Settings, Your install) ------------------------------------------

VPN_ENV = {"VPN_SERVICE_PROVIDER": "provider", "VPN_TYPE": "type", "SERVER_COUNTRIES": "countries",
           "WIREGUARD_PRIVATE_KEY": "wireguard_private_key", "WIREGUARD_ADDRESSES": "wireguard_addresses",
           "OPENVPN_USER": "openvpn_user", "OPENVPN_PASSWORD": "openvpn_password"}


def current_choice(data_dir):
    """The Install apps choice that wrote data/stack, read back from compose.yaml and .env; None when there is none."""
    keys = chosen_keys(data_dir)
    env = env_values(data_dir)
    if not keys or not env.get("CONFIG_DIR"):
        return None
    image = reelix_in_stack(data_dir)
    choice = {"apps": [k for k in keys if k in APPS], "config_dir": env["CONFIG_DIR"], "data_dir": env["DATA_DIR"],
              "puid": int(env.get("PUID", 1000)), "pgid": int(env.get("PGID", 1000)), "tz": env.get("TZ", "Etc/UTC"),
              "reelix_edition": edition_of(image) or "lite"}
    vpn = {field: env[name] for name, field in VPN_ENV.items() if env.get(name)}
    if vpn:
        choice["vpn"] = vpn
    return choice


def which_install(apps, edition=None):
    """"basics", "full" or "all" when the apps are one of INSTALLS (with either Usenet app where allowed), else "custom".
    The Reelix version is not part of it."""
    have = set(apps)
    for key in ("all", "full", "basics"):
        for usenet in USENET_APPS:
            spec = INSTALLS[key]
            want = [k for k in (spec["apps"] or offered()) if k in offered()]
            if any(k in USENET_APPS for k in want):
                want = [k for k in want if k not in USENET_APPS] + [usenet if spec["usenet_choice"] else "nzbget"]
            want, _ = with_needs(want)
            if set(want) == have:  # which Reelix runs is shown on its own: Full falls back to Lite when it must
                return key
    return "custom"


def own_services(data_dir):
    """Services someone added to data/stack/compose.yaml by hand (not Starboard's apps or their databases), as the
    text of each block, so a change keeps them. Raises ValueError when the file has other top-level sections, which
    Starboard would not know how to keep."""
    try:
        with open(os.path.join(folder(data_dir), "compose.yaml"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    ours = set(APPS) | {a["db"]["service"] for a in APPS.values() if a.get("db")}
    tops = re.findall(r"^([A-Za-z_][\w-]*):", text, re.M)
    if any(t != "services" for t in tops):
        raise ValueError("Your set-up file (data/stack/compose.yaml) has sections Starboard did not write ("
                         + ", ".join(t for t in tops if t != "services") + "), so it changes nothing. Move them to "
                         "their own Compose file first")
    blocks = re.split(r"(?m)^(?=  [A-Za-z0-9_.-]+:\s*$)", text.split("services:", 1)[1]) if "services:" in text else []
    out = []
    for b in blocks:
        m = re.match(r"  ([A-Za-z0-9_.-]+):", b)
        if m and m.group(1) not in ours:
            out.append(b.rstrip() + "\n")
    return out


def plan_change(data_dir, install=None, usenet=None, edition=None, check=None):
    """What changing to another install, Usenet app or Reelix means: the new choice, and the apps added and taken
    away. Raises ValueError when Install apps did not write this server's apps."""
    now = current_choice(data_dir)
    if not now:
        raise ValueError("Install apps did not set up the apps here, so Starboard cannot change them. Use Install apps first")
    apps = list(now["apps"])
    usenet_now = next((k for k in USENET_APPS if k in apps), None)
    if install:
        c = install_choice(install, check=check, usenet=usenet or usenet_now or "nzbget")
        apps = c["apps"]
        edition = edition or c["reelix_edition"]
    if usenet and usenet in USENET_APPS and usenet != next((k for k in USENET_APPS if k in apps), usenet):
        apps = [usenet if k in USENET_APPS else k for k in apps]
    apps, _ = with_needs(apps)
    choice = {**now, "apps": apps, "reelix_edition": edition or now["reelix_edition"], "own_ports": compose_ports(data_dir)}
    if choice["reelix_edition"] == "full" and "reelix" in apps:
        reelix_image("full", check)  # raises when the full Reelix cannot be downloaded
    return {"choice": choice, "own": own_services(data_dir), "add": [k for k in apps if k not in now["apps"]],
            "remove": [k for k in now["apps"] if k not in apps],
            "reelix": (now["reelix_edition"], choice["reelix_edition"]) if "reelix" in apps else None,
            "usenet": (usenet_now, next((k for k in USENET_APPS if k in apps), None))}


def keep_made_up(env_text, old_text, shown):
    """Values made up for this write (database passwords, NZBGet's sign-in) keep their earlier value when the old .env
    had one: a database and the apps using it already know the old one."""
    old = dict(line.split("=", 1) for line in (old_text or "").splitlines() if "=" in line and not line.startswith("#"))
    out = []
    for line in env_text.splitlines():
        key = line.split("=", 1)[0] if "=" in line and not line.startswith("#") else None
        if key and shown.get(key) == "(made up for you)" and old.get(key):
            line = f"{key}={old[key]}"
        out.append(line)
    return "\n".join(out) + "\n"


SABNZBD_PORT = 8085


def sabnzbd_seed(api_key):
    """SABnzbd's first settings file. SABnzbd fills in the rest when it starts. Used only when it has none yet."""
    return ("[misc]\n"
            f"port = {SABNZBD_PORT}\n"
            "host_whitelist = sabnzbd, gluetun, localhost\n"
            "download_dir = /data/downloads/usenet/incomplete\n"
            "complete_dir = /data/downloads/usenet/completed\n"
            f"api_key = {api_key}\n")


def sabnzbd_key(data_dir):
    """SABnzbd's API key as Install apps made it up (data/stack/.env), or None."""
    return env_values(data_dir).get("SABNZBD_API_KEY") or None


def write(data_dir, built):
    path = folder(data_dir)
    os.makedirs(path, mode=0o700, exist_ok=True)
    try:
        with open(os.path.join(path, ".env"), encoding="utf-8") as f:
            built = {**built, "env": keep_made_up(built["env"], f.read(), built.get("env_shown", {}))}
    except OSError:
        pass
    for name, text, mode in (("compose.yaml", built["compose"], 0o644), (".env", built["env"], 0o600)):
        target = os.path.join(path, name)
        if os.path.exists(target):
            os.replace(target, target + f".before-{time.strftime('%Y%m%d-%H%M%S')}")  # the old one is kept
            keep_recent_copies(target)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(fd, "w") as f:
            f.write(text)
    # Every folder the apps use, for the installer to make before they start (Reelix needs its library folders to exist).
    with open(os.path.join(path, "folders.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(built.get("folders", [])) + "\n")
    # First settings files, for the installer to put in an app's settings folder when that app has none yet.
    seed = os.path.join(path, "seed")
    key = next((l.split("=", 1)[1].strip().strip("'\"") for l in built["env"].splitlines() if l.startswith("SABNZBD_API_KEY=")), "")
    if key and re.fullmatch(r"[0-9a-f]{32}", key):
        os.makedirs(os.path.join(seed, "sabnzbd"), mode=0o700, exist_ok=True)
        with os.fdopen(os.open(os.path.join(seed, "sabnzbd", "sabnzbd.ini"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
            f.write(sabnzbd_seed(key))
    hooks = os.path.join(path, "starboard-before-update")
    for key, script in (built.get("hooks") or {}).items():
        os.makedirs(hooks, mode=0o700, exist_ok=True)
        target = os.path.join(hooks, f"{key}.sh")
        if not os.path.exists(target):  # one you changed is kept
            with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700), "w") as f:
                f.write(script)
    return path


def host_folder(data_dir):
    """Where data/stack is on the computer itself: from Starboard's own container (Docker sees host paths)."""
    if not containers.available():
        return None
    try:
        for c in containers.docker("GET", "/containers/json"):
            if (c.get("Labels") or {}).get("com.docker.compose.service") != "starboard":
                continue
            for m in c.get("Mounts") or []:
                if m.get("Destination") == data_dir.rstrip("/") and _SAFE_PATH.match(m.get("Source", "")):
                    return m["Source"] + "/stack"
    except containers.DockerError:
        return None
    return None if os.path.exists("/.dockerenv") else os.path.abspath(folder(data_dir))


def chosen_keys(data_dir):
    """The apps in data/stack/compose.yaml, by their container names (which are the catalogue's keys)."""
    try:
        with open(os.path.join(folder(data_dir), "compose.yaml"), encoding="utf-8") as f:
            return re.findall(r"^    container_name: ([A-Za-z0-9._-]+)$", f.read(), re.M)
    except OSError:
        return []


def note_reelix(data_dir, choice, built):
    """When the stack has Reelix, notes what its set-up needs (server.reelix_after_start, reelix_setup): its address
    with the port it was given, what was chosen, and how qBittorrent is reached. The installer adds the one-time
    set-up token and qBittorrent's first password once they have started. Removed when Reelix is not in the stack."""
    target = os.path.join(folder(data_dir), "reelix-setup.json")
    apps = set(choice.get("apps") or [])
    if "reelix" not in apps:
        try:
            os.remove(target)
        except FileNotFoundError:
            pass
        return
    port = re.search(r'"(\d+):7700"', built["compose"])
    vpn = "gluetun" in apps
    info = {"url": f"http://127.0.0.1:{port.group(1) if port else 7700}",
            "groups": [g for g in (choice.get("groups") or APPS["reelix"]["groups"]) if g in APPS["reelix"]["groups"]],
            "qbittorrent_host": "gluetun" if vpn and "qbittorrent" in apps else "qbittorrent",
            "sabnzbd": "sabnzbd" in apps,
            "usenet": next((k for k in USENET_APPS if k in apps), None),
            "usenet_host": ("gluetun" if vpn else next((k for k in USENET_APPS if k in apps), "nzbget"))}
    fd = os.open(target + ".new", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(info, f)
    os.replace(target + ".new", target)


def want_adopted(data_dir, keys, until):
    """Keeps the apps still to add to Starboard (server.adopt_started_apps), or none."""
    target = os.path.join(folder(data_dir), "adopt.json")
    if not keys:
        try:
            os.remove(target)
        except FileNotFoundError:
            pass
        return
    os.makedirs(folder(data_dir), mode=0o700, exist_ok=True)
    with open(target + ".new", "w", encoding="utf-8") as f:
        json.dump({"keys": list(keys), "until": until}, f)
    os.replace(target + ".new", target)


def adopting(data_dir):
    """(keys, until) for the apps still to add, or None when there are none or the time is up."""
    try:
        with open(os.path.join(folder(data_dir), "adopt.json"), encoding="utf-8") as f:
            data = json.load(f)
        keys = [k for k in data.get("keys", []) if isinstance(k, str)]
        until = float(data.get("until", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    return (keys, until) if keys and until > time.time() else None


STARTING_FOR = 900  # seconds after apps are started in which an app that does not answer is "still starting"


def seconds_since_start(data_dir):
    """Seconds since Starboard, the Run first window or the installer last started the apps, or None when unknown:
    the start job's own time, else when data/stack/adopt.json was written (the terminal set-up)."""
    times = [_job["started"]] if _job.get("started") else []
    try:
        times.append(os.path.getmtime(os.path.join(folder(data_dir), "adopt.json")))
    except OSError:
        pass
    return time.time() - max(times) if times else None


def job():
    with _lock:
        if _job.get("via") and not _job.get("finished"):
            _starter_result(_job)
        return {k: v for k, v in _job.items() if k not in ("via", "request")}


# Without Docker access, the Run first window can start the apps (run-first.sh, starter): Starboard leaves a request
# in data/stack and reads the result the window leaves next to it. data/starter, touched every few seconds by that
# window, says it is open.
STARTER_FRESH = 15  # seconds


def starter_waiting(data_dir):
    try:
        return time.time() - os.path.getmtime(os.path.join(data_dir, "starter")) < STARTER_FRESH
    except OSError:
        return False


def start_via_starter(data_dir):
    with _lock:
        if _job and not _job.get("finished"):
            raise ValueError("The apps are already starting")
        request = f"{time.time():.3f}"
        path = folder(data_dir)
        for name in ("start-result.json",):
            try:
                os.remove(os.path.join(path, name))
            except FileNotFoundError:
                pass
        target = os.path.join(path, "start-request")
        with open(target + ".new", "w", encoding="utf-8") as f:
            f.write(request)
        os.replace(target + ".new", target)
        _job.clear()
        _job.update(started=time.time(), finished=False, ok=None, log="", via=path, request=request)
    return job()


def _starter_result(j):
    """Called with _lock held: the window's result, or a problem when the window closed before it answered."""
    try:
        with open(os.path.join(j["via"], "start-result.json"), encoding="utf-8") as f:
            result = json.load(f)
    except (OSError, ValueError):
        result = None
    if isinstance(result, dict) and result.get("request") == j["request"]:
        j.update(ok=bool(result.get("ok")), log=str(result.get("log", ""))[-6000:], finished=True, ended=time.time())
    elif not starter_waiting(os.path.dirname(j["via"])) and time.time() - j["started"] > STARTER_FRESH:
        j.update(ok=False, finished=True, ended=time.time(),
                 log="The Run first window closed before the apps started. Run ./install.sh --start-apps in the Starboard folder.")


def start(host_stack, built_env):
    """Makes the folders (owned by PUID:PGID) and runs `docker compose up -d`, in a short-lived helper."""
    env = dict(line.split("=", 1) for line in built_env.splitlines() if "=" in line and not line.startswith("#"))
    for k in ("CONFIG_DIR", "DATA_DIR"):
        clean_folder(env.get(k, "").strip("'"), "folder")
    with _lock:
        if _job and not _job.get("finished"):
            raise ValueError("The apps are already starting")
        _job.clear()
        _job.update(started=time.time(), finished=False, ok=None, log="")
    threading.Thread(target=_start, args=(host_stack, env), name="stack", daemon=True).start()
    return job()


def _start(host_stack, env):
    q = containers._quote
    cfg, data = env["CONFIG_DIR"].strip("'"), env["DATA_DIR"].strip("'")
    script = " && ".join([
        f"mkdir -p {q(cfg)} {q(data)}",
        f"chown {int(env['PUID'])}:{int(env['PGID'])} {q(cfg)} {q(data)}",
        f"docker compose -p {PROJECT} --env-file .env -f compose.yaml pull 2>&1 | tail -n 20",
        # --remove-orphans: an app taken out of compose.yaml (a smaller install, NZBGet in place of SABnzbd) stops and
        # goes; its settings folder stays.
        f"docker compose -p {PROJECT} --env-file .env -f compose.yaml up -d --remove-orphans 2>&1",
        # Not a database's folder (jellystat-db, storyarr-db): the database owns it, and changing it while the
        # database sets itself up leaves it unfinished ("no pg_hba.conf entry for host").
        f"for d in {q(cfg)}/* {q(data)}/media {q(data)}/downloads; do case \"$d\" in *-db) continue ;; esac; "
        f"[ -d \"$d\" ] && chown {int(env['PUID'])}:{int(env['PGID'])} \"$d\"; done; true",
    ])
    try:
        try:
            containers.docker("POST", f"/images/create?fromImage={containers.urllib.parse.quote(containers.HELPER_IMAGE, safe='')}",
                              raw=True, timeout=300)
        except containers.DockerError:
            pass
        code, text = containers._helper(host_stack, script, extra_binds=[f"{cfg}:{cfg}", f"{data}:{data}"])
        with _lock:
            _job.update(ok=code == 0, log=text[-6000:])
    except containers.DockerError as e:
        with _lock:
            _job.update(ok=False, log=str(e))
    finally:
        with _lock:
            _job.update(finished=True, ended=time.time())
