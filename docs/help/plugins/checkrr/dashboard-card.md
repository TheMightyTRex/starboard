# Checkrr: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Checkrr adds 1 card you can put on your dashboard. It starts with a band: Checkrr's logo and name and a status in words. A footer says when it last changed.

## Damaged files

Shows how many files failed Checkrr's last check, and how many files it checked.

- **How often it updates:** every 10 minutes while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** 2 files failed the check. Of 8,214 files in the last check.

## What the status says

| Status | Means |
|---|---|
| **OK** | Every file passed the last check. |
| **Warning** | The band says how many bad files, such as "2 bad files". Open **Files that failed the check** on its tab for which ones and why. Nothing was changed. |
| **Scanning** | The band says "Checking". A check is running. |
| **Idle** | The band says "Not checked yet". The first check is on Sunday at 03:30, or select **Check now**. |
| **Waiting** | It started moments ago and Checkrr is not answering yet. The band says "Starting". |

It asks Checkrr every 5 minutes, and every 30 seconds while a check runs.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Checkrr), such as **Damaged files (Checkrr)**.
3. Select **Save**.

Checkrr must be added and active first. Read [Install](../checkrr/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../checkrr/settings.md)
- [Problems](../checkrr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
