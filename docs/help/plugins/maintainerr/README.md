# Maintainerr
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Maintainerr, clean-up rules for Jellyfin, such as films everyone has watched. It changes nothing until you give it keys and a rule that removes.

An app plug-in for Starboard (plug-in API 1.14 or later): Maintainerr runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (6246 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People whose disks fill up: rules such as "films everyone has watched and older than 90 days", shown as a list first, then removed through Jellyfin or Seerr only when you add that action.

## Set it up

1. Turn it on, choose **Open Maintainerr**, and add Jellyfin (and Seerr if you have it) with keys you make in each app.
2. Make rules and check what they find. Nothing is removed until you give a rule an action and the keys allow it. Starboard gives Maintainerr no key and no media folder.

## What it may do

- It can change: Its own folder in Starboard's data (data/plugins/maintainerr).
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its images, pinned by digest:

- `app`: `ghcr.io/maintainerr/maintainerr@sha256:5dcd5bef9d49c614bb74453df3da198afc05a38d8e2cd96b3669bc2c76a94112`

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 13 November 2026 | 140.3 MiB | 0.0% |
| 13 November benchmark (`bench-2026-11-13/RESULTS.md`, no limits) | 127.4 MiB | 0.0% |

## Removing it

**Settings**, **Plug-ins**, Maintainerr, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Maintainerr itself is under the MIT licence, made by others: https://github.com/maintainerr/maintainerr

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
