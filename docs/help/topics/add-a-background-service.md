[Help centre](../README.md) · Apps · how-to

# Add a background service

A background service has no web page of its own, such as a VPN (virtual private network), an unpacker or a
clean-up job. Add one so that Starboard shows whether it is running. It is listed on **System**, **Apps**,
**Other services**, not on the Apps page.

## Before you begin

- The service is installed. If it has a status address, such as Gluetun's, have its address and port to hand.
  Read [Addresses and ports](../basics/addresses-and-ports.md) if these are new to you.

## Steps

1. Go to **System**, then **Apps**, then **Other services**.
2. Select **Add a service**. **Manage apps** opens a side panel called **Add a background service**, with
   **Background service** already active.
3. In **Kind of app**, choose the service if it is in the list, such as **Gluetun (VPN)**. Otherwise, leave
   **Other app**.
4. In **Name**, enter a name, such as `VPN`.
5. In **Address Starboard uses**, enter its address if it has one, such as `http://127.0.0.1:8000`. Leave it
   empty if it has none.
6. If it has no address, choose an app in **Status follows**. Starboard then shows that app's status for the
   service, such as qBittorrent for a VPN that qBittorrent runs through.
7. Select **Add app**.

## Things to note

- You can also start from **Settings**, **Apps**, **Manage apps**: select **Add an app**, then activate
  **Background service**. To make an existing app a background service, activate it in the app's **Edit** panel.
- **Manage apps** lists background services under **Other services**.
- **Other services** has **Check again**, which checks every service now.

## Find out more

- [Add an app](add-an-app.md)
- [Change or remove an app](change-or-remove-an-app.md)
- [Find out what each app is using](monitor-apps.md)
- [The apps Starboard works with](../basics/the-apps.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
