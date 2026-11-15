# Jellystat: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Jellystat's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Jellystat**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Restore a Jellystat backup

| Setting | What it does | Default |
|---|---|---|
| **Backup file to restore** | Only if you have one: the name of a pg_dump file you put in the restore folder, such as jfstat.pgdump. Type the file's name only, not a path. | Empty |

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Restore a Jellystat backup** | A page of its own: where to put a backup, the files in the restore folder with their size and when they were added, and how the last restore went. You can read it, but not change it. | None |

## Buttons

These are on Jellystat's tab.

- **Restore the backup** restores the file named in **Backup file to restore**, after you confirm. Jellystat's figures are replaced by the backup's, and your current figures are kept in a database beside it, never deleted. The **Restore a Jellystat backup** page says when it is done.

## Things to note

- Everything else is set in Jellystat itself: open it from its tab with **Open**. Its own account and password are kept by Jellystat, not Starboard.
- Starboard gives Jellystat your Jellyfin's address and key once, the first time it starts with an empty database, so you never type them.
- The backup must be a PostgreSQL backup made with `pg_dump -Fc`, in `data/plugins/jellystat/data/main/restore` in Starboard's data folder. Jellystat's own JSON backups are restored in Jellystat itself.
- A restore goes into a new database first. Only when that worked is it swapped in. If it fails, nothing is changed.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder, with its database.

## Find out more

- [Install](../jellystat/install.md)
- [Dashboard card](../jellystat/dashboard-card.md)
- [Problems](../jellystat/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
