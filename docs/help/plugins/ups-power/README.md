# UPS and power
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Load, battery and time left of your UPS on a card, and an alert when the mains power is lost, read from NUT or PeaNUT.

An example Starboard plug-in by TheMightyTRexUK, MIT licence.

## What it may do

- It reaches your home network and the internet.
- It alerts:send.
- It runs one small container (32 MB of memory at most).

## On the dashboard

- **Power**: a status card.
- **UPS details**: a list card.
- **Load and battery**: a sparkline card.

## Settings

### The UPS

- **Read the UPS through**: NUT is the Network UPS Tools server (upsd). PeaNUT is the web page that sits in front of NUT.
- **NUT server**: For NUT: its address, such as 192.0.2.10, or 192.0.2.10:3493 for another port. NUT must allow this computer to read (LISTEN and ACCESS in its upsd.conf).
- **PeaNUT's address**: For PeaNUT: such as http://192.0.2.10:8080.
- **UPS name**: Leave empty to use the first UPS the server lists. Otherwise the name in ups.conf, such as ups.
- **User name**: For PeaNUT only, when it asks for a sign-in. Leave empty otherwise.
- **Password**: PeaNUT's password. Starboard never shows it again.

### Alerts

- **Send alerts through Starboard**: Sends one alert when the mains power is lost, the battery is low, it needs replacing or the UPS cannot be reached. Sends one more when each is over, to where Starboard sends its own alerts.
- **Low battery at**: On battery, a charge at or under this counts as low. 0 leaves it to the UPS's own low battery flag.
- **Low battery under**: On battery, a time left at or under this counts as low. 0 leaves it to the UPS's own flag.

## What it reads

- **NUT:** the Network UPS Tools server (`upsd`, port 3493), with its text protocol: `LIST UPS`, then `LIST VAR <ups>`. It
  needs no sign-in to read, but `upsd.conf` must listen on an address this computer can reach, and `upsd.users` or
  access rules must allow it.
- **PeaNUT:** `GET /api/v1/devices/<ups>` (or `/api/v1/devices` for the first), with a sign-in when PeaNUT is set to ask for one.

Both are read only. Neither was tried against a real UPS when this version was written: read the help's Problems page
before relying on it.

## Heavy jobs on battery

A plug-in cannot pause Starboard's own heavy jobs, so this version only tells you: the card says **On battery** and an alert
goes out. Pausing them needs a new plug-in permission in Starboard.

## Updating

Before an update, it finishes any check or message it is part way through and starts no new one. So the update never cuts one short (plug-in API 1.14). What changed in each version is in [CHANGELOG.md](https://github.com/TheMightyTRex/starboard-plugins/blob/main/ups-power/CHANGELOG.md), and Starboard shows it before you update.

## Add it

Needs Starboard with plug-in API 1.17 or later. A Starboard with an older plug-in API is offered the version before. In Starboard, go to **Settings**, then **Plug-ins**, then **Catalogue**, and find it under **System**. Or, under **Add one from elsewhere**, give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/ups-power/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
