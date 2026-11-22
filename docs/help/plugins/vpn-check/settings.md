# VPN check: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

VPN check's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **VPN check**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Your home's public address** | Optional, such as 203.0.113.7. If the VPN ever shows this address, the card says **Problem**: your downloads are not hidden. | Empty |
| **Check every** | How often it asks, through the VPN, which address your downloads come from. A number from 5 to 240 minutes. | 15 minutes |

## Buttons

These are on VPN check's tab.

- **Check now** checks through the VPN straight away and says the address and place it found, such as "Through the VPN: 198.51.100.23 in Amsterdam". If the VPN does not answer, Starboard shows what went wrong.

## Things to note

- **Your home's public address** is used straight away, at the next card refresh.
- A new **Check every** is used after VPN check starts again: select **Deactivate**, then **Activate**. Until then it keeps checking as often as before.
- To find your home's public address, find it from a device on your home network that does not use the VPN, or in your router.
- Each check sends one request to ipinfo.io, through the VPN. Nothing else is sent anywhere.
- It only reads. It never changes your VPN or stops downloads when the VPN shows your home address.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../vpn-check/install.md)
- [Dashboard card](../vpn-check/dashboard-card.md)
- [Problems](../vpn-check/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
