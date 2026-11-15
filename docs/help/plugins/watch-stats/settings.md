# Watch statistics: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Watch statistics's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Watch statistics**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Recent plays** | A page of its own: the newest 300 plays over the days set in **Over the last**, by day, with the time, person, title, device and minutes watched. You can search and sort it, but not change it. | None |
| **Top titles** | A page of its own: every title watched over the days set in **Over the last**, in groups such as Films and Series, with its plays, people, hours and when it was last watched. You can search and sort it, but not change it. | None |
| **People** | A page of its own: each person with their plays, hours, the title they watched most and when they last watched. You can search and sort it, but not change it. | None |
| **Over the last** | How many days back the tables and cards count, from 1 to 365. **Plays this week** always counts 7 days. | 30 days |
| **Leave out these people** | Jellyfin user names to leave out of every table and card, such as an account for testing. One a line, in any case. | Empty |

## Buttons

These are on Watch statistics's tab.

- **Read the figures again now** reads the plays from Jellyfin straight away, without waiting for the 15 minutes the last answer is kept. It says how many plays it read, such as "Read 23 plays over the last 30 days".

## Things to note

- A setting you change is used the next time a card or table asks; you do not need to deactivate it first. A change to **Over the last** makes it read from Jellyfin again.
- The figures come from Playback Reporting, a plug-in for Jellyfin in its official catalogue. Without it, the tables say "Playback Reporting is not installed in Jellyfin" and show only each person's last play of each title, with no device or time watched.
- Each answer from Jellyfin is kept for 15 minutes, and it reads 5,000 plays at most.
- It only reads. The tables cannot change anything, in Starboard or in Jellyfin.
- It rests after 5 minutes with nothing to do, and Starboard wakes it when a card or table asks.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../watch-stats/install.md)
- [Dashboard card](../watch-stats/dashboard-card.md)
- [Problems](../watch-stats/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
