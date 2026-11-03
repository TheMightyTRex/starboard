[Help centre](../README.md) · Alerts · how-to

# Turn on alerts

Starboard can send a message to your phone when an app stops answering, a disk has a problem or fills up, a
download is stuck, a backup fails or a certificate runs out. Alerts are off until you turn them on.

## Before you begin

Choose where alerts go. Starboard can send them to one of these:

- **ntfy:** a free phone app that receives messages. Install ntfy on your phone and subscribe to a topic. A
  topic is just a name; choose a long one that nobody could guess.
- **Gotify:** a message server you run yourself. You need its address and an application token from Gotify.
- **A webhook:** any service that accepts a message sent as JSON. Starboard sends a title, a message, a level
  and the source.

## Steps

### Turn on watching

1. Go to **Settings**, then **Alerts**.
2. Under **Watching**, switch on **Watch in the background**. Starboard now checks your apps with no page open.
3. In **How often**, choose how often it checks. **Every 5 minutes** is plenty for a home server.

### Choose where alerts go

1. Under **Where alerts go**, in **Send alerts to**, choose **ntfy**, **Gotify** or **A webhook (JSON)**.
2. In **Address**, type the full address. For ntfy, that is the topic's address, such as
   `https://ntfy.sh/` followed by your topic's name.
3. In **Token**, paste the token if you have one. Gotify needs an application token. For ntfy and webhooks it
   is optional.
4. Select **Save where alerts go**. Starboard shows **Saved where alerts go**.
5. Select **Send a test alert**. Starboard shows **Test alert sent. Check that it arrived.**
6. Check your phone. The test message says that alerts from Starboard reach you there.

### Choose what to alert on

Under **What to alert on**, switch on each alert you want. Each one applies at once.

- **An app stops answering:** after two checks in a row, so a restart does not alert. Another message comes
  when it answers again.
- **A disk reports a problem:** from Disk health, when a drive fails its health check or counts damaged areas.
  Read [Check your disks' health](check-disk-health.md).
- **A folder gets full:** choose **At 80%**, **At 85%**, **At 90%** or **At 95%**, for the folders on System,
  Storage. Read [Check free space and what is using it](check-storage.md).
- **A download needs attention:** when it has needed attention for 30 minutes.
- **The server backup fails:** from System, Backup and restore. Read
  [Back up the whole server](back-up-the-server.md).
- **A certificate runs out soon:** for apps with an outside `https://` address. Choose **7 days before**,
  **14 days before** or **30 days before**. Starboard checks once a day.

## Things to note

- Each alert is sent once, and again only after the problem has cleared and come back.
- Starboard keeps the token on the server and never shows it again. To keep the saved token when you change the
  address, leave **Token** empty.
- Watching also keeps each app's uptime history, shown in the app's details.
- Watching costs very little: about 0.02 seconds of processor per check, and under 1 MB of memory. Read
  [Make Starboard use less of your server](make-starboard-lighter.md).
- Anyone who knows your ntfy topic's name can read its messages, so keep the name long and private.

## If it does not work

- **Not sent** and a message: Starboard could not reach the address. Check the address and token, select
  **Save where alerts go**, then send another test.
- **No alerts arrive, but the test works:** check that **Watch in the background** is on. Then check the
  alert you want is switched on under **What to alert on**.
- **A disk or folder alert never comes:** Disk health or the Storage folders may not be set up. Read
  [Check your disks' health](check-disk-health.md) and [Check free space and what is using it](check-storage.md).

## Find out more

- [Get a weekly summary](weekly-summary.md)
- [Get told when something goes wrong](../guides/get-told-when-something-goes-wrong.md)
- [An app shows as not responding](app-not-responding.md)
