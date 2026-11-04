[Help centre](../README.md) · Jellyfin and Audiobookshelf · how-to

# Set up free Live TV in Jellyfin

Starboard can build free TV channels and their guides for Jellyfin's Live TV, from Samsung TV Plus, Pluto TV
and Free-TV. At the end, Jellyfin shows the channels with a TV guide, numbered the way Sky numbers them.

## Before you begin

- Jellyfin is installed and on your dashboard. Read [Add an app](add-an-app.md). Live TV works without
  Jellyfin's API key.
- Starboard can write to the folder Jellyfin reads its Live TV files from. The installer asks
  "Give Starboard a Live TV folder?": answer yes and give the folder, such as `/srv/jellyfin/config/iptv`.
  To change your answer, read [Change what Starboard can access](change-what-starboard-can-access.md).
- Phones and other computers on your home network can open Starboard, because Jellyfin fetches channel
  logos and Pluto TV streams from it. Read [Choose who can open Starboard](choose-who-can-open-starboard.md).

## Steps

### Activate Live TV in Starboard

1. Go to **Settings**, then **Apps**, then **Jellyfin**.
2. In **Live TV**, activate **Build Live TV channels and guide**.
3. Check **Address Jellyfin uses to reach Starboard**. Leave it blank to use the address Starboard shows in
   the field. If Jellyfin needs another address, type it, such as `http://192.168.1.20:8095`, and select
   **Save address**.
4. Select **Run Live TV now** to build the files straight away.

The first run tests every stream, so it takes a few minutes. When it ends, Starboard shows **Last run
worked** and what it did.

### Add the channels and guides in Jellyfin

1. Open Jellyfin and go to **Dashboard**, then **Live TV**.
2. Add a tuner of type M3U for each of these playlists, from the Live TV folder:
   - `channels.m3u`
   - `samsung.m3u`
   - `pluto.m3u`
3. Add an XMLTV guide for each of these guide files, from the same folder:
   - `guide.xml`
   - `guide-samsung.xml`
   - `guide-pluto.xml`
4. Let Jellyfin refresh its guide data.

Use the folder as Jellyfin sees it. If Jellyfin runs in Docker, that is the path inside Jellyfin's
container. For example, if `/srv/jellyfin/config` on the server is `/config` for Jellyfin, the playlist is
`/config/iptv/channels.m3u`.

## Things to note

- Starboard refreshes the guides once a day. It rebuilds the channel lists only when a source's list
  changes, or once a week to drop channels that stopped playing.
- Only free channels are included. Starboard skips channels that need DRM (digital rights management),
  adult channels and anything that does not play from your connection.
- Channels are numbered in blocks: 101 Entertainment, 401 Lifestyle, 451 Movies, 501 Music, 601 Sport,
  701 News, 801 Documentaries, 1001 Kids and 1101 Other.
- **White channel logos** turns each logo white on a clear background. Deactivate it to keep each channel's
  own logo.
- The page section **How Jellyfin uses these files** repeats the file names, so you can check them there.
- To make Live TV open on the Guide for everyone, read
  [Give every Jellyfin user the same defaults](jellyfin-user-defaults.md).
- Live TV uses a little of your server once a day, and more once a week while it tests streams. Read
  [Make Starboard use less of your server](make-starboard-lighter.md).

## If it does not work

- **"Needs set-up on the server":** Starboard has no Live TV folder. Run `./install.sh` again and say yes to
  Live TV. Read [Change what Starboard can access](change-what-starboard-can-access.md).
- **Channels have no logos, or Pluto TV channels do not play:** Jellyfin cannot reach Starboard. Check that
  home network access is active, and that **Address Jellyfin uses to reach Starboard** opens from the computer
  Jellyfin runs on.
- **"Last run failed":** read the reason next to it, then read [Read the log and report a problem](read-the-log.md).

## Find out more

- [Give every Jellyfin user the same defaults](jellyfin-user-defaults.md)
- [Change what Starboard can access](change-what-starboard-can-access.md)
- [The apps Starboard works with](../basics/the-apps.md)
