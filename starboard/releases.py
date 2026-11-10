"""What each Starboard release brings: the one source for release notes in the app (the version in the footer),
the upgrade wizard, and the notes file of each GitHub release (tools/release_notes.py writes docs/releases/).

Newest last. Each release:
  version, date
  added, changed, deprecated, removed, fixed, security
                             lists of (title, sentence), the same types as CHANGELOG.md; leave out the empty ones
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
     "fixed": [],
     "security": [("Full security check", "Fixes from a full security check: request sizes, password limits, the sign-in redirect, saved keys, container updates and more."),
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
     "added": [], "changed": [],
     "fixed": [("Upgrade available", "Looks for the newest version tag, which is what ./update.sh installs, and no longer offers an older version as an upgrade.")],
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
     "removed": [("Note issues", "Send feedback takes its place, and your notes are listed with the new reports.")],
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
                 ("Where things are", "Some pages moved in the menu. For example, Jellyfin and Audiobookshelf are under Settings, Apps; Updates and Other services are under System, Apps; Downloads and Requests are under Activity. The help says where each one is.")],
     "removed": [("Shelf", "The Shelf design no longer adds its own icon rail, because every design now has the side menu.")],
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
    {"version": "0.8.0", "date": "5 November 2026",
     "added": [("Set up in the terminal", "./install.sh --terminal asks every set-up question in the terminal, for a server with no desktop and no other device: your password, the apps for your media server and download hours, with Back, help and a plain mode for screen readers."),
               ("Drive pools", "A new Pool tab on System, Storage adds drives to one pool, balances the files, takes a drive out, and makes a drive a backup, with a check of every change before it is made."),
               ("Feedback from the terminal", "Press f at any question to report a problem with that step, and send it as a QR code to scan with your phone, as a link, or as a file."),
               ("What is new in Reelix", "Apps, Updates shows the changes in a waiting Reelix update, from Reelix's own changelog, and says when Reelix has been updated."),
               ("A guide from a bare computer", "Help, Get Starboard up and running: from installing Linux to Docker, then a path for the browser and one for the terminal only, with prompts to ask an AI assistant for help.")],
     "changed": [("The terminal fits the window", "The heading, the progress bar and the menu stay in place while the step scrolls between them, and the QR code holds more of a report in a larger window.")],
     "security": [("The pool helper", "Drive pools need a small helper that runs as root, installed only if you say yes to it. Starboard can only ask it for a fixed set of jobs, each checked first, with your password again, and erasing a drive needs the end of its serial number."),
                  ("Feedback reports", "A report never holds your answers to the set-up, passwords, VPN details or the setup code. Answers you type are kept only as keyed fingerprints for this run, and passwords are not kept at all."),
                  ("Checks", "Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release. One download address is now also checked to be https; ZAP's one signed-in warning was a false alarm, explained in docs/SECURITY-AND-TESTS.md.")],
     "review": [],
     "settings": "Nothing to choose. To use drive pools, run ./install.sh again and say yes to the pool helper (it asks for your password, for sudo). To go back, run ./update.sh --to v0.7.7."},
    {"version": "0.9.0", "date": "5 November 2026",
     "added": [("The Run first script", "Once Linux is installed, one command sets up everything else: it checks the computer, installs what is missing after a yes, downloads Starboard and starts the installer, with accessible mode asked first."),
               ("How to start", "Both set-ups start with the same question: New install, Move from apps you already run, or Restore a backup, recommended from what Starboard finds."),
               ("Storage", "For a new install, where your media goes: the main disk, a separate disk or a pool, and the media folder is made for you."),
               ("Keyboard help", "Help, The terminal: typing commands, says where the symbols in commands are on US, UK, German, French and Spanish keyboards.")],
     "changed": [("One order for both set-ups", "The browser and the terminal ask the same questions in the same order, each decided before what depends on it."),
                 ("The installer asks less", "A new install asks only about your home network and Docker access; the rest comes in the set-up."),
                 ("Text wraps at any size", "Everything in the terminal wraps between words, again when the window changes size, and in plain mode.")],
     "security": [("The set-up and the installer", "Only the options the set-up writes reach the installer, with every folder checked; the setup code is never read through a link; temporary files are private."),
                  ("Host names", "Starboard answers only to this computer's own name, alone or with a home-network ending, which stops DNS rebinding."),
                  ("Checks", "Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release, after a security review of every set-up wizard. Its findings are fixed above; ZAP's two signed-in warnings were false alarms, explained in docs/SECURITY-AND-TESTS.md.")],
     "review": [],
     "settings": "Nothing to choose. New installs use the Run first script; existing ones are not changed. To go back, run ./update.sh --to v0.8.0."},
    {"version": "0.9.1", "date": "5 November 2026",
     "added": [], "changed": [],
     "fixed": [("Updating after a long gap", "./update.sh stopped after listing what changed when more than 30 changes had come since your version. It now lists 30 and says how many more.")],
     "security": [("Checks", "Trivy, OWASP ZAP (signed out), Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release; only update.sh and the help changed since 0.9.0's full checks.")],
     "review": [],
     "settings": "Nothing to choose. Updating from 0.9.0 to 0.9.1 with ./update.sh works as before. To go back, run ./update.sh --to v0.9.0."},
    {"version": "0.9.2", "date": "5 November 2026",
     "added": [("Releases", "Settings, Updates, Releases shows every version in its own section, newest first: the one you have is open, each shows a count for each type of change, then what was added, changed and fixed, in colour."),
               ("Restore", "Settings, Updates, Restore puts back a copy of your settings that Starboard saved, or one from a file, and shows the command to go back to the version before."),
               ("Sign out on every Settings page", "A Sign out button now sits beside the title of every Settings page.")],
     "changed": [("Update settings", "About and updates is now Update settings, one of three pages under Settings, Updates."),
                 ("Help opens the right article", "The Help button at the top of each page opens the help centre article for that page, such as Check your disks' health on Disk health."),
                 ("A wide terminal used evenly", "The Run first script and the terminal set-up draw in a column up to 100 characters wide, centred in a wider window, and move it when the window changes size."),
                 ("Progress bars drawn once", "Each job has one bar, updated in place; when a job fails, its bar stays, marked, with the problem and Try again, Show the details or Stop below it. Install apps shows a moving bar and the time taken in the same way."),
                 ("Choosing several answers in the terminal", "Up and Down move, Space ticks or unticks and Enter carries on. Typing a number still works, and plain mode keeps typed numbers.")],
     "fixed": [("curl installed as a snap", "Docker's installer could not download on Ubuntu when curl was a snap. The Run first script now installs Ubuntu's usual curl beside it and explains the error in plain words."),
               ("The quick start without curl", "Ubuntu Desktop does not include curl, so the README and the help give the same command with wget."),
               ("Disk health installs what it needs", "Choosing disk health no longer stops with install smartmontools first: the installer installs it, and finds it in /usr/sbin.")],
     "security": [("Checks", "Trivy, OWASP ZAP (signed out), Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release and found nothing to fix. The new Restore page asks for your password before it restores, as on Backup.")],
     "review": [],
     "settings": "Nothing to choose. To go back, run ./update.sh --to v0.9.1. Restore your settings from a copy on Settings, Updates, Restore."},
    {
        "version": "0.10.0",
        "date": "7 November 2026",
        "added": [
            ('Reelix in Install apps', 'For a new server, Install apps installs Reelix, one app for films, series, books, audiobooks, music and radio, in place of Radarr, Sonarr, Lidarr, Bookshelf, Prowlarr and Seerr. Servers that run those keep them.'),
            ('Reelix set up for you', "After the apps start, Starboard makes Reelix's admin account with your Starboard password, a manager key for itself, the library folders, and qBittorrent with a password of its own, then shows Reelix's queue and calendar on your dashboard."),
            ('Basics, Full install or Everything', 'Both set-ups start by asking which install you want. Basics is Reelix Lite, Jellyfin, Audiobookshelf, subtitles, and qBittorrent and NZBGet through a VPN; Full install adds the full Reelix and more; Everything is every app. An app also brings what it needs.'),
            ('NZBGet', 'NZBGet is the Usenet app in every install, lighter than SABnzbd, which Full install and Everything offer instead. Starboard makes up its password, sets its folders and connects it to Reelix, and shows its queue and speed, and pauses it with download hours.'),
            ('Settings, Your install', 'Shows what is installed and changes it either way: a bigger or smaller install, NZBGet or SABnzbd, Reelix Lite or full. Your Usenet servers move across from SABnzbd to NZBGet, and the page explains each step.'),
            ('Usenet providers for SABnzbd', 'When you choose SABnzbd, both set-ups list some Usenet providers. They are affiliate links, marked Ad, and the step says to download only files you have the right to.'),
            ('Help for moving to Reelix', 'A new help page says what moves from Radarr, Sonarr and the others into Reelix, what does not, and what to type in afterwards.'),
            ('Passwords kept when the set-up is written again', 'Running Install apps again, or changing your install, keeps the passwords Starboard made up for databases and NZBGet, so they keep working.'),
            ('Help centre on the web', "The help is now web pages, one for each article, with search, a menu of every article, On this page beside each article and the same display settings as the app, at themightytrex.github.io/starboard/help. Help buttons, the set-ups' Help with this step and the terminal's ? help open the article for what you are doing."),
            ('New help pages', 'How Starboard keeps your server safe, What Reelix is, Everything Starboard does, and What the installer asks.'),
            ('Still starting', 'For 15 minutes after apps start, the Apps page says they are still starting instead of showing them as not responding.'),
        ],
        "changed": [
            ('One step list for both set-ups', 'The browser and terminal set-ups read the same step names and order, and offer the recommended answer first.'),
            ('Install apps explains Reelix', 'Start here and the connect guide describe Reelix, a TMDB key and the sites to search, instead of the separate apps.'),
            ('No affiliate note on the VPN step', 'The terminal set-up said some VPN providers had affiliate links in the help; none do, so the note is gone.'),
            ('A shorter README', 'The README now has the quick start, what Starboard does, the three installs, Reelix, installing and security, each linked to the help centre.'),
            ('Storyarr 0.6.1', 'Install apps installs Storyarr 0.6.1 instead of 0.4.8.'),
            ('One password in the browser set-up', 'The password you type to write the files is used again to start the apps.'),
        ],
        "fixed": [
            ('A fresh install ended with no apps running', 'Without Docker access for Starboard, the apps were written but never started. The installer now starts them, and the browser set-up asks the Run first window to.'),
            ('Only some apps reached the dashboard', 'Starboard looked for new apps the moment they started. Both set-ups now keep looking until the list stops growing.'),
            ('Sign out and back in', "On a fresh system the installer's second pass ran outside the new docker group and stopped. It now runs inside it."),
            ('Keys pressed together', 'Over SSH, several key presses could arrive at once and the tick list ignored them. Each key is now read in turn.'),
            ('Text cut at 80 columns', "The installer's explanations, long questions and Docker's messages now wrap at spaces."),
            ("Jellystat's database", "Starboard changed the owner of the database's folder while it was setting up, so Jellystat could never connect. Database folders are now left alone."),
            ('A download that broke off', 'A broken download stopped every app. The installer tries again twice, and the terminal set-up offers Try again or Carry on without them.'),
            ("Ubuntu 26.04's sudo", 'Ubuntu 26.04 shows a star for each letter of the password; the help said nothing shows.'),
            ('qBittorrent 5.1', 'Reelix is connected to qBittorrent again: qBittorrent 5.1 answers a right password differently, so the set-up said it was wrong.'),
            ('NZBGet on the dashboard and in Reelix', 'NZBGet is found and added to the dashboard, its downloads finish in the media folder, and series go to a tv category Reelix uses.'),
            ('SABnzbd', "SABnzbd works as the Usenet app: its own port 8085 beside qBittorrent behind the VPN, the names Reelix uses, downloads in the media folder, a key Starboard made up, and its newer address for Starboard's checks."),
            ('Changes without Docker access', 'After you run the command Settings, Your install shows, Starboard finishes the change: Reelix, the dashboard and moving your Usenet servers.'),
            ('Ports kept', 'Changing your install, or running Install apps again, keeps every app on its port instead of moving it to the next one up.'),
            ('Keys pressed while Run first works', 'Pressing Enter while a step runs no longer repeats the progress bar down the window.'),
        ],
        "security": [
            ('Checks', 'Tests, browser journeys, the help check and the private details check ran on this release. Reelix gets a manager key, never an admin key, and its one-time set-up token is deleted once used.'),
            ('A password to write the set-up', 'Writing the set-up file needs your password, as starting the apps does, because it decides which apps run on the computer.'),
            ('The set-up file is checked before it starts', "The Run first window and ./install.sh --start-apps check the set-up file with Starboard's own rules before starting anything: only the apps Starboard offers, no privileged containers, and folders inside your settings and media folders."),
            ('One change at a time, and smaller reads', "Writing, starting and changing the install take turns; Docker answers over 64 MB are refused; old copies of the set-up are capped at ten; qBittorrent's temporary password is removed once used; NZBGet's sign-in goes only to the NZBGet Starboard set up."),
            ('Scans', 'The six security scanners ran on this release; two warnings from the signed-in web scan were checked and found to be false alarms.'),
        ],
        "review": [],
        "settings": "Nothing changes in apps you already run. To go back, run ./update.sh --to v0.9.2. Restore your settings from a copy on Settings, Updates, Restore.",
    },
    {
        "version": "0.11.0",
        "date": "8 November 2026",
        "added": [
            ('Radio in Starboard', 'Install apps has a Radio group, which makes the radio folder and sets it up in Reelix. Episodes of the radio shows and podcasts you follow show in Coming up, radio downloads show in Downloads, and Discover links to the same search in Reelix radio.'),
            ('One frame for the terminal', 'The installer and the Run first script draw in the same frame, follow the same terminal rules, and redraw when the window changes size while a question waits.'),
            ('Error numbers in the terminal', 'Every way the Run first script and the installer can stop has an error number, such as RF-11, on a line of its own with the address of the help page that explains it.'),
            ('Help in slide-outs', 'Help with this step opens the help article in a slide-out beside the set-up, with square help icons, instead of a new tab.'),
            ('Help pictures for the terminal', 'Run first, the terminal set-up and the error numbers each have three marked-up pictures, and Install apps has pictures of what to set up, the VPN step and the Check table.'),
        ],
        "changed": [
            ('Install apps', 'The VPN step lists each provider with its site, required answers have a star, the Check table is tidier, and starting the apps shows how many are installed, then running.'),
            ('Numbered answers', 'Yes or no questions in the terminal have numbered answers with the recommended one first, in place of [y/N].'),
            ('App by app after Basics', 'Choosing app by app after Basics starts with the Basics groups ticked.'),
            ('Storage counts radio with audiobooks', 'A folder named radio or podcasts now counts as Audiobooks and radio, not Everything else.'),
            ('Storyarr 0.7.0', 'Install apps installs Storyarr 0.7.0, which finds radio from torrent and Usenet sources.'),
            ('The Screen logo', 'The set-up and sign-in pages, the browser tab and the app use the Screen logo.'),
        ],
        "fixed": [
            ('Run first on newer Ubuntu', 'The script stopped with sg: command not found straight after allowing your user to use Docker. It now works without sg.'),
            ('Running the installer straight after Run first', 'The installer stopped with IN-22 because the docker group was not active yet. It now starts itself again inside the group.'),
            ('Keys typed between questions', 'Keys pressed while a job runs or between questions no longer move the lines or show a question twice.'),
            ('The sudo password at the end', 'Applying the changes asks for your sudo password in the window when sudo has forgotten it, instead of stopping with IN-16.'),
            ('Text cut at the edge', 'Stop messages, the checklist hint, the sign-out line, long questions and help addresses wrap instead of running off the edge.'),
            ('A job that keeps failing', 'A failing job is tried three times, then offers Show the details and Carry on.'),
        ],
        "security": [
            ('Checks', 'The unit tests and the help check ran on this release, and the terminal set-up was checked on fresh Ubuntu 26.04 machines at four window sizes. Nothing in this release changes what Starboard can reach.'),
        ],
        "review": [],
        "settings": "Nothing changes in apps you already run. To go back, run ./update.sh --to v0.10.0.",
    },
    {
        "version": "0.12.0",
        "date": "8 November 2026",
        "added": [
            ('Take over the apps you already run', 'On a server set up by hand, Settings, Your install, Apps you already run takes your apps into Starboard. Their settings are copied, never moved, and each keeps its ports, the folders it uses, its devices, its own settings, its version and whether it runs through the VPN.'),
            ('Move your apps into Reelix', 'The same page moves Radarr, Sonarr, Lidarr, Readarr, Prowlarr and Seerr into Reelix through Reelix itself, with each key read from the app, the keys Prowlarr hides read from its database, and qBittorrent connected with its password.'),
            ('Roll back or keep it', 'Before anything stops, Starboard tags every app version and copies your Compose file and its own set-up. Roll back starts your old apps again exactly as they were; Keep it puts the way back aside without deleting anything.'),
        ],
        "changed": [
            ('Your install keeps what each app relies on', 'A later change in Your install keeps the ports, folders, devices and settings of apps Starboard took over, from data/stack/kept.json.'),
        ],
        "fixed": [
            ('Reelix problems on the page', 'When Reelix answers with a problem, the page now says what Reelix said, instead of Something went wrong.'),
            ('Coming up on a phone', 'With many filter chips, such as Reelix radio, the page scrolled sideways on a phone. The chips now scroll in their own row.'),
        ],
        "security": [
            ('Password for every change', 'Taking over, rolling back, keeping and moving into Reelix each ask for your password again, and run one at a time with the other changes to your apps.'),
            ('Secrets stay private', 'Passwords and keys an app had in its Compose file go only in data/stack/.env, which only you can read; data/stack/kept.json holds their names, never their values. Prowlarr\'s database is read into a private temporary folder and removed straight after.'),
            ('Old folders are never written to', 'The takeover only reads your old settings folders, refuses a settings folder inside one of them, and never copies over a folder that has files.'),
            ('Reelix joins your networks only for the move', 'To read your old apps, Reelix joins their Docker networks for the move and leaves them afterwards, even when the move fails.'),
            ('zlib in the image', 'The image takes Alpine\'s zlib 1.4 when it is built, which fixes CVE-2026-4738 (medium) in the base image\'s zlib 1.3.2.'),
            ('Checks', 'The unit tests, the help check, a rehearsal of the takeover and roll back on a stand-in of a real server (98 checks), the browser journeys (36 of 36), and a move of a real server\'s apps into a test Reelix ran on this release.'),
        ],
        "review": [],
        "settings": "Nothing changes until you choose Take over my apps. To go back after a takeover, choose Roll back on Settings, Your install. To go back to the previous Starboard, run ./update.sh --to v0.11.0.",
    },
    {
        "version": "0.12.1",
        "date": "8 November 2026",
        "added": [
            ('Finish setting up Reelix', 'When Reelix runs but its set-up did not finish, Settings, Reelix shows Finish setting up Reelix: your password makes its admin account, Starboard\'s key, its folders and its download apps. Your install sends you there when it is needed.'),
        ],
        "fixed": [
            ('Reelix set up after a start from the browser', 'Reelix stayed waiting for its admin account when Install apps started the apps from the browser, because only the installer read its one-time set-up token. Starboard now reads the token from Reelix\'s log itself, through its Docker access.'),
        ],
        "security": [
            ('Checks', 'The unit tests, the browser journeys and the help check ran on this release. Starboard reads only the Reelix log, and qBittorrent\'s only when it installed qBittorrent itself; the token and password go in data/stack/reelix-setup.json, which only you can read and which is removed once the set-up is done.'),
        ],
        "review": [],
        "settings": "Nothing changes in your apps. To go back, run ./update.sh --to v0.12.0.",
    },
    {
        "version": "0.12.2",
        "date": "8 November 2026",
        "fixed": [
            ('qBittorrent\'s user name', 'Moving your apps into Reelix signed in to qBittorrent as admin, so a qBittorrent with another user name refused the right password. Starboard now reads the user name from qBittorrent\'s own settings, shows it, and gives it to Reelix.'),
            ('Messages under each step', 'On Apps you already run, what happened after Show what moves, Move them into Reelix or Take over my apps appeared at the end of the section, out of sight. Each step now says it under its own buttons.'),
        ],
        "security": [
            ('Checks', 'The unit tests, the browser journeys and the help check ran on this release. Starboard reads one line of qBittorrent\'s settings file, its user name, into a private temporary folder that it removes straight after.'),
        ],
        "review": [],
        "settings": "Nothing changes in your apps. To go back, run ./update.sh --to v0.12.1.",
    },
    {
        "version": "0.13.0",
        "date": "9 November 2026",
        "added": [
            [
                "Reelix's settings in Starboard",
                "Settings, Reelix now shows Reelix's sites to search, media servers and download apps, each with its state, and adds, changes, tests and removes them."
            ],
            [
                "Sites to search",
                "Install apps and the terminal set-up have a new step, Sites to search, with the same questions in both: a short list of Reelix's public sites, none ticked unless you tick them, and your own Torznab or Newznab address."
            ],
            [
                "Searches through the VPN",
                "With the VPN installed, Reelix's searches go out through Gluetun, as Prowlarr's did, and wait when the VPN is down."
            ],
            [
                "Jellyfin and Audiobookshelf in Reelix",
                "Install apps connects Reelix to them with the API keys Starboard already has, so new files show in them at once."
            ],
            [
                "The Library, from Reelix",
                "Library shows everything Reelix holds, as TV, Films, Music, Radio, Books and Audiobooks."
            ],
            [
                "The A to Z list",
                "A row of letters above each wall."
            ],
            [
                "A page for each title",
                "A film, series, artist, radio show, book or audiobook opens its own page with its name, what it is, how much of it you have, and its episodes, albums, reading order or collection, then About."
            ],
            [
                "Groups",
                "Networks for TV, Collections for films, Stations for radio, and Series and Authors for books and audiobooks, each opening the wall with only that group's titles."
            ],
            [
                "Save this view as default",
                "A changed sort, layout, cover size or filter can be saved as how that kind opens, for your account on every device."
            ],
            [
                "Search opens on your library",
                "Before you type, Search shows what was recently added and each kind with its count."
            ],
            [
                "Help",
                "New articles: Change Reelix's settings in Starboard, Choose the sites Reelix searches, Connect Reelix to Jellyfin and Audiobookshelf, and Browse your library; Install apps, Set up in the terminal, Search for and add, and Follow radio shows are updated for the new steps and the new Search."
            ]
        ],
        "changed": [
            [
                "PrivadoVPN's link",
                "In both set-ups, the VPN step's PrivadoVPN link now goes to PrivadoVPN's sign-up page."
            ],
            [
                "Adverts in the help centre take turns",
                "The help centre's advert now shows Newshosting on one page and PrivadoVPN on the next, in turn."
            ],
            [
                "Search in the side menu",
                "On a computer, Search in the side menu now opens the Search page; phones keep the search button and the menu's search box."
            ],
            [
                "TV's second tab",
                "TV's second tab is now Networks, and Radio's Series tab is gone: a radio show's series are on its own page."
            ],
            [
                "Posters on Coming up and the Library",
                "The setting in Settings, Performance now covers the Library's covers too."
            ],
            [
                "The Library keeps a small list of each kind",
                "The Library keeps a small list of each kind in data/library, with only what a wall needs: about 210 bytes a film."
            ],
            [
                "Covers come through Starboard at a small size",
                "Covers come through Starboard at a small size (TMDB w185 on walls), are kept for a week (at most 400), and a missing picture is not asked for again for a day."
            ]
        ],
        "fixed": [
            [
                "Error numbers when a job does not finish",
                "In the terminal set-up, a job that did not finish, such as starting the apps, showed no error number in the boxed look, while accessible mode showed IN-33 only among the details. Both now show the number under the problem, with the address of its help on a line of its own, and Report this problem includes it (DASH-152)."
            ],
            [
                "The installer's own stops",
                "The Run first script showed RF-40 whenever the installer stopped, after the installer's own number, so a stop had two numbers, and some of the installer's stops had none. Every stop of the installer and the terminal set-up now has its own number (new: IN-35 to IN-38), and the Run first script ends on that number. RF-40 is kept for an installer that stopped without one, and stopping it yourself with q or Ctrl+C is no longer shown as an error (DASH-147)."
            ],
            [
                "Waiting for the apps to answer",
                "After starting the apps, the terminal set-up waited the full two minutes, with nothing new on the screen, for apps that had not started, such as qBittorrent behind a VPN that had not connected. It now waits only for the apps that started, and Starboard adds the others itself once they answer (DASH-151)."
            ],
            [
                "The installer's sudo question after Run first",
                "On systems without sg, the installer starts itself again with your new Docker access through sudo, and sudo asked for your password with no word of why. It now says why first."
            ],
            [
                "Long answers in accessible mode",
                "In the Run first script and the installer, accessible mode printed each answer of a question on one line, however long, so in an 80 column window the last letter ran onto a line of its own. Answers now wrap between words inside the window, the rest set in under the number."
            ],
            [
                "The last page in accessible mode",
                "When the set-up in the terminal asked to change this computer, such as for disk health, the Run first script ran the installer again without accessible mode, so the very last page came back with boxes. That run is plain too now."
            ],
            [
                "Docker access on Ubuntu 26.04",
                "When the installer starts itself again with your new Docker access through sudo, Ubuntu 26.04's sudo (sudo-rs) dropped all of Starboard's settings, so the second run lost accessible mode and the Run first script lost the installer's error number. The settings now go across by name."
            ],
            [
                "The last card in a narrow window",
                "At the end of the set-up in the terminal, a window 60 columns wide cut the card's labels short, such as \"On your other devic\", and a long folder ran past the card's edge. In a narrow window each label now has its own line with the value under it, and a word too long for the line is broken inside the card."
            ],
            [
                "The VPN list at 80 columns",
                "In the set-up in the terminal, PrivadoVPN's address in the VPN list ran past the right edge of a window 80 columns wide. When an address is too wide for its column, each provider's address now goes on the line under its name."
            ],
            [
                "Keys pressed while a job runs in accessible mode",
                "An Enter pressed while a job ran answered the next question with its default. It is now thrown away when the job ends, as in the boxed look."
            ],
            [
                "Live TV channels that would not play",
                "Jellyfin's FFmpeg refuses Live TV pieces whose address has no file ending, such as the ad links on Samsung TV Plus channels like U&Laughs, so 107 channels stopped playing. Install apps now runs Jellyfin's FFmpeg through a small Starboard file, jellyfin/ffmpeg-wrap/ffmpeg in your settings folder, which allows those addresses for Live TV only. Your library files and On demand links are played as before. Starting the apps, from Starboard, from the installer or by taking over your apps, puts the file in place, so running the guide again keeps the fix (DASH-169)."
            ],
            [
                "Error IN-34",
                "If the installer cannot put that file in Jellyfin's settings folder, it stops with error IN-34 rather than start a Jellyfin that cannot find FFmpeg."
            ],
            [
                "Taking over Reelix while it reports a problem",
                "Reelix says it is unhealthy while a download app it was given cannot be reached, which is often what the takeover is about to fix. Starboard now carries on instead of waiting for it."
            ],
            [
                "Old apps left on the Apps page after a takeover",
                "apps added before Starboard marked its entries were not recognised, so Radarr and the others stayed on the Apps page. They are now found by their kind or name and taken off. Reelix's own entries are kept."
            ]
        ],
        "security": [
            [
                "Only image sites",
                "Starboard fetches covers only over https from TMDB, Open Library and Cover Art Archive, or from Reelix itself, and follows a redirect only to another of those sites."
            ],
            [
                "Checks",
                "The unit tests (467), the browser journeys, the help check, the private details check and the security scans ran on this release; the terminal set-up was tested on test machines before it was merged."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your apps until you use the new steps. Install apps now turns on Gluetun's proxy so Reelix can search through the VPN. To go back, run ./update.sh --to v0.12.2."
    },
    {
        "version": "0.13.1",
        "date": "9 November 2026",
        "added": [
            [
                "Reelix's warnings in Starboard",
                "Apps, each app's details and System now show Reelix's own warnings, such as a site to search that keeps failing or a download app it cannot reach, each with a link to the place in Starboard that puts it right. Reelix's Sonarr- and Radarr-style health answer is always empty, so Starboard now asks Reelix's own health check."
            ],
            [
                "Tdarr on the dashboard",
                "A Full install's Tdarr is found and shown like the other apps."
            ]
        ],
        "changed": [
            [
                "One Reelix card",
                "Apps shows Reelix once, with the queue, wanted and update of films, series, books and music together, instead of a card for each kind."
            ],
            [
                "Reelix's logo",
                "Reelix's card shows its own logo, from the running Reelix, as the icon collection has none."
            ],
            [
                "FlareSolverr",
                "Reelix uses FlareSolverr whenever it is installed, through the VPN when there is one, not only when searches go through the VPN."
            ],
            [
                "Reelix never updates itself",
                "The set-up keeps Reelix's own installing of updates off, because Starboard updates Reelix on Apps, Updates."
            ],
            [
                "Starboard runs Reelix",
                "The set-up guides, messages and help now send you to Settings, Reelix in Starboard, not Reelix's own pages. The free TMDB key is the one thing still added in Reelix itself, until a later version asks for it."
            ],
            [
                "SABnzbd in the set-up guide",
                "The guide no longer asks you to set SABnzbd's folders, API key and Reelix connection by hand on the wrong port; Starboard already does all three."
            ],
            [
                "Help for going back to Reelix without YouTube and Spotify downloads",
                "The help for switching versions says what stops working when you go back."
            ],
            [
                "Accessible mode in the terminal",
                "Accessible mode says \"Still working\" every 2 minutes during a long job, such as downloading the apps, so a screen reader is never silent for long."
            ]
        ],
        "fixed": [
            [
                "Reelix's sites after a restart",
                "Reelix now starts once the VPN is ready, so its searches no longer fail for five minutes after the server restarts."
            ],
            [
                "Apps that keep restarting",
                "After starting the apps, the installer looks again a few seconds later, so an app that keeps restarting, such as a VPN with a wrong key, is no longer counted as running."
            ],
            [
                "A long row of filter chips",
                "A long row of filter chips on a phone now scrolls inside its toolbar, not the whole page."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (483), the browser journeys (67), the help check, the private details check and the security scans ran on this release. ShellCheck is clean again: it now follows the shared terminal frame, where the variables it called unused are read."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your apps. A new install starts Reelix once the VPN is ready. To go back, run ./update.sh --to v0.13.0."
    },
    {
        "version": "0.13.2",
        "date": "9 November 2026",
        "added": [
            [
                "Update in the side menu",
                "The version is now at the bottom of the side menu, and when a newer Starboard is out, Update with a dot shows above it, linked to About and updates; the footer's About and updates says (1) too."
            ]
        ],
        "changed": [
            [
                "The footer",
                "The footer is the design system's: Starboard's name and logo, then Help, Release notes, GitHub repository and About and updates, with the TheMightyTRexUK mark on the right."
            ],
            [
                "Reelix's updates come from your fork",
                "Apps, Updates checks the Lite or full image Starboard installed, from TheMightyTRex's Reelix, and its What is new reads that branch's changelog; Reelix's own check of upstream's releases is no longer shown."
            ]
        ],
        "fixed": [
            [
                "Reelix's logo",
                "Reelix's logo now shows on its card on servers where Starboard had looked for an icon before 0.13.1 and found none."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (486), the browser journeys (67), the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your apps. To go back, run ./update.sh --to v0.13.1."
    },
    {
        "version": "0.14.0",
        "date": "10 November 2026",
        "added": [
            [
                "Plug-ins",
                "Settings, Plug-ins adds a plug-in from its address, its file or its own installer, shows what it may do with a risk level and its test results first, and activates, deactivates or removes it, keeping its folder."
            ],
            [
                "Styles from plug-ins",
                "A plug-in can add styles to Display, which Starboard checks for accessibility in light and dark and draws itself; the Styles plug-in has eight, each with a picture to choose from."
            ],
            [
                "Plug-in tester",
                "Test a plug-in lists every issue with where it is and how to fix it, and always tests accessibility; the same tests run before any plug-in is added."
            ],
            [
                "Plug-in cards",
                "Plug-ins can add cards to the dashboard that show a number, a list or a status, asked at most once a minute."
            ],
            [
                "Starboard's API",
                "A read-only API at /api/v1 for other apps, scripts and AI assistants, with its own keys made in Settings, Security and a published description."
            ],
            [
                "The dashboard",
                "A dashboard of cards is the first page after signing in, in four layouts, with Edit dashboard to add, size and move cards."
            ],
            [
                "Library actions",
                "Film and series pages have Get it, Follow, Stop following, Delete, Choose a download and watched or not watched from Jellyfin."
            ],
            [
                "Wanted, History and Issues",
                "Wanted shows what is missing or below the quality wanted, with Search; History and Issues are real pages; Requests shows Reelix's own requests."
            ],
            [
                "Download now",
                "Wanted items can download straight away, outside download hours."
            ],
            [
                "Basic and advanced settings",
                "Every Settings page opens on its basic settings, with an Advanced settings switch for the rest."
            ],
            [
                "Settings, Downloads",
                "A new page for the VPN, the Usenet server and download hours, with Test buttons."
            ],
            [
                "Reelix's settings, backups and logs",
                "Settings, Reelix covers its basics, folders, information, files and requests; System has Reelix's backups and log; Reelix can update automatically, off until you switch it on."
            ],
            [
                "YouTube and Spotify",
                "With the full version of Reelix, downloads from a YouTube or Spotify link, with Connect Spotify."
            ],
            [
                "Apps set up for you",
                "Jellyfin, Audiobookshelf, Jellystat, qBittorrent, Bazarr and Gluetun are set up by Starboard, and Live TV's channels and guides are added to Jellyfin by itself."
            ],
            [
                "Guided steps",
                "The set-up checklist has short guided steps with Done for Tdarr, Wizarr, Dispatcharr and Soulseek."
            ],
            [
                "More apps",
                "Soulseek through slskd and the No-IP updater in Install apps; FlareSolverr is offered only when a site needs it."
            ],
            [
                "The graphics chip",
                "Jellyfin uses an Intel or AMD graphics chip to convert video when the computer has one."
            ]
        ],
        "changed": [
            [
                "One set-up in each place",
                "The browser and terminal set-ups ask the same questions in the same order, including the TMDB key, the Usenet server, sites to search and the VPN."
            ],
            [
                "First set-up only",
                "A new Starboard shows only the set-up until it is finished."
            ],
            [
                "Wizarr and Dispatcharr",
                "They are add-ons in Install apps instead of part of the Full install. Installs that have them keep them."
            ],
            [
                "Long lists",
                "Library walls, Wanted and History load more as you near the end."
            ],
            [
                "Plug-in words",
                "Plug-ins are activated and deactivated, in the house style."
            ]
        ],
        "fixed": [
            [
                "Test scripts after the dashboard",
                "The help pictures, screenshots and browser journeys wait for the dashboard after signing in."
            ]
        ],
        "security": [
            [
                "Settings by risk",
                "Each general setting has a level of access; network access, secure cookies, session length and the alert channel can never be changed by an API key."
            ],
            [
                "Addresses Starboard calls",
                "Link-local and cloud metadata addresses are refused, and a request carrying an app's key never follows a redirect to another server."
            ],
            [
                "Sign out everywhere",
                "It now asks for the password, so a session someone else has cannot sign everyone out."
            ],
            [
                "API keys",
                "Keys are shown once, stored only as a SHA-256 hash, sent only in a header, and every change is in an audit log."
            ],
            [
                "Plug-ins locked down",
                "Plug-ins never get the Docker socket, the host network, devices or other apps' folders; containers are read only, without capabilities, not root and limited in memory and processor."
            ],
            [
                "Checks",
                "The unit tests (600), the browser journeys (66), the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [
            "apps"
        ],
        "settings": "Your apps keep running as they are. New apps and guided steps are offered, never added on their own. To go back, run ./update.sh --to v0.13.2."
    },
    {
        "version": "0.14.1",
        "date": "10 November 2026",
        "added": [
            [
                "Choose now",
                "When an upgrade has something to choose, Choose now opens those choices in a slide-out over the page you are on; Open as a page still opens the full guide."
            ]
        ],
        "fixed": [
            [
                "API error links",
                "The links in the API's error answers open the new errors page in Starboard's repository."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your apps. To go back, run ./update.sh --to v0.14.0."
    },
    {
        "version": "0.15.0",
        "date": "10 November 2026",
        "added": [
            [
                "Live TV as a plug-in",
                "Live TV comes with Starboard as a built-in plug-in: add it in Settings, Plug-ins, with its own card, settings and Run Live TV now. It runs locked down on Starboard's own image."
            ],
            [
                "Waiting for Linux's updates",
                "Run first waits with a progress bar while Linux installs its own updates, and tries again by itself if they start part-way, instead of stopping with error RF-12."
            ]
        ],
        "changed": [
            [
                "Your Live TV moves by itself",
                "If Live TV was on, Starboard moves it into the plug-in on its first start, with the same settings and folder; Jellyfin's channels and guides do not change. Where the plug-in cannot run, Live TV stays in Starboard as before."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Live TV moves into its plug-in by itself. To go back, run ./update.sh --to v0.14.1, then switch Live TV on again in Settings, Apps, Jellyfin."
    }
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
    for heading, key in (("Added", "added"), ("Changed", "changed"), ("Deprecated", "deprecated"), ("Removed", "removed"),
                         ("Fixed", "fixed"), ("Security", "security")):
        if release.get(key):
            out += [f"## {heading}", ""] + [f"- **{t}.** {s}" for t, s in release[key]] + [""]
    out += ["## Your settings and the way back", "", release["settings"], ""]
    return "\n".join(out)
