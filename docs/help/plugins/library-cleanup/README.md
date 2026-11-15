# Library clean-up
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Moves films and series that everyone has watched, or that nobody has watched for a long time, to the holding folder,
so a small server's disks do not fill up. It never deletes: each item keeps its folders in
`media/.holding/library-cleanup`, and **Put back** returns it. Reelix stops following what moves, so it is not
downloaded again, and follows it again when it is put back.

A Starboard plug-in by TheMightyTRexUK, MIT licence. It follows the comparison report's recommendation 6 (DASH-406).

Read [HELP.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/HELP.md) for how to use it.

## The rules

| Rule | What it moves | Setting |
|---|---|---|
| Films watched by everyone | A film every person counted has watched, last watched more than 90 days ago | **Last watched more than**, 7 to 3,650 days |
| Series that ended, every episode watched | A series Jellyfin says has ended, every episode watched by everyone, the last more than the same days ago | the same |
| Films and series nobody watches | Nobody has watched it for 12 months, and it was added longer ago than that | **Not watched for**, 1 to 120 months |

Each rule is activated when you add it and can be deactivated. They look at the film and series libraries activated in
**Libraries** (all of them when you add it). "Everyone" is each Jellyfin user who can sign in, less those in
**People to leave out**.

Always kept, each a setting: favourites of anyone, anything in anyone's Continue watching or a series someone has
started, films in a collection, and anything with the keep tag (`keep`).

## What moves, and where

- A series: its folder. A film in its own folder: the folder. A film that shares a folder with other films, or sits at
  the top of the library: its file and the files beside it that share its name, such as subtitles.
- Into `media/.holding/library-cleanup/`, at the same place: `media/movies/A Film (2001)` becomes
  `media/.holding/library-cleanup/movies/A Film (2001)`.
- A move is a rename inside the media folder, so it is instant and needs no free space. A move that would have to copy
  is refused, and something with the same name already in the holding folder is never overwritten.
- Never the library folder itself, never the holding folder, never anything outside the media folder.

Reelix: the film or series stops being followed, with each followed episode, and is rescanned; Put back follows again
exactly what was followed. Jellyfin: told the path was deleted, or created on Put back, so it updates at once.

## When it runs

- **Preview**, worked out in the background when opened, when a setting changes, after six hours, or with **Preview
  again**: what would move and the space it frees. Nothing moves from Preview.
- **Move items to the holding folder**, a job once a day in Starboard's quiet hours, only when **Move items each
  day** is activated. It is deactivated when you add it. **Run now** in **System**, **Jobs** runs it at once, also only
  when activated. A run moves up to 200 items, within 50 minutes; the next carries on.

## What it may do

- `library:holding` (plug-in API 1.15, high risk): the media folder, read and write, at `/media`, to move items into
  its holding folder and back. Its code has no call that deletes a file or a folder; `tests/test_library_cleanup.py`
  checks that.
- `jellyfin:key` (high risk): reads each person's watched state, favourites, Continue watching and collections, and
  tells Jellyfin what moved.
- `reelix:key` (high risk): stops following what moves and follows it again on Put back. Without Reelix it still moves.
- `network:lan` (medium risk): your home network, where Jellyfin and Reelix answer.
- It runs as the owner of the media folder, so moved folders keep their owner.
- Memory, measured 15 November 2026 on made-up data (3,000 films and 300 series for 3 people): about 14 MB at rest,
  31 MB at its peak while working out Preview and moving 200 items, 28 MB after; 0% of a processor at rest. It is
  allowed 128 MB and half a processor, and rests when not used.

## Updating

Before an update it finishes the item it is moving and starts no new run, so nothing is left half moved. What changed
in each version is in [CHANGELOG.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/library-cleanup/CHANGELOG.md), and Starboard shows it before you update.

## Add it

Needs Starboard with plug-in API 1.15, Jellyfin, and Reelix to stop it being downloaded again. In Starboard, open
**Settings**, **Plug-ins**, **Catalogue**: it is under **Jellyfin**. Starboard never adds it by itself. Or give this
address under **Add a plug-in**:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/library-cleanup/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
