# Backups watch: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Backups watch 0.1.0 is the first version. It needs Starboard with plug-in API 1.17 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 0.1.1 | 1.17 or later | Not released yet |
| 0.1.0 | 1.17 or later | 22 November 2026 |

## What is new in 0.1.0

Added:

- **One card for your backups:** the last run, the size and the failures of each Backrest plan or Kopia source.
- **Alerts:** once when a backup is overdue or its last run failed, and once when it is fine again, through Starboard.
- **You choose** the tool, its address and password, and how many hours count as overdue.
- **Light:** it wakes once an hour, asks the tool once and rests; its cards read what it kept.

## How an update is kept safe

- **Before the update** Starboard asks Backups watch to get ready: it starts nothing new and lets anything running finish, for up to 60 seconds. If it is not ready, nothing changes and Starboard says why.
- **After the update,** or after a Roll back, it carries on with its work.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Backups watch has an **Update** chip in **Manage**.
2. Select **Backups watch** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Backups watch**.
5. When the dialog says it is updated, select **Done**.

## Find out more

- [Settings](../backups-watch/settings.md)
- [Problems](../backups-watch/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
