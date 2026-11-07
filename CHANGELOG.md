# Changelog

All notable changes to Starboard are listed here, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with dates written as in the TRex Design System.
Version numbers follow [Semantic Versioning](https://semver.org/) loosely: before version 1.0.0, a patch release may also
add features.

## [Unreleased]

## [0.10.0] (7 November 2026)

Reelix in place of the separate media apps, set up for you; Basics, Full install or Everything; NZBGet; and the fixes from testing on four systems.

### Added
- **Reelix in Install apps:** For a new server, Install apps installs Reelix, one app for films, series, books, audiobooks, music and radio, in place of Radarr, Sonarr, Lidarr, Bookshelf, Prowlarr and Seerr. Servers that run those keep them.
- **Reelix set up for you:** After the apps start, Starboard makes Reelix's admin account with your Starboard password, a manager key for itself, the library folders, and qBittorrent with a password of its own, then shows Reelix's queue and calendar on your dashboard.
- **Basics, Full install or Everything:** Both set-ups start by asking which install you want. Basics is Reelix Lite, Jellyfin, Audiobookshelf, subtitles, and qBittorrent and NZBGet through a VPN; Full install adds the full Reelix and more; Everything is every app. An app also brings what it needs.
- **NZBGet:** NZBGet is the Usenet app in every install, lighter than SABnzbd, which Full install and Everything offer instead. Starboard makes up its password, sets its folders and connects it to Reelix, and shows its queue and speed, and pauses it with download hours.
- **Settings, Your install:** Shows what is installed and changes it either way: a bigger or smaller install, NZBGet or SABnzbd, Reelix Lite or full. Your Usenet servers move across from SABnzbd to NZBGet, and the page explains each step.
- **Usenet providers for SABnzbd:** When you choose SABnzbd, both set-ups list some Usenet providers. They are affiliate links, marked Ad, and the step says to download only files you have the right to.
- **Help for moving to Reelix:** A new help page says what moves from Radarr, Sonarr and the others into Reelix, what does not, and what to type in afterwards.
- **Passwords kept when the set-up is written again:** Running Install apps again, or changing your install, keeps the passwords Starboard made up for databases and NZBGet, so they keep working.
- **Help centre on the web.** The help is now web pages, one for each article, with search, a menu of every article, On this page beside each article and the same display settings as the app, at themightytrex.github.io/starboard/help. Help buttons, the set-ups' Help with this step and the terminal's ? help open the article for what you are doing.
- **New help pages.** How Starboard keeps your server safe, What Reelix is, Everything Starboard does, and What the installer asks.
- **Still starting.** For 15 minutes after apps start, the Apps page says they are still starting instead of showing them as not responding.

### Changed
- **One step list for both set-ups:** The browser and terminal set-ups read the same step names and order, and offer the recommended answer first.
- **Install apps explains Reelix:** Start here and the connect guide describe Reelix, a TMDB key and the sites to search, instead of the separate apps.
- **No affiliate note on the VPN step:** The terminal set-up said some VPN providers had affiliate links in the help; none do, so the note is gone.
- **A shorter README.** The README now has the quick start, what Starboard does, the three installs, Reelix, installing and security, each linked to the help centre.
- **Storyarr 0.6.1.** Install apps installs Storyarr 0.6.1 instead of 0.4.8.
- **One password in the browser set-up.** The password you type to write the files is used again to start the apps.

### Fixed
- **A fresh install ended with no apps running:** Without Docker access for Starboard, the apps were written but never started. The installer now starts them, and the browser set-up asks the Run first window to.
- **Only some apps reached the dashboard:** Starboard looked for new apps the moment they started. Both set-ups now keep looking until the list stops growing.
- **Sign out and back in:** On a fresh system the installer's second pass ran outside the new docker group and stopped. It now runs inside it.
- **Keys pressed together:** Over SSH, several key presses could arrive at once and the tick list ignored them. Each key is now read in turn.
- **Text cut at 80 columns:** The installer's explanations, long questions and Docker's messages now wrap at spaces.
- **Jellystat's database:** Starboard changed the owner of the database's folder while it was setting up, so Jellystat could never connect. Database folders are now left alone.
- **A download that broke off:** A broken download stopped every app. The installer tries again twice, and the terminal set-up offers Try again or Carry on without them.
- **Ubuntu 26.04's sudo:** Ubuntu 26.04 shows a star for each letter of the password; the help said nothing shows.
- **qBittorrent 5.1.** Reelix is connected to qBittorrent again: qBittorrent 5.1 answers a right password differently, so the set-up said it was wrong.
- **NZBGet on the dashboard and in Reelix.** NZBGet is found and added to the dashboard, its downloads finish in the media folder, and series go to a tv category Reelix uses.
- **SABnzbd.** SABnzbd works as the Usenet app: its own port 8085 beside qBittorrent behind the VPN, the names Reelix uses, downloads in the media folder, a key Starboard made up, and its newer address for Starboard's checks.
- **Changes without Docker access.** After you run the command Settings, Your install shows, Starboard finishes the change: Reelix, the dashboard and moving your Usenet servers.
- **Ports kept.** Changing your install, or running Install apps again, keeps every app on its port instead of moving it to the next one up.
- **Keys pressed while Run first works.** Pressing Enter while a step runs no longer repeats the progress bar down the window.

### Security
- **Checks:** Tests, browser journeys, the help check and the private details check ran on this release. Reelix gets a manager key, never an admin key, and its one-time set-up token is deleted once used.
- **A password to write the set-up.** Writing the set-up file needs your password, as starting the apps does, because it decides which apps run on the computer.
- **The set-up file is checked before it starts.** The Run first window and ./install.sh --start-apps check the set-up file with Starboard's own rules before starting anything: only the apps Starboard offers, no privileged containers, and folders inside your settings and media folders.
- **One change at a time, and smaller reads.** Writing, starting and changing the install take turns; Docker answers over 64 MB are refused; old copies of the set-up are capped at ten; qBittorrent's temporary password is removed once used; NZBGet's sign-in goes only to the NZBGet Starboard set up.
- **Scans.** The six security scanners ran on this release; two warnings from the signed-in web scan were checked and found to be false alarms.


## [0.9.2] (5 November 2026)

Releases and Restore in Settings, Help that opens the right article, and a calmer terminal.

### Added
- **Releases:** Settings, Updates, Releases shows every version in its own section, newest first. The one you have is
  open; each shows how many changes of each type it has, then what was added, changed and fixed, in colour, and how to
  go back.
- **Restore:** Settings, Updates, Restore puts back a copy of your settings that Starboard saved, or one from a file,
  and shows the command to go back to the version before.
- **Sign out on every Settings page,** beside the page title.

### Changed
- **About and updates is now Update settings,** one of three pages under Settings, Updates.
- **Help opens the right article:** the Help button at the top of each page now opens the help centre article for
  that page, such as Check your disks' health on Disk health, instead of a general part of the help centre.
- **The terminal uses a wide window evenly:** the Run first script and the terminal set-up draw in a column up to 100
  characters wide, centred in a wider window, and move it when the window changes size.
- **Progress bars are drawn once:** each job has one bar, updated in place and cut to the window, so it never repeats
  down the page. When a job fails, its bar stays, marked "did not finish", and the problem and its choices (Try
  again, Show the details, Stop) are below it. Install apps shows a moving bar and the time taken while the apps
  start, in the same way.
- **Choosing several answers in the terminal:** Up and Down move, Space ticks or unticks, Enter carries on. Typing a
  number still works, and plain mode keeps typed numbers.

### Fixed
- **curl installed as a snap:** Docker's installer failed to download ("curl: (23) error on write"), because a snap is
  sandboxed. The Run first script now installs Ubuntu's usual curl beside it and explains the error in plain words;
  Show the details shows more of the log, wrapped, not cut off.
- **The quick start without curl:** Ubuntu Desktop does not include curl, so the README and the help now give the
  same command with `wget`, which Ubuntu, Linux Mint and Debian include.
- **Disk health installs what it needs:** choosing disk health no longer stops with "install smartmontools first":
  the installer installs smartmontools itself (sudo asks for the password), and finds it in /usr/sbin, which is not on
  every user's path.

## [0.9.1] (5 November 2026)

Updating works again after a long gap.

### Fixed
- **Updating after a long gap:** `./update.sh` stopped just after "What changed" when more than 30 changes had come
  since your version. It now lists 30 and says how many more. Until you have this version, Update Starboard in the help
  has the steps to update by hand.
- **Typing the Run first script's command:** the help and README now say that the address is case-sensitive after
  the repository's name, and what a 404 means. The terminal basics page has a new section, Capital letters matter.

### Security
- **Checks:** Trivy, OWASP ZAP (signed out), Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release;
  only update.sh and the help changed since 0.9.0's full checks.

## [0.9.0] (5 November 2026)

The Run first script, one order for both set-ups, and a security review of the set-up.

### Added
- **The Run first script:** once Linux is installed, one command sets up everything else. `run-first.sh` shows a
  welcome wizard with the logo, in the terminal set-up's style (heading box, progress bar, menu, help over the
  step), checks for git, Python, Docker, Docker Compose, Docker running and your user allowed to use Docker,
  installs only what is missing after you say yes, downloads Starboard and starts the installer. With a desktop it
  opens the set-up in your browser with the setup code filled in; with none, it carries on in the terminal.
  Accessible mode is asked first, in plain words, and goes on to the installer (`./install.sh --plain`). `--check`
  only reports. Find out more in **Set up everything with the Run first script**.
