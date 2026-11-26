# Checkrr: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Checkrr 1.0.0 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.0.0 | 1.14 or later | 17 November 2026 |

The catalogue offers each Starboard the newest version it can run.

## What is new in 1.0.0

Added:

- Checkrr as a plug-in, outside the main install, on its own page on your home network.
- **Checks your films and series** each Sunday at 03:30, reading them only: it never deletes, moves or replaces a file.
- **A card** with how many files failed the check, a list of them with Checkrr's reason, and Check now.

## How an update is kept safe

- Checkrr has no step before an update: Starboard stops it, installs the new version and starts it again.
- Starboard waits for its helper to answer its health check. If it does not, Starboard goes back to the version you had by itself.
- Your settings and its folder, with its list of bad files, are kept. Its settings file is not written again, so a change you made to it stays.
- **Roll back** brings back the older Checkrr and your settings, but not its folder as it was: if the newer app changed its own data, that stays. Back up its folder first if you are unsure.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Checkrr has an **Update** chip in **Manage**.
2. Select **Checkrr** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Checkrr**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Checkrr's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Checkrr's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/checkrr/starboard-plugin.json)
- [Problems](../checkrr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
