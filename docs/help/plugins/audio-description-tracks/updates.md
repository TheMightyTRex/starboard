# Audio description tracks: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description tracks 1.2.0 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.2.0 | 1.14 or later | 17 November 2026 |
| 1.1.4 | 1.14 or later | 17 November 2026 |
| 1.1.3 | 1.14 or later | 17 November 2026 |
| 1.1.2 | 1.14 or later | 16 November 2026 |
| 1.1.1 | 1.14 or later | 15 November 2026 |
| 1.1.0 | 1.14 or later | 15 November 2026 |
| 1.0.0 | 1.12 or later | 13 November 2026 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.2.0

Changed:

- **Rules 1.0:** the track words, how a file name is read, how close the lengths must be (5 seconds by default), the languages and the new track's name and title come from the same rules file as Jellyfin's own Audio description plug-in, so the two add tracks in the same way.
- **Idle beside the Jellyfin version:** when Jellyfin's own Audio description plug-in is installed, this one adds nothing and its card says **Idle**, so the two never add the same track. Add tracks in Jellyfin instead.

## What is new in 1.1.4

Changed:

- **Clearer words:** **Look in the folder now** is now **Check the folder now**, and its job is **Check for new description tracks**. Its card's band says **To check**, with the numbers on the card, and a track that was not added says what to do next.
- **Logo description:** where its logo stands on its own, a screen reader says "Audio description tracks logo", the plug-in's name, instead of a description of the symbol.

## What is new in 1.1.3

Fixed:

- **Jellyfin 12:** it sends Jellyfin's key the way Jellyfin 12 asks for it, so Jellyfin no longer refuses its requests where legacy authorisation is off. Older Jellyfin still works.

## What is new in 1.1.2

Changed:

- **Lighter at rest:** it wakes about once a minute while nothing asks it anything, not twice a second.
- **Starts faster:** its image comes with Python's modules already compiled, so a start takes about a quarter of the processor time.

## What is new in 1.1.1

Fixed:

- **Its card says when it last looked:** the grey band now shows when it last looked in the folder or a track last changed. Before, it never showed a time.

## What is new in 1.1.0

Added:

- **A logo** in Settings, Plug-ins, in the Catalogue and on its dashboard cards.
- **Its card says how things are:** a status and when it last changed, in the grey band at the top of the card.
- **Updates safely:** before an update it finishes adding the track it is on and starts no other.

Changed:

- Needs Starboard with plug-in API 1.14 or later. A Starboard with an older plug-in API keeps version 1.0.0.

## What is new in 1.0.0

Added:

- **Add a description track you already have:** put it in the audio-description folder in your media folder, or upload it, and it is matched to its film or episode by name
- **Lengths checked:** added only when the track and the film are the same length, within the seconds you choose; otherwise it says the track is probably for another cut
- **Added as an extra sound track** next to the film, named English (Audio Description), with the visual impaired flag; the film file is not changed
- **Nothing deleted:** the original moves to Confirmed once you say it plays in step, and a wrong track moves to Taken off

## How an update is kept safe

- **Before the update** Starboard asks Audio description tracks to get ready: it starts nothing new and lets anything running finish, for up to 60 seconds. If it is not ready, nothing changes and Starboard says why.
- If something is still running after about 50 seconds, Starboard says "Still busy with" and what it is, then "Try again in a few minutes". Nothing changes: try the update again later.
- **After the update,** or after a Roll back, it carries on with its work.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Audio description tracks has an **Update** chip in **Manage**.
2. Select **Audio description tracks** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Audio description tracks**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Audio description tracks' tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Audio description tracks' changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description-tracks/CHANGELOG.md)
- [Problems](../audio-description-tracks/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
