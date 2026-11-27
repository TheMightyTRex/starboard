# UPS and power: Updates
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

UPS and power 0.1.0 is the first version. It needs Starboard with plug-in API 1.17 or later.

## Versions

| Version | Needs plug-in API | Released |
|---|---|---|
| 0.1.1 | 1.17 or later | Not released yet |
| 0.1.0 | 1.17 or later | 25 November 2026 |

## What is new in 0.1.0

Added:

- **One card for your UPS:** on mains power or on battery, the battery charge, the time left and the load. The voltage and power used are in a list.
- **Alerts:** through Starboard, once when the mains power is lost, the battery is low, it needs replacing or the UPS cannot be reached. You get one more when each is over.
- **NUT or PeaNUT:** it reads NUT's own protocol, or PeaNUT's web address; you choose, and the UPS if there is more than one.
- **Light:** one small question a minute, about 32 MB of memory at most, and a short history kept for the sparkline.

## How an update is kept safe

- **Before the update** Starboard asks UPS and power to get ready: it starts nothing new and lets anything running finish, for up to 60 seconds. If it is not ready, nothing changes and Starboard says why.
- **After the update,** or after a Roll back, it carries on with its work.
- Starboard waits for the new version to answer. If it does not, Starboard goes back to the version you had by itself, with your settings as they were.
- Your settings and its folder are kept.

## Update it

1. Go to **Settings**, then **Plug-ins**. When a newer version is known, UPS and power has an **Update** chip in **Manage**.
2. Select **UPS and power** to open its tab.
3. In **Versions**, select **Update to** and the new version.
4. Read **What is new since** your version and **How the update is kept safe**, enter your Starboard password, and select **Update UPS and power**.
5. When the dialog says it is updated, select **Done**.

## Find out more

- [Settings](../ups-power/settings.md)
- [Problems](../ups-power/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
