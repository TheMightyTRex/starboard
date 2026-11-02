# Changelog

## 0.7.3 (2 November 2026)

- **App cards:** the reply time sits on the right and takes only its own width, with a gap between the cells, so
  long versions such as Prowlarr's 2.7.0.5723 no longer run into it. On a very narrow card a version breaks
  after a dot, never inside a number. An unknown version shows nothing; an app that does not answer shows N/A.

## 0.7.2 (2 November 2026)

- **App cards (Health first and Tiles):** every card has the same rows in the same places. The status sits beside
  the name; then what the app is doing ("3 in the queue", "Nobody playing", "Nothing to report", "Cannot reach
  it"); the home address as a link that opens the app (now on phones too); warnings, in a row only when a card in
  that category has one; and along the bottom, under a line, Update available, the version and the reply time
  ("Not known" and "No reply" when the app does not answer). Each card takes its rows from the grid, so cards
  side by side are the same height. The Open button is in the app's details.
- **App logos** are shown on their own, without a tile (shared library); initials keep their tile.
- **Updates for test builds:** an image pinned to a test build such as `v0.4.9-dev.6`, which is not in its
  registry, is now offered the newest release (a test build counts as older than its release).

## 0.7.1 (2 November 2026)

- **Long API keys:** keys were cut to 200 characters when saved, so Audiobookshelf (whose keys are about 211
  characters) refused its key. Keys up to 2000 characters are now kept whole. If Audiobookshelf says the key is
  wrong, paste it again in Settings, Manage apps.
- **Updates:** each app has its logo beside its name (no tile, as tall as the name and the line under it);
  Installed and Latest are left-aligned; every category's table has the same column widths, so the
  columns line up down the page; and each row's cells sit on the middle of the row.
- **Log:** a connection that stayed idle until it timed out no longer writes an error to Docker's log.

## 0.7.0 (2 November 2026)

### Install apps, for people who have never set up a media server
- **Start here:** what each app does (find, choose, download, sort, watch), how long it takes and what you need.
  **Advanced settings** (a tick, remembered) shows every app in each group, the settings folder, user and group
  numbers, time zone and the files; without it, the guide picks the apps and folders.
- **Every step is checked**, with the problem shown by its field: at least one thing ticked (and a warning when
  nothing can download), a full media folder path, numbers and time zone in Advanced settings, and the VPN.
- **VPN** is its own step: provider (with a list of common ones), WireGuard or OpenVPN as a segmented choice, and
  only that connection's fields, each saying where to find it. Only those fields are written to .env, and they
  are required.
- **Pool drive:** "Join several drives into one" opens a pop-up listing the mounted drives (from Disk health's
  drive list, or typed in), and writes the mergerfs commands to run on the server. The pool becomes the media
  folder. Nothing is erased.
- **Check** sums up every step with a Change link to it; the files are behind a disclosure (open in Advanced).
- **Connect your apps:** after starting, numbered steps with the exact hosts, ports and folders for qBittorrent,
  SABnzbd, Radarr, Sonarr, Lidarr, Bookshelf, Prowlarr, Jellyfin, Seerr and Bazarr (gluetun when they go through
  the VPN).
- **Storyarr** is offered by default (`ghcr.io/themightytrex/storyarr`, pinned, so Updates offers newer versions;
  `STARBOARD_STORYARR_IMAGE=none` leaves it out), and Install apps writes `starboard-before-update/storyarr.sh`, a
  database backup that runs before each update.

### Copy app settings (Settings, Manage apps)
- From one Sonarr, Radarr or Lidarr into another of the same kind and major version: tags, custom formats,
  quality profiles (format scores matched by name), root folders, download clients and remote path mappings,
  naming and media management. A preview says what will be added, what is already there and what will be
  replaced. Passwords the old app hides are asked for; without them a client is added switched off. Indexers:
  add the new app in Prowlarr.

### The API gaps (DASH-19)
- Apps: Check again in a slide-out checks that app only; Recent checks (the last 20, in memory); "Not responding
  for 12 minutes"; the app's own warnings carry its id, when first seen and a How to fix it link.
- Downloads: Remove (optionally blocking the release) and Find another; the added date; all messages.
- Coming up: each item's overview and a link to its page in the app; Earlier and Later move a month at a time.
- Search: In the library links open the item in its app.
- Storage: the folder path and the disk (or pool members) it is on.
- Disk health: rpm, the self-test history, every SMART attribute, events with their time and a status icon, and
  Download the full report.
- Backups: what a saved copy holds, and downloading it (password first); downloading a server backup through a
  one-time link (streamed); earlier runs, what went in and what could not be read, when the server job reports them.
- Settings: renaming or removing a category is one save; About shows when this version started.
- A wrong password in a dialog (or Install apps' Start) stays on the page: the server says `reason: "password"`.

### Look and feel
- **Slide-outs:** Display and accessibility is a slide-out; every slide-out header (and the phone menu's) is in
  the page background over a white or dark-surface body (library token `--color-slide-header`).

### Other
- Upgrade now from Storyarr: `apps-updates.html?app=storyarr` checks at once and goes to that row.
- Images for 32-bit Raspberry Pi (linux/arm/v7). Pillow is installed only where a ready-made build exists.

## 0.6.0 (2 November 2026)

- **Listening progress (Settings, Audiobookshelf):** reads where everyone is in each audiobook from a Plex server
  (your own account, from libraries with book in their name or the Audnexus agent), a Jellyfin or Emby server
  (every user, from Books libraries) or another Audiobookshelf (every user). A book in several files becomes one
  position. Match each account to an Audiobookshelf user, then Apply now, or keep applying every hour so books get
  their progress once they are scanned in.
- **Matching:** ASIN, then ISBN, then title and author (first author, ignoring punctuation and a leading The),
  then the book's folder. A position from a copy of a different length is scaled to fit. Books not found are
  listed, with their account.
- **Safe by default:** progress a person already has in Audiobookshelf is never changed, and each book is
  written once. The admin key makes a key that acts as one person, ends by itself after 15 minutes, and is
  deleted as soon as that person's progress is written.
- **Audiobookshelf app type:** its version on Apps, and an optional API key. Apps named Audiobookshelf move to the
  new type when you upgrade (settings schema 2; a backup is made first). The upgrade guide asks for the key.
- **Install apps:** the Listening progress offer is ready, and points to Settings, Audiobookshelf.

## 0.5.6 (2 November 2026)

From a design consistency review of Starboard and the shared component library (all 23 findings fixed):

- **Names:** "Check again" for every refresh (it was also Check now and Check for updates); Storage's job is
  "Sort by type". "Run now" stays for server jobs.
- **Saving:** choices save as soon as they change (the default design no longer needs a button); text fields keep
  a secondary Save; one primary button per page (request rows, Updates rows and settings forms no longer each
  have one).
- **Buttons and dialogs:** compact buttons only in dense tables; Decline and Restore are danger buttons, as their
  dialogs are; every confirm dialog says Cancel; delete uses the bin icon.
- **Logs:** the filter is a segmented control; detailed logging is the same select as in Settings; the wording
  follows whether it is on.
- **Charts:** the pool bar's labels no longer stretch; chart and ring text follow Text size; the second line on
  System charts is dashed to match its legend; media colours come from the library's new series tokens, with a
  high contrast set.
- **Layout:** no focus box on wizard headings; Performance's four presets in one row with their text lined up;
  space in the Jellyfin panel; headings at one level are one size; the guides show their Settings tab as current;
  an odd stat tile spans the row on phones; small legend rows no longer look muted.
- **Code:** old copies of library rules removed (rows, notices, panel heads, charts, stacks, focus); settings
  helpers moved into the library; Performance's wording fixed ("1 minute", "1 answering a page").

## 0.5.5 (2 November 2026)

### Logs

- **System, Logs:** what Starboard did (start-up, sign-ins, settings and apps changing, alerts, download hours,
  updates, storage readings, background jobs) and every problem it met, newest first, with Everything,
  Problems and Detailed, a search, Download and Delete logs.
- **Settings, General, Logs:** keep logs for 7 days to a year (60 by default); older days are removed once a day,
  with no thread of its own. **Detailed logging** (Off, For 24 hours, Until I turn it off) adds each page request
  and each call to your apps, and the full detail of errors.
- **Report a problem:** turn on detailed logging, do the thing again, then Copy the details (versions, how it
  runs, what is switched on, the kinds of apps, recent entries) and Open a new issue on GitHub, which uses a new
  issue template.
- Personal details are removed before anything is written, in both modes: passwords, API keys and tokens, IP
  addresses, host and computer names, email addresses, user names in folder paths and the dashboard's name.
- Docker's own log now holds only start-up and problems, and both Compose files cap it at 3 files of 1 MB.

### Fixed

- System, Overview: the charts' history failed to load since 0.4.0 (found by the new log).

## 0.5.4 (2 November 2026)

- System, Overview: Jellyfin's status chips sit beside its name, centred on the heading's line, with the
  version on the right. The pattern (`.title-status`) and the status icon after a name (`.status-icon`) are now
  in the shared component library, with a "where status goes" rule for both apps.

## 0.5.3 (2 November 2026)

- **Ready-made image** for amd64 and arm64 at `ghcr.io/themightytrex/starboard` (each version, its minor
  version and `latest`), published by a workflow for every release tag. `compose.image.yaml` runs it with no build.
- The README's clone address and the licence now name the GitHub account (TheMightyTRex) and author
  (TheMightyTRexUK). The privacy check allows those two names and still catches everything else.

## 0.5.2 (2 November 2026)

- An upgrade from 0.4.0 or earlier now opens the upgrade guide with the 0.5.0 questions (new apps and Storage).
  Before, it assumed 0.5.0 and skipped them.

## 0.5.1 (2 November 2026)

- Upgrade available looks for the newest version tag (what ./update.sh installs), and never offers an older
  version as an upgrade. Before, GitHub's last published release (0.1.8) could be offered.

## 0.5.0 (2 November 2026)

### Finding apps

- **Search for new apps** (Settings, Manage apps): Starboard tries the usual port of about 40 apps, and every
  port a container publishes, on this computer only. It recognises each app by its page, leaves out the ones you
  have, and adds the ones you tick. With Docker access it reads the API keys of Sonarr, Radarr, Lidarr, Readarr,
  Prowlarr, SABnzbd and Seerr from their own settings files, if you tick "Fill in API keys for me".
- It runs only when you press the button: no background work.

### Storage charts

- **System, Storage** shows each pool as a bar (how full) and a ring (what fills it) by type: TV, films,
  audiobooks, music, books and comics, downloads waiting and everything else, with free space. Also each drive
  in the pool (fullest first), space used over time with a forecast of when it fills, and the biggest series and
  films. Every chart has a table view.
- Sorting by type reads every file name, so Settings, Performance (and the set-up and upgrade guides) choose
  when: only when you press Work it out (the default), when you open Storage if over a day old, every night or
  every week at 3 am, or off. It now reads a pool once, skipping its drives, and stays on one file system: on
  the test server, 105 seconds for 30 TB, down from reading it twice.
- A daily record of used space (on; nothing noticeable) feeds the forecast. Storage page updates: only when you
  press Check again (the default), or every minute or 5 minutes while the page is open.
- The stat tiles count a pool once, not once for the pool and again for its drives.

### Install apps

- **Install apps** (Settings, Manage apps, or the first step of the set-up guide): tick groups such as Movies,
  TV, Music, Ebooks, Audiobooks, Comics, Watching, Downloads, VPN and Subtitles, and change the apps inside each.
  Apps already running are left alone; ports in use move to the next free one; each app shows its memory use.
- Starboard writes `data/stack/compose.yaml` and `.env` (private, with database passwords made up for you),
  shows both, and keeps older copies. With Docker access, Start asks for your password, then makes the folders
  and starts the apps; without it, it gives you the one command to run.
- It finds the folders your other apps already use for media and offers them, so nothing is moved. It offers
  watch history from Plex or Emby into a new Jellyfin; listening progress and copying app settings are next.
- Apps that need their own settings file first (Unpackerr, Decluttarr, Janitorr) are written but not started.

### Set-up and upgrades

- **Set-up guide** after the first password: apps, API keys, Jellyfin extras, download hours, alerts and how
  much Starboard does, with a summary and Change links at the end. Steps that do not apply are left out. Run it
  again from Settings, General.
- **Release notes** open from the version in the footer. "Upgrade available" shows there when GitHub has a newer
  release.
- **Upgrade guide:** after an upgrade that brings settings to choose, a notice opens a short guide with what is
  new and only those questions. "Remind me later" and "Keep the defaults and finish" are always there. Upgrades
  with nothing to choose do not interrupt.
- Releases follow one process, in `docs/RELEASING.md`; `tools/release_notes.py` writes the GitHub notes.

## 0.4.0 (2 November 2026)

### Performance

- **Settings, Performance:** Starboard's own memory, processor and threads, measured live; four presets (Small
  server, Balanced, Everything, Custom); and every piece of background work with a switch, how often it runs
  and what it costs. Changing anything by hand makes it Custom.
- Background threads exist only while their feature is on: history, watching, download hours and the Jellyfin
  jobs each start when turned on and end when turned off. With Small server, Starboard runs only its web server.
- System history can be off, or every 1, 5 or 15 minutes (5 by default, was 1), and no longer reads each
  container's use. The download hours check can run every 5 minutes. Downloads and Monitor update at the rate
  you choose, or Downloads only when you press Check again. Card numbers can be switched off.
- The Plex database and XML code are loaded only when an import or a Live TV run needs them.

### Security fixes

From a full security check. No critical issues; these are fixed:

- A request with a negative size could make Starboard read without end and use up memory, signed out. Refused now.
- Password guesses sent all at once got past the 5-attempt limit. Attempts are now counted before the check, and
  at most two password checks run at once. X-Forwarded-For is believed only from the proxy itself.
- The sign-in page's "next" address could send you to another site. Only pages on this dashboard now.
- A saved API key or alert token is not reused when an address points to a different server, and keys are not
  carried across a redirect to another server.
- Apps, Updates: Compose details from container labels are strictly checked and quoted, the folder can never be
  /, and the helper image is pinned to one exact build.
- Dot-dot paths, idle connections (closed after 30 seconds, 64 requests at most), malformed requests, unknown
  host names (DNS rebinding; STARBOARD_ALLOWED_HOSTS adds names), size limits on uploads and downloads, Live TV
  channel data cleaned, Pluto's stream server checked, XML guides with a DOCTYPE refused, Pillow image limits.
- Installer: names with characters that would break .env or Compose files are refused. The disk health job
  writes in a private folder and never follows a planted link.

## 0.3.4 (2 November 2026)

- Every setting that uses processor time or memory says what it costs, measured on a home server, so a small
  server can keep only what it needs. The access list on About and updates says the same for each item.

## 0.3.3 (2 November 2026)

- Live TV: logos the folder already serves are used as they are, not processed again.

## 0.3.2 (2 November 2026)

- Live TV: the guides refresh daily, but the channel lists are rebuilt (and every stream tested) only when a
  source's channel list changes, or once a week. Numbers and logos are redone only when a playlist changed.
- Watch history import: Jellyfin and Emby libraries are read 1,000 items at a time, so big libraries work.

## 0.3.1 (2 November 2026)

- Jellyfin jobs: send Jellyfin's API key the way newer Jellyfin versions need it.

## 0.3.0 (2 November 2026)

- **Settings, Jellyfin:** jobs moved in from the old launcher, each off until you turn it on.
  - **Live TV:** free channels and guides for Jellyfin (Free-TV, Samsung TV Plus, Pluto TV), Sky-style
    numbers, and white logos made with Pillow (switchable). Needs Jellyfin's Live TV folder (`./install.sh`).
  - **Import watch history** into Jellyfin from a Plex database file, a Plex server, Emby, another Jellyfin or a
    history file, with account matching; applied once per item, and every hour if you choose.
  - **User defaults** for every Jellyfin user.
- **Apps, Other services** lists Starboard's own jobs and whether each is on.
- **Set-up** offers the Jellyfin jobs when it finds Jellyfin.
- Pillow and the data sources are credited in THIRD-PARTY.md.

## 0.2.0 (2 November 2026)

Lightweight first: a dashboard for smaller servers that uses very little processor time and memory (about
14 MB while idle). Every page now uses the component library shared with Storyarr.

- **Lighter:** pages are compressed and the browser keeps them until they change; several tabs or devices
  share one answer from each app; hidden tabs stop refreshing; posters come from your own apps, kept for a
  week; background work starts only when needed.
- **Installer:** explains each step, and asks before each kind of access (home network, Docker for app
  updates, per-app use, folders for free space, Disk health). Run it again to change your answers.
  Settings, About and updates lists what Starboard can access, with the switch or command to change each.
- **Settings:** one column; Manage apps and the access list show each state as an icon beside the name;
  a new Alerts page; Coming up and Download hours settings in General.
- **Alerts:** to ntfy, Gotify or a webhook when an app stops answering, a disk has a problem or gets full, a
  download is stuck, a backup fails or a certificate runs out; uptime history for each app; a weekly
  summary. Off until you turn it on.
- **Apps:** small numbers on each card; Updates is its own page again, with each app's container, Check for
  updates, Update all and Update (needs Docker access).
- **Downloads:** download hours for qBittorrent and SABnzbd, with Resume, Pause and Follow the hours;
  speeds and the VPN's state (Gluetun); Finished this week; Requests from Seerr with Approve and Decline.
- **Coming up:** posters, a List or Calendar view, and how far ahead to look.
- **System:** Jellyfin's state, what is playing and what was added; server jobs with Run now; 30-day disk
  temperatures and the drive's own log; Read disks now; what is using the space; every drive; each app's
  processor and memory on Monitor; certificate expiry on Network.

## 0.1.8 (2 November 2026)

- Backup and restore: an option to include a rebuild prompt for an AI assistant with the server backup
  (the job is asked for `backup-with-prompt`). The page says what the server backup covers.

## 0.1.7 (2 November 2026)

- Storage: each folder has a tag with its filesystem, such as ext4, NTFS or mergerfs.

## 0.1.6 (2 November 2026)

- Apps: the running and external access counts sit on the same row as Check again and Add an app, at the
  same height, with their coloured edge: "20/20 running at 23:47", "0/4 external access".
- System, Backup and restore: download Starboard's settings as a file, restore from a file or from a copy
  Starboard saved, and start the server's own backup job and see its result and files. Downloading or
  restoring needs your password again.

## 0.1.5 (2 November 2026)

- Apps has a sub-menu: Apps, Updates (each app's version, and whether Sonarr, Radarr, Lidarr, Readarr and
  Prowlarr have an update) and Other services (services with no web page; a service with no address can follow
  another app's status).
- The Apps page opens with two cards: how many apps are running, and how many outside addresses are reachable.
- System has a sub-menu: Overview, Storage, Disk health, Monitor and Network.
- Charts: Starboard records a reading every minute for 24 hours. Overview has tiles with trend lines and charts
  for processor, memory, network, disk activity and temperature over the last hour, 6 hours or 24 hours.
  Storage, Disk health and Network have their own charts. Every chart can be read with the arrow keys and
  shown as a table.
- Disk health reads SMART reports saved by a small job on the server (`deploy/install-smart.sh`).
- Your own folders and disks go in `compose.override.yaml`, which updates leave alone.

## 0.1.4 (1 November 2026)

- New logo, Tile board: three tiles and a star. In dark mode the star is lighter. Used in the header, the
  phone menu, the browser tab and the home-screen icon.

## 0.1.3 (1 November 2026)

- Looks like Storyarr: its colours, its icons (Lucide) and its square tabs. The main menu and every sub-menu
  use the same tabs; on phones a menu drawer holds both.
- Settings is four pages with a sub-menu: Apps, General, Security and Updates. Old links still work.
- The installer and the setup page ask you to name your dashboard. Change it in Settings, General.
- Each app's own icon on its card, from the dashboard-icons collection. Starboard keeps a copy, so icons
  still show without the internet. Choose another icon in the app's settings.
- Apps are grouped by category: Watch, listen and request; Find and organise; Search and download;
  Dashboards and tools. New apps get a category chosen for them; change it in the app's settings. Health
  first still puts apps that are not responding at the top.
- A footer on every page: "Starboard: v" and the version, a link to the GitHub repository and to Updates.
- The version is only shown to people who have signed in.

## 0.1.2 (1 November 2026)

- Fixed: `./update.sh` made the new version's files readable by you only, so the container could not start
  and the roll-back failed the same way. The image now makes its files readable whatever the host's
  permissions, and the updater only keeps the backup private.

## 0.1.1 (1 November 2026)

- Passwords need 10 characters or more (was 12).
- Remember me on the sign-in and setup pages. Without it, you are signed out when the browser closes, or after
  a day. With it, you stay signed in for the number of days set in Settings, Security.
- The setup code stays the same when Starboard restarts or updates, so the code the installer printed keeps
  working until a password is set.

## 0.1.0 (1 November 2026)

- Apps, Search, Downloads, Coming up, System and Settings, each on its own page.
- Search Sonarr, Radarr, Lidarr and Readarr at once and add what you find.
- Five designs: Health first (the default), Tiles, Shelf, Command and Status board, plus the Display and
  accessibility panel.
- Installer (Docker or systemd) and updater with backup and automatic roll-back.
- Password sign-in with a one-time setup code; API keys never reach the browser.
- Open it from phones and other computers on your home network, or switch that off in Settings so only the
  computer it runs on can connect. Docker uses host networking for this.
- Phone layout on every page; add it to your home screen.
- Each app's home address and outside address on its card, each with a copy button. Both are on by default;
  turn them off in Settings, General. Apps saved as 127.0.0.1 open on the address your browser used, so they
  work from a phone.
- Downloads show the download client's own state, so a paused client shows Paused.
