[Help centre](../README.md) · The basics

# Addresses and ports

Every device on your home network has an address, and every app on a device has a port. Together they tell your
browser exactly where to go. It is like a block of flats: the address finds the building, and the port is the
number of the flat inside it.

## An address finds the computer

Your router, the box that gives you Wi-Fi, gives each device at home its own address. These are called IP (internet
protocol) addresses, and look like four numbers with dots between them:

```
192.168.1.20
```

Home addresses usually start with `192.168.`, `10.` or `172.`. They only work inside your home. Nobody outside can
use them to reach you.

Your router can give a device a new address from time to time, for example after a power cut. If Starboard's
address stops working one day, check the server's address again. Many routers let you keep the same address for
one device, called a "reserved address" or "static lease" in your router's settings.

## A port finds the app

One computer can run many apps at once. Each app listens on its own numbered port, so the computer knows which app
a request is for. Some examples:

| App | Usual port |
|---|---|
| Starboard | 8095 |
| Reelix | 7700 |
| Jellyfin | 8096 |
| Audiobookshelf | 13378 |

## Putting them together

A full web address names the kind of connection, the computer and the port:

```
http://192.168.1.20:8095
```

- `http://` is the kind of connection. Some addresses use `https://`, which is the same but encrypted.
- `192.168.1.20` is the server.
- `:8095` is the port, so this opens Starboard.

## This computer: localhost and 127.0.0.1

`localhost` and `127.0.0.1` are special addresses that always mean "this computer, the one I am using". On the
server itself, `http://localhost:8095` or `http://127.0.0.1:8095` opens Starboard.

On your phone, the same address would mean the phone, so it does not work there. Other devices need the server's
real address, such as `http://192.168.1.20:8095`.

## Find your server's address

On the server, open a terminal and run this command. It prints the server's addresses:

```bash
hostname -I
```

The first one, such as `192.168.1.20`, is usually the one to use. Read
[Open Starboard from a phone or another computer](../topics/open-from-another-device.md).

## What this means for Starboard

You use addresses and ports twice with Starboard:

- **To open Starboard:** on the server, `http://localhost:8095`; on other devices, the server's address with
  `:8095`.
- **To add your apps:** Starboard runs on the same computer as your apps, so it reaches them at `127.0.0.1` and each
  app's port, for example `http://127.0.0.1:8096` for Jellyfin.

## Find out more

- [Open Starboard from a phone or another computer](../topics/open-from-another-device.md)
- [Add an app](../topics/add-an-app.md)
- [Choose who can open Starboard](../topics/choose-who-can-open-starboard.md)
- [What a home server is](what-is-a-home-server.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
