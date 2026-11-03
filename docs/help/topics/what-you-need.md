[Help centre](../README.md) · Before you install · reference

# What you need to run Starboard

Starboard itself is very small: it needs about 30 MB of memory and 120 MB of disk space, so almost any
computer that runs Linux and Docker is big enough. What you need depends more on the other apps you run
beside it.

## Starboard on its own

These are measured, not estimated. Starboard was tested with 20 apps added and every page opened in a
browser.

| | Starboard needs | Measured |
|---|---|---|
| Memory | 32 MB | 15 to 27 MB when idle, 37 MB at its busiest. It ran without problems when Docker limited it to 24 MB. |
| Processor | Any | 2 seconds of processor time to open every page once. Close to nothing when nobody has it open. |
| Disk space | 150 MB | The image is 117 MB. Settings, logs and history add about 3 MB. |
| Download | 30 MB | 29 MB for 64-bit computers and 64-bit Raspberry Pi systems, 21 MB for 32-bit Raspberry Pi systems. |
| System | Linux with Docker | Tested on clean Ubuntu 24.04, Debian 12 and Fedora 42, and on 64-bit ARM with 1 GB and with 512 MB of memory. |

Docker itself adds about 60 to 100 MB of memory, and the system needs its own share. So the smallest
sensible computer for Starboard is one with **512 MB of memory**.

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

- **64-bit Raspberry Pi OS** works on the Raspberry Pi 3, 4, 5 and Zero 2 W. Use it if your Pi can run it.
  Starboard's install was tested on an emulated 64-bit ARM system with 1 GB of memory, like a Pi 3, and with
  512 MB, like a Zero 2 W. Every check passed both times, with the installer and with the ready-made image.
- **32-bit Raspberry Pi OS:** avoid it for a new install. Docker 28 was the last version made for it, so
  Docker gets no more updates there. Starboard's 32-bit image still works on it, for a Raspberry Pi 2 or a
  Pi you cannot reinstall, but it has no white Live TV logos.
- The Raspberry Pi 1 and the original Zero and Zero W are not supported, because Docker does not support
  their processor.
- Keep media on a USB disk, not the microSD card. Cards wear out quickly with constant writing.
- On a Pi with 1 GB of memory or less, choose the **Small server** preset:
  [Make Starboard use less of your server](make-starboard-lighter.md).

## Things to note

- Windows and Mac are not supported yet: [Can I use Windows or a Mac?](windows-and-mac.md)
- Your media needs its own space. Plan for 1 TB or more for films and series.
- A network cable is more reliable than Wi-Fi for a server.

## Find out more

- [What a home server is](../basics/what-is-a-home-server.md)
- [Install Starboard on a Linux computer](../guides/install-on-a-linux-computer.md)
- [Install Starboard on a Raspberry Pi](../guides/install-on-a-raspberry-pi.md)
