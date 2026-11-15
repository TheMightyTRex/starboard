# Library clean-up: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Library clean-up 1.0.0 is the latest version. It needs Starboard 0.19.0 or later, with plug-in API 1.15.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.0.0 | 1.15 or later | 2026-11-15 |

The catalogue offers each Starboard the newest version it can run. 1.0.0 is the first version, so a Starboard with plug-in API 1.14 or earlier is not offered Library clean-up until Starboard is updated.

## What is new in 1.0.0

Added:

- **Rules:** films watched by everyone, last watched more than 90 days ago; series that ended with every episode watched; films and series nobody has watched for 12 months. Each a setting, for the libraries you choose.
- **Always kept:** favourites, anything someone is part way through, films in a collection, and anything tagged keep.
- **Preview** lists what would move and the space it frees. Nothing moves until you activate **Move items each day**.
- **Never deletes:** it moves each item to `media/.holding`, keeping its folders, and **Put back** returns it.
- **Reelix and Jellyfin are told:** Reelix stops following what moves, so it is not downloaded again, and follows it again when it is put back.

## How an update is kept safe

- **Before the update** Starboard asks Library clean-up to get ready: it finishes the item it is moving and starts no new run, so nothing is left half moved. If it is still working, it says "Still working. Try again in a minute" and nothing changes.
- **After the update,** or after a Roll back, it says when it looks again, or that **Move items each day** is deactivated. The next run carries on where it stopped.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings, its folder and what is in the holding folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Library clean-up has an **Update** chip in **Manage**.
2. Select **Library clean-up** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Library clean-up**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Library clean-up's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Library clean-up's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/CHANGELOG.md)
- [Problems](../library-cleanup/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
