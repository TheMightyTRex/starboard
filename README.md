# Starboard

**A complete media server, set up from one place, light enough for an old laptop or a Raspberry Pi.**

## Quick start

Start with the **Run first script**. On any Linux computer, with or without a desktop, open a terminal and run:

```bash
curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
```

If it says "Command 'curl' not found" (Ubuntu Desktop does not include curl), use `wget`, which it does include.
Do not use the `sudo snap install curl` Ubuntu suggests: the snap version cannot save the files the script needs.

```bash
wget -qO- https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash
```

Typing it? Type it exactly: everything after `TheMightyTRex/starboard/` is case-sensitive, so `main/run-first.sh`
must be in small letters with a hyphen, or GitHub answers 404 (not found). The `|` (vertical bar) is in different
places on different keyboards: on a UK keyboard it is **Shift**
and the `\` key next to the left **Shift**, not the `¦` key. The help has
[where each symbol is](docs/help/basics/the-terminal.md#symbols-that-are-in-different-places-on-different-keyboards)
on US, UK, German, French and Spanish keyboards. Or use these two commands, which have no `|`:

```bash
curl -fsSL -o run-first.sh https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh
bash run-first.sh
```

It checks the computer, installs Docker and anything else missing after you say yes, downloads Starboard and
starts its installer. Type `a` at its first question for accessible mode, which carries on through the whole
installation.

**With a desktop: set up in the browser.** When the installer finishes, the set-up page opens in your browser by
itself, with the setup code filled in.

**With no desktop: set up in the terminal.** On the server, or connected to it over SSH, the script sees there is
no desktop and asks every set-up question in the terminal instead: your password, your apps and your download
hours. To choose the terminal yourself:

```bash
curl -fsSL https://raw.githubusercontent.com/TheMightyTRex/starboard/main/run-first.sh | bash -s -- --terminal
```

![The Run first script's welcome page in a terminal: the Starboard logo in blocks, what the script will do, and a choice to finish setting up in a browser (recommended, as this computer has a desktop) or here in the terminal](docs/screenshots/run-first.jpg)

**New to all this?** Follow the beginners' guide,
[Get Starboard up and running, from a bare computer](docs/help/guides/get-up-and-running.md). It starts with
installing Linux, then takes you through either path step by step. Check
[what you need to run Starboard](docs/help/topics/what-you-need.md) first. Already have Docker and git?
`git clone https://github.com/TheMightyTRex/starboard.git && cd starboard && ./install.sh` (add `--terminal` for the
terminal set-up).

## What Starboard does

Starboard sets up and runs a whole home media server: the apps that find, download and sort your films, series,
music, books and audiobooks, the apps that play them, and the server underneath. You set it up in a browser or,
on a server with no desktop, entirely in the terminal. Then you run everything from one accessible dashboard.

- **Lightweight first.** Starboard itself idles in about 16 MB of memory and almost no processor time
  ([Testing and system use](docs/TESTING.md)). A whole recommended media server, Starboard with qBittorrent,
  SABnzbd, Jellyfin and Audiobookshelf, used about 290 MB at rest on a clean Debian test machine, before any
  films were added. Every piece of background work can be stopped or slowed down.
- **One simple set-up, complete.** The set-up asks what you want (films, series, music, books, audiobooks, Live TV),
  picks the apps, folders and settings for it, checks every step, starts the apps and connects them to each other.
- **Accessible to everyone.** Built to WCAG 2.2 AA: keyboard first, screen readers, text up to 175%, high contrast,
  and a plain terminal mode for software that reads text aloud.
- **Runs on what you have.** 64-bit Intel and AMD, 64-bit ARM such as a Raspberry Pi 4 or 5, and 32-bit ARM, with
  Docker, or with Python and systemd and no Docker at all.

The [help centre](docs/help/README.md) explains everything else in plain steps.

![Apps, in the Health first design](docs/screenshots/apps.png)

## Set it up your way: in the browser or in the terminal

**In the browser.** Install Starboard with one command, open it from any phone or computer at home, and the
set-up guide takes it from there. **Install apps** builds a complete media server for you: say what you want, and
it chooses the apps, the folders and the ports, explains what each app does, writes one Compose file, starts the
apps when you say so, and talks you through connecting them. It can join several drives into one pool, and point
the new apps at the media folders your old ones already use.

