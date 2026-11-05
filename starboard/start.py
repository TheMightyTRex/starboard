"""How to start: the first question of both set-ups, in the browser and in the terminal (DASH-102).

One source for the words, so the two set-ups always ask the same question with the same answers and help
(the design system's WIZARD.md section 2, "One wizard, two ways to show it"). The recommended answer comes from
what is on this computer: apps Starboard can find that are not added yet, and what the Run first script found
before it handed over (data/run-first.json).
"""

import json
import os
import re

from . import discovery

CHOICES = [
    {"key": "new", "title": "New install",
     "about": "Set up a new media server. Starboard installs the apps you choose and connects them.",
     "help": "For a computer with no media apps yet. Starboard asks what you want to watch, listen to and read, "
             "then installs the apps for it, picks the folders and connects the apps to each other."},
    {"key": "move", "title": "Move from apps you already run",
     "about": "Starboard adds the apps already running on this computer, such as Sonarr, Radarr and Jellyfin, and "
              "keeps their media folders.",
     "help": "For a computer that already runs media apps. Starboard finds them and adds them, reading their API "
             "keys where it can. Nothing in the apps changes, and your films, series and books stay where they are. "
             "You can install more apps later in Settings, Install apps."},
    {"key": "restore", "title": "Restore a backup",
     "about": "Bring back Starboard's settings from a backup file: your apps, categories, design and alerts.",
     "help": "For moving Starboard to a new computer, or starting again. Use a file downloaded from System, Backup "
             "and restore, Download a copy of the settings. It is checked before anything changes, and your "
             "password stays the one you just chose."},
]
# Apps that mean "this computer already runs a media server".
MEDIA = {"sonarr", "radarr", "lidarr", "readarr", "prowlarr", "bazarr", "jellyfin", "emby", "plex", "seerr",
         "qbittorrent", "sabnzbd", "transmission", "deluge", "nzbget", "audiobookshelf"}


def handover(data_dir):
    """What the Run first script found before it handed over, or {}."""
    try:
        with open(os.path.join(data_dir, "run-first.json"), encoding="utf-8") as f:
            found = json.load(f)
        return found if isinstance(found, dict) else {}
    except (OSError, ValueError):
        return {}


def options(services, data_dir, search=None):
    """The choices, the recommended one, and the apps found that are not added yet."""
    try:
        found = (search or discovery.search)(services).get("items", [])
    except Exception:  # finding apps is a help, never a reason the set-up cannot go on
        found = []
    media = [f for f in found if f.get("key") in MEDIA]
    named = [str(n) for n in handover(data_dir).get("apps", []) if isinstance(n, str)]
    recommended = "move" if media or named else "new"
    return {"choices": [{**c, "recommended": c["key"] == recommended} for c in CHOICES],
            "recommended": recommended, "found": [f.get("name", "") for f in media] or named}


# Storage: where the media goes, for a new install. The same answers in both set-ups (DASH-103).
GOOD_FS = {"ext4", "xfs", "btrfs"}


def _tb(size):
    try:
        return f"{int(size) / 1e12:.1f} TB"
    except (TypeError, ValueError):
        return "unknown size"


def storage(main_folder, drives, pool_ready):
    """The answers for Storage: this computer's main disk, each separate disk, or a pool of them. drives are the
    mounted drives that are not the system disk (sysinfo.pool_candidates), or None when there is no drive list."""
    drives = drives or []
    choices = [{"key": "main", "title": "This computer's main disk",
                "about": "The media folder goes on the disk Linux is on. Fine for a start; a separate disk keeps "
                         "media apart from the system.", "folder": main_folder}]
    for d in sorted(drives, key=lambda d: -int(d.get("size") or 0)):
        fs_note = "" if d.get("fs") in GOOD_FS else f" It uses {d.get('fs') or 'an unknown file system'}, which works, but ext4 is better on Linux."
        choices.append({"key": "disk:" + d["mount"], "title": f"A separate disk: {d.get('label') or d.get('model') or d['device']}",
                        "about": f"{_tb(d.get('size'))}, at {d['mount']}.{fs_note}",
                        "folder": d["mount"].rstrip("/") + "/media"})
    if len(drives) >= 2 or pool_ready:
        choices.append({"key": "pool", "title": "A pool of several disks",
                        "about": "Joins disks into one folder, /mnt/pool, so the media has one place however many disks "
                                 "there are. Needs the pool helper" + ("." if pool_ready else ": run ./install.sh again and say yes to Drive pools."),
                        "folder": "/mnt/pool/media", "ready": bool(pool_ready)})
    if len(drives) >= 2 and pool_ready:
        recommended = "pool"
    elif drives:
        recommended = choices[1]["key"]  # the biggest separate disk
    else:
        recommended = "main"
    for c in choices:
        c["recommended"] = c["key"] == recommended
    return {"choices": choices, "recommended": recommended,
            "help": "The media folder holds your films, series, books and downloads together, so a finished download "
                    "moves into the library in an instant. It is made for you when the apps start. A separate disk "
                    "keeps media apart from the system; a pool joins several disks into one folder."}


SAFE_FOLDER = re.compile(r"^/[A-Za-z0-9._/-]{0,250}$")


def host_args(wanted):
    """./install.sh options for the set-up's changes to this computer. Folders are checked, so the command shown
    is safe to copy: absolute, no quotes, no shell characters."""
    wanted = wanted if isinstance(wanted, dict) else {}
    args = []
    media = str(wanted.get("media") or "")
    if media and SAFE_FOLDER.match(media):
        args += ["--disk", f"Media={media}"]
    livetv = str(wanted.get("livetv") or "")
    if livetv and SAFE_FOLDER.match(livetv):
        args += ["--livetv-folder", livetv]
    if wanted.get("health"):
        args.append("--disk-health")
    return args
