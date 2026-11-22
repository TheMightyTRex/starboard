# Seerr
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Seerr, a requests page for Jellyfin users. Reelix already has requests in Starboard, so most people do not need it.

An app plug-in for Starboard (plug-in API 1.14 or later): Seerr runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (5055 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People whose Jellyfin users already know Seerr's request page. Reelix already has requests in Starboard (Downloads, Requests), so most people do not need it.

## Set it up

1. Activate it, choose **Open Seerr**, and sign in with your Jellyfin account; its set-up asks for Jellyfin's address (`http://host.docker.internal:8096`) and your libraries.
2. If you also use Reelix's requests, choose one place for people to ask, so requests are not made twice.

## What it may do

- It can change: Its own folder in Starboard's data (data/plugins/seerr).
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its images, pinned by digest:

- `app`: `ghcr.io/seerr-team/seerr@sha256:aadee014b40e28cf9aa4928bc9d1183a6eb08f8c44d543cddc9efdcb16549be2`

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 13 November 2026 | 182.5 MiB | 0.0% |
| 13 November benchmark (`bench-2026-11-13/RESULTS.md`, no limits) | 127.0 MiB | 0.0% |

## Removing it

**Settings**, **Plug-ins**, Seerr, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Seerr itself is under the MIT licence, made by others: https://github.com/seerr-team/seerr

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