**In the terminal, with no browser at all.** For a server with no desktop and no second device, run
`./install.sh --terminal`, and every set-up question is asked in the terminal instead: your password (typed
hidden), the apps for your media server with their folders and VPN details, and the hours downloads may run.

- Each step has a heading box, a progress bar and a menu on the bottom line, which stay in place while only the
  lines between them scroll. It fits any window, and draws itself again when the window changes size.
- Enter takes the recommended answer, **b** goes back a step with your answers kept, **?** opens help over the
  step, and **q** stops with nothing changed.
- **f** sends feedback about the step you are on. A computer that is not online yet can show the report as a QR
  code drawn in the terminal: scan it with your phone to send it from there.
- `STARBOARD_PLAIN=1` gives plain numbered lines that never redraw, for screen readers.

| | |
|---|---|
| ![The terminal set-up at 80 by 24, step 2 of 10, How to start: the heading box and progress bar at the top, New install, Move from apps you already run and Restore a backup, each with a line under it, and the menu on the bottom line](docs/screenshots/terminal-setup.jpg) | ![Feedback from the terminal: a QR code drawn in the terminal, with the link under it](docs/screenshots/terminal-feedback-qr.jpg) |
| **The terminal set-up** in an 80 by 24 window | **Feedback** as a QR code, in an 80 by 30 window |

## Reelix

