# Download summary: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Download summary adds 1 card you can put on your dashboard. Each starts with a band: Download summary's logo and name and a status in words. A footer says when it last changed.

## Downloaded today

Shows how much has downloaded today, with how much this week under it. It adds up what **Activity** shows, then **Downloads**, then **Queue**: every minute, how much further each download has gone since the minute before. This week means today and the 6 days before it.

- **How often it updates:** once a minute while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** 12.88 GB today, 41 GB this week
- **The day starts** at midnight on your server's clock.

## What the status says

| Status | Means |
|---|---|
| **OK** | It is counting. The time in the band is when it last added to today's total. |
| **Problem** | It could not read the queue the last time it tried. The words under the number say what went wrong instead of the week's total, until a reading works again. |

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Download summary), such as **Downloaded today (Download summary)**.
3. Select **Save**.

Download summary must be added and active first. Read [Install](../download-summary/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../download-summary/settings.md)
- [Problems](../download-summary/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
