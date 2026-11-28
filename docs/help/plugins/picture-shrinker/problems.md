# Picture shrinker: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Picture shrinker, then follow the numbered answer.

```flow
title: Find your answer
start: Picture shrinker is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Needs an update -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  Last run failed -> 3
  Nothing seems to be shrunk -> 4
  Pictures under Could not read -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Read what the card says #read-what-the-card-says
4: Check when it runs #check-when-it-runs
5: Check the pictures it could not read #check-the-pictures-it-could-not-read
```

## Start it again

1. On Picture shrinker's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../picture-shrinker/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

It stops answering when it cannot read and change Jellyfin's metadata folder. If the **Space saved** page says "Jellyfin's metadata folder is not there", check Jellyfin is installed in **Settings**, then **Apps**, then turn off and turn on Picture shrinker.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Picture shrinker works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Check when it runs

- The card says when it runs next, such as "Next run tomorrow at 03:30". Change **When to shrink** to run it at another time, or select **Shrink now**.
- A picture already as small as the sizes you set is only opened, never written, so a run can save little once most pictures are shrunk.
- Only posters and photos of people are shrunk. Backdrops, logos and other pictures are left alone.
- A run stops itself after 115 minutes. The **Space saved** page says "Stopped at its time limit; the next run carries on".

## Read what the card says

- **No answer from** and its name: it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.
- **Last run failed** in the band: the card and the **Space saved** page say "The last run did not finish" and why. Fix that, then select **Shrink now** or wait for the next run.

## Check the pictures it could not read

1. On Picture shrinker's tab, open **Space saved**.
2. Open **Could not read**: each picture has the reason, such as a format it leaves as it is or a new picture that did not pass its check.
3. Those pictures are left as they were, so nothing is lost. Jellyfin can download them again if you choose **Refresh metadata** for that film or series in Jellyfin.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../picture-shrinker/settings.md)
- [Updates](../picture-shrinker/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
