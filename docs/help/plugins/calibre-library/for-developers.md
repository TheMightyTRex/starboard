# Calibre library maker: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Calibre library maker is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-library/starboard-plugin.json)
- [`app.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-library/app.py), the small server Starboard talks to
- [`Dockerfile`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-library/Dockerfile)
- [`sbplugin.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-library/sbplugin.py), the helper every plug-in here shares
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-library/install.py) and [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/calibre-library/logo.svg)
- [`tests/test_calibre_library.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tests/test_calibre_library.py)

## How it works

- Its one container, `main`, is `start: when_needed` with `idle_stop_minutes` 5. Starboard stops it when it is idle and starts it for its page or a button. It has no card and no `health`, because either would wake it.
- It is on the `default` network, so it can reach nothing. It asks for no permission.
- `media/books:ro` mounts the books folder read only; `media/books-library` mounts the new library folder for writing. It runs as the default user, `10001:10001`, the same as Calibre-Web's, so Calibre-Web can read what it writes.
- `app.py` scans the books folder and leaves out files that cannot be books (empty, cut short, not what the name says). It runs `calibredb add --with-library /media/books-library` on batches of 20 files. A batch that fails is listed, and the run carries on. `calibredb` copies each file, which is why the plug-in says the library needs room.
- Re-running is safe twice over. It remembers handled files in `/data/done.json` by path and size. Calibre also skips a book that is already in the library.
- The image is Debian with Calibre's package. The same step removes the web browser engine and graphics drivers. That makes the image about 0.7 GB instead of 1.2 GB. `calibredb --version` runs at the end of the build.

## Containers

| Container | Network | Folders | Runs as | Starts | Limits |
|---|---|---|---|---|---|
| `main` | `default` | `data`, `media/books:ro`, `media/books-library` | `10001:10001` | `when_needed` | 320 MB, 1 core, 128 processes |

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
