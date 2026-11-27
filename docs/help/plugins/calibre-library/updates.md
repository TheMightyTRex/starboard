# Calibre library maker: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Calibre library maker 1.0.1 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.0.1 | 1.14 or later | Not released yet |
| 1.0.0 | 1.14 or later | 26 November 2026 |

## What is new in 1.0.0

Added:

- **Calibre library maker:** makes a Calibre library from your books folder, in a new books-library folder, so Calibre-Web has something to open. It never changes your books, says what it will do first, shows progress, lists files it could not read and can be run again.

## How an update is kept safe

- Before an update, Starboard asks it to finish: a run in progress is waited for, or the update is refused until it ends.
- Starboard waits for it to answer after the update. If it does not, Starboard goes back to the version you had by itself.
- The library it made and the list of books it has handled are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, it has an **Update** chip in **Manage**.
2. Select **Calibre library maker** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version, enter your Starboard password, and select **Update Calibre library maker**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On its tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Problems](../calibre-library/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
