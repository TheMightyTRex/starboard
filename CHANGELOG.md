# Changelog

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
