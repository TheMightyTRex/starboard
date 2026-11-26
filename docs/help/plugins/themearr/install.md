# Themearr: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Themearr from Starboard's **Catalogue**, where it is listed under **Apps you can add**. Starboard shows what it may do and tests it before anything is added. At the end, Themearr is active, reads your films from Reelix, and has its own page on your home network.

## Before you begin

- Starboard with plug-in API 1.14 or later.
- Reelix added to Starboard, in **Settings**, then **Apps**. Starboard gives Themearr Reelix's address and key, so you do not enter them.
- Jellyfin, which plays the theme tunes on each film's page.
- A RapidAPI account subscribed to the youtube-mp36 service, for fetching the tunes. Its free plan has a monthly limit. Without it, Themearr reads your films but fetches no tunes. Read [Settings](../themearr/settings.md).
- Your Starboard password. Adding and removing a plug-in ask for it.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Use Reelix's API key, kept by Starboard (`reelix:key`) | High |
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |
| Open its own web page on your home network, at a port Starboard chooses (`network:port`) | Medium |

What it runs:

- **main:** a small helper. It reaches only Starboard and Themearr, on its own network: it cannot reach your home network or the internet. It can use its own folder in Starboard's data (`data/plugins/themearr`).
- **app:** Themearr. It reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/themearr`) and the `movies` folder in your media folder, to read and change, as the media folder's owner. Its web page is on your home network at port 8080 when that port is free, or the next free one.

What it changes in your films folder: it adds one file, `theme.mp3`, to each film's folder. It changes no film and deletes nothing there. Removing the plug-in leaves the tunes where they are.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its images are pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 64 MB of memory and 0.25 of a processor core at most.
- **app:** 512 MB of memory and 1 processor core at most, and 256 processes.

Measured:

- 47.6 MiB at rest as Starboard runs it, with no films yet: main 14.0 MiB and app 33.6 MiB (17 November 2026). With a test library read from Reelix, Themearr itself was about 57 MiB.

Themearr's image is about 1 GB to download, as it brings its own copy of FFmpeg.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Apps you can add**, find **Themearr** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Themearr**. To stop, select **Cancel**: nothing is installed.
5. Themearr's own tab opens under **Settings**, then **Plug-ins**, and Starboard activates it: its **State**, in **General**, says **Active**. If it needs settings first, it says what to enter: save them, then select **Activate**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/themearr/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Set it up

1. Wait up to 2 minutes for its **Film theme tunes** card or tab to say it reads your films from Reelix.
2. On Themearr's tab, under **Fetching theme tunes**, enter your **RapidAPI key** and **RapidAPI user name**, and select **Save**. Starboard passes them to Themearr.
3. To open Themearr's own page, open **Sign in to Themearr** on its tab and copy the access token.
4. Under **Its web page**, select **Open Themearr**. Paste the token into Themearr's **Access token** box. Each web browser asks once.

Themearr reads Reelix's films every 15 minutes and fetches a tune for each new one by itself, unless you deactivate **Fetch tunes for new films by itself**.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Themearr**.
2. Under **Remove**, select **Remove Themearr**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted: the `theme.mp3` files stay in your film folders, and Jellyfin carries on playing them.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Themearr does](../themearr/README.md)
- [Settings](../themearr/settings.md)
- [Problems](../themearr/problems.md)
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
