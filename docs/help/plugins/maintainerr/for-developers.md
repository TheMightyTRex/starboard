# Maintainerr: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Maintainerr is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/maintainerr/starboard-plugin.json)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/maintainerr/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/maintainerr/logo.svg)
- [`tests/test_app_plugins.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_app_plugins.py), the checks it shares with the other app plug-ins

## How it works

- It has no code of its own: Starboard runs the app's own image, pinned by digest, with the limits in `resources`.
- Its container is on the `lan` network with `publish` set. `network:port` lets Starboard open its page on the home network. `host_port` is the port Starboard tries first. When it is in use, Starboard takes the next free one and shows it on the tab.
- It has no `settings`, `cards`, `actions` or `health`, so Starboard waits for its container to start after an update.
- It runs read only, as a user that is not root, with no extra rights. What it writes goes in its own folder, `data/plugins/maintainerr`.
- It runs as `1000:1000`, the user its image expects, and keeps its data in `/opt/data`, its folder in Starboard's data.
- It lists `needs: ["jellyfin"]` but asks for no `jellyfin:key` and mounts no media folder: it removes only through Jellyfin or Seerr, with keys people give it.

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `app` | `lan` | `data:/opt/data` | `1000:1000` | `always` | 384 MB, 0.5 core, 128 processes |

Each image is pinned by digest in the manifest:

- `app`: `ghcr.io/maintainerr/maintainerr@sha256:5dcd5bef9d49c614bb74453df3da198afc05a38d8e2cd96b3669bc2c76a94112`

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
