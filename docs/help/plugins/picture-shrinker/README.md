# Picture shrinker
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Shrinks the posters and photos of people Jellyfin keeps, so they take less space. Posters become 900 pixels tall and
photos of cast and crew 400 pixels wide, both settings. Each picture is checked before it replaces the one Jellyfin
saved. It runs on the schedule you choose, at the lowest priority.

A Starboard plug-in by TheMightyTRexUK, MIT licence. Its rules are those of a one-off shrink of a Jellyfin server's
pictures on 14 November 2026.

Read [HELP.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/HELP.md) for how to use it.

## What it does to a picture

| Picture | Where Jellyfin keeps it | Shrunk to |
|---|---|---|
| Posters | `poster.jpg`, `poster.png` or `poster.webp` under `library` in Jellyfin's metadata folder | At most 900 pixels tall (**Posters no taller than**) |
| Photos of cast and crew | Under `People` in Jellyfin's metadata folder | At most 400 pixels wide (**Photos of people no wider than**) |

A picture already that small is only opened, never written. Backdrops, logos and other pictures are left alone.

Each picture is written to a hidden file beside it (JPEG at quality 85, progressive; PNG and WebP stay PNG and WebP),
opened again and decoded in full, checked for its size and format, and swapped in only when it is smaller than the
original. Jellyfin never reads a half-written file. A picture that cannot be read is left as it is and listed on the
**Space saved** page.

## When it runs

- **When to shrink:** every day, every week on a day, or every month on a date, at a time. Every Sunday at 03:30 when
  you add it. **System**, **Jobs** shows when it runs next.
- **Shrink now** in its actions, or **Run now** in **System**, **Jobs**. **Stop shrinking** stops after the picture
  it is on.
- **Shrink new pictures in quiet hours:** deactivated when you add it. When activated, each hour of Starboard's quiet
  hours it shrinks the pictures Jellyfin saved since the last pass.

A run stops itself after 115 minutes, and the next one carries on: pictures already shrunk are only opened.

## What it may do

- It reads and changes Jellyfin's metadata folder: the posters, photos and details Jellyfin saved
  (`jellyfin:metadata`, medium risk). It changes only posters and photos of people, as the owner of Jellyfin's files.
- It reaches nothing else: no network, no key, no media file.
- It runs one small container, with 128 MB of memory and half a processor at most; its work runs at nice 19 and in
  the idle disk class.

## Updating

Before an update it stops after the picture it is on and starts no new run, so nothing is left half done. What
changed in each version is in [CHANGELOG.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/CHANGELOG.md), and Starboard shows it before you update.

## Add it

Needs Starboard with plug-in API 1.14 or later, and Jellyfin. In Starboard, open **Settings**, **Plug-ins**, **Catalogue**: it
is under **Jellyfin**. Starboard never adds it by itself. Or give this address under **Add one from elsewhere**:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/picture-shrinker/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
