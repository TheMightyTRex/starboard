# Wizarr
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Wizarr, invitation links for Jellyfin: send someone a link and they make their own Jellyfin account, with the libraries you choose.

An app plug-in for Starboard (plug-in API 1.14 or later): Wizarr runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (5690 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People who share their Jellyfin with family and friends: send a link, and the person makes their own Jellyfin account with the libraries you chose, with an expiry if you want one.

## Set it up

1. Activate it, choose **Open Wizarr** and make its admin account.
2. Add your Jellyfin: the address `http://host.docker.internal:8096` and an API key you make in Jellyfin's Dashboard, API keys. Starboard does not hand Wizarr its own key.
3. Invitation links work on your home network. For people away from home, use the Remote access plug-in or your own address.

## What it may do

- It can change: Its own folder in Starboard's data (data/plugins/wizarr).
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its images, pinned by digest:

- `app`: `ghcr.io/wizarrrr/wizarr@sha256:08f2c6de534ec7d36d39a4f55b7c5c379021ca881dc519c702aad0ddafbdc67a`

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 13 November 2026 | 126.8 MiB | 0.02% |
| 13 November benchmark (`bench-2026-11-13/RESULTS.md`, no limits) | 124.5 MiB | 0.02% |

## Removing it

**Settings**, **Plug-ins**, Wizarr, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Wizarr itself is under the MIT licence, made by others: https://github.com/wizarrrr/wizarr

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
