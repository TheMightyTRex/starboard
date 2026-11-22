# Watch statistics
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

What was watched, by whom and when, and the top titles, from Jellyfin's Playback Reporting, with no second database.

An example Starboard plug-in by TheMightyTRexUK, MIT licence.

## What it may do

- It uses Jellyfin's key, which Starboard keeps.
- It reaches your home network and the internet.
- It runs one small container (64 MB of memory at most).

## On the dashboard

- **Plays this week**: a stat card.
- **Top titles**: a list card.
- **Who watched most**: a list card.
- **Watch statistics source**: a status card.

## In its section of Settings, Plug-ins

- **Recent plays**: a table to read.
- **Top titles**: a table to read.
- **People**: a table to read.

## Settings

- **Over the last**
- **Leave out these people**: One Jellyfin user name a line, such as an account for testing.

## Playback Reporting

The figures come from [Playback Reporting](https://github.com/jellyfin/jellyfin-plugin-playbackreporting), a plug-in
for Jellyfin in its official catalogue. Add it in Starboard's **Settings**, **Jellyfin**, or in Jellyfin's
**Dashboard**, **Plugins**, **Catalogue**, then restart Jellyfin. It counts from then on, and keeps its own history
inside Jellyfin's data, so nothing else needs a database.

Without it, this plug-in says so on its tables and its **Watch statistics source** card, and shows what Jellyfin knows
itself: each person's last play of each title, with no device or time watched.

## In place of Jellystat

Jellystat needs two containers and PostgreSQL (about 60 MB measured on a small server, 150 to 250 MB on a busy one).
This plug-in rests when nobody is using it, and uses about 14 MB for a few seconds when a card or table asks.

## Updating

Before an update, it finishes any check or message it is part way through and starts no new one, so the update never cuts one short (plug-in API 1.14). What changed in each version is in [CHANGELOG.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/watch-stats/CHANGELOG.md), and Starboard shows it before you update.

## Add it

Needs Starboard with plug-in API 1.14 or later, and Jellyfin added in **Settings**, then **Apps**; a Starboard with an older plug-in API is offered the version before. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it under **Jellyfin**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/watch-stats/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
