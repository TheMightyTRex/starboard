[Help centre](../README.md) · Guides

# Use Starboard away from home safely

This guide helps you open Starboard on your phone when you are out, without putting your server on the open
internet. It is for people who already use Starboard at home. A VPN (virtual private network) app takes about
30 minutes to set up.

**Never forward Starboard's port on your router to the internet.** Anyone in the world could then try to
sign in. There are two safe ways.

## Before you begin

- Starboard works at home on your phone: [Open Starboard from a phone or another computer](../topics/open-from-another-device.md).
- **Who can open the dashboard** is set to your home network: [Choose who can open Starboard](../topics/choose-who-can-open-starboard.md).
- Your password is long and not used anywhere else: [Change your password](../topics/change-your-password.md).

## The steps at a glance

1. Choose a way: a VPN (simplest and safest) or a reverse proxy with HTTPS (for people with their own domain).
2. Set it up.
3. Open Starboard from your phone away from home.
4. Add the outside address for your apps.

```mermaid
flowchart LR
    A["1. Choose a way"] --> B{"VPN or proxy?"}
    B -- VPN --> C["2. Set up the VPN"]
    B -- Proxy --> D["2. Set up the reverse proxy"]
    C --> E["3. Open it from your phone"]
    D --> E
    E --> F["4. Outside addresses"]
```

## Step 1: Choose a way

- **A VPN** joins your phone to your home network wherever you are, so Starboard behaves exactly as it does at
  home. Nothing new is open to the internet. Tailscale and WireGuard are popular choices, and many routers have
  a VPN built in. Choose this if you are unsure.
- **A reverse proxy** puts Starboard at an address of your own, such as `starboard.example.com`, protected by
  HTTPS. It needs a domain name and more care. Choose this only if you are confident.

## Step 2: Set it up

- **VPN:** follow your VPN's own instructions to install it on the server and on your phone. Starboard needs
  no changes.
- **Reverse proxy:** follow [Put Starboard behind a reverse proxy](../topics/reverse-proxy.md).

## Step 3: Open Starboard from your phone away from home

Switch your phone to mobile data, with Wi-Fi deactivated, and open Starboard's address: the home address through
the VPN, or your own address through the proxy.

**It worked when** Starboard asks you to sign in.

## Step 4: Add the outside address for your apps

Each app can have an outside address, so its card opens the right link when you are away. Add it in the app's
settings: [Change or remove an app](../topics/change-or-remove-an-app.md).

## What next

- [Sign out everywhere](../topics/sign-out-everywhere.md) if you lose a phone.
- [Activate alerts](../topics/activate-alerts.md), so you hear about problems wherever you are.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
