# Direct play: Dashboard card
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Direct play adds 2 cards you can put on your dashboard. Each starts with a band: Direct play's logo and name and a status in words. A footer says when it last changed.

## Direct play

Shows a short list, up to 6 lines:

- **Converting now:** the film or episode, what is being done, how far it is as a percentage and about how long is left. When nothing is being converted, the first line says why instead, such as "Waiting for the weekend", "Paused" or "Nothing left to do", and when it next runs.
- **Next:** the next four files and what will be done to each.
- **Totals:** how many files are fixed, how much space is saved and how many are still to do.

- **How often it updates:** every 30 seconds while the dashboard is open and in view, or as often as **Card updates every** says. Nothing is asked while the browser tab is hidden.
- **Example:**
  - Converting now: Dune (2021): Shrink, 34% done, about 1 hour 5 minutes left
  - Next: Slow Horses, series 1 episode 3: Add a playable sound track
  - Totals: 1,173 files fixed, 1.03 TB saved, 40 files still to do

## Space saved by Direct play

Shows how much space Direct play has saved, with how many files are fixed and how many are still to do under it.

- **How often it updates:** every 10 minutes while the dashboard is open. Nothing is asked while the browser tab is hidden.
- **Example:** 1.03 TB saved, 1,173 files fixed, 40 files to do

## What the status says

| Status | Means |
|---|---|
| **Converting** | A file is being fixed now. |
| **Waiting** | Nothing is being converted yet: it is outside the hours set in **When it works**, it is checking the library, it is about to start the next file, or an update is about to start. The **Direct play** card says which, such as "Waiting for the weekend" or "Waiting for quiet hours". |
| **Paused** | Someone selected **Pause fixing**. The **Direct play** card says "Resume it on the plug-in's page in Settings, Plug-ins". |
| **Done** | Every file is checked and nothing is left to do. New films and series are checked when it next runs. |
| **Needs setting up** | On the **Direct play** card only: no device is chosen in **Devices**. The card says "No devices chosen". |

The band's time on the **Space saved by Direct play** card is when the last file was fixed. If a pass goes wrong, the cards do not say so: the **Files** page on its tab says "The last pass did not finish" and why.

## Add it to your dashboard

1. Select **Edit dashboard**.
2. In **Add a card**, choose the card. Its name ends with (Direct play), such as **Direct play (Direct play)**.
3. Select **Save**.

Direct play must be added and active first. Read [Install](../direct-play/install.md).

## Find out more

- [Use and change the dashboard, in Starboard's help](../../topics/use-the-dashboard.md)
- [Settings](../direct-play/settings.md)
- [Problems](../direct-play/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
