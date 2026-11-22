# Library health: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Library health, then follow the numbered answer.

```flow
title: Find your answer
start: Library health is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but a card is wrong -> q2
q2: What does the card say?
  Checking soon -> 3
  No Jellyfin key -> 4
  A title is still listed after fixing -> 5
  Something else went wrong -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Wait for the first check #wait-for-the-first-check
4: Add Jellyfin to Starboard #add-jellyfin-to-starboard
5: Check it again #check-it-again
6: Read what the card says #read-what-the-card-says
```

## Start it again

1. On Library health's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../library-health/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Library health works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Wait for the first check

The band says "Checking soon" and the number card says "Not checked yet". The first check starts a few seconds after Library health is active.

1. Wait a minute.
2. If it still says "Checking soon", select **Check now** on its tab. If that shows an error, read [Read what the card says](#read-what-the-card-says).

## Add Jellyfin to Starboard

The number card says "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps".

1. Go to **Settings**, then **Apps**.
2. Add Jellyfin, with its address and API key.
3. On Library health's tab, select **Check now**.

## Check it again

A title you fixed in Jellyfin is still listed. The cards show the last check, and it checks every 6 hours.

1. Check the title in Jellyfin has a poster, a description and a year.
2. On Library health's tab, select **Check now**.

## Read what the card says

- **No answer from** and its name: it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.
- **Problem** on the card: the words under the number say what went wrong. A message about a connection or a time-out means Jellyfin did not answer: check Jellyfin is running and its address in **Settings**, then **Apps**, is right. Fix that, then select **Check now** on its tab.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../library-health/settings.md)
- [Updates](../library-health/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
