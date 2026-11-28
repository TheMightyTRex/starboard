# Calibre library maker: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Calibre library maker, then follow the numbered answer.

```flow
title: Find your answer
start: The library is not made
q: What does its page say?
  Not enough room -> 1
  Left out, with files listed -> 2
  It was interrupted -> 3
  Done, but Calibre-Web shows nothing -> 4
1: Make room #make-room
2: Fix files that were left out #fix-files-that-were-left-out
3: Carry on #carry-on
4: Make Calibre-Web open the library #make-calibre-web-open-the-library
```

## Make room

The library is a copy of your books, so the disk that holds your media folder needs about as much free room again. The page says how much it needs and how much is free.

1. Free some room, or move your media folder to a larger disk.
2. Reload the page, then select **Make the library** again.

## Fix files that were left out

A file is left out when it is empty, cut short or not the kind of file its name says. Calibre adds a damaged file with no details, so the plug-in leaves it out and lists it instead.

1. Read the reason beside each file.
2. Replace the file with a good copy in your books folder. Starboard never changes your books for you.
3. Select **Make the library** again. It adds only what is new, and tries the left-out files again.

## Carry on

A restart or an update can cut a run short. The page says **It was interrupted**.

1. Select **Make the library** again. Books already added are kept, and only the rest are copied.

## Make Calibre-Web open the library

Calibre-Web sets its library only when it starts.

1. Go to **Settings**, then **Plug-ins**, then **Calibre-Web**.
2. Select **Turn off**, then **Turn on**.
3. Open Calibre-Web again. If it still shows nothing, read [Calibre-Web, your books](https://themightytrex.github.io/starboard-plugins/help/plugins/calibre-web/your-books.html).

## Report a problem

If none of these helps, tell its maker, with what its page says: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../calibre-library/settings.md)
- [Updates](../calibre-library/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
