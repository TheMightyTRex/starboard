# Kavita: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Kavita from what its tab says or what happens, then follow the numbered answer.

```flow
title: Find your answer
start: Kavita is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Needs an update -> 2
  Active -> q2
q2: What is wrong?
  Its page will not open -> 3
  Books or comics are missing -> 4
  An e-reader app cannot connect -> 5
  There are two Kavitas -> 6
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Open its web page #open-its-web-page
4: Add the libraries #add-the-libraries
5: Connect a reading app #connect-a-reading-app
6: Keep one Kavita #keep-one-kavita
```

## Start it again

1. On Kavita's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../kavita/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Kavita works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Open its web page

1. Go to **Settings**, then **Plug-ins**, then **Kavita**.
2. Check its state is **Active**. If not, select **Turn on**.
3. In **Its web page**, select **Open Kavita**. Use the address shown there: Starboard chooses the port, 5000 when it is free, so it may be a different one.
4. Open it from a device on your home network. The page is not on the internet.

## Add the libraries

Kavita can read only `books` and `comics` in your media folder, as `/media/books` and `/media/comics`, and shows nothing until you add a library.

1. Open Kavita and sign in with its admin account.
2. Add a library for `/media/books`.
3. Add a library for `/media/comics`.
4. Put your files in those two folders. Files anywhere else are not shown.

It reads the folders only, so it cannot change, move or delete a file.

## Connect a reading app

1. In an app that speaks OPDS, use the address in **Its web page**, with `http://` and the port.
2. Sign in with an account you made in Kavita, not your Starboard account.
3. Use the app on your home network. Remote access shares only Starboard, Jellyfin and Audiobookshelf, so Kavita does not answer away from home through it.

## Keep one Kavita

The main install can also add Kavita, in **Install apps**, **Ebooks**. With both, the plug-in takes another port when 5000 is in use, and each has its own accounts and libraries.

1. Choose the one you want to keep.
2. Remove the other. For the plug-in, read [Install](../kavita/install.md).

## Report a problem

If none of these helps, tell its maker, with what its tab says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues). For a problem inside Kavita itself, read [Kavita's own help](https://www.kavitareader.com).

## Find out more

- [Settings](../kavita/settings.md)
- [Updates](../kavita/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
