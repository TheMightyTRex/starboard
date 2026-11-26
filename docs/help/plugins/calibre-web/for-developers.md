# Calibre-Web: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Calibre-Web is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-web/starboard-plugin.json)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-web/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-web/logo.svg)
- [`tests/test_app_plugins.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_app_plugins.py), the checks it shares with the other app plug-ins

## How it works

- It has no code of its own: Starboard runs the app's own image, pinned by digest, with the limits in `resources`.
- Its container is on the `lan` network with `publish` set. `network:port` lets Starboard open its page on the home network. `host_port` is the port Starboard tries first. When it is in use, Starboard takes the next free one and shows it on the tab.
- It has no `settings`, `cards`, `actions` or `health`, so Starboard waits for its container to start after an update.
- It runs read only, as a user that is not root, with no extra rights. What it writes goes in its own folder, `data/plugins/calibre-web`.
- `entrypoint` starts Calibre-Web's `cps.py` straight away, without the LinuxServer image's start-up, which needs root. `HOME` is `/tmp` and its cache is a `tmpfs`, so it runs read only.
- `media/books:ro` mounts only the books folder, read only, at `/media/books`. `CALIBRE_DBPATH` keeps its own database in `/config`, its folder in Starboard's data.

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `app` | `lan` | `data:/config`, `media/books:ro` | `10001:10001` | `always` | 384 MB, 0.5 core, 128 processes |

Each image is pinned by digest in the manifest:

- `app`: `lscr.io/linuxserver/calibre-web@sha256:8eabbc9ac4d7fcbc252434493078ba22e4e8c3aa461e11b102020b040c5fc3e6`

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
