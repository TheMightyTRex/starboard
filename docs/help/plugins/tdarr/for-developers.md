# Tdarr: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Tdarr is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tdarr/starboard-plugin.json)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tdarr/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tdarr/logo.svg)
- [`tests/test_app_plugins.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_app_plugins.py), the checks it shares with the other app plug-ins

## How it works

- It has no code of its own: Starboard runs the app's own image, pinned by digest, with the limits in `resources`.
- Its container is on the `lan` network with `publish` set. `network:port` lets Starboard open its page on the home network. `host_port` is the port Starboard tries first. When it is in use, Starboard takes the next free one and shows it on the tab.
- It has no `settings`, `cards`, `actions` or `health` in its manifest, so Starboard waits for its container to start after an update. Its **Settings** section is Starboard's own Tdarr settings (`APP_SETTINGS` in Starboard's `plugins.js`), which Starboard writes into Tdarr through Tdarr's own API.
- It runs read only, as a user that is not root, with no extra rights. What it writes goes in its own folder, `data/plugins/tdarr`.
- It runs as `media`, the owner of your media folder (plug-in API 1.12), so it can replace a file with its smaller copy and the new file is yours. It can write to `media/movies`, `media/tv` and `media/tdarr-cache`, and nothing else in the media folder.
- Its environment runs Tdarr's server with an internal node called `starboard` (`internalNode`), with its web page on 8265 and the server on 8266. `data/node-plugins` gives the node a folder it may write to for Tdarr's own plug-ins, and `/run` is a `tmpfs`.
- `adopt` lets Starboard copy the Tdarr from the main install (the container called `tdarr`) into the `server` container's folders: `/app/server`, `/app/configs` and `/app/logs`. `stop` is true, so Starboard stops the old Tdarr first, to copy its files whole. It copies, and never moves or deletes the old folders.

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `server` | `lan` | `data/server:/app/server`, `data/configs:/app/configs`, `data/logs:/app/logs`, `data/cache:/temp`, `data/node-plugins:/app/Tdarr_Node/assets/app/plugins`, `media/tdarr-cache`, `media/movies`, `media/tv` | `media` | `always` | 2048 MB, 2 cores, 512 processes |

Each image is pinned by digest in the manifest:

- `server`: `ghcr.io/haveagitgat/tdarr@sha256:84743e5ae433a5b49cb463b2dff2679eb02f0cac24fb88c830f49bf8aa9f1c04`

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