- **How to start, in both set-ups:** the browser set-up guide and the terminal set-up now start with the same
  question, New install, Move from apps you already run, or Restore a backup, with the recommended answer chosen from
  what Starboard finds on the computer. Restore takes a backup file and restores it after the password.
- **Storage, in both set-ups:** for a new install, where your media goes: this computer's main disk, a separate disk
  or a pool of several disks, with the media folder made for you when the apps start. Install apps uses the folder
  chosen there.
- **Alerts and disk health, and how much Starboard does, in the terminal set-up,** as in the browser.
- **Keyboard help for commands:** The terminal: typing commands now says where `|`, `~`, `\`, `"`, `@`, `$` and `&` are
  on US, UK and Ireland, German, French and Spanish keyboards, and warns that the `¦` key on a UK keyboard is a
  different character. The Run first script's command also comes in a version without `|`.
- **Connect to the internet from the terminal:** a help topic for a server with no desktop: check it is online,
  connect a network cable (Debian included), or Wi-Fi with NetworkManager or on Ubuntu Server. The guide from a bare
  computer links to it after installing Linux.

### Changed
- **One order for every step,** the same in the browser and the terminal: your password, how to start, storage, your
  apps, VPN, the check, connecting the apps, download hours, alerts and disk health, how much Starboard does. Each
  thing is decided before what depends on it.
- **The installer asks less on a new install:** only your home network and Docker access, and drive pools when there
  is more than one drive. The dashboard's name moves into the set-up, beside the password. Free space for the media
  folder, the Live TV folder and disk health are chosen in the set-up and applied at the end with one installer
  command, which the Run first script runs for you.
- **The Run first script fits the window:** the logo is drawn at the size that fits, or left out in a small window;
  below 60 by 20 it uses plain lines and says why; help shows a page at a time; and a change of window size is drawn
  again at once.
- **It works quietly:** sudo asks for the password once, then a bar with an animation shows each job, and the
  installer builds Starboard quietly too. When something fails, it says what happened in plain words and offers to
  try again, show the details or stop.
- **The installer runs inside the Run first script's frame,** as its step 6, and the browser path ends on a Done page
  with the addresses and the setup code.
- **Text in the terminal wraps at any window size:** paragraphs, questions, answers, cards and warnings wrap between
  words, are wrapped again when the window changes size, and wrap in plain mode too. Long answers put their
  description under the name. In a narrow window the menu leaves out its hint so the keys fit.

### Security
- **What the set-up hands to the installer:** the Run first script passes on only the three options the set-up
  writes (free space for the media folder, the Live TV folder and disk health), each folder checked again, and never
  `/`, a system folder or a top folder such as `/home`.
- **The setup code:** read only from a regular file, never through a link, and only as the characters a code has.
- **Files the scripts write:** the hand-over is written to a new file and moved into place; Docker's installer and
  the logs go in private temporary files, not fixed names in `/tmp`.
- **Host names:** Starboard answers only to this computer's own name, alone or with a home-network ending such as
  `.local`, which stops DNS rebinding against a native install.
- **Disk health:** its report folder belongs to root, and the job never follows a link.
- **The first password:** two requests at the same moment cannot both choose it.
- **Checks:** Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint
  and CodeQL ran on this release, after a security review of every set-up wizard. ZAP's two signed-in warnings
  were false alarms, explained in docs/SECURITY-AND-TESTS.md.

