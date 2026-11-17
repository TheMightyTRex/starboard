# Most watched: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Most watched adds 1 card you can put on your dashboard. Each starts with a band: Most watched's logo and name and a status in words. A footer says when it last changed.

## Most watched

Shows a short list, up to 10 lines: the films and series watched by the most people over the days set in **Over the last**, most people first. Each line says how many people watched it and how many plays it had. A series counts as one title, with each episode watched counted as a play.

- **How often it updates:** Most watched counts once an hour, and the card is asked once a minute while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Slow Horses: 3 people, 11 plays

## What the status says

| Status | Means |
|---|---|
| **OK** | The list is ready. The band says when it was last counted. |
| **Idle** | Nothing was watched in the last days set in **Over the last**, or the first count has not finished. The card says "Nothing watched yet" and "in the last 7 days" or the days you set. |
| **Problem** | The count went wrong before there was a list. The card says "Nothing watched yet" with what went wrong under it, such as "LookupError: Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps". |

Once there is a list, the card keeps showing the last good list if a later count goes wrong.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Most watched), such as **Most watched (Most watched)**.
3. Select **Save**.

Most watched must be added and active first. Read [Install](../most-watched/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../most-watched/settings.md)
- [Problems](../most-watched/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
