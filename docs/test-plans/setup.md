# Test plan: the Run first script

Written 6 November 2026. The Run first script (`run-first.sh`) takes a computer with only Linux on it to a running
Starboard: it checks what is there, installs what is missing after a yes, downloads Starboard and starts the
installer. This plan tests every step on each supported system. The systems and their hardware are in
[Systems Starboard supports](systems.md); the installer and set-up wizards have their own plan,
[Test plan: the installer and the set-up wizards](install.md).

## How to read this plan

- **Systems:** Mint is Linux Mint 22.3, Debian is Debian 13, Ubuntu is Ubuntu Server 26.04 and Pi is Raspberry Pi
  OS (64-bit, Trixie). "All" means all four.
- **How:** "Machine" runs in `tools/vm/vm.sh` on a clean copy of the system every time. "By hand" is done on a real
  computer: Linux Mint on the owner's PC, and a real Raspberry Pi when one is to hand.
- **Passes when** says what has to be true. Anything else is a fail, recorded with the system, the step and the
  window size.
- Each test runs at the system's minimum memory from [Systems](systems.md), and the whole plan once more at the
  recommended memory.

## The rules every test checks

These apply to every step on every system, as well as the step's own test.

| ID | Rule | Passes when |
|---|---|---|
| GEN-01 | As little typing as possible | The start is one short command, copied from the README or the help. After that, every question can be answered with Enter alone, and the only things a person must type are their password and details only they know, such as a VPN key |
| GEN-02 | The recommended answer comes first and is chosen already | In every list, in the terminal and in the browser, the recommended answer is at the top, marked "(recommended)" with its reason, and already selected or ticked. Enter (terminal) or Continue (browser) accepts it |
| GEN-03 | The terminal's layout is never broken | Nothing from apt, Docker or another program prints into the frame: their output goes to the log. No line repeats down the window, nothing runs past the edge, the menu stays on the bottom line, and a resize draws the step again whole. Checked at 80 by 24, at 120 by 40 and while the window changes size |
| GEN-04 | A computer with a desktop always goes to the browser | The terminal hands over to the browser set-up, with the setup code filled in, as soon as Starboard answers. The terminal then says the set-up continues in the browser, and how to open it again |
| GEN-05 | Everything else just works | No step asks the person to fix something by hand that the script could do itself after a yes |

## 1. Getting the script

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| SET-01 | The quick start with curl, copied from the README | All | Machine | The script starts and the welcome appears |
| SET-02 | The quick start with wget, on a system with no curl | Mint, Debian | Machine | The same as SET-01 |
| SET-03 | curl installed only as a snap | Ubuntu | Machine | The script installs Ubuntu's usual curl beside it, and Docker's installer downloads |
| SET-04 | A typing mistake in the address (wrong case after the repository name) | All | Machine | curl and wget stop with a 404; the help topic's words for a 404 match what the person sees |

## 2. The welcome and the look

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| SET-10 | The welcome, the logo and the first question (accessible mode) | All | Machine | The welcome fits 80 by 24 and a wider window, centred, with nothing cut |
| SET-11 | Accessible mode chosen | All | Machine | Plain lines only, no boxes or redraws, and plain mode passed on to the installer |
| SET-12 | The window resized during a step | All | Machine | The step is drawn again at the new size, words whole |
| SET-13 | A screen reader | Mint | By hand | Orca reads each question and answer in order, with nothing read twice |

## 3. The checks

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| SET-20 | Check only (`--check`) on a bare system | All | Machine | It lists exactly what is missing for that system (for example git on Debian) and changes nothing |
| SET-21 | The system and version are named | All | Machine | The name from `/etc/os-release` is shown; Pi OS is recognised as Raspberry Pi OS |
| SET-22 | A version older than supported (Debian 12, Ubuntu 24.04) | Debian, Ubuntu | Machine | A note says the version is not tested; the script carries on |
| SET-23 | A newer version than listed (Debian testing) | Debian | Machine | No warning; the script works as on Debian 13 |
| SET-24 | 32-bit Raspberry Pi OS | Pi | By hand | A clear message that only 64-bit is supported, with the help link; nothing installed |
| SET-25 | Not enough free disk space (under 10 GB) | Debian | Machine | The script says how much is needed and stops before installing |
| SET-26 | Not enough memory for the recommended apps | Pi at 2 GB | Machine | The check says so and the installer later recommends fewer apps |

