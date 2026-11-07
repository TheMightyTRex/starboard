[Help centre](../README.md) · Apps · how-to

# Search for apps already on your server

**Search for new apps** looks for apps running on the same computer as Starboard and adds the ones you tick.
It saves you typing each address by hand, and with Docker access it can fill in API keys too.

## Before you begin

- The apps are running on the same computer as Starboard. Apps on other computers are not found: add those
  with [Add an app](add-an-app.md).
- Optional: Docker access lets Starboard find apps on unusual ports and read their API keys. Read
  [Change what Starboard can access](change-what-starboard-can-access.md).

## Steps

1. Go to **Settings**, then **Apps**, then **Manage apps**.
2. Select **Search for new apps**. A side panel opens and Starboard looks for apps. This takes a few seconds.
3. Read the list. Each app shows its address and whether it needs an API key. Every app is ticked to start
   with.
4. Untick any app you do not want on your dashboard.
5. If **Fill in API keys for me** is shown, leave it ticked to have Starboard read each key from the app's own
   settings file.
6. Select **Add the ticked apps**. Starboard adds them to **Manage apps** and closes the panel.
7. If Starboard says some apps still need their API keys, select **Edit** for each one and paste its key.
   Read [Find an app's API key](find-an-api-key.md).

## Things to note

- Starboard looks only when you select **Search for new apps**. Nothing runs in the background.
- It tries the usual port of each app it knows, such as 8989 for Sonarr. With Docker access it also tries every
  port a container makes available.
- Apps already in **Manage apps** are left out. If everything is there, Starboard shows **Nothing new found**.
- **Fill in API keys for me** works for Sonarr, Radarr, Lidarr, Readarr, Prowlarr, SABnzbd and Seerr. The keys
  stay on the server.
- Apps are saved with `127.0.0.1` and their port. They still open from a phone, because Starboard swaps in the
  address you opened Starboard with.
- Each app is put in a category for you. Read [Organise apps into categories](organise-categories.md) to move
  it.

## If it does not work

- **An app is missing from the list:** it may run on a port Starboard does not expect. Add it with
  [Add an app](add-an-app.md), or give Starboard Docker access and search again.
- **Could not look:** Starboard could not finish the search. Reload the page and try again. If it happens again,
  read [Read the log and report a problem](read-the-log.md).

## Find out more

- [Add an app](add-an-app.md)
- [Change or remove an app](change-or-remove-an-app.md)
- [Set up your dashboard after installing](../guides/set-up-your-dashboard.md)
- [What Docker is](../basics/what-is-docker.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
