# Themearr: Accessibility
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard draws everything Themearr shows in Starboard: its settings, its card, the **Sign in to Themearr** page and its messages, with the same parts as the rest of Starboard. They follow your **Display** choices: text size, spacing, theme, **High contrast**, underlined links and reduced motion.

## What was checked

- **The plug-in tester:** accessibility passed, checking its settings and card. Starboard runs it before the plug-in is added, every time.
- **Its logo**, a music note on a screen, has the text description "Themearr logo" where it is shown without its name. Beside its name, screen readers skip it, so the name is read once.
- **Its card** says its status in words with an icon, never by colour alone. A screen reader hears the card's heading, then its status and when it last changed. Nothing on the card interrupts a screen reader when it refreshes.
- **Starboard's own parts** (settings, buttons, dialogs and cards) are checked with axe, a keyboard walk and the reading order in each Starboard release. Read [How Starboard is tested](../../accessibility/how-starboard-is-tested.md).

## Not checked

- **Themearr's own web page** is made by others. Starboard did not check it for accessibility: not checked. Its link, **Open Themearr**, says that it opens in a new tab, for screen reader users.

## Find out more

- [Accessibility in Starboard](../../accessibility/overview.md)
- [Problems](../themearr/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