## 4. Installing what is missing

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| SET-30 | curl, git and python3 installed when missing | All | Machine | Each one is there afterwards, with one progress bar each |
| SET-31 | Docker and Docker Compose, by Mint's packages | Mint | Machine | `docker.io` and `docker-compose-v2` from Mint's sources; `docker compose version` works |
| SET-32 | Docker and Docker Compose, by Docker's install script | Debian, Ubuntu, Pi | Machine | Docker's own packages for that release (trixie or resolute) and arm64 on the Pi; `docker compose version` works |
| SET-33 | Docker started and started again after a restart | All | Machine | `systemctl is-enabled docker` and active after a reboot |
| SET-34 | Your user allowed to use Docker | All | Machine | The user is in the docker group, and the installer runs within it without signing out |
| SET-35 | No sudo (Debian installed with a root password) | Debian | Machine | The script explains in plain words how to get sudo (`su -`, `usermod -aG sudo`), then stops; nothing half installed |
| SET-36 | A wrong sudo password, then the right one | All | Machine | It asks again; three wrong ones stop it with a clear message |
| SET-37 | The package manager is busy (automatic updates on first start) | Ubuntu, Pi, Mint | Machine | The step says another program is installing updates; Try again works once they finish |
| SET-38 | No internet | All | Machine | The step fails with the plain-words reason, Try again works once the network is back |
| SET-39 | A step fails (a package source down) | All | Machine | The bar stays marked "did not finish"; Try again, Show the details and Stop below it; the details are readable |

## 5. Starboard itself

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| SET-40 | Starboard downloaded | All | Machine | The folder is made in the home folder, owned by the user |
| SET-41 | Starboard already there | All | Machine | The script offers Update, Keep, or Change the settings, as in "How do you want to start?" |
| SET-42 | Apps already running (Sonarr, Radarr, Jellyfin in Docker) | All | Machine | They are found and passed on, so Move from your apps is recommended |
| SET-43 | The installer starts with the answers so far | All | Machine | Plain mode and the findings reach the installer |

## 6. Finishing

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| SET-50 | A computer with a desktop | Mint | Machine (virtual screen), and by hand | The browser opens the set-up page with the setup code filled in |
| SET-51 | Raspberry Pi OS with a desktop | Pi | By hand | The same as SET-50, in Chromium |
| SET-52 | A computer with no desktop | Debian, Ubuntu, Pi Lite | Machine | The terminal set-up starts, and the address to use from another device is shown |
| SET-53 | Run again once everything is there | All | Machine | Nothing to install; it starts the installer again and Starboard still answers |
| SET-54 | Starboard answers after a restart | All | Machine | `/healthz` answers after a reboot |

## 7. Speed and memory

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| SET-60 | Time from the quick start to the set-up page | All | Machine | Recorded for each system; no step goes quiet for more than a minute without its timer moving |
| SET-61 | At the minimum memory | All | Machine | The whole script finishes; nothing stopped for lack of memory |

## Behaviour these tests expect that is not built yet

The script does most of this today. These tests describe behaviour still to build, and fail until it is:

- **SET-22, SET-23:** a note for a version older than supported. Today the script does not compare versions.
- **SET-24:** a clear stop on 32-bit Raspberry Pi OS. Today it carries on.
- **SET-25:** stopping before installing when the disk has under 10 GB free. Today it shows the free space only.
- **SET-26:** advice for 2 GB of memory. Today the note appears only under 1 GB.
- **SET-35:** the exact steps to get sudo on Debian. Today it says the user is not allowed to install software.
- **SET-41:** Update, Keep, or Change the settings when Starboard is already there. Today it updates the download
  and starts the installer.

## What already exists

FIRST-01 to FIRST-03 in `tools/vm/vm.sh` cover SET-20, SET-30 to SET-34, SET-40, SET-52 and SET-53 on Debian 12,
Ubuntu 24.04 and Fedora 42 (12 checks). The new systems in [Systems](systems.md) carry them over; the other tests
are new.
