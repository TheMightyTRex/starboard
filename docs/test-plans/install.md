# Test plan: the installer and the set-up wizards

Written 6 November 2026. After the Run first script, the installer (`install.sh`) asks two questions and starts
Starboard. Then a set-up wizard asks the rest: in the browser on a computer with a desktop, or in the terminal on
one without. Both wizards ask the same questions in the same order (design system `WIZARD.md`, section 2), so
each step is tested in both. The systems and their hardware are in [Systems Starboard supports](systems.md); the
Run first script has its own plan, [Test plan: the Run first script](setup.md).

## How to read this plan

- **Systems:** Mint is Linux Mint 22.3, Debian is Debian 13, Ubuntu is Ubuntu Server 26.04 and Pi is Raspberry Pi
  OS (64-bit, Trixie). "All" means all four.
- **Wizard:** B is the browser set-up, T is the terminal set-up, B and T means both, each tested on its own.
- **How:** "Machine" runs in `tools/vm/vm.sh` on a clean copy every time; the browser steps are driven by
  Playwright from outside the machine. "By hand" is done on a real Linux Mint computer, and a real Raspberry Pi
  when one is to hand.
- Each step is also tested with Back, with Help (`?` in the terminal), and with Stop, and at 80 by 24 and a wide
  window in the terminal, and at phone and desktop width in the browser.

## The rules every test checks

These apply to every step on every system, as well as the step's own test.

| ID | Rule | Passes when |
|---|---|---|
| GEN-01 | As little typing as possible | The start is one short command, copied from the README or the help. After that, every question can be answered with Enter alone, and the only things a person must type are their password and details only they know, such as a VPN key |
| GEN-02 | The recommended answer comes first and is chosen already | In every list, in the terminal and in the browser, the recommended answer is at the top, marked "(recommended)" with its reason, and already selected or ticked. Enter (terminal) or Continue (browser) accepts it |
| GEN-03 | The terminal's layout is never broken | Nothing from apt, Docker or another program prints into the frame: their output goes to the log. No line repeats down the window, nothing runs past the edge, the menu stays on the bottom line, and a resize draws the step again whole. Checked at 80 by 24, at 120 by 40 and while the window changes size |
| GEN-04 | A computer with a desktop always goes to the browser | The terminal hands over to the browser set-up, with the setup code filled in, as soon as Starboard answers. The terminal then says the set-up continues in the browser, and how to open it again |
| GEN-05 | Everything else just works | No step asks the person to fix something by hand that the script could do itself after a yes |

## 1. The installer

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| INS-01 | The ready-made image starts | All | Machine | It prints the setup code; the right image for amd64 or arm64 is used |
| INS-02 | Every question answered No | All | Machine | Starboard starts; the first visit goes to set-up; `.env` and `data` are private; no Docker socket; the API refuses without signing in; another host name is refused |
| INS-03 | Home network: Yes | All | Machine | Another computer on the network opens Starboard |
| INS-04 | This computer only | All | Machine | Opens inside the machine, refused from outside |
| INS-05 | Run again with Docker access | All | Machine | The setup code is kept and the Docker socket is added |
| INS-06 | The quiet build | All | Machine | One line that turns, cut to the window; on a failure the line stays, marked, with the last lines of the build |
| INS-07 | ufw active, on the systems that have it | Mint, Ubuntu | Machine | The installer says which port to open, with the exact command; Starboard opens once it is |
| INS-08 | AppArmor active | Mint, Ubuntu, Debian | Machine | Starboard and the apps start with AppArmor on |

## 2. Opening the set-up

| ID | Test | Systems | Wizard | How | Passes when |
|---|---|---|---|---|---|
| WIZ-01 | The set-up page opens with the setup code filled in | Mint, Pi | B | Machine, and by hand | The code from the link is used; it never appears in the page address after it is read |
| WIZ-02 | The setup code typed by hand, from the server's screen | Debian, Ubuntu | B | Machine | Accepted; a wrong code is refused with the help link to find it |
| WIZ-03 | The terminal set-up starts | Debian, Ubuntu, Pi | T | Machine | The first step, with the menu fixed on the bottom line |
| WIZ-04 | Plain mode in the terminal | All | T | Machine | Numbered lines only; nothing redrawn |

## 3. Every step of the set-up

Each row is one step, in the agreed order (DASH-103). The browser and the terminal are each tested.

