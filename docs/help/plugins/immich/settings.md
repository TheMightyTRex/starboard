# Immich: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Immich's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Immich**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Immich

| Setting | What it does | Default |
|---|---|---|
| **Immich's address** | Such as http://192.0.2.10:2283, without /api on the end. A web address. Required. | Empty |
| **API key** | Made in Immich under Account settings, API keys. Give it only the permissions server.statistics, server.storage and queue.read (job.read for an older Immich). Kept secret by Starboard: it is never shown again. Required. | Empty |

![Immich's settings, with Immich's address outlined](../../images/plugins/immich/settings-1-address.png)

![Immich's settings, with API key outlined](../../images/plugins/immich/settings-2-key.png)

## Good to know

- Make a key for Starboard alone, so you can remove it in Immich if you stop using the plug-in. Read only permissions are enough: it never changes anything.
- Nothing is asked until a card is shown. Each answer is kept for a minute, so a dashboard with all three cards makes three small requests a minute at most.
- Where Starboard and Immich run on the same computer, use the computer's own address on your network, not `localhost`. Immich's plug-in runs in its own container.

## Find out more

- [Dashboard card](../immich/dashboard-card.md)
- [Problems](../immich/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
