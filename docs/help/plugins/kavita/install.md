# Kavita: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Kavita from Starboard's **Catalogue**, where it is listed under **Apps you can add**. Starboard shows what it may do and tests it before anything is added. At the end, Kavita is active, with its own page on your home network.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../kavita/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |
| Open its own web page on your home network, at a port Starboard chooses (`network:port`) | Medium |

What it runs:

- **app:** reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/kavita`), the `books` folder in your media folder, to read only, the `comics` folder in your media folder, to read only. Its web page is on your home network at port 5000 when that port is free, or the next free one.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **app:** 768 MB of memory and 1 processor core at most, and 256 processes.

Measured:

- 339.1 MiB at rest as Starboard runs it, with an empty library (13 November 2026). A real library uses more.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Apps you can add**, find **Kavita** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Kavita**. To stop, select **Cancel**: nothing is installed.
5. Kavita's own tab opens under **Settings**, then **Plug-ins**. Select **Activate**. Its state changes to **Active**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/kavita/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

### Open it

Kavita's tab shows its address on your home network, with **Open**. Anyone on your home network can open that page, so set the app's own password straight away.

## Set it up

1. On Kavita's tab, select **Activate** if it is not active yet.
2. In **Its web page**, select **Open Kavita**.
3. Make the first account. It is Kavita's admin, so give it a strong password.
4. In Kavita, add a library for `/media/books`.
5. Add a library for `/media/comics`.

Kavita reads both folders only, so it cannot change or delete a file. Its sign-in key is made for this install when it first starts.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Kavita**.
2. Under **Remove**, select **Remove Kavita**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Kavita does](../kavita/README.md)
- [Settings](../kavita/settings.md)
- [Problems](../kavita/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
