# Styles: Install
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Add Styles from Starboard's **Catalogue**, where it is listed under **Appearance**. Starboard shows what it may do and tests it before anything is added. At the end, Styles is active.

## Before you begin

- Starboard with plug-in API 1.14 or later. An older Starboard is offered an earlier version: read [Updates](../styles/updates.md).
- Your Starboard password. Adding and removing a plug-in ask for it.

## What it may do

Starboard lists these before you add it, each with its risk.

| Permission | Risk |
|---|---|
| Add styles to Display: colours, corners, a font and shadows, checked for accessibility (`appearance:styles`) | Low |

Styles runs nothing: no container, no code and no network access. It only adds styles, which Starboard writes itself after checking their contrast in light and dark (WCAG 2.2: 4.5:1 for text, 3:1 for edges and the focus ring). A style that fails cannot be added.

## Memory and processor

None: it runs no container.

## Add it

1. Go to **Settings**, then **Plug-ins**, then **Catalogue**.
2. Under **Appearance**, find **Styles** and select **Install…**.
3. A slide-out opens with what it can read, change and reach. Read it all.
4. Enter your Starboard password and select **Install Styles**. To stop, select **Cancel**: nothing is installed.
5. Styles' own tab opens under **Settings**, then **Plug-ins**, and Starboard turns it on: its **State**, in **General**, says **Active**. If it needs settings first, it says what to enter: save them, then select **Turn on**.
6. Select **Display** in the header.
7. Under **Style**, choose a style.
8. Select **Done**.

### Add it by its address

On the **Catalogue** page, under **Add one from elsewhere**, paste this into **The plug-in's manifest address**, then select **What it does** and carry on from step 3:

```text
https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/styles/starboard-plugin.json
```

Or run its installer, `install.py` in its folder, on any computer with Python, and give your Starboard's address.

## Remove it

1. Go to **Settings**, then **Plug-ins**, then **Styles**.
2. Under **Remove**, select **Remove Styles**.
3. Choose where its folder goes: **Keep it with Starboard's data** (in `data/plugins/.removed`) or **Move it to the holding folder**, listed in **System**, **Clean up**, where you can put it back or delete it for good.
4. Enter your Starboard password and select **Remove**.

Its styles are no longer offered in **Display**. Nothing is deleted.

To stop it for a while instead, select **Turn off** on its tab. While it is off, its styles are not offered in **Display**.

## Find out more

- [What Styles does](../styles/README.md)
- [Settings](../styles/settings.md)
- [Problems](../styles/problems.md)
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
