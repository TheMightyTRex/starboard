# Most watched: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Most watched, then follow the numbered answer.

```flow
title: Find your answer
start: Most watched is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  No Jellyfin key -> 3
  Nothing watched yet -> 4
  The list is wrong -> 5
  Something else went wrong -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add Jellyfin to Starboard #add-jellyfin-to-starboard
4: Wait for the first count #wait-for-the-first-count
5: Check how it counts #check-how-it-counts
6: Read what the card says #read-what-the-card-says
```

## Start it again

1. On Most watched's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../most-watched/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Most watched works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add Jellyfin to Starboard

The card says "Nothing watched yet" with "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps" under it.

1. Go to **Settings**, then **Apps**.
2. Add Jellyfin, with its address and API key.
3. Wait for the next count, which runs once an hour.

## Wait for the first count

The card says "Nothing watched yet" and "in the last 7 days", or the days you set, with status **Idle**.

- The first count starts a few seconds after Most watched is active. It asks Jellyfin about every user, so wait for it to finish, then check again.
- If nobody marked anything as played in that time, there is nothing to show. Make **Over the last** longer on its tab: the next count, within the hour, uses it.

## Check how it counts

- A series is one title: each episode watched counts as a play, and each person counts once.
- It reads up to 200 of each person's most recently played films and episodes, so a heavy watcher's oldest plays may be left out.
- The list is counted once an hour, so the newest plays can take up to an hour to appear.

## Read what the card says

- **No answer from** and its name: it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.
- **Problem** on the card: the words under it say what went wrong. A message about a connection or a time-out means Jellyfin did not answer: check Jellyfin is running and its address in **Settings**, then **Apps**, is right. Fix that, then wait for the next count, within the hour.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../most-watched/settings.md)
- [Updates](../most-watched/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
