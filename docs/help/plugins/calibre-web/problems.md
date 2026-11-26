# Calibre-Web: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Calibre-Web, then follow the numbered answer.

```flow
title: Find your answer
start: Calibre-Web is not working as it should
q: What does its tab say?
  Did not start -> 1
  Not supported -> 2
  Active, but something is wrong -> q2
q2: What is wrong?
  Its page does not open -> 3
  It finds no books -> 4
  It will not upload or edit books -> 5
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Open its page #open-its-page
4: Point it at your library #point-it-at-your-library
5: Add books with Calibre #add-books-with-calibre
```

## Start it again

Its tab says **Did not start** when Calibre-Web did not start, or stopped answering.

1. On Calibre-Web's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../calibre-web/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Calibre-Web works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Open its page

Calibre-Web's page is on your home network, at this computer's address and the port Starboard chose for it. The port is not always the usual one: Starboard takes the next free port when that one is in use.

1. Check Calibre-Web's tab says **Active**. Starboard gives it a port only once it is active.
2. Under **Its web page**, read the address, then select **Open Calibre-Web**.
3. Open it from a device on your home network. It does not open from away from home.
4. If it still does not open, deactivate it, activate it again and wait a minute for the app to start.

## Point it at your library

Calibre-Web finds books only in the `books` folder of your media folder, where a Calibre library keeps `metadata.db`.

1. Check that the `books` folder in your media folder has `metadata.db` in it. If your library is somewhere else, move it there with Calibre.
2. In Calibre-Web's admin settings, find **Location of Calibre database**.
3. Enter `/media/books` and save.

## Add books with Calibre

Starboard gives Calibre-Web the books folder read only, so it can never change your library. Uploading, editing details and deleting books in Calibre-Web do not work, by design.

1. Add or change books with Calibre itself, in the same library.
2. Calibre-Web shows the changes when it next reads the library.

## Report a problem

If none of these helps, tell its maker, with what its tab says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../calibre-web/settings.md)
- [Updates](../calibre-web/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
