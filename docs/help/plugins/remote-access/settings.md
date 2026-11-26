# Remote access: Settings
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Remote access's settings are on its own tab: go to **Settings**, then **Plug-ins**, then **Remote access**. Starboard draws them and keeps them; secrets are never shown again once saved.

## Settings

| Setting | What it does | Default |
|---|---|---|
| **Connect with** | Tailscale joins your phone to home privately. Cloudflare Tunnel gives a web address of your own, behind Cloudflare Access. One of: Nothing yet, Tailscale (recommended), Cloudflare Tunnel. | Nothing yet |
| **Addresses away from home** | A page of its own on Remote access's tab. It shows how it connects and the state of the connection, the Tailscale sign-in link when one is needed, and each shared app's address away from home with **Test**. It also lists the download apps, which are never shared. **Test all** tests every shared app. | None |

## Tailscale

| Setting | What it does | Default |
|---|---|---|
| **Sign in with** | With a link, the address to open shows in Addresses away from home. One of: An auth key you paste, A sign-in link. | An auth key you paste |
| **Tailscale auth key** | Make one in your own Tailscale admin page, Settings, Keys. It starts with tskey-auth-. Kept secret by Starboard: it is never shown again. | Empty |
| **Name on your tailnet** | Letters, numbers and hyphens, such as starboard. Words. | starboard |

## Cloudflare Tunnel

| Setting | What it does | Default |
|---|---|---|
| **Cloudflare Tunnel token** | From Cloudflare's dashboard, Networks, Tunnels. Point each public hostname at http://localhost:8095, 8096 or 13378. Kept secret by Starboard: it is never shown again. | Empty |

## What to share

| Setting | What it does | Default |
|---|---|---|
| **Share Starboard** | Starboard's own pages, away from home. Activated or deactivated. | Activated |
| **Share Jellyfin** | Jellyfin, so the apps on phones and televisions work away from home. Activated or deactivated. | Activated |
| **Share Audiobookshelf** | Shared only when Audiobookshelf is in Starboard's apps. Download apps are never shared. Activated or deactivated. | Activated |

## Buttons

These are on Remote access's tab.

- **Test remote access** checks that each shared app answers Remote access. With Cloudflare Tunnel, it also checks that Starboard answers to the name on its route. Starboard says what it found in **Actions**, and each app's result shows in **Addresses away from home**.
- **Start remote access again** stops Tailscale or Cloudflare Tunnel and starts it with the saved settings. Use it after fixing something outside Starboard, such as a route in Cloudflare's dashboard.

The buttons are in **Actions**, and work only while Remote access is active.

## Things to note

- **Connect with**, **Sign in with** and the switches are saved as soon as you change them. Select **Save** to keep a key, token or name.
- When you change how it connects, the key, the token or the name, Remote access stops and starts again with them, within about 10 seconds.
- Only Starboard, Jellyfin and Audiobookshelf can be shared. qBittorrent, NZBGet, SABnzbd, Reelix and the other apps are never reachable this way.
- **Share Audiobookshelf** and **Share Jellyfin** work only for apps in Starboard's apps. Remote access reads their addresses from there every 5 minutes.
- With Cloudflare Tunnel, a route to an app you have not shared stops the tunnel. Share the app or delete the route.
- Starboard answers only to names it knows. To open Starboard by a Cloudflare name, or by its name on your tailnet, add that name to `STARBOARD_ALLOWED_HOSTS` in Starboard's settings file.
- Keys and tokens never go on a command line or in the log.
- Settings are kept when you update or deactivate it, and when you remove it they stay in its folder.

## Find out more

- [Install](../remote-access/install.md)
- [Dashboard card](../remote-access/dashboard-card.md)
- [Problems](../remote-access/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
