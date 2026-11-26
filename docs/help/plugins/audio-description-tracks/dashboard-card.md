# Audio description tracks: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description tracks adds 1 card you can put on your dashboard. Each starts with a band: Audio description tracks' logo and name and a status in words. A footer says when it last changed.

## Description tracks to check

Shows how many added tracks are waiting for you to say whether they play in step. Under it, how many other files need checking, such as one with no match or lengths that differ, or "Nothing else waiting".

- **How often it updates:** once an hour while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **When it last changed:** the time in the band is when it last checked the folder, or when a track last changed, whichever is later.
- **Example:** 2 to check, Nothing else waiting

## What the status says

| Status | Means |
|---|---|
| **OK** | Nothing is waiting for you. Every file in the folder is confirmed, already described or already added. |
| **Working** | Shown as **Adding tracks**. It is checking the folder and checking new files now. |
| **Idle** | Jellyfin's own Audio description plug-in is installed and adds the tracks, so this one adds nothing. |
| **Warning** | Files need you. The band says "To check": added tracks to play and confirm, and files it could not add, such as **Lengths differ**, **No match** or **Choose the title**. |

For each file and what to do, open **Description tracks to add** on its tab. Read [Settings](../audio-description-tracks/settings.md).

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Audio description tracks), such as **Description tracks to check (Audio description tracks)**.
3. Select **Save**.

Audio description tracks must be added and active first. Read [Install](../audio-description-tracks/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../audio-description-tracks/settings.md)
- [Problems](../audio-description-tracks/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
