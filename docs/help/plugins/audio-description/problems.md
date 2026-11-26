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
  The described track is not played -> 8
  The card says Idle -> 9
  A title has no link, or the link does not open -> 10
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add Jellyfin to Starboard #add-jellyfin-to-starboard
4: Add Reelix or stop preferring #add-reelix-or-stop-preferring
5: Check for described titles now #check-for-described-titles-now
6: Check the track name #check-the-track-name
7: Activate the person #activate-the-person
8: Check the app accepts it #check-the-app-accepts-it
9: Idle beside the Jellyfin version #idle-beside-the-jellyfin-version
10: Enter Jellyfin's address for links #enter-jellyfins-address-for-links
```

## Start it again

1. On Audio description's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../audio-description/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

It rests after 10 minutes with nothing to do, and Starboard wakes it when it is needed. Resting is not a problem.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Audio description works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add Jellyfin to Starboard

"Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps" means Starboard has no Jellyfin key for it to use.

1. Go to **Settings**, then **Apps**, and add Jellyfin with its API key. Read [Add an app, in Starboard's help](../../topics/add-an-app.md).
2. Go to **Settings**, then **Plug-ins**, then **Audio description**.
3. Select **Check for described titles now**.

## Add Reelix or stop preferring

"Starboard has no Reelix key to give yet: add Reelix in Settings, Apps" means it cannot read Reelix. The plug-in never changes Reelix itself; the choice is made in Starboard.

- If you use Reelix, add it in **Settings**, then **Apps**. Then set **Audio description** to **Prefer** in **Settings**, **Reelix**, **Picture quality**, and select **Check the Reelix choice now** on Audio description's tab to check.
- "Reelix has no Audio description format yet" means your Reelix is older than the one with its own Audio description format. It comes with the next Reelix update.
- If you do not use Reelix, deactivate **Prefer releases with audio description**.

## Check for described titles now

"Not checked yet" and **Checks tonight** mean it has not read the library yet. It checks once a night at 04:20, in quiet hours.

1. Go to **Settings**, then **Plug-ins**, then **Audio description**.
2. Select **Check for described titles now**.
3. Wait a minute or two, then open **Titles with audio description**.

If it still says "Not checked yet", the card shows what went wrong instead: read [Add Jellyfin to Starboard](#add-jellyfin-to-starboard).

## Check the track name

It finds a described track by its name, because Jellyfin does not read the flag that marks one inside a file.

- A track counts when its name says "Audio Description", "Audio described", "Descriptive audio", "Described", "DVS" or "AD" on its own, such as "English (Audio Description)".
- A track whose name mentions commentary never counts.
- A track with no name, or another name, is not found. In Jellyfin, play the film and open its list of sound tracks: it shows their names.
- A film added since the last check is found at the next one. Select **Check for described titles now** to check straight away.

## Activate the person

Jellyfin cannot pick a described track by itself. For each person activated, Jellyfin remembers the sound track they choose.

1. Open **People who want audio description** on Audio description's tab.
2. Activate the person. Starboard says "Audio description activated for" and their name.
3. In Jellyfin, they choose the described track once for each film and series.

If Starboard says "That person is not in Jellyfin any more. Reload the page", reload the page and try again.

## Check the app accepts it

**Play the described track** asks the person's app to change the sound track, with Jellyfin's own command. Not every Jellyfin app accepts it.

1. Open **Play the described track** on Audio description's tab, and check the person is activated.
2. Read the last line of the page's introduction. "does not accept the command to change the sound track" names an app that does not: in that app, choose the described track in the player.
3. The change comes within about half a minute of the start, when Starboard notices the film playing. A title with no described track, or one already playing it, is left as it is.

## Idle beside the Jellyfin version

**Idle** means Jellyfin's own Audio description plug-in is installed. It does the tag, the collection and **Play the described track**, so this one does not, and the two never do the same thing twice. Choose the people in Jellyfin's plug-in instead: in Jellyfin, **Dashboard**, **Plugins**, **Audio description**. To use this one for those again, uninstall the Jellyfin plug-in; this one notices within 10 minutes.

## Enter Jellyfin's address for links

On **Titles with audio description**, each film and episode links to its page in Jellyfin. Starboard gives the plug-in Jellyfin's address as Starboard reaches it, which a browser often cannot open, such as host.docker.internal. Then the titles have no link, and the page says so.

1. Go to **Settings**, then **Plug-ins**, then **Audio description**.
2. Under **Your library**, enter the address you open Jellyfin at in **Jellyfin address for links**, such as http://192.0.2.10:8096, and save.
3. Open **Titles with audio description** again. Each title now has a link such as "Open Harbour Lights (2019) in Jellyfin".

A link that opens Jellyfin's home page instead of the title means the address is for another Jellyfin, or the title has gone since the last check. Select **Check for described titles now**.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../audio-description/settings.md)
- [Updates](../audio-description/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
