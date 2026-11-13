# Changelog

All notable changes to Starboard are listed here, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with dates written as in the TRex Design System.
Version numbers follow [Semantic Versioning](https://semver.org/) loosely: before version 1.0.0, a patch release may also
add features.

## [Unreleased]

### Added

- System, Backup and restore, Full without media says which disk the copies go on, and warns when the folder is on
  the system disk, where a failed disk would take the backups with it. The folder it suggests is on another disk:
  the media folder's when the media is on one, else the biggest other disk's. Making a full backup and restoring it
  onto a fresh install is tested end to end in scratch folders (DASH-260).
- Starboard's API, version 1.1.0: the rest of the pages' reads (Coming up, requests, speeds, download hours, history,
  the Library and its search, uptime, app updates, counts, containers, version and processor history), a second right,
  Read and manage, for the everyday actions (approve or decline a request, remove or block a download, pause or resume
  downloads, build a Library tab again, look for container updates, run a Jellyfin job, send a test alert), and an
  event stream, /api/v1/events. Make a key now asks what it may do and what it may see. No key can change settings,
  keys, plug-ins or the install. Each change made with a key is in the audit log (DASH-274).
- AI assistants: a guide, Connect an AI assistant, for a Read only key named after the assistant with the fewest
  scopes, and /api/v1/logs, Starboard's log with addresses, names and keys taken out, only for keys with Logs ticked
  (DASH-76).
- Settings, General, Discover rows is its own page on the level 2 menu, with a section for each area of Discover
  (Films, TV, Music, Radio, Books and Audiobooks), each with its own rows, ticks, Move up and Move down, and Put back
  the standard rows. Only the area shown asks Reelix for its rows. Each Discover page's Change these rows opens its own
  area, and old links still work. Discover, Radio offers a row for each genre every radio source shares (such as
  Comedy), unticked until chosen, fetched when it comes into view and kept for an hour. Books and Audiobooks already
  offer every subject Reelix has (nine); Music has no genres in Reelix yet (DASH-396).
- Settings, Radio, Performance and Security have their parts on the level 2 menu: Radio's Sources, Add a show from a
  link, Your podcast library and Station logos; Performance's Preset and Pictures; Security's Who can open the
  dashboard, Password, API keys and Sign out everywhere. Each page asks only for what it shows (Radio asks Reelix for
  one part, not four). Old links to a part go to its new page (DASH-391).
- Settings, Downloads has VPN, Usenet and Download hours on the level 2 menu. Download hours there is the same field
  as Settings, General, Download hours (one setting, so the two stay in step), in place of a link. Starboard's links to
  download hours open it there (DASH-390).
- Settings, General has its pages on the level 2 menu: Names and apps, Appearance, Pages and lists, Download hours,
  and Logs and feedback. Style is now Appearance, with the own style's colours, the default design and the
  accessibility options (theme, text size, motion, contrast, underlined links and text spacing), kept in step with
  Display. Old links to a part go to its new page. Long lists is shown again, on Pages and lists (DASH-389).
- Starboard's own style has colours to choose from: Teal (the standard) and the design system's five palettes,
  Indigo, Forest, Plum, Ember and Graphite, for everyone on the server. Choose them on the Styles plug-in's page or in
  Settings, General. Reset style, and a plug-in that is deactivated or removed, goes back to the own style in those
  colours. The palette file loads only when one other than Teal is chosen (DASH-388).
- Settings, Apps, Dispatcharr sets up the Dispatcharr add-on without opening it: its admin (your Starboard password)
  and a key for Starboard, your IPTV playlist or Xtream Codes server and guide, channels from the playlist (up to
  1000), and Dispatcharr in Jellyfin as an HDHomeRun tuner with its guide. Still to set up points there in place of
  the guided step (DASH-228).
- Settings, General, Default design and Display's Design list show a small picture of each design, drawn in the
  theme's colours with no image to download, so you can see what you choose (DASH-315).
- Library, Music: Bring them in for artist folders already on disk, as films, series, books and audiobooks have. Each
  folder gets MusicBrainz's best artists (with what tells two of the same name apart); a sure match is ticked, and each
  artist follows only the albums already there. Still to set up counts them too (DASH-282).
- Library, Bring them in: a folder with no match (a home video, a radio programme listed nowhere) can come in with
  your own details: title, year, description, station for radio, and a picture as an address or a file. It shows only
  when Reelix can take it (Reelix task RFX-90, not in Reelix yet); Starboard checks Reelix's API description at most
  once in ten minutes, only while a Bring them in note is shown (DASH-322).
- Activity, Downloads: Held downloads, the releases a delay profile is holding back, with what each is for, its
  quality and site, why it waits and when it goes. Get it now sends one to the download app at once; Remove asks
  first. Asked only while the page is open, not on the queue's timer (DASH-210).
- System, Backup and restore: When backups are made, with Off, Manual, Weekly (Sunday at 03:00, keeping 4) and Nightly
  (at 03:00, keeping 7). It makes a full backup without media when you let Starboard keep the backup password's key,
  then asks the server's own backup job, and shows the next run (DASH-17).
- Settings, Updates, Restore: Keep the copies of the last 5, 10 or 20 versions. Older saved settings copies, and
  update.sh's older data copies, are removed by themselves (DASH-109).
- **Where you are and your keyboard first (DASH-259):** The Run first script now asks where the computer is (country and time zone) and then the keyboard, each as a list you move through with the Up and Down arrows and choose with Enter; typing letters jumps through the list, and accessible mode keeps numbered answers. The suggested keyboard comes from the location, or from a layout someone already set. It sets the time zone, the keyboard layout (the console follows it) and the system language when that is already on the computer, with the other changes it asks about, then offers a line to try the keys. Both set-ups, in the browser and the terminal, ask the same two questions after the password, unless the Run first script has just asked them; a different answer there becomes part of the set-up's change to the computer (`./install.sh --timezone` and `--keyboard`). The apps Starboard installs take the chosen time zone.
- **Help when a symbol is not where it is marked (DASH-112):** The keyboard step's help says where |, \, #, ~, @ and " really are on UK, Irish, German, French, Spanish and Italian keyboards while the US layout is set, and how to set the right layout. The browser set-up shows it under the keyboard list.
- **Clean up (DASH-77):** System, Clean up lists what is left over (removed plug-ins, old saved copies of the settings, an unfinished full backup's work folder, update.sh's older backups) with sizes, and moves what you choose to the holding folder. The Holding folder page puts each thing back, or deletes it for good after a dialog that says it cannot be undone and asks for your password. Starboard never deletes them by itself. Both set-ups end with a Clean up step in all three jobs when something is left over.
- **After an unexpected shutdown (DASH-88):** Starboard notes when it was stopped properly. At the next start after a power cut or a crash it checks, once, the folders it watches, the pool and any pool job that stopped part-way, a full backup that was cut off, and the apps, then says what it found on System, Overview and through Alerts.
- **Settings from the terminal (DASH-90):** `./settings.sh` signs in with your Starboard password and changes settings through Starboard's own API, starting with the automatic updates: looking for new versions, Reelix installing its own updates, and the commands to update or go back to an earlier version. The same look as the terminal set-up, with plain lines for screen readers.
- **Running with no screen (DASH-89):** `sudo deploy/headless.sh` shows what it would change and asks first: never sleep, the lid ignored and the power button shutting down cleanly, no waiting at the boot menu, disk repairs at start without asking, starting again after a crash, and the watchdog where there is one. It saves a copy of each file it edits, and `--undo` puts every change back. `--firmware` lists the firmware settings to make by hand (power back on after a cut, no keyboard needed, Wake on LAN).
- **A dialog for long changes:** Move them into Reelix, Take over my apps, Roll back and Clear away open a dialog with a working bar and a list of each app or step (Waiting, Working, Done, Not moved, Not started), what it is doing now and the result. Close it and the work carries on; the page says it is still running, with Show progress
- **Review the move:** after moving into Reelix, the sites held off with Activate and Activate all, the sites Reelix cannot search yet, and the titles that did not move with Add by hand
- **Titles waiting for a match:** films and series a move could not match wait on Settings, Your install with the TMDB, TVDB and IMDb ids Radarr and Sonarr had for them, and are added to Reelix once they match: when a TMDB key is added, every six hours while any wait, or with Try again now
- **Requests after the move:** when Seerr runs beside Reelix, choose Reelix's own requests (recommended) or Keep Seerr, which points Seerr at Reelix; with a message for the people who use Seerr
- **Clear away the apps Reelix replaced:** after Keep it, Prowlarr, Radarr, Sonarr, Readarr, Lidarr, Kapowarr, Profilarr, Decluttarr and Unpackerr can be stopped and removed, their settings folders moved into a holding folder beside them (nothing is deleted) and their dashboard entries taken off

### Changed

- Library walls, Wanted and History load their next page with the design system's load more as you scroll (UX-52):
  "Loading the next 40 films" shows while it loads, a screen reader hears "24 more films shown", focus stays where it
  was, and after three lots in a row it pauses so the footer stays in reach; Show 40 more always works and carries on
  (DASH-277).
- Release notes: the footer's Release notes link says it opens a slide-out, and a test keeps the slide-out's newest 3
  releases the same as this changelog's, with their dates (UX-50).
- Footer: About and updates says Upgrade available, with the update dot, when a newer release is out, as the design
  system's footer sets out; Sign in and Set up have no footer (DASH-104).
- **The same item for the same job everywhere (DASH-309):** app cards show their state and one more chip at most, with
  one button besides opening the card (Copy is in the app's details); Still to set up has one button; Apps, Updates
  updates the apps you tick from a selection bar instead of an Update on every row; Library's count is at the end of
  its toolbar, with Save this view and Select several in the page head; History's keep setting and Delete history are
  at the end of the page; Wanted's rows open their details and Select several works as in Library; the pool's drives
  are rows; chart tables stack on phones; Install apps' Check step is a list with Change on each answer; saved
  settings on the Dashboard, Library, History, Logs and Reelix, System show a saved note instead of a toast; notices
  have a title, an icon and a tone.
- **Moving over on the Reelix route:** Install apps says which of your apps move into Reelix and which Starboard runs for you, and where (Settings, Your install, Apps you already run); the step is left out when there is nothing to bring over
- **Change your install:** apps running from your own Compose file are no longer offered again as new, empty apps; the page points to Apps you already run
- **Move them into Reelix:** each message is under its own button; qBittorrent's user name is read from its settings file; the qBittorrent password says what it is for and that it is optional; a new try clears the last error at once

### Removed

- The old Note an issue tester, ux-notes.js, and its styles: Send feedback (Snaglist) replaced it. Notes it saved
  are still listed in Settings, General, Logs and feedback (DEV-05).

### Fixed

- The API and plug-in checks are one command, `bash tools/check-api.sh`, run by CI on every push: the API
  description and reference must be what their tools write, then the contract tests, the plug-in tests and each example
  plug-in against the new build. The API description's tool wrote an older description than the one in the repository,
  so the CI check failed; it now takes each route's scope and the version from the route table (DASH-281).
- A full backup that fails now sends the backup alert; a copy cut off part way no longer stays in the backup folder;
  Reelix's backups section no longer says Starboard copies them (DASH-78).
- **qBittorrent's ban:** after too many wrong passwords qBittorrent stops accepting sign-ins from Starboard; the page now says so, for how long, and how to clear it
- **A move that stopped:** the steps after it say they did not start, and why

## [0.16.5] (11 November 2026)

### Added
- **Audiobooks and books already on disk:** Library, Audiobooks and Library, Books bring in the author folders already on disk through Reelix, each author matched on Open Library and following only the books you have, so Reelix never wants everything an author wrote. A folder is ticked only when the match is certain; the rest wait for you. Also in Still to set up.
- **Styles that change more:** A style from a plug-in may now also set the side menu, panel headers, the chosen button, count badges, status messages, chart colours and the logo, a heading font and weight, a thicker focus ring, more shadows, gradients and soft glows, textures (grain, dots, grid, lines), glass panels and rounded buttons and fields. Every colour text can sit on is checked for contrast (WCAG 2.2), glass panels as they look over the page behind them; Display's high contrast and a device set to reduce transparency turn the effects back to solid colours. Styles 1.1.0 uses them, with five new styles. Help: [Change text size, theme and other display settings](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/display-and-accessibility.md) and [Add a plug-in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/add-a-plugin.md).

### Changed
- **Plug-in API 1.1:** Plug-ins may ask for starboard_api >=1.1 to use the wider styles; plug-ins made for 1.0 work as before.

### Security
- **Image packages:** The image now takes every Alpine package's fixed version when it is built. This one fixes 16 high and 5 medium problems in krb5-libs (fixed in 1.22.3), found by the release's security scan.
- **Checks:** The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check, the screenshots and the security scans ran on this release.

## [0.16.4] (10 November 2026)

### Added
- **Reset style:** Display has a Reset style button under the style list, and Settings, General has a Style section saying which style this browser uses, with Reset style and Choose a style. Reset style goes back to Starboard's standard colours and keeps your other Display choices. Help: [Change text size, theme and other display settings](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/display-and-accessibility.md).

### Fixed
- **Live TV guides that ran out:** Samsung TV Plus's guide covers about ten hours, so refreshing once a day left its channels empty by the evening. A guide is now fetched again when it has under 12 hours left, and Jellyfin reads new guides straight away. Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md).
- **Each guide with its own channels:** With every guide set for every channel list, Jellyfin took programmes from the first guide only. Live TV now links each guide to its own list in Jellyfin, and puts right set-ups made before. Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md).
- **Display's Reset left the style ticked:** Reset in Display now also unticks a style from a plug-in.
- **Bringing in radio shows looked stuck:** Finding your radio shows on Reelix's sources searched one show after another, which could take minutes with nothing on screen. It now searches five at once, ten to a page, and the button says it is finding them. Help: [Follow radio shows and podcasts](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/follow-radio-shows.md#bring-in-shows-you-already-have).

### Security
- **Checks:** The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release.

## [0.16.3] (10 November 2026)

### Added
- **Radio shows you already have:** Library, Radio brings in the radio shows already in Audiobookshelf's Radio library: Starboard finds each one on Reelix's radio sources, ticks it when the title is the same, adds it, and asks Reelix to search for the episodes you do not have. Settings, Reelix, Radio connects Reelix to that library first, with the folder Audiobookshelf itself reports. Help: [Follow radio shows and podcasts](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/follow-radio-shows.md#bring-in-shows-you-already-have).

### Fixed
- **Still to set up keeps steps you did elsewhere:** Add a TMDB key and Point Reelix's radio at Audiobookshelf now go once Reelix has them, wherever they were done, not only from the set-up wizard. Radio is one step instead of two.
- **Folders of shows already in your library:** When bringing in films or series from disk, a folder whose match is already in your library (in another folder) says so and is unticked. Unticked folders are left out and no longer counted on Still to set up.
- **Radio set-up on older servers:** Set-up pointed Reelix's radio at /media/radio even where Audiobookshelf uses another folder, such as /radio; it now uses the folder Audiobookshelf reports.

### Security
- **Checks:** The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release.

## [0.16.2] (10 November 2026)

### Changed
- **TV networks as a grid:** Library, TV, Networks shows each network as a square card with its logo, its name and how many series it has; a network's own page shows its logo too. Help: [Browse your library](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/browse-your-library.md).
- **The A to Z bar:** Letters with titles are filled buttons and letters with none are plain grey, so you can see at once which letters have anything.

### Fixed
- **Posters slow to show:** Starboard keeps a poster for every item in every library (it used to keep 400, fewer than a larger library has), fetches missing ones in the background when a list is rebuilt, and no longer lets the browser remember a busy image site as no picture for an hour. Reported in issue #5.
- **Network logos cut off:** A wide logo now fits inside its card, and logos are drawn in greys rather than flat black, so white words inside a shape (Cinemax, ABC) stay readable. Reported in issue #4.

### Security
- **Checks:** The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release.

## [0.16.1] (10 November 2026)

### Added
- **The set-up helper with updates:** A server set up before 0.16.0 gets the set-up helper with this update, and later updates keep it. ./install.sh --no-starter turns it off for good, until ./install.sh --starter. Help: [Change what Starboard can access](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-what-starboard-can-access.md#the-set-up-helper).

### Fixed
- **Memory that grew with use:** Starboard kept every answer it had fetched for each search, item page and calendar range until it restarted, so its memory grew the more it was used. It now forgets answers once they are out of date and keeps at most 200. On the example server, 2,000 searches no longer add any memory.

### Security
- **Checks:** The unit tests (also as another user), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release.

## [0.16.0] (10 November 2026)

### Added
- **Nothing to set up outside Starboard:** The installer adds Docker when it is missing, Starboard reads each app's API key itself (Jellyfin, Audiobookshelf, Bazarr, NZBGet and others), and a small set-up helper on the server starts the apps and makes the set-up's changes, so the Run first window can close. Help: [Change what Starboard can access](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-what-starboard-can-access.md#the-set-up-helper).
- **Make the change now:** The set-up's last page makes its change to the server for you, after your Starboard password, with a progress bar and the installer's words live in a slide-out.
- **Still to set up, done in place:** Each of Starboard's own steps opens its page inside the slide-out, at the right part, so the set-up is done there; Next step checks again and drops a step that is done. Help: [Finish what is still to set up](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/finish-setting-up.md).
- **Picture quality in full:** Settings, Reelix, Picture quality: choose a level, see what it does in plain words, and under Advanced settings put its qualities in order, tick the ones to accept, move Stop upgrading here, and set extras to Prefer, Neutral or Never. Help: [Change Reelix's settings in Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-reelix-settings.md).
- **The folder picker:** Folders are chosen with Browse, and each one is checked as you type: whether it is there, which disk it is on and how much is free.
- **App logs:** System, Logs shows each app's own log, so Dozzle is no longer needed. Help: [Read the log and report a problem](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/read-the-log.md).
- **New releases in Alerts:** A short weekly line through Alerts when a new Starboard is out. Help: [Activate alerts](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/activate-alerts.md).
- **Graphics chip found everywhere:** The browser set-up also finds an Intel or AMD graphics chip for Jellyfin when Starboard runs in Docker.
- **A simpler help centre:** Every article checked against this version, simpler, and linked to the exact part of each area it mentions, with six new articles: Find a setting, Finish setting up, Get what is missing, Live TV channel will not play, Use Starboard's API and Use the dashboard. Help: [Starboard help centre](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/README.md).
- **Plug-ins in their own place:** The plug-in collection lives at github.com/TheMightyTRex/starboard-plugins, with each plug-in's install address and zip. Help: [The plug-in collection](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/plugin-collection.md).

### Changed
- **Add-ons:** Dozzle, Wizarr and Dispatcharr are add-ons you tick in Install apps, not part of the Full install. Help: [Basics, Full install and Everything: what each one has](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-types.md).
- **The setup code:** Filled in from the installer's link, it is read only, with a note that Starboard uses it to continue.
- **Run one command:** When a command is still needed, it always shows, and the page says to run it in a terminal on the server.

### Fixed
- **Out-of-date words:** Thirteen places in Starboard's pages said where things used to be, such as Send feedback in the corner; they say where things are now, and links to parts under Advanced settings show those parts.
- **Settings, Reelix with Reelix Lite:** The word null no longer shows between Basic settings and Sites to search.
- **Pages in a slide-out:** The upgrade guide opened inside Starboard only on its first visit; it now opens every time.

### Security
- **Checks:** The unit tests (also as another user, as GitHub runs them), the browser journeys, the API contract tests, the help check, the private details check, the design system copy check and the security scans ran on this release. The set-up helper runs as your user and cannot use sudo.

## [0.15.5] (10 November 2026)

### Added
- **Send feedback in the side menu:** Feedback is now an item at the foot of the side menu, and on a phone a row in the menu, instead of a button floating over the page. Pages with no side menu, such as the set-up, keep the button in the corner. Help: [Send feedback about a page](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/send-feedback.md).

### Fixed
- **The ready-made image:** The ready-made Starboard image builds again. Since 0.15.2 a test that only passed on one computer stopped GitHub building it, so installs from the image stayed on 0.15.1. Help: [Install Starboard from the ready-made image](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-from-the-ready-made-image.md).

### Security
- **Checks:** The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.15.4] (10 November 2026)

### Added
- **Still to set up, one at a time:** Go through them opens a slide-out that walks through each thing left to set up, with Do it now, Skip, Ignore, Done and Next step. It also opens by itself once in each browser session while anything is left.
- **Plug-in install addresses and downloads:** The plug-in collection in the help centre now gives each plug-in's install address, to paste into Add a plug-in, and a zip to download. The Styles plug-in lives in Starboard's own repository, under plugins-collection. Help: [The plug-in collection](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/plugin-collection.md) and [Add a plug-in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/add-a-plugin.md).

### Fixed
- **Links to apps in Still to set up:** Links in Still to set up, such as Tell Tdarr what to convert, open at the address you opened Starboard at, instead of 127.0.0.1, which another device cannot reach. Help: [Open Starboard from a phone or another computer](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/open-from-another-device.md).
- **Waiting for Linux's updates:** Run first no longer waits for Ubuntu's always-running shutdown helper as if it were updates, and its bar now says what is installing, how many are done and how much is downloaded. Help: [Set up everything with the Run first script](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first.md) and [RF-12](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#rf-12).
- **Done on guided steps:** Done on a guided step, such as Tdarr's, now saves instead of failing.

### Security
- **Checks:** The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.15.3] (10 November 2026)

### Fixed
- **Built-in plug-ins follow Starboard's updates:** Each time Starboard starts, its built-in plug-ins, such as Live TV, are set up again from the new version and started again, so they get its fixes.

### Security
- **Checks:** The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.15.2] (10 November 2026)

### Added
- **Send feedback everywhere:** Send feedback, with Snaglist 0.4.0 and its QR code reports, is now on every page by default; deactivate it in Settings, General. Help: [Send feedback about a page](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/send-feedback.md).

### Fixed
- **Region and language in Settings, Reelix:** Saving Information with Region empty no longer fails with "not in the form it needs"; Language of details and Region are now lists with plain names, one choice each, as Reelix uses. Help: [Change Reelix's settings in Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-reelix-settings.md).
- **Plug-in data folders:** Starboard makes each plug-in's data folder for the user the plug-in runs as, so a plug-in can save its work; Live TV's first run on a real server could not.
- **Plug-in cards and buttons:** Starboard finds a plug-in at its address when it uses the computer's own network, so cards and buttons such as Run Live TV now answer.
- **Built-in plug-ins' health:** Built-in plug-ins check their own health instead of Starboard's, so Docker no longer marks them unhealthy.

### Security
- **Checks:** The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.15.1] (10 November 2026)

### Fixed
- **Live TV's move:** Starboard's container now knows where the Live TV folder is on the computer, so Live TV moves into its plug-in as 0.15.0 meant to. Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md).
- **Live TV and newer Jellyfin:** Live TV sends Jellyfin's key the way Jellyfin 10.11 and later expect, so it can add its channels and guides there. Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md).
- **No channels twice:** When Live TV moves, it reads the folder from Jellyfin's own tuners, so it never adds the same channels again under another path. Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md).

### Security
- **Checks:** The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.15.0] (10 November 2026)

### Added
- **Live TV as a plug-in:** Live TV comes with Starboard as a built-in plug-in: add it in Settings, Plug-ins, with its own card, settings and Run Live TV now. It runs locked down on Starboard's own image. Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md) and [The plug-in collection](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/plugin-collection.md#live-tv).
- **Waiting for Linux's updates:** Run first waits with a progress bar while Linux installs its own updates, and tries again by itself if they start part-way, instead of stopping with error RF-12. Help: [Set up everything with the Run first script](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first.md) and [RF-12](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#rf-12).

### Changed
- **Your Live TV moves by itself:** If Live TV was on, Starboard moves it into the plug-in on its first start, with the same settings and folder; Jellyfin's channels and guides do not change. Where the plug-in cannot run, Live TV stays in Starboard as before. Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md).

### Security
- **Checks:** The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.14.1] (10 November 2026)

