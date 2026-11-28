# Uptime Kuma: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Uptime Kuma has no settings in Starboard. Everything is set in the app itself, on its own page: open it with **Open Uptime Kuma** on its tab.

## Buttons

Uptime Kuma's tab, in **Settings**, then **Plug-ins**, then **Uptime Kuma**, has these buttons:

- **Open Uptime Kuma** opens its own page in a new tab. It is there while it is active.
- **Turn on** starts it, and Starboard chooses a free port for its page. **Turn off** stops it and keeps its folder.
- **Try again** starts it again when it did not start.
- **Check for an update** is there when this Starboard is newer than the version was made for.
- **Remove Uptime Kuma** stops it and takes it away. You choose where its folder goes; nothing is deleted.

## Things to note

- Starboard already watches your apps and sends alerts. Uptime Kuma is for checks beyond them.
- Uptime Kuma reaches your home network and the internet, and this computer as `host.docker.internal`.
- Its status pages are on your home network only, unless you share them yourself.
- Uptime Kuma keeps its checks and history in its own folder in Starboard's data, `data/plugins/uptime-kuma`.
- Its settings are kept when you update or turn it off, and when you remove it they stay in its folder.

## Find out more

- [Install](../uptime-kuma/install.md)
- [Dashboard card](../uptime-kuma/dashboard-card.md)
- [Problems](../uptime-kuma/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
