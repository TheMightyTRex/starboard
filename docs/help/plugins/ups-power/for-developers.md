# UPS and power: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How UPS and power is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.17 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/CHANGELOG.md)
- [`tests/test_ups_power.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_ups_power.py)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data` | `10001:10001` | `always` | 32 MB, 0.1 core |

The image is the shared examples image. Until it is built and pinned by digest, the manifest names its next tag.

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Power card (status) |
| `GET /details` | The UPS details card (list) |
| `GET /history` | The Load and battery card (sparkline) |
| `POST /check` | The Check now button |
| `POST /update/before` | The update's before step, 60 seconds at most |
| `POST /update/after` | The update's after step, 10 seconds at most |

## How it works

- A background thread asks the UPS once a minute and keeps the reading in `/data/state.json`. It keeps a history of one point every 5 minutes (96 kept) and the last 10 times the power switched. The cards read only that file, so a card never asks the UPS.
- **NUT:** a TCP connection to port 3493 with `LIST UPS`, then `LIST VAR <ups>`, then `LOGOUT`. Each `VAR <ups> <name> "<value>"` line is one variable. At most 600 lines and 128 KB are read, and the whole exchange has a deadline.
- **PeaNUT:** `GET <address>/api/v1/devices/<ups>` (or `/api/v1/devices?meta=true` for the first), with HTTP Basic sign-in when set. The answer is read whether its variables are flat (`battery.charge`) or nested (`battery: {charge}`).
- Neither was tried against a real UPS. The tests use a made-up NUT server that speaks the real text protocol, and recorded PeaNUT answers that follow its README.
- **Alerts:** `POST /api/v1/plugin/alerts` with the permission `alerts:send`, once as `raised` and once as `cleared` for each key (`mains`, `low`, `replace`, `unreachable`). What was raised is kept in `/data/raised.json`, so a restart sends nothing twice. A Starboard that answers 404 is not asked again for an hour.
- The password is read from the settings each time and is never written to `/data`, a card or an error.
- It keeps running (`start: always`), because a power cut has to be noticed within a minute; the plug-in's container uses about 32 MB at most.

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
