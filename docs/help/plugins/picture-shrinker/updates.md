# Picture shrinker: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Picture shrinker 1.2.2 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.2.2 | 1.14 or later | 17 November 2026 |
| 1.2.1 | 1.14 or later | 17 November 2026 |
| 1.2.0 | 1.14 or later | 17 November 2026 |
| 1.1.1 | 1.14 or later | 16 November 2026 |
| 1.0.0 | 1.14 or later | 15 November 2026 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.2.2

Added:

- **Space saved by type:** a dashboard card with the space each type of picture saved, such as posters, backdrops and photos of cast and crew, how many of each were shrunk, and the last run.
- **Saved by type** in its settings: a table of the same figures, with the size before and now. Pictures shrunk before 1.2.2 were not counted by type, so they share one row.

Changed:

- **Space saved card:** with nothing shrunk yet, it says so and what to do next: choose a backup in Original pictures first, then Shrink now or the next run.
- **Sizes as Starboard shows them:** a kilobyte is 1,024 bytes in its words too, so the figures on its cards and pages agree with the number Starboard draws on the Space saved card.
- **Light as before:** both cards read the figures kept after each run; nothing is measured or scanned when a card asks.

## What is new in 1.2.1

Changed:

- **Clearer words:** **Just shrink, with no backup** is now **Shrink without a backup**. The card's band says **Scheduled**, and the card says when it runs next.
- **Logo description:** where its logo stands on its own, a screen reader says "Picture shrinker logo", the plug-in's name, instead of a description of the symbol.

## What is new in 1.2.0

Added:

- **Choose the backup:** Original pictures asks whether to keep a backup copy of each original or just shrink, once it is added and again after this update. Nothing is shrunk until you choose; a backup you already have is kept.
- **Start again** in its actions, for the pictures it shrinks or for every picture: deletes the backup and the records, and has Jellyfin download the pictures again at full size. A picture Jellyfin cannot download again is put back after a day.
- **Every picture type:** posters, photos of people, backdrops, thumbnails, logos, banners, disc art and clear art, each with its own size and all activated when you add it, with Shrink all picture types to shrink them all in one setting. Backdrops were asked for by Lentzeris in the Jellyfin version's issue #2.

Changed:

- **Rules 1.2:** the same rules file as the Jellyfin version.

Removed:

- **Back up each original before it is replaced:** replaced by Original pictures.

After this update, open Picture shrinker's tab and choose in **Original pictures**: until you do, it shrinks nothing and its card says **Choose a backup**.

## What is new in 1.1.1

Changed:

- **Lighter at rest:** it wakes about once a minute while nothing asks it anything, not twice a second.
- **Starts faster:** its image comes with Python's modules already compiled, so a start takes about a quarter of the processor time.

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

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
