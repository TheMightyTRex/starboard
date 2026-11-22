# Navidrome: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Navidrome from what its tab says or what happens, then follow the numbered answer.

```flow
title: Find your answer
start: Navidrome is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active -> q2
q2: What is wrong?
  Its page will not open -> 3
  Music is missing -> 4
  A Subsonic app cannot connect -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Open its web page #open-its-web-page
4: Put the music in the music folder #put-the-music-in-the-music-folder
5: Connect a Subsonic app #connect-a-subsonic-app
```

## Start it again

1. On Navidrome's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../navidrome/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Navidrome works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Open its web page

1. Go to **Settings**, then **Plug-ins**, then **Navidrome**.
2. Check its state is **Active**. If not, select **Activate**.
3. In **Its web page**, select **Open Navidrome**. Use the address shown there: Starboard chooses the port, 4533 when it is free, so it may be a different one.
4. Open it from a device on your home network. The page is not on the internet.

## Put the music in the music folder

Navidrome reads only `music` in your media folder, as `/media/music`. Music anywhere else is not shown.

1. Put your music in `music` in your media folder.
2. Open Navidrome to check the music is there. When it checks for new music is set in Navidrome itself: read [Navidrome's own help](https://www.navidrome.org).

It reads the folder only, so it cannot fix a file's name or tags for you.

## Connect a Subsonic app

1. In the app, use the address in **Its web page**, such as `http://192.168.1.20:4533`, with `http://` and the port.
2. Sign in with an account you made in Navidrome, not your Starboard account.
3. Use the app on your home network. Remote access shares only Starboard, Jellyfin and Audiobookshelf, so Navidrome does not answer away from home through it.

## Report a problem

If none of these helps, tell its maker, with what its tab says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues). For a problem inside Navidrome itself, read [Navidrome's own help](https://www.navidrome.org).

## Find out more

- [Settings](../navidrome/settings.md)
- [Updates](../navidrome/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
