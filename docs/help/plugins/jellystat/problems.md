# Jellystat: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Jellystat, then follow the numbered answer.

```flow
title: Find your answer
start: Jellystat is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Needs an update -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  No Jellyfin key -> 3
  Jellystat is not answering yet -> 4
  Did not accept the address and key -> 5
  A restore did not work -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Add Jellyfin to Starboard #add-jellyfin-to-starboard
4: Wait for Jellystat to start #wait-for-jellystat-to-start
5: Check Jellyfin is running #check-jellyfin-is-running
6: Read how the restore went #read-how-the-restore-went
```

## Start it again

1. On Jellystat's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../jellystat/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

If the card says **No answer from** and its name, it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Jellystat works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Add Jellyfin to Starboard

The card says "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps."

1. Go to **Settings**, then **Apps**.
2. Add Jellyfin, with its address and API key.
3. Wait up to 2 minutes: it gives Jellystat the address and key by itself.

## Wait for Jellystat to start

The card says "Jellystat is not answering yet". Jellystat and its database take a while to start.

1. Wait a few minutes. It asks again every 2 minutes.
2. If it still says so, on Jellystat's tab select **Turn off**, then **Turn on**.
3. Still not answering: go to **System**, then **Logs**, and find its name.

## Check Jellyfin is running

The card says "Jellystat did not accept Jellyfin's address and key". Jellystat checks them against Jellyfin before saving them.

1. Check Jellyfin is running and its address in **Settings**, then **Apps**, is right.
2. Wait up to 2 minutes: it tries again by itself.

## Read how the restore went

1. On Jellystat's tab, open **Restore a Jellystat backup**. **Last restore** says what happened.
2. "It is not a PostgreSQL backup made with pg_dump -Fc": use a backup made with `pg_dump -Fc`. Jellystat's own JSON backups are restored in Jellystat itself.
3. "There is no" and the file's name: put the file in `data/plugins/jellystat/data/main/restore` and enter its name only in **Backup file to restore**.
4. "The backup did not restore, so nothing was changed": your figures are as they were. The words after it say why.
5. "Jellystat kept its database busy": select **Turn off** on its tab, then **Turn on**, and select **Restore the backup** again.

When a restore worked but Jellystat's pages still show the old figures, turn off and turn on Jellystat.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../jellystat/settings.md)
- [Updates](../jellystat/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
