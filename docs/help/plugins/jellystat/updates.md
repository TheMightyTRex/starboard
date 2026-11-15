# Jellystat: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Jellystat 1.1.1 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.1.1 | 1.14 or later | 2026-11-15 |
| 1.1.0 | 1.14 or later | 2026-11-15 |
| 1.0.0 | 1.13 or later | 2026-11-13 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.1.1

Fixed:

- **Its card's example** in the Catalogue and on Edit dashboard now shows what the card really says: "Jellystat has your Jellyfin."

## What is new in 1.1.0

Added:

- **A logo** in Settings, Plug-ins, in the Catalogue and on its dashboard cards.
- **Its card says how things are:** a status and when it last changed, in the grey band at the top of the card.
- **Updates safely:** an update waits for a restore that is running, or is refused until it is done.

Changed:

- Needs Starboard with plug-in API 1.14 or later. A Starboard with an older plug-in API keeps version 1.0.0.

## What is new in 1.0.0

Added:

- Jellystat and its PostgreSQL 15 database as one plug-in, outside the main install, on its own page on your home network.
- Jellyfin's address and key handed over by Starboard, and a database password made for this install.
- Restore a Jellystat backup: a pg_dump file, restored beside your figures and then swapped in.

## How an update is kept safe

- **Before the update** Starboard asks Jellystat to get ready: it starts nothing new and lets a restore that is running finish, for up to 60 seconds. If it is not ready, nothing changes and Starboard says why.
- **After the update,** or after a Roll back, it carries on with its work.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.
- **Roll back** brings back the older Jellystat and your settings, but not its folder as it was: if the newer app changed its own data, that stays. Back up its folder first if you are unsure.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Jellystat has an **Update** chip in **Manage**.
2. Select **Jellystat** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Jellystat**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Jellystat's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Jellystat's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/jellystat/starboard-plugin.json)
- [Problems](../jellystat/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
