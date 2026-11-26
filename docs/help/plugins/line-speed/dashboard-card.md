# Line speed: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Line speed adds 2 cards you can put on your dashboard. Each starts with a band: Line speed's logo and name and a status in words. A footer says when it last changed.

## Line speed

Shows the download speed of the newest test, in Mbps, with the day and time of that test.

- **How often it updates:** once a minute while the dashboard is open. The number itself changes only after a test: once a night at **Test at**, or when you select **Test now**. Nothing is asked while the browser tab is hidden.
- **Example:** 72 Mbps, Wed 04:00

## Line speed this week

Shows the last 7 tests, newest first: the speed, then the day, date and time of each.

- **How often it updates:** once a minute while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:**
  - 72 Mbps: Wednesday 11 Nov, 04:00

## What the status says

| Status | Means |
|---|---|
| **OK** | There is at least one result. The time in the band is when the newest test ran. |
| **Scheduled** | There is no result yet. The card says "Not tested yet" and "Next test at" with the hour of the first test. |
| **Problem** | Only on the **Line speed** card, before the first result: the last test failed. The card says why. |

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose **Line speed (Line speed)** or **Line speed this week (Line speed)**.
3. Select **Save**.

Line speed must be added and active first. Read [Install](../line-speed/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../line-speed/settings.md)
- [Problems](../line-speed/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