| ID | Step | Systems | Wizard | How | Passes when |
|---|---|---|---|---|---|
| WIZ-10 | Your password | All | B and T | Machine | A short password is refused with the reason; the password signs in afterwards |
| WIZ-11 | How to start: New install | All | B and T | Machine | The next steps are those for a new install |
| WIZ-12 | How to start: Already installed (keep, or change the settings) | All | B and T | Machine | Keep goes to the summary; Change goes through the steps with the saved answers |
| WIZ-13 | How to start: Restore a backup | All | B and T | Machine | The file is checked, then restored; a wrong file is refused in plain words |
| WIZ-14 | How to start: Move from your apps | All | B and T | Machine | The apps found by the Run first script are listed with their media folders |
| WIZ-20 | Storage: the main disk | All | B and T | Machine | The media folder is made, owned by the user's ID, with the folders each app needs |
| WIZ-21 | Storage: a separate disk | All | B and T | Machine (an extra virtual drive) | The drive is listed by size and serial; the media folder goes on it |
| WIZ-22 | Storage: a pool | Mint, Debian, Ubuntu | B and T | Machine (five virtual drives) | mergerfs, gdisk and snapraid are found or installed on that system; the pool is made at `/mnt/pool` and survives a reboot |
| WIZ-23 | Storage: a pool on a Raspberry Pi | Pi | B and T | Machine (USB drives emulated) | The same as WIZ-22, with arm64 packages |
| WIZ-30 | What you want | All | B and T | Machine | Ticking a kind of media picks its apps; the memory total is shown |
| WIZ-31 | Your apps | All | B and T | Machine | Apps already running are left out; with less memory than recommended, a warning says which apps to leave out |
| WIZ-32 | Your apps on a 2 GB Raspberry Pi | Pi at 2 GB | B and T | Machine | The Small server choices are recommended; Tdarr and Jellystat are not ticked |
| WIZ-33 | Every app chosen has an image for this processor | Pi | B and T | Machine | No app that has no arm64 image can be ticked; the reason is shown beside it |
| WIZ-40 | Your VPN | All | B and T | Machine | The details go in `.env` only, never in the screen, the logs or a feedback report |
| WIZ-41 | Your Usenet provider (only with SABnzbd) | All | B and T | Machine | The Ad note before the providers; browser links open in a new tab; the terminal shows each address in full; the rights notice after them |
| WIZ-50 | Check before anything changes | All | B and T | Machine | Everything chosen is listed; Back changes an answer without losing the others |
| WIZ-51 | Start the apps | All | B and T | Machine | One bar while the images download and start, with a timer; each app answers afterwards |
| WIZ-52 | Start fails (no internet during the download) | All | B and T | Machine | The bar stays marked "did not finish"; Try again, Show the details and Stop below it; Try again works once the network is back |
| WIZ-60 | Connect your apps: keys | All | B and T | Machine | The keys of the apps Starboard started are set by Starboard; the apps show as connected |
| WIZ-61 | Connect your apps: Jellyfin extras and the Live TV folder | All | B and T | Machine | The Live TV folder is made where Jellyfin reads it, with the right owner |
| WIZ-70 | Download hours | All | B and T | Machine | The schedule is saved; outside the hours the download apps are paused |
| WIZ-71 | Alerts | All | B and T | Machine | A test alert arrives at a test address |
| WIZ-72 | Disk health | All | B and T | Machine, and by hand | smartmontools is installed if missing; in a virtual machine (no SMART data) the step says so plainly; on real disks each disk's health shows |
| WIZ-80 | How much Starboard does | All | B and T | Machine | The chosen preset is saved and shown on Settings, Performance |
| WIZ-81 | The summary | All | B and T | Machine | What was set and what was skipped, with where to change each later |

## 4. After the set-up

| ID | Test | Systems | How | Passes when |
|---|---|---|---|---|
| AFT-01 | A restart of the computer | All | Machine | Starboard and every app come back on their own; the pool is mounted before the apps start |
| AFT-02 | `./update.sh --check` | All | Machine | It names the newest release and changes nothing |
| AFT-03 | Update from the release before | All | Machine | The settings are kept and the upgrade notice appears |
| AFT-04 | Go back (`./update.sh --to` the release before) | All | Machine | The release before runs with the settings it had |
| AFT-05 | Remove Starboard | All | Machine | Starboard and its containers are gone; the media folder and the apps' settings are kept, as the help says |
| AFT-06 | Memory and processor at rest, with the apps chosen | All | Machine | Recorded in `docs/TESTING.md`; within the advice in [Systems](systems.md) |

## 5. By hand on Linux Mint

These are tested on the owner's Mint 22.3 computer at each release, because a virtual machine cannot show them.

| ID | Test | Passes when |
|---|---|---|
| MAN-01 | The whole path from the quick start to the summary, in Firefox | Every step works and reads well |
| MAN-02 | The same with the keyboard only | Every control is reached in order, with a visible focus |
| MAN-03 | The same with Orca, the screen reader | Every question, answer, error and progress update is read |
| MAN-04 | Text size at 175% and High contrast | Nothing overlaps or is cut off |
| MAN-05 | A phone on the same network, after the set-up | Starboard opens and is usable |

## Behaviour these tests expect that is not built yet

- **GEN-02:** a check of every list in both wizards that the recommended answer is first and chosen. Most are;
  each needs confirming, and the lists that are not change.
- **GEN-04:** the terminal saying where the set-up continues once the browser opens.
- **INS-07:** the installer naming the port and the ufw command when ufw is active.
- **WIZ-31, WIZ-32:** a warning when the apps chosen need more memory than the computer has.
- **WIZ-33:** leaving out apps that have no image for 64-bit ARM on a Raspberry Pi.
- **WIZ-72:** the plain message when a disk gives no health data, as in a virtual machine.

## What already exists

The 17 checks in `tools/vm/vm.sh` cover INS-01 to INS-05 and AFT-02 on Ubuntu 24.04, Debian 12, Fedora 42 and
64-bit ARM. The terminal set-up's own tests (`tests/test_terminal_setup.py`) cover WIZ-10 to WIZ-81 against a
running Starboard, but not on each system. The browser steps (WIZ in the browser) are new for the machines.