## [0.8.0] (5 November 2026)

Set up in the terminal, drive pools, and feedback with a QR code.

### Added
- **Drive pools** (DASH-87): a new **Pool** tab on System, Storage, and a **Your drives** step in the terminal
  set-up. Add a drive to a mergerfs pool (keeping its files, or erasing and preparing it as ext4), balance the
  files by whole folders, take a drive out (its files move to the others first), and make a drive a backup drive:
  parity with SnapRAID (recommended: one drive protects them all) or a nightly rsync copy, whose deleted files go
  to a dated holding folder. A root helper, installed with sudo by `./install.sh`, does the work; Starboard only
  asks. Every change is checked first (a dry run with the exact commands), needs the password again, and erasing
  needs the end of the drive's serial number. `mergerfs.balance` can be chosen when it is installed, and is not
  installed by default. Diagrams in the help explain balancing and what happens without it. Tested in a
  throwaway VM with blank virtual drives (`tools/vm/vm.sh pool debian`). Find out more in **Add a drive to the pool**.
- **Set up in the terminal, with no browser** (DASH-86): `./install.sh --terminal` carries on once Starboard is
  running and asks the set-up questions in the same terminal: your password (typed hidden, with no setup code
  needed on the server itself), the apps for your media server (what you want, then the apps, folders and VPN
  details) and download hours. Enter takes the recommended answer, `?` shows help, `b` goes back a step with the
  last answers as the defaults, and `q` stops. It uses Starboard's own API, so every answer is checked as the
  browser checks it. Each step starts on a cleared screen with a heading box ("Starboard | step"), a progress bar
  and a menu on the bottom line; help opens as a box over the dimmed step. With `STARBOARD_PLAIN=1`, `--plain`, a
  small window or no terminal, it prints plain lines that never clear or redraw, which suit software that reads
  text aloud; `NO_COLOR` keeps the boxes without colour. Run it again with `python3 -m starboard.terminal_setup`.
  Find out more in **Set up Starboard in the terminal, with no browser**.
