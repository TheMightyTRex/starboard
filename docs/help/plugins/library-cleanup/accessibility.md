# Library clean-up: Accessibility
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard draws everything Library clean-up shows in Starboard: its settings, its **Preview**, **Holding folder** and **Libraries** pages, the **Put back** buttons, its card and messages, with the same parts as the rest of Starboard. They follow your **Display** choices: text size, spacing, theme, **High contrast**, underlined links and reduced motion.

## What was checked

- **The plug-in tester:** Starboard runs it before the plug-in is added, every time, and it checks the accessibility of its settings, cards and actions.
- **Its logo**, a storage box with an arrow going into it, has the text description "Library clean-up logo" where it is shown without its name. Beside its name, screen readers skip it, so the name is read once.
- **Its card** says its status in words with an icon, never by colour alone. A screen reader hears the card's heading, then its status and when it last changed. Nothing on the card interrupts a screen reader when it refreshes.
- **Its words:** every switch has a hint that says what it does, and every setting has a label in sentence case.
- **Starboard's own parts** (settings, buttons, dialogs and cards) are checked with axe, a keyboard walk and the reading order in each Starboard release. Read [How Starboard is tested](../../accessibility/how-starboard-is-tested.md).

## Find out more

- [Accessibility in Starboard](../../accessibility/overview.md)
- [Problems](../library-cleanup/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
