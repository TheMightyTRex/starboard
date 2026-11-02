"""What Starboard can reach and control, in words, for Settings, About and updates.

Each item says what it is for, whether it is on now (read from what Starboard can actually see, not from what
was asked for), and how to change it: a switch in Settings, or a question in ./install.sh.
"""

import os

from . import containers


def _item(key, title, what, on, change, **extra):
    return {"key": key, "title": title, "what": what, "on": bool(on), "change": change, **extra}


def summary(app):
    d = app.config.data
    clients = [s["name"] for s in d["services"] if s["type"] in ("qbittorrent", "sabnzbd") and s.get("api_key")]
    jobs = os.environ.get("STARBOARD_JOBS_DIR", "")
    smart = os.environ.get("STARBOARD_SMART_DIR", "")
    return [
        _item("network", "Your home network",
              "Phones and computers on your home network can open Starboard. Off: only this computer can.",
              d.get("network_access", True), "setting", link="/settings-security.html"),
        _item("apps", "Your apps",
              "Starboard reads status, queues, calendars and updates from the apps you add, with the API keys you give it. "
              "It adds films, series and books only when you choose Add.",
              any(s.get("api_key") for s in d["services"]), "apps", link="/settings.html"),
        _item("download_hours", "Pausing and resuming downloads",
              "Outside your download hours, Starboard pauses qBittorrent and SABnzbd"
              + (f" ({' and '.join(clients)})" if clients else "") + ".",
              d["download_hours"]["enabled"] and clients, "setting", link="/settings-general.html#download-hours"),
        _item("docker", "Docker, for app updates",
              "Lists your containers and installs new images on Apps, Updates. This is full control of Docker, "
              "which is the same as full control of the server.",
              containers.available(), "installer", on_flag="--docker", off_flag="--no-docker"),
        _item("disks", "Your folders, for free space",
              "Reads how full the folders you chose are, on System, Storage. Read-only.",
              app.disks, "installer", on_flag="--disk Name=/path", off_flag="--no-disks"),
        _item("disk_health", "Disk health reports",
              "A timer on the server runs smartctl as root every 30 minutes and saves reports that Starboard reads. "
              "Setting it up asks for your password with sudo.",
              smart and os.path.isdir(smart), "installer", on_flag="--disk-health", off_flag="--no-disk-health"),
        _item("backup", "A backup job on the server",
              "Starboard asks a backup job that you set up on the server to run, and lists the files it makes. "
              "It cannot read or change the backups.",
              jobs and os.path.isdir(jobs), "readme"),
        _item("release_check", "GitHub, for new Starboard versions",
              "At most every 6 hours, Starboard asks GitHub for its newest release. Nothing about you is sent.",
              d["update_check"] and app.repo, "setting", link="#update-check-row", setting="update_check"),
        _item("icons", "The dashboard-icons collection, for app icons",
              "The server downloads each app's icon once from the dashboard-icons collection and keeps a copy. "
              "Off: only icons already saved, or ones you put in data/icons.",
              d["fetch_icons"], "setting", setting="fetch_icons"),
        _item("posters", "Image sites, for posters on Coming up",
              "Your browser loads posters and covers from the sites your apps use, such as TheTVDB and TMDB, "
              "so those sites see your address. Off: Coming up shows the app's icon instead.",
              d["show_posters"], "setting", setting="show_posters"),
    ]
