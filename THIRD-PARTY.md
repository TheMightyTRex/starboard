# Third-party software and data

Starboard is written with Python's standard library and plain HTML, CSS and JavaScript. These open-source
projects and free data sources are used too, with thanks.

## Software

| Project | Used for | Licence |
|---|---|---|
| [Pillow](https://python-pillow.github.io/) | Turning Live TV channel logos white (only while Live TV and White channel logos are on; Settings, Jellyfin) | MIT-CMU (HPND) |
| [cryptography](https://cryptography.io/) | Encrypting full backups (AES-256-GCM; only while a full backup is made or restored; System, Backup and restore) | Apache-2.0 or BSD-3-Clause |
| [Lucide](https://lucide.dev/) | Icons | ISC (`tools/LICENSE-lucide.txt`) |
| [Atkinson Hyperlegible Next](https://www.brailleinstitute.org/freefont/) | The typeface | SIL Open Font Licence (`web/fonts/LICENSE-OFL.txt`) |

## Data

| Source | Used for |
|---|---|
| [dashboard-icons](https://github.com/homarr-labs/dashboard-icons) | App icons (can be switched off in Settings, About and updates) |
| [i.mjh.nz](https://github.com/matthuisman/i.mjh.nz) by Matt Huisman | Samsung TV Plus and Pluto TV channel lists and guides (Live TV) |
| [epgshare01](https://epgshare01.online/) | TV guides for the channels in `guide-map.txt` (Live TV) |
| [tv-logo/tv-logos](https://github.com/tv-logo/tv-logos) | Better logos for a few channels (Live TV) |
