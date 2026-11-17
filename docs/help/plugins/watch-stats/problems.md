# Watch statistics: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Watch statistics, then follow the numbered answer.

```flow
title: Find your answer
start: Watch statistics is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but a card or table is wrong -> q2
q2: What does it say?
  Needs Playback Reporting or Last plays only -> 3
  No Jellyfin key -> 4
  Jellyfin not answering -> 5
  Figures are old or wrong -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add Playback Reporting #add-playback-reporting
4: Add Jellyfin to Starboard #add-jellyfin-to-starboard
5: Read what the card says #read-what-the-card-says
6: Check the figures again #check-the-figures-again
```

## Start it again

1. On Watch statistics's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../watch-stats/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Watch statistics works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add Playback Reporting

The source card says "Needs Playback Reporting", the other cards say "Last plays only", or a table says "Playback Reporting is not installed in Jellyfin". Without it, the tables show only each person's last play of each title, with no device or time watched.

1. Add Playback Reporting in Starboard's **Settings**, then **Jellyfin**, or in Jellyfin's **Dashboard**, then **Plugins**, then **Catalogue**.
2. Restart Jellyfin.
3. On Watch statistics's tab, select **Check now**.

Playback Reporting counts from the day it is added, so older plays stay as last plays only.

## Add Jellyfin to Starboard

A card says "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps".

1. Go to **Settings**, then **Apps**.
2. Add Jellyfin, with its address and API key.
3. On Watch statistics's tab, select **Check now**.

## Check the figures again

- The figures are kept for 15 minutes, so a play can take that long to appear. Select **Check now** on its tab to read them straight away.
- Someone missing: check they are not listed in **Leave out these people**.
- A series counts all its episodes as one title.
- It reads 5,000 plays at most. On a busy server, make **Over the last** shorter.

## Read what the card says

- **No answer from** and its name: it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.
- **Jellyfin not answering** on the source card: it says "Jellyfin did not answer" and why. Check Jellyfin is running and its address in **Settings**, then **Apps**, is right.
- **Problem** on another card: the words under it say what went wrong. Fix that, then select **Check now** on its tab.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../watch-stats/settings.md)
- [Updates](../watch-stats/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
