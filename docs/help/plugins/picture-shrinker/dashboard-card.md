# Picture shrinker: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Picture shrinker adds 2 cards you can put on your dashboard. Each starts with a band: Picture shrinker's logo and name and a status in words. A footer says when it last changed.

Both cards read the figures Picture shrinker keeps after each run. Nothing is measured or scanned when a card asks, so they add no work for your server.

## Space saved

Shows how much space Picture shrinker has saved so far. Under it, how many pictures are shrunk, the size of the backup and when it runs next, or how far the run it is on has gone.

- **How often it updates:** every minute while a run is going, and every 10 minutes the rest of the time, while the dashboard is open and in view. Nothing is asked while the browser tab is hidden.
- **When it last changed:** when the last run ended.
- **Example:** 41.2 GB saved. 18,402 pictures shrunk; backup 1.1 GB. Next run Sunday 23 November at 03:30
- **Before anything is shrunk:** it says "Nothing shrunk yet" and when the first run is.

## Space saved by type

Shows the space each type of picture has saved, the most first, such as "Backdrops: 24.6 GB", with how many were shrunk and their size before and now. The last line is the last run: when it ended, what started it, how many pictures it shrank and the space it saved.

- **How often it updates:** every 10 minutes while the dashboard is open and in view, and every minute while a run is going.
- **When it last changed:** when the last run ended.
- **Example:** Posters: 11.3 GB. 7,804 pictures shrunk, from 14.9 GB to 3.6 GB
- **Pictures shrunk before version 1.2.2** were not counted by type, so what they saved is on one line, "Before version 1.2.2, all types".
- **Before anything is shrunk:** it says "Nothing shrunk yet", when the first run is, and that **Shrink now** in its actions starts one now.

The same figures, with the size before and now, are in **Saved by type** in Picture shrinker's settings. Read [Settings](../picture-shrinker/settings.md).

## Nothing shrunk yet

Picture shrinker shrinks nothing until you choose what happens to the original pictures. Until then, both cards say **Choose a backup** in the band, and **Space saved by type** says what to do:

1. Go to **Settings**, then **Plug-ins**, then **Picture shrinker**.
2. In **What to shrink**, choose an option in **Original pictures**: **Keep a backup copy of each original** or **Shrink without a backup**.
3. Select **Save**.
4. In **Actions**, select **Shrink now**, or wait for the time in **When to shrink**.

## What the status says

| Status | Means |
|---|---|
| **Scheduled** | It runs on its schedule. The cards say when it runs next, or how far the run it is on has gone. A finished run changes only the figures, never the status. |
| **Done** | No next run is set in **When to shrink**. |
| **Choose a backup** | Shown as a warning. Nothing is shrunk until you choose an option in **Original pictures**. |
| **Starting again** | **Start again** is asking Jellyfin to download the pictures again. The figures start again from nothing. |
| **Idle** | Jellyfin's own Picture shrinker is installed, so this one does nothing. Its figures are on its page in Jellyfin. |

A run that does not finish does not change the status: the reason is on the **Space saved** page in its settings.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Picture shrinker), such as **Space saved (Picture shrinker)** or **Space saved by type (Picture shrinker)**.
3. Select **Save**.

Picture shrinker must be added and active first. Read [Install](../picture-shrinker/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../picture-shrinker/settings.md)
- [Problems](../picture-shrinker/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
