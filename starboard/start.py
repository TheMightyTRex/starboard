"""How to start: the first question of both set-ups, in the browser and in the terminal (DASH-102).

One source for the words, so the two set-ups always ask the same question with the same answers and help
(the design system's WIZARD.md section 2, "One wizard, two ways to show it"). The recommended answer comes from
what is on this computer: apps Starboard can find that are not added yet, and what the Run first script found
before it handed over (data/run-first.json).
"""

import json
import os

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
