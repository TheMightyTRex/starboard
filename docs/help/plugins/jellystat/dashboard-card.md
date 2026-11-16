# Jellystat: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Jellystat adds 1 card you can put on your dashboard. Each starts with a grey band: Jellystat's logo and name and a status in words. A lighter grey footer says when it last changed.

## Jellystat

Shows one line saying whether Jellystat has your Jellyfin, or that a backup is being restored. The figures themselves are on Jellystat's own page: open it from its tab with **Open**.

- **How often it updates:** every 10 minutes while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** Jellystat has your Jellyfin.

## What the status says

| Status | Means |
|---|---|
| **OK** | Jellystat has your Jellyfin's address and key. The card says "Jellystat has your Jellyfin." or "Gave Jellystat your Jellyfin's address and key." |
| **Working** | A backup is being restored. The band says "Restoring a backup" and the card says which file. |
| **Waiting** | It has just started and has not asked Jellystat yet. The band and the card say "Starting". |
| **Warning** | Jellystat does not have your Jellyfin yet. The card says why: "Jellystat is not answering yet", "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps." or "Jellystat did not accept Jellyfin's address and key". |

It asks Jellystat every 2 minutes, starting 20 seconds after it starts.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Jellystat), such as **Jellystat (Jellystat)**.
3. Select **Save**.

Jellystat must be added and active first. Read [Install](../jellystat/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../jellystat/settings.md)
- [Problems](../jellystat/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
