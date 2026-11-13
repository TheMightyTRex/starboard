# Systems Starboard supports, and the hardware each needs

Written 6 November 2026. These are the systems Starboard is built and tested for. Each version named here, or any
later one, is supported. The two test plans test every step on each of them:

- [Test plan: the Run first script](setup.md)
- [Test plan: the installer and the set-up wizards](install.md)

## The four systems

| System | Oldest supported | Based on | Recommended for | How it is tested |
|---|---|---|---|---|
| **Linux Mint (recommended)** | 22.3 "Zena" | Ubuntu 24.04 | A computer with a screen, where you also use the desktop: the browser set-up opens by itself | A Mint virtual machine, and a real Mint 22.3 computer by hand |
| Debian | 13 "Trixie" | Itself | A computer with no screen (a server), on older or smaller hardware | Debian 13 virtual machines, PC and 64-bit ARM |
| Ubuntu Server | 26.04 LTS "Resolute Raccoon" | Debian | A server, when you want Ubuntu's 5 years of updates | Ubuntu 26.04 virtual machines |
| Raspberry Pi OS (64-bit) | The Trixie release | Debian 13, 64-bit ARM | A Raspberry Pi 4 or 5 | An emulated Raspberry Pi OS on Debian 13 for 64-bit ARM, and a real Raspberry Pi by hand when one is to hand |

"Or later" means the next releases of each, such as Debian 14, Ubuntu 26.10 and Linux Mint 23, as soon as they are
out. Starboard checks the version when it starts: on an older version it says that version is not tested, and
carries on.

Fedora, Ubuntu 24.04 and Debian 12 still work, because the scripts know them, but they are no longer tested at
each release. Ubuntu 24.04 is still tested indirectly, because Linux Mint 22.3 is built on it.

## Minimum and recommended hardware

The figures are for a whole media server: Starboard and Reelix Lite (49 MB together at rest with a small library;
the full Reelix read 350 to 380 MB while working on a large library on 13 November 2026), Jellyfin (150 to 300 MB
with a small library, 590 to 920 MB with a large one), Audiobookshelf, a download app and the operating system. Starboard on its own runs in
512 MB.

| System | Minimum | Recommended |
|---|---|---|
| **Linux Mint 22.3** | 64-bit processor with 2 cores, 4 GB of memory, 40 GB for the system | 4 cores, 8 GB of memory, an SSD of 120 GB or more for the system, and a separate drive for media |
| Debian 13 (no desktop) | 64-bit processor with 2 cores, 2 GB of memory, 20 GB for the system | 4 cores, 4 GB of memory or more, an SSD of 64 GB or more, and a separate drive for media |
| Ubuntu Server 26.04 | 64-bit processor with 2 cores, 3 GB of memory, 20 GB for the system | 4 cores, 8 GB of memory, an SSD of 64 GB or more, and a separate drive for media |
| Raspberry Pi OS (64-bit) | Raspberry Pi 4 with 4 GB of memory, a 32 GB card, and a USB drive for media | Raspberry Pi 5 with 8 GB of memory, starting from a USB or NVMe SSD rather than a memory card |

Why these figures:

- **Linux Mint:** Mint needs 2 GB and recommends 4 GB for its desktop; the media server adds about 1 GB. 8 GB
  leaves room for a browser on the same computer.
- **Debian:** with no desktop, Debian itself uses about 300 MB, so 2 GB holds the whole server. Debian's
  installer now needs at least 512 MB.
- **Ubuntu Server:** Ubuntu asks for 1.5 GB for the server itself and suggests 3 GB for real use.
- **Raspberry Pi:** a Raspberry Pi 3 or Zero 2 W has 1 GB or less, which runs Starboard but not Jellyfin
  turning videos into another format. Apps' databases wear out memory cards, so a Pi that runs every day should
  start from an SSD. Only the 64-bit system is supported, because many apps no longer publish 32-bit images.
- **Every system:** turning video into another format (transcoding) needs a processor with video support (Intel
  Quick Sync on most Intel processors from 2015 on) or several fast cores. Without it, play files in a format the
  device can play directly.

## What differs between the systems

These differences are what the tests look at most closely.

| | Linux Mint 22.3 | Debian 13 | Ubuntu Server 26.04 | Raspberry Pi OS |
|---|---|---|---|---|
| Docker comes from | Mint's own packages (`docker.io`, `docker-compose-v2`) | Docker's install script | Docker's install script | Docker's install script |
| curl at first | Check: present on Mint, missing on Ubuntu Desktop | Present on the cloud image; check the netinst | Present | Present |
| git at first | Missing | Missing | Present | Present on the desktop image; check Lite |
| sudo | Your user has it | Missing if a root password was set during install: the script must explain how to get it | Your user has it | Your user has it |
| Desktop | Cinnamon: the browser set-up opens by itself | None (a server) | None | Desktop or Lite |
| Firewall | ufw installed, inactive | None | ufw installed, inactive | None |
| First minutes after starting | Updates may hold the package manager | | Automatic updates hold the package manager for some minutes | Automatic updates hold the package manager for some minutes |
| Drive pool tools (mergerfs, gdisk, snapraid) | Ubuntu's packages: check each is there | Debian's packages: check each is there | Check each is there | Check each is there |

## How each system is made for testing

`tools/vm/vm.sh` gains four systems. Each test starts from a clean copy.

| Name in vm.sh | Made from | Notes |
|---|---|---|
| `mint` | The Linux Mint 22.3 ISO, installed once without questions, then kept as the ready copy | If an unattended install proves unreliable, the fallback is Ubuntu 24.04.3's cloud image with Mint's repository, its `base-files` and `mint-meta-core`, so `/etc/os-release` says Linux Mint. A real Mint computer covers the desktop by hand either way |
| `debian13` | Debian 13's cloud image (genericcloud, amd64) | Also tested with no sudo, to match an install that set a root password |
| `ubuntu2604` | Ubuntu 26.04's cloud image (amd64) | |
| `pios` | Debian 13's cloud image for 64-bit ARM, with Raspberry Pi's apt repository and `raspberrypi-sys-mods` added, and `/etc/rpi-issue` | Run at 4 GB, and once at 2 GB to check the low-memory advice. Always emulated, so about 10 times slower |

For the steps that need a desktop, the test machines run a virtual screen (Xvfb) and a stand-in browser that
records the address it was asked to open. The real desktop is tested by hand on Linux Mint.

## Sources

- Ubuntu 26.04 release notes and requirements: [OMG Ubuntu](https://www.omgubuntu.co.uk/2026/04/ubuntu-2604-system-requriments?noamp=mobile),
  [It's FOSS](https://itsfoss.com/news/ubuntu-26-04-minimum-ram-requirement/),
  [Ubuntu 26.04 release notes](https://ubuntu-release-notes-i18n.readthedocs.io/en/latest/26.04/)
- Linux Mint 22.3: [Linux Mint blog](https://blog.linuxmint.com/?p=4973), [OSTechnix](https://ostechnix.com/linux-mint-22-3-zena-whats-new-upgrade-guide/)
- Debian 13 memory: forum reports on the Trixie installer's memory check; check the Debian installation manual
- Docker on Debian 13 and Ubuntu 26.04: [Linuxize](https://linuxize.com/post/how-to-install-docker-on-debian-13/),
  [ComputingForGeeks](https://computingforgeeks.com/install-docker-ce-on-linux-systems/)
- Docker on Raspberry Pi OS 64-bit: [OneUptime](https://oneuptime.com/blog/post/2026-02-08-how-to-install-docker-on-raspberry-pi-os-64-bit/markdown)
