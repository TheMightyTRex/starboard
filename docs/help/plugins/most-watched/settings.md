# Most watched: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Most watched's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Most watched**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Over the last** | How many days back to count, from 1 to 90. | 7 days |

## Things to note

- A change to **Over the last** is used at the next count, which runs once an hour. You do not need to deactivate it first.
- It needs Jellyfin added to Starboard first: go to **Settings**, then **Apps**. Starboard gives it Jellyfin's address and key.
- It counts what each Jellyfin user has marked as played, looking at up to 200 of each person's most recently played films and episodes. A person counts once for each title, however many times they watched it.
- It only reads from Jellyfin and never changes anything there. It keeps the last list in its folder.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../most-watched/install.md)
- [Dashboard card](../most-watched/dashboard-card.md)
- [Problems](../most-watched/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
