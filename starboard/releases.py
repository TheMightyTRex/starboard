"""What each Starboard release brings: the one source for release notes in the app (the version in the footer),
the upgrade wizard, and the notes file of each GitHub release (tools/release_notes.py writes docs/releases/).

Newest last. Each release:
  version, date
  added, changed, fixed      lists of (title, sentence)
  review                     upgrade wizard steps for settings worth choosing after this upgrade (ids the wizard
                             knows: "apps", "keys", "jellyfin", "hours", "alerts", "preset", "names", "storage"); empty when
                             the upgrade needs no choices, so it finishes on its own
  settings                   what changed in your settings, and the way back to the version before
"""

RELEASES = [
    {"version": "0.2.0", "date": "2 November 2026",
     "added": [("Coming up", "Posters, a List or Calendar view, and how far ahead to look."),
               ("Download hours", "qBittorrent and SABnzbd download only between the hours you set."),
               ("Alerts", "Uptime history, alerts to ntfy, Gotify or a webhook, and a weekly summary."),
               ("Apps, Updates", "Each app's container, Check for updates, Update all and Update.")],
      "changed": [("Lightweight first", "Compressed pages, a shared cache and hidden tabs that stop refreshing."),
                  ("Shared look", "Every page uses the component library shared with Storyarr.")],
      "fixed": [], "review": [],
      "settings": "New settings start off. To go back, run ./update.sh --to v0.1.8."},
    {"version": "0.3.0", "date": "2 November 2026",
     "added": [("Settings, Jellyfin", "Live TV, watch history import and user defaults, moved in from the old launcher.")],
     "changed": [("Other services", "Lists Starboard's own jobs and whether each is on.")],
     "fixed": [], "review": ["jellyfin"],
     "settings": "Each Jellyfin job starts off. To go back, run ./update.sh --to v0.2.0."},
    {"version": "0.3.4", "date": "2 November 2026",
     "added": [("Costs", "Every setting that uses processor time or memory says what it costs.")],
     "changed": [("Live TV", "Channel lists are rebuilt only when they change; guides refresh daily.")],
     "fixed": [("Jellyfin", "The API key is sent the way newer Jellyfin versions need it."),
               ("Imports", "Big Jellyfin libraries are read in pages.")],
     "review": [], "settings": "No settings change. To go back, run ./update.sh --to v0.3.0."},
    {"version": "0.4.0", "date": "2 November 2026",
     "added": [("Settings, Performance", "Starboard's own use, presets (Small server, Balanced, Everything) and a switch for every piece of background work.")],
     "changed": [("Background work", "Each thread runs only while its feature is on. System history every 5 minutes by default.")],
     "fixed": [("Security", "Fixes from a full security check: request sizes, password limits, the sign-in redirect, saved keys, container updates and more."),
               ("Host names", "Starboard answers only to IP addresses, localhost, the computer's name and STARBOARD_ALLOWED_HOSTS.")],
     "review": ["preset", "names"],
     "settings": "Adds performance settings (the Balanced preset). To go back, run ./update.sh --to v0.3.4."},
    {"version": "0.5.0", "date": "2 November 2026",
     "added": [("Install apps", "A guide that sets up a media server in groups (Movies, TV, Music, Ebooks, Audiobooks, Comics and more): it writes a Compose file, shows it, and starts the apps when you give your password. It can point them at your media where it is."),
               ("Storage charts", "System, Storage shows the pool as a bar and a ring by type (TV, films, books and more) with free space, each drive in the pool, space used over time with a forecast, and the biggest series and films."),
               ("Search for new apps", "Manage apps finds apps on this computer and adds the ones you tick, with their API keys if Starboard has Docker access."),
               ("Set-up guide", "Finds your apps, then asks about API keys, Jellyfin, download hours, alerts and how much Starboard does. Run it again from Settings, General."),
               ("Release notes", "Select the version in the footer to read what is new."),
               ("Upgrade guide", "After an upgrade with something to choose, a short guide shows what is new and asks only those questions.")],
     "changed": [], "fixed": [],
     "review": ["apps", "storage"],
     "settings": "Adds a record of the set-up guide and the last upgrade, and three Storage settings in Settings, Performance (sorting by type only when you ask, a daily record of used space, and page updates only when you press Check again). To go back, run ./update.sh --to v0.4.0."},
    {"version": "0.5.1", "date": "2 November 2026",
     "added": [], "changed": [("Upgrade available", "Looks for the newest version tag, which is what ./update.sh installs.")],
     "fixed": [("Upgrade available", "No longer offers an older version as an upgrade.")],
     "review": [], "settings": "No settings change. To go back, run ./update.sh --to v0.5.0."},
    {"version": "0.5.2", "date": "2 November 2026",
     "added": [], "changed": [],
     "fixed": [("Upgrade guide", "An upgrade from 0.4.0 or earlier now shows the 0.5.0 questions (new apps and Storage) instead of skipping them.")],
     "review": [], "settings": "No settings change. To go back, run ./update.sh --to v0.5.1."},
]


FIRST_RECORDED = "0.5.0"  # the first release that records which version the upgrade guide last finished


def _key(version):
    try:
        return tuple(int(x) for x in str(version).split(".")[:3])
    except ValueError:
        return (0, 0, 0)


def between(old, new):
    """Releases after old, up to and including new, oldest first."""
    return [r for r in RELEASES if _key(old) < _key(r["version"]) <= _key(new)]


def pending(last_version, current, set_up):
    """What the upgrade wizard needs: the releases since the last one finished, and the questions they bring.
    An install with no password yet needs none (set-up records the version); an install from before this was
    recorded (0.4.0 or earlier) starts from 0.4.0."""
    if not set_up and not last_version:
        return {"from": current, "to": current, "releases": [], "review": [], "wizard": False}
    # The record began with 0.5.0, so an install without one came from 0.4.0 or earlier.
    start = last_version or ("0.4.0" if _key(current) >= _key(FIRST_RECORDED) else current)
    found = between(start, current)
    review = []
    for r in found:
        review += [x for x in r["review"] if x not in review]
    return {"from": start, "to": current, "releases": found, "review": review, "wizard": bool(review)}


def markdown(release):
    """A release's notes for GitHub (docs/releases/vX.Y.Z.md)."""
    out = [f"# Starboard v{release['version']}", "", f"Released {release['date']}.", ""]
    for heading, key in (("Added", "added"), ("Changed", "changed"), ("Fixed", "fixed")):
        if release[key]:
            out += [f"## {heading}", ""] + [f"- **{t}.** {s}" for t, s in release[key]] + [""]
    out += ["## Your settings and the way back", "", release["settings"], ""]
    return "\n".join(out)
