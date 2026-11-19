# Audio description: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Audio description 1.5.0 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.5.0 | 1.14 or later | 17 November 2026 |
| 1.4.0 | 1.14 or later | 17 November 2026 |
| 1.3.0 | 1.14 or later | 17 November 2026 |
| 1.2.3 | 1.14 or later | 17 November 2026 |
| 1.2.2 | 1.14 or later | 17 November 2026 |
| 1.2.1 | 1.14 or later | 16 November 2026 |
| 1.2.0 | 1.14 or later | 15 November 2026 |
| 1.1.0 | 1.12 or later | 13 November 2026 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.5.0

Added:

- **Films to list and Series to list:** how many Titles with audio description lists of each: All, or the last 10, 20, 50, 100 or 500 added to Jellyfin, newest first. Last 20 by default. A series counts by its newest described episode and still lists all its described episodes.
- **The page says how many it shows,** such as "Showing the last 20 of 143 films", and where to change it.

Changed:

- **Newest first:** the films and series are listed by when they were added to Jellyfin, newest first. The nightly check keeps that date; select **Check for described titles now** once after updating.

## What is new in 1.4.0

Added:

- **Titles with audio description:** every film, and every described episode by series, with its year, its described track and its status in words. Films and Series show their counts, and each title opens its page in Jellyfin. The same page as in Jellyfin's own Audio description plug-in.
- **Jellyfin address for links:** the address you open Jellyfin at, for the links on Titles with audio description, when Starboard reaches Jellyfin at an address a browser cannot open.

Changed:

- **The nightly check keeps a little more:** each title's Jellyfin id and year, and which episodes are described, for the page. Select **Check for described titles now** once after updating to fill it.

Fixed:

- **Films in the collection:** the nightly check asks Jellyfin for each film, not the Audio description collection in their place, so once the collection was made, films in it no longer dropped out of the check and lost their tag.

## What is new in 1.3.0

Added:

- **Find and tag:** each film and episode with a described sound track, and its series, gets the tag **Audio description** in Jellyfin at the nightly check, and the tag comes off when the track goes. Every Jellyfin app, televisions included, can filter by it.
- **The Audio description collection:** activated by default, the films and series with a described track are in one Jellyfin collection. Deactivate **Add them to the Audio description collection** to leave it as it is.
- **Play the described track:** for each person you activate on its page, inactive until chosen. When they start a title with a described track and another plays, Starboard asks their app to change to it. Not every Jellyfin app accepts this.
- **Rules 1.0:** the same rules file as Jellyfin's own Audio description plug-in. When that plug-in is installed, this one leaves the tag, the collection and Play the described track to it, and its card says **Idle**.

Changed:

- **A new logo:** a film frame with a speech bubble holding a loudspeaker, to match the Jellyfin version.
- **It hears when playback starts:** it asks to read what is playing (media:read), so Starboard tells it when someone starts a film.
- **Check the Reelix choice now:** was **Apply the Reelix choice now**, and its job is **Check the audio description choice in Reelix**: both now only read Reelix and say what to do.

Fixed:

- **Reelix (issue #144):** it no longer tries to add a format to Reelix or change its quality levels, which Reelix refuses to all but an admin key. It reads Reelix's own Audio description format and says to set it to Prefer in **Settings**, **Reelix**, **Picture quality**. The job no longer fails.

## What is new in 1.2.3

Changed:

- **Clearer words:** **Look for described titles now** is now **Check for described titles now**, and its job is **Check for titles with audio description**. Its messages put the settings they name in quotation marks and spell out RNIB.
- **Logo description:** where its logo stands on its own, a screen reader says "Audio description logo", the plug-in's name, instead of a description of the symbol.

## What is new in 1.2.2

Fixed:

- **Jellyfin 12:** it sends Jellyfin's key the way Jellyfin 12 asks for it, so Jellyfin no longer refuses its requests where legacy authorisation is off. Older Jellyfin still works.

## What is new in 1.2.1

Changed:

- **Lighter at rest:** it wakes about once a minute while nothing asks it anything, not twice a second, and writes nothing to its folder when a run goes well.
- **Starts faster:** its image comes with Python's modules already compiled, so a start takes about a quarter of the processor time.

## What is new in 1.2.0

Added:

- **A logo** in Settings, Plug-ins, in the Catalogue and on its dashboard cards.
- **Its cards say how things are:** a status and when they last changed, in the grey band at the top of each card.
- **Updates safely:** before an update it finishes what it is doing and starts nothing new.

Changed:

- Needs Starboard with plug-in API 1.14 or later. A Starboard with an older plug-in API keeps version 1.1.0.

## What is new in 1.1.0

Added:

- **AudioVault search links:** for each film and series without audio description, a link to AudioVault's own search. Deactivated until you activate it in Sources; Starboard never downloads from AudioVault
- **YouDescribe search links:** for each film and series, a link to YouDescribe's own search, where volunteers describe YouTube videos such as trailers
- **MovieReading and Earcatch:** how to use these phone apps alongside Jellyfin, which play a description in step by listening, and where to get them

Changed:

- **Audio description elsewhere:** each place is now a link that opens in a new tab

## How an update is kept safe

- **Before the update** Starboard asks Audio description to get ready: it starts nothing new and lets anything running finish, for up to 60 seconds. If it is not ready, nothing changes and Starboard says why.
- If something is still running after about 50 seconds, Starboard says "Still busy with" and what it is, then "Try again in a few minutes". Nothing changes: try the update again later.
- **After the update,** or after a Roll back, it carries on with its work.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Audio description has an **Update** chip in **Manage**.
2. Select **Audio description** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Audio description**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Audio description's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Audio description's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/audio-description/CHANGELOG.md)
- [Problems](../audio-description/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
