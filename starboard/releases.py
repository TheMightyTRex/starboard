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
    },
    {
        "version": "0.15.1",
        "date": "10 November 2026",
        "fixed": [
            [
                "Live TV's move",
                "Starboard's container now knows where the Live TV folder is on the computer, so Live TV moves into its plug-in as 0.15.0 meant to."
            ],
            [
                "Live TV and newer Jellyfin",
                "Live TV sends Jellyfin's key the way Jellyfin 10.11 and later expect, so it can add its channels and guides there."
            ],
            [
                "No channels twice",
                "When Live TV moves, it reads the folder from Jellyfin's own tuners, so it never adds the same channels again under another path."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Live TV moves into its plug-in by itself on the next start. To go back, run ./update.sh --to v0.14.1, then switch Live TV on again in Settings, Apps, Jellyfin."
    },
    {
        "version": "0.15.2",
        "date": "10 November 2026",
        "added": [
            [
                "Send feedback everywhere",
                "Send feedback, with Snaglist 0.4.0 and its QR code reports, is now on every page by default; deactivate it in Settings, General."
            ]
        ],
        "fixed": [
            [
                "Language and Region in Settings, Reelix",
                "Language of details and Region are lists with plain names, one choice each, and an empty Region no longer stops Information saving."
            ],
            [
                "Plug-in styles before signing in",
                "The sign-in page loads a chosen plug-in style without an error."
            ],
            [
                "Region and language in Settings, Reelix",
                "Saving Information with Region empty no longer fails with \"not in the form it needs\"; Language of details and Region are now lists with plain names, one choice each, as Reelix uses."
            ],
            [
                "Plug-in data folders",
                "Starboard makes each plug-in's data folder for the user the plug-in runs as, so a plug-in can save its work; Live TV's first run on a real server could not."
            ],
            [
                "Plug-in cards and buttons",
                "Starboard finds a plug-in at its address when it uses the computer's own network, so cards and buttons such as Run Live TV now answer."
            ],
            [
                "Built-in plug-ins' health",
                "Built-in plug-ins check their own health instead of Starboard's, so Docker no longer marks them unhealthy."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Live TV starts its first run as a plug-in. To go back, run ./update.sh --to v0.15.1."
    },
    {
        "version": "0.15.3",
        "date": "10 November 2026",
        "fixed": [
            [
                "Built-in plug-ins follow Starboard's updates",
                "Each time Starboard starts, its built-in plug-ins, such as Live TV, are set up again from the new version and started again, so they get its fixes."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. To go back, run ./update.sh --to v0.15.2."
    },
    {
        "version": "0.15.4",
        "date": "10 November 2026",
        "added": [
            [
                "Still to set up, one at a time",
                "Go through them opens a slide-out that walks through each thing left to set up, with Do it now, Skip, Ignore, Done and Next step. It also opens by itself once in each browser session while anything is left."
            ],
            [
                "Plug-in install addresses and downloads",
                "The plug-in collection in the help centre now gives each plug-in's install address, to paste into Add a plug-in, and a zip to download. The Styles plug-in lives in Starboard's own repository, under plugins-collection."
            ]
        ],
        "fixed": [
            [
                "Links to apps in Still to set up",
                "Links in Still to set up, such as Tell Tdarr what to convert, open at the address you opened Starboard at, instead of 127.0.0.1, which another device cannot reach."
            ],
            [
                "Waiting for Linux's updates",
                "Run first no longer waits for Ubuntu's always-running shutdown helper as if it were updates, and its bar now says what is installing, how many are done and how much is downloaded."
            ],
            [
                "Done on guided steps",
                "Done on a guided step, such as Tdarr's, now saves instead of failing."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your apps. Ignored items can be brought back on Apps. To go back, run ./update.sh --to v0.15.3."
    },
    {
        "version": "0.15.5",
        "date": "10 November 2026",
        "added": [
            [
                "Send feedback in the side menu",
                "Feedback is now an item at the foot of the side menu, and on a phone a row in the menu, instead of a button floating over the page. Pages with no side menu, such as the set-up, keep the button in the corner."
            ]
        ],
        "fixed": [
            [
                "The ready-made image",
                "The ready-made Starboard image builds again. Since 0.15.2 a test that only passed on one computer stopped GitHub building it, so installs from the image stayed on 0.15.1."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. To go back, run ./update.sh --to v0.15.4."
    },
    {
        "version": "0.16.0",
        "date": "10 November 2026",
        "added": [
            [
                "Nothing to set up outside Starboard",
                "The installer adds Docker when it is missing, Starboard reads each app's API key itself (Jellyfin, Audiobookshelf, Bazarr, NZBGet and others), and a small set-up helper on the server starts the apps and makes the set-up's changes, so the Run first window can close."
            ],
            [
                "Make the change now",
                "The set-up's last page makes its change to the server for you, after your Starboard password, with a progress bar and the installer's words live in a slide-out."
            ],
            [
                "Still to set up, done in place",
                "Each of Starboard's own steps opens its page inside the slide-out, at the right part, so the set-up is done there; Next step checks again and drops a step that is done."
            ],
            [
                "Picture quality in full",
                "Settings, Reelix, Picture quality: choose a level, see what it does in plain words, and under Advanced settings put its qualities in order, tick the ones to accept, move Stop upgrading here, and set extras to Prefer, Neutral or Never."
            ],
            [
                "The folder picker",
                "Folders are chosen with Browse, and each one is checked as you type: whether it is there, which disk it is on and how much is free."
            ],
            [
                "App logs",
                "System, Logs shows each app's own log, so Dozzle is no longer needed."
            ],
            [
                "New releases in Alerts",
                "A short weekly line through Alerts when a new Starboard is out."
            ],
            [
                "Graphics chip found everywhere",
                "The browser set-up also finds an Intel or AMD graphics chip for Jellyfin when Starboard runs in Docker."
            ],
            [
                "A simpler help centre",
                "Every article checked against this version, simpler, and linked to the exact part of each area it mentions, with six new articles: Find a setting, Finish setting up, Get what is missing, Live TV channel will not play, Use Starboard's API and Use the dashboard."
            ],
            [
                "Plug-ins in their own place",
                "The plug-in collection lives at github.com/TheMightyTRex/starboard-plugins, with each plug-in's install address and zip."
            ]
        ],
        "changed": [
            [
                "Add-ons",
                "Dozzle, Wizarr and Dispatcharr are add-ons you tick in Install apps, not part of the Full install."
            ],
            [
                "The setup code",
                "Filled in from the installer's link, it is read only, with a note that Starboard uses it to continue."
            ],
            [
                "Run one command",
                "When a command is still needed, it always shows, and the page says to run it in a terminal on the server."
            ]
        ],
        "fixed": [
            [
                "Out-of-date words",
                "Thirteen places in Starboard's pages said where things used to be, such as Send feedback in the corner; they say where things are now, and links to parts under Advanced settings show those parts."
            ],
            [
                "Settings, Reelix with Reelix Lite",
                "The word null no longer shows between Basic settings and Sites to search."
            ],
            [
                "Pages in a slide-out",
                "The upgrade guide opened inside Starboard only on its first visit; it now opens every time."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (also as another user, as GitHub runs them), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release. The set-up helper runs as your user and cannot use sudo."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your apps. Dozzle stays if you have it. To go back, run ./update.sh --to v0.15.5."
    },
    {
        "version": "0.16.1",
        "date": "10 November 2026",
        "added": [
            [
                "The set-up helper with updates",
                "A server set up before 0.16.0 gets the set-up helper with this update, and later updates keep it. ./install.sh --no-starter turns it off for good, until ./install.sh --starter."
            ]
        ],
        "fixed": [
            [
                "Memory that grew with use",
                "Starboard kept every answer it had fetched for each search, item page and calendar range until it restarted, so its memory grew the more it was used. It now forgets answers once they are out of date and keeps at most 200. On the example server, 2,000 searches no longer add any memory."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. To go back, run ./update.sh --to v0.16.0."
    },
    {
        "version": "0.16.2",
        "date": "10 November 2026",
        "changed": [
            [
                "TV networks as a grid",
                "Library, TV, Networks shows each network as a square card with its logo, its name and how many series it has; a network's own page shows its logo too."
            ],
            [
                "The A to Z bar",
                "Letters with titles are filled buttons and letters with none are plain grey, so you can see at once which letters have anything."
            ]
        ],
        "fixed": [
            [
                "Posters slow to show",
                "Starboard keeps a poster for every item in every library (it used to keep 400, fewer than a larger library has), fetches missing ones in the background when a list is rebuilt, and no longer lets the browser remember a busy image site as no picture for an hour. Reported in issue #5."
            ],
            [
                "Network logos cut off",
                "A wide logo now fits inside its card, and logos are drawn in greys rather than flat black, so white words inside a shape (Cinemax, ABC) stay readable. Reported in issue #4."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. To go back, run ./update.sh --to v0.16.1."
    },
    {
        "version": "0.16.3",
        "date": "10 November 2026",
        "added": [
            [
                "Radio shows you already have",
                "Library, Radio brings in the radio shows already in Audiobookshelf's Radio library: Starboard finds each one on Reelix's radio sources, ticks it when the title is the same, adds it, and asks Reelix to search for the episodes you do not have. Settings, Reelix, Radio connects Reelix to that library first, with the folder Audiobookshelf itself reports."
            ]
        ],
        "fixed": [
            ["Still to set up keeps steps you did elsewhere", "Add a TMDB key and Point Reelix's radio at Audiobookshelf now go once Reelix has them, wherever they were done, not only from the set-up wizard. Radio is one step instead of two."],
            ["Folders of shows already in your library", "When bringing in films or series from disk, a folder whose match is already in your library (in another folder) says so and is unticked. Unticked folders are left out and no longer counted on Still to set up."],
            [
                "Radio set-up on older servers",
                "Set-up pointed Reelix's radio at /media/radio even where Audiobookshelf uses another folder, such as /radio; it now uses the folder Audiobookshelf reports."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. To go back, run ./update.sh --to v0.16.2."
    },
    {
        "version": "0.16.4",
        "date": "10 November 2026",
        "added": [
            [
                "Reset style",
                "Display has a Reset style button under the style list, and Settings, General has a Style section saying which style this browser uses, with Reset style and Choose a style. Reset style goes back to Starboard's standard colours and keeps your other Display choices."
            ]
        ],
        "fixed": [
            [
                "Live TV guides that ran out",
                "Samsung TV Plus's guide covers about ten hours, so refreshing once a day left its channels empty by the evening. A guide is now fetched again when it has under 12 hours left, and Jellyfin reads new guides straight away."
            ],
            [
                "Each guide with its own channels",
                "With every guide set for every channel list, Jellyfin took programmes from the first guide only. Live TV now links each guide to its own list in Jellyfin, and puts right set-ups made before."
            ],
            [
                "Display's Reset left the style ticked",
                "Reset in Display now also unticks a style from a plug-in."
            ],
            [
                "Bringing in radio shows looked stuck",
                "Finding your radio shows on Reelix's sources searched one show after another, which could take minutes with nothing on screen. It now searches five at once, ten to a page, and the button says it is finding them."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. To go back, run ./update.sh --to v0.16.3."
    },
    {
        "version": "0.16.5",
        "date": "11 November 2026",
        "added": [
            [
                "Audiobooks and books already on disk",
                "Library, Audiobooks and Library, Books bring in the author folders already on disk through Reelix, each author matched on Open Library and following only the books you have, so Reelix never wants everything an author wrote. A folder is ticked only when the match is certain; the rest wait for you. Also in Still to set up."
            ],
            [
                "Styles that change more",
                "A style from a plug-in may now also set the side menu, panel headers, the chosen button, count badges, status messages, chart colours and the logo, a heading font and weight, a thicker focus ring, more shadows, gradients and soft glows, textures (grain, dots, grid, lines), glass panels and rounded buttons and fields. Every colour text can sit on is checked for contrast (WCAG 2.2), glass panels as they look over the page behind them; Display's high contrast and a device set to reduce transparency turn the effects back to solid colours. Styles 1.1.0 uses them, with five new styles."
            ]
        ],
        "changed": [
            [
                "Plug-in API 1.1",
                "Plug-ins may ask for starboard_api >=1.1 to use the wider styles; plug-ins made for 1.0 work as before."
            ]
        ],
        "security": [
        ["Image packages", "The image now takes every Alpine package's fixed version when it is built. This one fixes 16 high and 5 medium problems in krb5-libs (fixed in 1.22.3), found by the release's security scan."],
            [
                "Checks",
                "The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check, the screenshots and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. To go back, run ./update.sh --to v0.16.4."
    },
    {
        "version": "0.17.0",
        "date": "14 November 2026",
        "added": [
            [
                "Starboard's API 1.1.0",
                "The API now reads everything the pages show (Coming up, requests, speeds, download hours, history, the Library and its search, uptime, app updates, containers and more), and a second right, Read and manage, covers the everyday actions: approve or decline a request, pause or resume downloads, remove or block a download, build a Library tab again, look for container updates, run a Jellyfin job and send a test alert. /api/v1/events streams app changes and alerts as they happen. Make a key asks what each key may do and what it may see."
            ],
            [
                "Developer help and AI assistants",
                "The help has a Developers section with the plug-in and API references (the API reference built from the API description), a quick start, a page listing what the API covers for every action on the pages, and Connect an AI assistant, which gives an assistant its own Read only key with the fewest scopes. /api/v1/logs gives Starboard's log with addresses, names and keys taken out, only to keys with Logs ticked."
            ],
            [
                "App plug-ins",
                "A whole app can now come as a plug-in, kept apart from the main install, such as Jellystat with its database: it gets its own page on your home network at a port Starboard chooses, its own passwords made once for your server, and Remove asks where its folder goes. A plug-in can also copy an app you already run, such as Tdarr, into itself, without removing the old one. The Catalogue has a group, Apps you can add."
            ],
            [
                "Plug-ins you can trust and update",
                "Adding a plug-in first shows what it can see, change and reach, with Install and Cancel; its menu items appear only once it is added. Settings, Plug-ins has Manage, the Catalogue (sources can be added from a link) and a page for each plug-in. Catalogue versions are checked against their checksums, State shows each plug-in's version and What is new after an update, and Update, Roll back and Update from an address are on Versions. A plug-in that stops answering says Not answering, and one that is idle rests until it is needed."
            ],
            [
                "Plug-ins can do more (plug-in API 1.2 to 1.13)",
                "Plug-ins may now restyle the whole of Starboard (up to 32 styles), use a folder inside the media folders they mount, set up before they are activated, hear events and run jobs, lay out their settings in sections, use Reelix's key and your news server when you approve it, draw their own screens with menus, folding tables, filters, links and file uploads, put a VPN app's port on Gluetun for your home network, add files to your media folders as the media folder's owner (never as root) and run whole apps. Plug-ins made for API 1.0 and 1.1 work as before."
            ],
            [
                "Discover by area",
                "Discover has a page each for Films, TV, Music, Radio, Books and Audiobooks, from Reelix's own lists. Settings, General, Discover rows chooses each area's rows and their order, including a row for each genre (such as Comedy or Science fiction) for films, series and radio. Recently added follows what arrived, so new episodes come first, On demand history shows what you started watching, with Add to wanted and Remove, and pictures are kept for four weeks, with Clear the picture cache in Settings, Performance."
            ],
            [
                "Discover, Radio",
                "One search across every radio source, with From radio stations and Podcast feeds only; the genres the sources share as chips; every BBC station in a picker by group; and each source's own categories under More categories."
            ],
            [
                "Search filters and Search the sites",
                "Search filters results by whether they are in your library, kind, year or decade, genre, status (Have it, Missing, Downloading, Below the quality wanted), released or coming soon, followed or not, language, rating and radio source, and remembers them for your account. Search the sites is its own page: one search across the sites Reelix searches, to compare size, seeders and age, with Get this one."
            ],
            [
                "Complete collections and series",
                "An opened film collection shows every film in it, and audiobook and book series come from Audiobookshelf with the missing books from Audible, each with Add missing. Books, Series and Authors are banners like audiobooks, covers of anything not in your library yet are faded behind a dashed outline, and Library, Audiobooks, Narrators lists everyone who reads your audiobooks, with a page each."
            ],
            [
                "More in the Library",
                "Books, music and podcasts have their actions: Quality and folder, Select several, Files and history, and Podcasts and Keep. Change match searches for the right title and moves the item in Reelix with its files kept, or puts the old match back. Library, Radio, Stations is a square grid like TV networks."
            ],
            [
                "Bring in music, and folders nobody lists",
                "Library, Music brings in the artist folders already on disk, as films, series, books and audiobooks do, each artist following only the albums you have. A folder with no match, such as a home video, can come in with your own title, year, description and picture once Reelix can take it (Reelix task RFX-90)."
            ],
            [
                "Downloads and Wanted",
                "Activity, Downloads lists Held downloads, the releases a delay profile is holding back, with Get it now and Remove; Choose the episode handles files Reelix refused for their episode number; and paused unpacking in NZBGet is said, with Resume unpacking. Wanted has an item for each media type with Missing and Below the quality wanted, and each film or episode has Details with what Reelix last did and See what Reelix can find. History has Keep history for and Delete history."
            ],
            [
                "More of Reelix in Settings",
                "Settings, Reelix has Tags, Path mappings and Site list updates; Reelix's health shows a broken yt-dlp or FFmpeg, an expired Spotify sign-in and YouTube downloads that keep failing. Settings, Radio has Your podcast library (files Reelix has not matched, with Match by hand), Add a show from a link, and a Catch-up downloads switch for each source that has catch-up."
            ],
            [
                "Live TV, your own channel lists",
                "Live TV takes your own M3U or JSON channel lists and XMLTV guides, by address or as a file up to 60 MB, each with Activate, Deactivate, Test and Remove, and adds them to Jellyfin as one more tuner. Channels fold into sections by list, region and section, each with its own switch and a table to sort, filter and tick several; a list longer than 2,000 channels says only the first 2,000 are read. The dashboard can show On TV now, and logos stay legible."
            ],
            [
                "Dispatcharr from Starboard",
                "Settings, Apps, Dispatcharr sets up the Dispatcharr add-on without opening it: its admin and a key, your IPTV playlist or Xtream Codes server and guide, the channels, and Dispatcharr in Jellyfin as a tuner with its guide."
            ],
            [
                "Tdarr from Starboard",
                "Starboard gives Tdarr its key, and its settings have the basic choices: which libraries, save space or check only, how many at once, and any time or in quiet hours. With the Tdarr plug-in, films and series are converted in a folder on the media disks, so working copies never fill the system disk."
            ],
            [
                "Recommended Jellyfin plug-ins",
                "Settings, Apps, Jellyfin offers skipping intros and credits (from downloaded times, or analysed here in quiet hours only), Playback Reporting, Merge Versions and Trakt, each installed and set up through Jellyfin and shown with its version. Choosing another deactivates the old one; nothing is uninstalled."
            ],
            [
                "Kavita in Install apps",
                "Kavita, the ebook reader, is in the Ebooks group. It reads the media folder only and has a Still to set up step."
            ],
            [
                "Full backups without media",
                "System, Backup and restore makes a full backup of Starboard, its plug-ins, the set-up files and every app's settings and database, encrypted with a password you choose, on another disk, keeping the newest 5; it says which disk and warns when the folder is on the system disk. When backups are made can be Manual, Weekly or Nightly, and Copies off this computer sends each backup to another disk, a network share or your own rclone remote. A backup restores onto a fresh install in both set-ups."
            ],
            [
                "Clean up",
                "System, Clean up lists what is left over (removed plug-ins, an unfinished backup's work folder, older update copies) with sizes and moves what you choose to the holding folder, where each thing can be put back, or deleted for good after you confirm with your password. Settings, Updates, Restore keeps the copies of the last 5, 10 or 20 versions."
            ],
            [
                "After an unexpected shutdown",
                "After a power cut or a crash, Starboard checks once the folders it watches, the pool, any pool job or full backup that stopped part way, and the apps, then says what it found on System, Overview and through Alerts."
            ],
            [
                "Server care from the terminal",
                "./settings.sh changes settings through Starboard with your password, starting with automatic updates, and sudo deploy/headless.sh readies a computer to run with no screen (never sleeping, the lid ignored, starting again after a crash), showing each change first and with --undo to put them back."
            ],
            [
                "Where you are and your keyboard first",
                "The Run first script and both set-ups ask where the computer is and which keyboard it has, as lists you move through with the arrow keys, then set the time zone, keyboard layout and language; the apps take the time zone. The keyboard step says where symbols such as |, \\ and # really are on UK, Irish, German, French, Spanish and Italian keyboards."
            ],
            [
                "Audio description in the first set-up",
                "Both set-ups' Jellyfin extras step offers Audio description, unticked. Ticking it makes Settings, Plug-ins offer the Audio description plug-ins from the Catalogue; Not now forgets it."
            ],
            [
                "Own style colours and design pictures",
                "Starboard's own style has six colours to choose from: Teal (the standard), Indigo, Forest, Plum, Ember and Graphite; Reset style comes back to them, and the own style comes first in the Styles gallery. Default design and Display's Design list show a small picture of each design."
            ],
            [
                "Moving in from other apps, step by step",
                "Move them into Reelix, Take over my apps, Roll back and Clear away open a dialog with each step and its result, and carry on if it is closed. Install apps can do the move too, more site keys are read for you, and after the move you can review the held sites, add titles that did not match (they wait with their IDs and are added once they match), choose Reelix's own requests or keep Seerr, and clear away the apps Reelix replaced into a holding folder."
            ],
            [
                "Restart in Manage apps",
                "Each app's menu has Restart. Restarting Gluetun also restarts the apps that use its network."
            ],
            [
                "Comparisons in the help",
                "A new help section compares Starboard's stack with other media server stacks, with the memory and processor measured at rest, how the tests were run and how to repeat them."
            ]
        ],
        "changed": [
            [
                "Settings pages on the second menu",
                "The parts of Settings, General (now Names and apps, Appearance, Pages and lists, Download hours, and Logs and feedback), Downloads (VPN, Usenet, Download hours), Radio, Performance and Security are each a page of their own on the second menu, and each page asks only for what it shows. Style is now Appearance, with the accessibility options. Old links still work."
            ],
            [
                "Settings that work the same everywhere",
                "Every folder is chosen with the location picker; switches and choices apply at once with a saved note beside them instead of a pop-up message; typed text has one Save per section; lists such as Reelix's sites and API keys are rows that open; and danger zones come last."
            ],
            [
                "The same item for the same job everywhere",
                "Across Apps, the Dashboard, the Library, Discover, Coming up, Activity, System and Install apps: app cards show at most two chips and one button, filters that pick one of several are segmented controls, a state sits on its title's line, lists open in slide-outs instead of dialogs, and one primary button is in view. Apps, Updates updates the apps you tick, and Still to set up has one button and shows only the part each step needs."
            ],
            [
                "Both set-ups ask the same questions",
                "The browser and terminal set-ups ask the same things in the same order, with the same words. Let me choose starts from the recommended apps (Basics), films are Films, not movies, and Reelix's set-up code is read for you so you never see a second code. The set-ups now warn when the apps ticked need more memory than the computer has, leave out apps that do not run on a Raspberry Pi, and stop on a 32-bit system or with under 10 GB free."
            ],
            [
                "Lighter on memory and processor",
                "Heavy jobs (the watch history import, listening progress, Live TV and building Library lists) run in a short-lived process of their own, so the server stays small: building a 10,000-film list now leaves it at 35 MB. The hourly watch history import reads the whole library only when something changed (a run with nothing new from 1.7 seconds to 0.01), the Library keeps a list it has just read for 2 minutes (a search of 10,000 films from 172 ms to 13 ms), plug-in files are read once while unchanged, and an idle Live TV plug-in wakes 12 times a minute instead of 120."
            ],
            [
                "Load more as you scroll",
                "Library walls, Wanted and History load the next page as you scroll, say how many more are shown, leave focus where it was, and pause after three pages so the footer stays in reach; Show 40 more always works."
            ],
            [
                "Footer, release notes and loading",
                "The footer says Upgrade available when a newer release is out, and its Release notes link says it opens a slide-out; Sign in and Set up have no footer. A thin line under the menu shows a page is loading, and Settings pages use the full width."
            ],
            [
                "Network logos in their own colours",
                "Network logos keep their own colours, on a dark or light tile chosen by their tone."
            ],
            [
                "Seerr, Overseerr and Jellyseerr",
                "Seerr is recognised wherever Overseerr or Jellyseerr are, including by its image when taking over your apps, and has its own icon."
            ],
            [
                "Memory figures in the help",
                "The help and Install apps give Reelix's and Jellyfin's memory at rest and while working, measured on a large library, so each install's range is wider and more honest."
            ],
            [
                "The plug-ins collection needs this release",
                "Most plug-ins in TheMightyTRex/starboard-plugins now ask for plug-in API 1.8 to 1.13, which this release brings; Starboard 0.16.5 and earlier had plug-in API 1.1."
            ]
        ],
        "removed": [
            [
                "Note an issue",
                "The old Note an issue tester has gone; Send feedback replaced it. Notes it saved are still listed in Settings, General, Logs and feedback."
            ],
            [
                "Storyarr",
                "Storyarr, retired on 11 November 2026, is no longer offered by Install apps or the set-ups. A server that already runs it keeps it and still updates."
            ]
        ],
        "fixed": [
            [
                "An update could stop at its backup",
                "On a server with plug-ins, ./update.sh stopped before updating anything, because each plug-in's own data folder belongs to the plug-in's user and could not be read for the backup. The backup now leaves those folders out (the plug-ins' settings are still in it), and going back after a failed start keeps them with their plug-in. Updates from this version on use the fixed script."
            ],
            [
                "Bringing in books, audiobooks and radio",
                "Bringing in audiobooks and books sends the quality profile Reelix needs, and their matches read well in the list; radio shows match only when the titles agree, with English stations first."
            ],
            [
                "Issues reported on GitHub",
                "Download states such as post_processing show as words (#7); a plug-in's Activate sits under its state (#8); Sign out is in the side menu (#9); Manage's rows and the Advanced settings switch line up (#10, #11, DASH-413); two-tone logos are legible (#12, #13); an opened collection takes the page heading with Add missing on its line (#14, #15); and Discover's buttons line up, its rows with arrows and fades (#16, #17)."
            ],
            [
                "Apps on the VPN after Gluetun restarts",
                "Apps on Gluetun's network rejoin it after Gluetun restarts or is made again, and the VPN apps check runs every 5 minutes whether or not Alerts is active."
            ],
            [
                "Accessibility",
                "48 findings from the accessibility check are fixed, and a screen reader keeps its place: a page drawn again never sends focus to the top, whole lists are no longer read out, form slide-outs start in their first field and Show more moves to the first new row."
            ],
            [
                "Backups and moves that fail",
                "A full backup that fails sends the backup alert and leaves no part copy behind. When qBittorrent stops accepting sign-ins after wrong passwords, the move says so, for how long and how to clear it, and the steps after a stopped move say they did not start."
            ],
            [
                "Plug-in pages",
                "A saved setting reaches a running plug-in at once, a button without an ID works, no stray null shows on pages with no introduction, and the Catalogue no longer scrolls sideways on a phone."
            ],
            [
                "API checks",
                "The API description, its reference, the contract tests and every example plug-in are checked in one command on every push; the description had fallen behind the routes."
            ]
        ],
        "security": [
            [
                "Folders checked where they are used",
                "The folder picker follows links and refuses a folder outside the usual places (a link under /mnt to /etc is refused), and a plug-in's folder must sit directly in Starboard's plug-ins folder."
            ],
            [
                "Passwords kept out of logs",
                "The set-up password is hidden from every log line, even when an app repeats it in an error message."
            ],
            [
                "Exact addresses for YouTube and Spotify",
                "A link counts as YouTube or Spotify only when its host is exactly theirs, so a link that mentions spotify.com in its path is not taken as Spotify."
            ],
            [
                "No slow checks on crafted input",
                "The TMDB key check and the check of a plug-in's settings values (code scanning #53) no longer slow down on long crafted input: a 210 KB value is checked at once."
            ],
            [
                "TLS 1.2 for news servers",
                "Connections to a news server over SSL need TLS 1.2 or newer."
            ],
            [
                "Plug-ins see only what you approve",
                "A plug-in's key reads only what you approved when you added it, catalogue versions are checked against their checksums, and a plug-in that adds files to your media runs as the media folder's owner, never as root."
            ],
            [
                "API keys that cannot change your server",
                "No API key can change settings, keys, plug-ins or the install; each change made with a key is in the audit log; and the log a key can read has addresses, names and keys taken out."
            ],
            [
                "Backups and keys stay private",
                "Full backups are encrypted (AES-256-GCM) with a password Starboard never stores; a share's password and an rclone set-up stay in Starboard's own folder, never in a backup or sent to the page; site keys typed for a move are never stored or logged; and the rclone set-up handed to a copy is readable by Starboard alone (found by this release's scan)."
            ],
            [
                "Checks",
                "The unit tests (also as another user), the browser journeys, the accessibility checks, the API contract tests and example plug-ins, the help check, the private details check and the full security scans, with CodeQL, ran on this release."
            ]
        ],
        "review": [
            "jellyfin"
        ],
        "settings": "Settings, General, Downloads, Radio, Performance and Security have their parts on pages of their own; old links still work. Starboard now keeps the saved settings copies, and update.sh's data copies, of the last 5 versions and removes older ones by itself (choose 5, 10 or 20 in Settings, Updates, Restore). Backups are not scheduled until you choose. Tdarr's Overnight is now In quiet hours. The upgrade guide offers Audio description in Jellyfin's extras. To go back, run ./update.sh --to v0.16.5."
    },
    {
        "version": "0.18.0",
        "date": "15 November 2026",
        "added": [
            [
                "Update now and automatic updates",
                "Settings, Updates has Update now, which asks for your Starboard password and installs the newest release, showing each step as it goes. Install Starboard updates automatically (deactivated until you activate it) installs a new release by itself in quiet hours and does not try a version again after it did not install. Reelix's automatic updates wait for quiet hours too, and both set-ups ask about updates after Download hours."
            ],
            [
                "Recommended plug-ins",
                "The Catalogue starts with a Recommended group: Direct play, Notifications and Disk forecast, each with a Recommended chip. Direct play gets films and episodes ready to play on every device without converting them as you watch. Nothing is added until you choose it, with what it may do and your password as before."
            ],
            [
                "Plug-in logos",
                "A plug-in can have a small logo, which Starboard checks and cleans before it shows it in Manage, the Catalogue, the plug-in's page and its dashboard cards; a plug-in without one shows its initials."
            ],
            [
                "Plug-in jobs on your schedule",
                "A plug-in's job can run when you choose in its settings: every day, every week on a day, or every month on a date, at a time. System, Jobs shows when it runs next, with Run now."
            ],
            [
                "Plug-ins for Jellyfin's pictures",
                "A new permission lets a plug-in read and change Jellyfin's metadata folder (its posters, photos and details). It is said plainly before you add the plug-in, with a medium risk, and nothing else gets the folder."
            ],
            [
                "Plug-in updates you can trust",
                "Before a plug-in updates, its warning shows What is new since your version, which of your settings move and how the update is kept safe. The update then runs as steps you can follow: the plug-in finishes its work first, your settings move to the new version, and Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were, and says why."
            ],
            [
                "Plug-in API 1.14",
                "For plug-in makers: logos, the card band, a card's own refresh time (10 seconds at the quickest), job schedules from settings, the jellyfin:metadata permission, and update tools: a step before and after an update, settings migrations kept for Roll back, a health wait with an automatic Roll back, and What is new before an update. Plug-ins made for earlier versions work as before."
            ],
            [
                "Starboard's API 1.2.0, updates",
                "A key with Updates ticked (never given unless ticked) can list what can be updated, start an update to the version Starboard already found, follow its steps and roll a plug-in back, with an Idempotency-Key and a line in the audit log. One update runs at a time, with the same backup, health check and way back as the pages."
            ],
            [
                "A new help centre",
                "The help has a home page with the journey from first install to everyday use, a side menu of areas and groups on every page, the newest change, and a problem solver that asks what is wrong and leads to the answer. Every Fix a problem topic starts with a flow chart. New topics cover updating Starboard, plug-ins, Reelix and apps, and going back."
            ],
            [
                "Accessibility in the help",
                "The help has its own Accessibility section: how to change Starboard to suit you (text size and spacing, contrast, reduce motion, underlined links), ways to use it (a keyboard, a screen reader, zoom, a phone or tablet), and how it is checked, with the latest results, the known gaps and how to tell us about a problem."
            ]
        ],
        "changed": [
            [
                "Plug-in cards look the same",
                "Every plug-in card on the dashboard has a grey band across the top with the plug-in's logo, its name as the heading, and at the right a status and when it last updated."
            ],
            [
                "Updates hand over to the new version",
                "update.sh hands over to the new version's own update.sh, so a fix to it helps in the very update that brings it. Going back keeps the running copy."
            ],
            [
                "What is new fills the width",
                "In the upgrade guide, What is new now fills the slide-out's width on wide screens instead of leaving an empty strip."
            ]
        ],
        "fixed": [
            [
                "Large text in the side menu",
                "At 125% to 175% text, and with wider spacing, the side menu grows wider, so Starboard no longer breaks in the middle of the word and Feedback no longer runs past its edge."
            ],
            [
                "Large text in the header",
                "When the header has too little room it gives way in steps: icons only, then the Search button, then Help and Display as icons, then the menu under Menu. Nothing is cut off and the search box is never squeezed to a few letters."
            ],
            [
                "Short windows and phones",
                "In a window about 600 pixels tall the side menu items no longer overlap, and the menu scrolls on its own when they still do not fit. On a phone at 150% and 175% text, Downloads no longer scrolls sideways."
            ],
            [
                "Reduce motion Off",
                "Off now brings back all movement even when your device asks for reduced motion; Match device follows the device and On always reduces it."
            ]
        ],
        "security": [
            [
                "Updates need your password or their own scope",
                "Update now asks for your Starboard password, and an API key can start updates only when Updates was ticked when it was made; each update is in the audit log."
            ],
            [
                "Logos are cleaned before they show",
                "A plug-in's logo is checked and cleaned by Starboard (no scripts, links or outside files) before any page shows it."
            ],
            [
                "Jellyfin's pictures only when you approve",
                "Only a plug-in with the jellyfin:metadata permission, approved when you add it, can reach Jellyfin's metadata folder."
            ],
            [
                "Checks",
                "The unit tests, the browser journeys, the accessibility checks (axe, reading order, keyboard tasks and the new layout check), the API contract tests and example plug-ins, the help check, the private details check and the full security scans, with CodeQL, ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings: Install Starboard updates automatically stays deactivated until you activate it. To go back, run ./update.sh --to v0.17.0."
    },
    {
        "version": "0.19.0",
        "date": "15 November 2026",
        "added": [
            [
                "Download without a VPN",
                "Both set-ups now ask how your downloads connect: with your VPN account (recommended) or without one. Going without one shows a plain warning first, with Cancel as the default, and Settings, Downloads, VPN adds or removes a VPN later."
            ],
            [
                "Automatic updates for everything",
                "Settings, Updates lets each part update by itself: Starboard, Reelix, your other apps, Starboard's plug-ins and Jellyfin's plug-ins. Each stays deactivated until you activate it. Updates happen once a day in the hours you choose, one at a time, each with a copy first, a check afterwards and the way back by itself."
            ],
            [
                "One place for updates",
                "Settings, Updates lists everything that can be updated, with Update now on each, the same password and progress for every part, and Recent updates. An alert tells you when an update is waiting for you."
            ],
            [
                "Copy issues for an AI helper",
                "Activity, Downloads, Queue has Copy issues for an AI helper and Download as Markdown: every download that needs attention, with what Starboard knows and already tried, ready to paste into an AI helper. Keys, passwords and private addresses are taken out. Starboard's API 1.3.0 gives the same."
            ],
            [
                "Plug-ins from a zip file",
                "A private plug-in with no address, such as On demand, can be added with Upload a zip file in the Catalogue. Starboard checks the zip, shows what the plug-in may do, then builds and installs it step by step, with limits. Its page has Update from a zip file."
            ],
            [
                "Library clean-up and Jellyfin libraries",
                "A plug-in such as Library clean-up can move films and series into a holding folder in your media folder and put them back with Put back on each row, never deleting. A plug-in such as On demand can have Starboard add its libraries to Jellyfin. Each needs a permission you approve, said plainly first."
            ],
            [
                "Jellyfin's pictures outside its settings folder",
                "New installs keep Jellyfin's posters and details in their own folder, so Jellyfin watches far fewer folders. Settings, Jellyfin, Pictures and details moves an older install the same way."
            ],
            [
                "Plug-in API 1.15",
                "For plug-in makers: containers built from a zip file, Jellyfin libraries, the holding folder in the media folder, Put back on a custom screen's rows, and a card title for each card size. Plug-ins made for earlier versions work as before."
            ],
            [
                "Help for every plug-in",
                "The help centre's Plug-ins area has the same eight pages for each plug-in in the collection, from what it does to fixing problems."
            ]
        ],
        "changed": [
            [
                "Every dashboard card has the band",
                "Every built-in card now has the grey band plug-in cards have: a logo, its name, and a status chip and when it updated where it has something to say. A card about one app shows that app's logo. Go through them sits in the Still to set up card's band, and a small card's chip shows only its icon."
            ],
            [
                "A new install gets the newest release",
                "Run first and the installer install the newest release instead of the main branch. For testing, --main keeps the main branch."
            ],
            [
                "Help, simplest first",
                "The set-up help starts with the default install, with more apps and advanced options apart."
            ],
            [
                "Reelix you can name",
                "Starboard notes the exact Reelix build it installed, such as lite-0.8.7-trex.2."
            ]
        ],
        "fixed": [
            [
                "The Docker helper image",
                "Starboard downloads its Docker helper image again when it is missing, so activating a plug-in no longer fails with No such image."
            ],
            [
                "Plug-in buttons that ask first",
                "A plug-in button with a question, such as Line speed's Test now, now asks it, starting on Cancel."
            ],
            [
                "Plug-in list settings",
                "A list setting is a box with one value a line, and saves."
            ],
            [
                "Removing an app plug-in",
                "Its entry on Apps goes with it, and Settings, Tdarr says Tdarr is not installed."
            ],
            [
                "An app update that keeps restarting goes back",
                "After an app update, Starboard waits until the new version has stayed running for 15 seconds without starting again, so a version that keeps stopping goes back to the one before."
            ]
        ],
        "security": [
            [
                "Plug-ins from a zip are built with limits",
                "Only a zip can install a plug-in built on your computer. Its Dockerfile is checked first, and the build cannot reach your home network, folders, Docker or apps, with limits on memory, processor, time and size."
            ],
            [
                "The holding folder only when you approve",
                "Only a plug-in with the library:holding permission, approved with its high risk said plainly, can reach your whole media folder."
            ],
            [
                "Checks",
                "The unit tests, the browser journeys, the accessibility checks (axe, reading order, keyboard tasks and the layout check), the API contract tests and example plug-ins, the end-to-end update test, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings: every automatic update stays deactivated until you activate it, and an install with a VPN keeps it. To go back, run ./update.sh --to v0.18.0."
    },
    {
        "version": "0.19.1",
        "date": "16 November 2026",
        "changed": [
            [
                "Backup and restore in Settings",
                "Backup and restore is now in Settings, General, where you would look for it. It was under System. Settings, Updates, Restore still restores a backup."
            ],
            [
                "Dashboard cards on one line",
                "Each card's grey band now holds its logo, its name and its status, on one line. When it last updated sits in a small, lighter grey footer at the bottom of the card."
            ],
            [
                "The version in the side menu",
                "The version at the foot of the side menu now opens Settings, Updates. When a newer release is out, a red dot sits just above it and pulses gently, and keeps still when Reduce motion is on."
            ]
        ],
        "fixed": [
            [
                "Update now stopped at Backing up your settings",
                "Updating from the page could stop with Starboard was not updated, because the backup read Starboard's settings folder while the page's update log was being rewritten there. The backup now leaves out the update log and half-written files, carries on when a file changes as it is read, and when a backup really fails the page says why. Every update now checks that its backup reads back whole before it changes anything, so going back after a failed update always has your settings to restore."
            ],
            [
                "Two topic tabs at once",
                "Activating Advanced settings on a page with topic tabs, such as Settings, Reelix, no longer selects two tabs at once."
            ],
            [
                "Search said null",
                "Each kind under Not in your library in Search no longer ends with the word null."
            ]
        ],
        "security": [
            [
                "Checks",
                "The unit tests (also as another user), the browser journeys, the accessibility checks, the API contract tests and example plug-ins, the end-to-end update test, the help check, the private details check and the security scans ran on this release."
            ]
        ],
        "review": [],
        "settings": "Nothing changes in your settings. Updating from 0.18.0 or earlier still uses that version's script: if Update now stops at Backing up your settings, try it again or run ./update.sh on the server. To go back, run ./update.sh --to v0.19.0."
    },
    {
        "version": "0.20.0",
        "date": "17 November 2026",
        "added": [
            [
                "Bring in media you already have",
                "An optional step in the set-up, and a Bring in media button in Library, copies films, series, music and books from folders, disks, network shares, OneDrive and Google Drive into your library, named so Reelix and Jellyfin match them. It never changes anything where the media is now."
            ],
            [
                "A new folder picker",
                "Every page that picks a folder opens on this computer and each disk, then shows each folder's size and what is in it, with a path bar and Back."
            ],
            [
                "Install all updates",
                "When more than one update is waiting, Settings, Updates installs them all in one go, one at a time and in a safe order, each with its own copy and way back. It says first what will install and what is held back, and why."
            ],
            [
                "Connect a cloud service",
                "Settings, General, Backup and restore has a wizard that signs in to Google Drive, OneDrive, Dropbox and other services, chooses the folder and tests it, so copies of your backups can go off this computer."
            ],
            [
                "Test connection",
                "Beside the place your backup copies go, Test connection checks it can be reached and written to, that there is room, and that a cloud sign-in still works."
            ],
            [
                "Monthly backups",
                "Backups can now be made once a month, on the 1st at 03:00, keeping the newest 6."
            ],
            [
                "Log limits and Delete all logs",
                "Settings, General, Logs and feedback sets how long Starboard keeps its logs and the most they may take, and Delete all logs removes them after your password."
            ]
        ],
        "changed": [
            [
                "Lighter pages and checks",
                "The plug-ins list, dashboard cards, jobs, styles and the Alerts card do much less work each time they are asked, and the Apps and Updates pages ask Docker about each image once."
            ]
        ],
        "fixed": [
            [
                "Escape in a slide-out",
                "Escape now closes a slide-out even while focus is inside the page shown in it, such as a step of Still to set up."
            ],
            [
                "Clicking in a set-up step",
                "Clicking a field or button inside a Still to set up step's page no longer sends focus back to the step's heading."
            ],
            [
                "Settings, Radio could stop loading",
                "The Radio settings could stop with an error when Starboard answered before the page's own script had loaded. Every page now starts once its scripts are ready."
            ],
            [
                "No sideways scroll on narrow phones",
                "A long folder path in a heading, as on Backup and restore, now wraps instead of pushing the page sideways."
            ]
        ],
        "security": [
            [
                "Cloud sign-ins",
                "The address you paste back after signing in is checked before it is used: only this computer's own address on rclone's port, with this sign-in's own state and code. The sign-in helper publishes no port and is removed when the sign-in ends."
            ],
            [
                "Bring in media reads only",
                "Every source is opened read only, so nothing where your media is now can be renamed, moved or deleted."
            ],
            [
                "Delete all logs asks for your password",
                "Removing every log is a danger action, so it needs your Starboard password, as Sign out everywhere does, and the log says which browser did it."
            ]
        ],
        "review": [],
        "settings": "Your settings stay as they are. Logs keep your number of days, now with a 50 MB limit as well, which you can change in Settings, General, Logs and feedback. Starboard's built-in plug-ins restart once after the update to take the apps' log limit of 3 files of 10 MB. To go back, run ./update.sh --to v0.19.1."
    },
    {
        "version": "0.20.1",
        "date": "17 November 2026",
        "fixed": [
            [
                "Jellyfin 12 and plug-in libraries",
                "Adding a plug-in's libraries to Jellyfin and the poster check on the Library health page work again with Jellyfin 12, which turns away the older way of sending its key."
            ],
            [
                "Release notes for 0.15.2",
                "Starboard's own notes for 0.15.2 now show the Added entry this changelog has, not a second wording of it."
            ]
        ],
        "security": [
            [
                "Code and writing checks",
                "Once a week GitHub checks the code for likely bugs, the writing rules, misspellings and the safety of its workflows, and that the tests run as much of the code as before. The workflows' actions are pinned to exact versions and kept up to date."
            ],
            [
                "The key check reads the whole history again",
                "The release check for keys and passwords read no history at all when run from a second working copy, so it passed without looking. It now reads all of it: it found only made-up keys in tests and one placeholder in the help."
            ]
        ],
        "review": [],
        "settings": "Your settings stay as they are. To go back, run ./update.sh --to v0.20.0."
    },
    {
        "version": "0.20.2",
        "date": "17 November 2026",
        "fixed": [
            [
                "Update now could stop at the backup",
                "Update now could stop with \"data/self-update.log.new: No such file or directory\" while it backed up your settings, because the page's own progress log was being rewritten beside them. The log is now written outside your settings folder, and a backup that meets a file changing is tried again."
            ]
        ],
        "review": [],
        "settings": "Your settings stay as they are. To go back, run ./update.sh --to v0.20.1."
    },
    {
        "version": "0.21.0",
        "date": "17 November 2026",
        "added": [
            ["Check for updates", "Settings, Updates, Ready to update has a Check for updates button that asks every part for new versions now: Starboard, the apps, Reelix, the plug-ins and Jellyfin."],
            ["What is new in every update", "A What is new button beside Install all updates opens the release notes of every waiting update in one slide-out, from the version you have to the new one."]
        ],
        "changed": [
            ["Install all updates from one update", "Install all updates shows when even one update is ready, as Install 1 update, with the same order, safety copies and way back."],
            ["One address for the Jellyfin plug-ins", "Settings, Apps, Jellyfin installs TheMightyTRexUK's Jellyfin plug-ins from one repository, and replaces the old Picture shrinker address in Jellyfin."],
            ["Words that follow the design system", "Pages, messages, the terminal set-up and the help follow the design system's words: no sight words, Enter for typing, disk for a disk, and Active and Inactive for settings."],
            ["One set of status words", "Every chip, band and row takes its word and colour from the design system's one list."],
            ["Square library cards", "Collection and network cards, logo tiles and the dashboard's edit box use the design system's square corners and focus ring."],
            ["What Starboard does not do", "The help article that listed plans now gives the facts only."]
        ],
        "fixed": [
            ["Reading the Jellyfin plug-ins list changed Jellyfin", "Opening Settings, Apps, Jellyfin no longer changes Intro Skipper's or Merge Versions' settings when you added them yourself."],
            ["A plug-in job's failure gave only a status line", "System, Jobs and the log keep the plug-in's own reason when a job fails."],
            ["A built-in plug-in left failed was never started again", "Live TV and other built-in plug-ins start again at the next start after a failure."],
            ["Apps a full backup stopped could stay stopped", "If Starboard stops during a full backup, the apps it stopped start again at its next start."]
        ],
        "security": [
            ["A check for banned words, and the word check reads charts", "The weekly checks fail on the design system's banned words in pages, scripts, help and flow charts."]
        ],
        "review": [],
        "settings": "Your settings stay as they are. To go back, run ./update.sh --to v0.20.2."
    }
,
    {
        "version": "0.22.0",
        "date": "19 November 2026",
        "added": [
            ["Play in Jellyfin", "Films and episodes in the Library have a Play button that opens them in Jellyfin's web app in a new tab, using the address you gave Jellyfin for your browser."],
            ["Restart where it is needed", "When Jellyfin says Restart needed, Restart Jellyfin is on System, Overview, on Settings, Updates and beside Jellyfin's recommended plug-ins; Restart Reelix waits beside a Reelix restore."],
            ["Cache counts in the diagnostics", "System diagnostics show how often Starboard's caches were used and emptied, with no keys or names in them."]
        ],
        "changed": [
            ["Mica is Starboard's own style", "Neutral greys, 6px corners, a light lift on cards and a Blue accent, with the dashboard card as the model for panels, settings sections, tables, slide-outs and dialogs."],
            ["Light unless you choose", "Starboard opens in Light for everyone who has not chosen a theme in Display; a choice already made is kept."],
            ["Glass", "The header, side menu, menus, slide-outs and dialogs are frosted layers, solid in high contrast and with Reduce transparency."],
            ["Accent colour", "Settings, General, Appearance chooses the accent for everyone on the server: Blue, Teal, Indigo, Forest, Plum, Ember or Graphite."],
            ["A clearer hover on every menu", "Menus and tabs show a light fill with an edge at least 3:1 against the menu, in every theme and with every accent."],
            ["Styles from plug-ins keep their own design", "Cards lift only in styles with elevated cards, and headings keep their weight."],
            ["Library episode rows line up", "Each episode shows its name, its status, Watched and Play in columns that line up; on a phone the status and Watched show as icons, and screen readers still read their words."]
        ],
        "fixed": [
            ["Plug-ins added or removed could stop an update", "The settings backup before an update leaves out every folder only a plug-in can read, wherever it is, such as a removed plug-in's data in holding, and going back returns each one whole."],
            ["Plug-ins could not reach Starboard on the home network", "Plug-ins on the home network, such as Remote access, now reach Starboard's API on the server at Starboard's own port."],
            ["Reelix was listed several times in Updates", "System, Apps, Updates lists Reelix once, as its films, series, books and music connections run in its one container."],
            ["Discover tiles had square corners", "Cover tiles on Discover have the same 6px corners as the rest of Starboard."]
        ],
        "security": [
            ["Live TV checks every address it opens", "Live TV checks each list, guide and stream address it downloads, and every redirect, against the same rules as app addresses, so a list cannot lead Starboard to a refused address such as cloud metadata."],
            ["Pinned scanner versions", "The security checks run fixed versions of their scanner image and Bandit, so a changed scanner cannot change a result without a review."]
        ],
        "review": [],
        "settings": "Your settings stay as they are. People with no theme chosen see Light. A server on Teal, the old default colour, moves to Blue once; choose Teal again in Settings, General, Appearance to keep it. To go back, run ./update.sh --to v0.21.0."
    },
    {
        "version": "0.23.0",
        "date": "19 November 2026",
        "added": [
            ["Add Coming up to your calendar", "Coming up has Add to your calendar: an address a phone or computer calendar can subscribe to, which can read the calendar and nothing else."],
            ["AI assistants over MCP", "An AI assistant that speaks the Model Context Protocol can ask Starboard about your library, downloads, requests and apps, with a read-only key, once you switch it on in Settings, Security, API keys."],
            ["Plug-ins activate when installed", "A plug-in is activated as soon as it is installed, unless it needs settings first or an app it brings in is already on the computer."],
            ["Close on Install all updates", "When Install all updates finishes, Close takes its panel away, and it does not come back."],
            ["Pictures in What is new", "Each plug-in's logo, each app's icon and Starboard's mark sit beside their notes in What is new."],
            ["Plug-ins know their home address", "A plug-in with a page on your home network is given its address there, so Create your own TV channel connects to Jellyfin by itself."],
            ["An alert when a disk changes", "Every job of the disk pool helper is logged, as a warning when a disk was erased, and sent to plug-ins such as Notifications."]
        ],
        "changed": [
            ["General on every plug-in's page", "The first tab is General, with a card each for State, Versions, Jobs, What it may do and Remove."],
            ["Install all updates says whether it is still working", "While it works, the panel says Installing updates with how many are done, and a bar moves; at the end it says how it ended."]
        ],
        "fixed": [
            ["Plug-ins on their own network reach Starboard", "A plug-in on its own closed network, such as Disk forecast or Download summary, reaches Starboard through a socket in its own folder."],
            ["Plug-in boxes take plain text", "A plug-in's Add box and row boxes, such as a TV channel's name, no longer refuse anything that is not a web address."],
            ["Settings, Radio sometimes stopped loading", "Every page now waits until all its scripts have run."],
            ["Three slips on the Updates and plug-in pages", "Clear words where a place was missing, no old Starboard message after an update, and summaries that end at a whole sentence."],
            ["Live TV's address message", "It says Enter rather than Type."]
        ],
        "security": [
            ["The disk pool helper's risk, written down", "The security notes explain why Starboard's user counts as root, and every disk change is now logged and alerted."],
            ["A calendar address that can only read the calendar", "It is stored hashed, compared in constant time, rate limited, and refused everywhere else."]
        ],
        "review": [],
        "settings": "Your settings stay as they are. AI assistants stay off until you switch them on. To go back, run ./update.sh --to v0.22.0."
    },
    {
        "version": "0.24.0",
        "date": "19 November 2026",
        "added": [
            ["Plug-in pages that save in place", "A plug-in's own page, such as Create your own TV channel's, saves a change without drawing the whole page again, lets you tick several things in a slide-out, and comes in cards, with pictures such as an uploaded logo."]
        ],
        "changed": [
            ["File pickers match the rest of Starboard", "Every file upload is a Choose a file button in the site's style, with the chosen file's name and size beside it."]
        ],
        "fixed": [
            ["Copy issues for an AI helper found nothing from Reelix", "It reads Reelix's downloads again, with their custom formats and score, and says when an answer could not be read rather than that Reelix did not answer."],
            ["A plug-in's Versions had no upload button", "Update from a zip file has Upload and check, which uploads the zip, checks it and shows What is new before anything changes."],
            ["A plug-in's links to its own page open", "A link to a plug-in's own web page, such as the TV channel's schedule grid, uses the address you opened Starboard with."],
            ["A row's Remove words", "The More menu on a plug-in's row uses the plug-in's own words, such as Remove the logo."]
        ],
        "review": [],
        "settings": "Your settings stay as they are. To go back, run ./update.sh --to v0.23.0."
    },
    {
        "version": "0.25.0",
        "date": "20 November 2026",
        "added": [
            ["New parts from the design system", "App logs on System, Logs can be searched, filtered by level, followed as they arrive and downloaded; a new API key has Show, Copy and Replace; System's processor, memory and temperature are gauges; item pages have tabs; lists of words in Reelix settings are tags; Add an app lists every mistake at the top."],
            ["Connection lost", "When the page cannot reach Starboard, such as while it restarts for an update, a banner says so until it answers again."],
            ["Plug-ins can show a trend and send alerts", "Plug-in API 1.17: a card can be a small line of recent values with the latest, lowest and highest in words, and a plug-in allowed to can send alerts where Starboard sends its own."],
            ["Everything you can do with a download that needs attention", "On Activity, Downloads, Queue, a slide-out says what is wrong in plain words and offers every action that fits, including removing it with its files."],
            ["Detailed log for backup connections", "A setting in Copies off this computer logs each test, copy and step of connecting a cloud service, to find out why one does not connect."]
        ],
        "changed": [
            ["New colour themes", "Starboard's own style can be Blue, Teal, Dusk, Lime, Rose, Amber or Graphite; the four new ones also tint the page and cards. A saved Indigo, Forest, Plum or Ember becomes Dusk, Lime, Rose or Amber."],
            ["A smaller, quicker Starboard", "The image is 101 MB instead of 162 MB and the download 25 MB instead of 41 MB; each settings page loads only its own script, and pages are served from memory."],
            ["Hidden tabs stop asking", "Pages left open in a hidden tab no longer check for updates until you come back to them."],
            ["Plug-ins can take files up to 100 MB", "A file chosen on a plug-in's own page, such as a TV channel's holding slide, may be up to 100 MB."]
        ],
        "removed": [
            ["White Live TV channel logos", "Every Live TV channel shows its own logo in its own colours; the White channel logos setting and the picture library it needed are gone."]
        ],
        "fixed": [
            ["Plug-in pages", "Grouped lists have headings in order, a schedule being changed is read as a list item, and section tabs stay in view under the header."],
            ["Searching a plug-in's list of sections that fold", "Searching or filtering such a list, such as On demand's sports leagues, no longer stops it with an error."],
            ["Radio downloads stuck at import", "Try the import again and Ignore work for a radio episode too."]
        ],
        "security": [
            ["Words from an app never become page code", "The new secret field, pagination and error summary set names and links as text, found by GitHub's CodeQL before release; nothing released was affected."],
            ["Security scan", "Trivy, Gitleaks, Bandit, ShellCheck, Hadolint and ZAP signed out and signed in found nothing to fix."]
        ],
        "review": [],
        "settings": "Your settings stay as they are, except that an old colour theme moves to its new one and the White channel logos setting goes. To go back, run ./update.sh --to v0.24.0."
    },
    {
        "version": "0.26.0",
        "date": "21 November 2026",
        "added": [
            ["Bulk actions on the download queue", "On Activity, Downloads, Queue, tick downloads or Select all, then try the import again, ignore, find another or remove them together; Starboard asks first, names how many, and says what was done."]
        ],
        "fixed": [
            ["The red edge of a Remove section", "It now runs the full height of the section and is as wide as every other status edge."]
        ],
        "security": [
            ["Security scan", "Trivy, Gitleaks, Bandit, ShellCheck, Hadolint and ZAP signed out and signed in found nothing to fix."]
        ],
        "review": [],
        "settings": "Your settings stay as they are. To go back, run ./update.sh --to v0.25.0."
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
