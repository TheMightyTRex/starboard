# Watch statistics: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Watch statistics adds 4 cards you can put on your dashboard. Each starts with a grey band: Watch statistics's logo and name, a status in words, and when it last changed.

## Plays this week

Shows how many plays there were in the last 7 days. Under it, how many hours were watched and by how many people. Without Playback Reporting in Jellyfin, it says "Playback Reporting is not installed in Jellyfin" there instead.

- **How often it updates:** every 30 minutes while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** 23 plays this week, 14.5 hours by 3 people

## Top titles

Shows a short list, up to 10 lines: the titles watched by the most people over the days set in **Over the last**, then by plays. A series counts all its episodes together. With nothing watched, it says "Nothing watched yet".

- **How often it updates:** every 30 minutes while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Slow Horses: 2 people, 3 plays

## Who watched most

Shows a short list, up to 10 lines: the people who watched longest over the days set in **Over the last**, with their hours, plays and the title they watched most. Without Playback Reporting there are no hours. With nothing watched, it says "Nobody has watched anything yet".

- **How often it updates:** every 30 minutes while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Sam: 4.1 hours, 5 plays, most Slow Horses

## Watch statistics source

Shows one line saying where the figures come from: Jellyfin's Playback Reporting, or only Jellyfin's own last plays.

- **How often it updates:** every 1 hour while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** Reading Jellyfin's Playback Reporting

## What the status says

| Status | Means |
|---|---|
| **OK** | The figures come from Playback Reporting. The source card says "Reading Jellyfin's Playback Reporting". |
| **Warning** | On **Plays this week**, **Top titles** and **Who watched most**: Playback Reporting is not installed in Jellyfin, so the figures are only each person's last play of each title. The band says "Last plays only". |
| **Needs setting up** | On **Watch statistics source** only: Playback Reporting is not installed in Jellyfin. The band says "Needs Playback Reporting" and the card says how to add it. |
| **Problem** | On **Watch statistics source** only: Jellyfin did not answer. The band says "Jellyfin not answering" and the card says "Jellyfin did not answer" and why. |

The figures are kept for 15 minutes, so the band's time says when they were last read from Jellyfin. If Jellyfin cannot be asked, the other three cards show what went wrong instead of figures, such as "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps".

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Watch statistics), such as **Plays this week (Watch statistics)**.
3. Select **Save**.

Watch statistics must be added and active first. Read [Install](../watch-stats/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../watch-stats/settings.md)
- [Problems](../watch-stats/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
