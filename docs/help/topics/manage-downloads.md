[Help centre](../README.md) · Everyday use · how-to

# Pause, resume and remove downloads

The Downloads page shows the queues of all your apps in one list. From it you can pause and resume all
downloads, remove one download, or ask an app to find a different copy.

## Before you begin

- Your download apps are in Starboard, such as Sonarr and Radarr, and qBittorrent or SABnzbd. Read
  [Add an app](add-an-app.md).
- To pause and resume all downloads, download hours must be on. Read
  [Download only at certain hours](set-download-hours.md).

## Steps

### See what is downloading

1. Go to **Activity**, then **Downloads**, then **Queue**. Each download shows its name, its app, its size, the time left and
   its state, such as **Downloading**, **Waiting** or **Needs attention**.
2. Optional: to see only one state, select its filter, such as **Needs attention**. Select it again to see
   everything.
3. Optional: select **Sort** to change the order. The choices are **Needs you first**, **Time left**, **Name**
   and **Queue order**.
4. Optional: select **Group by app** to see one list for each app.

### Remove a download

1. Select the download's name. A side panel opens with its details and any messages from the app.
2. Select **Remove**. Starboard asks **Remove this download?**
3. Optional: tick **Block this release** so the app never downloads this copy again.
4. Select **Remove download**. The app removes it from the queue and from the download client, with what it has
   downloaded so far.

### Find another copy of a download

Use this when a download is stuck or the wrong one.

1. Select the download's name.
2. Select **Find another**. Starboard asks **Block this release and find another?**
3. Select **Block and search**. The app removes this copy, never downloads it again and searches for another
   now.

### Pause or resume all downloads

The **Download hours** panel on the Downloads page has these buttons while download hours are active.

1. Go to **Activity**, then **Downloads**, then **Queue**.
2. In **Download hours**, select one of these:
   - **Resume downloads now**: starts downloads outside your hours, until the next time they would pause.
   - **Pause downloads until** and a time: stops downloads until your hours start again.
   - **Follow the hours**: goes back to your download hours after you paused or resumed by hand.

## Things to note

- The page updates itself while it is open, every 15 seconds unless you change it. Select **Pause updates**
  to stop that while you read, and select it again to carry on. **Check again** asks the apps straight away.
- How often the page updates is in **Settings**, then **Performance**, under **Downloads page updates**.
- **Open the queue in** and the app's name opens the app's own queue in a new tab, for anything Starboard
  cannot do.
- The speed tiles show each download client's speed. If you added Gluetun, a VPN (virtual private network),
  a tile shows whether it is connected.
- **Finished this week** lists what your apps imported in the last 7 days.
- Pausing all downloads pauses only qBittorrent and SABnzbd. Seeding is left alone.

## If it does not work

- **Needs attention:** open the download and read **Messages from** the app. Then use **Find another**, or
  sort it out in the app's own queue.
- **Not done** and a message: the app refused the action. Check the app is running and try again.
- **Download hours says Off, with no buttons:** activate download hours first. Read
  [Download only at certain hours](set-download-hours.md).
- **The VPN tile says Not connected:** downloads may stop. Check Gluetun in its own app or on the Apps page.

## Find out more

- [Download only at certain hours](set-download-hours.md)
- [Search for and add films, series, music and books](search-and-add.md)
- [Approve or decline requests](approve-requests.md)
- [Make Starboard use less of your server](make-starboard-lighter.md)
