# Ad blocking
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How many adverts and trackers Pi-hole or AdGuard Home blocked today.

An example Starboard plug-in by TheMightyTRexUK, MIT licence.

## What it may do

- It reaches your home network and the internet.
- It runs one small container (48 MB of memory at most).

## On the dashboard

- **Blocked today**: a stat card.

## Settings

- **Which one**
- **Its address**: Such as http://192.0.2.2 for Pi-hole, or http://192.0.2.2:3000 for AdGuard Home.
- **User name**: AdGuard Home only.
- **Password**: Pi-hole's web password, or AdGuard Home's. Kept by Starboard.

## Add it

Needs Starboard with plug-in API 1.14 or later; a Starboard with an older plug-in API is offered the version before. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it under **Network**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/dns-blocking/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
