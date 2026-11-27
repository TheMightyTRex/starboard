# Calibre library maker: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Calibre library maker has one page, **Make a Calibre library from your books**, in **Settings**, then **Plug-ins**, then **Calibre library maker**.

## What the page shows

- **Your books folder:** how many book files it found, how many are not yet in the library, and their size.
- **Your Calibre library:** how many books `books-library` holds, or that it is not made yet.
- **What Make the library will do:** the books to copy, the room needed and free, and the time it takes. It says **Not enough room** when the disk is too full, and does not start.
- **Last run:** what happened, and when.
- **Left out:** each file it could not read, with the reason.
- **Added, no author:** each book Calibre found no title or author inside.

## Buttons

- **Make the library** asks first, then copies the books that are not in the library yet. It takes about 3 seconds a book.
- **Stop** ends the run after the books it is adding now. Run it again to carry on.
- **Deactivate** stops the plug-in and keeps its folder. **Remove Calibre library maker** takes it away; nothing is deleted.

## Things to note

- Your `books` folder is read only here. Nothing in it is changed, moved or deleted.
- The library is a copy. Delete the `books-library` folder yourself, outside Starboard, if you want it gone.
- A file with a format Calibre does not know is not copied. It reads epub, mobi, azw, azw3, kepub, pdf, fb2, txt, rtf, docx, odt, cbz, cbr, djvu and lit.

## Find out more

- [Install](../calibre-library/install.md)
- [Problems](../calibre-library/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
