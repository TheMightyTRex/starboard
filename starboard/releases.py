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
    {"version": "0.5.3", "date": "2 November 2026",
     "added": [("Ready-made image", "Starboard is published at ghcr.io/themightytrex/starboard for amd64 and arm64, with compose.image.yaml to run it without building anything.")],
     "changed": [("Links", "The README and licence name the project's GitHub account and author.")],
     "fixed": [], "review": [], "settings": "No settings change. To go back, run ./update.sh --to v0.5.2."},
    {"version": "0.5.4", "date": "2 November 2026",
     "added": [], "changed": [("Status beside headings", "On System, Overview, Jellyfin's state (Up to date, Restart needed, Update available) sits beside its name instead of on a line of its own. Status follows one rule across Starboard and Storyarr.")],
     "fixed": [], "review": [], "settings": "No settings change. To go back, run ./update.sh --to v0.5.3."},
    {"version": "0.5.5", "date": "2 November 2026",
     "added": [("System, Logs", "What Starboard did and every problem it met, newest first, with Download and Delete logs. Kept for 60 days by default (Settings, General)."),
               ("Report a problem", "Detailed logging for 24 hours, then Copy the details and Open a new issue on GitHub. Passwords, API keys, addresses and names are removed before anything is written.")],
     "changed": [("Docker's log", "Holds only start-up and problems, capped at 3 MB in the Compose files.")],
     "fixed": [("System, Overview", "The charts' history loads again (broken since 0.4.0).")],
     "review": [], "settings": "Adds log settings: kept for 60 days, detailed logging off. To go back, run ./update.sh --to v0.5.4."},
    {"version": "0.5.6", "date": "2 November 2026",
     "added": [], "changed": [
        ("One name for refresh", "Check again everywhere; Storage's slower job is Sort by type."),
        ("Settings save one way", "Choices save as soon as they change; text fields keep a Save button; one main button per page."),
        ("Buttons and dialogs", "Full-size buttons outside dense tables; danger buttons before danger dialogs, with Cancel and the bin icon."),
        ("Charts", "Text follows the Text size setting; media colours come from the shared library, with a high contrast set.")],
     "fixed": [("Look and feel", "Wizard headings no longer show a focus box; Performance's preset cards line up; Jellyfin's sections have room; the second line on System charts is dashed like its legend; phone stat tiles fill their row.")],
     "review": [], "settings": "No settings change. To go back, run ./update.sh --to v0.5.5."},
    {"version": "0.6.0", "date": "2 November 2026",
     "added": [("Listening progress", "Settings, Audiobookshelf copies where everyone is in each audiobook, and what they finished, from Plex, Jellyfin, Emby or another Audiobookshelf. Progress people already have is never changed, and books not found are listed.")],
     "changed": [("Audiobookshelf", "Is an app type of its own, with its version and an optional admin API key. Apps named Audiobookshelf move to it by themselves."),
                 ("Install apps", "Listening progress is no longer marked coming soon.")],
     "fixed": [],
     "review": ["keys"],
     "settings": "Adds a switch to keep applying listening progress (off; on in the Everything preset), and gives apps named Audiobookshelf their own type. To go back, run ./update.sh --to v0.5.6, which keeps the app as an Other app."},
    {"version": "0.7.0", "date": "2 November 2026",
     "added": [("Install apps for beginners", "A Start here step explains how the apps work together; sensible apps and folders are chosen for you, with Advanced settings for the rest; every step is checked; a pool can join several drives; and after starting, a guide shows how to connect each app."),
               ("Copy app settings", "Copies tags, custom formats, quality profiles, root folders, download clients and naming from one Sonarr, Radarr or Lidarr into another, and asks for the passwords the old app keeps hidden."),
               ("Storyarr in Install apps", "Offered by default, with a database backup before each update."),
               ("Upgrade now from Storyarr", "Apps, Updates opens on one app (apps-updates.html?app=storyarr), checks at once and goes to its row."),
               ("More detail", "Recent checks and Check again for one app; how long an app has been down; Remove and Find another for downloads; overviews and app links on Coming up, with a month at a time; links from Search into the app; the full SMART table, self-tests and report download; what each saved settings copy holds, and downloads of copies and server backups; the date this version started.")],
     "changed": [("Slide-outs", "Display and accessibility is now a slide-out. Every slide-out has its header in the page colour over a white (or dark) body."),
                 ("Categories", "Renaming or removing one moves its apps in a single save."),
                 ("Wrong passwords", "A wrong password in a dialog or Install apps stays on the page instead of signing you out."),
                 ("Raspberry Pi", "The image is also built for 32-bit Raspberry Pi; Pillow (white logos) is left out where it cannot be installed.")],
     "fixed": [],
     "review": [],
     "settings": "No settings change. To go back, run ./update.sh --to v0.6.0."},
    {"version": "0.7.1", "date": "2 November 2026",
     "added": [],
     "changed": [("Updates", "Each app has its logo beside its name. Installed and Latest are left-aligned, every category's table has the same column widths so the columns line up, and each row's cells sit on the middle of the row.")],
     "fixed": [("Long API keys", "Keys were cut to 200 characters when saved, so Audiobookshelf, whose keys are longer, refused its key. If Audiobookshelf says the key is wrong, paste it again in Manage apps."),
               ("Log", "A connection that stayed idle until it timed out no longer writes an error to Docker's log.")],
     "review": [],
     "settings": "No settings change. To go back, run ./update.sh --to v0.7.0."},
    {"version": "0.7.2", "date": "2 November 2026",
     "added": [],
     "changed": [("App cards", "In Health first and Tiles every card has the same rows in the same places: the status beside the name, what the app is doing, the address as a link that opens the app, warnings, then update, version and reply time along the bottom. Cards side by side are the same height."),
                 ("App logos", "A logo is shown on its own, without a tile; apps without one keep their initials on a tile.")],
     "fixed": [("Updates for test builds", "An app on a test build, such as v0.4.9-dev.6, which is not in its registry, is now offered the newest release instead of nothing.")],
     "review": [],
     "settings": "No settings change. To go back, run ./update.sh --to v0.7.1."},
    {"version": "0.7.3", "date": "2 November 2026",
     "added": [],
     "changed": [("App cards", "The reply time is on the right, so long versions such as 2.7.0.5723 have room. An unknown version shows nothing, and an app that does not answer shows N/A for its reply time.")],
     "fixed": [("Long versions", "A long version number no longer runs into the reply time; on a very narrow card it breaks after a dot.")],
     "review": [],
     "settings": "No settings change. To go back, run ./update.sh --to v0.7.2."},
    {"version": "0.7.4", "date": "3 November 2026",
     "added": [("Help centre", "Help for installing and using Starboard, written for people new to home servers: guides, one topic for each task, and the basics. Help in the footer opens it."),
               ("Reset a forgotten password", "Run ./reset-password.sh on the server. It signs everyone out and shows a new setup code; your apps and settings stay."),
               ("Not in Jellyfin yet", "Importing watch history now lists the films and episodes Jellyfin does not have yet, in Settings, Jellyfin."),
               ("Note issues", "For testing: activate it in Settings, General to note a problem with any page as you find it.")],
     "changed": [("Messages", "Confirmations appear as cards in the corner, and a settings page shows Saved at and the time beside the button instead."),
                 ("Words", "Settings are activated and deactivated, and show as active or inactive.")],
     "fixed": [("Disk health", "The page shows again: a mistake in its script had stopped it since 0.7.0."),
               ("Restoring old backups", "A backup from before 0.6.0 is brought up to date, and a design that no longer exists goes back to the default instead of stopping the restore."),
               ("Large text on phones", "At 175% the Apps page fits the screen, and an app's status goes under its name when they do not fit side by side."),
               ("Docker access with the ready-made image", "compose.image.yaml now has the line that lets Starboard use the Docker socket. Add your socket's group number there, as the file explains.")],
     "security": [("Pillow 13.0.0", "The picture library for white Live TV logos had 58 known problems, 5 of them critical. Logos are now read only as PNG, JPEG, GIF, WebP, BMP or ICO."),
                  ("Smaller image", "The image no longer includes pip, which Starboard does not need to run."),
                  ("Sign-in", "The password is never put in the page address, even if Enter is pressed before the page has loaded."),
                  ("Live TV playlists", "A stream check no longer opens a file: link written in a playlist from the internet."),
                  ("Other sites", "New headers stop other sites loading Starboard's files into their pages. Live TV logos stay open to Jellyfin."),
                  ("Exact addresses", "An address that only starts like one of Starboard's own, such as /api/containers - Copy, is now not found."),
                  ("Checks", "Every release is scanned with Trivy, OWASP ZAP, Gitleaks, Bandit, ShellCheck and Hadolint. What each found is in docs/SECURITY-AND-TESTS.md.")],
     "review": [],
     "settings": "No settings change. To go back, run ./update.sh --to v0.7.3."},
    {"version": "0.7.5", "date": "3 November 2026",
     "added": [("Send feedback", "In place of Note issues, activate it in Settings, General to report a problem, suggest something or check a page for accessibility problems. Each report opens as an issue on Starboard's GitHub page or is saved in Starboard, listed under Testing.")],
     "changed": [("Errors where they happened", "A problem saving a setting or running an action shows beside that switch or button, and clears on your next try. An error with nothing on the page to belong to stays in the corner until you close it."),
                 ("Updates", "The button says Check until the first check, then Check again."),
                 ("Watch history files", "A history file can be up to 80 MB, which is more than 250,000 films and episodes. Reading one takes about four and a half times its size in memory.")],
     "fixed": [],
     "security": [("Memory and process limits", "Starboard is capped at 512 MB of memory and 200 processes, so a fault cannot take the whole server's. Docker Bench for Security found it had none."),
                  ("Slow name check", "A saved copy's name made of many hyphens could make one check slow. Names are now length-checked and matched only one way (found by CodeQL)."),
                  ("Line breaks in headers", "A header value with a line break is never sent, so no answer can be split in two (found by CodeQL)."),
                  ("Older TLS", "Checking when an https address's certificate runs out now needs TLS 1.2 or newer (found by CodeQL)."),
                  ("Send feedback", "Its reports are saved only with a key given to a signed-in browser, which stops working when that browser signs out. The content policy lets in only Snaglist's own stylesheet."),
                  ("Checks", "Trivy, OWASP ZAP, Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release. What each found is in docs/SECURITY-AND-TESTS.md.")],
     "review": [],
     "settings": "If Note issues was active, Send feedback is active, and your notes are listed with the new reports. With Docker, the limits come with the update. Without Docker (--native), run ./install.sh --native again to add them. To go back, run ./update.sh --to v0.7.4."},
    {"version": "0.7.6", "date": "4 November 2026",
     "added": [("A menu in three levels", "A side menu beside every page has the Starboard logo, Search and five sections: Library, Discover, Activity, System and Settings. The level 1 menu along the header holds a section's pages, and the level 2 menu under it holds a page's own tabs. Every page keeps its address."),
               ("Server name", "Give your server a name of up to 10 characters in Settings, General. It shows in bold at the start of the level 1 menu. Phones show only the logo."),
               ("Help for each section", "A Help button beside Display opens the help for the section you are in, in a new tab."),
               ("Places for Reelix", "The Library (TV, Films, Radio, Books and Audiobooks), Trending, Recently finished, Wanted, History and Settings, Reelix have their places in the menu. Each says it comes with Reelix.")],
     "changed": [("A new logo", "The Screen logo, a screen with four tiles and a star, in the side menu and the header. The browser tab and the app icon keep the old one for now."),
                 ("Where things are", "Some pages moved in the menu. For example, Jellyfin and Audiobookshelf are under Settings, Apps; Updates and Other services are under System, Apps; Downloads and Requests are under Activity. The help says where each one is."),
                 ("Shelf", "The Shelf design no longer adds its own icon rail, because every design now has the side menu.")],
     "fixed": [],
     "security": [("Checks", "Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release. They found nothing to fix; ZAP's two warnings were false alarms, explained in docs/SECURITY-AND-TESTS.md.")],
     "review": [],
     "settings": "Nothing to choose. A dashboard name of 10 characters or fewer becomes the server name, which you can change or clear in Settings, General. To go back, run ./update.sh --to v0.7.5."},
    {"version": "0.7.7", "date": "4 November 2026",
     "added": [],
     "changed": [("Pages open faster", "A page and its files now share one connection, and the browser keeps the styles, scripts and icons until they change. Opening a page takes less than half the server's processor time, and a page you have opened before about a sixth."),
                 ("Live TV uses far less memory", "TV guides are read as they unpack instead of all at once. A large guide peaked at 197 MB and now takes 36 MB."),
                 ("Starting up", "Starboard's code is prepared when the image is built, so it starts in about half the time.")],
     "fixed": [("Samsung TV Plus and Pluto TV guides", "They were refused because of a line at their start, and every stream was tested again every hour as a result. They now load, and the hourly check finds nothing to do."),
               ("Failed guides", "A guide that fails is tried again after 12 hours, not every hour.")],
     "security": [("Error answers", "Python's own error answers, such as for a request method Starboard does not handle, now carry the same security headers as every other answer (found by OWASP ZAP)."),
                  ("Checks", "Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release. ZAP's two signed-in warnings were false alarms, explained in docs/SECURITY-AND-TESTS.md.")],
     "review": [],
     "settings": "Nothing to choose, and no setting changes. Live TV builds its channels and guides once after the update. To go back, run ./update.sh --to v0.7.6."},
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
    for heading, key in (("Added", "added"), ("Changed", "changed"), ("Fixed", "fixed"), ("Security", "security")):
        if release.get(key):
            out += [f"## {heading}", ""] + [f"- **{t}.** {s}" for t, s in release[key]] + [""]
    out += ["## Your settings and the way back", "", release["settings"], ""]
    return "\n".join(out)
