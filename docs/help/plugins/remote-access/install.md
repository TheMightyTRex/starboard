# Remote access: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Remote access from Starboard's **Catalogue**, where it is listed under **Network**. Starboard shows what it may do and tests it before anything is added. At the end, Remote access is active and its card is ready for your dashboard.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../remote-access/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.
- A 64-bit computer (amd64 or arm64). There is no build for 32-bit Arm, such as older Raspberry Pis, because Cloudflare does not make cloudflared for it.
- A Tailscale account, or a Cloudflare account with a tunnel. Tailscale is recommended.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Your apps and whether they answer (`apps:read`) | Low |
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |

What it runs:

- **main:** reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/remote-access`).

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 128 MB of memory and 0.5 of a processor core at most.

Measured:

- About 20 MB with nothing chosen, 22 to 32 MB with Tailscale waiting to sign in, and 20 to 30 MB with Cloudflare Tunnel, and 0.01 to 0.03% of a core at rest (13 November 2026).

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Network**, find **Remote access** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Remote access**. To stop, select **Cancel**: nothing is installed.
5. Remote access's own tab opens under **Settings**, then **Plug-ins**. Select **Activate**. Its state changes to **Active**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/remote-access/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Set it up with Tailscale

Your phone joins your own private network, a tailnet, and the shared apps answer there. Nothing is open to the internet.

1. In your own Tailscale admin page, go to **Settings**, then **Keys**, and make an auth key. It starts with `tskey-auth-`.
2. In Starboard, go to **Settings**, then **Plug-ins**, then **Remote access**.
3. In **Connect with**, choose **Tailscale (recommended)**.
4. In **Tailscale auth key**, paste the key.
5. Select **Save**.
6. Wait for the card or **Addresses away from home** to say **Connected**.
7. Install Tailscale on your phone and sign in to the same tailnet.
8. Away from home, use the addresses in **Addresses away from home**, such as `http://<its Tailscale address>:8095` for Starboard.

To sign in without a key, choose **A sign-in link** in **Sign in with** instead of steps 1, 4 and 5. Open the link that shows in **Addresses away from home** on any device, sign in to your own Tailscale account and approve this computer.

## Set it up with Cloudflare Tunnel

You get a web address of your own, such as `https://tv.example.org`, through Cloudflare.

1. In Cloudflare's dashboard, go to **Networks**, then **Tunnels**, and copy your tunnel's token. The whole command Cloudflare shows is fine too.
2. In Cloudflare, add a public hostname for each app, pointing at `http://localhost:8095` for Starboard, `http://localhost:8096` for Jellyfin or `http://localhost:13378` for Audiobookshelf, and nothing else.
3. Protect Starboard's hostname with Cloudflare Access. Without it, Remote access stops the tunnel.
4. In Starboard, go to **Settings**, then **Plug-ins**, then **Remote access**.
5. In **Connect with**, choose **Cloudflare Tunnel**.
6. In **Cloudflare Tunnel token**, paste the token.
7. Select **Save**.
8. Add Starboard's hostname to `STARBOARD_ALLOWED_HOSTS` in Starboard's settings file, so Starboard answers to it.
9. Select **Test remote access**.

Cloudflare's terms limit how much video its free service carries, so use Tailscale to watch Jellyfin away from home.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Remote access**.
2. Under **Remove**, select **Remove Remote access**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Remote access does](../remote-access/README.md)
- [Settings](../remote-access/settings.md)
- [Problems](../remote-access/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
