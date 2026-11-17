# Audio description: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Audio description is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/CHANGELOG.md)
- [`tests/test_audio_description.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_audio_description.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data` | `10001:10001` | `when_needed` | 64 MB, 0.25 core |

Each image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-examples@sha256:83b980f1828cdee537bcdf03702ddf6458710cba53f9009938225df430d34d9e`

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /count` | The Audio description card (stat) |
| `GET /recent` | The Recently found with audio description card (list) |
| `POST /scan` | The Check for described titles now button |
| `POST /reelix` | The Apply the Reelix choice now button |
| `GET /people` | The People who want audio description page |
| `GET /titles` | The Titles with audio description page |
| `GET /elsewhere` | The Audio description elsewhere page |
| `GET /audiovault` | The Search AudioVault page |
| `GET /youdescribe` | The Search YouDescribe page |
| `GET /apps` | The MovieReading and Earcatch page |
| `POST /jobs/scan` | The job Check for titles with audio description |
| `POST /jobs/reelix` | The job Keep the audio description choice in Reelix |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## Jobs

- `scan`: daily at 04:20, only in quiet hours, 20 minutes at most.
- `reelix`: when Starboard starts, 2 minutes at most.

## How it works

- The container rests when idle (`start: when_needed`, resting after 10 minutes). Starboard wakes it for its jobs, its buttons and its pages. Nothing runs on a timer of its own.
- `scan` reads every film and episode from Jellyfin's `/Items`, 200 at a time with their streams only, so memory stays flat whatever the library's size. A track counts when its title, display title or comment names audio description and does not mention commentary.
- It keeps `/data/result.json` (the described titles), `/data/seen.json` (when each was first found, for the Recently found card) and `/data/without.json` (titles without a described track, for the Sources' links).
- `reelix` adds a custom format named **Audio description** with one release title pattern, and scores it 100 in every video quality level that does not already score it, or takes the score out when **Prefer releases with audio description** is deactivated.
- For each person activated, it sets Jellyfin's **RememberAudioSelections** and keeps what they had in `/data/people.json`, to put back when they are deactivated. It tries Jellyfin 10.9's `/Users/Configuration` first, then 10.8's address.
- **Check for described titles now** runs the scan in the background, because a button must answer in 10 seconds.
- Cards set their status with `band()` from `sbplugin.py`. Its before update step holds new runs and waits for one that is running.

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
