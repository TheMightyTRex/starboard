# Audio description tracks: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Audio description tracks from Starboard's **Catalogue**, where it is listed under **Accessibility**. Starboard shows what it may do and tests it before anything is added. At the end, Audio description tracks is active and its card is ready for your dashboard.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../audio-description-tracks/updates.md).
- Jellyfin added to Starboard, in **Settings**, then **Apps**. It uses the key Starboard keeps to find each title and ask Jellyfin to read it again. Without it, files say "Starboard has no Jellyfin key to give yet: add Jellyfin in Settings, Apps".
- Your films and series in the movies and tv folders of Starboard's media folder. It cannot add a track to a title anywhere else.
- A description track you already have, such as one from AudioVault. It never downloads one for you.
- Your Starboard password. Adding and removing a plug-in ask for it.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Use Jellyfin's API key, kept by Starboard (`jellyfin:key`) | High |
| Reach other computers on your home network, and the internet (`network:lan`) | Medium |

What it runs:

- **main:** reaches your home network and the internet, and this computer as `host.docker.internal`. It can use its own folder in Starboard's data (`data/plugins/audio-description-tracks`), the `movies` folder in your media folder, to read and change, the `tv` folder in your media folder, to read and change, the `audio-description` folder in your media folder, to read and change. It runs as the owner of your media folder, so the files it adds are yours. It never downloads from or reads any website. It rests after 10 minutes with nothing to do, and Starboard wakes it when it is needed.

Like every plug-in, it runs read only, as a user that is not root, with no extra rights. Its image is pinned by digest, so what you approved is what runs.

## Memory and processor

- **main:** 96 MB of memory and 0.5 of a processor core at most.

These figures are the most it may use.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Accessibility**, find **Audio description tracks** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Audio description tracks**. To stop, select **Cancel**: nothing is installed.
5. Audio description tracks' own tab opens under **Settings**, then **Plug-ins**. Select **Activate**. Starboard makes the audio-description folder in your media folder. Its state changes to **Active**.
6. Put a description track in the audio-description folder, named as the film and its year, such as `Dune (2021).mp3`. Or open **Description tracks to add** on its tab and select **Upload a description track**.
7. Select **Check the folder now**.
8. When the file shows **Added**, play the film in Jellyfin and choose the **English (Audio Description)** sound track.
9. On **Description tracks to add**, in **Plays in step?**, choose **Yes: put the original away** or **No: take the track off**.

To add the card, read [Dashboard card](../audio-description-tracks/dashboard-card.md). It goes with the [Audio description plug-in](../audio-description/install.md), whose **Search AudioVault** page links to AudioVault's search for each title without audio description.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/audio-description-tracks/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Audio description tracks**.
2. Under **Remove**, select **Remove Audio description tracks**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its containers stop and go, and its API key stops working. Nothing is deleted. Files it already changed in your media folder stay as they are.

To stop it for a while instead, select **Deactivate** on its tab: its settings and folder are kept.

## Find out more

- [What Audio description tracks does](../audio-description-tracks/README.md)
- [Settings](../audio-description-tracks/settings.md)
- [Problems](../audio-description-tracks/problems.md)
- [Add a plug-in, in Starboard's help](../../topics/add-a-plugin.md)
- [What a plug-in can change, in Starboard's help](../../basics/what-plugins-can-change.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
