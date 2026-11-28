# Watching now: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Watching now from Starboard's **Catalogue**, where it is listed under **Jellyfin**. Starboard shows what it may do and tests it before anything is added. At the end, Watching now is active and its card is ready for your dashboard.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../watching-now/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.
- Jellyfin added to Starboard, in **Settings**, then **Apps**. Watching now uses the key Starboard keeps for it. Without it, the card says "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps".

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Use Jellyfin's API key, kept by Starboard (`jellyfin:key`) | High |
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |

What it runs:

- **main:** reaches your home network and the internet, and this computer as `host.docker.internal`.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 48 MB of memory and 0.1 of a processor core at most.

These figures are the most it may use.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Jellyfin**, find **Watching now** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Watching now**. To stop, select **Cancel**: nothing is installed.
5. Watching now's own tab opens under **Settings**, then **Plug-ins**, and Starboard turns it on: its **State**, in **General**, says **Active**. If it needs settings first, it says what to enter: save them, then select **Turn on**.
6. Add its card to your dashboard. Read [Dashboard card](../watching-now/dashboard-card.md).

There is nothing else to set up: it has no settings of its own.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/watching-now/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Watching now**.
2. Under **Remove**, select **Remove Watching now**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Turn off** on its tab: its settings and folder are kept.

## Find out more

- [What Watching now does](../watching-now/README.md)
- [Settings](../watching-now/settings.md)
- [Problems](../watching-now/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
