# Themearr: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Themearr 1.0.0 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.0.0 | 1.14 or later | 17 November 2026 |

The catalogue offers each Starboard the newest version it can run.

## What is new in 1.0.0

Added:

- Themearr as a plug-in, outside the main install, on its own page on your home network.
- **Reads your films from Reelix** with nothing to enter: Starboard gives Themearr Reelix's address and key, and its films folder.
- **Your RapidAPI key** in its settings in Starboard, and the access token for Themearr's own page on its tab.
- **A card** with how many films have a theme tune.

## How an update is kept safe

- Themearr has no step before an update: Starboard stops it, installs the new version and starts it again.
- Starboard waits for its helper to answer its health check. If it does not, Starboard goes back to the version you had by itself.
- Your settings, its folder and the tunes in your film folders are kept.
- **Roll back** brings back the older Themearr and your settings, but not its folder as it was: if the newer app changed its own data, that stays. Back up its folder first if you are unsure.
- Themearr's own **Updates** page cannot update it here, as its files are read only: Starboard updates it, from the catalogue.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Themearr has an **Update** chip in **Manage**.
2. Select **Themearr** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Themearr**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Themearr's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Themearr's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/themearr/starboard-plugin.json)
- [Problems](../themearr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