[Reelix](https://github.com/demonzoned/Reelix) is one app that finds, downloads and sorts films, series, music and
books, and takes requests: the work of Radarr, Sonarr, Lidarr, Readarr, Prowlarr and Seerr, in under 40 MB of
memory. Starboard shows Reelix like any other app, with its queue, what is coming up and its health, and before
Reelix updates, **What is new** lists the changes from Reelix's own changelog.

The plan is for Starboard and Reelix to install together from one set-up: Starboard installs Reelix in its own
container, sets it up through Reelix's own API, and then shows everything it does. Until then, add Reelix in
**Settings, Apps, Manage apps** like any other app. Reelix is a separate project with its own licence (GPL-3.0);
Starboard talks to it over its API only.

## Works with the apps you already have

Starboard finds the apps already running on your server and adds them, with their API keys when it may. **Install
apps** can install any of the ones marked "can install".

| What for | Apps |
|---|---|
| Finding and downloading | Reelix, Sonarr, Radarr, Lidarr, Readarr (and Bookshelf, its maintained version), Prowlarr, Kapowarr, Whisparr (can install Sonarr, Radarr, Lidarr, Bookshelf, Prowlarr and Kapowarr) |
| Download apps and VPN | qBittorrent, SABnzbd, Transmission, Deluge, NZBGet, and Gluetun for a VPN (can install qBittorrent, SABnzbd and Gluetun) |
| Watching and listening | Jellyfin, Plex, Emby, Audiobookshelf, Navidrome, Kavita, Komga, Calibre-Web, Storyarr (can install Jellyfin, Audiobookshelf and Storyarr) |
| Requests and users | Seerr, Jellyseerr, Overseerr, Wizarr, Jellystat, Tautulli (can install Seerr, Wizarr and Jellystat) |
| Subtitles and tidying | Bazarr, Profilarr, Decluttarr, Janitorr, Unpackerr, FlareSolverr, Tdarr (can install all) |
| Live TV | Dispatcharr (can install), and Starboard's own free Live TV channels and guides for Jellyfin |
| The rest of the server | Dozzle (can install), Portainer, Uptime Kuma, Homepage, Homarr, Grafana, Pi-hole, AdGuard Home, Home Assistant, Immich, Nextcloud, Paperless, Syncthing, Vaultwarden |

## Screenshots

All made with example data (`tools/screenshots.sh`).

| | |
|---|---|
| ![System, Storage: the pool by type, with free space](docs/screenshots/storage.png) | ![System, Storage in dark mode](docs/screenshots/storage-dark.png) |
| **Storage:** the pool by type, with free space | **Storage** in dark mode |
| ![Each drive in the pool, fullest first](docs/screenshots/storage-drives.png) | ![Space used over time, with a forecast of when the pool fills](docs/screenshots/storage-history.png) |
| **Drives in the pool**, fullest first | **Space used over time**, with a forecast |
| ![System, Overview: Jellyfin with its status beside the name](docs/screenshots/jellyfin.png) | ![Release notes, opened from the version in the footer](docs/screenshots/release-notes.png) |
| **Jellyfin** on System, Overview | **Release notes** from the footer |
| ![Install apps: groups such as Movies and TV](docs/screenshots/install-apps.png) | ![Search for new apps, in a slide-out on Manage apps](docs/screenshots/search-new-apps.png) |
| **Install apps:** set up a media server in groups | **Search for new apps** |
| ![The set-up guide's first step](docs/screenshots/setup-guide.png) | ![The upgrade guide: what is new, then only the new questions](docs/screenshots/upgrade-guide.png) |
| **Set-up guide** after the first password | **Upgrade guide** after an upgrade with choices |
| ![The notice after an upgrade, with Open the upgrade guide](docs/screenshots/upgrade-notice.png) | ![Settings, Performance: presets and a switch for each piece of background work](docs/screenshots/performance.png) |
| **After an upgrade** | **Settings, Performance:** what each part costs |
| ![System, Logs: the log, Report a problem, Download and Delete logs](docs/screenshots/logs.png) | ![The log, newest first, with Everything, Problems and Detailed](docs/screenshots/logs-entries.png) |
| **Logs**, with Report a problem | **The log**, newest first |
| ![Settings, General: how long to keep logs, and detailed logging](docs/screenshots/logs-settings.png) | ![Settings, Apps, Audiobookshelf: each account, the Audiobookshelf user it goes to, and how many books were applied](docs/screenshots/audiobookshelf.png) |
| **Log settings** | **Listening progress** into Audiobookshelf |
| ![Display and accessibility, a slide-out with the header in the page colour](docs/screenshots/display.png) | ![Copy app settings: what will be added, what is already there and what will be replaced](docs/screenshots/copy-settings.png) |
| **Display and accessibility** | **Copy app settings** |
| ![Apps with the notice that Reelix is updated to 0.7.1, with What is new](docs/screenshots/reelix-notice.png) | ![What is new in Reelix: the waiting update's changes from its changelog, under Added and Fixed](docs/screenshots/reelix-whats-new.png) |
| **After a Reelix update** | **What is new in Reelix** |
| ![System, Storage, Pool: the drives in the pool, each with its space and role](docs/screenshots/pool.png) | ![Add a drive: the check before anything changes, with the exact steps](docs/screenshots/pool-add-3-check.png) |
| **Pool:** the drives in the pool | **Add a drive:** the check before anything changes |
| ![Settings, Updates, Releases: every version in its own section, the one you have open, with a count for each type of change](docs/screenshots/releases.png) | ![Settings, Updates, Restore: Restore your settings with the saved copies, and Go back to an earlier version](docs/screenshots/restore.png) |
| **Releases**, one section each | **Restore** your settings |
| ![Apps on a phone](docs/screenshots/apps-phone.png) ![Storage on a phone](docs/screenshots/storage-phone.png) | |
| **On a phone** | |

## Design principles

Lightweight comes first. Every change to Starboard has to keep it small and quiet:

1. **Very little processor time and memory.** Measure before and after a change; idle use must stay near zero.
   Measured: 15 to 27 MB idle, 37 MB at its busiest, and it runs in a 24 MB memory limit. It installs and runs
   on 64-bit ARM with 512 MB of memory, like a Raspberry Pi Zero 2 W ([Testing and system use](docs/TESTING.md)).
2. **Almost no third-party packages.** Python's standard library and plain HTML, CSS and JavaScript. The one
   exception is Pillow, open source and credited, used only while Live TV's white logos are on.
3. **Nothing runs unless it is needed.** Work happens when a page that shows it is open, or on a schedule you
   turned on. Hidden tabs stop refreshing.
4. **Ask the apps as little as possible.** Share and cache answers rather than asking again for each tab or
   device; fetch only what a page shows.
5. **Small to send.** Files are cached by the browser and compressed; images are small and kept locally
   where possible.
6. **Only the access you allow.** Each kind of access is optional, asked for by the installer and listed in
   Settings.
7. **You choose what runs.** Settings, Performance shows Starboard's own use, offers presets (Small server,
   Balanced, Everything, Custom) and lets you switch off, or slow down, every piece of background work.
8. **Accessible to everyone.** WCAG 2.2 AA, built on the shared component library.

## Everything it does

- **Every page has its own address:** `/index.html` (Apps), `/search.html`, `/downloads.html`,
  `/upcoming.html`, `/system.html`, and Settings as `/settings.html` (Apps), `/settings-general.html`,
  `/settings-security.html` and `/settings-updates.html`. Searches link too: `/search.html?q=dune`.
- **Apps by category, with their own icons.** Icons come from the
  [dashboard-icons](https://github.com/homarr-labs/dashboard-icons) collection; Starboard keeps a copy in `./data/icons`.
  Put your own `name.svg` or `name.png` there and use that name as the app's icon.
- **A fixed header on every page**, with the main menu and a section's sub-menu as the same square tabs,
  search and Display. On phones a menu drawer holds both. The look matches Storyarr.
- **Five designs:** Health first (the default: apps that are not responding go to the top), Tiles, Shelf,
  Command and Status board. Change the default in Settings; anyone can pick their own in Display.
- **Display and accessibility:** theme (match device, light, dark), text size up to 175%, high contrast,
  reduce motion, underline links and wider text spacing. Built to WCAG 2.2 AA, with 44px controls and the
  Atkinson Hyperlegible Next typeface.
- **Coming up** as a list or a month calendar, with posters, as far ahead as you choose.
- **Download hours:** qBittorrent and SABnzbd download only between the hours you set, with Resume and
  Pause on the Downloads page, plus download speeds and the VPN's state (Gluetun) at the top.
- **Requests** from Seerr, Jellyseerr or Overseerr, with Approve and Decline; **Finished this week** from
  your apps' history.
- **Alerts** to ntfy, Gotify or a webhook when an app stops answering, a disk has a problem or gets full, a
  download is stuck, a backup fails or a certificate runs out; **uptime history** for each app; an optional
  **weekly summary**. Off until you turn it on in Settings, Alerts.
- **Jellyfin** on System, Overview: update or restart needed, Live TV guide, what is playing (and whether it
  is being converted) and what was added.
- **Drive pools** (System, Storage, Pool): add a drive to one pool (keeping its files, or erasing and preparing
  it), balance the files, take a drive out, and make a drive a backup with SnapRAID parity or a nightly copy.
  Every change is checked first with the exact commands, and needs your password again. A small helper does the
  work as root, installed only if you say yes in `./install.sh`.
- **Storage charts:** each pool as a bar and a ring by type (TV, films, books and more) with free space, each
  drive in the pool, space used over time with a forecast, and the biggest series and films. Sorting by type
  reads every file name, so it runs only when you choose (Settings, Performance).
- **Server jobs** (such as a check of every app) with Run now; **Disk health** with 30-day temperatures;
  **Storage** with what is using the space and every drive; **Monitor** with each app's processor and memory.
- **Jellyfin extras** (Settings, Apps, Jellyfin), each off until you turn it on: free **Live TV** channels and
  guides with Sky-style numbers and white logos; **import watch history** from Plex, Emby or another Jellyfin;
  **defaults for every user**. Set-up offers them when it finds Jellyfin.
- **Copy app settings** (Settings, Apps, Manage apps): tags, quality profiles, folders, download clients and naming from
  one Sonarr, Radarr or Lidarr into another, with a preview first and the hidden passwords asked for.
- **Listening progress** (Settings, Apps, Audiobookshelf): copies where everyone is in each audiobook, and what they
  finished, from Plex, Jellyfin, Emby or another Audiobookshelf. Books are matched by ASIN, ISBN, title and author,
  or folder; progress people already have is never changed, and books not found are listed. It needs an admin API
  key from Audiobookshelf (Settings, API Keys): Starboard uses it to make a key that acts as each person for a few
  minutes, and deletes that key straight after.
- **Search for new apps** (Settings, Apps, Manage apps) finds apps on this computer and adds the ones you tick, with
  their API keys if Starboard has Docker access. It runs only when you press it.
- **Install apps: a complete *arr stack for beginners.** Never set one up? The guide explains what each app does,
  picks the apps for what you want (Movies, TV, Music, Ebooks, Audiobooks, Comics, Watching, Downloads, VPN and
  more) and sensible folders, checks every step, and can join several drives into one pool. It writes a Compose
  file into `data/stack`, shows it, and starts the apps only when you press Start and give your password (with
  Docker access), or gives you the command to run. Then it talks you through connecting each app, with the exact
  addresses and folders. **Advanced settings** shows every app, folder and number. It can point the new apps at the
  media folders your other apps already use.
- **A set-up guide** after the first password, and an **upgrade guide** after an upgrade that brings something
  to choose. The version in the footer opens the release notes.
- **Almost no third-party packages:** Python's standard library and plain HTML, CSS and JavaScript, plus Pillow
  for Live TV logos (see Credits).

## Install

Two ways: the **ready-made image** (quickest; nothing to build), or the **installer** (builds from this
repository and asks, step by step, what Starboard may access).

### The ready-made image

Images for amd64, arm64 (such as a Raspberry Pi 4 or 5 on a 64-bit system) and 32-bit arm (armv7, such as a
Raspberry Pi 2 or 3 on a 32-bit system) are published for every release
at `ghcr.io/themightytrex/starboard`. Download [`compose.image.yaml`](compose.image.yaml), then:

```bash
mkdir -p data
docker compose -f compose.image.yaml up -d
```

Open `http://<your server>:8095`. The setup code is in the log: `docker logs starboard`. The file explains each
optional extra (Docker access for System, Apps, Updates; folders for System, Storage) as comments you can uncomment.
Update with `docker compose -f compose.image.yaml pull && docker compose -f compose.image.yaml up -d`.

### The installer

You need Docker with the Compose plugin (or Python 3.10+ and systemd for `--native`), and git.

```bash
git clone https://github.com/TheMightyTRex/starboard.git
cd starboard
./install.sh
```

The installer prints two addresses: one for this computer and one for phones and other computers on your
home network, plus a one-time setup code. Open either address, enter the code and choose a password (at least
10 characters). Then go to **Settings, Apps, Manage apps** and add your apps. Use `127.0.0.1` and each app's port
(for example `http://127.0.0.1:8989` for Sonarr) as the address the server uses.

### What the installer does, and what it asks

`./install.sh` explains each step before it runs it, and asks before giving Starboard any access to your
computer. Every kind of access is optional: say no and only that part of Starboard is missing. Run
`./install.sh` again at any time to change your answers; your settings and password stay.

1. **Checks what is installed:** Docker and Docker Compose (or Python and systemd). It changes nothing.
2. **Asks what Starboard may access** (the table below).
3. **Saves your answers** in `.env` (readable by you only) and `compose.access.yaml`. Both are ignored by git.
4. **Builds and starts Starboard** with `docker compose up -d --build`, or a systemd service for your user
   with `--native`. Neither needs `sudo`.

| Access | What it is for | What it means for your computer | Default | Change it |
|---|---|---|---|---|
| Home network | Phones and computers on your network can open Starboard | Starboard listens on your network, behind your password | Yes | Settings, Security (`--local-only` on a new install) |
| Docker | **System, Apps, Updates**: check for and install new app images | The Docker socket is mounted: full control of Docker, so of the computer | No | `--docker`, `--no-docker` |
| Per-app use | **System, Overview, Monitor**: each app's processor and memory | `/sys/fs/cgroup` is mounted read-only; two small files per container are read while Monitor is open | No | `--app-use`, `--no-app-use` |
| Live TV folder | **Settings, Apps, Jellyfin**: free channels and guides for Jellyfin | Jellyfin's Live TV folder is mounted read-write; Starboard writes playlists, guides and logos there once a day while Live TV is on | None | `--livetv-folder /path`, `--no-livetv` |
| Folders | **System, Storage**: free space | Each folder is mounted read-only; Starboard reads sizes, not files | None | `--disk Name=/path`, `--no-disks` |
| Disk health | **System, Disk health**: each drive's SMART report, and the drive list on Storage | Runs `deploy/install-smart.sh` with `sudo`: a systemd timer runs `deploy/starboard-smart.sh` (smartctl and lsblk, as root) every 30 minutes and saves reports in `./smart`. Starboard may write only to `./smart/requests`, to ask for a reading now | No | `--disk-health`, `--no-disk-health` |

`--yes` answers without asking: the options you give, then your last answers, then No. To remove the Disk
health timer, run `sudo deploy/install-smart.sh --remove`.

Some access is a switch in Settings instead, because it needs nothing from the installer:

- **Your apps** (Settings, Apps, Manage apps): Starboard reads status, queues and calendars with the API keys you
  give it, and adds films, series and books only when you choose Add.
- **Download hours** (Settings, General): pauses qBittorrent and SABnzbd outside the hours you choose. Off
  until you turn it on. It needs each client's API key (qBittorrent 5.2 or later).
- **GitHub** (Settings, Updates): looks for new Starboard releases, at most every 6 hours.
- **The dashboard-icons collection** (Settings, Updates): downloads each app's icon once.
- **Posters** (Settings, Updates): the server fetches small posters for Coming up from your own
  apps and keeps copies for a week. Search results still show covers from the sites your apps use, such as TMDB.

**Settings, Updates, What Starboard can access** lists all of these, says which are on now, and
gives the switch or the command to change each one.

### Home network or this computer only

**Settings, Security, Who can open the dashboard** switches between your home network (the default) and this
computer only. The change takes effect at once: Starboard stops listening on the network, so other devices
cannot connect at all. Install with `--local-only` to start that way. The Docker setup uses host networking
so this works (Docker on Linux).

### App updates

With Docker access, **System, Apps, Updates** lists every app on the Apps page in the same categories, with the
container it runs in, the version installed and the newest one. **Check again** asks each image's
registry (only a few small files are downloaded). **Update** downloads the new image and runs
`docker compose up -d` for the app's Compose project, in a short-lived `docker:cli` container, so anything
that depends on it restarts too. An image pinned to a version (such as `v1.4.2`) is offered the newest
higher version; Starboard copies the Compose file before it changes the tag. If the project folder has
`starboard-before-update/<service>.sh`, that runs first (a database backup, for example), and if it fails
nothing changes. Starboard finds each app's container by name; choose another in the app's settings.

### Your own folders and disks: compose.override.yaml

Keep anything else specific to your server in `compose.override.yaml` next to `compose.yaml`. Git ignores
it, and `./install.sh` and `./update.sh` leave it alone. For example, folders you set up by hand:

```yaml
services:
  starboard:
    volumes:
      - /mnt/media:/disks/media:ro          # Storage page
      - /var/lib/starboard-smart:/smart:ro  # Disk health page
```

with `STARBOARD_DISKS=Media=/disks/media` and `STARBOARD_SMART_DIR=/smart` in `.env`. The installer sees
folders set up this way and leaves them as they are.

### Drive pools

**System, Storage, Pool** joins drives into one folder, `/mnt/pool`, with mergerfs; balances the files across
them by whole folders; and makes a drive a backup drive: parity with SnapRAID, or a nightly copy with rsync. It
can also take a drive out of the pool, moving its files to the others first. `./install.sh --terminal` asks the
same questions in its **Your drives** step.

Starboard itself never runs as root and never touches a drive. The pool helper does, installed with sudo by
`./install.sh` (answer Yes to **Set up Drive pools?**) or by hand:

```bash
sudo deploy/install-pool.sh "$PWD/pool"
```

It is one standard-library Python file, `starboard/pool_helper.py`, installed as `/usr/local/bin/starboard-pool`.
Starboard drops a small request in `pool/requests` (the one folder it may write) and reads the answers in
`pool/status`. The helper:

- accepts only a fixed list of actions, and never runs a command taken from a request;
- plans every change first (a dry run with the exact commands), and refuses the plan if a drive changed since or
  the check is more than 15 minutes old;
- erases a drive only with the last 4 characters of its serial number, and Starboard asks for the password again
  before it sends any change;
- never offers the system drive or a drive in RAID, LVM or ZFS, changes only its own lines in `/etc/fstab`
  (saving a copy first) and only a `snapraid.conf` it wrote, and leaves a pool made by hand alone.

Needs `mergerfs`, `rsync` and `gdisk` (and `snapraid` for a parity drive). Test it only in a throwaway virtual
machine: `tools/vm/vm.sh pool debian` adds five blank virtual drives and runs every step, then restarts.

### Backup and restore

**System, Backup** downloads Starboard's settings as a file (your apps, API keys, categories and
settings, never your password) and restores from one. Starboard also keeps copies of its settings in
`./data/backups` before a restore or an update that changes them.

For the whole server, Starboard works with a backup job that runs on the host, so it never needs to read the
server itself. Point it at two folders in `compose.override.yaml` and `.env`:

- `STARBOARD_JOBS_DIR`: a folder with a `requests` folder inside. **Back up the server now** creates an empty
  file in `requests`: `backup`, or `backup-with-prompt` when **Include a rebuild prompt** is
  ticked. Your job (for example a systemd path unit) runs, removes it, and writes `backup.json` (or
  `backup-with-prompt.json`) with `status` (`running`, `done` or `failed`), `started`, `finished` and `summary`.
  Mount the folder read-only and its `requests` folder read-write.
- `STARBOARD_BACKUP_DIR`: where the job saves its files, mounted read-only, so the page can list them.

### Other services

Services with no web page of their own (a VPN, an unpacker, a clean-up job) go under **System, Apps, Other services**:
tick **Background service** when you add them. A service with no address can follow another app's status.

## Update

```bash
./update.sh
```

It backs up `./data` to `./backups`, installs the newest release, and goes back to the version you had (with
your settings restored) if the new one does not start. `./update.sh --check` only checks;
`./update.sh --to v0.1.0` installs a particular release, which is also how you go back.

After an upgrade, select the version in the footer for the release notes. If the release brings settings worth
choosing, a notice opens the upgrade guide, which asks only those questions; you can leave it for later. How
releases are made is in [docs/RELEASING.md](docs/RELEASING.md).

## Security

- One password (at least 10 characters), hashed with PBKDF2-SHA256 (600,000 rounds). Without Remember me,
  you are signed out when the browser closes, or after a day. Five wrong attempts lock an address out for
  15 minutes. The first password needs the setup code from the installer.
- Sign-in cookies are `HttpOnly` and `SameSite=Strict`. Every change also needs a header only the dashboard's
  own pages send, and a matching `Origin`.
- API keys stay in `./data/config.json` (readable by you only) and are never sent to the browser.
- A strict Content Security Policy: no inline scripts, nothing loaded from other sites except cover images.
- The container runs as your user, read-only, with every Linux capability dropped. It has the Docker socket
  only if you say yes to app updates.
- Install apps starts containers only from its own list of images, with folders it has checked (never a system
  folder), and asks for your password first. Starting containers through Docker is as powerful as root, so it
  needs the Docker access you chose at install.
- Other devices on your home network can open it unless you switch that off in Settings. To use it away from home, put it behind a VPN or a reverse
  proxy with HTTPS (set `STARBOARD_TRUST_PROXY=1` and turn on HTTPS-only cookies in Settings). Do not forward
  the port straight to the internet.

See [SECURITY.md](SECURITY.md) to report a problem, and
[Security: how Starboard protects you, and how it was tested](docs/SECURITY-AND-TESTS.md) for the review and
the security tests.

## Keep your details out of the repository

Settings, API keys, sessions and backups live in `./data`, `./backups` and `.env`, which git ignores. Before
contributing, run `tools/install-hooks.sh`: every commit is then checked for home network addresses, dynamic
DNS names, email addresses, keys and the words you list in `.private-words` (also ignored by git).

## Develop

```bash
STARBOARD_DATA=./data python3 -m starboard     # http://127.0.0.1:8095
python3 -m unittest discover -s tests
python3 tools/apply_shell.py                   # after changing the header or menu
tools/screenshots.sh                           # retake the README screenshots from example data
tools/journeys.sh                              # browser journeys against example data
python3 tools/check-help.py                    # the help centre's links, layout and writing rules
tools/vm/vm.sh test ubuntu                     # a fresh install on a clean system (also debian, fedora, arm64)
```

What each test covers, and the latest results, are in [docs/TESTING.md](docs/TESTING.md).

The header and Display panel are written into every page by `tools/apply_shell.py`. Design tokens are in
`web/css/tokens.css`; the five designs in `web/css/designs.css`.

## Credits

Pillow, Lucide, Atkinson Hyperlegible Next and the data sources Starboard uses are listed, with their
licences, in [THIRD-PARTY.md](THIRD-PARTY.md).

## Licence

MIT, by TheMightyTRexUK and contributors. Atkinson Hyperlegible Next is under the SIL Open Font Licence (`web/fonts/LICENSE-OFL.txt`). Icons are from
Lucide, under the ISC licence (`tools/LICENSE-lucide.txt`).
