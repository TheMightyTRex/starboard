# Testing and system use

How Starboard is tested, how to run each test, and what Starboard uses on a server. Lightweight comes first
(README, Design principles), so system use is measured, not guessed, and checked again before each release.

Latest results: 3 November 2026. Security has its own page: [Security: how Starboard protects you, and how it
was tested](SECURITY-AND-TESTS.md).

## What Starboard uses

| | Measured | How |
|---|---|---|
| Memory, idle | 15 to 27 MB | `docker stats` on fresh installs in test VMs (Ubuntu 24.04, Debian 12, Fedora 42, 64-bit ARM). Docker's figure includes some file cache, so it varies between runs. |
| Memory, at its busiest | 37 MB | The example server with 20 apps, while `tools/journeys.sh` opened every page (peak resident memory). |
| Least memory it runs in | 24 MB | The published image under a Docker memory limit, with 20 apps and 45 page and API requests. At 16 MB it is stopped for lack of memory. |
| Processor | 2 seconds | Processor time for the whole journey run, which opens every page. Close to nothing while no page is open. |
| Disk | 117 MB image, about 3 MB of data | `docker image ls`, and `du` of a server's `data` folder. |
| Download | 29 MB (amd64, arm64), 21 MB (arm/v7) | The layer sizes of the published image for each platform. |

For a person choosing a computer, the help centre turns these into advice:
[What you need to run Starboard](help/topics/what-you-need.md).

Settings, Performance shows Starboard's own use on a running server, and what each piece of background work
costs.

## The tests

