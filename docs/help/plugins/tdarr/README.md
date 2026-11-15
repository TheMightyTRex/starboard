# Tdarr
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Tdarr converts films and series to save space, in Starboard's quiet hours. It can copy the Tdarr you already have, with its libraries and history.

An app plug-in for Starboard (plug-in API 1.14 or later): Tdarr runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (8265 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People who want their films and series converted to save space (H.265), and people who ran Tdarr in the main install before.

## Set it up

1. If the main install runs Tdarr, choose **Bring in the Tdarr you already have** on the plug-in's page **before** activating it. Starboard stops your Tdarr (it does not remove it) and copies its `server`, `configs` and `logs` folders into the plug-in, so its libraries, flows, history and its key for Starboard carry over. Your Tdarr's own folders are never moved, changed or deleted. Its cache (files part way through converting, often many gigabytes) is not copied. From 1.0.2 the plug-in converts in a `tdarr-cache` folder in your media folder, on the same drives as your films, so the system disk does not fill.
2. Activate it. Its page is on your home network at port 8265 when that is free (it is once your old Tdarr is stopped), so Starboard's Settings, Tdarr page keeps working with the address it had.
3. Choose what it does in the **Settings** section of the plug-in's page, or in **Settings**, **Tdarr**: **When** is **In quiet hours** by default (Starboard's download hours when they are set, otherwise 01:00 to 06:00).
4. When the plug-in shows your libraries, remove Tdarr from the main install: **Settings**, **Install apps**, untick Tdarr and apply (or delete the `tdarr:` entry in `data/stack/compose.yaml`). Its old folders (`config/tdarr` beside the other apps' settings) stay until you move them to the holding folder in **System**, **Clean up**.
5. A new Tdarr with no Tdarr before: activate it, then in **Settings**, **Apps**, choose **Search for new apps** so Starboard finds it and gives it a key.

## What it may do

- It can change: Its own folder in Starboard's data (data/plugins/tdarr).
- It can change: Files in your media folder under movies: it can change, replace and remove them.
- It can change: Files in your media folder under tv: it can change, replace and remove them.
- It can change: Files in your media folder under tdarr-cache: its working copies while it converts.
- It can change: It runs as the owner of your media folder, so the files it adds there are yours to move or delete.
- It can change: Only if you choose it: a copy of the Tdarr you already have, put in its own folder (your app's own folders are read, never changed).
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs as the owner of your media folder (plug-in API 1.12's `"user": "media"`: the apps' user from Install apps, 1000 on a usual install), so it can replace a file with its smaller copy and the new file is yours. It can change, replace and remove files in `media/movies` and `media/tv`, and keep its working copies in `media/tdarr-cache`, and only there: that is the least a converter needs. It gets up to 2 GB of memory and 2 processor cores while converting; at rest it uses far less (below).

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its images, pinned by digest:

- `server`: `ghcr.io/haveagitgat/tdarr@sha256:84743e5ae433a5b49cb463b2dff2679eb02f0cac24fb88c830f49bf8aa9f1c04`

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 13 November 2026 | 59.1 MiB | 0.11% |
| 13 November benchmark (`bench-2026-11-13/RESULTS.md`, no limits), server only, no internal node | 31.1 MiB | 0.07% |

## Removing it

**Settings**, **Plug-ins**, Tdarr, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings, history and converted-file records):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**, from where you can put it
back or delete it for good. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Tdarr itself is free to use but not open source, made by others: https://tdarr.io

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