- **Feedback from the terminal set-up** (DASH-91): `f` at any question sends Snaglist's report about that step,
  in a box over it: what it is about (Snaglist's seven kinds), one or two of Snaglist's questions, then the whole
  report before any choice to send. It is a pre-filled GitHub issue with the step, Starboard's version, the system,
  the window size and the last error. Answers to the set-up, passwords, VPN details and the setup code are never
  in it, and email and network addresses, user names in paths and anything like a key are replaced. Send it as a
  QR code drawn in the terminal (a new standard-library encoder, `starboard/qr.py`), as the link, or saved to a
  file. Plain mode never draws a QR code. After a failure, `r` reports it with the error filled in.
- **What is new in Reelix:** on **Apps**, **Updates**, **What is new** beside **Update** lists the changes in a
  waiting Reelix update, from Reelix's own changelog, under Added, Changed, Fixed and the other kinds of change.
  After Reelix's version goes up, a notice on the Apps page and on Updates says so, with **What is new** for the
  versions it skipped. The changelog is downloaded only when you open What is new, and kept for 6 hours. Find
  out more in **Update your apps**.
- **A guide from a bare computer:** the help centre's new guide, Get Starboard up and running, goes from
  installing Linux to Docker, then splits into a path for the browser and one for the terminal only. New topics:
  Install Linux on a computer, and Ask an AI assistant to help you set up, with prompts for a chat assistant and
  for one on the server.

### Changed
- **The terminal set-up fits the window:** the heading box, the progress bar and the menu stay in place and only
  the lines between them scroll; the window is measured at every step and when it changes size. The QR code holds
  more of the report the larger the window is: the title in 80 by 24 (with a 2-module edge), a short report in
  80 by 30, the report without its technical details in 140 by 60. The line above the code says what it holds,
  and the whole report is always saved on the server.

### Security
- **The pool helper:** drive pools need a small helper that runs as root, installed only if you say yes in
  `./install.sh`. Starboard can only ask it for a fixed set of jobs, each checked first (a dry run with the exact
  commands), with the password again; erasing a drive needs the end of its serial number.
- **Feedback reports:** a report never holds answers to the set-up, passwords, VPN details or the setup code.
  Answers typed in the open are kept only as keyed fingerprints (HMAC-SHA-256 with a random key for each run), to
  take them out of a report; hidden answers are not kept at all. CodeQL's alerts on this were fixed, and two in
  the screenshot tool (values written into page scripts are now escaped beyond JSON).
- **Checks:** Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint
  and CodeQL ran on this release. One download address is now also checked to be https; ZAP's one signed-in
  warning was a false alarm, explained in docs/SECURITY-AND-TESTS.md.

## [0.7.7] (4 November 2026)

Lighter, from the performance review (DASH-79); each change measured before and after. Measured, not done: the
memory a weekly Live TV build leaves behind (25 MB to 54 MB) comes back once heavy jobs run in their own
short-lived process, the next step of DASH-79.

### Changed

- **Pages open faster:** HTTP/1.1 keep-alive with Nagle off, so a page and its files share one connection, and
  idle connections wait 10 seconds. Pages, scripts and styles link the CSS, scripts, icons and font with the
  linked file's hash, added when served, and those links are kept by the browser for a year. A first visit took
  10.5 ms of server processor and now 4.7 ms; a revisit 10.3 ms and 10 requests, now 1.7 ms and 3 requests.
- **Live TV guides** are downloaded to a temporary file and read as they unpack, and each finished entry is
  dropped: a made-up 147 MB guide peaked at 197 MB, now 36 MB.
- **The image** compiles Starboard's code at build time (start-up about 430 ms to 204 ms), and every
  `__pycache__` is left out of the build.
- **Smaller:** the processor model is read once, the temperature sensors are found every 10 minutes, the upgrade
  summary is kept until it changes, the listener wakes every 5 seconds instead of twice a second, and the health
  check runs every 60 seconds.

### Fixed

- **Live TV guides:** a DOCTYPE line is accepted (entity definitions are still refused), so the Samsung TV Plus
  and Pluto TV guides load again. They had failed every hour, with every stream tested again each time (559
  seconds and 20 seconds of processor an hour); the hourly check now does nothing. A guide that fails waits 12
  hours before the next try.

### Security

- **Error answers:** Python's own error answers (such as 501 for a request method Starboard does not handle)
  carry the same security headers as every other answer, found by OWASP ZAP; with a test.
- **Checks:** Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint
  and CodeQL ran on this release. ZAP's two signed-in warnings were false alarms, explained in
  `docs/SECURITY-AND-TESTS.md`.

## [0.7.6] (4 November 2026)

### Added

- **A new menu, in three levels:** a side menu beside every page has the Screen logo with Starboard underneath,
  Search, then five sections: Library, Discover, Activity, System and Settings. The level 1 menu along the
  top holds a section's pages, and the level 2 menu under it holds a page's own tabs, only when it has them.
  On phones the side menu is hidden and the menu drawer lists the sections with their pages. Every page
  keeps its address.
- **Server name:** a new setting in Settings, General, up to 10 characters, shown in bold at the start of
  the level 1 menu (phones show only the logo). A dashboard name of 10 characters or fewer is copied across
  once. The dashboard name still names the browser tab and alerts.
- **Help for each section:** a Help button beside Display opens that section's help in a new tab. For now each
  one opens the matching part of the help index, while a new help centre is made; the addresses are kept in
  one place, `HELP` in `tools/apply_shell.py`.
- **Places for what Reelix will fill:** the Library (TV, Films, Radio, Books, Audiobooks), Trending,
  Recently finished, Wanted, History and Settings, Reelix have their pages in the menu, saying they come
  with Reelix.

### Changed

- **The help and the app's own text** name the new places, such as **Settings**, then **Apps**, then
  **Jellyfin**. What Starboard is has a new part, Find your way around.

### Removed

- **Shelf** no longer adds its own icon rail, because every design now has the side menu.

### Security

- **Checks:** Trivy, OWASP ZAP (signed out, and an active scan signed in), Gitleaks, Bandit, ShellCheck, Hadolint
  and CodeQL ran on this release. They found nothing to fix; ZAP's two warnings were false alarms, explained in
  `docs/SECURITY-AND-TESTS.md`.

## [0.7.5] (3 November 2026)

### Added

- **Send feedback** (Settings, General, Testing) replaces Note issues. It uses
  [Snaglist](https://github.com/TheMightyTRex/snaglist): report a problem, suggest something or check a page for
  accessibility problems, then open it as an issue on Starboard's GitHub page or save it in Starboard. Saved
  reports, and the older notes, are listed under Testing with Mark fixed, Remove and Download all.

### Changed

- **Errors show where they happened:** a problem saving a setting, renaming a category or running an action
  now shows beside that control, in words, and clears on the next try. An error with nothing on the page to
  belong to is an error toast that stays until you close it (it used to fade like an information toast).
- **Apps, Updates:** the button says Check until the first check, then Check again.
- **Watch history:** a watch history file can now be up to 80 MB (was 512 MB): reading one takes about 4.5 times
  its size, and 80 MB is more than 250,000 films and episodes.

### Removed

- **Note issues:** Send feedback takes its place, and the older notes are listed with the new reports under
  Testing.

### Security

- **Limits:** the compose files and the service for `--native` cap Starboard at 512 MB of memory and 200
  processes, so a fault cannot take the whole server's (Docker Bench for Security, 3 November 2026).
- **CodeQL:** a saved copy's name is length-checked and matched only one way, so it cannot make the check slow;
  a header value with a line break is never sent; certificate checks need TLS 1.2 or newer. Each has a test.
  The other 15 alerts are explained in `docs/SECURITY-AND-TESTS.md` and dismissed with reasons.
- **Send feedback:** its reports are saved only with a key given to a signed-in browser, which stops working
  when that browser signs out. The content policy lets in only Snaglist's own stylesheet.
- **Checks:** Trivy, OWASP ZAP, Gitleaks, Bandit, ShellCheck, Hadolint and CodeQL ran on this release. What each
  found is in `docs/SECURITY-AND-TESTS.md`.

## [0.7.4] (3 November 2026)

### Added

- **Help centre** (`docs/help`): 53 topics, 8 guides and 7 basics articles for people new to home servers, with
  install guides for a Linux computer and a Raspberry Pi, and what you need for each set-up. Help in the footer
  of every page opens it.
- **Reset a forgotten password:** `./reset-password.sh` on the server (or `touch data/reset-password` and a
  restart with the ready-made image) removes the password, signs everyone out and starts with a new setup code.
- **Watch history:** applying it lists the films and episodes not in Jellyfin yet. A history file over 512 MB is
  refused before it uploads.
- **Tests:** backup and migration round trips, browser journeys (`tools/journeys.sh`), install tests in VMs on
  Ubuntu, Debian, Fedora and 64-bit ARM (`tools/vm/vm.sh`), and `docs/TESTING.md` with measured system use.
- **Testing aid:** Note issues (Settings, General) adds the shared Note an issue button to every page.

### Changed

- **Messages:** confirmations are cards in the corner (up to three, with Close); problems use the information
  style. Settings pages show "Saved at" and the time beside Save name, Save where alerts go, Save address and
  Change password. Words follow the shared content guide: settings are activated and deactivated.

### Fixed

- **Watch history:** a second run no longer counts episodes it applied before as missing.
- **Restore:** backups from before 0.6.0 are brought up to date; a design or choice that no longer exists goes
  to the default; an app of a kind Starboard no longer knows becomes a plain link.
- **Disk health:** the page script works again (broken since 0.7.0).
- **Apps on a phone:** the Apps page works at 175% text.
- **Ready-made image:** Docker access works, as it needs the socket's group (`group_add` in `compose.image.yaml`).
- **Address hint:** Manage apps now suggests 127.0.0.1 and the port.

### Security

- **Pillow 13.0.0** (58 known problems in 11.3.0), no pip in the image, logos read only as PNG, JPEG, GIF, WebP,
  BMP or ICO.
- **Sign-in:** the sign-in form posts, so the password never lands in the address.
- **Other sites:** new Cross-Origin-Resource-Policy and Cross-Origin-Opener-Policy headers.
- **Live TV playlists:** stream checks never open a `file:` link from a playlist.
- **Exact addresses:** an address that only starts like one of Starboard's own is now not found.
- **Checks:** `tools/security-scan.sh` runs Trivy, ZAP, Gitleaks, Bandit, ShellCheck and Hadolint; results in
  `docs/SECURITY-AND-TESTS.md`.

## [0.7.3] (2 November 2026)

### Changed

- **App cards:** the reply time sits on the right and takes only its own width, with a gap between the cells. An
  unknown version shows nothing; an app that does not answer shows N/A.

### Fixed

- **Long versions:** long versions such as Prowlarr's 2.7.0.5723 no longer run into the reply time. On a very
  narrow card a version breaks after a dot, never inside a number.

## [0.7.2] (2 November 2026)

### Changed

- **App cards (Health first and Tiles):** every card has the same rows in the same places. The status sits beside
  the name; then what the app is doing ("3 in the queue", "Nobody playing", "Nothing to report", "Cannot reach
  it"); the home address as a link that opens the app (now on phones too); warnings, in a row only when a card in
  that category has one; and along the bottom, under a line, Update available, the version and the reply time
  ("Not known" and "No reply" when the app does not answer). Each card takes its rows from the grid, so cards
  side by side are the same height. The Open button is in the app's details.
- **App logos** are shown on their own, without a tile (shared library); initials keep their tile.

### Fixed

- **Updates for test builds:** an image pinned to a test build such as `v0.4.9-dev.6`, which is not in its
  registry, is now offered the newest release (a test build counts as older than its release).

## [0.7.1] (2 November 2026)

### Changed

- **Updates:** each app has its logo beside its name (no tile, as tall as the name and the line under it);
  Installed and Latest are left-aligned; every category's table has the same column widths, so the
  columns line up down the page; and each row's cells sit on the middle of the row.

### Fixed

- **Long API keys:** keys were cut to 200 characters when saved, so Audiobookshelf (whose keys are about 211
  characters) refused its key. Keys up to 2000 characters are now kept whole. If Audiobookshelf says the key is
  wrong, paste it again in Settings, Manage apps.
- **Log:** a connection that stayed idle until it timed out no longer writes an error to Docker's log.

## [0.7.0] (2 November 2026)

### Added

- **Install apps, for people who have never set up a media server:**
  - **Start here:** what each app does (find, choose, download, sort, watch), how long it takes and what you
    need. **Advanced settings** (a tick, remembered) shows every app in each group, the settings folder, user
    and group numbers, time zone and the files; without it, the guide picks the apps and folders.
  - **Every step is checked**, with the problem shown by its field: at least one thing ticked (and a warning
    when nothing can download), a full media folder path, numbers and time zone in Advanced settings, and the
    VPN.
  - **VPN** is its own step: provider (with a list of common ones), WireGuard or OpenVPN as a segmented choice,
    and only that connection's fields, each saying where to find it. Only those fields are written to .env, and
    they are required.
  - **Pool drive:** "Join several drives into one" opens a pop-up listing the mounted drives (from Disk health's
    drive list, or typed in), and writes the mergerfs commands to run on the server. The pool becomes the media
    folder. Nothing is erased.
  - **Check** sums up every step with a Change link to it; the files are behind a disclosure (open in
    Advanced).
  - **Connect your apps:** after starting, numbered steps with the exact hosts, ports and folders for
    qBittorrent, SABnzbd, Radarr, Sonarr, Lidarr, Bookshelf, Prowlarr, Jellyfin, Seerr and Bazarr (gluetun
    when they go through the VPN).
  - **Storyarr** is offered by default (`ghcr.io/themightytrex/storyarr`, pinned, so Updates offers newer
    versions; `STARBOARD_STORYARR_IMAGE=none` leaves it out), and Install apps writes
    `starboard-before-update/storyarr.sh`, a database backup that runs before each update.
- **Copy app settings (Settings, Manage apps):** from one Sonarr, Radarr or Lidarr into another of the same kind
  and major version: tags, custom formats, quality profiles (format scores matched by name), root folders,
  download clients and remote path mappings, naming and media management. A preview says what will be added,
  what is already there and what will be replaced. Passwords the old app hides are asked for; without them a
  client is added switched off. Indexers: add the new app in Prowlarr.
- **More detail, from the API gaps (DASH-19):**
  - Apps: Check again in a slide-out checks that app only; Recent checks (the last 20, in memory); "Not
    responding for 12 minutes"; the app's own warnings carry its id, when first seen and a How to fix it link.
  - Downloads: Remove (optionally blocking the release) and Find another; the added date; all messages.
  - Coming up: each item's overview and a link to its page in the app; Earlier and Later move a month at a time.
  - Search: In the library links open the item in its app.
  - Storage: the folder path and the disk (or pool members) it is on.
  - Disk health: rpm, the self-test history, every SMART attribute, events with their time and a status icon,
    and Download the full report.
  - Backups: what a saved copy holds, and downloading it (password first); downloading a server backup through
    a one-time link (streamed); earlier runs, what went in and what could not be read, when the server job
    reports them.
  - Settings: About shows when this version started.
- **Upgrade now from Storyarr:** `apps-updates.html?app=storyarr` checks at once and goes to that row.

### Changed

- **Slide-outs:** Display and accessibility is a slide-out; every slide-out header (and the phone menu's) is in
  the page background over a white or dark-surface body (library token `--color-slide-header`).
- **Categories:** renaming or removing a category is one save.
- **Wrong passwords:** a wrong password in a dialog (or Install apps' Start) stays on the page: the server says
  `reason: "password"`.
- **Raspberry Pi:** images for 32-bit Raspberry Pi (linux/arm/v7). Pillow is installed only where a ready-made
  build exists.

## [0.6.0] (2 November 2026)

### Added

- **Listening progress (Settings, Audiobookshelf):** reads where everyone is in each audiobook from a Plex server
  (your own account, from libraries with book in their name or the Audnexus agent), a Jellyfin or Emby server
  (every user, from Books libraries) or another Audiobookshelf (every user). A book in several files becomes one
  position. Match each account to an Audiobookshelf user, then Apply now, or keep applying every hour so books get
  their progress once they are scanned in.
  - **Matching:** ASIN, then ISBN, then title and author (first author, ignoring punctuation and a leading The),
    then the book's folder. A position from a copy of a different length is scaled to fit. Books not found are
    listed, with their account.
  - **Safe by default:** progress a person already has in Audiobookshelf is never changed, and each book is
    written once. The admin key makes a key that acts as one person, ends by itself after 15 minutes, and is
    deleted as soon as that person's progress is written.

### Changed

- **Audiobookshelf app type:** its version on Apps, and an optional API key. Apps named Audiobookshelf move to the
  new type when you upgrade (settings schema 2; a backup is made first). The upgrade guide asks for the key.
- **Install apps:** the Listening progress offer is ready, and points to Settings, Audiobookshelf.

## [0.5.6] (2 November 2026)

From a design consistency review of Starboard and the shared component library (all 23 findings fixed).

### Changed

- **Names:** "Check again" for every refresh (it was also Check now and Check for updates); Storage's job is
  "Sort by type". "Run now" stays for server jobs.
- **Saving:** choices save as soon as they change (the default design no longer needs a button); text fields keep
  a secondary Save; one primary button per page (request rows, Updates rows and settings forms no longer each
  have one).
- **Buttons and dialogs:** compact buttons only in dense tables; Decline and Restore are danger buttons, as their
  dialogs are; every confirm dialog says Cancel; delete uses the bin icon.
- **Logs:** the filter is a segmented control; detailed logging is the same select as in Settings; the wording
  follows whether it is on.
- **Charts:** the pool bar's labels no longer stretch; chart and ring text follow Text size; the second line on
  System charts is dashed to match its legend; media colours come from the library's new series tokens, with a
  high contrast set.
- **Code:** old copies of library rules removed (rows, notices, panel heads, charts, stacks, focus); settings
  helpers moved into the library; Performance's wording fixed ("1 minute", "1 answering a page").

### Fixed

- **Layout:** no focus box on wizard headings; Performance's four presets in one row with their text lined up;
  space in the Jellyfin panel; headings at one level are one size; the guides show their Settings tab as current;
  an odd stat tile spans the row on phones; small legend rows no longer look muted.

## [0.5.5] (2 November 2026)

### Added

- **System, Logs:** what Starboard did (start-up, sign-ins, settings and apps changing, alerts, download hours,
  updates, storage readings, background jobs) and every problem it met, newest first, with Everything,
  Problems and Detailed, a search, Download and Delete logs.
  - Personal details are removed before anything is written, in both modes: passwords, API keys and tokens, IP
    addresses, host and computer names, email addresses, user names in folder paths and the dashboard's name.
- **Settings, General, Logs:** keep logs for 7 days to a year (60 by default); older days are removed once a day,
  with no thread of its own. **Detailed logging** (Off, For 24 hours, Until I turn it off) adds each page request
  and each call to your apps, and the full detail of errors.
- **Report a problem:** turn on detailed logging, do the thing again, then Copy the details (versions, how it
  runs, what is switched on, the kinds of apps, recent entries) and Open a new issue on GitHub, which uses a new
  issue template.

### Changed

- **Docker's own log** now holds only start-up and problems, and both Compose files cap it at 3 files of 1 MB.

### Fixed

- **System, Overview:** the charts' history failed to load since 0.4.0 (found by the new log).

## [0.5.4] (2 November 2026)

### Changed

- **System, Overview:** Jellyfin's status chips sit beside its name, centred on the heading's line, with the
  version on the right. The pattern (`.title-status`) and the status icon after a name (`.status-icon`) are now
  in the shared component library, with a "where status goes" rule for both apps.

## [0.5.3] (2 November 2026)

### Added

- **Ready-made image** for amd64 and arm64 at `ghcr.io/themightytrex/starboard` (each version, its minor
  version and `latest`), published by a workflow for every release tag. `compose.image.yaml` runs it with no
  build.

### Changed

- **Links:** the README's clone address and the licence now name the GitHub account (TheMightyTRex) and author
  (TheMightyTRexUK). The privacy check allows those two names and still catches everything else.

## [0.5.2] (2 November 2026)

### Fixed

- **Upgrade guide:** an upgrade from 0.4.0 or earlier now opens the upgrade guide with the 0.5.0 questions (new apps and Storage).
  Before, it assumed 0.5.0 and skipped them.

## [0.5.1] (2 November 2026)

### Fixed

- **Upgrade available:** looks for the newest version tag (what ./update.sh installs), and never offers an older
  version as an upgrade. Before, GitHub's last published release (0.1.8) could be offered.

## [0.5.0] (2 November 2026)

### Added

- **Search for new apps** (Settings, Manage apps): Starboard tries the usual port of about 40 apps, and every
  port a container publishes, on this computer only. It recognises each app by its page, leaves out the ones you
  have, and adds the ones you tick. With Docker access it reads the API keys of Sonarr, Radarr, Lidarr, Readarr,
  Prowlarr, SABnzbd and Seerr from their own settings files, if you tick "Fill in API keys for me".
  - It runs only when you press the button: no background work.
- **System, Storage** shows each pool as a bar (how full) and a ring (what fills it) by type: TV, films,
  audiobooks, music, books and comics, downloads waiting and everything else, with free space. Also each drive
  in the pool (fullest first), space used over time with a forecast of when it fills, and the biggest series and
  films. Every chart has a table view.
  - Sorting by type reads every file name, so Settings, Performance (and the set-up and upgrade guides) choose
    when: only when you press Work it out (the default), when you open Storage if over a day old, every night or
    every week at 3 am, or off. It now reads a pool once, skipping its drives, and stays on one file system: on
    the test server, 105 seconds for 30 TB, down from reading it twice.
  - A daily record of used space (on; nothing noticeable) feeds the forecast. Storage page updates: only when you
    press Check again (the default), or every minute or 5 minutes while the page is open.
- **Install apps** (Settings, Manage apps, or the first step of the set-up guide): tick groups such as Movies,
  TV, Music, Ebooks, Audiobooks, Comics, Watching, Downloads, VPN and Subtitles, and change the apps inside each.
  Apps already running are left alone; ports in use move to the next free one; each app shows its memory use.
  - Starboard writes `data/stack/compose.yaml` and `.env` (private, with database passwords made up for you),
    shows both, and keeps older copies. With Docker access, Start asks for your password, then makes the folders
    and starts the apps; without it, it gives you the one command to run.
  - It finds the folders your other apps already use for media and offers them, so nothing is moved. It offers
    watch history from Plex or Emby into a new Jellyfin; listening progress and copying app settings are next.
  - Apps that need their own settings file first (Unpackerr, Decluttarr, Janitorr) are written but not started.
- **Set-up guide** after the first password: apps, API keys, Jellyfin extras, download hours, alerts and how
  much Starboard does, with a summary and Change links at the end. Steps that do not apply are left out. Run it
  again from Settings, General.
- **Release notes** open from the version in the footer. "Upgrade available" shows there when GitHub has a newer
  release.
- **Upgrade guide:** after an upgrade that brings settings to choose, a notice opens a short guide with what is
  new and only those questions. "Remind me later" and "Keep the defaults and finish" are always there. Upgrades
  with nothing to choose do not interrupt.
- **Releases:** one process, in `docs/RELEASING.md`; `tools/release_notes.py` writes the GitHub notes.

### Fixed

- **System, Storage:** the stat tiles count a pool once, not once for the pool and again for its drives.

## [0.4.0] (2 November 2026)

A full security check found no critical issues. Its fixes are listed under Security.

### Added

- **Settings, Performance:** Starboard's own memory, processor and threads, measured live; four presets (Small
  server, Balanced, Everything, Custom); and every piece of background work with a switch, how often it runs
  and what it costs. Changing anything by hand makes it Custom.

### Changed

- **Background threads** exist only while their feature is on: history, watching, download hours and the Jellyfin
  jobs each start when turned on and end when turned off. With Small server, Starboard runs only its web server.
- **System history** can be off, or every 1, 5 or 15 minutes (5 by default, was 1), and no longer reads each
  container's use. The download hours check can run every 5 minutes. Downloads and Monitor update at the rate
  you choose, or Downloads only when you press Check again. Card numbers can be switched off.
- **Plex code:** the Plex database and XML code are loaded only when an import or a Live TV run needs them.

### Security

- **Request sizes:** a request with a negative size could make Starboard read without end and use up memory, signed out. Refused now.
- **Password guesses** sent all at once got past the 5-attempt limit. Attempts are now counted before the check, and
  at most two password checks run at once. X-Forwarded-For is believed only from the proxy itself.
- **Sign-in redirect:** the sign-in page's "next" address could send you to another site. Only pages on this dashboard now.
- **Saved keys:** a saved API key or alert token is not reused when an address points to a different server, and keys are not
  carried across a redirect to another server.
- **Apps, Updates:** Compose details from container labels are strictly checked and quoted, the folder can never be
  /, and the helper image is pinned to one exact build.
- **Requests:** dot-dot paths, idle connections (closed after 30 seconds, 64 requests at most), malformed requests, unknown
  host names (DNS rebinding; STARBOARD_ALLOWED_HOSTS adds names), size limits on uploads and downloads, Live TV
  channel data cleaned, Pluto's stream server checked, XML guides with a DOCTYPE refused, Pillow image limits.
- **Installer:** names with characters that would break .env or Compose files are refused. The disk health job
  writes in a private folder and never follows a planted link.

## [0.3.4] (2 November 2026)

### Added

- **Costs:** every setting that uses processor time or memory says what it costs, measured on a home server, so a small
  server can keep only what it needs. The access list on About and updates says the same for each item.

## [0.3.3] (2 November 2026)

### Changed

- **Live TV:** logos the folder already serves are used as they are, not processed again.

## [0.3.2] (2 November 2026)

### Changed

- **Live TV:** the guides refresh daily, but the channel lists are rebuilt (and every stream tested) only when a
  source's channel list changes, or once a week. Numbers and logos are redone only when a playlist changed.

### Fixed

- **Watch history import:** Jellyfin and Emby libraries are read 1,000 items at a time, so big libraries work.

## [0.3.1] (2 November 2026)

### Fixed

- **Jellyfin jobs:** send Jellyfin's API key the way newer Jellyfin versions need it.

## [0.3.0] (2 November 2026)

### Added

- **Settings, Jellyfin:** jobs moved in from the old launcher, each off until you turn it on.
  - **Live TV:** free channels and guides for Jellyfin (Free-TV, Samsung TV Plus, Pluto TV), Sky-style
    numbers, and white logos made with Pillow (switchable). Needs Jellyfin's Live TV folder (`./install.sh`).
  - **Import watch history** into Jellyfin from a Plex database file, a Plex server, Emby, another Jellyfin or a
    history file, with account matching; applied once per item, and every hour if you choose.
  - **User defaults** for every Jellyfin user.

### Changed

- **Apps, Other services** lists Starboard's own jobs and whether each is on.
- **Set-up** offers the Jellyfin jobs when it finds Jellyfin.
- **Credits:** Pillow and the data sources are credited in THIRD-PARTY.md.

## [0.2.0] (2 November 2026)

Lightweight first: a dashboard for smaller servers that uses very little processor time and memory (about
14 MB while idle). Every page now uses the component library shared with Storyarr.

### Added

- **Alerts:** to ntfy, Gotify or a webhook when an app stops answering, a disk has a problem or gets full, a
  download is stuck, a backup fails or a certificate runs out; uptime history for each app; a weekly
  summary. Off until you turn it on.
- **Apps:** small numbers on each card; Updates is its own page again, with each app's container, Check for
  updates, Update all and Update (needs Docker access).
- **Downloads:** download hours for qBittorrent and SABnzbd, with Resume, Pause and Follow the hours;
  speeds and the VPN's state (Gluetun); Finished this week; Requests from Seerr with Approve and Decline.
- **Coming up:** posters, a List or Calendar view, and how far ahead to look.
- **System:** Jellyfin's state, what is playing and what was added; server jobs with Run now; 30-day disk
  temperatures and the drive's own log; Read disks now; what is using the space; every drive; each app's
  processor and memory on Monitor; certificate expiry on Network.

### Changed

- **Lighter:** pages are compressed and the browser keeps them until they change; several tabs or devices
  share one answer from each app; hidden tabs stop refreshing; posters come from your own apps, kept for a
  week; background work starts only when needed.
- **Installer:** explains each step, and asks before each kind of access (home network, Docker for app
  updates, per-app use, folders for free space, Disk health). Run it again to change your answers.
  Settings, About and updates lists what Starboard can access, with the switch or command to change each.
- **Settings:** one column; Manage apps and the access list show each state as an icon beside the name;
  a new Alerts page; Coming up and Download hours settings in General.

## [0.1.8] (2 November 2026)

### Added

- **Backup and restore:** an option to include a rebuild prompt for an AI assistant with the server backup
  (the job is asked for `backup-with-prompt`). The page says what the server backup covers.

## [0.1.7] (2 November 2026)

### Added

- **Storage:** each folder has a tag with its filesystem, such as ext4, NTFS or mergerfs.

## [0.1.6] (2 November 2026)

### Added

- **System, Backup and restore:** download Starboard's settings as a file, restore from a file or from a copy
  Starboard saved, and start the server's own backup job and see its result and files. Downloading or
  restoring needs your password again.

### Changed

- **Apps:** the running and external access counts sit on the same row as Check again and Add an app, at the
  same height, with their coloured edge: "20/20 running at 23:47", "0/4 external access".

## [0.1.5] (2 November 2026)

### Added

- **Apps has a sub-menu:** Apps, Updates (each app's version, and whether Sonarr, Radarr, Lidarr, Readarr and
  Prowlarr have an update) and Other services (services with no web page; a service with no address can follow
  another app's status).
- **The Apps page opens with two cards:** how many apps are running, and how many outside addresses are reachable.
- **System has a sub-menu:** Overview, Storage, Disk health, Monitor and Network.
- **Charts:** Starboard records a reading every minute for 24 hours. Overview has tiles with trend lines and charts
  for processor, memory, network, disk activity and temperature over the last hour, 6 hours or 24 hours.
  Storage, Disk health and Network have their own charts. Every chart can be read with the arrow keys and
  shown as a table.
- **Disk health:** reads SMART reports saved by a small job on the server (`deploy/install-smart.sh`).
- **Your own folders and disks** go in `compose.override.yaml`, which updates leave alone.

## [0.1.4] (1 November 2026)

### Changed

- **New logo, Tile board:** three tiles and a star. In dark mode the star is lighter. Used in the header, the
  phone menu, the browser tab and the home-screen icon.

## [0.1.3] (1 November 2026)

### Added

- **Dashboard name:** the installer and the setup page ask you to name your dashboard. Change it in Settings, General.
- **App icons:** each app's own icon on its card, from the dashboard-icons collection. Starboard keeps a copy, so icons
  still show without the internet. Choose another icon in the app's settings.
- **Apps are grouped by category:** Watch, listen and request; Find and organise; Search and download;
  Dashboards and tools. New apps get a category chosen for them; change it in the app's settings. Health
  first still puts apps that are not responding at the top.
- **A footer on every page:** "Starboard: v" and the version, a link to the GitHub repository and to Updates.

### Changed

- **Looks like Storyarr:** its colours, its icons (Lucide) and its square tabs. The main menu and every sub-menu
  use the same tabs; on phones a menu drawer holds both.
- **Settings is four pages with a sub-menu:** Apps, General, Security and Updates. Old links still work.

### Security

- **The version** is only shown to people who have signed in.

## [0.1.2] (1 November 2026)

### Fixed

- **Updates:** `./update.sh` made the new version's files readable by you only, so the container could not start
  and the roll-back failed the same way. The image now makes its files readable whatever the host's
  permissions, and the updater only keeps the backup private.

## [0.1.1] (1 November 2026)

### Added

- **Remember me** on the sign-in and setup pages. Without it, you are signed out when the browser closes, or after
  a day. With it, you stay signed in for the number of days set in Settings, Security.

### Changed

- **Passwords** need 10 characters or more (was 12).
- **The setup code** stays the same when Starboard restarts or updates, so the code the installer printed keeps
  working until a password is set.

## [0.1.0] (1 November 2026)

### Added

- **Pages:** Apps, Search, Downloads, Coming up, System and Settings, each on its own page.
- **Search:** Search Sonarr, Radarr, Lidarr and Readarr at once and add what you find.
- **Five designs:** Health first (the default), Tiles, Shelf, Command and Status board, plus the Display and
  accessibility panel.
- **Installer and updater:** installer (Docker or systemd) and updater with backup and automatic roll-back.
- **Sign-in:** password sign-in with a one-time setup code; API keys never reach the browser.
- **Home network:** open it from phones and other computers on your home network, or switch that off in Settings so only the
  computer it runs on can connect. Docker uses host networking for this.
- **Phones:** phone layout on every page; add it to your home screen.
- **App addresses:** each app's home address and outside address on its card, each with a copy button. Both are on by default;
  turn them off in Settings, General. Apps saved as 127.0.0.1 open on the address your browser used, so they
  work from a phone.
- **Downloads:** show the download client's own state, so a paused client shows Paused.

[Unreleased]: https://github.com/TheMightyTRex/starboard/compare/v0.10.0...HEAD
[0.10.0]: https://github.com/TheMightyTRex/starboard/compare/v0.9.2...v0.10.0
[0.9.2]: https://github.com/TheMightyTRex/starboard/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/TheMightyTRex/starboard/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/TheMightyTRex/starboard/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/TheMightyTRex/starboard/compare/v0.7.7...v0.8.0
[0.7.7]: https://github.com/TheMightyTRex/starboard/compare/v0.7.6...v0.7.7
[0.7.6]: https://github.com/TheMightyTRex/starboard/compare/v0.7.5...v0.7.6
[0.7.5]: https://github.com/TheMightyTRex/starboard/compare/v0.7.4...v0.7.5
[0.7.4]: https://github.com/TheMightyTRex/starboard/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/TheMightyTRex/starboard/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/TheMightyTRex/starboard/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/TheMightyTRex/starboard/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/TheMightyTRex/starboard/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/TheMightyTRex/starboard/compare/v0.5.6...v0.6.0
[0.5.6]: https://github.com/TheMightyTRex/starboard/compare/v0.5.5...v0.5.6
[0.5.5]: https://github.com/TheMightyTRex/starboard/compare/v0.5.4...v0.5.5
[0.5.4]: https://github.com/TheMightyTRex/starboard/compare/v0.5.3...v0.5.4
[0.5.3]: https://github.com/TheMightyTRex/starboard/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/TheMightyTRex/starboard/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/TheMightyTRex/starboard/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/TheMightyTRex/starboard/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/TheMightyTRex/starboard/compare/v0.3.4...v0.4.0
[0.3.4]: https://github.com/TheMightyTRex/starboard/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/TheMightyTRex/starboard/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/TheMightyTRex/starboard/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/TheMightyTRex/starboard/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/TheMightyTRex/starboard/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/TheMightyTRex/starboard/compare/v0.1.8...v0.2.0
[0.1.8]: https://github.com/TheMightyTRex/starboard/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/TheMightyTRex/starboard/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/TheMightyTRex/starboard/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/TheMightyTRex/starboard/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/TheMightyTRex/starboard/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/TheMightyTRex/starboard/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/TheMightyTRex/starboard/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/TheMightyTRex/starboard/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/TheMightyTRex/starboard/releases/tag/v0.1.0
