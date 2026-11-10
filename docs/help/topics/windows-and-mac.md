[Help centre](../README.md) · Before you install · reference

# Can I use Windows or a Mac?

Not for now. Starboard runs on Linux only, and Windows and Mac computers are not tested or supported. You can still
use a Windows or Mac computer to open Starboard in a browser, once it runs on a Linux computer.

## Why Starboard needs Linux

Starboard runs in Docker with a setting called host networking. This lets it reach your other apps and decide who
may connect to it. Host networking works fully only with Docker on Linux. On Windows and Mac, Docker runs inside a
hidden Linux computer of its own, and Starboard cannot work properly through it. Read
[What Docker is](../basics/what-is-docker.md).

## What you can do instead

- **Use a spare computer with Linux.** An old laptop or desktop is often enough. Linux Mint, Debian and Ubuntu
  Server are free. Read [Choose which Linux](install-linux.md#choose-which-linux), then
  [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md).
- **Use a Raspberry Pi.** A small, cheap computer that uses little electricity. Read
  [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md).
- **Keep using Windows or a Mac to open Starboard.** Once Starboard runs on a Linux computer at home, any browser on
  any computer or phone at home can open it. Read
  [Open Starboard from a phone or another computer](open-from-another-device.md).

## Windows with WSL: untested

WSL (Windows Subsystem for Linux) runs Linux inside Windows. Some people may get Starboard working there, but it has
not been tested and is not supported. If you try it, you do so at your own risk.

## Find out more

- [What you need to run Starboard](what-you-need.md)
- [What a home server is](../basics/what-is-a-home-server.md)
- [What Docker is](../basics/what-is-docker.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
