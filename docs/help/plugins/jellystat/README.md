# Jellystat
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Jellystat, the full watch statistics app for Jellyfin, with its own PostgreSQL database, kept apart from the main install. Opens on its own web page.

An app plug-in for Starboard (plug-in API 1.14 or later): Jellystat runs outside the main install, in Starboard's locked-down
containers, with its own page on your home network. Starboard chooses the port (3000 when it is free) and shows the address
on the plug-in's page with **Open**.

## Who it is for

People who want every figure Jellystat gives (libraries, people, devices and a long history), and people who had Jellystat in the main install before 13 November 2026. For the usual figures, the Watch statistics plug-in is lighter: no database, and it rests when nobody has it open.

## Set it up

1. Activate it. Starboard gives Jellystat your Jellyfin's address and key, so you do not enter them.
2. Choose **Open Jellystat** and make Jellystat's own account (the first one is its admin).
3. Optional: **Restore a Jellystat backup**. Put a PostgreSQL backup of Jellystat's database (made with `pg_dump -Fc`) in `data/plugins/jellystat/data/main/restore` in Starboard's data folder, enter its name in **Backup file to restore**, then choose **Restore the backup**. It is restored into a new database first; only when that worked is it swapped in, and the database before it is kept beside it, never deleted. Jellystat's own JSON backups are restored in Jellystat itself.

## What it may do

- It can read: Everything in Jellyfin: your library, the people who use it and what each one watched.
- It can change: Its own folder in Starboard's data (data/plugins/jellystat).
- It can change: Anything in Jellyfin: it gets Jellyfin's API key, which can change users, libraries and settings.
- It can reach: Other computers on your home network, and the internet.
- It can reach: Its own web page is opened on your home network: anyone on your home network can open it, at this computer's address and a port Starboard chooses.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its images, pinned by digest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-jellystat:1.1.0` (pinned by its digest in the manifest)
- `app`: `docker.io/cyfershepard/jellystat@sha256:e61c759ec706da378bc8374e797da1dfd298ab30f804cefd82d192c301a888c7`
- `db`: `docker.io/library/postgres@sha256:fc41cfa8a90c09e84dd723ee764be4b2f59ba6c98b1e5b3fca540adddf68a5ba`

## At rest

What it uses when nobody is using it, measured with `tools/app_check.py` (median of 36 readings over 3 minutes, after
2 minutes to settle). A real library uses more.

| Reading | Memory | Processor (one core) |
|---|---|---|
| As Starboard runs it (hardened, empty library), 13 November 2026 | 126.4 MiB (main 14.2 MiB, app 75.3 MiB, db 36.9 MiB) | 0.22% |
| 13 November benchmark (`bench-2026-11-13/RESULTS.md`, no limits), Jellystat 71.3 and PostgreSQL 15.2 46.1 | 117.4 MiB | 0.22% |

## Removing it

**Settings**, **Plug-ins**, Jellystat, **Remove**. Its containers stop and go and its key stops working. You choose
where its folder goes, with everything it kept (settings, its database):
kept in `data/plugins/.removed`, or moved to the holding folder in **System**, **Clean up**.
From there you can put it back or delete it permanently. Starboard never deletes it. Your media folder is not touched.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Jellystat itself is under the MIT licence, made by others: https://github.com/CyferShepard/Jellystat

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
