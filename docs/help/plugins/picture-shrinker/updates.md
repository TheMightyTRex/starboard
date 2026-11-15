# Picture shrinker: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Picture shrinker 1.0.0 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.0.0 | 1.14 or later | 2026-11-15 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.0.0

Added:

- **Shrinks Jellyfin's pictures:** posters to 900 pixels tall and photos of cast and crew to 400 pixels wide, both settings. Smaller pictures are left alone.
- **Checked before it replaces:** each picture is written beside the original, opened again and checked, and swapped in only when it is smaller.
- **When you choose:** every day, week or month at a time, with Shrink now, at the lowest priority.
- **New pictures in quiet hours:** deactivated unless you activate it.
- **Space saved:** on its page and on a dashboard card.

## How an update is kept safe

- **Before the update** Starboard asks Picture shrinker to get ready: it stops after the picture it is on and starts no new run, so nothing is left half done. If a picture is still being shrunk, it says "A picture is still being shrunk. Try again in a minute" and nothing changes.
- **After the update,** or after a Roll back, it says when the next run is. The next run carries on where it stopped.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Picture shrinker has an **Update** chip in **Manage**.
2. Select **Picture shrinker** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Picture shrinker**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Picture shrinker's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Picture shrinker's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/CHANGELOG.md)
- [Problems](../picture-shrinker/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
