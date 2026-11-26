# Backups watch: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Backups watch is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.17 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/CHANGELOG.md)
- [`tests/test_backups_watch.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_backups_watch.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data` | `10001:10001` | `when_needed` | 48 MB, 0.1 core |

The image is the shared examples image. Until it is built and pinned by digest, the manifest names its next tag.

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Backups card (status) |
| `GET /runs` | The Backup runs card (list) |
| `GET /sizes` | The Backup sizes card (sparkline) |
| `POST /check` | The Check now button |
| `POST /jobs/check` | The job Check the backups, every hour, 2 minutes at most |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## How it works

- The job asks the tool once and keeps the answer in `/data/state.json`. The three cards read only that file, so a card never wakes the backup tool.
- **Backrest:** `POST <address>/v1.Backrest/GetSummaryDashboard` with a JSON body of `{}` and the header `Connect-Protocol-Version: 1`. Each entry of `planSummaries` is one backup: `recentBackups` (times, statuses and bytes added in step), `backupsFailed30days`, `protectedBytes`. 64 bit numbers may arrive as text.
- **Kopia:** `GET <address>/api/v1/control/sources` with HTTP Basic sign-in. Each entry of `sources` is one backup: `lastSnapshot` with `endTime`, `stats.totalSize`, `stats.errorCount` and `incomplete`.
- Neither was tried against the real program. The tests use recorded sample answers built from each tool's published API (Backrest's `service.proto`, Kopia's `serverapi.go`). Duplicati's server API could not be checked from its documentation, so it is not offered.
- **Alerts:** `POST /api/v1/plugin/alerts` with the permission `alerts:send`, once as `raised` and once as `cleared` for each key (`overdue:<backup>`, `failed:<backup>`). What was raised is kept in `/data/raised.json`, so a restart sends nothing twice. A Starboard that answers 404 is not asked again for an hour.
- The password is read from the settings each time and is never written to `/data`, a card or an error.
- It starts when needed and stops after 5 minutes with nothing to do.

## Find out more

- [The plug-in collection's developer pages](https://themightytrex.github.io/starboard-plugins/help/developers/plug-in-api.html)
- [Plug-in manifest reference](../../developers/plugin-manifest-reference.md)
- [Plug-in API reference](../../developers/plugin-api-reference.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
