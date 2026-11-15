[Help centre](../README.md) · When something is wrong · troubleshooting
<!-- help: fix / apps -->

# An app shows as not responding

When Starboard cannot reach one of your apps, its card says **Not responding**. Either the app has stopped, or
Starboard has the wrong address or API key for it. Find what the app's details say on the chart, then follow its
numbered answer.

```flow
title: Find your answer
start: An app's card says Not responding
step: Open the app's details | Select its name on Apps
q: What do the details say?
  Cannot reach the app -> q2
  Refused the API key -> 3
  Answered with an error -> 4
q2: Does the app open in your browser?
  No -> 1
  Yes -> 2
1: Start the app again #start-the-app-again
2: Check the address Starboard uses #check-the-address-starboard-uses
3: Copy the API key again #copy-the-api-key-again
4: Read the app's own messages #read-the-apps-own-messages
```

## Find what went wrong

On **Apps**, select the app's name on its card to open its details. They say what went wrong, such as "Cannot reach
Jellyfin" or "Jellyfin refused the API key".

## Start the app again

Open the app itself in your browser. If it does not open, the app has stopped. Start it again, then select
**Check again** in the app's details.

## Check the address Starboard uses

1. If the app opens in your browser, select **Edit app** in its details. The app's **Edit** panel opens in
   **Manage apps**.
2. Check **Address Starboard uses**. Starboard uses your server's own network, so an app on the same server
   is at `http://127.0.0.1` and the app's port, such as `http://127.0.0.1:8096` for Jellyfin.
3. Select **Test connection**. Starboard shows **Connected** and how quickly the app answered, or
   **Cannot connect** and the reason.
4. When the test says **Connected**, select **Save app**. For Sonarr, Radarr, Lidarr and Readarr, from an existing
   set-up, select **Save and continue**, then **Save adding options**.

## Copy the API key again

1. Select **Edit app** in the app's details.
2. Check **API key**: copy it again from the app and paste it in. Read
   [Find an app's API key](find-an-api-key.md#where-each-app-keeps-its-key).
3. Select **Test connection**, and when it says **Connected**, select **Save app**.

## Read the app's own messages

When the details say the app **answered with error** and a number, the app is running but had a problem. Open the
app and read its own messages.

## Things to note

- **Address Starboard uses** can differ from the address you open in your browser. The one for your browser
  is **Address to open in your browser**.
- A Docker container name, such as `http://sonarr:8989`, only works between containers that share a Docker
  network. Starboard does not join one, so use `127.0.0.1` and the port the app publishes.
- The port is the one the app publishes on the server, which is not always the app's usual port. This
  command, run on the server, lists each container and its ports. The port is the number before `->`:

  ```bash
  docker ps
  ```

- An app on another computer uses that computer's address, such as `http://192.168.1.21:8989`.
- A background service with no address can follow another app's status instead. Read
  [Add a background service](add-a-background-service.md).

## If it does not work

- **"Cannot reach" the app:** the address or port is wrong, or the app is not running. Check both again.
- **"refused the API key":** the key is wrong or was changed in the app. Copy it again.
- **"answered with error" and a number:** the app is running but had a problem. Open the app and read its
  own messages.
- If none of this helps, activate detailed logging and report the problem. Read
  [Report a problem](read-the-log.md#report-a-problem).

## Find out more

- [Change or remove an app](change-or-remove-an-app.md)
- [Find an app's API key](find-an-api-key.md)
- [Addresses and ports](../basics/addresses-and-ports.md)
- [What Docker is](../basics/what-is-docker.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
