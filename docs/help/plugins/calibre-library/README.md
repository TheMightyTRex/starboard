# Calibre library maker
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Makes a Calibre library from the books in your books folder, in a new folder beside it, so Calibre-Web has something to open. Your own books are never changed.

An app plug-in for Starboard (plug-in API 1.14 or later). It rests when it is not used, so it costs nothing while you read.

## Who it is for

People who keep books as files, such as `Author/Title.epub`, and want Calibre-Web (or Calibre) to list them. Calibre-Web needs a Calibre library, which is a folder with `metadata.db` in it. A folder of book files is not one.

## What it does

- Reads your `books` folder, read only. It never changes, moves or deletes a book there.
- Copies each book into a new library in `books-library`, with Calibre's own tool, `calibredb`. It copies, so the library needs room for a second copy of your books. It says how much first.
- Says what it will do before it starts: how many books, how much room and about how long (about 3 seconds a book).
- Shows progress in words. A file it could not read is listed with the reason and left out. A book Calibre found no author in is listed too.
- Safe to run again: it remembers what it has handled. Calibre also skips a book that is already in the library, so only new books are added.
- Calibre-Web, set up by Starboard, opens `books-library` at its next start.

## What it may do

- It can read: Files in your media folder under books (read only).
- It can change: Its own folder in Starboard's data, and the `books-library` folder in your media folder.
- It can reach: nothing. It has no way out to your home network or the internet.

It runs read only, as a user that is not root, with no extra rights, like every plug-in. Its image holds Calibre's command line tools, about 0.7 GB on disk, and is pulled when you add it.

## At rest

Nothing is running when it is not used: Starboard stops it after 5 idle minutes and starts it when you open its page. Measured 26 November 2026, hardened as Starboard runs it. It uses 14 MiB and no processor while it waits, and up to 73 MiB while Calibre adds books. It added 13 books in 26 seconds from a cold start (about 2.5 seconds a book after 6 seconds to start). The image is 703 MB on disk.

## Removing it

**Settings**, **Plug-ins**, Calibre library maker, **Remove**. Your books and the library it made are not touched, and you choose where its own folder goes.

## Licence

This plug-in is MIT, by TheMightyTRexUK. Calibre is under the GPL-3.0 licence, made by others: https://calibre-ebook.com

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
