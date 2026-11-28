# Calibre-Web
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Calibre-Web, a browser page for a Calibre library: read, search and send books to an e-reader. It reads your books folder and never changes it.

An app plug-in for Starboard (plug-in API 1.14 or later): Calibre-Web runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (8083 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People who keep their books in a Calibre library (a folder with metadata.db) and want to read, search and send them to an e-reader from a browser.

## Set it up

1. Turn it on and choose **Open Calibre-Web**.
2. Sign in with Calibre-Web's own first sign-in, `admin` and `admin123`, and **change the password at once** in Admin, Edit user: anyone on your home network can open the page.
3. For **Location of Calibre database** give `/media/books` (the folder with `metadata.db`). It is read only, so uploading and editing books in Calibre-Web are not possible; add books with Calibre itself.

## What it may do

- It can read: Files in your media folder under books (read only).
- It can change: Its own folder in Starboard's data (data/plugins/calibre-web).
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its images, pinned by digest:

- `app`: `lscr.io/linuxserver/calibre-web@sha256:8eabbc9ac4d7fcbc252434493078ba22e4e8c3aa461e11b102020b040c5fc3e6`

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 13 November 2026 | 182.2 MiB | 0.01% |

## Removing it

**Settings**, **Plug-ins**, Calibre-Web, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Calibre-Web itself is under the GPL-3.0 licence, made by others: https://github.com/janeczku/calibre-web

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
