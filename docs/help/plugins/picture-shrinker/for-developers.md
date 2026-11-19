# Picture shrinker: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Picture shrinker is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/logo.svg)
- [`HELP.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/HELP.md)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/CHANGELOG.md)
- [`tests/test_picture_shrinker.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_picture_shrinker.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `default` | `data`, `jellyfin-metadata` | `media` | `always` | 128 MB, 0.5 core |

Each image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-picture-shrinker@sha256:aa8c586d5766acd23fe9bacb6ca68d236387b2949881fc9c6417bf5e261a3cad`

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Space saved card (stat) |
| `GET /card/by-type` | The Space saved by type card (list): each type of picture and the last run |
| `POST /shrink-now` | The Shrink now button |
| `POST /stop` | The Stop shrinking button |
| `GET /saved` | The Space saved page |
| `GET /saved-by-type` | The Saved by type page, from the figures kept after each run |
| `POST /jobs/shrink` | The job Shrink pictures |
| `POST /jobs/new` | The job Shrink new pictures in quiet hours |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## Jobs

- `shrink`: on the schedule in its `when` setting, 120 minutes at most.
- `new`: every 1 hour, only in quiet hours, 30 minutes at most.

## How it works

- Starboard runs its two jobs. `POST /jobs/shrink` runs on the schedule in **When to shrink**, for 120 minutes at most. `POST /jobs/new` runs each hour of quiet hours, for 30 minutes at most, when **Shrink new pictures in quiet hours** is activated. It shrinks only pictures saved since the last pass.
- Each picture is written to a hidden file beside it (JPEG at quality 85, progressive; PNG and WebP stay PNG and WebP), opened again and decoded in full, checked for its size and format, and swapped in only when it is smaller. Its work runs at nice 19 and in the idle disk class.
- A run stops itself after 115 minutes, before the job's limit. The totals and the last runs are kept in its folder.
- `GET /health` answers 200 only while Jellyfin's metadata folder can be read and changed and its own folder can be written.
- The card's status comes from `band()`: `running`, `scheduled`, `done` or `problem`.
- It reaches only Starboard and holds no key: it needs only `jellyfin:metadata`.

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
