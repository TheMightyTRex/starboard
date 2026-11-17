# VPN check: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add VPN check from Starboard's **Catalogue**, where it is listed under **Downloads**. Starboard shows what it may do and tests it before anything is added. At the end, VPN check is active and its card is ready for your dashboard.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../vpn-check/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.
- Your VPN set up in Starboard, with Gluetun running. VPN check runs inside Gluetun's network, so it reaches the internet as your downloads do.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Run inside your VPN connection (`network:vpn`) | Medium |

What it runs:

- **main:** reaches the internet through your VPN only, inside Gluetun's network. It asks ipinfo.io which address your downloads come from. It can use its own folder in Starboard's data (`data/plugins/vpn-check`).

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 48 MB of memory and 0.1 of a processor core at most.

These figures are the most it may use.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Downloads**, find **VPN check** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install VPN check**. To stop, select **Cancel**: nothing is installed.
5. VPN check's own tab opens under **Settings**, then **Plug-ins**. Select **Activate**. Its state changes to **Active**.
6. Optional: on its tab, enter **Your home's public address** and select **Save**, so the card warns you if the VPN ever shows it.
7. Add its card to your dashboard. Read [Dashboard card](../vpn-check/dashboard-card.md).

It checks for the first time a few seconds after it starts. Read [Settings](../vpn-check/settings.md).

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/vpn-check/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **VPN check**.
2. Under **Remove**, select **Remove VPN check**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What VPN check does](../vpn-check/README.md)
- [Settings](../vpn-check/settings.md)
- [Problems](../vpn-check/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
