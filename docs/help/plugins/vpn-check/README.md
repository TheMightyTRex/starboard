# VPN check
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Shows the address and country your downloads use through the VPN, and warns if it is your home address.

An example Starboard plug-in by TheMightyTRexUK, MIT licence.

## What it may do

- It runs inside your VPN.
- It runs one small container (48 MB of memory at most).

## On the dashboard

- **VPN**: a status card.

## Settings

- **Your home's public address**: Optional, such as 81.2.69.160. If the VPN ever shows this address, the card turns red.
- **Check every**

## Add it

Needs Starboard with plug-in API 1.14 or later; a Starboard with an older plug-in API is offered the version before. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it under **Downloads**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/vpn-check/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
