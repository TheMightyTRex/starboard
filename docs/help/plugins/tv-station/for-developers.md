# Create your own TV channel: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Create your own TV channel is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.15 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/app.py): the web server, Starboard's pages and card, and Jellyfin
- [`schedule.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/schedule.py): the schedule and the breaks, with no input or output
- [`guide.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/guide.py): the channel list (M3U) and the guide (XMLTV)
- [`dog.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/dog.py): the on-screen logo, straps and cards as FFmpeg filters
- [`stream.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/stream.py): one FFmpeg for each channel being watched, shared by its viewers
- [`library.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/library.py): line-ups and clips from Jellyfin
- [`pack.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/pack.py): broadcast packs: the zip rules, the checks with ffprobe, loudness, the placement guides and the template
- [`pack.schema.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/pack.schema.json): the JSON Schema for a pack's `pack.json`, checked with no library
- [`promo.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/promo.py): which promos to make and replace, and the FFmpeg command for one
- [`grid.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/grid.py): the schedule grid: every change as a function on a small JSON document, the week worked out, and the channel that follows it
- [`suggest.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/suggest.py): suggests a week from watch history; also a script: `python3 suggest.py --url <Jellyfin> --key <key>`
- [`grid.html`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/grid.html), [`grid.js`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/grid.js), [`grid.css`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/grid.css): the grid's own page, on [`ds-tokens.css`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/ds-tokens.css), the design system's tokens (Mica): light unless Dark is chosen on the page
- [`example_pack.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/example_pack.py): makes the Example TV pack with FFmpeg alone: `python3 example_pack.py <folder> --zip <file>`
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/logo.svg)
- [`atkinson-hyperlegible-next.woff2`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/atkinson-hyperlegible-next.woff2), the font on the television, with its licence, [`LICENSE-OFL.txt`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/LICENSE-OFL.txt)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tv-station/CHANGELOG.md)
- [`tests/test_tv_station.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_tv_station.py) and [`tests/test_tv_station_pack.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_tv_station_pack.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan`, published (it tries port 8790 first) | `data` | `10001:10001` | `always` | 768 MB, 2 cores |

Its image is built for amd64, arm64 and arm/v7 by `.github/workflows/tv-station-image.yml`, and pinned by digest in the manifest when it is published.

## How the schedule works

A channel is a function from time to programme, an idea from [Clickarr](https://github.com/thegregstengel/clickarr) (MIT); no code is copied. A channel keeps eras: each is a frozen line-up (every programme and its length), the moment it starts, a seed and the channel's order and times. What is on at any moment is worked out from those, so the guide, the card and the stream always agree, and nothing is kept or run between viewings.

- **Shuffled** uses a SplitMix64 random number generator of its own, so a shuffle is the same on every computer.
- **A new line-up** starts at the end of the programme on air, carrying on from the programme that would have come next.
- **Breaks** are planned from the same inputs: a broadcast pack's logo with music, an ident, trailers, clips and promos that fit, then Later and Coming up next cards for the rest. A pack's idents are chosen at random from the break's seed, so the same break always has the same ident.
- **Transitions** sit on each cut between programme and break. The last half of a piece that ends on a cut is played as a piece of its own, so each FFmpeg run starts its transition at its own start, paced like the piece, and never holds frames waiting.
- **The stream** carries on from the end of what it has sent, within 8 seconds of the clock, so FFmpeg's first burst never sends anything twice and a slow start never passes anything over. Every looped input is cut a second after its piece.

## Broadcast packs and promos

- **A pack** is unpacked to a new folder, checked, and only then put in place of the one in use, in `/data/packs/station`, `/data/packs/example` or `/data/packs/ch-<channel>`. What the stream uses is kept as `checked.json` beside it. [Make a broadcast pack](https://themightytrex.github.io/starboard-plugins/help/use/make-a-broadcast-pack.html) has the specification.
- **Promos** are made by `POST /jobs/promos`, which Starboard calls each hour of its quiet hours: one FFmpeg at a time, at the lowest priority with one thread, stopped at once when a channel starts. They are kept in `/data/promos`.

## What Starboard and Jellyfin call

| Path | Who | What it is |
|---|---|---|
| `GET /health` | Starboard | 200 while it runs |
| `GET /card` | Starboard | **What is on now**, a guide card |
| `GET` and `POST /channels`, `/clips`, `/guide` | Starboard | Its custom pages; refused without the plug-in's own key in `X-Api-Key` |
| `GET` and `POST /pack` | Starboard | The **Broadcast pack** page |
| `POST /channels/file`, `/clips/file`, `/pack/file` | Starboard | A logo, ident, clip or pack zip chosen on a page, streamed to its folder |
| `POST /actions/example`, `/actions/promos`, `/actions/refresh`, `/actions/stop` | Starboard | Its four buttons |
| `POST /jobs/refresh` | Starboard | The nightly line-up refresh, at 04:40 |
| `POST /jobs/promos` | Starboard | Promos, each hour of Starboard's quiet hours |
| `POST /update/before`, `/update/after` | Starboard | Stops every stream before an update |
| `GET /` | People | A small page; opening it tells Create your own TV channel its own address |
| `GET /t/<token>/channels.m3u` | Jellyfin | The channel list |
| `GET /t/<token>/guide.xml` | Jellyfin | The guide, 7 days |
| `GET /t/<token>/stream/<channel>.ts` | Jellyfin | A channel's stream, MPEG-TS |
| `GET /t/<token>/logo/<channel>.png`, `/art/<item>.jpg` | Jellyfin | Channel logos, and programme pictures from Jellyfin |
| `GET /t/<token>/preview/<channel>.png` | People | A frame with the on-screen logo, or `?kind=card`, `ident`, `sting` or `promo` |
| `GET /t/<token>/grid` and `POST /t/<token>/grid/api/op` | People | The schedule grid's page, and each change to it (JSON only) |
| `GET` and `POST /schedule` | Starboard | The **Schedule grid** page: a link to each channel's grid |
| `GET /t/<token>/download/<file>` | People | `template.zip`, `placement-coming-next.png`, `placement-promo.png`, `placement-logo.png` and `example-pack.zip`, as downloads |

`<token>` is a random word kept in its folder, given only to Jellyfin.

## Tests

`python3 -m unittest tests.test_tv_station tests.test_tv_station_pack tests.test_tv_station_grid`: the schedule (the same answer for the same time, joining part way, boundaries, breaks filling the gap, new episodes joining at the next boundary), the guide and channel list, the on-screen logo options, the pages, and, where FFmpeg is installed, a real run that tunes in part way through a made-up clip and checks the logo is drawn, then two viewers sharing one stream that stops after they leave. For packs: `pack.json` against its schema, the zip rules (paths outside the folder, links, unknown names, zip bombs, size limits), the example pack made small and checked, broken copies of it refused, a card drawn from it, the random ident choice, the logo with music, both halves of a transition at each cut, which promos are made and replaced, a real promo made by FFmpeg and stopped when someone watches, promos on the other channels, the placement guides' marks and the template. For the grid: the store, every change and its alternative to dragging, copy a day, stripe, where a series starts, the guide following the grid, the suggester with made-up history, and the page's answers.

## Find out more

- [Plug-in API](https://themightytrex.github.io/starboard-plugins/help/developers/plug-in-api.html)
- [App plug-ins](https://themightytrex.github.io/starboard-plugins/help/developers/app-plug-ins.html)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
