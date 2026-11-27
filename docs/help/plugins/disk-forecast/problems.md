# Disk forecast: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Disk forecast, then follow the numbered answer.

```flow
title: Find your answer
start: Disk forecast is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Needs an update -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  Measuring -> 3
  Not growing -> 4
  Full in a few days -> 5
  An error -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Wait for two days #wait-for-two-days
4: Check the disk is filling #check-the-disk-is-filling
5: Make room on the disk #make-room-on-the-disk
6: Read the error #read-the-error
```

## Start it again

1. On Disk forecast's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../disk-forecast/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Disk forecast works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Wait for two days

"Measuring: a forecast after two days" means it has no readings yet. It takes its first reading a few seconds after it starts, then one every hour.

- A forecast needs readings from two different days, so wait until the day after it was activated.
- If it still says **Measuring** after an hour, check its tab says **Active**.

## Check the disk is filling

"62% full, not growing" (or another figure) means that disk is no fuller than on the oldest day it kept.

- On its first day it has nothing to compare with, so every disk says this. Wait until the next day.
- A disk you only read from, or one you cleared space on, is not growing. That is not a problem.

## Make room on the disk

**Warning** means a disk fills in less than 60 days, and **Problem** means in less than 14 days, at the rate it has been filling.

1. Read which disk the card names.
2. Make room on it, or add space. Read [Check free space and what is using it, in Starboard's help](../../topics/check-storage.md).
3. Wait for the next reading, within an hour.

The forecast compares with the oldest day it kept, up to 35 days back, so a big download some weeks ago can bring the date forward.

## Read the error

When it could not measure at all, the card shows **Problem** and what went wrong, such as an error reaching Starboard.

1. Go to **Settings**, then **Plug-ins**, then **Disk forecast**.
2. Select **Deactivate**.
3. Select **Activate**. It measures again a few seconds after it starts.
4. If the error stays, go to **System**, then **Logs**, and find its name.

Once it has readings, a later error is not shown on the card. If the time in the band is more than a few hours old, it has stopped measuring: start it again.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../disk-forecast/settings.md)
- [Updates](../disk-forecast/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
