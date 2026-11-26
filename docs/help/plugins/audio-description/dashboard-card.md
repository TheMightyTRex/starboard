# Audio description: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description adds 2 cards you can put on your dashboard. Each starts with a band: Audio description's logo and name and a status in words. A footer says when it last changed.

## Audio description

Shows how many films and series in Jellyfin have a described sound track, with how many films and episodes it checked under it.

- **How often it updates:** once an hour while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** 42 described, of 1,240 films and episodes

## Recently found with audio description

Shows the 10 films and series it found most recently with a described sound track. A film shows its described track's name, and a series shows how many of its episodes are described. Before anything is found, it says "None found yet".

- **How often it updates:** once an hour while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Slow Horses: 12 of 18 episodes described

## What the status says

| Status | Means |
|---|---|
| **OK** | It has checked the library. The time in the band is when the last check finished. |
| **Idle** | Only on the **Audio description** card: Jellyfin's own Audio description plug-in is installed and does the tag, the collection and Play the described track. The number still counts the described titles. |
| **Scheduled** | Shown as **Checks tonight**. It has not checked the library yet. The number card says "Not checked yet". |
| **Problem** | Only on the **Audio description** card, before the first check: the last check failed, and the words under the number say why, such as "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps". |

Both cards change once a night, after the check at 04:20, or a minute or two after you select **Check for described titles now**.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Audio description), such as **Audio description (Audio description)**.
3. Select **Save**.

Audio description must be added and active first. Read [Install](../audio-description/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../audio-description/settings.md)
- [Problems](../audio-description/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
