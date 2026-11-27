# Immich
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Photo and video counts, storage used and the job queue of your Immich server on cards.

An example Starboard plug-in by TheMightyTRexUK, MIT licence.

## What it may do

- It reaches your home network and the internet.
- It runs one small container (32 MB of memory at most).

## On the dashboard

- **Immich library**: a stat card.
- **Immich storage**: a list card.
- **Immich jobs**: a status card.

## Settings

- **Immich's address**: Such as http://192.0.2.10:2283, without /api on the end.
- **API key**: Made in Immich under Account settings, API keys. Give it only the permissions server.statistics, server.storage and queue.read (job.read for an older Immich). Starboard never shows it again.

## What it reads

Immich's own API, with your API key in the `x-api-key` header, read only:

- `GET /api/server/statistics`: the photo and video counts and the space they use, in total and for each person.
- `GET /api/server/storage`: how full the disk Immich keeps its library on is.
- `GET /api/queues` (or `GET /api/jobs` on an Immich from before it): each job queue's active, waiting and failed jobs.

It never changes anything in Immich. It was not tried against a real server when this version was written: read the
help's Problems page before relying on it.

## Add it

Needs Starboard with plug-in API 1.17 or later. A Starboard with an older plug-in API is offered the version before. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it under **Photos**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/immich/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
