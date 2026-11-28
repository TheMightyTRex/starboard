# Picture shrinker
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Shrinks the posters and photos of people Jellyfin keeps, so they take less space. Posters become 900 pixels tall and
photos of cast and crew 400 pixels wide, both settings. Each picture is checked before it replaces the one Jellyfin
saved. It runs on the schedule you choose, at the lowest priority.

A Starboard plug-in by TheMightyTRexUK, MIT licence. Its rules are those of a one-off shrink of a Jellyfin server's
pictures on 14 November 2026, now kept in `rules.json` (rules 1.1).

**A version for Jellyfin itself** runs on any Jellyfin 10.11 or 12 server, with or without Starboard: it is in
[TheMightyTRex/jellyfin-plugins](https://github.com/TheMightyTRex/jellyfin-plugins/tree/main/picture-shrinker), the
one repository for every Jellyfin plug-in by TheMightyTRexUK, whose address is
`https://raw.githubusercontent.com/TheMightyTRex/jellyfin-plugins/main/manifest.json`.
Both follow the same `rules.json` and shared test pictures; its [SYNC.md](https://github.com/TheMightyTRex/jellyfin-plugins/blob/main/picture-shrinker/SYNC.md)
says what must match and how to change a rule (`tools/sync_picture_rules.py` copies the rules here). When the Jellyfin
version is installed, this one stays idle and says so on its card, so the two never shrink the same pictures.

Read [HELP.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/picture-shrinker/HELP.md) for how to use it.

## What it does to a picture

| Picture | Where Jellyfin keeps it | Shrunk to |
|---|---|---|
| Posters | `poster.jpg`, `poster.png` or `poster.webp` under `library` in Jellyfin's metadata folder | At most 900 pixels tall (**Posters no taller than**) |
| Photos of cast and crew | Under `People` in Jellyfin's metadata folder | At most 400 pixels wide (**Photos of people no wider than**) |
| Backdrops | `backdrop.jpg`, `backdrop1.jpg` and so on under `library` | At most 1920 pixels wide |
| Thumbnails | `landscape.*` under `library` | At most 1280 pixels wide |
| Logos | `logo.*` under `library` | At most 800 pixels wide |
| Banners | `banner.*` under `library` | At most 1000 pixels wide |
| Disc art | `disc.*` under `library` | At most 500 pixels wide |
| Clear art | `clearart.*` under `library` | At most 800 pixels wide |

Every type is shrunk when you add it (**Shrink all picture types**); turn that off to choose types one by one.

A picture already that small is only opened, never written.

Each picture is written to a hidden file beside it (JPEG at **Quality** 85, progressive; PNG and WebP stay PNG and
WebP), opened again and decoded in full, checked for its size and format, and swapped in only when it is smaller than
the original. Jellyfin never reads a half-written file. A picture that cannot be read is left as it is and listed on
the **Space saved** page.

## The backup

**Original pictures** has no default: you choose **Keep a backup copy of each original** or **Shrink without a
backup** after you add it, and again after the update to 1.2.0 (rules 1.2). Nothing is shrunk until you choose, and the
card says **Choose a backup**. A backup you already have is kept whatever you choose.

With a backup, each original is copied once, before its first shrink, to `originals` in the plug-in's own folder,
keeping its place under `library` or `People`. A copy already there is never replaced. If the copy fails, or the disk
would have less than 100 MB free, the picture is not shrunk and the run says why.

- **Restore original pictures** in its actions puts every original back and keeps the backup.
- **Delete backup** in its actions removes the backup for good, after asking. Restore can then no longer put those
  pictures back; the shrunk pictures stay. It removes only the pictures in the backup folder and is refused while a
  run is going.
- **Space saved** shows the pictures now, the backup and the space saved, measured when the page opens; the cards show
  the figures kept after the last run or action.
- **Saved by type** and the **Space saved by type** card show the space each type of picture saved, counted as each
  run goes, so nothing is scanned to show them.

The first run may need almost as much free space as the pictures take now.

## Start again

Two actions clear everything and have Jellyfin download pictures again at full size. Each deletes the backup and the
records of what was shrunk, keeps the choice in **Original pictures**, is refused while a run is going, and changes
nothing if Jellyfin does not answer.

- **Start again: the pictures it shrinks** moves each poster, backdrop and photo of a person aside, to a hidden
  `.<name>.picture-shrinker-old` beside it, and asks Jellyfin to refresh that film, series or person with every
  picture checked again and nothing replaced, so Jellyfin downloads the missing one. A check every 10 minutes, only
  while pictures are waiting, deletes the old one once Jellyfin has a new one, and puts it back after 24 hours without
  one, so a poster you added yourself is never lost.
- **Start again: every picture** asks Jellyfin to refresh each library and each person with every picture replaced,
  backdrops and logos included.

## When it runs

- **When to shrink:** every day, every week on a day, or every month on a date, at a time. Every Sunday at 03:30 when
  you add it. **System**, **Jobs** shows when it runs next.
- **Shrink now** in its actions, or **Run now** in **System**, **Jobs**. **Stop shrinking** stops after the picture
  it is on.
- **Shrink new pictures in quiet hours:** turned off when you add it. When turned on, each hour of Starboard's quiet
  hours it shrinks the pictures Jellyfin saved since the last pass.
- **No notifications:** a finished run changes only the figures on its card and **Space saved** page. It sends no
  event, so the Notifications plug-in hears nothing, and the card's status stays on when it runs next. A run that
  failed says so on the **Space saved** page.

A run stops itself after 115 minutes, and the next one carries on: pictures already shrunk are only opened.

## What it may do

- It reads and changes Jellyfin's metadata folder: the posters, photos and details Jellyfin saved
  (`jellyfin:metadata`, medium risk). It changes only posters and photos of people, as the owner of Jellyfin's files.
- It uses Jellyfin's key (`jellyfin:key`, on the home network) for one thing: reading Jellyfin's list of plug-ins, at
  most every 10 minutes, to stay idle when the Jellyfin version is installed. No media file is touched.
- It runs one small container, with 128 MB of memory and half a processor at most; its work runs at nice 19 and in
  the idle disk class.

## How much it uses

Measured on 15 November 2026 against the Jellyfin version, one at a time, on a sample of 540 made-up pictures (300
posters at 2,000 by 3,000 pixels and 240 photos at 1,365 by 2,048, 776.3 MB), with backup turned on in both. This one
ran as Starboard runs it (128 MB, half a processor); the Jellyfin version in a throwaway Jellyfin 10.11.11.

| What | Jellyfin version | Starboard version (this plug-in) |
|---|---|---|
| Where it runs | Inside Jellyfin | Its own container beside Jellyfin |
| Memory at rest | At most about 15 MB more than Jellyfin without it (164 MB against 148 MB; the samples overlap) | 13 MB (its whole container) |
| Memory at the peak of a run | About 20 MB more than Jellyfin at rest (183 MB against 164 MB) | 33 MB (its whole container) |
| Memory after a run | Back to Jellyfin at rest (164 MB) | 23 MB (the image library stays loaded) |
| Processor time for the run | 35 seconds | 39 seconds |
| Time the run took | 55 seconds (one processor at most, as it uses one thread) | 80 seconds (capped at half a processor) |
| Pictures shrunk | 540 of 540 | 540 of 540 |
| Space saved | 758.8 MB (776.3 MB to 17.5 MB) | 758.4 MB (776.3 MB to 17.9 MB) |
| Jellyfin's answers during the run | `/System/Info` every 2 seconds: median 25 ms, slowest 68 ms (at rest: 30 ms and 59 ms) | Not affected (a separate container) |

Both work at the lowest priority. At rest both are small (about 13 to 15 MB). The Jellyfin version uses slightly
less processor time and less memory during a run; the Starboard version keeps its memory apart from Jellyfin's, so a
problem in it can never slow Jellyfin.

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

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
