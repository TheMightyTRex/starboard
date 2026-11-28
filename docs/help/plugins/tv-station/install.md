# Create your own TV channel: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Create your own TV channel from Starboard's **Catalogue**, where it is listed under **Jellyfin**. Starboard shows what it may do and tests it before anything is added. At the end, your first channel is in Jellyfin's Live TV.

## Before you begin

- Starboard with plug-in API 1.15 or later.
- Jellyfin added in Starboard, in **Settings**, then **Apps**, with its API key. Create your own TV channel reads your films and series from Jellyfin and plays them from there.
- Your Starboard password. Adding and removing a plug-in ask for it.
- A computer with a desktop browser. Setting up channels, the schedule grid and the broadcast pack are made for a computer; on a phone or tablet, the grid says to use a computer. The dashboard card works anywhere.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Use Jellyfin's API key, kept by Starboard (`jellyfin:key`) | High |
| Reach other computers on your home network (`network:lan`) | Medium |
| Open its own web page on your home network, at a port Starboard chooses (`network:port`) | Medium |

What it runs:

- **main:** reaches your home network, so Jellyfin can read its channel list, guide and streams. It can use only its own folder in Starboard's data (`data/plugins/tv-station`). It does not mount your media folder: it plays everything through Jellyfin.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 768 MB of memory and 2 processor cores at most.

Measured on 17 November 2026: 16.4 MiB of memory and no measurable processor (0.00%) at rest, and about 140 MiB and 0.9 of a processor core while one channel played at 720p with its on-screen logo. Each channel being watched adds about the same again.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Jellyfin**, find **Create your own TV channel** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Create your own TV channel**. To stop, select **Cancel**: nothing is installed.
5. Create your own TV channel's own tab opens under **Settings**, then **Plug-ins**, and Starboard turns it on: its **State**, in **General**, says **Active**. If it needs settings first, it says what to enter: save them, then select **Turn on**.
6. Within a minute, Create your own TV channel adds its channel list and guide to Jellyfin's Live TV, at the address Starboard gives it on your home network (Starboard 0.23.0 and later). With an older Starboard, next to its web page's address, select **Open** once, so it learns that address.
7. In **Station**, enter the **Station name**.
8. Open **Channels** and add your first channel. Read [Settings](../tv-station/settings.md).
9. Add its card to your dashboard. Read [Dashboard card](../tv-station/dashboard-card.md).

Jellyfin reads the new guide within a minute. In Jellyfin, go to **Live TV**: your channels are first, from number 1.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/tv-station/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Create your own TV channel**.
2. Under **Remove**, select **Remove Create your own TV channel**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its container stops and goes. Nothing is deleted: its channels, idents, clips and logos stay in its folder. In Jellyfin, go to **Dashboard**, then **Live TV**, and remove the tuner and the guide with the station's address, or its channels stay in the list with nothing to play.

To stop it for a while instead, select **Turn off** on its tab: its settings and folder are kept.

## Find out more

- [What Create your own TV channel does](../tv-station/README.md)
- [Settings](../tv-station/settings.md)
- [Problems](../tv-station/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
