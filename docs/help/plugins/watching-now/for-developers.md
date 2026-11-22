# Watching now: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Watching now is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watching-now/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watching-now/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watching-now/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watching-now/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watching-now/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watching-now/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watching-now/CHANGELOG.md)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | None | `10001:10001` | `always` | 48 MB, 0.1 core |

Each image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-examples@sha256:83b980f1828cdee537bcdf03702ddf6458710cba53f9009938225df430d34d9e`

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Watching now card (list) |

## How it works

- Each time the card is asked, `app.py` asks Jellyfin for `/Sessions?ActiveWithinSeconds=120` through `jellyfin()` in `sbplugin.py`, and lists each session that has something playing. It keeps nothing, so it needs no folder.
- The card's status comes from `band()`: `running` with how many are watching, or `idle` when nobody is.
- Without a Jellyfin key, `jellyfin()` raises "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps", and the card answers 502 with that message.

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

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
