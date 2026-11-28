# Checkrr: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Checkrr from Starboard's **Catalogue**, where it is listed under **Apps you can add**. Starboard shows what it may do and tests it before anything is added. At the end, Checkrr is active, checks your films and series each Sunday night, and has its own page on your home network.

## Before you begin

- Starboard with plug-in API 1.14 or later.
- Your films in the `movies` folder and your series in the `tv` folder of your media folder, as Starboard sets them up.
- Your Starboard password. Adding and removing a plug-in ask for it.

## What it does with a bad file

Checkrr only reports. When a file fails its check, Checkrr adds it to its list of bad files, with the reason, and the plug-in's card and **Files that failed the check** page show it. That is all:

- It never deletes, moves, renames or replaces a file. It reads your `movies` and `tv` folders read only, so it cannot change them.
- It asks no app to replace a file: it is given no Reelix, Radarr, Sonarr or Lidarr, so its own way of replacing files, which deletes the file first, is never used.
- Replacing a bad file is up to you, such as by searching for the film or episode again in Reelix.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |
| Open its own web page on your home network, at a port Starboard chooses (`network:port`) | Medium |

What it runs:

- **main:** a small helper. It reaches only Starboard and Checkrr, on its own network: it cannot reach your home network or the internet. It can use its own folder in Starboard's data (`data/plugins/checkrr`).
- **app:** Checkrr. It reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/checkrr`), the `movies` folder in your media folder, to read only, and the `tv` folder in your media folder, to read only. Its web page is on your home network at port 8585 when that port is free, or the next free one.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its images are pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 64 MB of memory and 0.25 of a processor core at most.
- **app:** 512 MB of memory and 1 processor core at most, and 128 processes.

Measured:

- 19.0 MiB at rest as Starboard runs it, with an empty library: main 13.6 MiB and app 5.4 MiB (17 November 2026).

A check reads every file and runs FFprobe on each film and episode, so it uses a processor core while it runs. The first check of a large library takes hours; later checks skip files that have not changed since.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Apps you can add**, find **Checkrr** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Checkrr**. To stop, select **Cancel**: nothing is installed.
5. Checkrr's own tab opens under **Settings**, then **Plug-ins**, and Starboard turns it on: its **State**, in **General**, says **Active**. If it needs settings first, it says what to enter: save them, then select **Turn on**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/checkrr/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Set it up

There is nothing to set up. Checkrr checks your films and series each Sunday at 03:30, in the server's time zone.

1. To check now instead, select **Check now** on Checkrr's tab and confirm.
2. Add its **Damaged files** card to your dashboard, or open **Files that failed the check** on its tab, to find what it found.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Checkrr**.
2. Under **Remove**, select **Remove Checkrr**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted, and your media folder is not touched.

To stop it for a while instead, select **Turn off** on its tab: its settings and folder are kept.

## Find out more

- [What Checkrr does](../checkrr/README.md)
- [Settings](../checkrr/settings.md)
- [Problems](../checkrr/problems.md)
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
