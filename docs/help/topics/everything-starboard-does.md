[Help centre](../README.md) · Before you install · reference

# Everything Starboard does

A list of what Starboard can do, by area, and the apps it works with. Each item links to the help for it.

## The dashboard

- **Apps by category, with their own icons,** and five designs: Health first (apps that are not responding come
  first), Tiles, Shelf, Command and Status board. Read [Choose a design](choose-a-design.md).
- **Every page has its own address,** so you can bookmark any page, and searches too: `/search.html?q=dune`.
- **Display and accessibility:** light or dark theme, text up to 175%, high contrast, less motion, underlined links
  and wider spacing. Built to WCAG 2.2 AA. Read [Display and accessibility](display-and-accessibility.md).

## Your media

- **Search once, add anywhere.** Read [Search for something and add it](search-and-add.md).
- **Coming up** as a list or a month calendar. Read [See what is coming up](coming-up.md).
- **Downloads,** with pause and resume, speeds and the VPN's state, and **download hours**. Read
  [Manage downloads](manage-downloads.md) and [Set download hours](set-download-hours.md).
- **Requests,** with **Approve** and **Decline**. Read [Approve requests](approve-requests.md).
- **Jellyfin extras:** free Live TV channels and guides, watch history from Plex, Emby or another Jellyfin, and
  defaults for every user. Read [Set up Live TV](set-up-live-tv.md) and [Import watch history](import-watch-history.md).
- **Listening progress** into Audiobookshelf from Plex, Jellyfin, Emby or another Audiobookshelf. Read
  [Copy listening progress](copy-listening-progress.md).

## Your server

- **Install apps:** a complete media server in Basics, Full install or Everything, set up for you. Read
  [Install apps with Starboard](install-apps.md) and [Change your install](change-your-install.md).
- **Search for new apps** on this computer, with their API keys. Read [Search for new apps](search-for-new-apps.md).
- **Copy app settings** from one Sonarr, Radarr or Lidarr to another. Read [Copy app settings](copy-app-settings.md).
- **App updates** with a backup first. Read [Update your apps](update-your-apps.md).
- **Storage** with charts by type and a forecast, **Disk health**, and **Monitor** for each app's use. Read
  [Check storage](check-storage.md) and [Check disk health](check-disk-health.md).
- **Drive pools:** join drives into one folder, balance them, take one out, and keep a backup drive. Read
  [Add a drive to the pool](add-a-drive-to-the-pool.md).
- **Alerts** to ntfy, Gotify or a webhook, uptime history and a weekly summary. Read
  [Activate alerts](activate-alerts.md).
- **Backups** of Starboard's settings, and of the whole server through a job you run. Read
  [Back up Starboard's settings](back-up-settings.md) and [Back up the server](back-up-the-server.md).

## The apps it works with

Starboard finds the apps already running on your server and adds them. **Install apps** can install the ones
marked "can install".

| What for | Apps |
|---|---|
| Finding and downloading | Reelix, Sonarr, Radarr, Lidarr, Readarr (and Bookshelf, its maintained version), Prowlarr, Kapowarr, Whisparr (can install Reelix, Sonarr, Radarr, Lidarr, Bookshelf, Prowlarr and Kapowarr) |
| Download apps and VPN | qBittorrent, NZBGet, SABnzbd, Transmission, Deluge, and Gluetun for a VPN (can install qBittorrent, NZBGet, SABnzbd and Gluetun) |
| Watching and listening | Jellyfin, Plex, Emby, Audiobookshelf, Navidrome, Kavita, Komga, Calibre-Web, Storyarr (can install Jellyfin, Audiobookshelf and Storyarr) |
| Requests and users | Seerr, Jellyseerr, Overseerr, Wizarr, Jellystat, Tautulli (can install Seerr, Wizarr and Jellystat) |
| Subtitles and tidying | Bazarr, Profilarr, Decluttarr, Janitorr, Unpackerr, FlareSolverr, Tdarr (can install all) |
| Live TV | Dispatcharr (can install), and Starboard's own free Live TV channels and guides for Jellyfin |
| The rest of the server | Dozzle (can install), Portainer, Uptime Kuma, Homepage, Homarr, Grafana, Pi-hole, AdGuard Home, Home Assistant, Immich, Nextcloud, Paperless, Syncthing, Vaultwarden |

## How it is built

Light comes first. Starboard idles in about 16 MB of memory and almost no processor time, uses Python's standard
library and plain HTML, CSS and JavaScript, does work only when a page that shows it is open or on a schedule you
chose, and lets you pause or slow every piece of background work in **Settings**, **Performance**. Read
[Make Starboard lighter](make-starboard-lighter.md).

## Find out more

- [What Starboard is](../basics/what-is-starboard.md)
- [Basics, Full install and Everything: what each one has](install-types.md)
- [What Reelix is](../basics/what-is-reelix.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
