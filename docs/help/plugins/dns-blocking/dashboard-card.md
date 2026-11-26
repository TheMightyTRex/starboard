# Ad blocking: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Ad blocking adds 1 card you can put on your dashboard. It starts with a band: Ad blocking's logo and name, a status in words, and when it last changed.

## Blocked today

Shows how many lookups Pi-hole or AdGuard Home blocked today, with the share of all lookups, such as "12% of 35,000 lookups". Before any lookups are counted today, it says "no lookups yet".

- **How often it updates:** once a minute while the dashboard is open. Each time, Ad blocking asks Pi-hole or AdGuard Home for today's numbers. Nothing is asked while the browser tab is hidden.
- **Example:** 4,210 blocked, 12% of 35,000 lookups

## What the status says

| Status | Means |
|---|---|
| **Protected** | Pi-hole or AdGuard Home answered, and the number is today's. The time in the band is when it last asked. |
| **Needs setting up** | **Its address** is empty. The card says "Add the address in the plug-in's settings". |

If Ad blocking cannot get the numbers, for example because the address or password is wrong, the card shows **No answer from Ad blocking** instead. Read [Problems](../dns-blocking/problems.md).

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose **Blocked today (Ad blocking)**.
3. Select **Save**.

Ad blocking must be added and active first. Read [Install](../dns-blocking/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../dns-blocking/settings.md)
- [Problems](../dns-blocking/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
