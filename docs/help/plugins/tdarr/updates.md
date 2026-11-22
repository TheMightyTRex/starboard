# Tdarr: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Tdarr 1.1.1 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.1.1 | 1.14 or later | 17 November 2026 |
| 1.1.0 | 1.14 or later | 15 November 2026 |
| 1.0.2 | 1.13 or later | 13 November 2026 |

Versions 1.0.1 and 1.0.0, from 13 November 2026, are no longer offered.

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.1.1

Changed:

- **Logo description:** where its logo stands on its own, a screen reader says "Tdarr logo", the plug-in's name, instead of a description of the symbol.

## What is new in 1.1.0

Added:

- **A logo** in Settings, Plug-ins and in the Catalogue.

Changed:

- Needs Starboard with plug-in API 1.14 or later. A Starboard with an older plug-in API keeps version 1.0.2.

## What is new in 1.0.2

Changed:

- Files are converted in a tdarr-cache folder on your media drives, not on the system disk, so working copies of large films cannot fill it. Starboard points its Films and Series libraries there.

## What is new in 1.0.1

Fixed:

- The worker can download Tdarr's plug-ins: it has a folder it may write to.

## What is new in 1.0.0

Added:

- Tdarr as a plug-in, outside the main install, on its own page on your home network.

## How an update is kept safe

- Tdarr has no step before an update: Starboard stops it, installs the new version and starts it again.
- It has no health check of its own, so Starboard waits for its containers to start. If they do not, Starboard goes back to the version you had by itself.
- Your settings and its folder are kept, with Tdarr's libraries, flows and history.
- Files Tdarr already converted stay as they are.
- **Roll back** brings back the older Tdarr and your settings, but not its folder as it was: if the newer app changed its own data, that stays. Back up its folder first if you are unsure.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Tdarr has an **Update** chip in **Manage**.
2. Select **Tdarr** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Tdarr**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Tdarr's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Tdarr's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/tdarr/starboard-plugin.json)
- [Problems](../tdarr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
