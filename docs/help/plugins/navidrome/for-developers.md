# Navidrome: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Navidrome is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/navidrome/starboard-plugin.json)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/navidrome/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/navidrome/logo.svg)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `app` | `lan` | `data`, `media/music:ro` | `10001:10001` | `always` | 256 MB, 0.5 core, 128 processes |

Each image is pinned by digest in the manifest:

- `app`: `docker.io/deluan/navidrome@sha256:38dc2727bfcfd5ede290f8ada114fc90368146f265ae4701ddddbcbe2a44ee52`

## How it works

- Navidrome is an app plug-in: it runs Navidrome's own image, pinned by digest, with no code of its own and no dashboard card.
- Its page is published on your home network (`network:port`). Starboard chooses the port, 4533 when it is free.
- `ND_DATAFOLDER` is `/data`, its own folder, and `ND_MUSICFOLDER` is `/media/music`, mounted read only.
- It has no health check and no update steps: Starboard waits for its container to start after an update.
- It uses about 20 MiB at rest, measured with `tools/app_check.py` on 13 November 2026, with an empty library.

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
