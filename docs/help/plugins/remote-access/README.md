# Remote access
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard, Jellyfin and Audiobookshelf away from home through Tailscale or Cloudflare Tunnel, with no port opened on
your router. Download apps are never shared.

A Starboard plug-in by TheMightyTRexUK, MIT licence. Needs Starboard with plug-in API 1.14 or later.

Its image is for 64-bit computers only (amd64 and arm64): Cloudflare does not make cloudflared for 32-bit Arm, so
there is no arm/v7 build for older Raspberry Pis.

## Choose a way

- **Tailscale (recommended).** Your phone joins your own private network (a tailnet), and Starboard, Jellyfin and
  Audiobookshelf answer there at an address such as `http://<its Tailscale address>:8095`. Nothing is open to the internet.
  It runs in userspace networking: no device, no extra rights and no change to this computer's network.
  Sign in with an auth key you make in your own Tailscale admin page (**Settings**, **Keys**), or choose
  **A sign-in link** and open the link the plug-in shows.
- **Cloudflare Tunnel.** A web address of your own, such as `https://tv.example.org`, through Cloudflare. Paste the
  tunnel token from Cloudflare's dashboard (**Networks**, **Tunnels**; the whole command is fine too). Add each
  public hostname in Cloudflare pointing at one of these, and nothing else:

  | App | Service in Cloudflare |
  |---|---|
  | Starboard | `http://localhost:8095`, protected with Cloudflare Access |
  | Jellyfin | `http://localhost:8096` |
  | Audiobookshelf | `http://localhost:13378` |

  Starboard answers only to names it knows: add the name to `STARBOARD_ALLOWED_HOSTS`. Cloudflare's terms limit how
  much video its free service carries, so use Tailscale to watch Jellyfin away from home.

## Kept safe

- Only Starboard, Jellyfin and Audiobookshelf are forwarded, each by its own small forwarder inside the plug-in.
  qBittorrent, NZBGet, SABnzbd, Reelix and the other apps are never reachable this way.
- With Cloudflare, the plug-in reads the tunnel's routes and **stops the tunnel** if any route leads anywhere else,
  to an app you have not shared, or to Starboard without Cloudflare Access.
- A key or token that is missing or wrong is said plainly on the card and in **Addresses away from home**; a token
  Cloudflare refuses stops the tunnel rather than retrying for ever.
- Keys and tokens never go on a command line or in the log. The image is pinned by digest, and the Tailscale,
  cloudflared and Python images it is built from are pinned by digest too.

## What it may do

- It sees your apps and whether they answer (`apps:read`), to find Jellyfin and Audiobookshelf.
- It reaches your home network and the internet (`network:lan`).
- It runs one container, 128 MB of memory and half a core at most. Measured on 13 November 2026: about 20 MB with
  nothing chosen, about 22 to 32 MB with Tailscale waiting to sign in, about 20 to 30 MB with Cloudflare Tunnel, and
  0.01 to 0.03% of a core at rest.

## On the dashboard

- **Away from home**: a status card with the address to use and the state.

## Settings

- **Connect with**: Nothing yet, Tailscale or Cloudflare Tunnel.
- **Addresses away from home**: each shared app's address and state, with Test.
- **Tailscale**: Sign in with (an auth key or a sign-in link), the auth key, and the name on your tailnet.
- **Cloudflare Tunnel**: the tunnel token.
- **What to share**: Starboard, Jellyfin and Audiobookshelf, each activated by default.
- Buttons: **Test remote access** and **Start remote access again**.

## Add it

In Starboard, open **Settings**, **Plug-ins**, **Add a plug-in**, and give this address:

`https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/remote-access/starboard-plugin.json`

Or run `python3 install.py` in this folder.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
