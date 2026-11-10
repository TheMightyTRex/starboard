[Help centre](../README.md) · When something is wrong · troubleshooting

# An app shows as not responding

When Starboard cannot reach one of your apps, its card says **Not responding**. Either the app has stopped, or
Starboard has the wrong address or API key for it. These checks find out which.

## Steps

1. On **Apps**, select the app's name on its card to open its details. They say what went wrong, such as
   "Cannot reach Sonarr" or "Sonarr refused the API key".
2. Open the app itself in your browser. If it does not open, the app has stopped. Start it again, then
   select **Check again** in the app's details.
3. If the app opens in your browser, select **Edit app** in its details. The app's **Edit** panel opens in
   **Manage apps**.
4. Check **Address Starboard uses**. Starboard uses your server's own network, so an app on the same server
   is at `http://127.0.0.1` and the app's port, such as `http://127.0.0.1:8989` for Sonarr.
5. Check **API key**: copy it again from the app and paste it in. Read
   [Find an app's API key](find-an-api-key.md#where-each-app-keeps-its-key).
6. Select **Test connection**. Starboard shows **Connected** and how quickly the app answered, or
   **Cannot connect** and the reason.
7. When the test says **Connected**, select **Save app**. For Sonarr, Radarr, Lidarr and Readarr, select
   **Save and continue**, then **Save adding options**.

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
