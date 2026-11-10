[Help centre](../README.md) · Your server · how-to

# Make Starboard use less of your server

Starboard is built to be light, but some of its features do work in the background. The Performance page lets
you choose a preset, or activate and deactivate each piece of work one by one.

## Steps

1. Go to **Settings**, then **Performance**.
2. Under **Preset**, choose one. The change applies at once.
   - **Small server:** for a small or busy server. No history, no watching, no card numbers, no white logos or
     posters, no hourly Jellyfin or Audiobookshelf jobs, and slower pages.
   - **Balanced:** the default. History every 5 minutes, card numbers, white logos, posters and normal page
     updates.
   - **Everything:** everything on and as fresh as it goes, including watching every 5 minutes with a weekly
     summary.
   - **Custom:** your own choices. Changing any single item yourself makes the preset **Custom**.
3. Optional: to change single items, activate **Advanced settings**. Then change any item under
   **Background work** or **While a page is open**. Each one applies at once.

With **Advanced settings** active, **Starboard now** also shows Starboard's own **Memory**, its **Processor** use
and what is **Running**.

## What each item costs

Each item on the page says what it costs, measured on a home server. In short:

### Background work

This runs with no page open.

- **System history:** readings for the charts on System, Overview. Under 0.01% of the processor and up to 1.5 MB
  of memory.
- **Watching and alerts:** checks your apps and sends alerts. About 0.02 seconds of processor per check, and
  under 1 MB of memory. Read [Activate alerts](activate-alerts.md).
- **Download hours check:** every minute or every 5 minutes, only while download hours are in use. Every 5
  minutes uses a fifth of the requests. Read [Set download hours](set-download-hours.md).
- **Live TV white logos:** only while Live TV is active. A second or two per new logo, and up to 15 MB more memory
  while it runs.
- **Keep applying imported history:** up to 40 MB more memory for about 20 seconds an hour.
- **Jellyfin user defaults:** two small requests per Jellyfin user an hour.
- **Keep applying listening progress:** one reading of Audiobookshelf an hour, under a second of processor.
- **Work out what uses the space:** reads every file name in your folders. A few minutes for a large drive, so
  it runs only when you choose. Read [Check free space and what is using it](check-storage.md#sort-the-space-by-type).
- **Daily record of used space:** one size check a day. Nothing noticeable.
- **Posters on Coming up and the Library:** a small download per new poster, kept for a week. When it is
  inactive, Coming up shows each app's icon and the Library shows titles on plain tiles.

### While a page is open

This runs only while the page is open and in view. A hidden tab asks for nothing.

- **Downloads page updates:** how often Downloads asks your download apps, or **Only when I press Check
  again**.
- **Storage page updates:** how often Storage checks each folder's size.
- **Monitor page readings:** every 2, 5 or 10 seconds.
- **Numbers on app cards:** such as 3 in the queue, on Apps. One small request per app when Apps opens.

## Things to note

- Features you chose for what they do, such as Live TV and download hours, stay as they are when you choose a
  preset. A preset changes only how often and how much.
- Starboard uses about 16 MB of memory while it is idle. Read
  [What you need to run Starboard](what-you-need.md#starboard-on-its-own).
- To find out what the rest of your server is doing, read [Find out what each app is using](monitor-apps.md).

## Find out more

- [Find out what each app is using](monitor-apps.md)
- [Activate alerts](activate-alerts.md)
- [What you need to run Starboard](what-you-need.md)
- [What a home server is](../basics/what-is-a-home-server.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
