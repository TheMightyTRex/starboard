# Tdarr: Accessibility
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard draws everything Tdarr shows in Starboard: its tab, its buttons and its messages, with the same parts as the rest of Starboard. They follow your **Display** choices: text size, spacing, theme, **High contrast**, underlined links and reduced motion.

## What was checked

- **The plug-in tester:** accessibility passed. Starboard runs it before the plug-in is added, every time. Tdarr has no settings, card or actions in its manifest, so there was little to check.
- **Its Settings section** is Starboard's own Tdarr settings, drawn with Starboard's parts: each choice is a labelled control and says beside itself when it is saved. It was not checked on its own for this plug-in: not checked.
- **Its logo**, two arrows in a circle, has the text description "Tdarr logo" where it is shown without its name. Beside its name, screen readers skip it, so the name is read once.
- **Starboard's own parts** (settings, buttons, dialogs and cards) are checked with axe, a keyboard walk and the reading order in each Starboard release. Read [How Starboard is tested](../../accessibility/how-starboard-is-tested.md).

## Not checked

- **Tdarr's own web page** is made by others. Starboard did not check it for accessibility: not checked. Its link, **Open Tdarr**, says that it opens in a new tab, for screen reader users.

## Find out more

- [Accessibility in Starboard](../../accessibility/overview.md)
- [Problems](../tdarr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
