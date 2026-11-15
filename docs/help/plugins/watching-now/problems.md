# Watching now: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Watching now, then follow the numbered answer.

```flow
title: Find your answer
start: Watching now is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  No Jellyfin key -> 3
  Nobody is watching, but someone is -> 4
  Something else went wrong -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add Jellyfin to Starboard #add-jellyfin-to-starboard
4: Check what Jellyfin sees #check-what-jellyfin-sees
5: Read what the card says #read-what-the-card-says
```

## Start it again

1. On Watching now's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../watching-now/updates.md).
4. Still failing: go to **System**, then **Logs**, and look for its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Watching now works with, so Starboard stopped it.

1. Select **Look for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add Jellyfin to Starboard

The card says "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps". Watching now asks Jellyfin with the key Starboard keeps, and Starboard does not have one yet.

1. Go to **Settings**, then **Apps**.
2. Add Jellyfin, with its address and API key.
3. Go back to the dashboard and wait up to 30 seconds for the card to be asked again.

## Check what Jellyfin sees

The card says "Nobody is watching" while someone is watching.

- The card is asked every 30 seconds, so someone who has just started can take that long to appear.
- It lists only sessions Jellyfin saw in the last 2 minutes that are playing something. Someone who opened Jellyfin but has not started playing is not listed.
- It asks the Jellyfin that Starboard knows, in **Settings**, then **Apps**. If you have more than one Jellyfin, check it is the one they are watching on.

## Read what the card says

- **No answer from** and its name: it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.
- **Problem** on the card: the words under it say what went wrong. A message about a connection or a time-out means Jellyfin did not answer: check Jellyfin is running and its address in **Settings**, then **Apps**, is right. Fix that, then wait for the next check.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../watching-now/settings.md)
- [Updates](../watching-now/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
