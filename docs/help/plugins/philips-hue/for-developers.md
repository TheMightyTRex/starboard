# Philips Hue: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Philips Hue is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.16 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/app.py): the tabs Starboard draws, the cards, the buttons and the event
- [`hue.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/hue.py): the bridge: HTTPS with its pinned certificate, pairing, CLIP v2, the version 1 schedules and rules, and mDNS discovery
- [`words.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/words.py): colours in words, and schedules written and read in one sentence
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/sbplugin.py): the helper every plug-in in the collection shares
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/CHANGELOG.md)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data` | `10001:10001` | `when_needed`, rests after 15 minutes | 48 MB, 0.25 core |

Its own image, `ghcr.io/themightytrex/starboard-plugin-philips-hue`, built for amd64, arm64 and arm/v7 by `.github/workflows/philips-hue-image.yml`, and pinned by digest once GitHub has built it. Python's standard library only, no other packages.

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while its folder can be written |
| `GET` and `POST /bridge` | The Bridge tab: find, pair, test and forget |
| `GET` and `POST /rooms`, `/zones`, `/types` | The lights grouped three ways (custom settings) |
| `GET` and `POST /scenes` | The Scenes tab |
| `GET` and `POST /schedules` | The Schedules tab |
| `GET` and `POST /play` | **Scene when something plays** |
| `POST /events` | Starboard's `playback.started` event |
| `GET /card/rooms`, `/card/lights` | The Rooms (list) and Lights on (status) cards |
| `POST /actions/all-off`, `/actions/all-on` | **Turn every light off** and **Turn every light on** |
| `POST /update/before`, `/update/after` | The update steps, from the shared helper |

## How it works

- **The bridge:** HTTPS to the bridge's own address only. Signify signs the bridge's certificate, not a public authority. So the plug-in keeps its SHA-256 fingerprint from the first answer and refuses any other afterwards. Pairing posts `{"devicetype": "starboard#philips-hue", "generateclientkey": true}` to `/api` once every 3 seconds while the page is open, for up to 90 seconds.
- **Reading:** one CLIP v2 `GET /clip/v2/resource` gives every light, room, zone, device, scene and grouped light, kept for 3 seconds. A room's or zone's change goes to its grouped light in one command, as the Hue app does. A device type has no grouped light, so the plug-in sends each light its own command.
- **Schedules:** CLIP v2 has none. So they are version 1 schedules, named `Starboard` and the start of their words, with `autodelete` for one that runs once. Sunrise and sunset are version 1 rules on the bridge's daylight sensor. The plug-in keeps the words and the bridge's ids, and drops any the bridge no longer has.
- **When something plays:** Starboard sends `playback.started` (plug-in API 1.16). The plug-in checks the app's name and the daylight sensor, then recalls the chosen scene.
- **Discovery:** an mDNS question for `_hue._tcp.local` on the home network, asked at most once a minute. `HUE_DISCOVER=off` asks nothing, for the tests and pictures. Hue's discovery website is never used.
- **What is kept,** in its own folder: `bridge.json` (address, key, fingerprint, name), `pairing.json`, `schedules.json` and `play.json`.

## Tests and pictures

- `python3 -m unittest tests.test_philips_hue`: 31 tests against [`tests/hue_mock_bridge.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/hue_mock_bridge.py), a made-up bridge over HTTPS (needs `openssl` to make its certificate). It has not been tried on a real bridge yet.
- `tools/hue_screens/run.sh`: runs the plug-in locked down as Starboard does against the made-up bridge. It checks its tabs with axe, a Tab walk and the reading order. It also takes the pictures. `tools/hue_screens/markup.py` then marks up the help pictures in `help/images/philips-hue`.

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
