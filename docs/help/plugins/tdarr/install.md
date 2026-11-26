# Tdarr: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Tdarr from Starboard's **Catalogue**, where it is listed under **Apps you can add**. Starboard shows what it may do and tests it before anything is added. At the end, Tdarr is active, with its own page on your home network.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../tdarr/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.
- If the main install already runs Tdarr: bring it in before you activate the plug-in, so its libraries, flows and history carry over. Read [Set it up](#set-it-up).

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |
| Open its own web page on your home network, at a port Starboard chooses (`network:port`) | Medium |

What it runs:

- **server:** reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/tdarr`), the `tdarr-cache` folder in your media folder, to read and change, the `movies` folder in your media folder, to read and change, the `tv` folder in your media folder, to read and change. Its web page is on your home network at port 8265 when that port is free, or the next free one.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **server:** 2048 MB of memory and 2 processor cores at most, and 512 processes.

Measured:

- 59.1 MiB at rest as Starboard runs it, with an empty library (13 November 2026).
- 748 MiB while it converted a file (13 November 2026).

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Apps you can add**, find **Tdarr** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Tdarr**. To stop, select **Cancel**: nothing is installed.
5. Tdarr's own tab opens under **Settings**, then **Plug-ins**, and Starboard activates it: its **State**, in **General**, says **Active**. If it needs settings first, it says what to enter: save them, then select **Activate**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/tdarr/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Set it up

### If the main install already runs Tdarr

When Tdarr is already on this computer, Starboard leaves the plug-in inactive after the install, so you can bring your Tdarr in first.

1. On Tdarr's tab, under **Your Tdarr**, select **Bring in the Tdarr you already have…**.
2. Read which folders Starboard copies: Tdarr's `server`, `configs` and `logs` folders.
3. Enter your Starboard password and select **Copy**.
4. Select **Activate** in **General**, **State**. Its page is on your home network at port 8265 when that is free, as it is once your old Tdarr is stopped.
5. Check the plug-in shows your libraries, then remove Tdarr from the main install: go to **Settings**, then **Install apps**, untick Tdarr and apply.

Starboard stops your Tdarr to copy its files whole. It does not remove it, and its own folders are never moved, changed or deleted. Its cache, the files part way through converting, is not copied. Its old folders (`config/tdarr`, beside the other apps' settings) stay until you move them to the holding folder in **System**, **Clean up**.

### A new Tdarr

1. Starboard activates Tdarr when it is installed, as there is no Tdarr to bring in. If its state is not **Active**, select **Activate** in **General**, **State**.
2. Go to **Settings**, then **Apps**, and select **Search for new apps**, so Starboard finds Tdarr and gives it a key.
3. If its tab says **Tdarr is not connected yet** under **Settings**, select **Connect Tdarr**. Tdarr restarts once.
4. Choose its libraries, what it does and when. Read [Settings](../tdarr/settings.md).

### Open it

Tdarr's tab shows its address on your home network, under **Its web page**, with **Open Tdarr**. Anyone on your home network can open that page.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Tdarr**.
2. Under **Remove**, select **Remove Tdarr**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted. Files it already changed in your media folder stay as they are.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Tdarr does](../tdarr/README.md)
- [Settings](../tdarr/settings.md)
- [Problems](../tdarr/problems.md)
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
