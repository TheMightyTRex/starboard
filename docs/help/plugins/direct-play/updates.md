# Direct play: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Direct play 1.0.0 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.0.0 | 1.14 or later | 2026-11-14 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.0.0

Added:

- **Plays directly on the devices you choose:** Rokus, Fire TV Sticks, Chromecast, smart TV apps, web browsers, Apple TV and Nvidia Shield
- **Four fixes, cheapest first:** repackages the wrong container, adds a sound track your devices play beside the original, shrinks very large H.264 files and converts old formats to H.264
- **Checked before it replaces:** the length, the picture, the first sound track and where sound and picture start; a file that fails is left as it was
- **One file at a time, at the lowest priority:** at weekends, in quiet hours or any time, with Pause and Resume
- **On the dashboard:** what is being converted, what is next and how much space it has saved
- **A logo and a status on its cards:** the grey band at the top of each card says whether it is converting, waiting, paused or done, and when it last changed.
- **Updates safely:** before an update it stops the file being converted, which is converted again afterwards, and starts no new one.

## How an update is kept safe

- **Before the update** Starboard asks Direct play to get ready: it stops the file being converted, removes its unfinished copy and starts no new file, as **Pause fixing** does. The original stays as it was. If a file is still being converted after 30 seconds, it says "A file is still being converted. Try again in a minute" and nothing changes.
- **After the update,** or after a Roll back, it carries on, and converts that file again from the start.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Direct play has an **Update** chip in **Manage**.
2. Select **Direct play** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Direct play**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Direct play's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Direct play's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/CHANGELOG.md)
- [Problems](../direct-play/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
