# Changelog

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
