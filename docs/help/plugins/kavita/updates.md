# Kavita: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Kavita 1.1.1 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.1.1 | 1.14 or later | 17 November 2026 |
| 1.1.0 | 1.14 or later | 15 November 2026 |
| 1.0.0 | 1.13 or later | 13 November 2026 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.1.1

Changed:

- **Clearer words:** its description spells out OPDS, the Open Publication Distribution System.
- **Logo description:** where its logo stands on its own, a screen reader says "Kavita logo", the plug-in's name, instead of a description of the symbol.

## What is new in 1.1.0

Added:

- **A logo** in Settings, Plug-ins and in the Catalogue.

Changed:

- Needs Starboard with plug-in API 1.14 or later. A Starboard with an older plug-in API keeps version 1.0.0.

## What is new in 1.0.0

Added:

- Kavita as a plug-in, outside the main install, on its own page on your home network.

## How an update is kept safe

- Kavita has no step before an update: Starboard stops it, installs the new version and starts it again.
- It has no health check of its own, so Starboard waits for its containers to start. If they do not, Starboard goes back to the version you had by itself.
- Your settings and its folder are kept.
- **Roll back** brings back the older Kavita and your settings, but not its folder as it was: if the newer app changed its own data, that stays. Back up its folder first if you are unsure.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Kavita has an **Update** chip in **Manage**.
2. Select **Kavita** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Kavita**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Kavita's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Kavita's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/kavita/starboard-plugin.json)
- [Problems](../kavita/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
