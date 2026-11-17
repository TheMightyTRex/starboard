# Styles: Accessibility
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard draws everything Styles shows in Starboard: its settings, buttons and messages, with the same parts as the rest of Starboard. They follow your **Display** choices: text size, spacing, theme, **High contrast**, underlined links and reduced motion.

## What was checked

- **The plug-in tester:** accessibility passed, checking 21 styles in light and dark, settings, cards and actions. Starboard runs it before the plug-in is added, every time.
- **Its logo**, a painter's palette, has the text description "Styles logo" where it is shown without its name. Beside its name, screen readers skip it, so the name is read once.
- **Contrast:** Starboard checks every colour pair of every style, in light and dark, against WCAG 2.2 before it can be added: 4.5:1 for text, and 3:1 for edges and the focus ring.
- **Your Display choices win:** **High contrast**, text size, wider spacing, underlined links and reduced motion always win over a style.
- **Large and clear** is made for reading with low vision: strong contrast, heavy headings, wide focus rings and no glass or texture.
- **Not checked:** how each style works with every font on your device, since a style may use fonts already there.
- **Starboard's own parts** (settings, buttons, dialogs and cards) are checked with axe, a keyboard walk and the reading order in each Starboard release. Read [How Starboard is tested](../../accessibility/how-starboard-is-tested.md).

## Find out more

- [Accessibility in Starboard](../../accessibility/overview.md)
- [Problems](../styles/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
