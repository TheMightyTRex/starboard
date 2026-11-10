[Help centre](../README.md) · Everyday use · how-to

# Pause, resume and remove downloads

**Activity**, then **Downloads** shows the queues of all your apps in one list. From it you can pause and resume
all downloads, remove one download, or ask an app to find a different copy.

## Before you begin

- Reelix, or apps such as Sonarr, Radarr and qBittorrent, are in Starboard with their API keys. Read
  [Add an app](add-an-app.md).
- To pause and resume all downloads, download hours must be active. Read
  [Download only at certain hours](set-download-hours.md).

## Steps

### Check what is downloading

1. Go to **Activity**, then **Downloads**, then **Queue**. Each download shows its name, its app, its size, the
   time left and its state, such as **Downloading**, **Waiting** or **Needs attention**.
2. Optional: to show only one state, select its filter, such as **Needs attention**. Select it again to show
   everything.
3. Optional: select **Sort** to change the order: **Needs you first**, **Time left**, **Name** or **Queue order**.
4. Optional: select **Group by app** to show one list for each app.

### Remove a download

1. Select the download's name. A side panel opens with its details and any messages from the app.
2. Select **Remove**. Starboard asks **Remove this download?**
3. Optional: tick **Block this release** so the app never downloads this copy again.
4. Select **Remove download**. The app removes it from the queue and from the download app, with what it has
   downloaded so far.

### Find another copy of a download

Use this when a download is stuck or the wrong one.

1. Select the download's name.
2. Select **Find another**. Starboard asks **Block this release and find another?**
3. Select **Block and search**. The app removes this copy, never downloads it again and searches for another
   now.

### Fix a Reelix download that will not import

A Reelix download can finish but not move into your library. It then shows **Needs attention** or **Failed**.

1. Select the download's name and read the messages from Reelix.
2. Select **Try the import again**, then **Try again**. Reelix looks at the finished files again.
3. Or select **Ignore**, then **Ignore** again. Reelix stops warning about it and leaves the files in the
   download app's folder. Nothing is deleted.

### Pause or resume all downloads

While download hours are active, the **Download hours** panel on the Queue page has these buttons:

- **Resume downloads now**: starts downloads outside your hours, until the next time they would pause.
- **Pause downloads until** and a time: stops downloads until your hours start again.
- **Follow the hours**: goes back to your hours after you paused or resumed by hand.

### Download from a YouTube or Spotify link

This needs the full version of Reelix. Read [Switch between the two versions of Reelix](switch-reelix-version.md).

1. Go to **Activity**, then **Downloads**, then **From a link**.
2. In **Link**, paste a link from youtube.com, youtu.be or open.spotify.com.
3. In **What to keep**, choose **Sound only (music, podcasts)** or **Video**.
4. Optional: select **See what it holds** to list what the link has.
5. Select **Download**. If Starboard asks, enter Reelix's admin password.

**Downloads from links** lists each one, newest first, with **Cancel** or **Try again**.

## Things to note

- The page updates itself while it is open. Select **Pause updates** to stop that while you read, and select it
  again to carry on. **Check again** asks the apps straight away. To change how often it updates, go to
  **Settings**, then **Performance**, activate **Advanced settings**, and change **Downloads page updates**.
- **Open the queue in** and the app's name opens the app's own queue in a new tab, for anything Starboard
  cannot do.
- The tiles show each download app's speed. With a VPN (Gluetun), a tile shows whether it is connected.
- **Finished this week** on the Queue page lists what your apps imported in the last 7 days.
  **Recently finished** in the menu does not list anything yet.
- Pausing all downloads pauses qBittorrent, NZBGet, SABnzbd and Soulseek. Seeding is left alone.

## If it does not work

- **Needs attention:** open the download and read **Messages from** the app. Then use **Find another**, or
  sort it out in the app's own queue.
- **Not done** and a message: the app refused the action. Check the app is running and try again.
- **Download hours says Off, with no buttons:** activate download hours first. Read
  [Download only at certain hours](set-download-hours.md#steps).
- **The VPN tile says Not connected:** downloads may stop. Check Gluetun on the **Apps** page.
- **This needs the full version of Reelix** on From a link: switch to the full version in **Settings**, then
  **Apps**, then **Your install**.

## Find out more

- [Download only at certain hours](set-download-hours.md)
- [Find and get what is missing](get-what-is-missing.md)
- [Approve or decline requests](approve-requests.md)
- [Make Starboard use less of your server](make-starboard-lighter.md#while-a-page-is-open)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
