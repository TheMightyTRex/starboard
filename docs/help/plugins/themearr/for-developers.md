# Themearr: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Themearr is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/themearr/starboard-plugin.json)
- [`helper.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/themearr/helper.py), the helper
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/themearr/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/themearr/logo.svg)
- [`tests/test_app_helpers.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_app_helpers.py) and [`tests/test_app_plugins.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_app_plugins.py)
- [`tools/make_app_helpers.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tools/make_app_helpers.py), which copies `helper.py` into the manifest

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `default` | `data:/helper` | `10001:10001` | `always` | 64 MB, 0.25 core |
| `app` | `lan` | `data:/opt/themearr/data`, `media/movies` | `media` | `always` | 512 MB, 1 core, 256 processes |

Each image is pinned by digest in the manifest:

- `main`: `docker.io/library/python@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89`, the official Python 3.12 image on Alpine
- `app`: `ghcr.io/themearr/themearr@sha256:0a5c617c35f93342f8fc44eb2ce874005f2142315d2c7b4410c709790143448a`, Themearr 1.52.1

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while the helper runs |
| `GET /card` | The Film theme tunes card (stat) |
| `GET /sign-in` | The Sign in to Themearr page, only with the plug-in's own key in `X-Api-Key` |

## How it works

- **No image of ours.** The helper, `helper.py`, is Python's standard library only. It is in the manifest's `files` as `app-1.0.0.py`: Starboard writes it once into the helper's own folder before its first start, and `command` runs it in the official Python image. The version in the file name means an update writes the new helper beside the old one. `tools/make_app_helpers.py` copies it in, and its check fails when they differ.
- **Reelix as Radarr.** Reelix answers Radarr's API at `<Reelix>/radarr/api/v3`. Every 2 minutes the helper reads `/run/starboard/reelix.json` (permission `reelix:key`) and, when Themearr has no Radarr or a different one, saves Reelix's address and key with Themearr's `POST /api/settings/radarr`. Themearr then reads `GET /api/v3/movie` (each film's `id`, `title`, `year`, `path` and `hasFile`) and checks `GET /api/v3/system/status`. Reelix answers both. It does not answer `GET /api/v3/mediacover`, so Themearr shows no posters.
- **The films folder.** The helper adds `/media/movies` to Themearr's library folders and maps Reelix's `/data/media/movies` to it, with `POST /api/settings`, then completes Themearr's set-up (`POST /api/setup/complete`) and starts the first read.
- **RapidAPI.** The key and user name in the plug-in's settings are sent with `POST /api/settings/rapidapi`, once each time they change.
- **The access token** is `{secret:auth_token}`, made by Starboard for this install and given to both containers as `THEMEARR_AUTH_TOKEN`. The helper calls Themearr with it and shows it on the Sign in page.
- **Media folder.** `app` runs as `media`, the media folder's owner, so the `theme.mp3` files it writes into `media/movies` are owned like the films.
- The helper keeps what it gave as fingerprints in `given.json` in its folder, so it sends each thing once.

## Find out more

- [The plug-in collection's developer pages](https://themightytrex.github.io/starboard-plugins/help/developers/plug-in-api.html)
- [App plug-ins](https://themightytrex.github.io/starboard-plugins/help/developers/app-plug-ins.html)
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
