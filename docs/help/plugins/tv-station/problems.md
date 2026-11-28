# Create your own TV channel: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Create your own TV channel, then follow the numbered answer.

```flow
title: Find your answer
start: Create your own TV channel is not working as it should
q: Where is the problem?
  Its tab says Failed or Not answering -> 1
  The channels are not in Jellyfin -> 2
  A channel will not play -> q2
  A channel has nothing on -> 4
  A broadcast pack was not used -> 6
  There are no promos -> 7
q2: What happens?
  Jellyfin says no tuner is free -> 3
  It starts, then stops -> 5
1: Start it again #start-it-again
2: Give Jellyfin its address #give-jellyfin-its-address
3: Let more channels play at once #let-more-channels-play-at-once
4: Add something to the channel #add-something-to-the-channel
5: Check the stream #check-the-stream
6: Fix the pack and upload it again #fix-the-pack-and-upload-it-again
7: Give promos what they need #give-promos-what-they-need
```

## Start it again

1. On Create your own TV channel's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../tv-station/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Give Jellyfin its address

Jellyfin reads the channel list and the guide from Create your own TV channel's own web page, so Create your own TV channel needs to know the address Jellyfin can reach it at.

1. Check Starboard is 0.23.0 or later, in **Settings**, **Updates**: it gives Create your own TV channel its address on your home network by itself. With an older Starboard, on Create your own TV channel's tab, next to its web page's address, select **Open**, and a page with the station's name opens.
2. Within a minute, Create your own TV channel adds its tuner and guide to Jellyfin and starts Jellyfin's guide refresh.
3. If Jellyfin runs on another computer, enter the address it reaches this server at in **Address Jellyfin uses to reach this plug-in**, in **Station**, then select **Read the channels from Jellyfin again**.
4. In Jellyfin, go to **Dashboard**, then **Live TV**: the tuner has the station's name. Select **Refresh guide data** if the channels have no programmes.

## Let more channels play at once

Each channel being watched is one conversion, and **Most channels at once** is 2 unless you change it. People watching the same channel share one, so it is the number of different channels at once.

1. In **Streaming**, raise **Most channels at once**. Each one adds about 0.9 of a processor core at 720p.
2. Or choose **720p** in **Picture size**, which is lighter.

## Add something to the channel

A channel with nothing in **What it shows**, or whose series and films Jellyfin no longer has, has nothing to play.

1. Open the channel in **Channels** and add a series, film, collection or playlist.
2. Select **Read the channels from Jellyfin again**.
3. Check **Today and tomorrow** on the channel's page.

## Check the stream

1. Select **Preview a frame** on the channel's page. If it says what went wrong, such as Jellyfin not answering, fix that first.
2. A programme that will not play is replaced by a slate with the station's name for 20 seconds, then the channel goes on.
3. Check **System**, then **Logs**, for Create your own TV channel.
4. If the server is busy, choose **720p** in **Picture size**, or turn off the on-screen logo and the straps for that channel, so it copies its programmes with no converting.

## Fix the pack and upload it again

The pack is checked before anything in it is used, and the pack in use stays when it does not pass.

1. In **Broadcast pack**, read **The last pack checked**: each row names a file and what to change, such as a logo with no transparent parts or a file name the pack does not use.
2. Change those files. [Make a broadcast pack](https://themightytrex.github.io/starboard-plugins/help/use/make-a-broadcast-pack.html) has every name, size and length.
3. Zip the folder again and select **Upload a pack**.
4. Still refused: download the template, put your files in its folders with the same names, and upload that.

## Give promos what they need

1. Check the channel's broadcast pack has a promo: **Broadcast pack**, **Each channel's pack**, then its summary under **Station's pack** says "a promo". The example pack has one.
2. Check **Make promos in quiet hours** is on, in the plug-in's settings under **Promos**.
3. Promos are made in Starboard's quiet hours while nobody is watching anything in Jellyfin. To make them now, select **Make promos now** on the plug-in's tab, with nothing playing.
4. A channel needs programmes in the next 6 days that start at least 2 hours from now.

## Find out more

- [Settings](../tv-station/settings.md)
- [A plug-in is not working](https://themightytrex.github.io/starboard-plugins/help/fix/a-plug-in-is-not-working.html)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
