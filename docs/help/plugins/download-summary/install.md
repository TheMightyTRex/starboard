# Download summary: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Download summary from Starboard's **Catalogue**, where it is listed under **Downloads**. Starboard shows what it may do and tests it before anything is added. At the end, Download summary is active and its card is ready for your dashboard.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../download-summary/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.
- Your download apps, or Reelix, added to Starboard in **Settings**, then **Apps**, so their downloads show in **Activity**, then **Downloads**. Read [Pause, resume and remove downloads, in Starboard's help](../../topics/manage-downloads.md).

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| What is downloading (`downloads:read`) | Low |

What it runs:

- **main:** reaches only Starboard, on its own network: it cannot reach your home network or the internet. It can use its own folder in Starboard's data (`data/plugins/download-summary`).

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 48 MB of memory and 0.1 of a processor core at most.

These figures are the most it may use.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Downloads**, find **Download summary** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Download summary**. To stop, select **Cancel**: nothing is installed.
5. Download summary's own tab opens under **Settings**, then **Plug-ins**. Select **Activate**. Its state changes to **Active**.
6. Add its card to your dashboard. Read [Dashboard card](../download-summary/dashboard-card.md).

There is nothing else to set up: it has no settings of its own. It starts counting about a minute after you activate it, from 0 for that day.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/download-summary/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Download summary**.
2. Under **Remove**, select **Remove Download summary**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Download summary does](../download-summary/README.md)
- [Settings](../download-summary/settings.md)
- [Problems](../download-summary/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
