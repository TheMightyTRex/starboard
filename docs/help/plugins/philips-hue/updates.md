# Philips Hue: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Philips Hue 0.1.1 is the latest version, and the first. It needs Starboard with plug-in API 1.16 or later (Starboard 0.23.0).

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 0.1.1 | 1.16 or later | Not released yet |
| 0.1.0 | 1.16 or later | 20 November 2026 |

The catalogue offers each Starboard the newest version it can run. A Starboard with an older plug-in API is not offered Philips Hue.

## What is new in 0.1.0

Added:

- **Pairing on your home network:** give the bridge's address, or choose one found on the network, then press its link button. Nothing goes to the Hue cloud.
- **Lights three ways:** by room, by zone and by device type. Each light has on and off, brightness, and a colour or a white named in words.
- **A switch for every light** in a room, a zone, a type or the whole home. You can also set the brightness and colour of them all at once.
- **Scenes:** each room's and zone's scenes, to show one or turn the room off.
- **Schedules in words,** such as Every weekday at 07:00, Kitchen to 80%, with sunrise and sunset. Kept on the bridge, so they run while the plug-in rests.
- **When something plays:** a scene of your choice when someone starts playing something in Jellyfin, after sunset if you like.
- **Dashboard cards:** your rooms with their lights, and which rooms have lights on. Buttons to turn every light off or on.

## How an update is kept safe

- Philips Hue runs nothing in the background, so there is nothing to finish first: Starboard stops it, installs the new version and starts it again.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Starboard keeps your settings and its folder. That covers the bridge's address and key, your choice for **When something plays**, and its list of the schedules it made.
- Your schedules are kept on the bridge, so they run while it updates.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, Philips Hue has an **Update** chip in **Manage**.
2. Select **Philips Hue** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update Philips Hue**.
5. When the dialog says it is updated, select **Done**.

## Roll it back

1. On Philips Hue's tab, in **Versions**, select **Roll back to** and the version you had.
2. Enter your Starboard password and select **Roll back**.
3. When the dialog says it is back on that version, select **Done**.

Rolling back needs no download, and only one earlier version is kept. There is no earlier version of Philips Hue yet.

## Find out more

- [Update a plug-in and roll it back, in Starboard's help](../../topics/update-a-plugin.md)
- [Philips Hue's changes, in full](https://github.com/TheMightyTRex/starboard-plugins/blob/main/philips-hue/CHANGELOG.md)
- [Problems](../philips-hue/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
