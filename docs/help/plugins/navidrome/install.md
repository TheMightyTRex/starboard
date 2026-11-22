# Navidrome: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Navidrome from Starboard's **Catalogue**, where it is listed under **Apps you can add**. Starboard shows what it may do and tests it before anything is added. At the end, Navidrome is active, with its own page on your home network.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../navidrome/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |
| Open its own web page on your home network, at a port Starboard chooses (`network:port`) | Medium |

What it runs:

- **app:** reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/navidrome`), the `music` folder in your media folder, to read only. Its web page is on your home network at port 4533 when that port is free, or the next free one.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **app:** 256 MB of memory and 0.5 of a processor core at most, and 128 processes.

Measured:

- 20.0 MiB at rest as Starboard runs it, with an empty library (13 November 2026). A real library uses more.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Apps you can add**, find **Navidrome** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Navidrome**. To stop, select **Cancel**: nothing is installed.
5. Navidrome's own tab opens under **Settings**, then **Plug-ins**, and Starboard activates it: its **State**, in **General**, says **Active**. If it needs settings first, it says what to enter: save them, then select **Activate**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/navidrome/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

### Open it

Navidrome's tab shows its address on your home network, with **Open**. Anyone on your home network can open that page, so set the app's own password straight away.

## Set it up

1. On Navidrome's tab, select **Activate** if it is not active yet.
2. In **Its web page**, select **Open Navidrome**.
3. Make the first account. It is Navidrome's admin, so give it a strong password.
4. Put your music in `music` in your media folder. Navidrome reads it there, read only.
5. In your Subsonic app, such as Symfonium, Substreamer, Amperfy or play:Sub, add a server with the address Starboard shows, such as `http://192.168.1.20:4533`, and the account you made.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Navidrome**.
2. Under **Remove**, select **Remove Navidrome**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Navidrome does](../navidrome/README.md)
- [Settings](../navidrome/settings.md)
- [Problems](../navidrome/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
