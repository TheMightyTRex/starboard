[Help centre](../README.md) · Everyday use · how-to
<!-- help: use / library -->

# Limit how fast your downloads go

You can set how fast qBittorrent and NZBGet download, and how fast qBittorrent uploads, without opening their own pages.
This helps when the family streams in the evening and a download would slow the picture down. The settings are in
Starboard, with a keyboard and a screen reader in mind.

## Before you begin

- qBittorrent or NZBGet is in Starboard with its API key. Read [Add an app](add-an-app.md) and
  [Find an app's API key](find-an-api-key.md#where-each-app-keeps-its-key).
- qBittorrent must be version 5.2 or later, because older versions have no API key.

## Steps

1. Go to **Settings**, then **Downloads**, then **Speed limits**. If it says **No download app with a key yet**, add the app
   with its API key first.
2. Find the app. In **Download limit**, enter how many kilobytes a second it may download. 1,000 is about 1 megabyte a second.
   Enter 0 for no limit.
3. For qBittorrent, in **Upload limit**, enter how many kilobytes a second it may upload, or 0 for no limit.
4. Move to the next control. Starboard says **Saved** beside the one you changed.

To use the second pair of limits you set in qBittorrent, such as for the daytime, activate **Use the alternative speed limits**.
Starboard does not change those limits. Set them in qBittorrent, under **Speed**.

Each change applies at once. There is no save button.

## Things to note

- A limit covers every download of that app together, not each download.
- Starboard asks the apps only when this page is open and when you change a limit. It does nothing in the background.
- A speed limit is not the same as **Download hours**, which pause downloads. They work together: the limit applies while
  downloads run. Read [Download only at certain hours](set-download-hours.md).
- SABnzbd is not on this page yet. Set its limit in SABnzbd.

## If it does not work

- **The page says an app did not answer:** check that the app is running, then open the page again.
- **A limit does not stay:** an app can change its own limits at set times, such as qBittorrent's speed schedule. Check its
  own scheduler.
- **A message says to give a whole number:** enter digits only, such as 500. Decimals and units such as MB are not accepted.

## Find out more

- [Download only at certain hours](set-download-hours.md)
- [Pause, resume and remove downloads](manage-downloads.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
