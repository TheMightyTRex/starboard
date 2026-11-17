# Wizarr: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Wizarr from Starboard's **Catalogue**, where it is listed under **Apps you can add**. Starboard shows what it may do and tests it before anything is added. At the end, Wizarr is active, with its own page on your home network, and set up.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../wizarr/updates.md).
- Jellyfin added to Starboard, in **Settings**, **Apps**. Wizarr works with it.
- Your Starboard password. Adding and removing a plug-in ask for it.
- An API key for Wizarr, made in Jellyfin's **Dashboard**, **API keys**. Starboard does not hand Wizarr its own key.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |
| Open its own web page on your home network, at a port Starboard chooses (`network:port`) | Medium |

What it runs:

- **app:** reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/wizarr`). Its web page is on your home network at port 5690 when that port is free, or the next free one.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **app:** 384 MB of memory and 0.5 of a processor core at most, and 128 processes.

Measured:

- 126.8 MiB at rest as Starboard runs it, with an empty library (13 November 2026).

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Apps you can add**, find **Wizarr** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Wizarr**. To stop, select **Cancel**: nothing is installed.
5. Wizarr's own tab opens under **Settings**, then **Plug-ins**. Select **Activate**. Its state changes to **Active**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/wizarr/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Set it up

Wizarr's tab shows its address on your home network, under **Its web page**.

1. On Wizarr's tab, under **Its web page**, select **Open Wizarr**. Its page opens in a new tab.
2. Make Wizarr's admin account. Anyone on your home network can open the page, so do this straight away.
3. Add your Jellyfin in Wizarr: the address `http://host.docker.internal:8096` and the API key you made in Jellyfin.
4. Choose the libraries each invitation gives, and an expiry if you want one, then make your first invitation link.

Invitation links work on your home network. For people away from home, use the [Remote access](../remote-access/install.md) plug-in or your own address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Wizarr**.
2. Under **Remove**, select **Remove Wizarr**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Wizarr does](../wizarr/README.md)
- [Settings](../wizarr/settings.md)
- [Problems](../wizarr/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
