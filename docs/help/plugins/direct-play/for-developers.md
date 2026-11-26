# Direct play: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Direct play is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/logo.svg)
- [`HELP.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/HELP.md)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/CHANGELOG.md)
- [`tests/test_direct_play.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_direct_play.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data`, `media/movies`, `media/tv` | `media` | `always` | 512 MB, 1 core |

Each image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-direct-play@sha256:5f98e9a8583c7cfaf909f939047777adccc235792ed67b9c7961bc33ca418830`

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Direct play card (list) |
| `GET /summary` | The Space saved by Direct play card (stat) |
| `POST /pause` | The Pause fixing button |
| `POST /resume` | The Resume fixing button |
| `POST /survey` | The Check the library now button |
| `GET /files` | The Files page |
| `POST /jobs/quiet` | The job Direct play in quiet hours |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## Jobs

- `quiet`: every 1 hour, only in quiet hours, 1 minutes at most.

## How it works

- A worker wakes once a minute and does nothing outside the hours set in **When it works**. In its hours it reads the movies and tv folders with ffprobe, at most every 6 hours, reading only new or changed files, then fixes one file at a time, cheapest fix first.
- ffmpeg runs with `nice` and `ionice` at the lowest priority, with two threads. Each new file is checked before it replaces the original, then Reelix rescans the film or series and Jellyfin is told the file changed.
- Starboard's quiet-hours job (`POST /jobs/quiet`) wakes it each hour in Starboard's quiet hours.
- The cards read a small status file the worker writes, at most as often as **Card updates every** says, so nothing is probed for a card. The **Direct play** card sends `converting`, `waiting`, `paused`, `done` or `needs_setup`.
- Before an update it stops the file being converted and removes its unfinished copy, and after the update it carries on.
- It runs as the owner of your media folder (`user: media`), so the new files are yours.

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
