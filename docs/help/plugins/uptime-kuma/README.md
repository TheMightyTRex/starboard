# Uptime Kuma
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Uptime Kuma, status checks for websites and services, with alerts and status pages. Starboard already watches your apps; this is for more.

An app plug-in for Starboard (plug-in API 1.14 or later): Uptime Kuma runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (3001 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People who want status checks beyond their apps: websites, a router, ports and certificates, with status pages. Starboard already watches your apps and sends alerts, so most people do not need it.

## Set it up

1. Activate it, choose **Open Uptime Kuma** and make its admin account.
2. Add the checks you want. Its status pages are on your home network only, unless you share them yourself.

## What it may do

- It can change: Its own folder in Starboard's data (data/plugins/uptime-kuma).
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its images, pinned by digest:

- `app`: `docker.io/louislam/uptime-kuma@sha256:d213a1d2b6a7d7c00afbcb936b53f585afea3e1620432b3a161b68bfffa13dac`

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 13 November 2026 | 115.6 MiB | 0.0% |

## Removing it

**Settings**, **Plug-ins**, Uptime Kuma, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Uptime Kuma itself is under the MIT licence, made by others: https://github.com/louislam/uptime-kuma

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
