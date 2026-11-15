# Audio description: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Audio description, then follow the numbered answer.

```flow
title: Find your answer
start: Audio description is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  No Jellyfin key -> 3
  No Reelix key -> 4
  Not checked yet -> 5
  A described film is missing -> 6
  The described track is not kept -> 7
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add Jellyfin to Starboard #add-jellyfin-to-starboard
4: Add Reelix or stop preferring #add-reelix-or-stop-preferring
5: Look for described titles now #look-for-described-titles-now
6: Check the track name #check-the-track-name
7: Activate the person #activate-the-person
```

## Start it again

1. On Audio description's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../audio-description/updates.md).
4. Still failing: go to **System**, then **Logs**, and look for its name.

It rests after 10 minutes with nothing to do, and Starboard wakes it when it is needed. Resting is not a problem.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Audio description works with, so Starboard stopped it.

1. Select **Look for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add Jellyfin to Starboard

"Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps" means Starboard has no Jellyfin key for it to use.

1. Go to **Settings**, then **Apps**, and add Jellyfin with its API key. Read [Add an app, in Starboard's help](../../topics/add-an-app.md).
2. Go to **Settings**, then **Plug-ins**, then **Audio description**.
3. Select **Look for described titles now**.

## Add Reelix or stop preferring

"Starboard has no Reelix key to give yet: add Reelix in Settings, Apps" means it cannot add the **Audio description** format to Reelix.

- If you use Reelix, add it in **Settings**, then **Apps**, then select **Apply the Reelix choice now** on Audio description's tab.
- If you do not use Reelix, deactivate **Prefer releases with audio description**. The rest of the plug-in works without Reelix.

## Look for described titles now

"Not checked yet" and **Checks tonight** mean it has not read the library yet. It checks once a night at 04:20, in quiet hours.

1. Go to **Settings**, then **Plug-ins**, then **Audio description**.
2. Select **Look for described titles now**.
3. Wait a minute or two, then open **Titles with audio description**.

If it still says "Not checked yet", the card shows what went wrong instead: read [Add Jellyfin to Starboard](#add-jellyfin-to-starboard).

## Check the track name

It finds a described track by its name, because Jellyfin does not read the flag that marks one inside a file.

- A track counts when its name says "Audio Description", "Audio described", "Descriptive audio", "Described", "DVS" or "AD" on its own, such as "English (Audio Description)".
- A track whose name mentions commentary never counts.
- A track with no name, or another name, is not found. In Jellyfin, play the film and look at its sound tracks to see their names.
- A film added since the last check is found at the next one. Select **Look for described titles now** to check straight away.

## Activate the person

Jellyfin cannot pick a described track by itself. For each person activated, Jellyfin remembers the sound track they choose.

1. Open **People who want audio description** on Audio description's tab.
2. Activate the person. Starboard says "Audio description activated for" and their name.
3. In Jellyfin, they choose the described track once for each film and series.

If Starboard says "That person is not in Jellyfin any more. Reload the page", reload the page and try again.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../audio-description/settings.md)
- [Updates](../audio-description/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
