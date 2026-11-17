# VPN check: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

VPN check 1.1.3 is the latest version. It needs Starboard with plug-in API 1.14 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 1.1.3 | 1.14 or later | 17 November 2026 |
| 1.1.2 | 1.14 or later | 17 November 2026 |
| 1.1.1 | 1.14 or later | 16 November 2026 |
| 1.1.0 | 1.14 or later | 15 November 2026 |
| 1.0.0 | 1.1 or later | 12 November 2026 |

The catalogue offers each Starboard the newest version it can run, so an older Starboard keeps an earlier version.

## What is new in 1.1.3

Changed:

- **Clearer words:** the hint and the card's example use addresses kept for examples, and the hint says the card says Problem, not what colour it turns.
- **Logo description:** where its logo stands on its own, a screen reader says "VPN check logo", the plug-in's name, instead of a description of the symbol.

## What is new in 1.1.2

Changed:

- **Shared helper:** the helper every example shares sends Jellyfin's key the way Jellyfin 12 asks for it. This plug-in does not ask Jellyfin anything, so it works as before.

## What is new in 1.1.1

Changed:

- **Lighter at rest:** it wakes about once a minute while nothing asks it anything, not twice a second, and writes nothing to its folder when a run goes well.
- **Starts faster:** its image comes with Python's modules already compiled, so a start takes about a quarter of the processor time.

## What is new in 1.1.0

Added:

- **A logo** in Settings, Plug-ins, in the Catalogue and on its dashboard cards.
- **Its cards say how things are:** a status and when they last changed, in the grey band at the top of each card.

Changed:

- Needs Starboard with plug-in API 1.14 or later. A Starboard with an older plug-in API keeps version 1.0.0.

## What is new in 1.0.0

Added:

- Shows the address and country your downloads use through the VPN, and warns if it is your home address.

## How an update is kept safe

- VPN check has no step before an update: Starboard stops it, installs the new version and starts it again.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, VPN check has an **Update** chip in **Manage**.
2. Select **VPN check** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update VPN check**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On VPN check's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [VPN check's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/vpn-check/CHANGELOG.md)
- [Problems](../vpn-check/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
