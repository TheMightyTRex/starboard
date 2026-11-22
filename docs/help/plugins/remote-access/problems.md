# Remote access: Problems
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Find what is wrong with Remote access from what its tab or its card says, then follow the numbered answer. **Addresses away from home**, on its tab, says the same with more detail.

```flow
title: Find your answer
start: Remote access is not working as it should
q: What does its tab say?
  Failed or Not answering -> 1
  Not supported -> 2
  Active, but the card is wrong -> q2
q2: What does the card say?
  Needs setting up -> 3
  Needs signing in or approving -> 4
  Not connected -> 5
  Stopped the tunnel to keep your apps safe -> 6
  Connected, but an address will not open -> 7
1: Start it again #start-it-again
2: Update it or update Starboard #update-it-or-update-starboard
3: Choose a way to connect #choose-a-way-to-connect
4: Sign in to Tailscale #sign-in-to-tailscale
5: Read why it is not connected #read-why-it-is-not-connected
6: Fix the routes in Cloudflare #fix-the-routes-in-cloudflare
7: Test each address #test-each-address
```

## Start it again

1. On Remote access's tab, read the message under its state: it says why it stopped.
2. Select **Try again**.
3. If it stopped soon after an update, select **Roll back to** and the version you had. Read [Updates](../remote-access/updates.md).
4. Still failing: go to **System**, then **Logs**, and find its name.

## Update it or update Starboard

Your Starboard's plug-in API is outside what this version of Remote access works with, so Starboard stopped it.

1. Select **Check for an update** on its tab.
2. If there is none, update Starboard. Read [Update Starboard](../../topics/update-starboard.md).

## Choose a way to connect

The card says "Not set up: choose Tailscale or Cloudflare Tunnel in its settings": **Connect with** is **Nothing yet**, so nothing runs.

1. Go to **Settings**, then **Plug-ins**, then **Remote access**.
2. In **Connect with**, choose **Tailscale (recommended)** or **Cloudflare Tunnel**.
3. Follow the steps in [Install](../remote-access/install.md) for the way you chose.

## Sign in to Tailscale

- **Needs signing in:** the card says "Open the sign-in link on any device and sign in to Tailscale". Open **Sign-in link for Tailscale** in **Addresses away from home**, sign in to your own Tailscale account and approve this computer. Remote access carries on by itself.
- **Needs approving:** the card says "Approve this device in Tailscale's admin page, Machines". Approve it there, and Remote access carries on by itself.

## Read why it is not connected

The card says **Not connected** and why. Do what it says:

- **"Paste a Tailscale auth key"** or **"Paste your Cloudflare Tunnel token"**: the key or token is empty. Paste it, or for Tailscale choose **A sign-in link** in **Sign in with**.
- **"That is not a Tailscale auth key"**: auth keys start with `tskey-auth-`. Make one in Tailscale's admin page, **Settings**, **Keys**, and paste it whole.
- **"That is not a Cloudflare Tunnel token"**: copy the long token after `--token` from Cloudflare's dashboard, **Networks**, **Tunnels**.
- **"Tailscale did not accept the auth key"**: it may be expired, used already or deleted. Make a new one and paste it.
- **"Cloudflare did not accept the tunnel token"**: the tunnel may have been deleted or its token changed. Copy the token again.
- **"could not be reached"**: check the server's internet connection. Remote access tries again by itself.

When you paste a new key or token and select **Save**, it starts again by itself.

## Fix the routes in Cloudflare

The card says "Stopped the tunnel to keep your apps safe" and names a route. Remote access reads the tunnel's routes and stops it when one is not safe.

1. In Cloudflare's dashboard, find the route the card names.
2. Point it at `http://localhost:8095`, `8096` or `13378`, or delete it. If it leads to an app you have not shared, share the app or delete the route.
3. If it leads to Starboard, protect it with a Cloudflare Access application, and tick **Protect with Access** on the route.
4. In Starboard, select **Start remote access again** in Remote access's **Actions**.

## Test each address

1. Go to **Settings**, then **Plug-ins**, then **Remote access**.
2. In **Addresses away from home**, select **Test all**.
3. Read what it says for each app:
   - **"Remote access cannot reach Starboard on the server"**: update Starboard in **Settings**, **Updates**, then select **Start again** on Remote access's page. Starboard 0.21.1 and later give plug-ins on the home network an address that reaches it.
   - **"Not checked: Remote access could not read Starboard's apps"**: the same cause as the one before. It goes once Remote access can reach Starboard.
   - **"is not in Starboard's apps, so it is not shared"**: add the app in **Settings**, **Apps** first.
   - **"is not answering"**: the app is not running, or has moved. Check it in **System**, **Apps**.
   - **"does not open at"** a name, or the steps to use your Tailscale name: in Starboard's folder on the server, add the name to `STARBOARD_ALLOWED_HOSTS` in the `.env` file (names separated by commas), then run `./update.sh`.
   - **"No route in Cloudflare leads to"** an app: add a public hostname for it in Cloudflare.
4. With Tailscale, check your phone is signed in to the same tailnet.

## Report a problem

If none of these helps, tell its maker, with what its tab, the card and **Addresses away from home** say: [the plug-ins' issues on GitHub](https://github.com/TheMightyTRex/starboard-plugins/issues).

## Find out more

- [Settings](../remote-access/settings.md)
- [Updates](../remote-access/updates.md)
- [If a plug-in will not add, in Starboard's help](../../topics/add-a-plugin.md#if-it-does-not-work)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