### Added
- **Choose now:** When an upgrade has something to choose, Choose now opens those choices in a slide-out over the page you are on; Open as a page still opens the full guide. Help: [Update Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-starboard.md#after-the-update).

### Fixed
- **API error links:** The links in the API's error answers open the new errors page in Starboard's repository.

### Security
- **Checks:** The unit tests, the browser journeys, the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.14.0] (10 November 2026)

### Added
- **Plug-ins:** Settings, Plug-ins adds a plug-in from its address, its file or its own installer, shows what it may do with a risk level and its test results first, and activates, deactivates or removes it, keeping its folder. Help: [Add a plug-in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/add-a-plugin.md) and [What a plug-in can change](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/what-plugins-can-change.md).
- **Styles from plug-ins:** A plug-in can add styles to Display, which Starboard checks for accessibility in light and dark and draws itself; the Styles plug-in has eight, each with a picture to choose from. Help: [The plug-in collection](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/plugin-collection.md#styles).
- **Plug-in tester:** Test a plug-in lists every issue with where it is and how to fix it, and always tests accessibility; the same tests run before any plug-in is added. Help: [Add a plug-in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/add-a-plugin.md#test-a-plug-in).
- **Plug-in cards:** Plug-ins can add cards to the dashboard that show a number, a list or a status, asked at most once a minute. Help: [Write a plug-in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/write-a-plugin.md#dashboard-cards).
- **Starboard's API:** A read-only API at /api/v1 for other apps, scripts and AI assistants, with its own keys made in Settings, Security and a published description.
- **The dashboard:** A dashboard of cards is the first page after signing in, in four layouts, with Edit dashboard to add, size and move cards.
- **Library actions:** Film and series pages have Get it, Follow, Stop following, Delete, Choose a download and watched or not watched from Jellyfin. Help: [Browse your library](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/browse-your-library.md).
- **Wanted, History and Issues:** Wanted shows what is missing or below the quality wanted, with Search; History and Issues are real pages; Requests shows Reelix's own requests.
- **Download now:** Wanted items can download straight away, outside download hours.
- **Basic and advanced settings:** Every Settings page opens on its basic settings, with an Advanced settings switch for the rest.
- **Settings, Downloads:** A new page for the VPN, the Usenet server and download hours, with Test buttons.
- **Reelix's settings, backups and logs:** Settings, Reelix covers its basics, folders, information, files and requests; System has Reelix's backups and log; Reelix can update automatically, off until you switch it on. Help: [Change Reelix's settings in Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-reelix-settings.md).
- **YouTube and Spotify:** With the full version of Reelix, downloads from a YouTube or Spotify link, with Connect Spotify. Help: [Switch between the two versions of Reelix](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/switch-reelix-version.md).
- **Apps set up for you:** Jellyfin, Audiobookshelf, Jellystat, qBittorrent, Bazarr and Gluetun are set up by Starboard, and Live TV's channels and guides are added to Jellyfin by itself. Help: [Install apps with Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-apps.md).
- **Guided steps:** The set-up checklist has short guided steps with Done for Tdarr, Wizarr, Dispatcharr and Soulseek.
- **More apps:** Soulseek through slskd and the No-IP updater in Install apps; FlareSolverr is offered only when a site needs it.
- **The graphics chip:** Jellyfin uses an Intel or AMD graphics chip to convert video when the computer has one.

### Changed
- **One set-up in each place:** The browser and terminal set-ups ask the same questions in the same order, including the TMDB key, the Usenet server, sites to search and the VPN.
- **First set-up only:** A new Starboard shows only the set-up until it is finished.
- **Wizarr and Dispatcharr:** They are add-ons in Install apps instead of part of the Full install. Installs that have them keep them. Help: [Basics, Full install and Everything: what each one has](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-types.md).
- **Long lists:** Library walls, Wanted and History load more as you near the end.
- **Plug-in words:** Plug-ins are activated and deactivated, in the house style.

### Fixed
- **Test scripts after the dashboard:** The help pictures, screenshots and browser journeys wait for the dashboard after signing in.

### Security
- **Settings by risk:** Each general setting has a level of access; network access, secure cookies, session length and the alert channel can never be changed by an API key.
- **Addresses Starboard calls:** Link-local and cloud metadata addresses are refused, and a request carrying an app's key never follows a redirect to another server.
- **Sign out everywhere:** It now asks for the password, so a session someone else has cannot sign everyone out. Help: [Sign out everywhere](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/sign-out-everywhere.md).
- **API keys:** Keys are shown once, stored only as a SHA-256 hash, sent only in a header, and every change is in an audit log.
- **Plug-ins locked down:** Plug-ins never get the Docker socket, the host network, devices or other apps' folders; containers are read only, without capabilities, not root and limited in memory and processor. Help: [What a plug-in can change](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/what-plugins-can-change.md#what-a-plug-in-can-never-do).
- **Checks:** The unit tests (600), the browser journeys (66), the API contract tests, the help check, the private details check and the security scans ran on this release.

## [0.13.2] (9 November 2026)

### Added
- **Update in the side menu:** the version is now at the bottom of the side menu, and when a newer Starboard is out, "Update" with a dot shows above it, linked to About and updates. The footer's About and updates says "(1)" too (DASH-104, DASH-105). Help: [Update Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-starboard.md#find-out-whether-an-update-is-out).

### Changed
- **The footer** is the design system's: Starboard's name and logo, then Help, Release notes, GitHub repository and About and updates, with the TheMightyTRexUK mark on the right (DASH-104).
- **Reelix's updates come from your fork:** Apps, Updates checks the Lite or full image Starboard installed, from TheMightyTRex's Reelix, and its What is new reads that branch's changelog. Reelix's own check of upstream's releases is no longer shown. Help: [Update your apps](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-your-apps.md#what-is-new-in-reelix).

### Fixed
- **Reelix's logo** now shows on its card on servers where Starboard had looked for an icon before 0.13.1 and found none.

## [0.13.1] (9 November 2026)

### Added
- **Reelix's warnings in Starboard:** Apps, each app's details and System now show Reelix's own warnings, such as a site to search that keeps failing or a download app it cannot reach, each with a link to the place in Starboard that puts it right. Reelix's Sonarr- and Radarr-style health answer is always empty, so Starboard now asks Reelix's own health check (DASH-176, DASH-160).
- **Tdarr on the dashboard:** a Full install's Tdarr is found and shown like the other apps (DASH-221).

### Changed
- **One Reelix card:** Apps shows Reelix once, with the queue, wanted and update of films, series, books and music together, instead of a card for each kind (DASH-256).
- **Reelix's logo** on its card comes from the running Reelix, as the icon collection has none (DASH-255).
- **FlareSolverr** is given to Reelix whenever it is installed, through the VPN when there is one, not only when searches go through the VPN (DASH-219).
- **Reelix never updates itself:** the set-up keeps Reelix's own installing of updates off, because Starboard updates Reelix on Apps, Updates (DASH-187). Help: [Update your apps](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-your-apps.md).
- **Starboard runs Reelix:** the set-up guides, messages and help now send you to Settings, Reelix in Starboard, not Reelix's own pages. The free TMDB key is the one thing still added in Reelix itself, until a later version asks for it (DASH-161). Help: [Change Reelix's settings in Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-reelix-settings.md).
- **SABnzbd in the set-up guide:** the guide no longer asks you to set SABnzbd's folders, API key and Reelix connection by hand on the wrong port; Starboard already does all three (DASH-215).
- **Help for going back to Reelix without YouTube and Spotify downloads** says what stops working (DASH-224). Help: [Switch between the two versions of Reelix](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/switch-reelix-version.md).
- **Accessible mode in the terminal** says "Still working" every 2 minutes during a long job, such as downloading the apps, so a screen reader is never silent for long (DASH-236).

### Fixed
- **Reelix's sites after a restart:** Reelix now starts once the VPN is ready, so its searches no longer fail for five minutes after the server restarts (DASH-262).
- **Apps that keep restarting:** after starting the apps, the installer looks again a few seconds later, so an app that keeps restarting, such as a VPN with a wrong key, is no longer counted as running (DASH-235).
- **A long row of filter chips** on a phone scrolls inside its toolbar, from the design system (DASH-244).

## [0.13.0] (9 November 2026)

### Added
- **Reelix's settings in Starboard:** Settings, Reelix now shows Reelix's sites to search, media servers and download apps, each with its state, and adds, changes, tests and removes them. The forms come from Reelix's own description of each setting, so a setting Reelix adds shows without a Starboard update. Each change asks for Reelix's admin password, signs in to Reelix for that change only and signs out again; Starboard still keeps only a manager key (DASH-154). Help: [Change Reelix's settings in Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-reelix-settings.md).
- **Sites to search:** Install apps and the terminal set-up have a new step, Sites to search, with the same questions in both: a short list of Reelix's public sites, none ticked unless you tick them, and your own Torznab or Newznab address. Settings, Reelix lists every site Reelix knows, with how many searches each has answered (DASH-155). Help: [Choose the sites Reelix searches](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-sites-to-search.md).
- **Searches through the VPN:** with the VPN installed, Reelix's searches go out through Gluetun, as Prowlarr's did, and wait when the VPN is down. Install apps sets it up, and Settings, Reelix has a switch for it. Gluetun's own proxy is activated for this (DASH-133). Help: [Choose the sites Reelix searches](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-sites-to-search.md).
- **Jellyfin and Audiobookshelf in Reelix:** Install apps connects Reelix to them with the API keys Starboard already has, so new files show in them at once. Settings, Reelix, Media servers connects them with one button (DASH-156). Help: [Connect Reelix to Jellyfin and Audiobookshelf](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/connect-reelix-to-media-servers.md).
- **The Library, from Reelix:** **Library** shows everything Reelix holds, as TV, Films, Music, Radio, Books and Audiobooks. Each is a wall of covers, A to Z, with a search for that kind, filters with their counts (such as **Missing** or **Coming soon**), sort (A to Z, Recently added, Year), Covers or List, three cover sizes and **Show 40 more**. The placeholder Library pages are gone (DASH-163). Help: [Browse your library](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/browse-your-library.md).
- **The A to Z list:** a row of letters above each wall. Letters with nothing under them are shown but cannot be chosen, and say so to screen readers. It stays in view as you scroll, marks the letter you are at, and takes one Tab stop: the arrow keys move along it and Enter jumps. A letter further on opens the wall at that letter, with **Show earlier titles** above it. The row comes from the TRex Design System. Help: [Browse your library](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/browse-your-library.md).
- **A page for each title:** a film, series, artist, radio show, book or audiobook opens its own page with its name, what it is, how much of it you have, and its episodes, albums, reading order or collection, then **About**. A series' episodes are grouped by season, the newest open, so a long series is not one long list. Radio shows link to Audiobookshelf to listen. Help: [Browse your library](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/browse-your-library.md).
- **Groups:** **Networks** for TV, **Collections** for films, **Stations** for radio, and **Series** and **Authors** for books and audiobooks, each opening the wall with only that group's titles. Help: [Browse your library](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/browse-your-library.md).
- **Save this view as default:** a changed sort, layout, cover size or filter can be saved as how that kind opens, for your account on every device. **Settings**, **General**, **Library views** lists them, with **Reset Library views**. Help: [Browse your library](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/browse-your-library.md#keep-your-favourite-view).
- **Search opens on your library:** before you type, Search shows what was recently added and each kind with its count. As you type, it searches your library first, then lists what Reelix can find under **Not in your library**, each kind as soon as it is ready, with **Add**, or **Follow** for radio shows and podcasts (DASH-162). Without Reelix, Search looks in Sonarr, Radarr, Lidarr and Readarr as before. Help: [Search for and add films, series, music and books](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/search-and-add.md).
- **Help:** new articles: Change Reelix's settings in Starboard, Choose the sites Reelix searches, Connect Reelix to Jellyfin and Audiobookshelf, and Browse your library; Install apps, Set up in the terminal, Search for and add, and Follow radio shows are updated for the new steps and the new Search. Each has marked-up screenshots.

### Changed
- **PrivadoVPN's link:** In both set-ups, the VPN step's PrivadoVPN link now goes to PrivadoVPN's sign-up page. It is an affiliate link, so the step says so in an Ad note before the list, and PrivadoVPN's line is marked Ad.
- **Adverts in the help centre take turns:** The help centre's advert now shows Newshosting on one page and PrivadoVPN on the next, in turn. Nothing changes while a page is open, and Hide hides both.
- **Search in the side menu** is now a link to the Search page on a computer. On a phone, the search button at the top of the screen and the search box in the menu work as before. The Search page stays in **Discover**.
- **TV's second tab** is now **Networks**, and Radio's **Series** tab is gone: a radio show's series are on its own page.
- **Posters on Coming up and the Library:** the setting in **Settings**, **Performance** now covers the Library's covers too. Help: [Find out what is coming up](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/coming-up.md#show-or-hide-posters).
- **The Library keeps a small list of each kind** in `data/library`, with only what a wall needs: about 210 bytes a film. It is read from disk for each request, never held in memory, rebuilt when you open a kind and it is more than five minutes old, and every 30 minutes while the Library is in use. Nothing runs when nobody uses the Library. With 5,000 made-up items, Starboard held 2.4 to 3.6 MB more memory after using every part of the Library than after opening the old pages, and at most 4.9 MB more while reading Reelix; at idle, 0.7 to 0.9 MB more.
- **Covers come through Starboard at a small size** (TMDB w185 on walls), are kept for a week (at most 400), and a missing picture is not asked for again for a day. Your browser never contacts the image sites.

### Fixed
- **Error numbers when a job does not finish:** In the terminal set-up, a job that did not finish, such as starting the apps, showed no error number in the boxed look, while accessible mode showed IN-33 only among the details. Both now show the number under the problem, with the address of its help on a line of its own, and Report this problem includes it (DASH-152). Help: [IN-33](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#in-33).
- **The installer's own stops:** The Run first script showed RF-40 whenever the installer stopped, after the installer's own number, so a stop had two numbers, and some of the installer's stops had none. Every stop of the installer and the terminal set-up now has its own number (new: IN-35 to IN-38), and the Run first script ends on that number. RF-40 is kept for an installer that stopped without one, and stopping it yourself with q or Ctrl+C is no longer shown as an error (DASH-147). Help: [RF-40](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#rf-40).
- **Waiting for the apps to answer:** After starting the apps, the terminal set-up waited the full two minutes, with nothing new on the screen, for apps that had not started, such as qBittorrent behind a VPN that had not connected. It now waits only for the apps that started, and Starboard adds the others itself once they answer (DASH-151).
- **The installer's sudo question after Run first:** On systems without `sg`, the installer starts itself again with your new Docker access through sudo, and sudo asked for your password with no word of why. It now says why first.
- **Long answers in accessible mode:** In the Run first script and the installer, accessible mode printed each answer of a question on one line, however long, so in an 80 column window the last letter ran onto a line of its own. Answers now wrap between words inside the window, the rest set in under the number.
- **The last page in accessible mode:** When the set-up in the terminal asked to change this computer, such as for disk health, the Run first script ran the installer again without accessible mode, so the very last page came back with boxes. That run is plain too now.
- **Docker access on Ubuntu 26.04:** When the installer starts itself again with your new Docker access through sudo, Ubuntu 26.04's sudo (sudo-rs) dropped all of Starboard's settings, so the second run lost accessible mode and the Run first script lost the installer's error number. The settings now go across by name.
- **The last card in a narrow window:** At the end of the set-up in the terminal, a window 60 columns wide cut the card's labels short, such as "On your other devic", and a long folder ran past the card's edge. In a narrow window each label now has its own line with the value under it, and a word too long for the line is broken inside the card.
- **The VPN list at 80 columns:** In the set-up in the terminal, PrivadoVPN's address in the VPN list ran past the right edge of a window 80 columns wide. When an address is too wide for its column, each provider's address now goes on the line under its name.
- **Keys pressed while a job runs in accessible mode:** An Enter pressed while a job ran answered the next question with its default. It is now thrown away when the job ends, as in the boxed look.
- **Live TV channels that would not play:** Jellyfin's FFmpeg refuses Live TV pieces whose address has no file ending, such as the ad links on Samsung TV Plus channels like U&Laughs, so 107 channels stopped playing. Install apps now runs Jellyfin's FFmpeg through a small Starboard file, `jellyfin/ffmpeg-wrap/ffmpeg` in your settings folder, which allows those addresses for Live TV only. Your library files and On demand links are played as before. Starting the apps, from Starboard, from the installer or by taking over your apps, puts the file in place, so running the guide again keeps the fix (DASH-169).
- **Error IN-34:** If the installer cannot put that file in Jellyfin's settings folder, it stops with error IN-34 rather than start a Jellyfin that cannot find FFmpeg. Help: [IN-34](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#in-34).
- **Taking over Reelix while it reports a problem:** Reelix says it is unhealthy while a download app it was given cannot be reached, which is often what the takeover is about to fix. Starboard now carries on instead of waiting for it. Help: [Take over the apps you already run](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/take-over-your-apps.md).
- **Old apps left on the Apps page after a takeover:** apps added before Starboard marked its entries were not recognised, so Radarr and the others stayed on the Apps page. They are now found by their kind or name and taken off. Reelix's own entries are kept. Help: [Take over the apps you already run](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/take-over-your-apps.md).

### Security
- **Only image sites:** Starboard fetches covers only over https from TMDB, Open Library and Cover Art Archive, or from Reelix itself, and follows a redirect only to another of those sites. Adding from Search sends Reelix only the identifier from Reelix's own lookup and the choices in the panel.

## [0.12.2] (8 November 2026)

Moving your apps into Reelix works with any qBittorrent user name, and each step says what happened under its own buttons.

### Fixed
- **qBittorrent's user name:** Moving your apps into Reelix signed in to qBittorrent as admin, so a qBittorrent with another user name refused the right password. Starboard now reads the user name from qBittorrent's own settings, shows it, and gives it to Reelix. Help: [Move from Radarr, Sonarr and the others to Reelix](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/move-your-apps-to-reelix.md).
- **Messages under each step:** On Apps you already run, what happened after Show what moves, Move them into Reelix or Take over my apps appeared at the end of the section, out of sight. Each step now says it under its own buttons.

### Security
- **One line of qBittorrent's settings:** Starboard reads only qBittorrent's user name from its settings file, into a private temporary folder that it removes straight after.

## [0.12.1] (8 November 2026)

Reelix's set-up finishes after a start from the browser, and can be finished from Settings, Reelix.

### Added
- **Finish setting up Reelix:** When Reelix runs but its set-up did not finish, Settings, Reelix shows Finish setting up Reelix: your password makes its admin account, Starboard's key, its folders and its download apps. Your install sends you there when it is needed. Help: [Take over the apps you already run](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/take-over-your-apps.md).

### Fixed
- **Reelix set up after a start from the browser:** Reelix stayed waiting for its admin account when Install apps started the apps from the browser, because only the installer read its one-time set-up token. Starboard now reads the token from Reelix's log itself, through its Docker access.

### Security
- **Only the logs it needs:** Starboard reads only the Reelix log, and qBittorrent's only when it installed qBittorrent itself; the token and password go in data/stack/reelix-setup.json, which only you can read and which is removed once the set-up is done.

## [0.12.0] (8 November 2026)

Take over the apps you already run, move them into Reelix, and roll back if you need to.

### Added
- **Take over the apps you already run:** On a server set up by hand, Settings, Your install, Apps you already run takes your apps into Starboard. Their settings are copied, never moved, and each keeps its ports, the folders it uses, its devices, its own settings, its version and whether it runs through the VPN. Help: [Take over the apps you already run](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/take-over-your-apps.md).
- **Move your apps into Reelix:** The same page moves Radarr, Sonarr, Lidarr, Readarr, Prowlarr and Seerr into Reelix through Reelix itself, with each key read from the app, the keys Prowlarr hides read from its database, and qBittorrent connected with its password. Help: [Move from Radarr, Sonarr and the others to Reelix](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/move-your-apps-to-reelix.md).
- **Roll back or keep it:** Before anything stops, Starboard tags every app version and copies your Compose file and its own set-up. Roll back starts your old apps again exactly as they were; Keep it puts the way back aside without deleting anything. Help: [Take over the apps you already run](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/take-over-your-apps.md#roll-back).

### Changed
- **Your install keeps what each app relies on:** A later change in Your install keeps the ports, folders, devices and settings of apps Starboard took over, from data/stack/kept.json. Help: [Change your install](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-your-install.md).

### Fixed
- **Reelix problems on the page:** When Reelix answers with a problem, the page now says what Reelix said, instead of Something went wrong.
- **Coming up on a phone:** With many filter chips, such as Reelix radio, the page scrolled sideways on a phone. The chips now scroll in their own row.

### Security
- **Password for every change:** Taking over, rolling back, keeping and moving into Reelix each ask for your password again, and run one at a time with the other changes to your apps.
- **Secrets stay private:** Passwords and keys an app had in its Compose file go only in data/stack/.env, which only you can read; data/stack/kept.json holds their names, never their values. Prowlarr's database is read into a private temporary folder and removed straight after.
- **Old folders are never written to:** The takeover only reads your old settings folders, refuses a settings folder inside one of them, and never copies over a folder that has files.
- **zlib in the image:** The image takes Alpine's zlib 1.4 when it is built, which fixes CVE-2026-4738 (medium) in the base image's zlib 1.3.2.
- **Reelix joins your networks only for the move:** To read your old apps, Reelix joins their Docker networks for the move and leaves them afterwards, even when the move fails.

## [0.11.0] (8 November 2026)

Radio in Starboard, one terminal frame with error numbers, help in slide-outs, and the fixes from the terminal checks.

### Added
- **Radio in Starboard:** Install apps has a Radio group, which makes the radio folder and sets it up in Reelix. Episodes of the radio shows and podcasts you follow show in Coming up, radio downloads show in Downloads, and Discover links to the same search in Reelix radio. Help: [Follow radio shows and podcasts](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/follow-radio-shows.md).
- **One frame for the terminal:** The installer and the Run first script draw in the same frame, follow the same terminal rules, and redraw when the window changes size while a question waits.
- **Error numbers in the terminal:** Every way the Run first script and the installer can stop has an error number, such as RF-11, on a line of its own with the address of the help page that explains it. Help: [Run first and installer error numbers](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md).
- **Help in slide-outs:** Help with this step opens the help article in a slide-out beside the set-up, with square help icons, instead of a new tab.
- **Help pictures for the terminal:** Run first, the terminal set-up and the error numbers each have three marked-up pictures, and Install apps has pictures of what to set up, the VPN step and the Check table.

### Changed
- **Install apps:** The VPN step lists each provider with its site, required answers have a star, the Check table is tidier, and starting the apps shows how many are installed, then running. Help: [Install apps with Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-apps.md).
- **Numbered answers:** Yes or no questions in the terminal have numbered answers with the recommended one first, in place of [y/N].
- **App by app after Basics:** Choosing app by app after Basics starts with the Basics groups ticked.
- **Storage counts radio with audiobooks:** A folder named radio or podcasts now counts as Audiobooks and radio, not Everything else. Help: [Check free space and what is using it](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/check-storage.md#sort-the-space-by-type).
- **Storyarr 0.7.0:** Install apps installs Storyarr 0.7.0, which finds radio from torrent and Usenet sources.
- **The Screen logo:** The set-up and sign-in pages, the browser tab and the app use the Screen logo.

### Fixed
- **Run first on newer Ubuntu:** The script stopped with sg: command not found straight after allowing your user to use Docker. It now works without sg.
- **Running the installer straight after Run first:** The installer stopped with IN-22 because the docker group was not active yet. It now starts itself again inside the group. Help: [IN-22](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#in-22).
- **Keys typed between questions:** Keys pressed while a job runs or between questions no longer move the lines or show a question twice.
- **The sudo password at the end:** Applying the changes asks for your sudo password in the window when sudo has forgotten it, instead of stopping with IN-16. Help: [IN-16](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#in-16).
- **Text cut at the edge:** Stop messages, the checklist hint, the sign-out line, long questions and help addresses wrap instead of running off the edge.
- **A job that keeps failing:** A failing job is tried three times, then offers Show the details and Carry on.

### Security
- **Checks:** The unit tests and the help check ran on this release, and the terminal set-up was checked on fresh Ubuntu 26.04 machines at four window sizes. Nothing in this release changes what Starboard can reach.

## [0.10.0] (7 November 2026)

Reelix in place of the separate media apps, set up for you; Basics, Full install or Everything; NZBGet; and the fixes from testing on four systems.

### Added
- **Reelix in Install apps:** For a new server, Install apps installs Reelix, one app for films, series, books, audiobooks, music and radio, in place of Radarr, Sonarr, Lidarr, Bookshelf, Prowlarr and Seerr. Servers that run those keep them. Help: [What Reelix is](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/what-is-reelix.md) and [Install apps with Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-apps.md).
- **Reelix set up for you:** After the apps start, Starboard makes Reelix's admin account with your Starboard password, a manager key for itself, the library folders, and qBittorrent with a password of its own, then shows Reelix's queue and calendar on your dashboard.
- **Basics, Full install or Everything:** Both set-ups start by asking which install you want. Basics is Reelix Lite, Jellyfin, Audiobookshelf, subtitles, and qBittorrent and NZBGet through a VPN; Full install adds the full Reelix and more; Everything is every app. An app also brings what it needs. Help: [Basics, Full install and Everything: what each one has](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-types.md).
- **NZBGet:** NZBGet is the Usenet app in every install, lighter than SABnzbd, which Full install and Everything offer instead. Starboard makes up its password, sets its folders and connects it to Reelix, and shows its queue and speed, and pauses it with download hours. Help: [Choose a Usenet provider and add it](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-a-usenet-provider.md).
- **Settings, Your install:** Shows what is installed and changes it either way: a bigger or smaller install, NZBGet or SABnzbd, Reelix Lite or full. Your Usenet servers move across from SABnzbd to NZBGet, and the page explains each step. Help: [Change your install](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-your-install.md).
- **Usenet providers for SABnzbd:** When you choose SABnzbd, both set-ups list some Usenet providers. They are affiliate links, marked Ad, and the step says to download only files you have the right to. Help: [Choose a Usenet provider and add it](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-a-usenet-provider.md).
- **Help for moving to Reelix:** A new help page says what moves from Radarr, Sonarr and the others into Reelix, what does not, and what to type in afterwards. Help: [Move from Radarr, Sonarr and the others to Reelix](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/move-your-apps-to-reelix.md).
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
- **Ubuntu 26.04's sudo:** Ubuntu 26.04 shows a star for each letter of the password; the help said nothing shows. Help: [The terminal: typing commands](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/the-terminal.md#when-a-command-asks-for-your-password).
- **qBittorrent 5.1.** Reelix is connected to qBittorrent again: qBittorrent 5.1 answers a right password differently, so the set-up said it was wrong.
- **NZBGet on the dashboard and in Reelix.** NZBGet is found and added to the dashboard, its downloads finish in the media folder, and series go to a tv category Reelix uses.
- **SABnzbd.** SABnzbd works as the Usenet app: its own port 8085 beside qBittorrent behind the VPN, the names Reelix uses, downloads in the media folder, a key Starboard made up, and its newer address for Starboard's checks.
- **Changes without Docker access.** After you run the command Settings, Your install shows, Starboard finishes the change: Reelix, the dashboard and moving your Usenet servers. Help: [Change your install](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-your-install.md#if-starboard-has-no-docker-access).
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
  go back. Help: [Update Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-starboard.md#find-out-whether-an-update-is-out).
- **Restore:** Settings, Updates, Restore puts back a copy of your settings that Starboard saved, or one from a file,
  and shows the command to go back to the version before. Help: [Restore a saved copy of your settings](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/restore-a-saved-copy.md).
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
  Show the details shows more of the log, wrapped, not cut off. Help: [RF-10](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first-errors.md#rf-10).
- **The quick start without curl:** Ubuntu Desktop does not include curl, so the README and the help now give the
  same command with `wget`, which Ubuntu, Linux Mint and Debian include. Help: [Quick start: one command sets up everything](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/guides/quick-start.md).
- **Disk health installs what it needs:** choosing disk health no longer stops with "install smartmontools first":
  the installer installs smartmontools itself (sudo asks for the password), and finds it in /usr/sbin, which is not on
  every user's path. Help: [Check your disks' health](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/check-disk-health.md).

## [0.9.1] (5 November 2026)

Updating works again after a long gap.

### Fixed
- **Updating after a long gap:** `./update.sh` stopped just after "What changed" when more than 30 changes had come
  since your version. It now lists 30 and says how many more. Until you have this version, Update Starboard in the help
  has the steps to update by hand. Help: [Update Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-starboard.md#if-it-does-not-work).
- **Typing the Run first script's command:** the help and README now say that the address is case-sensitive after
  the repository's name, and what a 404 means. The terminal basics page has a new section, Capital letters matter. Help: [The terminal: typing commands](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/the-terminal.md#capital-letters-matter).

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
  only reports. Find out more in **Set up everything with the Run first script**. Help: [Set up everything with the Run first script](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/run-first.md).
- **How to start, in both set-ups:** the browser set-up guide and the terminal set-up now start with the same
  question, New install, Move from apps you already run, or Restore a backup, with the recommended answer chosen from
  what Starboard finds on the computer. Restore takes a backup file and restores it after the password.
- **Storage, in both set-ups:** for a new install, where your media goes: this computer's main disk, a separate disk
  or a pool of several disks, with the media folder made for you when the apps start. Install apps uses the folder
  chosen there.
- **Alerts and disk health, and how much Starboard does, in the terminal set-up,** as in the browser.
- **Keyboard help for commands:** The terminal: typing commands now says where `|`, `~`, `\`, `"`, `@`, `$` and `&` are
  on US, UK and Ireland, German, French and Spanish keyboards, and warns that the `¦` key on a UK keyboard is a
  different character. The Run first script's command also comes in a version without `|`. Help: [The terminal: typing commands](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/the-terminal.md#symbols-that-are-in-different-places-on-different-keyboards).
- **Connect to the internet from the terminal:** a help topic for a server with no desktop: check it is online,
  connect a network cable (Debian included), or Wi-Fi with NetworkManager or on Ubuntu Server. The guide from a bare
  computer links to it after installing Linux. Help: [Connect to the internet, by cable or Wi-Fi](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/connect-to-the-internet.md).

### Changed
- **One order for every step,** the same in the browser and the terminal: your password, how to start, storage, your
  apps, VPN, the check, connecting the apps, download hours, alerts and disk health, how much Starboard does. Each
  thing is decided before what depends on it.
- **The installer asks less on a new install:** only your home network and Docker access, and drive pools when there
  is more than one drive. The dashboard's name moves into the set-up, beside the password. Free space for the media
  folder, the Live TV folder and disk health are chosen in the set-up and applied at the end with one installer
  command, which the Run first script runs for you. Help: [What the installer asks, and what each answer means](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/what-the-installer-asks.md).
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
  throwaway VM with blank virtual drives (`tools/vm/vm.sh pool debian`). Find out more in **Add a drive to the pool**. Help: [Add a drive to the pool](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/add-a-drive-to-the-pool.md) and [What a drive pool is](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/what-is-a-drive-pool.md).
- **Set up in the terminal, with no browser** (DASH-86): `./install.sh --terminal` carries on once Starboard is
  running and asks the set-up questions in the same terminal: your password (typed hidden, with no setup code
  needed on the server itself), the apps for your media server (what you want, then the apps, folders and VPN
  details) and download hours. Enter takes the recommended answer, `?` shows help, `b` goes back a step with the
  last answers as the defaults, and `q` stops. It uses Starboard's own API, so every answer is checked as the
  browser checks it. Each step starts on a cleared screen with a heading box ("Starboard | step"), a progress bar
  and a menu on the bottom line; help opens as a box over the dimmed step. With `STARBOARD_PLAIN=1`, `--plain`, a
  small window or no terminal, it prints plain lines that never clear or redraw, which suit software that reads
  text aloud; `NO_COLOR` keeps the boxes without colour. Run it again with `python3 -m starboard.terminal_setup`.
  Find out more in **Set up Starboard in the terminal, with no browser**. Help: [Set up Starboard in the terminal, with no browser](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-in-the-terminal.md).
- **Feedback from the terminal set-up** (DASH-91): `f` at any question sends Snaglist's report about that step,
  in a box over it: what it is about (Snaglist's seven kinds), one or two of Snaglist's questions, then the whole
  report before any choice to send. It is a pre-filled GitHub issue with the step, Starboard's version, the system,
  the window size and the last error. Answers to the set-up, passwords, VPN details and the setup code are never
  in it, and email and network addresses, user names in paths and anything like a key are replaced. Send it as a
  QR code drawn in the terminal (a new standard-library encoder, `starboard/qr.py`), as the link, or saved to a
  file. Plain mode never draws a QR code. After a failure, `r` reports it with the error filled in. Help: [Set up Starboard in the terminal, with no browser](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-in-the-terminal.md#send-feedback-from-the-terminal).
- **What is new in Reelix:** on **Apps**, **Updates**, **What is new** beside **Update** lists the changes in a
  waiting Reelix update, from Reelix's own changelog, under Added, Changed, Fixed and the other kinds of change.
  After Reelix's version goes up, a notice on the Apps page and on Updates says so, with **What is new** for the
  versions it skipped. The changelog is downloaded only when you open What is new, and kept for 6 hours. Find
  out more in **Update your apps**. Help: [Update your apps](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-your-apps.md#what-is-new-in-reelix).
- **A guide from a bare computer:** the help centre's new guide, Get Starboard up and running, goes from
  installing Linux to Docker, then splits into a path for the browser and one for the terminal only. New topics:
  Install Linux on a computer, and Ask an AI assistant to help you set up, with prompts for a chat assistant and
  for one on the server. Help: [Get Starboard up and running, from a bare computer](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/guides/get-up-and-running.md) and [Ask an AI assistant to help you set up](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/ask-an-ai-for-help.md).

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
  keeps its address. Help: [What Starboard is](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/what-is-starboard.md#find-your-way-around).
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
  **Jellyfin**. What Starboard is has a new part, Find your way around. Help: [What Starboard is](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/basics/what-is-starboard.md#find-your-way-around).

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
  reports, and the older notes, are listed under Testing with Mark fixed, Remove and Download all. Help: [Send feedback about a page](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/send-feedback.md).

### Changed

- **Errors show where they happened:** a problem saving a setting, renaming a category or running an action
  now shows beside that control, in words, and clears on the next try. An error with nothing on the page to
  belong to is an error toast that stays until you close it (it used to fade like an information toast).
- **Apps, Updates:** the button says Check until the first check, then Check again.
- **Watch history:** a watch history file can now be up to 80 MB (was 512 MB): reading one takes about 4.5 times
  its size, and 80 MB is more than 250,000 films and episodes. Help: [Import watch history into Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/import-watch-history.md).

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
  restart with the ready-made image) removes the password, signs everyone out and starts with a new setup code. Help: [Reset a forgotten password](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/reset-a-forgotten-password.md).
- **Watch history:** applying it lists the films and episodes not in Jellyfin yet. A history file over 512 MB is
  refused before it uploads. Help: [Import watch history into Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/import-watch-history.md).
- **Tests:** backup and migration round trips, browser journeys (`tools/journeys.sh`), install tests in VMs on
  Ubuntu, Debian, Fedora and 64-bit ARM (`tools/vm/vm.sh`), and `docs/TESTING.md` with measured system use.
- **Testing aid:** Note issues (Settings, General) adds the shared Note an issue button to every page.

### Changed

- **Messages:** confirmations are cards in the corner (up to three, with Close); problems use the information
  style. Settings pages show "Saved at" and the time beside Save name, Save where alerts go, Save address and
  Change password. Words follow the shared content guide: settings are activated and deactivated.

### Fixed

- **Watch history:** a second run no longer counts episodes it applied before as missing. Help: [Import watch history into Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/import-watch-history.md).
- **Restore:** backups from before 0.6.0 are brought up to date; a design or choice that no longer exists goes
  to the default; an app of a kind Starboard no longer knows becomes a plain link. Help: [Back up and restore Starboard's settings](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/back-up-settings.md).
- **Disk health:** the page script works again (broken since 0.7.0).
- **Apps on a phone:** the Apps page works at 175% text.
- **Ready-made image:** Docker access works, as it needs the socket's group (`group_add` in `compose.image.yaml`). Help: [Change what Starboard can access](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-what-starboard-can-access.md#if-you-used-the-ready-made-image).
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
  columns line up down the page; and each row's cells sit on the middle of the row. Help: [Update your apps](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-your-apps.md).

### Fixed

- **Long API keys:** keys were cut to 200 characters when saved, so Audiobookshelf (whose keys are about 211
  characters) refused its key. Keys up to 2000 characters are now kept whole. If Audiobookshelf says the key is
  wrong, paste it again in Settings, Manage apps. Help: [Find an app's API key](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/find-an-api-key.md).
- **Log:** a connection that stayed idle until it timed out no longer writes an error to Docker's log.

## [0.7.0] (2 November 2026)

### Added

- **Install apps, for people who have never set up a media server:** The changes are listed below. Help: [Install apps with Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-apps.md).
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
  client is added switched off. Indexers: add the new app in Prowlarr. Help: [Copy settings from one app to another](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/copy-app-settings.md).
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
- **Categories:** renaming or removing a category is one save. Help: [Organise apps into categories](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/organise-categories.md).
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
  their progress once they are scanned in. Help: [Copy listening progress into Audiobookshelf](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/copy-listening-progress.md).
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
  Problems and Detailed, a search, Download and Delete logs. Help: [Read the log and report a problem](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/read-the-log.md#read-the-log).
  - Personal details are removed before anything is written, in both modes: passwords, API keys and tokens, IP
    addresses, host and computer names, email addresses, user names in folder paths and the dashboard's name.
- **Settings, General, Logs:** keep logs for 7 days to a year (60 by default); older days are removed once a day,
  with no thread of its own. **Detailed logging** (Off, For 24 hours, Until I turn it off) adds each page request
  and each call to your apps, and the full detail of errors. Help: [Read the log and report a problem](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/read-the-log.md).
- **Report a problem:** turn on detailed logging, do the thing again, then Copy the details (versions, how it
  runs, what is switched on, the kinds of apps, recent entries) and Open a new issue on GitHub, which uses a new
  issue template. Help: [Read the log and report a problem](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/read-the-log.md#report-a-problem).

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
  build. Help: [Install Starboard from the ready-made image](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-from-the-ready-made-image.md).

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
  Prowlarr, SABnzbd and Seerr from their own settings files, if you tick "Fill in API keys for me". Help: [Search for apps already on your server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/search-for-new-apps.md).
  - It runs only when you press the button: no background work.
- **System, Storage** shows each pool as a bar (how full) and a ring (what fills it) by type: TV, films,
  audiobooks, music, books and comics, downloads waiting and everything else, with free space. Also each drive
  in the pool (fullest first), space used over time with a forecast of when it fills, and the biggest series and
  films. Every chart has a table view. Help: [Check free space and what is using it](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/check-storage.md).
  - Sorting by type reads every file name, so Settings, Performance (and the set-up and upgrade guides) choose
    when: only when you press Work it out (the default), when you open Storage if over a day old, every night or
    every week at 3 am, or off. It now reads a pool once, skipping its drives, and stays on one file system: on
    the test server, 105 seconds for 30 TB, down from reading it twice.
  - A daily record of used space (on; nothing noticeable) feeds the forecast. Storage page updates: only when you
    press Check again (the default), or every minute or 5 minutes while the page is open.
- **Install apps** (Settings, Manage apps, or the first step of the set-up guide): tick groups such as Movies,
  TV, Music, Ebooks, Audiobooks, Comics, Watching, Downloads, VPN and Subtitles, and change the apps inside each.
  Apps already running are left alone; ports in use move to the next free one; each app shows its memory use. Help: [Install apps with Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-apps.md).
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
  and what it costs. Changing anything by hand makes it Custom. Help: [Make Starboard use less of your server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/make-starboard-lighter.md).

### Changed

- **Background threads** exist only while their feature is on: history, watching, download hours and the Jellyfin
  jobs each start when turned on and end when turned off. With Small server, Starboard runs only its web server. Help: [Make Starboard use less of your server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/make-starboard-lighter.md#background-work).
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
  server can keep only what it needs. The access list on About and updates says the same for each item. Help: [Make Starboard use less of your server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/make-starboard-lighter.md#what-each-item-costs).

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
    numbers, and white logos made with Pillow (switchable). Needs Jellyfin's Live TV folder (`./install.sh`). Help: [Set up free Live TV in Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-live-tv.md).
  - **Import watch history** into Jellyfin from a Plex database file, a Plex server, Emby, another Jellyfin or a
    history file, with account matching; applied once per item, and every hour if you choose. Help: [Import watch history into Jellyfin](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/import-watch-history.md).
  - **User defaults** for every Jellyfin user. Help: [Give every Jellyfin user the same defaults](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/jellyfin-user-defaults.md).

### Changed

- **Apps, Other services** lists Starboard's own jobs and whether each is on. Help: [Add a background service](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/add-a-background-service.md).
- **Set-up** offers the Jellyfin jobs when it finds Jellyfin.
- **Credits:** Pillow and the data sources are credited in THIRD-PARTY.md.

## [0.2.0] (2 November 2026)

Lightweight first: a dashboard for smaller servers that uses very little processor time and memory (about
14 MB while idle). Every page now uses the component library shared with Storyarr.

### Added

- **Alerts:** to ntfy, Gotify or a webhook when an app stops answering, a disk has a problem or gets full, a
  download is stuck, a backup fails or a certificate runs out; uptime history for each app; a weekly
  summary. Off until you turn it on. Help: [Activate alerts](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/activate-alerts.md) and [Get a weekly summary](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/weekly-summary.md).
- **Apps:** small numbers on each card; Updates is its own page again, with each app's container, Check for
  updates, Update all and Update (needs Docker access).
- **Downloads:** download hours for qBittorrent and SABnzbd, with Resume, Pause and Follow the hours;
  speeds and the VPN's state (Gluetun); Finished this week; Requests from Seerr with Approve and Decline. Help: [Download only at certain hours](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-download-hours.md) and [Approve or decline requests](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/approve-requests.md).
- **Coming up:** posters, a List or Calendar view, and how far ahead to look. Help: [Find out what is coming up](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/coming-up.md).
- **System:** Jellyfin's state, what is playing and what was added; server jobs with Run now; 30-day disk
  temperatures and the drive's own log; Read disks now; what is using the space; every drive; each app's
  processor and memory on Monitor; certificate expiry on Network.

### Changed

- **Lighter:** pages are compressed and the browser keeps them until they change; several tabs or devices
  share one answer from each app; hidden tabs stop refreshing; posters come from your own apps, kept for a
  week; background work starts only when needed.
- **Installer:** explains each step, and asks before each kind of access (home network, Docker for app
  updates, per-app use, folders for free space, Disk health). Run it again to change your answers.
  Settings, About and updates lists what Starboard can access, with the switch or command to change each. Help: [What the installer asks, and what each answer means](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/what-the-installer-asks.md) and [Change what Starboard can access](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-what-starboard-can-access.md).
- **Settings:** one column; Manage apps and the access list show each state as an icon beside the name;
  a new Alerts page; Coming up and Download hours settings in General.

## [0.1.8] (2 November 2026)

### Added

- **Backup and restore:** an option to include a rebuild prompt for an AI assistant with the server backup
  (the job is asked for `backup-with-prompt`). The page says what the server backup covers. Help: [Back up the whole server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/back-up-the-server.md).

## [0.1.7] (2 November 2026)

### Added

- **Storage:** each folder has a tag with its filesystem, such as ext4, NTFS or mergerfs.

## [0.1.6] (2 November 2026)

### Added

- **System, Backup and restore:** download Starboard's settings as a file, restore from a file or from a copy
  Starboard saved, and start the server's own backup job and see its result and files. Downloading or
  restoring needs your password again. Help: [Back up and restore Starboard's settings](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/back-up-settings.md) and [Back up the whole server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/back-up-the-server.md).

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
- **Disk health:** reads SMART reports saved by a small job on the server (`deploy/install-smart.sh`). Help: [Check your disks' health](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/check-disk-health.md).
- **Your own folders and disks** go in `compose.override.yaml`, which updates leave alone. Help: [What the installer asks, and what each answer means](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/what-the-installer-asks.md#your-own-folders-composeoverrideyaml).

## [0.1.4] (1 November 2026)

### Changed

- **New logo, Tile board:** three tiles and a star. In dark mode the star is lighter. Used in the header, the
  phone menu, the browser tab and the home-screen icon.

## [0.1.3] (1 November 2026)

### Added

- **Dashboard name:** the installer and the setup page ask you to name your dashboard. Change it in Settings, General.
- **App icons:** each app's own icon on its card, from the dashboard-icons collection. Starboard keeps a copy, so icons
  still show without the internet. Choose another icon in the app's settings. Help: [Change an app's icon](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/change-an-icon.md).
- **Apps are grouped by category:** Watch, listen and request; Find and organise; Search and download;
  Dashboards and tools. New apps get a category chosen for them; change it in the app's settings. Health
  first still puts apps that are not responding at the top. Help: [Organise apps into categories](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/organise-categories.md).
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
  a day. With it, you stay signed in for the number of days set in Settings, Security. Help: [Create your password and sign in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/create-your-password.md).

### Changed

- **Passwords** need 10 characters or more (was 12). Help: [Create your password and sign in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/create-your-password.md).
- **The setup code** stays the same when Starboard restarts or updates, so the code the installer printed keeps
  working until a password is set. Help: [Find the setup code](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/find-the-setup-code.md).

## [0.1.0] (1 November 2026)

### Added

- **Pages:** Apps, Search, Downloads, Coming up, System and Settings, each on its own page.
- **Search:** Search Sonarr, Radarr, Lidarr and Readarr at once and add what you find. Help: [Search for and add films, series, music and books](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/search-and-add.md#without-reelix).
- **Five designs:** Health first (the default), Tiles, Shelf, Command and Status board, plus the Display and
  accessibility panel. Help: [Choose a design for the Apps page](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-a-design.md) and [Change text size, theme and other display settings](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/display-and-accessibility.md).
- **Installer and updater:** installer (Docker or systemd) and updater with backup and automatic roll-back. Help: [Install Starboard with the installer](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/install-with-the-installer.md) and [Update Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-starboard.md).
- **Sign-in:** password sign-in with a one-time setup code; API keys never reach the browser. Help: [Create your password and sign in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/create-your-password.md).
- **Home network:** open it from phones and other computers on your home network, or switch that off in Settings so only the
  computer it runs on can connect. Docker uses host networking for this. Help: [Choose who can open Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-who-can-open-starboard.md) and [Open Starboard from a phone or another computer](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/open-from-another-device.md).
- **Phones:** phone layout on every page; add it to your home screen.
- **App addresses:** each app's home address and outside address on its card, each with a copy button. Both are on by default;
  turn them off in Settings, General. Apps saved as 127.0.0.1 open on the address your browser used, so they
  work from a phone.
- **Downloads:** show the download client's own state, so a paused client shows Paused. Help: [Pause, resume and remove downloads](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/manage-downloads.md).

[Unreleased]: https://github.com/TheMightyTRex/starboard/compare/v0.16.5...HEAD
[0.16.5]: https://github.com/TheMightyTRex/starboard/compare/v0.16.4...v0.16.5
[0.16.4]: https://github.com/TheMightyTRex/starboard/compare/v0.16.3...v0.16.4
[0.16.3]: https://github.com/TheMightyTRex/starboard/compare/v0.16.2...v0.16.3
[0.16.2]: https://github.com/TheMightyTRex/starboard/compare/v0.16.1...v0.16.2
[0.16.1]: https://github.com/TheMightyTRex/starboard/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/TheMightyTRex/starboard/compare/v0.15.5...v0.16.0
[0.15.5]: https://github.com/TheMightyTRex/starboard/compare/v0.15.4...v0.15.5
[0.15.4]: https://github.com/TheMightyTRex/starboard/compare/v0.15.3...v0.15.4
[0.15.3]: https://github.com/TheMightyTRex/starboard/compare/v0.15.2...v0.15.3
[0.15.2]: https://github.com/TheMightyTRex/starboard/compare/v0.15.1...v0.15.2
[0.15.1]: https://github.com/TheMightyTRex/starboard/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/TheMightyTRex/starboard/compare/v0.14.1...v0.15.0
[0.14.1]: https://github.com/TheMightyTRex/starboard/compare/v0.14.0...v0.14.1
[0.14.0]: https://github.com/TheMightyTRex/starboard/compare/v0.13.2...v0.14.0
[0.13.2]: https://github.com/TheMightyTRex/starboard/compare/v0.13.1...v0.13.2
[0.13.1]: https://github.com/TheMightyTRex/starboard/compare/v0.13.0...v0.13.1
[0.13.0]: https://github.com/TheMightyTRex/starboard/compare/v0.12.2...v0.13.0
[0.12.2]: https://github.com/TheMightyTRex/starboard/compare/v0.12.1...v0.12.2
[0.12.1]: https://github.com/TheMightyTRex/starboard/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/TheMightyTRex/starboard/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/TheMightyTRex/starboard/compare/v0.10.0...v0.11.0
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
