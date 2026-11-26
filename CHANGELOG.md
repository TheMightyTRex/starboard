# Changelog

All notable changes to Starboard are listed here, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), with dates written as in the TRex Design System.
Version numbers follow [Semantic Versioning](https://semver.org/) loosely: before version 1.0.0, a patch release may also
add features.

## [Unreleased]

### Added
- **A first sign-in for app plug-ins.** A plug-in can now set its app's first password, and the plug-in's page shows it once after you enter your Starboard password. Calibre-Web uses this from version 1.2.0. Find out more in the [manifest reference](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/developers/plugin-manifest-reference.md#a-first-sign-in-shown-once-first_sign_in).
- **A wizard for switching media server.** The media server tab in Settings, Apps has Switch with help, which says what moves, what cannot and what keeps working before anything changes. Find out more in [Choose your media server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-your-media-server.md).
- **Plex and Emby as kinds of app.** Manage apps, Add an app now lists Plex and Emby, each with its own form and connection test. If you go back to an older version, restore a Settings backup made before this change, because older versions do not know these kinds.
- **Phone apps for Calibre-Web.** Starboard now names and links the apps for reading Calibre-Web books on a phone: KOReader and Calibre-Web-Companion for Android, and Readest for iPhone and iPad. Starboard does not run them.
- **Several places for backups.** Settings, General, Backup and restore has Where backups go, which copies each backup to a folder, a network share or a cloud service. Starboard encrypts the server settings zip before it sends it and shows the key once, so store it.
- **A custom card for any service's JSON.** System, Apps, Other services has Custom cards, which show the fields you choose from any service's JSON on a dashboard card. Starboard asks only addresses on your home network unless you allow others. Find out more in [Show any service's JSON on a dashboard card](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/show-any-services-json-on-a-card.md).
- **A link to the plug-in store.** The README and the help topics The plug-in collection and Add a plug-in now link to the Stallboard plug-in store.
- **Plug-ins show the system they need.** A tag such as Jellyfin only, Plex or Emby, or Needs Reelix now shows on each plug-in that needs one. A manifest sets it with the new `requires` list (plug-in API 1.19).
- **One place for the media server.** Starboard can now ask any media server the same nine questions, with Jellyfin as the first and the default. Nothing you see changes.
- **Jellyfin as a built-in plug-in.** Jellyfin now has its own page in Settings, Plug-ins, and its address, key and settings stay where they were. You cannot deactivate or remove it while it is the media server in use.
- **Choose your media server.** Settings, Apps now lets you check your media server, choose another one and go back to the old one within 24 hours. Find out more in [Choose your media server](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-your-media-server.md).
- **Emby and Plex as media servers.** Both are now built-in plug-ins that the dashboard can show, read only for now. They cannot play, mark watched, show Live TV or use the Jellyfin tools.

### Changed
- **One tab for your media server.** Settings, Apps has one tab named for the media server in use, so the separate Media server tab and plug-in tab are gone. The old address still opens the right page.
- **Alerts and Performance are part of General.** Settings, General has new Alerts, Performance and Pictures tabs, and the old addresses still open the right page.
- **Lighter pages and quicker tests.** Page scripts and style sheets are now built without comments and blank lines, so a first visit sends about 38 KB less. The parallel test runner cuts a full run from 5 minutes 18 seconds to 53 seconds.
- **Two small savings.** The dashboard now asks for the settings once instead of twice. The Bring in progress page stops asking for its status while its tab is hidden.
- **Plain English pilot.** The README and the help topics Add an app and How lean Starboard is now use shorter sentences and the active voice.

### Fixed
- **An even row of controls on a Library item page.** On a radio show, the Following list now sits in the same frame and height as the buttons beside it, and every control on a film, series, artist, book, audiobook or radio show page is one height and wraps on a phone.
- **A full backup that was not made is now reported.** A scheduled backup with no saved backup password used to say it had run. It now says "No full backup was made", raises an alert and shows a warning in Settings.

## [0.31.0] (25 November 2026)

### Added
- **Host alerts.** Settings, Alerts has a section, The server itself, that warns about processor load, memory, disks, full folders, a changed outside address and stopped containers. Each is deactivated until you activate it.

### Fixed
- **A sparkline card with nothing to draw yet is accepted.** A plug-in that is not set up yet can now send an empty sparkline card, and the dashboard shows its note instead of an error.

## [0.30.0] (24 November 2026)

### Added
- **Stallboard as a catalogue source.** Settings, Plug-ins, Catalogue has a Stallboard catalogue tick that reads Stallboard's list once a day. Installing from it still shows what each plug-in asks for first. Find out more in [Add a plug-in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/add-a-plugin.md).
- **Why is this here? for found apps.** System, Apps, Other services has a button that says what found each app, and why an app was not found. Find out more in [Find out why an app is here, or why one was not found](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/why-is-this-here.md).
- **A health line on Reelix's card.** When some of Reelix's sites to search fail, its card on Apps says so, for example "1 of 3 sites failing". The words link to Sites to search. Find out more in [Choose the sites Reelix searches](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/choose-sites-to-search.md).
- **What is using the processor now.** System, Overview has a Busy now page that lists the containers and processes using the most processor and memory. It reads only when you open it or select Check again, and it cannot stop or change anything. Find out more in [Find out what is using the processor](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/find-out-what-is-using-the-processor.md).
- **Limit the logs shown.** System, Logs has Lines shown (50, 100, 200, 500 or 1,000) and an Alerts only switch. Download now saves only those lines, and Show older entries is gone. Find out more in [Read the log and report a problem](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/read-the-log.md).

### Fixed
- **The content check passes again.** Five lines that used words the check rejects are reworded, so the check finds none.
- **A plug-in's schedule control shows the real schedule.** The control now shows the schedule the job uses, not a guessed Sunday at 03:30.
- **Poster file names are checked outright.** A poster's file name is refused unless it resolves inside the posters folder.
- **The sign-in provider request has an allowlist test.** Starboard now tests the provider's address against public, home network and local addresses before and after it connects.
- **The full security scan needs no manual tuning.** It now runs ZAP with 8 GB and a 150 minute limit.
- **A browser journey tests an unanswered shadows setting again.** This changes a test only.
- **The Busy now test passes in a fresh container.** This changes a test only.

### Security
- **Poster file names stay inside the posters folder.** This answers CodeQL alerts 77 to 79, and GitHub now shows them as fixed.
- **The sign-in provider request tests an allowlist first.** This answers CodeQL alert 82, and GitHub now shows it as fixed. No alert was dismissed.

## [0.29.0] (23 November 2026)

### Added
- **Remove drop shadows.** A new switch in Display takes every drop shadow off every page for everyone on the server, which helps small and older computers. A new Reelix Lite install starts with shadows removed, and an older install keeps its shadows.

### Changed
- **Covers take the card shading everywhere.** Every cover now has the card's border, corner and shadow, in the Library, Discover, Search, Wanted, item pages, collections, books, plug-ins and the help centre. Activate Remove drop shadows if a small or older computer scrolls badly.

### Fixed
- **Updates offers a newer qBittorrent build.** An app kept on one LinuxServer.io build tag now gets the newer build on the same branch, and never changes branch. An app on a pinned tag whose new version is not healthy goes back to the old tag by itself.
- **Updates remembers its last check across a restart.** Apps, Updates now says when apps were last checked, even after Starboard restarts, and tries once more when the registry is busy.

### Security
- **Security scan.** Trivy, Gitleaks, Bandit, ShellCheck, Hadolint and ZAP found nothing to fix, and this release fixes no security problem. CodeQL alerts 77 to 79 and 82 are still open, neither fixed nor dismissed here.

## [0.28.0] (23 November 2026)

### Added
- **Two-step code and single sign-on for Starboard's own sign-in (DASH-512; owner, 22 November 2026, from the research shortlist: 239 votes for single sign-on on Jellyfin's own discussion):** Settings, Security, Sign-in methods, all off until you set them up. A two-step code (TOTP, RFC 6238): a QR code from Starboard's own encoder, 8 recovery codes shown once and kept only as hashes, the code asked after the password, wrong codes limited and every use written to the audit log. Single sign-on (OpenID Connect) with any standard provider: the authorisation code flow with PKCE, state and nonce checked, the ID token's RS256 signature checked against the provider's published keys with standard library code (no new dependency), and only your verified email, or a claim you choose, gets in. The client secret is kept on the server and never shown again. The password keeps working unless you turn it off on purpose, which needs single sign-on on and a working test; `./reset-sign-in.sh` on the server turns both off and allows the password (`./reset-password.sh` does too). Sessions are unchanged. Single sign-on does not ask for the two-step code: your provider decides whether you need a second step. Starboard's help says which claims are safe to match on (a verified email, or the provider's own stable subject, not a name people can choose). Listed in What Starboard can access. Help: [Set up a two-step code](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-a-two-step-code.md), [Set up single sign-on](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/set-up-single-sign-on.md) and [Get back in when sign-in is locked](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/get-back-in-when-sign-in-is-locked.md), each with marked-up pictures.

- **A hardware video conversion check (DASH-515; owner, 22 November 2026, from the research shortlist):** System, Overview has a Hardware video conversion panel. Select Test now and Starboard runs a 2 second test picture through Jellyfin's own ffmpeg, with Docker's exec on the Jellyfin container as the user Jellyfin runs as, once each for VAAPI, Intel Quick Sync, NVIDIA NVENC and software. It says which works, which device it used and, for each that does not, why (no /dev/dri, the device's group, a missing or too old driver, no NVIDIA card passed) and the fix in plain words. It runs only when asked, opens no media, writes nothing and changes no setting; the last result is kept in memory only and each run is written to the audit log. Help: [Test hardware video conversion](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/test-hardware-video-conversion.md), with three marked-up pictures.
- **Help pictures: at least 3 in 42 more topics (DASH-144, DASH-245; owner, 7 November 2026):** 129 new marked-up screenshots from made-up data, each marked with the step numbers of its article, for topics on alerts, apps, backups, disks and the pool, Security, Settings, the installs and Take over the apps you already run (DASH-245). Before this there were 67 topics with fewer than 3 pictures; now there are 25: install and terminal topics, and five whose screen the example server cannot show (`python3 tools/check-help.py --list-screenshots`). `tools/help-screenshots.sh` can now put an arrow on the side of a control that has room (`side` auto, and a side with no room falls back to one that has), keeps a picture that failed the mark-up check for you to look at (`KEEP_FAILED=1`) and makes pictures smaller without pngquant; the example server has two saved copies of the settings, so Restore has a list to show.
- **The developer help follows the code (DASH-150, DASH-275):** the plug-in manifest reference now names every field the check accepts, including a container's `entrypoint` and `files` and every field of a style (a table made from the JSON Schema), and `tests.test_developer_docs` fails when a field, a schema property or a route in the API description is missing from the help. `docs/help/llms-full.txt` holds the developer pages in one file for AI tools that read a single file, made by `tools/make_llms_full.py`, and `bash tools/check-api.sh` checks that it is up to date.

### Changed
- **A resting plug-in is never stopped while it works (DASH-516, lighter at rest):** a plug-in with `start: when_needed` now counts processor time as use as well as network traffic, so one that is converting a file or shrinking pictures stays up until it finishes. This makes it safe to let the helpers that only work on a schedule rest between jobs. `tools/measure-rest.sh` samples the containers and the disks at rest, read only, for before and after figures.
- **About, redone (DASH-408; owner, 13 November 2026: "highlighting all the accessibility features and another section talking about it being a lean system"):** Settings, Updates, About now has a section on every accessibility feature (always on, chosen in Display, and how it is checked) and a section on how lean Starboard is, with figures measured on the server on 22 November 2026: Starboard's container 33.6 MiB of memory, 0.12% of one processor over 3 hours 38 minutes, a 102 MB image and a median page of 132,649 bytes compressed, beside Reelix, Jellyfin and qBittorrent measured at the same time. Help: [How lean Starboard is](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/how-lean-starboard-is.md) says how each figure was measured, what it does not show, and how to measure your own server; `tools/measure-lean.sh` repeats the readings, read only.
- **The bug report form says where to find the version:** the Starboard version box now says to find it on Settings, then Updates, then About, in place of Settings, then About and updates. The guided GitHub issue form of 0.27.0 is otherwise as it was.

### Security
- **Single sign-on needs https (DASH-512 review):** The provider's address must be https, except for this computer itself (loopback), which is allowed for testing.
- **Junk requests cannot lock the owner out of the two-step step (DASH-512 review):** A flood of junk requests can no longer use up the tries of the two-step step, so it cannot lock the owner out.
- **The saved client secret is cleared when the provider changes (DASH-512 review):** Changing the single sign-on provider clears the client secret saved for the old one, so it is never sent to a new provider.
- **Single sign-on has its own limiter (DASH-512 review):** Single sign-on has its own limit on tries, apart from the password's, so one cannot use up the other.
- **One pinned address lookup, with an overall deadline (DASH-512 review):** The provider's name is looked up once and that address is connected to, with one overall time limit, so DNS rebinding and slow-drip servers are refused.
- **Sign-in starts are limited for each address (DASH-512 review):** Starting a sign-in is limited for each address, so one address cannot push other people's started sign-ins out.
- **Provider text is cleaned in logs (DASH-512 review):** Text that comes from the provider has control characters removed before it is written to a log, so it cannot forge log lines.
- **The provider connection refuses TLS older than 1.2 (DASH-512 review):** The connection to the sign-in provider refuses TLS versions older than 1.2 (a CodeQL finding).
- **Security scan:** Trivy (image and configuration), Gitleaks, Bandit, ShellCheck, Hadolint and ZAP signed out (58 passed) and signed in (112 passed) found nothing to fix.

## [0.27.0] (22 November 2026)

### Added
- **Filters on Discover's rows (DASH-301; owner, 10 November 2026):** the rest of the Search filters are done, so Discover's rows have them too. Above the rows, once the first row has loaded: In your library or Not in your library, a Year (by decade), Released or Not released, and a Language, each choice with how many covers it leaves, plus Clear filters. They combine, act on every row at once without asking Reelix again, say how many are shown, and are remembered for your account on every Discover page. A row with nothing left says so. Help: Filter the rows on a Discover page, with a picture.
- **Bulk actions on Activity, Wanted (DASH-524; owner, 22 November 2026: "I want the same bulk selections on Activity > Wanted"):** every row on the Wanted pages (Films, TV, Music, Books, Audiobooks) now has a box at its start, as the download queue has, and Select all in the toolbar ticks every row on the list; Shift and a tick selects a run of rows. A bar at the foot of the list says how many are selected and offers Search, Download now (for films and episodes while download hours pause downloads), Stop following and Clear selection. Stop following is new here: Reelix stops searching for the ticked titles, so they leave the list, and nothing is deleted; Starboard asks first and names how many. When the bar closes, focus goes to Select all, or to the list's words when it is empty, and the result is said. This replaces Select several, which only searched. Help: Act on several at once, in Find and get what is missing, with two pictures.
- **Discord support server link (DASH-526):** in the footer of every page, on About and updates, and in the help centre's footer, front page and the README, opening in a new tab.
- **Report a bug with a guided GitHub issue form:** New issue on GitHub now opens a form that asks what you did, what you expected, what happened, the Starboard version and how you run it, in place of a blank Markdown template. Blank issues stay on, and the chooser links to the Discord support server, where you can ask for help first.
- **Fallback posters (DASH-65):** when an app has no small posters of its own, such as Reelix, Coming up uses the picture address the app gives for the item, then TMDB's poster through the app's own search, each at a small size (TMDB's 185 pixels wide). With no picture anywhere, the item shows the app's icon, and the app is asked again after an hour. Help: [Find out what is coming up](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/coming-up.md).
- **Restore a full backup on this server (DASH-387):** on Settings, General, Backup and restore, each full backup in the folder has Restore beside it, so you can go back to an earlier day without a new install. A danger dialog says what is replaced and asks for the backup's password and your Starboard password. Nothing changes until both are right and the whole file has been read. Starboard first makes a full backup of how things are now, in the same folder and with the same backup password, and removes no older one to make room; then it stops the apps in the backup, puts Starboard's files and each app's settings and database back, and starts the apps again, saying each step on the page. Your Starboard password and sign-ins stay as they are. If Starboard stops part way, the apps are started at its next start. A backup from a server with another settings folder, or from a newer Starboard, is refused in words. Help: [Make and restore a full backup](docs/help/topics/make-and-restore-a-full-backup.md).
- **Each full backup is checked after it is made (DASH-381):** Starboard reads the new file back from the backup folder (its size, its start and its last part, opened with the key) and the list says Checked beside it. One that does not read back is not kept and the backup is reported as failed, with the alert for a failed backup; the older backups stay. The check reads at most 1 MiB, never the whole file.
- **Reelix's backups on another disk than its settings (DASH-386):** when the media folder is on another disk, Reelix's backups has Where Reelix keeps them: next to its settings, or in the media folder, each with its disk named. The backups already made move with the choice, and Restart Reelix beside it makes Reelix use the new folder. When both are on one disk, the page says so. Help: [Reelix's own backups](docs/help/topics/reelix-backups.md).
- **What was added, failed and upgraded across your apps, on one page (DASH-68):** Activity, History has a second page, Across apps. It lists what your apps added to the library, downloads and updates that failed, apps that stopped responding, and what was upgraded: a better copy of a film or episode, or a newer version of an app, a plug-in or Starboard. Added, Failed and Upgraded show one kind at a time, and Delete history empties the page. It is small on purpose: Starboard keeps the newest 500 entries in one file, usually under 100 KB. It costs nothing at rest: no new background check, entries are written by work Starboard already does, and each app's own history is read only when the page is opened. The weekly summary gains a line with the week's counts. Read [Check what was added, failed and upgraded across your apps](docs/help/topics/check-what-happened-across-your-apps.md).

### Changed
- **Pages load the design system's new components only where they are used (DASH-507; owner, 20 November 2026):** the thirteen new components had made every page about 22 KB heavier. The design system now splits twelve of them into parts (log viewer, tabs, combobox, sparkline and gauge, pagination, error summary, secret field, schedule picker, tag input, popover, alerts centre, command palette), and a page loads a part only when it uses it: the log viewer on System, Logs, tabs on a film, series, book or artist page, gauges on System, tag inputs on the Reelix settings pages, the secret field and error summary on the sign-in and security settings, and the error summary on Settings and Dispatcharr. The page banner and the tooltip stay in the core. Median page weight (compressed HTML, styles and scripts) fell from 148,865 to 132,649 bytes, 16.2 KB or 10.9%; Dashboard from 145,349 to 128,364. Needs design system pull request 16 (merged).
- **Search no longer repeats "Added" in a toast (DASH-309):** after Add in the legacy Search (without Reelix), the slide-out already says Added to the app in a notice, so the toast that said the same is gone; screen readers still hear it. This was the last open line of the design system audit of repeated items; every other line was already on main (checked 22 November 2026).
- **Download only what you have the right to, on About (owner, 22 November 2026):** the notice in Settings, About and updates now covers every download app, torrents as well as Usenet, in the same words as the help footer. Before, it named Usenet only.
- **Apps that are not responding are checked less often (DASH-66):** after 2 checks with no answer, Starboard waits 30 seconds, then 1, 2 and 4 minutes, and from then on 5 minutes between checks, so a stopped app costs the server little. The app's details say how often. Check again checks at once, and the first answer from the app puts it back to every check. Help: [An app shows as not responding](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/app-not-responding.md).
- **The updater's backup is smaller (DASH-384):** `./update.sh` and Update now leave fetched posters and icons, the logs and the Library's lists out of the copy of the `data` folder they make before each update, as a full backup without media does. Going back keeps the posters, icons and logs that are there. Help: [Update Starboard](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/update-starboard.md).
- **Set-up code, and a heading for each page (DASH-72):** the one-time code is "set-up code" everywhere, and the page where you enter it is called Create your password, so it no longer shares the heading Set up Starboard with the set-up guide. Help: [Create your password and sign in](https://github.com/TheMightyTRex/starboard/blob/main/docs/help/topics/create-your-password.md).
- **Reelix's backup settings follow the settings patterns (DASH-385):** how often Reelix makes a backup and how many it keeps are selects that apply at once, each with the saved note beside it, in place of two typed fields and Save the schedule. A choice that is not saved goes back to what it was. The dialog for restoring a Reelix backup says that nothing changes until Reelix restarts.
- **A full backup is put back only once it has been read to its end:** the set-up's Restore a backup now reads the whole file before it changes anything, so a damaged or cut-off backup leaves a new install as it was.

### Fixed
- **Install all updates (owner, 19 November 2026: "show the animated progress bar at 1% then increase as items get installed"; DASH-489):** on Settings, Updates, the moving bar shows from the moment the panel says Installing updates, and grows as each update ends. It no longer waits empty for the first update. The count read out stays the true one, such as "0 of 5 done".
- **The VPN card said No VPN on a server that uses one (owner, 22 November 2026):** when Gluetun was kept from an earlier set-up, Starboard had no connection to ask it, and the dashboard and Downloads said No VPN although every download went through it. Starboard now reads the VPN's own health check from its container, so the card says Connected or Not connected. If the state cannot be read, it says Not known, never No VPN.
- **Restoring a full backup stopped with "Permission denied":** the helper wrote Starboard's working copy of the backup readable by root only, and Starboard never runs as root, so the set-up's Restore a backup could not open it. Found by restoring for real, with Docker, on made-up data (`tools/try-full-restore.py`).
- **The footer check knew only some links (FOOT-01):** the browser journey that checks the footer on every page now expects the Discord support server link beside Help, so a page that loses it is found before a release.

### Security
- **Security scan:** Trivy (image and configuration), Gitleaks, Bandit, ShellCheck, Hadolint and ZAP signed out (58 passed) and signed in (112 passed) found nothing to fix.

## [0.26.0] (21 November 2026)

### Added
- **Bulk actions on the download queue (owner, 21 November 2026: "add a bulk selector to the list so can do bulk actions"):** on Activity, Downloads, Queue, each download has a box at the start of its row, and Select all in the toolbar ticks every download on the list; Shift and a tick selects a run of rows. A bar at the foot of the list says how many are selected and offers Try the import again and Ignore (for Reelix downloads waiting to import), Find another, Remove (with Block these releases) and Clear selection. Starboard asks first, naming how many it acts on, then sends each download to its app in turn, counts them in the bar and says what was done; any it could not do are named with the app's reason. A download the filter hides drops out of the selection. Screen readers hear the count and the result, and focus goes back to Select all, or to the empty list's words, when the bar closes. Design system: selection bar, selectable rows.

### Fixed
- **The red edge of a Remove section (design system, 21 November 2026; reported twice with Snaglist, on Plug-ins and on a plug-in's settings):** its grey head band ran out over the top of the red edge. The edge now runs the full height and is as wide as every other status edge.

### Security
- **Security scan:** Trivy (image and configuration), Gitleaks, Bandit, ShellCheck, Hadolint and ZAP signed out (58 passed) and signed in (111 passed) found nothing to fix.

## [0.25.0] (20 November 2026)

### Added
- **The design system's new components where they help (owner, 20 November 2026: "see where they can be used in all the apps"):** App logs on System, Logs is the log viewer: search marks each match and says how many, each level (Errors, Warnings, Info, Debug) shows its count and can be turned off, and Wrap lines and Download the lines (TXT) sit beside Copy; only the newest 1,000 matching lines are drawn. A new API key is in the secret field, hidden until Show, with Copy beside it. System, Overview shows processor, memory and temperature as gauges, the value in words in the middle and the status chip under it when it is busy or hot. A film's, series' or book's page uses the shared tabs. Reelix's lists of words (Extra file types, Countries to prefer, Formats to prefer, and list fields of sites and download apps) are tag inputs: Enter or a comma adds each word, and each has its own Remove button. Add an app and Dispatcharr's IPTV source list every missing field at once in an error summary at the top of the form, with a link to each. Status icons and copy buttons name themselves with the shared tooltip, which keyboards reach too.
- **Connection lost:** when the page cannot reach Starboard, such as while it restarts for an update, a banner under the header says so until Starboard answers again. It asks every 10 seconds, only while the banner shows.
- **Plug-ins can show a trend and send alerts (plug-in API 1.17, Starboard API 1.8.0), for the Uptime and status plug-in:** a plug-in card can be a sparkline, a small line for each thing it measures, such as a router's response times over the last day, with the latest, lowest and highest value in words beside it. Screen readers read the words, not the line, and the line follows light, dark, high contrast and forced colours. A plug-in given the new permission Send alerts can raise and clear its own alerts, which go where Starboard sends its own (ntfy, Gotify, a webhook, and the Notifications plug-in), once until cleared, and only while alerts are on; up to 30 new alerts an hour for each plug-in. Its alerts are forgotten when it is removed.
- **Everything you can do with a download that needs attention (owner, 19 November 2026: "For needs attention - I want a slide out with a list of things to do with the file including delete"):** on Activity, Downloads, Queue, selecting the name of a download marked Needs attention or Failed opens a wider slide-out. It says what is wrong in plain words, such as The files are inside archives, The episode is numbered differently, You already have a copy that is as good or better, Only a sample was downloaded or This download holds a program, not media, then lists every action that fits, each with one line on what it does and the likeliest one marked Suggested: Unpack the archives, then import; Choose the episode; Choose the film; Try the import again; Find another; Ignore; Remove from the list and keep the files; Remove and delete the files; and Remove, delete and add to the blocklist, for a fake or harmful release such as an .exe posing as an episode. Under them it lists what is in the download folder: each file, its size and whether it is media, a sample, an archive (each RAR set as one row), a program or something else. Deleting asks first and names the files, the folder and the space it frees; the result, such as "Removed. 14 files deleted, 1.4 GB freed.", is said by screen readers and gets focus. Starboard reads the folder and unpacks inside the app's own container through Docker, only when the slide-out opens; RAR needs the RAR tool in Reelix (from 10 November 2026), zip uses Starboard's Docker helper. What the download app leaves behind is deleted by Starboard only when the folder is the download's own. Without the Docker connection the slide-out still explains the messages and offers the other actions. Design system: action list.
- **Detailed log for backup connections (owner, 19 November 2026):** a setting at the end of Copies off this computer. When it is on, each Test connection, each copy and each step of connecting a cloud service writes the service's own words to Starboard's log (area backup connection), such as the reason Microsoft gave for refusing a sign-in. Lines with a password, a key, a token or a sign-in code are left out. Off unless chosen; it saves as soon as it changes.
- **Each step of connecting a cloud service is logged (owner, 19 November 2026: OneDrive's two-step check did not finish, and nothing showed why):** started, sign-in page ready, the address pasted back (or why it was not used), signed in, the folder list and the test, and where and why a sign-in stopped, ran out of time or was closed part way. Never the sign-in's address, code or token.

### Changed
- **New colour themes (design system, 20 November 2026):** Starboard's own style can be Blue, Teal, Dusk, Lime, Rose, Amber or Graphite. Dusk, Lime, Rose and Amber replace Indigo, Forest, Plum and Ember, and also tint the page and its cards in light and dark; high contrast keeps white or black. A server or browser that had an old one moves to its new one by itself (Indigo to Dusk, Forest to Lime, Plum to Rose, Ember to Amber), as does a settings backup from before.
- **A smaller image (optimisation review, 20 November 2026):** the image takes 101 MB on disk instead of 162 MB, and the download is 25 MB instead of 41 MB (amd64). Parts of Python that Starboard never uses are left out (pip's own copy in ensurepip, IDLE, lib2to3, the help() texts, Tk, the turtle demos and the files for building C extensions); the system is now one layer, so removed files and the packages that apk upgrade replaced are no longer kept twice; and the step that sets file permissions no longer copies every file a second time. Idle memory is the same, about 21 MB.
- **Each settings page loads only its own script:** settings.js (340 KB) was loaded by all 37 settings pages. It is now settings-core.js (41 KB) and one part for each group of pages, so a settings page loads 72 KB of settings script on average (23 KB compressed) instead of 340 KB (91 KB compressed). With their other scripts and styles, settings pages are 149 KB compressed instead of 218 KB.
- **The menus are kept once:** the header, side menu, phone menu and Display panel were written into each of the 96 pages (3.6 MB, 95% of the pages' size). Starboard now fills them in when it first serves a page and keeps the result in memory; the pages that reach the browser are the same. The web folder is 2.3 MB instead of 5.9 MB.
- **Pages, scripts and styles are served from memory:** inside the image they cannot change, so Starboard no longer checks a file and everything it links to on the disk for each request (about 81 microseconds each time before, under 1 now).
- **Hidden tabs stop asking:** the bring-in banner (every 10 seconds) and the progress of app updates (every 1.5 seconds) wait while the tab is hidden, and catch up as soon as it is shown again.
- **Radio downloads stuck at import:** Try the import again and Ignore now work for a radio episode too, from the page and from the API.
- **Signing in to a cloud service in this browser** says to finish every check the service asks for, such as a code from your phone or approving the sign-in in an app, and names the page that does not load ("This site cannot be reached") as the expected end.
- **Plug-ins can take files up to 100 MB (owner, 19 November 2026):** a file chosen on a plug-in's own page, such as a TV channel's holding slide, may be up to 100 MB instead of 60 MB. Each plug-in still sets its own limit.

### Removed
- **White Live TV channel logos (owner, 20 November 2026: "I dont need to turn the logos white anymore - can you remove it"):** every Live TV channel now shows its own logo in its own colours, as it did with White channel logos deactivated. A channel with no logo, or a photo for one, shows its name in Jellyfin instead of a drawn one. The White channel logos setting is gone from Settings, Apps, Jellyfin, from Settings, Performance, and from the Live TV plug-in, and Pillow (18 MB) is no longer in Starboard at all, nor downloaded. White logos already made stay in the Live TV folder's `logos` folder unused, and can be removed.

### Fixed
- **Plug-in pages (accessibility check of the Philips Hue and Uptime and status pages, 20 November 2026):** a plug-in's grouped lists no longer jump from the section's heading (h2) to h4: their headings follow on from the section's, in a group too. A list with its Change editor open, such as Philips Hue's schedules, is a valid list again (the editor is inside its list item, not in place of one). The tabs for a page's sections stay under the header while the page scrolls, in windows at least 768 pixels wide and 640 tall: scrolled, a tab could sit part under the header, too small to press, and the page now keeps their height clear above what has focus. In smaller windows they scroll with the page, as before.
- **Searching or filtering a plug-in's list of sections that fold (owner, 19 November 2026: "q is not defined. when activating leagues"):** on a plug-in's page drawn as sections that fold, such as Live TV's Channels or On demand's Sports and leagues, a search or the Show filter that left a section with nothing to show stopped the page with "q is not defined". The list was then not drawn again after a change, so a choice that had been saved looked as if it had not been.
- **A section's switch is named for what it holds:** a screen reader heard "Every channel in" before the section's name on every such list. It now hears the plug-in's own words for the switch, such as "Every league in Football".

### Security
- **Words from an app never become page code (CodeQL, 20 November 2026):** the new secret field, pagination and error summary from the design system now set a name, a noun or a link as text, or escape it, so words with page code in them show as words. Found by GitHub's CodeQL before the release; nothing released was affected.
- **Security scan:** Trivy (image and configuration), Gitleaks, Bandit, ShellCheck, Hadolint and ZAP signed out (58 passed) and signed in (111 passed) found nothing to fix. The scan's Trivy check now keeps its database in memory, as it cannot open on a pool drive.

## [0.24.0] (19 November 2026)

### Added
- **Plug-in pages that save in place, choose several and come in cards (plug-in API 1.16, owner, 19 November 2026):** a plug-in's own page can answer a change with only the part that changed, so the page keeps the open menu, where you were and focus, and says what was saved beside what you changed, in words a screen reader reads out once. A row can open a slide-out to choose several things at once, such as series and films from Jellyfin's library, with search, a filter for each kind, tick boxes and Show more, and focus goes back to its button. A page can draw each menu and each group of rows as a card with a sentence on what it is for, and show a small picture on a row, such as an uploaded logo, with its words. Create your own TV channel 0.2.0 uses them all; older plug-ins are drawn as before. Design system: plug-in screen cards and row pictures.

### Changed
- **File pickers match the rest of Starboard (owner, 19 November 2026):** every file upload is a "Choose a file" button in the site's style with the chosen file's name and size beside it, instead of the browser's own picker; choosing a file clears an earlier error. Design system: `.file-field`.

### Fixed
- **A plug-in's links to its own page open (owner, 19 November 2026: "The Schedule grid is not appearing"):** a link on a plug-in's page to the plug-in's own web page, such as Create your own TV channel's Open the schedule grid, now uses the address you opened Starboard with, at the plug-in's port, as Its web page does. The plug-in only knows the server's home network address, which a browser that reaches Starboard by a name or another address may not reach.
- **A row's Remove words:** the More menu on a plug-in's row says the plug-in's own words for Remove, such as Remove the logo, in place of Remove guide.
- **A plug-in's Versions had no upload button:** Update from a zip file now has **Upload and check**, which uploads the zip, checks it and shows What is new before anything changes; it said What is new before.
- **Copy issues for an AI helper found nothing from Reelix (owner, 19 November 2026):** Reelix gives a download's quality as plain text, which Starboard could not read, so every Reelix download was left out and the page said Reelix did not answer. It now reads both forms, adds Reelix's custom formats and score (for "Not an upgrade for the existing file"), and says "Starboard could not read Reelix's answer" when an answer cannot be read, with the detail in the log, instead of "Cannot reach".

## [0.23.0] (19 November 2026)

### Added
- **Plug-ins activate when installed (owner, 19 November 2026):** a plug-in from the catalogue, an address or a zip file is activated as soon as it is installed. One that needs settings first says what to enter and waits, as before, and so does an app plug-in such as Tdarr while the same app is on this computer, so you can bring it in first. Activate and Deactivate stay in General, State.
- **Plug-ins know their home address:** a plug-in with a page on your home network is given its own address there (`STARBOARD_HOME_ADDRESS`), so Create your own TV channel gives Jellyfin its channel list without anyone opening its page first.
- **AI assistants over MCP (DASH-464):** an AI assistant that speaks MCP, the Model Context Protocol, can ask Starboard about the media server: search the Library, what was added and is coming up, what is playing, downloads and their problems, requests, how each app is, and disk space. It is off until you activate Let AI assistants connect in Settings, Security, API keys, which says what it shares and gives the address to copy. Each assistant needs a Read only key, reads only what that key's scopes cover, and cannot change anything; each question is written to the audit log and counts towards the key's 120 requests a minute. Starboard speaks the protocol itself, with no new dependency, and nothing runs until an assistant asks. API 1.7.0 adds POST /api/v1/mcp. Changes from an assistant, each approved in Starboard's page first, are left for later. What Starboard can access lists AI assistants too.
- **An alert when a disk changes (issue #187):** every pool job the helper finishes, however it was asked for, is written to the log, as a warning when a disk was erased, and sent as the new `disk.changed` event (plug-in API 1.16), which the Notifications plug-in turns into an alert. The security notes explain why Starboard's user counts as root, so a check on the pool helper alone would not help.
- **Close on Install all updates (DASH-473):** when Install all updates finishes, Close takes its panel away. Focus goes to Ready to update, a screen reader hears that it closed, and the panel does not come back when the page opens again; Recent updates keeps the batch.
- **Pictures in What is new (DASH-475):** in Settings, Updates, What is new, each plug-in's own logo (or its initials), each app's and Reelix's icon and Starboard's mark sit beside its notes, as on its card.
- **Add Coming up to your calendar (DASH-67, #180):** the Coming up page has Add to your calendar, which makes an address a phone or computer calendar can subscribe to. The calendar shows the films, episodes, albums, books and radio from Coming up, from a week ago to about 8 weeks ahead: films, albums and books as all-day events on their release date, episodes and radio at the time they air. The address carries a token that opens this calendar and nothing else, never an API key or a Reelix key. Starboard keeps only its fingerprint and shows it once; Make a new address stops the old one at once, and Stop the address stops it. A refused token counts towards the lockout for that address, a good one is limited like an API key, and the calendar is kept for 15 minutes, so a calendar app that asks often costs nothing more.

### Changed
- **General on every plug-in's page (owner, 19 November 2026):** the first tab is General, with a card each for State, Versions, Jobs, What it may do and Remove. The plug-in's settings, its own pages, styles and actions keep their tabs, and a plug-in's page shows tabs from two parts. Design system: section groups.
- **Install all updates says whether it is still working (#161):** while it works, the panel says Installing updates and "4 of 5 done", and soft stripes move along the bar (still when your device asks for less motion); at the end it says All updates finished, Some updates did not install or The updates stopped. It no longer says Updates finished while updates are still installing.

### Fixed
- **Settings, Radio sometimes stopped loading:** a page could start before its own scripts had run ("startRadioSettings is not defined"); every page now waits until they all have.
- **Plug-in boxes take plain text:** a plug-in's Add box and the boxes under its rows, such as a TV channel's name, Rename and Change number, no longer refuse anything that is not a web address. Each plug-in checks what it is given.
- **Live TV's address message** says Enter rather than Type.
- **Plug-ins on their own network reach Starboard (DASH-482):** a plug-in on its own network, such as Disk forecast or Download summary, or on the VPN, now reaches Starboard's API through a socket in its own run folder, /run/starboard/api.sock, given to it as STARBOARD_API_SOCKET. Starboard runs on the server's own network, so it could not join the plug-in's network, and the plug-in could not read its figures. The plug-in's network stays closed to everything else, and the socket answers only Starboard's API and only to that plug-in's own key. There is no extra container: one waiting thread in Starboard serves every plug-in's socket. Starboard no longer tries to join each plug-in's network.
- **Three slips on the Updates and plug-in pages (DASH-474):** Settings, Updates names Apps, Updates in its words and gives Open Apps, Updates beside them, instead of "Each app's image is on ." when the link is not read; Starboard's last update result, such as "Starboard v0.20.1 is installed and answering", is no longer shown once Starboard runs a newer version; and a plug-in's What is new summary from its catalogue, on its Versions card and in Ready to update, ends at its last whole sentence or word with an ellipsis instead of stopping mid-word.

### Security
- **The disk pool helper's risk, written down (#187):** the security notes explain why Starboard's user counts as root, so a check on the helper alone would not help; every disk change is now logged and alerted instead.
- **A calendar address that can only read the calendar:** stored hashed, compared in constant time, rate limited with the API's limits, and refused by every other route.

## [0.22.0] (19 November 2026)

### Added
- **Play in Jellyfin (DASH-480):** films and episodes in the Library have a Play button that opens them in Jellyfin's web app in a new tab, ready to play: on the Films wall (covers and list), at the top of a film's page, and on each episode's row in a series. It uses the address you gave Jellyfin for your browser in Settings, Manage apps (Address to open in your browser, or Outside address when you open Starboard away from home), never an address only Starboard can reach, such as a container's name. When Jellyfin's only address is one on the server itself (http://127.0.0.1:8096, as Install apps saves it), Play uses the name you opened Starboard with and Jellyfin's port, as Starboard's other Open buttons do, so it works at home without setting anything. Something Jellyfin has not added yet has no Play button and says Not in Jellyfin yet. When no address can be made (for example Jellyfin on another computer with no address for your browser), the Library says where to add one. Starboard finds Jellyfin's films while it builds the Films list, in one list, and an item's page uses the lookup it makes already for Watched, so no row asks Jellyfin anything.
- **Restart where it is needed (DASH-470):** when Jellyfin says Restart needed, Restart Jellyfin is right there: on System, Overview, under Jellyfin's heading; on Settings, Updates, beside Jellyfin's plug-ins; and on Settings, Apps, Jellyfin, Recommended plug-ins. Beside a Reelix restore that waits for Reelix to start again, on Backup, Restart Reelix does it now. Each button shows only while a restart is needed and says what it does: anyone watching or listening is stopped and has to press play again, and Jellyfin is back in under a minute. It asks first, then follows the app until it answers again, saying how it is going, and the status updates by itself. Focus stays on the button while it works and moves to the result; a failure is said beside the button, which can be pressed again. It asks one small question every 3 seconds, only after you press it, for at most 3 minutes.
- **Cache counts in the diagnostics:** System diagnostics show how often Starboard's caches were used and emptied, with no keys or names in them.

### Changed
- **Library episode rows line up (owner, 19 November 2026):** each episode shows its name, then its status, Watched or Not watched, and Play, in fixed columns that line up down the season. On a phone they sit under the name on one line, with the status and Watched as icons only; screen readers still read their words. Status chips in any list row show their icon only on a phone, from the design system.
- **Mica is Starboard's own style (DASH-479):** calm neutral greys, 6px corners on buttons, fields, cards, panels, menus and dialogs, a light lift on cards, and a Blue accent. The dashboard card is the model for the rest: System panels, Settings sections, tables, slide-outs and dialogs wear its grey band across the top. Card edges and rules are one colour, a little darker than before. The design before it is the Classic style in the Styles plug-in (1.5.0).
- **Light unless you choose:** Starboard opens in Light for everyone who has not chosen a theme in Display; Dark and Match device stay as choices, and a choice already made is kept.
- **Glass:** the header, side menu, menus, slide-outs and dialogs are frosted layers over a soft wash of the accent colour, solid in high contrast and with Reduce transparency; cards have Mica's drop shadow.
- **Accent colour:** Settings, General, Appearance chooses the accent (Blue, Teal, Indigo, Forest, Plum, Ember or Graphite) on Mica's greys, for everyone on the server. High contrast keeps the chosen accent in a stronger shade. A server on Teal, the old default, moves to Blue once; choose Teal again to keep it.
- **A clearer hover on every menu:** the side menu, the header tabs, topic tabs and menus show a light fill with an edge at least 3:1 against the menu, in light, dark and high contrast and with every accent; the page you are on keeps its accent bar.
- **Styles from plug-ins keep their own design:** cards lift only in styles with elevated cards, headings keep their weight, and the menu hover edge is the style's secondary text colour, checked at 3:1 when a style is added.

### Fixed
- **Plug-ins added or removed no longer stop an update (DASH-484):** the settings backup before an update leaves out every folder Starboard's user cannot read, wherever a plug-in made it, such as a removed plug-in's data in holding, and going back after a failed update returns each one whole, including plug-ins added or removed after the backup. A backup interrupted by a file renamed away is tried five times instead of three.
- **Plug-ins on the home network reach Starboard (Remote access):** a plug-in on the home network is given Starboard's API on the server at host.docker.internal and Starboard's own port, which Starboard now accepts as a host name, so Remote access can read Starboard's apps.
- **Reelix listed once:** System, Apps, Updates lists Reelix once, as its films, series, books and music connections run in its one container.
- **Discover tiles:** cover tiles on Discover have the default 6px corners.

### Security
- **Live TV checks every address it opens:** each list, guide and stream address Live TV downloads, and every redirect, is checked against the same rules as app addresses, so a list cannot lead Starboard to a refused address such as cloud metadata.
- **Pinned scanner versions:** the security checks run fixed versions of their scanner image and Bandit.

## [0.21.0] (17 November 2026)

### Added
- **Check for updates (DASH-462):** Settings, Updates, Ready to update has a Check for updates button. It asks now, instead of waiting for the next scheduled check: GitHub for Starboard's newest release, each app's and Reelix's image registry, every plug-in catalogue, and Jellyfin for new versions of its plug-ins. Ready to update then says when it checked, what is ready and anything it could not reach, and focus stays on the button. Nothing is asked when the page opens.
- **What is new for every waiting update (DASH-462):** A What is new button beside Install all updates opens one slide-out with the release notes of every update ready, from the version you have to the new one: Starboard, Reelix, each plug-in, Jellyfin's plug-ins and the apps, each item's changes under Added, Changed, Fixed and Security, the version of each change in brackets when there are several, a list at the top to jump to each item, and each item's release page. An item with no notes says so and links its release page. The notes are read only when you press the button.

### Changed
- **One address for TheMightyTRexUK's Jellyfin plug-ins:** Picture shrinker for Jellyfin has moved to TheMightyTRex/jellyfin-plugins, one repository for every Jellyfin plug-in by TheMightyTRexUK. Settings, Apps, Jellyfin installs it from the new address. If your Jellyfin lists the old Picture shrinker address, Starboard replaces it with the new one the next time it offers Jellyfin plug-ins, in the same place in the list; every other repository you added stays as it is, and what is installed stays installed.
- **Words that follow the design system (design audit, 17 November 2026):** Starboard's pages, messages, terminal set-up and help no longer tell you to "see" or "look", and say "enter" rather than "type", and "disk" rather than "drive"; the switch that shows the rest of a Settings page is now More settings. Buttons are renamed to match: What it does, Check for an update, What is new, Show what it holds, Show the files, Find it, Find releases, Open Wanted and Open the report. A plug-in's install slide-out now says It can read, and its permissions are named Your apps and whether they answer, What is downloading, Your films, series and books, and Processor, memory and disks. API keys say What it may read and Reads. Messages no longer point at a place on the page ("below", "above"), and a waiting line names its job and nothing more.
- **One set of status words:** every chip, band and row takes its word and colour from one list, the design system's: Running and Not responding for apps, Healthy, Needs attention and Not working for plug-in cards, In progress, Done, Failed and Not started for jobs, Active and Inactive for settings, and Check before updating for a big change. Wanted's first tab and the Library's filter are now Not in library, and a title not out yet is Not released.
- **Square library cards:** the network and collection cards, the logo tiles and the dashboard's edit box now use the design system's square corners, its focus ring width and its type weights. The tiles behind light and dark logos take the browser's own colours instead of written-out ones.
- **What Starboard does not do:** the help article that listed plans is now the facts only, checked against Starboard 0.20.2. Its address is the same.
- **A check for banned words:** tools/checks.sh now fails on the design system's banned words in the pages, their scripts and the help, with each exception and its reason in tools/words-allowed.txt. The plug-in tester also warns about contractions, "see" and "look", "click", exclamation marks, em dashes and Title Case in a plug-in's labels, hints and confirm texts.
- **Install all updates shows from one update (DASH-462):** It used to show only when two or more updates were ready; now it shows for one, as Install 1 update, with the same order, holds and confirmation. Jellyfin plug-ins that Check for updates found are named in the list and counted.

### Fixed
- **Reading the Jellyfin plug-ins list changed Jellyfin (DASH-409, #147):** Opening Settings, Apps, Jellyfin finished the set-up of Intro Skipper and Merge Versions even when you had added them in Jellyfin yourself, which changed their settings and schedules. Starboard now finishes the set-up only for a plug-in it installed or activated for you; one you added in Jellyfin keeps its own settings, and reading the list changes nothing.
- **A plug-in job's failure said only "HTTP Error 502: Bad Gateway" (DASH-448, #145):** When a plug-in's job failed, System, Jobs and the log kept only the status line of the answer. They now keep the plug-in's own reason as well, for example "HTTP Error 403: Forbidden (the plug-in answered 502: Bad Gateway)", and Settings, Plug-ins shows that reason beside the job whose last run failed.
- **A built-in plug-in left "failed" was never started again (DASH-449, #146):** If a built-in plug-in such as Live TV failed to start once, for example because its helper image had been tidied away, Starboard left it failed for good, even while its container ran. Starboard now tries a failed built-in plug-in again each time it starts. One you made inactive stays inactive.
- **Apps a full backup stopped stayed stopped (DASH-382, #148):** A full backup stops each app for the moment it copies its settings. If Starboard itself stopped during that moment, the app was not started again. Starboard now notes each app before it stops it, and starts any app left stopped the next time Starboard starts. The backup that was cut off is marked as stopped, so you can make it again.

## [0.20.2] (17 November 2026)

### Fixed
- **Update now could stop at the backup:** Update now on the page could stop with "tar: data/self-update.log.new: No such file or directory" while backing up your settings. The page's update helper rewrites its progress log after every line, and its BusyBox tar looks each file up before it checks what to leave out, so the log being renamed away mid-read stopped it. The helper now writes the half-made log beside the data folder, not in it, and a backup that fails is tried again, up to three times. Updating from 0.20.1 or earlier still uses the installed helper: if it stops, choose Update now again, or run ./update.sh on the server.

## [0.20.1] (17 November 2026)

### Fixed
- **Jellyfin 12 refused two of Starboard's calls (DASH-458):** Jellyfin 12 with legacy authorisation off answers 401 when the key comes only in X-Emby-Token. Adding a plug-in's libraries to Jellyfin and the poster check on the Library health page now send the key in Authorization too, as Live TV and Moving in already did, and keep X-Emby-Token for older Jellyfin and Emby.
- **Release notes for 0.15.2:** Starboard's own release notes had the 0.15.2 Added entry twice, in two wordings, and showed only the second. They now have the one in this changelog.

### Security
- **Code and writing checks:** Once a week, and by hand whenever wanted, GitHub checks the code for likely bugs (Ruff and Biome), the writing rules (Vale), misspellings (typos) and the safety of the workflows (actionlint and zizmor), and runs the unit tests under coverage.py, which fails if they run less of the code than before. The workflows' actions are pinned to exact versions, and Dependabot keeps them up to date. The first run found and fixed unused code in 33 files.
- **The key check reads the whole history again:** Since 10 November, the security scan's check for keys and passwords in the git history read no commits when run from a second working copy of the code (a git worktree), and passed. It now reads them all; the 7 it found are made-up keys in tests and a placeholder in the help, now listed in `.gitleaksignore`. The checks image also runs as a user that is not root.

## [0.20.0] (17 November 2026)

### Added
- **Bring in media you already have:** An optional step in the set-up, after Storage, and on its own from Library, Bring in media, and Still to set up. It copies films, series, music, books and audiobooks from folders on this computer, another disk or a network share (SMB or NFS) into your media folder, named and placed so Reelix and Jellyfin match them. Four parts: where your media is (in order, with Move up and Move down: the place higher in the list wins when a title is in two places), what is in each (with a correction for a whole place or one folder), Check names (Matched, Needs a look and Left where it is, with the space needed) and Copy. Nothing at a source is renamed, moved or deleted: shares are mounted read only and folders are only read. Subtitles, artwork and .nfo files travel with their film or episode; samples and leftovers stay; exact copies are brought in once; a file already in the media folder is never written over. The copy runs in the background at the lowest priority, can be paused, carries on after a restart, and shows on the dashboard and in Activity; then Reelix's own library import adds each title and Reelix's rename names each file its own way. Linking films and series on the same disk, instead of copying them, is offered and off to start with. The same step in the terminal set-up. OneDrive and Google Drive too, signed in read only with Connect a cloud service's sign-in (Google Drive in this browser only, as Google allows reading existing files only then), copied down to a staging folder on the media disk that goes to the holding folder at the end.
- **The folder picker opens on places:** Every page that picks a folder opens on This computer and each disk, then one list of folders with a path bar and Back, each folder with its size and what is in it, and Use this folder (design system 7a3f938).
- **Log limits (DASH-451):** Settings, General, Logs and feedback keeps Starboard's logs for a number of days (30 by default) and no more than a total size (50 MB by default, from 10 MB to 500 MB); whichever comes first removes the oldest days. They cover Starboard's own log (with its jobs, updates and plug-ins' lines), the API's audit log and the last Starboard update's log, and the page says what the logs take now. Old days go when a new day starts, when the limits are saved, or when what was written since passes the limit, with no new timer or thread. A Starboard from before keeps the days it was set to.
- **Delete all logs (DASH-451):** In its own danger section on Settings, General, Logs and feedback, and on System, Logs: the dialog says how much goes and what stays, and asks for the password. Today's file and the audit log are emptied, not removed, so logging goes on, and the first new line says the logs were deleted, from which browser session or API key.
- **The apps' own log limit:** Logs and feedback shows what Docker keeps for each app (such as 3 files of 10 MB, from daemon.json) and lists apps with no limit. Apps and plug-ins Starboard installs get 3 files of 10 MB in their own Compose file, so a new install is capped without daemon.json; running containers keep theirs until their file is written again. The Compose check refuses a log driver that sends logs away from the computer.
- **API 1.4.0:** `GET /api/v1/logs/limits`, and with a manage key that ticked Logs, `POST /api/v1/logs/limits` and `POST /api/v1/logs/delete` (`{"confirm": true}`).
- **Install all updates (DASH-454):** When more than one update is waiting, Settings, Updates has Install all updates at the top of Ready to update, with how many ("Install all 6 updates"). One password, then a dialog lists what installs, in order, and what is held back for you with the reason: a plug-in asking for new permissions or that comes as a zip file, a big change (a new major version), or anything Starboard cannot update from here. The updates install one at a time, never in parallel: your other apps and Jellyfin's plug-ins, then Starboard's plug-ins, then Reelix, then Jellyfin restarts once for all its plug-ins (waiting while someone is watching, and saying so), then Starboard last. Each keeps its own copy, check and way back; one that does not work goes back by itself and the rest carry on. One panel shows each update's state in words and icons (Waiting, Updating, Done, Went back, Held back), how many have finished, and announces each change politely; it reconnects after Starboard restarts and shows how it ended. Recent updates lists the batch as All updates.
- **API 1.5.0:** `GET /api/v1/updates/all` (what Install all updates would do, and what is held back) and, with a manage key that ticked Updates, `POST /api/v1/updates/all` (202, followed with `/api/v1/updates/runs/{id}`). Apps and Reelix in `GET /api/v1/updates` say `big_change`.
- **Connect a cloud service:** On Settings, General, Backup and restore, Copies off this computer, **Connect a cloud service** opens a wizard in a slide-out: choose Google Drive, OneDrive, Dropbox, Backblaze B2, an S3-compatible service, Nextcloud or another WebDAV server, an SFTP server or your own rclone remote, sign in, choose or make the folder, test it (write, read back and remove a small file) and save, with how many copies to keep. You sign in on the service's own page and Starboard never sees that password. Find out more in **Copy backups to a cloud service**.
- **Complete on the phone, once switched on:** Google Drive and OneDrive can be signed in on a phone: scan a QR code, enter the code, and the wizard moves on by itself once you allow it. This choice shows only once Starboard is registered with Google and Microsoft; until then, Complete in this browser is the way. Complete in this browser works for every service that signs in on its own page: open the sign-in page, then paste back the address it ends on.
- **Test connection:** Beside the place copies go, Test connection reaches it, writes a small file, reads it back, removes it, checks there is room for the newest backup and, for a cloud service, that the sign-in still works. The result is shown in words and kept, and a sign-in the service no longer accepts offers Sign in again.
- **Monthly backups:** When backups are made has Monthly, on the 1st of each month at 03:00, keeping the newest 6. A server that was off on the 1st makes that month's backup once when it starts again.
- **API 1.6.0:** `GET /api/v1/backup/copies` and `POST /api/v1/backup/copies/test`, with the system scope.

### Changed
- **Lighter plug-in pages and checks:** The plug-ins list no longer reads and hashes every plug-in's logo on each call, and the styles, dashboard cards, System jobs, events and the idle-stop check (every minute) read only each plug-in's manifest and state. The plug-ins routes answer 1.6 to 2.8 times faster. (DASH-445)
- **Alerts card:** The log's problems are found without reading every line of every day kept as JSON: 13 ms instead of 250 ms over 60 days, each minute the dashboard is open. (DASH-445)
- **Apps and Updates pages:** Docker is asked about each image once, not on every visit; Look for updates still reads each image's registry digests fresh. (DASH-445)
- **Set-up steps:** The set-ups' words are read once for each page instead of at every step. (DASH-445)

### Fixed
- **Escape in a slide-out:** Escape closes a slide-out even while focus is inside the page shown in it, such as a step of Still to set up.
- **Clicking in a set-up step:** Clicking a field or button inside a Still to set up step's page no longer sends focus back to the step's heading.
- **Settings, Radio could stop loading:** Every page now starts once its own scripts are ready, so Settings, Radio no longer stops with "startRadioSettings is not defined".
- **No sideways scroll on narrow phones:** A long folder path in a heading, as on Backup and restore, wraps instead of pushing the page sideways at 320 pixels (design system).

### Security
- **Cloud sign-ins:** The address pasted back is checked before it is used: only this computer's own address on rclone's port, with this sign-in's own state and a code, rebuilt from those two values. The sign-in helper publishes no port, has a 10-minute limit, and is removed when the sign-in ends or the slide-out closes. Passwords and keys are read from a file inside the helper, never put on its command line, and kept as the existing rclone config is: in Starboard's own folder, never in a backup, never sent to the browser.

## [0.19.1] (16 November 2026)

### Changed
- **Backup and restore is in Settings, General:** It was under System, Backup. The page keeps its address, and Settings, Updates, Restore still restores a backup.
- **Dashboard cards keep their band on one line:** The grey band at the top of each card has the logo, the name and the status chip; when the card last updated moves to a small footer, a lighter grey, so Disk space, System load, VPN and the rest no longer wrap onto two lines. (Design system 3949689, `.card-foot`.)
- **The version in the side menu:** The version at the foot of the side menu is a link to Settings, Updates. When a newer release is out, a red dot sits just above it and pulses gently, still when Reduce motion is on; screen readers hear "update available" with the version. The word Update above the version is gone. (Design system c7c53bc.)

### Fixed
- **Help centre cards:** The plug-ins help centre shows at most three plug-in cards to a row, and banded cards no longer have a white strip above the band (design system 76983d3).
- **Update now stopped at Backing up your settings:** Updating from the page could stop with "Starboard was not updated" because the backup read Starboard's settings folder while the page's update log, and Starboard's own settings, were being rewritten there. The backup now leaves out the update log and half-written files, carries on when a file changes as it is read, and when a backup really fails, the page says why instead of "update.sh stopped without saying why". Every update now checks that its backup reads back whole before it changes anything, so going back after a failed update always has your settings to restore. Updating from 0.18.0 or earlier still uses that version's script: if Update now stops at the backup, try it again or run ./update.sh on the server.
- **Settings topic tabs:** Activating Advanced settings on a page with topic tabs, such as Settings, Reelix, no longer selects two tabs at once and shows two sections together. A section that appears gets an id no other has.
- **Search:** Each kind under Not in your library no longer ends with the word "null".

### Help
- **Pictures for 0.19:** Every help and README picture retaken from the example server's default install, and new marked-up pictures (at least 3 each) for Use the dashboard, Finish setting up, Find a setting, Coming up, Organise categories, Copy download issues, Get what is missing, Manage downloads, Download without a VPN, Set download hours, Update Starboard, Update a plug-in, Add a plug-in from a zip file, Use Starboard's API and Set up Live TV. Their steps were checked against the screens and corrected where they had changed (Settings, Updates as one page, Settings, General's pages, Discover's Search, Reelix's topic tabs and Edit buttons, Make a key as a slide-out).
- **Library clean-up's help pages** now have their pictures in the plug-ins help, mirrored here with the pictures (tools/sync-plugin-help.py copies help/images/<id>/ to docs/help/images/plugins/<id>/).
- **Help picture tools:** tools/help-screenshots.sh runs to the end: a shot that fails is listed and the rest are still taken (it stopped at change-reelix-settings-3-form.png). Each shot has a fresh page, can put back what it changed (after), and topics can keep their shots in tools/screenshots/help_shots.d/. Both picture tools use the Playwright cache folder when there is one.

## [0.19.0] (15 November 2026)

### Added
- **Download without a VPN:** Both set-ups' VPN step asks first how downloads connect: Use my VPN account (recommended) or Continue without a VPN. Going without one shows a warning in plain words first (other people sharing torrents see your home internet address, your internet provider sees what you download, and what that can lead to), with Cancel as the default; the choice is recorded. The apps are then installed without Gluetun, with qBittorrent on its own network and ports and Reelix reaching it by its name. (DASH-440)
- **Add or remove a VPN later:** Settings, Downloads, VPN adds a VPN to an install without one (Gluetun is installed, the download apps move behind it and Reelix follows), or removes it after the same warning. Without one, Downloads says Downloading without a VPN with Add a VPN, hidden for 90 days with Hide for 90 days, and the dashboard's VPN card says No VPN. No alerts are sent about it. A new help topic, Download without a VPN. (DASH-440)
- **Automatic updates for everything:** Settings, Updates, Update by themselves lets each part update by itself: Starboard, Reelix, your other apps, Starboard's plug-ins (from a catalogue or their own address) and Jellyfin's plug-ins. Each is deactivated until you activate it, here or in either set-up. They update once a day in the hours you choose (your download hours, or always 01:00 to 06:00), one at a time, each with a copy first, a check afterwards and the way back by itself (Jellyfin's plug-ins cannot go back by themselves, so a copy of their folder is kept and you are told). A plug-in version that asks for new permissions always waits for you, and a version that did not work is not tried again until you update it yourself. (DASH-422)
- **One place for updates:** Settings, Updates now lists everything that can be updated, with Update now on each, the same password dialog and progress for Starboard, Reelix, an app and Jellyfin's plug-ins, how each part is kept safe, and Recent updates with what each did. Apps, Updates points to it. (DASH-420)
- **A copy of an app's settings before its update:** An app updated from Starboard has its settings folder copied first (without caches), as Reelix's is. (DASH-422)
- **Alerts when an update waits:** One alert for each plug-in or app version that waits for you, and one "Updated by itself" alert with what is new after an automatic update. Nothing is checked for them. (DASH-420, DASH-421)
- **Copy issues for an AI helper:** Activity, Downloads, Queue has Copy issues for an AI helper and Download as Markdown. They gather every download that needs attention or failed, with its app, download app, state and the app's own state, every message, size, progress, age, indexer, paths inside the container, its ids in Reelix or the app, the download's id and what Starboard already tried, under a short prompt asking the AI helper to diagnose each one, say the likely cause, the fix to try and what to check. Keys, passwords, tokens, private addresses and full download addresses are taken out. Each app is asked only when you select a button. A new help topic, Copy download issues for an AI helper. (DASH-434)
- **Starboard's API 1.3.0:** GET /api/v1/downloads/issues gives the same, with a read key and the downloads scope. (DASH-434)
- **Plug-ins from a zip file:** Settings, Plug-ins, Catalogue has Upload a zip file, for a private plug-in with no address such as On demand. Starboard checks the zip (up to 50 MB, starboard-plugin.json at the top, no links or names outside it), shows what the plug-in may do and asks for your password, then builds its container from the zip's Dockerfile with limits (2 GB of memory, 2 processor cores, 20 minutes) and installs it, step by step. Its page has Update from a zip file; Roll back works as for any plug-in. A new help topic, Add a plug-in from a zip file. (DASH-414)
- **Plug-ins that tidy the library:** A new permission lets a plug-in such as Library clean-up move films and series into a holding folder inside your media folder, media/.holding, keeping their folders, and put them back. It is said plainly before you add it, with a high risk, as the plug-in is given your whole media folder. A plug-in's list can now have a Put back button on each row. (DASH-406)
- **Jellyfin libraries for plug-ins:** A plug-in that fills folders, such as On demand, can have Starboard add its libraries to Jellyfin each time it is activated, with real-time monitoring deactivated, after you approve the jellyfin:libraries permission (medium risk). (DASH-430)
- **Plug-in API 1.15:** For plug-in makers: `build` on a container, for an image Starboard builds from the plug-in's zip file (`local/<id>:<version>`); `jellyfin_libraries` with the `jellyfin:libraries` permission; the `library:holding` permission with the `media:holding` volume; and `restore` on a custom setting's item, drawn as Put back. Built from a zip file, Jellyfin libraries and The holding folder in the media folder are in the manifest reference, with the AI prompts. Plug-ins made for earlier versions work as before. (DASH-414, DASH-430, DASH-406)
- **Jellyfin's pictures and details outside its settings folder:** New installs give Jellyfin a /metadata folder (jellyfin-metadata beside its settings) and set it at set-up, so Jellyfin watches far fewer folders. Settings, Jellyfin has Pictures and details, which moves an older install's the same way, with a link at the old address so every picture still shows and a count of Jellyfin's folder watches afterwards; it also runs after Starboard takes Jellyfin over. (DASH-431)
- **Picture shrinker inside Jellyfin:** Settings, Apps, Jellyfin can offer Picture shrinker for Jellyfin 10.11 and 12, which shrinks posters and photos inside Jellyfin with a backup of each original. It is offered once its first version for your Jellyfin is released; until then it says Not released yet. Starboard's own Picture shrinker plug-in stays idle while it is installed. (DASH-433)
- **Which Reelix you run:** Starboard notes the exact Reelix build it installed (its version tag, such as lite-0.8.7-trex.2, version, commit and digest) after an install, a switch, an update or a way back, with the 20 before it. GET /api/reelix/editions gives it. (DASH-419)
- **Help for every plug-in in the collection:** The help centre's Plug-ins area has the same eight pages for each plug-in in the Starboard plug-ins collection (what it does, install and remove, settings, its dashboard card, updates and roll back, accessibility, problems with a flow chart, and for developers), each with its logo, mirrored from the collection's own help centre by tools/sync-plugin-help.py and checked by check-help.py. (DASH-426)
- **A title for each card size (plug-in API 1.15):** a plug-in card can have its own title for each size in Edit dashboard (small, medium, half, wide and full), each short enough to fit on one line in that size: up to 17, 28, 22, 43 and 45 characters. The manifest check refuses a longer one and the plug-in tester names it with its limit. Picture shrinker's card in the example pictures has one for each size. (DASH-443)

### Changed
- **Dashboard cards:** Every card on the dashboard now has the grey band that plug-in cards have: a logo, the card's name as the heading, and at the right a status chip and when it was updated where the card has something to say, such as Nearly full on Disk space or Not responding on Service health. A card about one app shows that app's own logo, the same as on the Apps page: Jellyfin's on Now playing, Reelix's on Downloads, Coming up and Recently added when Reelix is the only source, and so on. Starboard's own cards, and cards that combine several apps, show a Starboard icon. (DASH-442)
- **A new install gets the newest release:** Run first and the installer now install the newest release, as ./update.sh does, instead of the main branch, which can have changes not released yet. For testing, Run first and ./install.sh take --main, which ./update.sh then follows too; ./install.sh --releases goes back to releases. Update in Run first, for a Starboard already installed, now uses ./update.sh, with its backup and way back. (DASH-416)
- **Help, simplest first:** Set up your dashboard is rewritten around the default install (Starboard, Reelix Lite and its apps), with Add more apps and Advanced options as their own sections, and moves to Get started. Install apps, the terminal set-up and the quick start keep the default install first and the other installs apart; examples use Jellyfin rather than Sonarr. (DASH-439)
- **AI prompts for developers:** One prompt each for a card plug-in, an app plug-in and a plug-in that converts files like Direct play, each with the checklist the assistant must follow (permissions, memory limits, accessibility, updates, card refresh times and the content rules), for plug-in API 1.15. llms.txt lists the developer pages and the plug-ins help centre. check-help.py fails when Starboard's plug-in API is newer than these pages describe. (DASH-426)
- **Examples for a new install:** Add an app's example address is Jellyfin's, http://127.0.0.1:8096, and the Install apps summary says Starboard connects Bazarr to Reelix rather than asking you to connect Sonarr and Radarr. The screenshots' example server shows the default install; the older set-up with Sonarr and Radarr is kept for Copy app settings.
- **Clearer words on the way to updating:** The set-up's summary says Activated or Deactivated, not On or Off, and so does Reelix's task list. (DASH-420)
- **Update checks in every release:** The release checklist has an update step: tools/update_e2e.sh updates Starboard from the release before to this build and back, Update now's own helper, an app and Reelix (from one version tag to another with REELIX_FROM and REELIX_TO), all in a sealed Docker in a container; the plug-in tester takes --previous to rehearse a plug-in's update and Roll back. (DASH-418, DASH-423)
- **Still to set up and small cards:** Go through them sits at the right of the Still to set up card's grey band, and focus comes back to it when the slide-out closes. On a small card (a quarter of the width) the band's status chip shows only its icon; screen readers still hear its words. (DASH-443)

### Fixed
- **The Docker helper image:** Starboard downloads its pinned Docker helper image when it is missing, such as after unused images were removed, before it starts or updates apps or plug-ins, makes backups or looks in folders. If it cannot, it says so plainly: check that this computer can reach Docker Hub, then try again. Before, activating a plug-in could fail with "No such image". (DASH-438)
- **Plug-in buttons that ask first:** A plug-in button with a confirm, such as Line speed's Test now, asks first in the standard confirm box, which starts on Cancel; Escape cancels. Before, the question was never asked. (DASH-441)
- **Plug-in list settings:** A list setting, such as Outside services' Addresses to check or Home Assistant's What to show, is a box with one value a line, saved as a list. Before, it was a one-line box and saving said "give a list". (DASH-441)
- **Removing an app plug-in:** Its entry on Apps goes with it (the one it added, or the app it took over), and Settings, Tdarr says Tdarr is not installed, with a link to add its plug-in, instead of offering to connect it. (DASH-427)
- **An app update that keeps restarting goes back:** After an app update, Starboard now waits until the new version has stayed running for 15 seconds without starting again. Before, a version that exited at once and was started again by its restart policy could be caught running for a moment and kept. Found by the end-to-end update test before this release.

### Security
- **Plug-ins from a zip are built with limits:** Only a zip can install a plug-in that is built on your computer; its Dockerfile is checked first (no outside builders, mounts, network or security options, no downloads with ADD, no images from your computer), the build cannot reach your home network, folders, Docker or apps, and it has limits on memory, processor, time and size. (DASH-414)
- **The holding folder only when you approve:** Only a plug-in with the library:holding permission, approved when you add it with its high risk said plainly, can reach your whole media folder. (DASH-406)
- **Downloading without a VPN is your informed choice:** The warning says what others can see before anything is installed without a VPN, with Cancel as the default. (DASH-440)
- **Copy issues leaves secrets out:** Keys, passwords, tokens, private addresses and full download addresses are taken out of what is copied for an AI helper. (DASH-434)
- **Checks:** The unit tests, the browser journeys, the accessibility checks (axe, reading order, keyboard tasks and the layout check), the API contract tests and example plug-ins, the end-to-end update test, the help check, the private details check and the security scans ran on this release.

## [0.18.0] (15 November 2026)

### Added
- **Update now and automatic updates:** Settings, Updates has Update now, which asks for your Starboard password and installs the newest release, with its progress step by step, and Install Starboard updates automatically (deactivated by default), which installs a new release by itself in quiet hours and does not try a version again after it did not install. Reelix's automatic updates wait for quiet hours too, and both set-ups ask about updates after Download hours. (DASH-417)
- **Recommended plug-ins:** The Catalogue starts with Recommended: Direct play, Notifications and Disk forecast, each with a Recommended chip. Nothing is added until you choose it, with what it may do and your password as before. (DASH-425)
- **Plug-in logos:** A plug-in can have a small logo, which Starboard checks and cleans before it shows it in Manage, the Catalogue, the plug-in's page and its dashboard cards. A plug-in without one shows its initials. (DASH-428)
- **Plug-in jobs on your schedule:** A plug-in's job can run when you choose in its settings: every day, every week on a day, or every month on a date (the last day in a shorter month), at a time. System, Jobs shows when it runs next, with Run now. (DASH-432)
- **Plug-ins for Jellyfin's pictures:** A new permission lets a plug-in read and change Jellyfin's metadata folder (its posters, photos and details), said plainly before you add it, with a medium risk. Nothing else gets the folder. (DASH-432)
- **Plug-in updates you can trust:** Before a plug-in updates, its warning shows What is new since your version, which of your settings move, and how the update is kept safe. The update then runs as steps you can follow: the plug-in is asked to finish its work first, your settings move to the new version, and Starboard waits for the new version to answer. If it does not start or answer, Starboard goes back to the version you had by itself, with your settings as they were, and says why. Roll back runs as steps too and puts your settings back. (DASH-424)
- **Starboard's API 1.2.0, updates:** A key with Updates ticked (never given unless ticked) can list what can be updated (Starboard, Reelix, your apps and plug-ins), start an update to the version Starboard already found, follow its steps and roll a plug-in back, with Read and manage, an Idempotency-Key and a line in the audit log. One update runs at a time, each with the same backup, health check and way back as the pages; an app updated this way goes back by itself if it does not run within two minutes. (DASH-424)
- **Help for updating:** New topics, Update a plug-in and roll it back, and Update Starboard from its page with Update now and automatic updates; going back for Reelix, apps and plug-ins; and for developers, Write a plug-in that updates safely, with the references, the API changelog, the API reference and AI prompts for a safe new version and an update script. (DASH-424)
- **Plug-in API 1.14:** A card's own refresh time (10 seconds at the quickest, cards due together asked in one request, nothing while the tab is hidden), recommended entries in the catalogue, logos, the card band with a status and when it updated, job schedules from settings, the jellyfin:metadata permission, and update tools: a step before and after an update with time limits, a health wait with an automatic Roll back, settings migrations kept for Roll back, and What is new before an update. The developer help, the manifest schema, the plug-in tester and the AI prompts are brought up to date, and check-api updates an example plug-in with a settings migration and a failing health check. Plug-ins made for earlier versions work as before, and gain the health wait when they have a health path. (DASH-424, DASH-425, DASH-428, DASH-432)
- **A new help centre:** The help has a home page with the journey from first install to everyday use, a side menu of areas and groups on every page, the newest change, and a problem solver that asks what is wrong and leads to the answer. Every Fix a problem topic starts with a flow chart, with each answer in its own section. (DASH-436)
- **Accessibility in the help:** The help has its own Accessibility section: an overview; Change it for you (text size and spacing, light, dark and high contrast, reduce motion, underline links); Ways to use it (a keyboard, a screen reader, zoom and large screens, a phone or tablet); and How we check it (how Starboard is tested, the latest results, limits and known gaps, and how to tell us about a problem), each with marked-up pictures. (DASH-435)

### Changed
- **Plug-in cards:** Every plug-in card on the dashboard has a grey band across the top with the plug-in's logo, its name as the heading, and at the right a status chip and when it last updated, so they all look the same. (DASH-428)
- **Updates:** update.sh hands over to the new version's own update.sh when it updates to a newer version, so a fix to it helps in the very update that brings it. Going back keeps the running copy. (DASH-429)
- **Upgrade guide:** What is new fills the slide-out's width on wide screens. (Design system 10584ca)

### Fixed
- **Large text in the side menu:** At 125% to 175% text, and with wider spacing, the side menu grows wider, so Starboard no longer breaks in the middle of the word and Feedback no longer runs past its edge. (DASH-437, design system e3334ef)
- **Large text in the header:** When the header has too little room, it gives way in steps: icons only, then the Search button, then Help and Display as icons, then the menu under Menu. It refits when the text size or spacing changes in Display, so nothing is cut off and the search box is never squeezed to a few letters. (DASH-437)
- **Short windows:** In a window about 600 pixels tall, the side menu items no longer overlap: they sit a little closer, and the menu scrolls on its own when they still do not fit. (DASH-437)
- **Reduce motion Off:** Off now brings back all movement even when your device asks for reduced motion; Match device follows the device and On always reduces it. (DASH-437)
- **Phones at large text:** Held downloads and long buttons, such as Sort, no longer push Downloads sideways at 150% and 175% text. (DASH-437)

### Security
- **Updates need your password or their own scope:** Update now asks for your Starboard password, and an API key can start updates only when Updates was ticked when it was made; each update is in the audit log. (DASH-417, DASH-424)
- **Logos are cleaned before they show:** A plug-in's logo is checked and cleaned by Starboard (no scripts, links or outside files) before any page shows it. (DASH-428)
- **Jellyfin's pictures only when you approve:** Only a plug-in with the jellyfin:metadata permission, approved when you add it, can reach Jellyfin's metadata folder. (DASH-432)
- **Checks:** The unit tests, the browser journeys, the accessibility checks (with the new layout check), the API contract tests and example plug-ins, the help check, the private details check and the full security scans, with CodeQL, ran on this release.

## [0.17.0] (14 November 2026)

### Added
- **Starboard's API 1.1.0:** The API now reads everything the pages show (Coming up, requests, speeds, download hours, history, the Library and its search, uptime, app updates, containers and more), and a second right, Read and manage, covers the everyday actions: approve or decline a request, pause or resume downloads, remove or block a download, build a Library tab again, look for container updates, run a Jellyfin job and send a test alert. /api/v1/events streams app changes and alerts as they happen. Make a key asks what each key may do and what it may see. (DASH-274)
- **Developer help and AI assistants:** The help has a Developers section with the plug-in and API references (the API reference built from the API description), a quick start, a page listing what the API covers for every action on the pages, and Connect an AI assistant, which gives an assistant its own Read only key with the fewest scopes. /api/v1/logs gives Starboard's log with addresses, names and keys taken out, only to keys with Logs ticked. (DASH-150, DASH-275, DASH-246, DASH-76)
- **App plug-ins:** A whole app can now come as a plug-in, kept apart from the main install, such as Jellystat with its database: it gets its own page on your home network at a port Starboard chooses, its own passwords made once for your server, and Remove asks where its folder goes. A plug-in can also copy an app you already run, such as Tdarr, into itself, without removing the old one. The Catalogue has a group, Apps you can add. (DASH-411)
- **Plug-ins you can trust and update:** Adding a plug-in first shows what it can see, change and reach, with Install and Cancel; its menu items appear only once it is added. Settings, Plug-ins has Manage, the Catalogue (sources can be added from a link) and a page for each plug-in. Catalogue versions are checked against their checksums, State shows each plug-in's version and What is new after an update, and Update, Roll back and Update from an address are on Versions. A plug-in that stops answering says Not answering, and one that is idle rests until it is needed. (DASH-318, DASH-330, DASH-357, DASH-360, DASH-393)
- **Plug-ins can do more (plug-in API 1.2 to 1.13):** Plug-ins may now restyle the whole of Starboard (up to 32 styles), use a folder inside the media folders they mount, set up before they are activated, hear events and run jobs, lay out their settings in sections, use Reelix's key and your news server when you approve it, draw their own screens with menus, folding tables, filters, links and file uploads, put a VPN app's port on Gluetun for your home network, add files to your media folders as the media folder's owner (never as root) and run whole apps. Plug-ins made for API 1.0 and 1.1 work as before.
- **Discover by area:** Discover has a page each for Films, TV, Music, Radio, Books and Audiobooks, from Reelix's own lists. Settings, General, Discover rows chooses each area's rows and their order, including a row for each genre (such as Comedy or Science fiction) for films, series and radio. Recently added follows what arrived, so new episodes come first, On demand history shows what you started watching, with Add to wanted and Remove, and pictures are kept for four weeks, with Clear the picture cache in Settings, Performance. (DASH-303, DASH-324, DASH-395, DASH-396)
- **Discover, Radio:** One search across every radio source, with From radio stations and Podcast feeds only; the genres the sources share as chips; every BBC station in a picker by group; and each source's own categories under More categories. (DASH-339)
- **Search filters and Search the sites:** Search filters results by whether they are in your library, kind, year or decade, genre, status (Have it, Missing, Downloading, Below the quality wanted), released or coming soon, followed or not, language, rating and radio source, and remembers them for your account. Search the sites is its own page: one search across the sites Reelix searches, to compare size, seeders and age, with Get this one. (DASH-301, DASH-213)
- **Complete collections and series:** An opened film collection shows every film in it, and audiobook and book series come from Audiobookshelf with the missing books from Audible, each with Add missing. Books, Series and Authors are banners like audiobooks, covers of anything not in your library yet are faded behind a dashed outline, and Library, Audiobooks, Narrators lists everyone who reads your audiobooks, with a page each. (DASH-261)
- **More in the Library:** Books, music and podcasts have their actions: Quality and folder, Select several, Files and history, and Podcasts and Keep. Change match searches for the right title and moves the item in Reelix with its files kept, or puts the old match back. Library, Radio, Stations is a square grid like TV networks. (DASH-206, DASH-209, DASH-319, DASH-321)
- **Bring in music, and folders nobody lists:** Library, Music brings in the artist folders already on disk, as films, series, books and audiobooks do, each artist following only the albums you have. A folder with no match, such as a home video, can come in with your own title, year, description and picture once Reelix can take it (Reelix task RFX-90). (DASH-282, DASH-322)
- **Downloads and Wanted:** Activity, Downloads lists Held downloads, the releases a delay profile is holding back, with Get it now and Remove; Choose the episode handles files Reelix refused for their episode number; and paused unpacking in NZBGet is said, with Resume unpacking. Wanted has an item for each media type with Missing and Below the quality wanted, and each film or episode has Details with what Reelix last did and See what Reelix can find. History has Keep history for and Delete history. (DASH-210, DASH-304, DASH-305)
- **More of Reelix in Settings:** Settings, Reelix has Tags, Path mappings and Site list updates; Reelix's health shows a broken yt-dlp or FFmpeg, an expired Spotify sign-in and YouTube downloads that keep failing. Settings, Radio has Your podcast library (files Reelix has not matched, with Match by hand), Add a show from a link, and a Catch-up downloads switch for each source that has catch-up. (DASH-204, DASH-212, DASH-218)
- **Live TV, your own channel lists:** Live TV takes your own M3U or JSON channel lists and XMLTV guides, by address or as a file up to 60 MB, each with Activate, Deactivate, Test and Remove, and adds them to Jellyfin as one more tuner. Channels fold into sections by list, region and section, each with its own switch and a table to sort, filter and tick several; a list longer than 2,000 channels says only the first 2,000 are read. The dashboard can show On TV now, and logos stay legible. (DASH-359, DASH-312, DASH-313)
- **Dispatcharr from Starboard:** Settings, Apps, Dispatcharr sets up the Dispatcharr add-on without opening it: its admin and a key, your IPTV playlist or Xtream Codes server and guide, the channels, and Dispatcharr in Jellyfin as a tuner with its guide. (DASH-228)
- **Tdarr from Starboard:** Starboard gives Tdarr its key, and its settings have the basic choices: which libraries, save space or check only, how many at once, and any time or in quiet hours. With the Tdarr plug-in, films and series are converted in a folder on the media disks, so working copies never fill the system disk. (DASH-306, OPS-19)
- **Recommended Jellyfin plug-ins:** Settings, Apps, Jellyfin offers skipping intros and credits (from downloaded times, or analysed here in quiet hours only), Playback Reporting, Merge Versions and Trakt, each installed and set up through Jellyfin and shown with its version. Choosing another deactivates the old one; nothing is uninstalled. (DASH-404)
- **Kavita in Install apps:** Kavita, the ebook reader, is in the Ebooks group. It reads the media folder only and has a Still to set up step.
- **Full backups without media:** System, Backup and restore makes a full backup of Starboard, its plug-ins, the set-up files and every app's settings and database, encrypted with a password you choose, on another disk, keeping the newest 5; it says which disk and warns when the folder is on the system disk. When backups are made can be Manual, Weekly or Nightly, and Copies off this computer sends each backup to another disk, a network share or your own rclone remote. A backup restores onto a fresh install in both set-ups. (DASH-260, DASH-17, DASH-380)
- **Clean up:** System, Clean up lists what is left over (removed plug-ins, an unfinished backup's work folder, older update copies) with sizes and moves what you choose to the holding folder, where each thing can be put back, or deleted for good after you confirm with your password. Settings, Updates, Restore keeps the copies of the last 5, 10 or 20 versions. (DASH-77, DASH-109)
- **After an unexpected shutdown:** After a power cut or a crash, Starboard checks once the folders it watches, the pool, any pool job or full backup that stopped part way, and the apps, then says what it found on System, Overview and through Alerts. (DASH-88)
- **Server care from the terminal:** ./settings.sh changes settings through Starboard with your password, starting with automatic updates, and sudo deploy/headless.sh readies a computer to run with no screen (never sleeping, the lid ignored, starting again after a crash), showing each change first and with --undo to put them back. (DASH-89, DASH-90)
- **Where you are and your keyboard first:** The Run first script and both set-ups ask where the computer is and which keyboard it has, as lists you move through with the arrow keys, then set the time zone, keyboard layout and language; the apps take the time zone. The keyboard step says where symbols such as |, \ and # really are on UK, Irish, German, French, Spanish and Italian keyboards. (DASH-259, DASH-112)
- **Audio description in the first set-up:** Both set-ups' Jellyfin extras step offers Audio description, unticked. Ticking it makes Settings, Plug-ins offer the Audio description plug-ins from the Catalogue; Not now forgets it. (DASH-399)
- **Own style colours and design pictures:** Starboard's own style has six colours to choose from: Teal (the standard), Indigo, Forest, Plum, Ember and Graphite; Reset style comes back to them, and the own style comes first in the Styles gallery. Default design and Display's Design list show a small picture of each design. (DASH-388, DASH-315)
- **Moving in from other apps, step by step:** Move them into Reelix, Take over my apps, Roll back and Clear away open a dialog with each step and its result, and carry on if it is closed. Install apps can do the move too, more site keys are read for you, and after the move you can review the held sites, add titles that did not match (they wait with their IDs and are added once they match), choose Reelix's own requests or keep Seerr, and clear away the apps Reelix replaced into a holding folder. (DASH-127, DASH-128, DASH-129, DASH-190 to DASH-192, DASH-249 to DASH-254)
- **Restart in Manage apps:** Each app's menu has Restart. Restarting Gluetun also restarts the apps that use its network.
- **Comparisons in the help:** A new help section compares Starboard's stack with other media server stacks, with the memory and processor measured at rest, how the tests were run and how to repeat them. (DASH-398)

### Changed
- **Settings pages on the second menu:** The parts of Settings, General (now Names and apps, Appearance, Pages and lists, Download hours, and Logs and feedback), Downloads (VPN, Usenet, Download hours), Radio, Performance and Security are each a page of their own on the second menu, and each page asks only for what it shows. Style is now Appearance, with the accessibility options. Old links still work. (DASH-389, DASH-390, DASH-391)
- **Settings that work the same everywhere:** Every folder is chosen with the location picker; switches and choices apply at once with a saved note beside them instead of a pop-up message; typed text has one Save per section; lists such as Reelix's sites and API keys are rows that open; and danger zones come last. (DASH-308, DASH-310, DASH-353)
- **The same item for the same job everywhere:** Across Apps, the Dashboard, the Library, Discover, Coming up, Activity, System and Install apps: app cards show at most two chips and one button, filters that pick one of several are segmented controls, a state sits on its title's line, lists open in slide-outs instead of dialogs, and one primary button is in view. Apps, Updates updates the apps you tick, and Still to set up has one button and shows only the part each step needs. (DASH-309)
- **Both set-ups ask the same questions:** The browser and terminal set-ups ask the same things in the same order, with the same words. Let me choose starts from the recommended apps (Basics), films are Films, not movies, and Reelix's set-up code is read for you so you never see a second code. The set-ups now warn when the apps ticked need more memory than the computer has, leave out apps that do not run on a Raspberry Pi, and stop on a 32-bit system or with under 10 GB free. (DASH-83, DASH-96, DASH-114, DASH-271)
- **Lighter on memory and processor:** Heavy jobs (the watch history import, listening progress, Live TV and building Library lists) run in a short-lived process of their own, so the server stays small: building a 10,000-film list now leaves it at 35 MB. The hourly watch history import reads the whole library only when something changed (a run with nothing new from 1.7 seconds to 0.01), the Library keeps a list it has just read for 2 minutes (a search of 10,000 films from 172 ms to 13 ms), plug-in files are read once while unchanged, and an idle Live TV plug-in wakes 12 times a minute instead of 120. (DASH-79, DASH-397)
- **Load more as you scroll:** Library walls, Wanted and History load the next page as you scroll, say how many more are shown, leave focus where it was, and pause after three pages so the footer stays in reach; Show 40 more always works. (UX-52, DASH-277)
- **Footer, release notes and loading:** The footer says Upgrade available when a newer release is out, and its Release notes link says it opens a slide-out; Sign in and Set up have no footer. A thin line under the menu shows a page is loading, and Settings pages use the full width. (DASH-104, UX-50)
- **Network logos in their own colours:** Network logos keep their own colours, on a dark or light tile chosen by their tone.
- **Seerr, Overseerr and Jellyseerr:** Seerr is recognised wherever Overseerr or Jellyseerr are, including by its image when taking over your apps, and has its own icon. (DASH-405)
- **Memory figures in the help:** The help and Install apps give Reelix's and Jellyfin's memory at rest and while working, measured on a large library, so each install's range is wider and more honest. (DASH-405)
- **The plug-ins collection needs this release:** Most plug-ins in TheMightyTRex/starboard-plugins now ask for plug-in API 1.8 to 1.13, which this release brings; Starboard 0.16.5 and earlier had plug-in API 1.1.

### Removed
- **Note an issue:** The old Note an issue tester has gone; Send feedback replaced it. Notes it saved are still listed in Settings, General, Logs and feedback. (DEV-05)
- **Storyarr:** Storyarr, retired on 11 November 2026, is no longer offered by Install apps or the set-ups. A server that already runs it keeps it and still updates. (DASH-405)

### Fixed
- **An update could stop at its backup:** On a server with plug-ins, ./update.sh stopped before updating anything, because each plug-in's own data folder belongs to the plug-in's user and could not be read for the backup. The backup now leaves those folders out (the plug-ins' settings are still in it), and going back after a failed start keeps them with their plug-in. Updates from this version on use the fixed script.
- **Bringing in books, audiobooks and radio:** Bringing in audiobooks and books sends the quality profile Reelix needs, and their matches read well in the list; radio shows match only when the titles agree, with English stations first. (DASH-392)
- **Issues reported on GitHub:** Download states such as post_processing show as words (#7); a plug-in's Activate sits under its state (#8); Sign out is in the side menu (#9); Manage's rows and the Advanced settings switch line up (#10, #11, DASH-413); two-tone logos are legible (#12, #13); an opened collection takes the page heading with Add missing on its line (#14, #15); and Discover's buttons line up, its rows with arrows and fades (#16, #17).
- **Apps on the VPN after Gluetun restarts:** Apps on Gluetun's network rejoin it after Gluetun restarts or is made again, and the VPN apps check runs every 5 minutes whether or not Alerts is active. (DASH-394)
- **Accessibility:** 48 findings from the accessibility check are fixed, and a screen reader keeps its place: a page drawn again never sends focus to the top, whole lists are no longer read out, form slide-outs start in their first field and Show more moves to the first new row.
- **Backups and moves that fail:** A full backup that fails sends the backup alert and leaves no part copy behind. When qBittorrent stops accepting sign-ins after wrong passwords, the move says so, for how long and how to clear it, and the steps after a stopped move say they did not start. (DASH-78)
- **Plug-in pages:** A saved setting reaches a running plug-in at once, a button without an ID works, no stray null shows on pages with no introduction, and the Catalogue no longer scrolls sideways on a phone. (DASH-357)
- **API checks:** The API description, its reference, the contract tests and every example plug-in are checked in one command on every push; the description had fallen behind the routes. (DASH-281)

### Security
- **Folders checked where they are used:** The folder picker follows links and refuses a folder outside the usual places (a link under /mnt to /etc is refused), and a plug-in's folder must sit directly in Starboard's plug-ins folder. (code scanning)
- **Passwords kept out of logs:** The set-up password is hidden from every log line, even when an app repeats it in an error message. (code scanning)
- **Exact addresses for YouTube and Spotify:** A link counts as YouTube or Spotify only when its host is exactly theirs, so a link that mentions spotify.com in its path is not taken as Spotify. (code scanning)
- **No slow checks on crafted input:** The TMDB key check and the check of a plug-in's settings values (code scanning #53) no longer slow down on long crafted input: a 210 KB value is checked at once. (code scanning)
- **TLS 1.2 for news servers:** Connections to a news server over SSL need TLS 1.2 or newer. (code scanning)
- **Plug-ins see only what you approve:** A plug-in's key reads only what you approved when you added it, catalogue versions are checked against their checksums, and a plug-in that adds files to your media runs as the media folder's owner, never as root. (DASH-330, DASH-410)
- **API keys that cannot change your server:** No API key can change settings, keys, plug-ins or the install; each change made with a key is in the audit log; and the log a key can read has addresses, names and keys taken out. (DASH-274, DASH-76)
- **Backups and keys stay private:** Full backups are encrypted (AES-256-GCM) with a password Starboard never stores; a share's password and an rclone set-up stay in Starboard's own folder, never in a backup or sent to the page; site keys typed for a move are never stored or logged; and the rclone set-up handed to a copy is readable by Starboard alone (found by this release's scan). (DASH-260, DASH-380, DASH-128)
- **Checks:** The unit tests (also as another user), the browser journeys, the accessibility checks, the API contract tests and example plug-ins, the help check, the private details check and the full security scans, with CodeQL, ran on this release.

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

[Unreleased]: https://github.com/TheMightyTRex/starboard/compare/v0.31.0...HEAD
[0.31.0]: https://github.com/TheMightyTRex/starboard/compare/v0.30.0...v0.31.0
[0.30.0]: https://github.com/TheMightyTRex/starboard/compare/v0.29.0...v0.30.0
[0.29.0]: https://github.com/TheMightyTRex/starboard/compare/v0.28.0...v0.29.0
[0.28.0]: https://github.com/TheMightyTRex/starboard/compare/v0.27.0...v0.28.0
[0.27.0]: https://github.com/TheMightyTRex/starboard/compare/v0.26.0...v0.27.0
[0.26.0]: https://github.com/TheMightyTRex/starboard/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/TheMightyTRex/starboard/compare/v0.24.0...v0.25.0
[0.24.0]: https://github.com/TheMightyTRex/starboard/compare/v0.23.0...v0.24.0
[0.23.0]: https://github.com/TheMightyTRex/starboard/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/TheMightyTRex/starboard/compare/v0.21.0...v0.22.0
[0.21.0]: https://github.com/TheMightyTRex/starboard/compare/v0.20.2...v0.21.0
[0.20.2]: https://github.com/TheMightyTRex/starboard/compare/v0.20.1...v0.20.2
[0.20.1]: https://github.com/TheMightyTRex/starboard/compare/v0.20.0...v0.20.1
[0.20.0]: https://github.com/TheMightyTRex/starboard/compare/v0.19.1...v0.20.0
[0.19.1]: https://github.com/TheMightyTRex/starboard/compare/v0.19.0...v0.19.1
[0.19.0]: https://github.com/TheMightyTRex/starboard/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/TheMightyTRex/starboard/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/TheMightyTRex/starboard/compare/v0.16.5...v0.17.0
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
