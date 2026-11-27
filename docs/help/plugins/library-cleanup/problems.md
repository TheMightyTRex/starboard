# Library clean-up: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Library clean-up, then follow the numbered answer.

```flow
title: Find your answer
start: Library clean-up is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Needs an update -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  Nothing moves -> 3
  Preview lists nothing, or the wrong things -> 4
  The card says Last run failed -> 5
  Put back did not work -> 6
  The disk is as full as before -> 7
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Check Move items each day #check-move-items-each-day
4: Check the rules #check-the-rules
5: Read what the card says #read-what-the-card-says
6: Check the Holding folder page #check-the-holding-folder-page
7: Free the space for good #free-the-space-for-good
```

## Start it again

1. On Library clean-up's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../library-cleanup/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

It stops answering when it cannot read and change the media folder, or cannot write its own folder. Check that Jellyfin is added in **Settings**, then **Apps**, then deactivate and activate Library clean-up.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Library clean-up works with, so Starboard stopped it. Library clean-up needs plug-in API 1.15, in Starboard 0.19.0 or later.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Check Move items each day

- Nothing moves until **Move items each day** is activated in **Rules**. When it is deactivated, the card says **Deactivated** and what **Preview** would move.
- It moves once a day, in Starboard's quiet hours. To move straight away, go to **System**, then **Jobs**, and select **Run now** beside **Move items to the holding folder**.
- A run moves up to 200 items, within 50 minutes. The next run carries on.
- A move that would have to copy the files is not made, and something with the same name already in the holding folder is never overwritten.

## Check the rules

- **Films watched by everyone** finds nothing when one person never watches, such as a guest account. Add their Jellyfin user name to **People to leave out**.
- Check that the rules you want are activated in **Rules**, and that the library is not deactivated in **Libraries**.
- Something in **Always keep** stays: favourites, anything someone is part way through, films in a collection and anything with the keep tag.
- To keep something **Preview** lists, add the keep tag to it in Jellyfin, or change the rules. Then select **Preview again** and check the list again.
- **Preview** is worked out in the background, which takes a few seconds on a large library. The page updates by itself.

## Read what the card says

- **No answer from** and its name: it did not answer in 3 seconds. Check that it is **Active** on its tab, then wait a minute.
- **Last run failed** in the band: the card says "The last run did not finish" and why. Fix that, then select **Run now** in **System**, then **Jobs**, or wait for the next run.

## Check the Holding folder page

1. On Library clean-up's tab, open **Holding folder**.
2. Find the item. If something else is in its place now, it stays in the holding folder and the page says so. Move or rename what is in its place, then select **Put back** again.
3. Jellyfin is told when an item is put back, so it is back in your library within a minute. Reelix follows it again exactly as before.

If you removed Library clean-up, **Put back** has gone. Move the folder back from `media/.holding/library-cleanup` yourself, then choose **Follow** for it in Starboard's **Library**.

## Free the space for good

Library clean-up never deletes, so the space is still used while an item is in the holding folder. When you are sure you do not want something, delete its folder in `media/.holding/library-cleanup` yourself, with your computer's file manager or a terminal.

## Report a problem

If none of these helps, tell its maker, with what its tab and the card say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../library-cleanup/settings.md)
- [Updates](../library-cleanup/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
