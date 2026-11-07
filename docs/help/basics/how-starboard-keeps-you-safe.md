[Help centre](../README.md) · The basics

# How Starboard keeps your server safe

Starboard runs a server that other devices in your home can reach, so it is built to be safe by default. This
page explains what protects you, what Starboard can and cannot do on your computer, and the few choices that are
yours.

## Your password

- Starboard has one password, at least 10 characters long. It is stored only as a hash (PBKDF2-SHA256 with
  600,000 rounds), so the password itself is never kept.
- Choosing the first password needs the one-time setup code the installer prints, so nobody else on your network
  can claim a new server before you.
- Five wrong attempts lock that address out for 15 minutes.
- Without **Remember me**, you are signed out when the browser closes, or after a day.
- Changes that affect the computer itself, such as starting apps, changing your install or erasing a drive, ask
  for the password again.

## Your keys and settings

- API keys stay on the server, in `data/config.json`, which only your user can read. They are never sent to the
  browser.
- Passwords Starboard makes up for your apps (databases, NZBGet, SABnzbd) stay in `data/stack/.env`, which only your
  user can read.
- Starboard never sends your settings anywhere.

## What Starboard can do on your computer

- Starboard runs as your user, in a read-only container with every Linux capability dropped. It never runs as
  root.
- Each kind of access is optional and asked for by the installer: your home network, Docker (for app updates and
  starting apps), each app's memory use, folders for the Storage page, and Disk health. Say no and only that part
  is missing. [What the installer asks](../topics/what-the-installer-asks.md) explains each one.
- Docker access is as powerful as the root account, so it is off unless you say yes.
- **Install apps** starts only the apps on its own list, with folders it has checked (never a system folder or a
  whole home folder). Before the apps start, the Run first window and the installer check the set-up file again
  with the same rules, so a changed file cannot start anything else.
- Drives are changed only by a small helper you install yourself, which accepts a fixed list of actions, checks
  every change first and asks for the last characters of a drive's serial number before erasing it.

## In the browser

- Sign-in cookies cannot be read by scripts and are sent only by Starboard's own pages. Every change also needs
  a header that only Starboard's pages send, from Starboard's own address.
- A strict content security policy: no scripts from anywhere else, and nothing loaded from other sites except
  cover pictures.

## The choices that are yours

- **Who can open Starboard.** Other devices on your home network can open it unless you choose this computer
  only. Read [Choose who can open Starboard](../topics/choose-who-can-open-starboard.md).
- **Away from home.** Never forward Starboard's port straight to the internet. Use a VPN or a reverse proxy with
  HTTPS. Read [Use Starboard away from home safely](../guides/use-starboard-away-from-home.md).
- **Downloads through a VPN.** Every install sends torrents and Usenet through a VPN, Gluetun, so your internet
  provider sees only the VPN.

## How it is tested

Every release is checked with six free security scanners and a review of the code, and the results are
published with the release. Read
[Security: how Starboard protects you, and how it was tested](../../SECURITY-AND-TESTS.md), or report a problem
privately as [SECURITY.md](../../../SECURITY.md) explains.

## Find out more

- [What the installer asks, and what each answer means](../topics/what-the-installer-asks.md)
- [Change what Starboard can access](../topics/change-what-starboard-can-access.md)
- [Change your password](../topics/change-your-password.md)
- [Sign out everywhere](../topics/sign-out-everywhere.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
