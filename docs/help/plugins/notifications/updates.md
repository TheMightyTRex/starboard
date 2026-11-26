# Notifications: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Notifications 1.2.0 is the latest version. It needs Starboard with plug-in API 1.16 or later (Starboard 0.23.0); an older Starboard keeps 1.1.3.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.2.0 | 1.16 or later | Not yet released |
| 1.1.3 | 1.14 or later | 17 November 2026 |
| 1.1.2 | 1.14 or later | 17 November 2026 |
| 1.1.1 | 1.14 or later | 16 November 2026 |
| 1.1.0 | 1.14 or later | 15 November 2026 |
| 1.0.0 | 1.11 or later | 13 November 2026 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.2.0

Added:

- **Disk changes:** a message whenever a disk is erased, added to the pool or taken out of it, however it was asked for, so an erase you did not start reaches you at once. Needs Starboard with plug-in API 1.16 or later; an older Starboard keeps 1.1.3.

## What is new in 1.1.3

Changed:

- **Clearer words:** each channel's switch says what to enter before you activate it, the band says **Not sent**, and a message about an event it does not know says "Starboard has an alert. Open Starboard for the details."
- **Logo description:** where its logo stands on its own, a screen reader says "Notifications logo", the plug-in's name, instead of a description of the symbol.

## What is new in 1.1.2

Changed:

- **Shared helper:** the helper every example shares sends Jellyfin's key the way Jellyfin 12 asks for it. This plug-in does not ask Jellyfin anything, so it works as before.

## What is new in 1.1.1

Changed:

- **Lighter at rest:** it wakes about once a minute while nothing asks it anything, not twice a second, and writes nothing to its folder when a run goes well.
- **Starts faster:** its image comes with Python's modules already compiled, so a start takes about a quarter of the processor time.

## What is new in 1.1.0

Added:

- **A logo** in Settings, Plug-ins, in the Catalogue and on its dashboard cards.
- **Its cards say how things are:** a status and when they last changed, in the grey band at the top of each card.
- **Updates safely:** before an update it finishes what it is doing and starts nothing new.

Changed:

- Needs Starboard with plug-in API 1.14 or later. A Starboard with an older plug-in API keeps version 1.0.0.

## What is new in 1.0.0

Added:

- **Seven ways to send:** email, Telegram, Discord, Signal (through signal-cli-rest-api), Pushover, ntfy and Apprise-style webhooks, each with a Test button.
- **What it sends:** a request ready to watch (to the person who asked too), a failed download, an app down and back, a disk nearly full, an update ready, and New this week.
- Plain words with no meaning in symbols, and links with words before them.
- Rests between messages: Starboard's events and its daily job wake it, so it uses no memory while idle.

## How an update is kept safe

- **Before the update** Starboard asks Notifications to get ready: it starts nothing new and lets anything running finish, for up to 60 seconds. If it is not ready, nothing changes and Starboard says why.
- If something is still running after about 50 seconds, Starboard says "Still busy with" and what it is, then "Try again in a few minutes". Nothing changes: try the update again later.
- **After the update,** or after a Roll back, it carries on with its work.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Notifications has an **Update** chip in **Manage**.
2. Select **Notifications** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Notifications**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Notifications' tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Notifications' changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/notifications/CHANGELOG.md)
- [Problems](../notifications/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
