# Library health: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Library health adds 2 cards you can put on your dashboard. Each starts with a grey band: Library health's logo and name and a status in words. A lighter grey footer says when it last changed.

## Library health

Shows how many films and series in Jellyfin have no poster, no description or no year, out of how many titles it checked.

- **How often it updates:** Library health checks Jellyfin every 6 hours, or when you select **Check now**. The card is asked once a minute while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** 4 to fix, of 1,240 titles

## To fix in Jellyfin

Shows a short list, up to 10 lines: the films and series to fix, each with what it is missing, such as "No poster" or "No description, no year". With nothing to fix, it says "Nothing to fix" and "Every title has a poster, a description and a year".

- **How often it updates:** Library health checks Jellyfin every 6 hours, or when you select **Check now**. The card is asked once a minute while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Brazil (1985): No poster

## What the status says

| Status | Means |
|---|---|
| **OK** | The last check found nothing to fix. The band says "Nothing to fix". |
| **Waiting** | It has just started and has not checked yet. The band says "Checking soon" and the number card says "Not checked yet". |
| **Warning** | The last check found titles to fix. The band says how many, such as "4 titles to fix". |
| **Problem** | The first check went wrong. The number card says what went wrong under the number, such as "LookupError: Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps". The list card shows its "Nothing to fix" line until a check works, so read the band and the number card. |

Once a check has worked, the cards keep showing its result if a later check goes wrong.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Library health), such as **Library health (Library health)**.
3. Select **Save**.

Library health must be added and active first. Read [Install](../library-health/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../library-health/settings.md)
- [Problems](../library-health/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
