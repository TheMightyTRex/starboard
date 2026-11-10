"""What Starboard can reach and control, in words, for Settings, Updates.

Each item says what it is for, whether it is on now (read from what Starboard can actually see, not from what
was asked for), and how to change it: a switch in Settings, or a question in ./install.sh.
"""

import os

from . import containers, sysinfo


def _item(key, title, what, on, change, **extra):
    return {"key": key, "title": title, "what": what, "on": bool(on), "change": change, **extra}


def summary(app):
    d = app.config.data
    clients = [s["name"] for s in d["services"] if s["type"] in ("qbittorrent", "sabnzbd", "nzbget") and s.get("api_key")]
    jobs = os.environ.get("STARBOARD_JOBS_DIR", "")
    smart = os.environ.get("STARBOARD_SMART_DIR", "")
    return [
        _item("network", "Your home network",
              "Phones and computers on your home network can open Starboard. Off: only this computer can.",
              d.get("network_access", True), "setting", link="/settings-security.html", cost="Nothing noticeable."),
        _item("apps", "Your apps",
              "Starboard reads status, queues, calendars and updates from the apps you add, with the API keys you give it. "
              "It adds films, series and books only when you choose Add.",
              any(s.get("api_key") for s in d["services"]), "apps", link="/settings.html", cost="A few small requests to each app when a page that shows it is open, shared for a few seconds."),
        _item("download_hours", "Pausing and resuming downloads",
              "Outside your download hours, Starboard pauses qBittorrent, NZBGet and SABnzbd"
              + (f" ({' and '.join(clients)})" if clients else "") + ".",
              d["download_hours"]["enabled"] and clients, "setting", link="/settings-general.html#download-hours", cost="One small check a minute, under 0.01% of the processor."),
        _item("watch", "Watching in the background, and alerts",
              "Checks your apps every few minutes with no page open, keeps their uptime history, and sends alerts"
              + (f" to {d['watch']['channel']['kind']}" if d["watch"]["channel"].get("kind") else "") + ".",
              d["watch"]["enabled"], "setting", link="/settings-alerts.html", cost="About 0.02 seconds of processor every 5 minutes and under 1 MB of memory."),
        _item("docker", "Docker, for app updates",
              "Lists your containers and installs new images on System, Apps, Updates. This is full control of Docker, "
              "which is the same as full control of the server.",
              containers.available(), "installer", on_flag="--docker", off_flag="--no-docker", cost="Nothing until you open System, Apps, Updates; a check reads a few small files from each registry."),
        _item("app_use", "Per-app processor and memory use",
              "Reads two small files per container from the server's cgroup folder, read-only, while System, Overview, Monitor is open.",
              bool(sysinfo.cgroup_dir()) and os.path.isdir(os.path.join(sysinfo.cgroup_dir(), "system.slice")),
              "installer", on_flag="--app-use", off_flag="--no-app-use", cost="Two small files per container every 2 seconds, only while Monitor is open."),
        _item("livetv", "Jellyfin's Live TV folder",
              "Starboard writes channel playlists, guides and logos there once a day while the Live TV plug-in is active (Settings, Plug-ins). "
              "Jellyfin can fetch logos and Pluto streams from Starboard without signing in, and only while the Live TV plug-in is active.",
              bool(os.environ.get("STARBOARD_IPTV_DIR")), "installer", on_flag="--livetv-folder /path", off_flag="--no-livetv", cost="See Settings, Apps, Jellyfin: under 2 seconds a day, about a minute a week."),
        _item("jellyfin_jobs", "Jellyfin: watch history import and user defaults",
              "With Jellyfin's API key, Starboard marks imported history as watched and sets defaults for users who have not chosen their own.",
              d["extras"].get("import_keep") or d["extras"].get("defaults"), "setting", link="/settings-jellyfin.html", cost="About 1 second of processor and up to 40 MB of memory for 20 seconds an hour (import); defaults, nothing noticeable."),
        _item("listening", "Audiobookshelf: listening progress",
              "With an admin API key, Starboard makes a key that acts as each person for up to 15 minutes, writes their progress "
              "and deletes the key. Progress a person already has is never changed.",
              d["extras"].get("listening_keep"), "setting", link="/settings-audiobookshelf.html", cost="Reads your Audiobookshelf library once an hour: about a second of processor."),
        _item("disks", "Your folders, for free space",
              "Reads how full the folders you chose are, on System, Storage. Read-only.",
              app.disks, "installer", on_flag="--disk Name=/path", off_flag="--no-disks", cost="Reads free space when a page shows it; Sort by type (on demand) reads every file once."),
        _item("disk_health", "Disk health reports",
              "A timer on the server runs smartctl as root every 30 minutes and saves reports that Starboard reads. "
              "Setting it up asks for your password with sudo.",
              smart and os.path.isdir(smart), "installer", on_flag="--disk-health", off_flag="--no-disk-health", cost="The reading job runs on the server itself, not in Starboard: a few seconds every 30 minutes."),
        _item("backup", "A backup job on the server",
              "Starboard asks a backup job that you set up on the server to run, and lists the files it makes. "
              "It cannot read or change the backups.",
              jobs and os.path.isdir(jobs), "readme", cost="Nothing in Starboard; the job runs on the server when you ask."),
        _item("release_check", "GitHub, for new Starboard versions",
              "At most every 6 hours, Starboard asks GitHub for its newest release. Nothing about you is sent.",
              d["update_check"] and app.repo, "setting", link="#update-check-row", setting="update_check", cost="One small request every 6 hours at most."),
        _item("icons", "The dashboard-icons collection, for app icons",
              "The server downloads each app's icon once from the dashboard-icons collection and keeps a copy. "
              "Off: only icons already saved, or ones you put in data/icons.",
              d["fetch_icons"], "setting", setting="fetch_icons", cost="One download per app, once; then a few kilobytes on disk."),
        _item("posters", "Posters on Coming up",
              "The server fetches small posters from your own apps and keeps copies for a week (a few megabytes). "
              "Off: Coming up shows each app's icon instead. Search results still show covers from the sites "
              "your apps use, such as TMDB.",
              d["show_posters"], "setting", setting="show_posters", cost="A small download per new poster, kept for a week (a few megabytes on disk)."),
    ]
