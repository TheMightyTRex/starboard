# Changelog

## 0.1.3 (1 November 2026)

- Looks like Storyarr: its colours, its icons (Lucide) and its square tabs. The main menu and every sub-menu
  use the same tabs; on phones a menu drawer holds both.
- Settings is four pages with a sub-menu: Apps, General, Security and Updates. Old links still work.
- The installer and the setup page ask you to name your dashboard. Change it in Settings, General.
- Each app's own icon on its card, from the dashboard-icons collection. Starboard keeps a copy, so icons
  still show without the internet. Choose another icon in the app's settings.
- Apps are grouped by category: Watch, listen and request; Find and organise; Search and download;
  Dashboards and tools. New apps get a category chosen for them; change it in the app's settings. Health
  first still puts apps that are not responding at the top.
- A footer on every page: "Starboard: v" and the version, a link to the GitHub repository and to Updates.
- The version is only shown to people who have signed in.

## 0.1.2 (1 November 2026)

- Fixed: `./update.sh` made the new version's files readable by you only, so the container could not start
  and the roll-back failed the same way. The image now makes its files readable whatever the host's
  permissions, and the updater only keeps the backup private.

## 0.1.1 (1 November 2026)

- Passwords need 10 characters or more (was 12).
- Remember me on the sign-in and setup pages. Without it, you are signed out when the browser closes, or after
  a day. With it, you stay signed in for the number of days set in Settings, Security.
- The setup code stays the same when Starboard restarts or updates, so the code the installer printed keeps
  working until a password is set.

## 0.1.0 (1 November 2026)

- Apps, Search, Downloads, Coming up, System and Settings, each on its own page.
- Search Sonarr, Radarr, Lidarr and Readarr at once and add what you find.
- Five designs: Health first (the default), Tiles, Shelf, Command and Status board, plus the Display and
  accessibility panel.
- Installer (Docker or systemd) and updater with backup and automatic roll-back.
- Password sign-in with a one-time setup code; API keys never reach the browser.
- Open it from phones and other computers on your home network, or switch that off in Settings so only the
  computer it runs on can connect. Docker uses host networking for this.
- Phone layout on every page; add it to your home screen.
- Each app's home address and outside address on its card, each with a copy button. Both are on by default;
  turn them off in Settings, General. Apps saved as 127.0.0.1 open on the address your browser used, so they
  work from a phone.
- Downloads show the download client's own state, so a paused client shows Paused.
