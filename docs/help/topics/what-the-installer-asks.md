[Help centre](../README.md) · Install and update · reference

# What the installer asks, and what each answer means

`./install.sh` explains each step before it runs it, and asks before giving Starboard any access to your
computer. Every kind of access is optional: say no, and only that part of Starboard is missing. Run
`./install.sh` again at any time to change your answers; your settings and password stay.

## What the installer does, in order

1. **Checks what is installed:** Docker and Docker Compose, or Python and systemd with `--native`. It changes
   nothing.
2. **Asks what Starboard may access** (the table below).
3. **Saves your answers** in `.env` (only your user can read it) and `compose.access.yaml`. Git ignores both.
4. **Builds and starts Starboard** with `docker compose up -d --build`, or as a systemd service for your user with
   `--native`. Neither needs `sudo`.

## The access it asks for

| Access | What it is for | What it means for your computer | Answer when new | Change it |
|---|---|---|---|---|
| Home network | Phones and computers at home can open Starboard | Starboard listens on your network, behind your password | Yes | **Settings**, **Security**, or `--local-only` on a new install |
| Docker | **System**, **Apps**, **Updates**, and starting the apps Install apps sets up | Docker's socket is shared with Starboard: full control of Docker, so of the computer | No | `--docker`, `--no-docker` |
| Each app's use | **System**, **Overview**, **Monitor**: each app's processor and memory | `/sys/fs/cgroup` is shared read-only; two small files for each app are read while Monitor is open | No | `--app-use`, `--no-app-use` |
| Live TV folder | **Settings**, **Apps**, **Jellyfin**: free channels and guides for Jellyfin | Jellyfin's Live TV folder is shared; Starboard writes playlists, guides and logos there once a day while Live TV is on | None | `--livetv-folder /path`, `--no-livetv` |
| Folders | **System**, **Storage**: free space | Each folder is shared read-only; Starboard reads sizes, not files | None | `--disk Name=/path`, `--no-disks` |
| Disk health | **System**, **Disk health**: each drive's health report | Runs `deploy/install-smart.sh` with `sudo`: a timer reads each drive every 30 minutes as root and saves the reports in `./smart`; Starboard may only ask it for a reading now | No | `--disk-health`, `--no-disk-health` |
| Drive pools | **System**, **Storage**, **Pool**: join drives into one folder | Installs a small helper with `sudo` that changes drives only from a fixed list of actions, after a check | No | Answer **Set up Drive pools?** again |

`--yes` answers without asking: the options you give, then your last answers, then No. To remove the Disk health
timer: `sudo deploy/install-smart.sh --remove`.

## Access that is a setting instead

Some access needs nothing from the installer, so it is a setting in Starboard:

- **Your apps** (**Settings**, **Apps**, **Manage apps**): Starboard reads status, queues and calendars with the
  API keys you give it, and adds films, series and books only when you choose **Add**.
- **Download hours** (**Settings**, **General**): pauses the download apps outside the hours you choose.
- **Updates** (**Settings**, **Updates**): looks for new Starboard releases, at most every 6 hours, and downloads
  app icons and posters.

**Settings**, **Updates**, **What Starboard can access** lists all of these, says which are active, and gives the
setting or the command that changes each one.

## Your own folders: compose.override.yaml

Keep anything else particular to your server in `compose.override.yaml`, next to `compose.yaml`. Git ignores it,
and `./install.sh` and `./update.sh` leave it alone. The installer sees folders added this way and keeps them.

## Find out more

- [Install Starboard with the installer](install-with-the-installer.md)
- [Change what Starboard can access](change-what-starboard-can-access.md)
- [How Starboard keeps your server safe](../basics/how-starboard-keeps-you-safe.md)
- [Choose who can open Starboard](choose-who-can-open-starboard.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
