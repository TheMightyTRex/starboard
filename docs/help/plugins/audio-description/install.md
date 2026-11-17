# Audio description: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Audio description from Starboard's **Catalogue**, where it is listed under **Accessibility**. Starboard shows what it may do and tests it before anything is added. At the end, Audio description is active and its cards are ready for your dashboard. Starboard's first set-up also offers it, unticked.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../audio-description/updates.md).
- Jellyfin added to Starboard, in **Settings**, then **Apps**. Audio description uses the key Starboard keeps for it. Without it, its card says "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps".
- Optional: Reelix added to Starboard, in **Settings**, then **Apps**, so it can prefer releases with audio description. Without it, **Apply the Reelix choice now** says "Starboard has no Reelix key to give yet: add Reelix in Settings, Apps".
- Your Starboard password. Adding and removing a plug-in ask for it.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Use Jellyfin's API key, kept by Starboard (`jellyfin:key`) | High |
| Use Reelix's API key, kept by Starboard (`reelix:key`) | High |
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |

What it runs:

- **main:** reaches your home network and the internet, and this computer as `host.docker.internal`, to reach Jellyfin and Reelix. It never downloads from or reads any website. It can use its own folder in Starboard's data (`data/plugins/audio-description`). It rests after 10 minutes with nothing to do, and Starboard wakes it when it is needed.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 64 MB of memory and 0.25 of a processor core at most.

These figures are the most it may use.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Accessibility**, find **Audio description** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Audio description**. To stop, select **Cancel**: nothing is installed.
5. Audio description's own tab opens under **Settings**, then **Plug-ins**. Select **Activate**. Its state changes to **Active**.
6. Open **People who want audio description** on its tab.
7. Activate each person who wants audio description.
8. Optional: select **Check for described titles now**, so you do not wait for tonight's check.
9. Add its cards to your dashboard. Read [Dashboard card](../audio-description/dashboard-card.md).

When Starboard starts, it adds the **Audio description** format to Reelix and prefers it. To stop that, deactivate **Prefer releases with audio description**. Read [Settings](../audio-description/settings.md).

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/audio-description/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Audio description**.
2. Under **Remove**, select **Remove Audio description**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Audio description does](../audio-description/README.md)
- [Settings](../audio-description/settings.md)
- [Problems](../audio-description/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
