# Watch statistics: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Watch statistics is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/CHANGELOG.md)
- [`tests/test_watch_stats.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_watch_stats.py)

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
| `GET /card/week` | The Plays this week card (stat) |
| `GET /card/top` | The Top titles card (list) |
| `GET /card/people` | The Who watched most card (list) |
| `GET /card/source` | The Watch statistics source card (status) |
| `POST /refresh` | The Check now button |
| `GET /screen/plays` | The Recent plays page |
| `GET /screen/titles` | The Top titles page |
| `GET /screen/people` | The People page |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## How it works

- `app.py` asks Jellyfin for its plug-ins. With Playback Reporting, it sends one query to Playback Reporting's own table through Jellyfin's API (`/user_usage_stats/submit_custom_query`), 5,000 rows at most. Without it, it reads each user's played films, episodes and audio, 200 a user at most.
- The answer is kept in `/data/plays.json` for 15 minutes, or until **Over the last** changes, and every card and table is worked out from it. **Check now** (`POST /refresh`) reads it again straight away.
- The three tables are read only: a change sent to them answers "These figures are read only".
- The cards' status comes from `band()`: `ok` with Playback Reporting, `warning` ("Last plays only") without it. The source card sends `ok`, `needs_setup` or `problem`.
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
