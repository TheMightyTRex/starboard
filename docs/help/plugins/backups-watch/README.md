# Backups watch
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

The last run, size and failures of your Backrest or Kopia backups on a card, and an alert when one is overdue.

An example Starboard plug-in by TheMightyTRexUK, MIT licence.

## What it may do

- It reaches your home network and the internet.
- It alerts:send.
- It runs one small container (48 MB of memory at most).

## On the dashboard

- **Backups**: a status card.
- **Backup runs**: a list card.
- **Backup sizes**: a sparkline card.

## Settings

### The backup tool

- **Backup tool**: Backrest or Kopia. Duplicati is not offered yet: its server API could not be checked from its documentation.
- **Its address**: Such as http://192.0.2.10:9898 for Backrest, or https://192.0.2.10:51515 for the Kopia server.
- **User name**: Leave empty if the tool needs no sign-in. For Kopia, the server's user name.
- **Password**: The tool's password. Starboard never shows it again.
- **Accept a self-signed certificate**: For a Kopia server that makes its own certificate. Only on your own network.

### Alerts

- **Overdue after**: How many hours without a good run count as overdue. 36 suits a nightly backup.
- **Send alerts through Starboard**: Sends one alert when a backup is overdue or failed, and one when it is fine again, to where Starboard sends its own alerts.

## What it reads

- **Backrest:** its summary dashboard (`/v1.Backrest/GetSummaryDashboard`), one summary for each plan.
- **Kopia:** the server control API (`/api/v1/control/sources`), the last snapshot of each source.

Both are read only. Neither was tried against the real program when this version was written: read the help's
Problems page before relying on it.

## Updating

Before an update, it finishes any check or message it is part way through and starts no new one. So the update never cuts one short (plug-in API 1.14). What changed in each version is in [CHANGELOG.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/backups-watch/CHANGELOG.md), and Starboard shows it before you update.

## Add it

Needs Starboard with plug-in API 1.17 or later. A Starboard with an older plug-in API is offered the version before. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it under **System**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/backups-watch/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
