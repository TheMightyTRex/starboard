# Watching now: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Watching now adds 1 card you can put on your dashboard. Each starts with a grey band: Watching now's logo and name, a status in words, and when it last changed.

## Watching now

Shows a short list, up to 10 lines: one line for each person playing something in Jellyfin, from the sessions Jellyfin saw in the last 2 minutes. Each line has the film or episode, then who is watching, on which device, how far through they are, and "paused" when they have paused it. An episode shows its series, season and episode number, such as "S01E02".

- **How often it updates:** every 30 seconds while the dashboard is open and in view. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Dune: Part Two: Sam, living room TV, 40%

## What the status says

| Status | Means |
|---|---|
| **Running** | One person or more is watching. The band says how many, such as "1 watching". |
| **Idle** | Nobody is watching. The band says "Nobody watching" and the card says "Nobody is watching" and "Jellyfin is quiet". |

Someone who has paused is still counted as watching: their line ends with "paused".

If Watching now cannot ask Jellyfin, the card shows what went wrong instead of a list, such as "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps". Read [Problems](../watching-now/problems.md).

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Watching now), such as **Watching now (Watching now)**.
3. Select **Save**.

Watching now must be added and active first. Read [Install](../watching-now/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../watching-now/settings.md)
- [Problems](../watching-now/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
