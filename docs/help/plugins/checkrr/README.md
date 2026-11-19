# Checkrr
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Checkrr checks your films and series for damaged files each Sunday night and lists them. It only reports: it never deletes, moves or replaces a file, and reads your media read only.

An app plug-in for Starboard (plug-in API 1.14 or later): Checkrr runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (8585 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People who want to know before a film night that a file will not play: files damaged by a failing disk, a download that went wrong or a copy cut short at the start. Checkrr reads each file in your `movies` and `tv` folders, checks it is a film or episode FFprobe can read, and lists the ones that fail.

## What it does with a bad file

It adds it to its list, with its reason, and the plug-in's card and page show it. Nothing else: it never deletes, moves,
renames or replaces a file. It reads the folders read only, and it is given no Reelix, Radarr or Sonarr, so its own way
of replacing a file (which deletes it first) never runs. Replacing a file is up to you.

## Set it up

1. Activate it. It checks each Sunday at 03:30. To check now, select **Check now** on its tab.
2. Add its **Damaged files** card to your dashboard, or open **Files that failed the check** on its tab.

## What it may do

- It can read: The `movies` and `tv` folders in your media folder, read only.
- It can change: Its own folder in Starboard's data (data/plugins/checkrr).
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. A small helper beside it, run in the
official Python image, answers Starboard's card, page and button; it reaches only Starboard and Checkrr. Its images, pinned by digest:

- `main`: `docker.io/library/python@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89` (Python 3.12 on Alpine)
- `app`: `docker.io/aetaric/checkrr@sha256:c817e081e9397c240e5b13b09363fe26c9f94248489d3b4f0279e67495b1f12e` (Checkrr 3.6.1)

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A check uses up to one processor core while it runs.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 17 November 2026 | 19.0 MiB (helper 13.6, Checkrr 5.4) | 0.0% |

## Removing it

**Settings**, **Plug-ins**, Checkrr, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (its settings file and its list of bad files):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Checkrr itself is under the MIT licence, made by others: https://github.com/aetaric/checkrr

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
