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
- [`rules.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/rules.json), shared with the Jellyfin version and copied by `tools/sync_audio_description_rules.py`
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
| `POST /reelix` | The Check the Reelix choice now button |
| `GET /people` | The People who want audio description page |
| `GET /titles` | The Titles with audio description page |
| `GET /elsewhere` | The Audio description elsewhere page |
| `GET /audiovault` | The Search AudioVault page |
| `GET /youdescribe` | The Search YouDescribe page |
| `GET /apps` | The MovieReading and Earcatch page |
| `GET /play` | The Play the described track page |
| `POST /events` | Starboard's `playback.started` event |
| `POST /jobs/scan` | The job Check for titles with audio description |
| `POST /jobs/reelix` | The job Check the audio description choice in Reelix |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## Jobs

- `scan`: daily at 04:20, only in quiet hours, 20 minutes at most.
- `reelix`: when Starboard starts, 2 minutes at most.

## How it works

- The container rests when idle (`start: when_needed`, resting after 10 minutes). Starboard wakes it for its jobs, its buttons and its pages. Nothing runs on a timer of its own.
- `scan` reads every film and episode from Jellyfin's `/Items`, 200 at a time with their streams only, then every series once with its tags and year, so memory stays flat whatever the library's size. A track counts when its title, display title or comment names audio description and does not mention commentary.
- It keeps `/data/result.json` (the described titles: each film's Jellyfin id, name, year, track and when it was added (DateCreated), and each series' id, year, counts and described episodes with their numbers and tracks, for **Titles with audio description**, which reads only this file), `/data/seen.json` (when each was first found, for the Recently found card) and `/data/without.json` (titles without a described track, for the Sources' links).
- `reelix` only reads Reelix with the manager key Starboard gives (issue #144): `GET /customformats/builtin/audio_description`, or on an older Reelix `GET /customformats` by name, and `GET /qualityprofiles`, and counts the video levels that give the format a score of more than 0. It never posts a format or puts a quality level, which Reelix allows only to an admin key, and never fails the job: it answers with what to do.
- For each person turned on, it sets Jellyfin's **RememberAudioSelections** and keeps what they had in `/data/people.json`, to put back when they are off. It tries Jellyfin 10.9's `/Users/Configuration` first, then 10.8's address.
- After reading the library, `scan` tags with `POST /Items/{id}` (the whole item, read with `GET /Items/{id}`, as Jellyfin's metadata editor saves it) only the items whose tag changes, and keeps the collection with `/Collections`. It skips both when Jellyfin's `/Plugins` lists the Jellyfin version (`7a591954-9c27-4ba7-80c3-dc5f0a140692`), asked at most every 10 minutes.
- On `playback.started`, it reads `/Sessions`; for each session of a chosen person playing a title whose described track is not playing, and whose app lists `SetAudioStreamIndex` in its supported commands, it sends `POST /Sessions/{id}/Command` with that command and the track's `Index`. Each start is handled once.
- **Check for described titles now** runs the scan in the background, because a button must answer in 10 seconds.
- Cards set their status with `band()` from `sbplugin.py`. Its before update step holds new runs and waits for one that is running.

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
