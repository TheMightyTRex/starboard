[Help centre](../README.md) · Everyday use · how-to

# Download only at certain hours

Starboard can pause qBittorrent and SABnzbd outside the hours you choose, for example to keep your internet
free during the day. At the end, downloads run only between your start and end times, and you can still resume
or pause them by hand.

## Before you begin

- qBittorrent, SABnzbd or both are in Starboard with their API keys. Read [Add an app](add-an-app.md) and
  [Find an app's API key](find-an-api-key.md).
- qBittorrent must be version 5.2 or later, because older versions have no API key. In qBittorrent the key is in
  **Options**, then **Web UI**. In SABnzbd it is in **Config**, then **General**.

## Steps

1. Go to **Settings**, then **General**.
2. Find **Download hours**. If it says **No download apps yet**, add qBittorrent or SABnzbd with its API key
   first.
3. In **Start**, choose the hour downloads start, such as **01:00**.
4. In **End**, choose the hour downloads pause, such as **07:00**.
5. Activate **Only download between set hours**. Starboard confirms with **Download hours activated**, and the hours, such as
   "Downloads run from 01:00 to 07:00".

Each change applies at once. There is no save button.

### Resume or pause by hand

1. Go to **Activity**, then **Downloads**, then **Queue**.
2. In **Download hours**, select **Resume downloads now** or **Pause downloads until** and a time.
3. To go back to your hours, select **Follow the hours**. Otherwise Starboard goes back to them at the next
   start or end time.

## Things to note

- An end time before the start time runs overnight. For example, a start of 23:00 and an end of 07:00 downloads
  through the night.
- The hours use the server's own time. With the ready-made image, the `TZ` line in `compose.image.yaml` sets
  the time zone, such as `TZ=Europe/London`.
- Starboard starts again only what it paused. Anything you paused yourself in qBittorrent or SABnzbd stays
  paused. Seeding is left alone.
- Starboard checks every minute while download hours are active, unless you chose the **Small server** preset.
  To change it, go to **Settings**, then **Performance**, and change **Download hours check**.
- The Downloads page shows the state of download hours, such as **Downloading** or **Paused**, and when it next
  changes.

## If it does not work

- **No qBittorrent or SABnzbd with an API key is set up yet:** paste the app's API key. Edit the app in
  **Settings**, then **Apps**, then **Manage apps**. Read [Change or remove an app](change-or-remove-an-app.md).
- **qBittorrent has no API key:** update qBittorrent to version 5.2 or later.
- **Downloads pause at the wrong hour:** the server's time zone may be wrong. With the ready-made image, check
  the `TZ` line in `compose.image.yaml`. Then, in the folder with that file, run this command to start
  Starboard again with the new setting:

  ```bash
  docker compose -f compose.image.yaml up -d
  ```
- **Downloads resumed, with problems:** one download client did not answer. Check it is running, then select
  **Follow the hours** again.

## Find out more

- [Pause, resume and remove downloads](manage-downloads.md)
- [Make Starboard use less of your server](make-starboard-lighter.md)
- [What an API key is](../basics/what-is-an-api-key.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
