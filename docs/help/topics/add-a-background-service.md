[Help centre](../README.md) · Apps · how-to

# Add a background service

A background service is something with no web page of its own, such as a VPN (virtual private network), an
unpacker or a clean-up job. Add one so Starboard shows whether it is running. It is listed under **Apps**,
**Other services**, not on the Apps page.

## Before you begin

- The service is installed. If it has a status address, such as Gluetun's, have its address and port to hand.
  Read [Addresses and ports](../basics/addresses-and-ports.md) if these are new to you.

## Steps

1. Go to **Apps**, then **Other services**.
2. Select **Add a service**. Starboard opens **Manage apps** with a side panel called **Add a background
   service**. The **Background service** switch is already on.
3. In **Kind of app**, choose the service if it is in the list, such as **Gluetun (VPN)**. Otherwise leave it
   as **Other app**.
4. In **Name**, type a name, such as `VPN`.
5. In **Address Starboard uses**, type its address if it has one, such as `http://127.0.0.1:8000`. Leave it
   empty if it has none.
6. If it has no address, choose an app in **Status follows**. Starboard then shows that app's status for the
   service, such as qBittorrent for a VPN that qBittorrent runs through.
7. Select **Add app**.

## Things to note

- You can also start from **Settings**, **Manage apps**, **Add an app**, then activate **Background service**.
- To make an existing app a background service, activate **Background service** in its **Edit** panel.
- In **Manage apps**, background services are listed under **Other services**.
- **Apps**, **Other services** has **Check again** to check every service now.

## Find out more

- [Add an app](add-an-app.md)
- [Change or remove an app](change-or-remove-an-app.md)
- [Find out what each app is using](monitor-apps.md)
- [The apps Starboard works with](../basics/the-apps.md)
