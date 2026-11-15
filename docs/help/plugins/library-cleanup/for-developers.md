# Library clean-up: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Library clean-up is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.15 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/logo.svg)
- [`HELP.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/HELP.md)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/CHANGELOG.md)
- [`tests/test_library_cleanup.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_library_cleanup.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data`, `media:holding` | `media` | `when_needed`, rests after 15 minutes | 128 MB, 0.5 core |

Its image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-library-cleanup@sha256:3628026fa40597cf465848f2e9daddcb444b44dc873cf7339925f4821e808cb6` (version 1.0.0)

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Holding folder card (stat, in bytes) |
| `GET /preview` and `POST /preview` | The Preview page |
| `GET /held` and `POST /held` | The Holding folder page, with **Put back** on each row |
| `GET /libraries` and `POST /libraries` | The Libraries page |
| `POST /preview-again` | The Preview again button |
| `POST /jobs/move` | The job Move items to the holding folder |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## Jobs

- `move`: every 24 hours, only in quiet hours, 60 minutes at most. It moves nothing unless the `active` setting (**Move items each day**) is activated.

## How it works

- It asks for `library:holding` (plug-in API 1.15) and mounts `media:holding`: the whole media folder, read and write, at `/media`. What it moves goes in `/media/.holding/library-cleanup/`, keeping the folders it was in.
- A series moves as its folder. A film in its own folder moves as the folder. A film that shares a folder with other films, or sits at the top of the library, moves as its file and the files beside it that share its name, such as subtitles.
- A move is a rename inside the one mount, so it is instant and needs no free space. A move that would have to copy is refused, and something with the same name already in the holding folder is never overwritten. It never moves the library folder itself, the holding folder, or anything outside the media folder.
- Its code has no call that deletes a file or a folder; `tests/test_library_cleanup.py` checks that.
- **Put back** is the `restore` action on a row of the `held` custom setting (plug-in API 1.15), drawn by Starboard as a **Put back** button.
- With `reelix:key`, it stops Reelix following what moves, with each followed episode, and rescans it; **Put back** follows again exactly what was followed. With `jellyfin:key`, it reads each person's watched state, favourites, Continue watching and collections, and tells Jellyfin the path was deleted, or created on **Put back**, so Jellyfin updates at once. Without Reelix it still moves.
- **Preview** is worked out in the background when opened, when a setting changes, after six hours, or with **Preview again**. A run moves up to 200 items, within 50 minutes; the next carries on.
- Before an update it finishes the item it is moving and starts no new run, so nothing is left half moved.
- It runs as `media`, the owner of the media folder, so moved folders keep their owner.

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
