# Jellystat: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Jellystat is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/jellystat/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/jellystat/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/jellystat/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/jellystat/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/jellystat/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/jellystat/logo.svg)
- [`tests/test_jellystat.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_jellystat.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `default` | `data` | `70:70` | `always` | 64 MB, 0.25 core |
| `app` | `lan` | `data:/app/backend/backup-data` | `10001:10001` | `always` | 320 MB, 0.5 core, 128 processes |
| `db` | `default` | `data` | `70:70` | `always` | 256 MB, 0.5 core, 128 processes |

Each image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-jellystat@sha256:c229ae7259f383b17d03d2a5877eb62b706957d917f4a7e289162169418960fa`
- `app`: `docker.io/cyfershepard/jellystat@sha256:e61c759ec706da378bc8374e797da1dfd298ab30f804cefd82d192c301a888c7`
- `db`: `docker.io/library/postgres@sha256:fc41cfa8a90c09e84dd723ee764be4b2f59ba6c98b1e5b3fca540adddf68a5ba`

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /status` | The Jellystat card (status) |
| `POST /restore-now` | The Restore the backup button |
| `GET /restore` | The Restore a Jellystat backup page |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## How it works

- `main` is a small helper beside Jellystat (`app`) and its PostgreSQL (`db`). Every 2 minutes it asks Jellystat whether it has a Jellyfin. While it has none, it gives Jellystat Starboard's Jellyfin address and key through Jellystat's own set-up call, which checks them against Jellyfin before saving.
- **Restore the backup** (`POST /restore-now`) checks the file is a `pg_dump -Fc` backup, restores it into a new database, then renames the current database to `jfstat_before_` and the date and swaps the new one in. A failed restore is kept as `jfstat_failed_` and the date, and the current database is not touched.
- A restore runs inside `working()` from `sbplugin.py`, so an update waits for it or is refused.
- The card's status comes from `band()`: `working`, `waiting`, `ok` or `warning`.
- The database password and Jellystat's sign-in secret are made for this install by Starboard (`{secret:...}` in the manifest).

## Find out more

- [The plug-in collection's developer pages](https://themightytrex.github.io/starboard-plugins/help/developers/plug-in-api.html)
- [Plug-in manifest reference](../../developers/plugin-manifest-reference.md)
- [Plug-in API reference](../../developers/plugin-api-reference.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
