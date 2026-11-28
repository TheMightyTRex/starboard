# Direct play
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Makes your films and series play directly on the devices you choose, so Jellyfin does not have to convert them while
they play. It fixes one file at a time, at the lowest priority, in the hours you choose, and checks each new file
before it replaces the old one.

A Starboard plug-in by TheMightyTRexUK, MIT licence. Its rules are those of a script that converted 1,173 files and
saved 1.03 TB on the server it was written for.

Read [HELP.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/HELP.md) for how to use it.

## What it does to a file

Cheapest first, one at a time:

| Fix | When | How |
|---|---|---|
| Repackage as MKV | The wrong container, such as AVI, M2TS or TS | The streams are copied into MKV; nothing is converted |
| Add a playable sound track | No sound track every chosen device plays, such as DTS, TrueHD or FLAC only | A Dolby Digital 5.1 track (or AAC stereo when a chosen device lacks Dolby Digital) is added first; the original track is kept |
| Shrink | H.264 over the bitrate you set: 15 Mbps for 1080p, 8 for 720p, 5 for smaller | H.264 at CRF 20, capped at 10 Mbps; kept as it was unless it gets at least a tenth smaller |
| Convert to H.264 | DivX, Xvid, MPEG-2, WMV, VC-1, 10-bit H.264, larger than a chosen device shows, or HEVC when you ask and no chosen device plays it | H.264 at CRF 20 |

HEVC is left alone unless you turn on **Convert HEVC to H.264**: it costs space, and Jellyfin converts it as it
plays. Subtitles, chapters and fonts are kept.

## Each new file is checked

Before it replaces the original: its length is within 2 seconds (or 0.5%) of the original's, it has a picture of
the right kind, its first sound track is one your devices play, sound and picture start within half a second of each
other, and it has every subtitle track. A file that fails is left as it was and listed under **Not fixed** with why.
Then Reelix rescans the film or series, and Jellyfin is told the file changed.

## What it may do

- It uses Jellyfin's key and Reelix's key, which Starboard keeps, only to tell them a file changed.
- It reaches your home network, where Jellyfin and Reelix are.
- It can read and change files in your media folder under movies and tv, as the owner of your media folder.
- It runs one container, with 512 MB of memory and one processor at most. ffmpeg runs only while a file is fixed,
  at the lowest processor and disk priority, two threads at most.

## Add it

Needs Starboard with plug-in API 1.14 or later, and Jellyfin. In Starboard, open **Settings**, **Plug-ins**,
**Catalogue**: it is under **Jellyfin**, marked **Recommended**. Or give this address under **Add one from elsewhere**:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/direct-play/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