| Test | Command | Covers | Time |
|---|---|---|---|
| Unit and API tests | `python3 -m unittest discover -s tests` | 117 tests: the server and its API, security findings, backup and restore, moving history from other apps, storage, logs, Install apps, discovery, copying app settings | 25 seconds |
| Browser journeys | `tools/journeys.sh` | 29 checks in a real browser against example data | 2 minutes |
| Install tests in VMs | `tools/vm/vm.sh test <system>` | 17 checks of a fresh install on a clean system | 15 to 60 minutes each |
| Help centre | `python3 tools/check-help.py` | Links, layout and writing rules of `docs/help` | 1 second |
| Security scans | `tools/security-scan.sh` (`--full` adds ZAP's active scan) | Trivy, ZAP, Gitleaks, Bandit, ShellCheck, Hadolint ([Security](SECURITY-AND-TESTS.md)) | 10 minutes, or about an hour with `--full` |
| Private details | `tools/check-private.sh` | Addresses, keys, email addresses and private words in tracked files | 1 second |
| Screenshots | `tools/screenshots.sh` | Retakes the README pictures and fails if a page scrolls sideways | 2 minutes |

### Unit and API tests

Python's own `unittest`, with no packages to install. Apps such as Sonarr, Jellyfin, Plex and Audiobookshelf
are small made-up servers inside the tests, and a Plex database is built from scratch, so nothing real is
needed. By file:

| File | Tests | What it keeps working |
|---|---|---|
| `test_server.py` | 33 | Sign-in, setup, sessions, a new password signing out other browsers, every API route, limits, settings, backup routes, saved reports and the Send feedback key |
| `test_backup_migration.py` | 12 | Settings round trip to a fresh install, old and odd backups, saved copies, the server backup job and its alert, moving the data folder, password reset, watch history from a Plex database and another Jellyfin, history files, running an import twice, Plex audiobooks into Audiobookshelf |
| `test_stack.py` | 9 | Install apps: only known apps, safe folders and VPN values, secrets kept off the page, free ports, VPN apps through Gluetun, old files kept |
| `test_discovery.py` | 9 | Search for new apps, reading keys only from safe containers, finding the newest release, and which upgrade guide questions to ask |
| `test_security.py` | 11 | The findings of the November 2026 security review, and forwarded addresses ([Security](SECURITY-AND-TESTS.md)) |
| `test_gaps.py` | 8 | App checks and history, queue actions, saved copies, server backup files |
| `test_storage.py` | 8 | Storage: types from folder names, pools, the usage scan and when it runs, the daily space log |
| `test_listening.py` | 6 | Listening progress from Jellyfin, Plex and Audiobookshelf |
| `test_logs.py` | 6 | The log: personal details removed, detailed logging that turns itself off, old days removed, Delete |
| `test_jellyfin.py` | 4 | Watch history apply, user defaults, Live TV numbering |
| `test_copyset.py` | 3 | Copying settings between two Sonarrs |
| `test_performance.py` | 3 | Presets and background work that stops when turned off |
| `test_pinned.py` | 3 | App updates for images pinned to a version |
| `test_schedule.py` | 2 | Download hours: pause outside the hours, then resume only what Starboard paused |

### Browser journeys

`tools/journeys.sh` starts the example server (`tools/screenshots/example_server.py`, made-up data only) and
runs `tools/journeys/journeys.mjs` in the Playwright image. It needs Docker. It checks:

- every page script parses;
- adding, changing, testing and removing an app through the page;
- an error shows beside what it belongs to (renaming a category to a name in use), the next try clears it, and
  an error with nothing on the page to belong to is an error toast;
- the Updates button says Check until the first check;
- Send feedback (Snaglist): it appears when activated, the content policy lets its styles in, a report saved
  in Starboard is listed in Settings, General, and it is gone when deactivated;
- after signing in, the `next` address cannot send you to another site;
- names, categories, descriptions and saved reports that look like code are shown as text, and nothing runs;
- the content security policy is on all 26 pages and blocks nothing;
- a saved API key appears in no page or answer;
- no page scrolls sideways at 375 pixels wide;
- no page has a script error.

### Install tests in VMs

`tools/vm/vm.sh` makes throwaway virtual machines with plain QEMU: no root, nothing on the home network. Run
`prepare` once for each system, then `test` as often as needed; each test starts from a clean copy.

```bash
tools/vm/vm.sh prepare ubuntu
tools/vm/vm.sh test ubuntu
```

Systems: `ubuntu` (24.04), `debian` (12), `fedora` (42) and `arm64` (Debian 12 for 64-bit ARM, like Raspberry
Pi OS). `VM_MEMORY=512` sets the memory, for example to match a Raspberry Pi Zero 2 W. The arm64 system needs
the `qemu-system-arm` and `qemu-efi-aarch64` packages. Without hardware speed-up (KVM) the PC systems are about
ten times slower; arm64 is always emulated.

The 17 checks: the installer with every question answered No (starts, first visit goes to set-up, setup code,
`.env` and `data` private, no Docker socket, the API refuses without signing in, another host name is
refused); the installer run again with Docker access (setup code kept, socket mounted); this computer only
(answers inside the VM, refused from outside); `./update.sh --check`; the published image starts and prints
the setup code.

## Latest results

From release 0.10.0 (7 November 2026): unit tests, journeys, and fresh installs on Debian 13, Ubuntu 26.04, Linux Mint 22.3 and the emulated Raspberry Pi OS, through the terminal and the browser. From 0.9.2: install tests on Ubuntu 24.04 and 64-bit ARM, and the Run first script on Ubuntu 24.04. The Run first script on Debian and Fedora is from 0.9.0. Debian, Fedora and ARM at 512 MB are from 0.7.4.

| | Result |
|---|---|
| Unit and API tests | 219 passed |
| Browser journeys | 36 passed |
| Install tests, Ubuntu 24.04 | 17 passed |
| Install tests, Debian 12 | 17 passed |
| Install tests, Fedora 42 | 17 passed |
| Install tests, 64-bit ARM, 1 GB | 17 passed |
| Install tests, 64-bit ARM, 512 MB | 17 passed |
| The Run first script on bare Debian 12, Ubuntu 24.04 and Fedora 42 | 12 passed on each |
| Published ARM images (arm64, arm/v7) under emulation | Start and answer every request |
| Help centre check | 83 articles, 0 problems |
| Security scans | See [Security](SECURITY-AND-TESTS.md#security-review-of-the-set-up-wizards-5-november-2026-090) |

## Test plans for each system

From 6 November 2026, Starboard is built and tested for Linux Mint 22.3 (recommended), Debian 13, Ubuntu Server
26.04 and Raspberry Pi OS (64-bit), or later versions of each. [Systems Starboard supports](test-plans/systems.md)
gives the minimum and recommended hardware for each. Every step of the start is tested on each, in
[Test plan: the Run first script](test-plans/setup.md) and
[Test plan: the installer and the set-up wizards](test-plans/install.md).

## Not tested by machine

Left for people: real apps and a real Plex, Windows and Mac, a physical Raspberry Pi, keyboard-only and screen
reader passes, and how pages look and read. Send feedback (Settings, General, Testing) records
problems found while testing by hand, as GitHub issues or saved in Starboard.
