# Remote access: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Remote access is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/remote-access/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/remote-access/app.py)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/remote-access/sbplugin.py)
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/remote-access/Dockerfile)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/remote-access/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/remote-access/logo.svg)

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `lan` | `data` | `10001:10001` | `always` | 128 MB, 0.5 core |

Each image is pinned by digest in the manifest:

- `main`: `ghcr.io/themightytrex/starboard-plugin-remote-access@sha256:ef50260e2ded8917b42c216efe97f20eab495845f3192f496513a9bf1e0373d1`

## What Starboard calls

| Path | What it is |
|---|---|
| `GET /health` | Health: 200 while it can work |
| `GET /card` | The Away from home card (status) |
| `POST /test` | The Test remote access button |
| `POST /restart` | The Start remote access again button |
| `GET /screen` | The Addresses away from home page |
| `POST /screen` | **Test** and **Test all** on that page |

## How it works

- `app.py` is one Python helper, standard library only, in an image built from pinned Tailscale, cloudflared and Python images (`Dockerfile`). It does not use `sbplugin.py`'s `serve()`: it has its own server, which refuses anything from inside the container, because a visitor through the tunnel arrives from `127.0.0.1`.
- A supervisor checks every 10 seconds. It runs `tailscaled` in userspace networking (no device and no extra rights) or `cloudflared` with the token in its environment, never both, and none while **Connect with** is **Nothing yet** or the key is missing.
- Shared apps are reached through small forwarders on `127.0.0.1` inside the container: 8095 to Starboard, 8096 to Jellyfin and 13378 to Audiobookshelf. Nothing else is forwarded. Jellyfin's and Audiobookshelf's addresses come from Starboard's apps (`apps:read`), read again every 5 minutes.
- With Cloudflare, it reads the routes from `cloudflared` and stops the tunnel if any leads anywhere but the three forwarders, to an app not shared, or to Starboard without Cloudflare Access.
- It has no update steps: Starboard stops it and starts the new version.

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
