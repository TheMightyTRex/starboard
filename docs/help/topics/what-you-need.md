[Help centre](../README.md) · Before you install · reference

# What you need to run Starboard

Starboard runs on four Linux systems, each in the version named here or any later one. Starboard itself is very
small, so what your computer needs depends on the media apps you run beside it. The figures below are for a whole
media server: Starboard, Reelix, Jellyfin, Audiobookshelf and a download app.

## The four systems

| System | Best for | Minimum | Recommended | Start here |
|---|---|---|---|---|
| **Linux Mint 22.3 (recommended)** | A computer with a screen: the set-up opens in its browser | 2 cores, 4 GB of memory, 40 GB for the system | 4 cores, 8 GB, an SSD of 120 GB or more | [Start Starboard on Linux Mint](start-on-linux-mint.md) |
| Debian 13 | A server with no screen, or an older or smaller computer | 2 cores, 2 GB, 20 GB | 4 cores, 4 GB or more, an SSD of 64 GB or more | [Start Starboard on Debian](start-on-debian.md) |
| Ubuntu Server 26.04 LTS | A server with no screen, with 5 years of updates | 2 cores, 3 GB, 20 GB | 4 cores, 8 GB, an SSD of 64 GB or more | [Start Starboard on Ubuntu Server](start-on-ubuntu-server.md) |
| Raspberry Pi OS (64-bit), Trixie | A small, quiet server on a Raspberry Pi | Raspberry Pi 4 with 4 GB, a 32 GB card | Raspberry Pi 5 with 8 GB, starting from an SSD | [Start Starboard on Raspberry Pi OS](start-on-raspberry-pi-os.md) |

Every system needs a 64-bit processor. Keep your media on a separate drive of 1 TB or more. To convert video for
phones and browsers, choose an Intel processor from 2018 or later, which has video hardware (Quick Sync).

Downloads:

- Linux Mint: [linuxmint.com](https://linuxmint.com/download.php), the Cinnamon Edition
- Debian: [debian.org](https://www.debian.org/download), the netinst file for 64-bit PC
- Ubuntu Server: [ubuntu.com](https://ubuntu.com/download/server)
- Raspberry Pi OS: [Raspberry Pi Imager](https://www.raspberrypi.com/software/)

## Starboard on its own

These are measured, not estimated. Starboard was tested with 20 apps added and every page opened in a
browser.

| | Starboard needs | Measured |
|---|---|---|
| Memory | 32 MB | 15 to 27 MB when idle, 37 MB at its busiest. It ran without problems when Docker limited it to 24 MB. The compose files cap it at 512 MB, for room to read a large watch history. |
| Processor | Any | 2 seconds of processor time to open every page once. Close to nothing when nobody has it open. |
| Disk space | 150 MB | The image is 117 MB. Settings, logs and history add about 3 MB. |
| Download | 30 MB | 29 MB for 64-bit computers and 64-bit Raspberry Pi systems, 21 MB for 32-bit Raspberry Pi systems. |
| System | One of the four systems above | Tested on clean copies of each, and on 64-bit ARM with 1 GB and with 512 MB of memory. |

Docker itself adds about 60 to 100 MB of memory, and the system needs its own share. So Starboard on its own runs
on a computer with **512 MB of memory**, such as a Raspberry Pi Zero 2 W, but a whole media server needs the
minimum in **The four systems**.

## Which computer for which set-up

The rows below Starboard on its own are guidance for the other apps, not measurements of Starboard. Each app's
own documentation has the final word.

| What you want | Memory | Examples |
|---|---|---|
| Starboard only, watching apps on other computers | 512 MB or more | Raspberry Pi Zero 2 W, Raspberry Pi 3, any old PC |
| Starboard and the apps that find media (Sonarr, Radarr, Prowlarr) with a download app | 2 GB or more | Raspberry Pi 4 or 5 with 2 GB, a small PC |
| All of that, plus Jellyfin playing to one or two people without converting video | 4 GB or more | Raspberry Pi 5 with 4 GB, a small PC |
| A full media server for a household, converting video for phones and browsers | 8 GB or more, and a processor with video hardware | A small PC with an Intel processor from 2018 or later (Quick Sync), or a home server |

A Raspberry Pi is fine for the first three rows. For converting video, a PC with an Intel processor does much
better than a Raspberry Pi.

## Raspberry Pi and other small devices

- **A whole media server** needs a Raspberry Pi 4 with 4 GB of memory or more, and a Raspberry Pi 5 with 8 GB is
  recommended. Read [Start Starboard on Raspberry Pi OS](start-on-raspberry-pi-os.md).
- **A Raspberry Pi 3 or Zero 2 W** runs Starboard on its own, watching apps on other computers. Starboard's
  install was tested on an emulated 64-bit ARM system with 1 GB of memory, like a Pi 3, and with 512 MB, like a
  Zero 2 W.
- **Only 64-bit Raspberry Pi OS is supported.** Docker no longer updates the 32-bit system, and many apps no
  longer publish 32-bit versions.
- The Raspberry Pi 1, 2 and the original Zero and Zero W are not supported.
- Keep media on a USB disk, not the microSD card. Cards wear out quickly with constant writing.
- On a Pi with 1 GB of memory or less, choose the **Small server** preset:
  [Make Starboard use less of your server](make-starboard-lighter.md).

## Things to note

- Windows and Mac are not supported yet: [Can I use Windows or a Mac?](windows-and-mac.md)
- Your media needs its own space. Plan for 1 TB or more for films and series.
- A network cable is more reliable than Wi-Fi for a server.

## Find out more

- [What a home server is](../basics/what-is-a-home-server.md)
- [Install Linux on a computer](install-linux.md)
- [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md)
- [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md)
