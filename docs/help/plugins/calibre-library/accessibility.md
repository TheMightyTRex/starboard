# Calibre library maker: Accessibility
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard draws everything Calibre library maker shows in Starboard: its page, its buttons and its messages, with the same parts as the rest of Starboard. They follow your **Display** choices: text size, spacing, theme, **High contrast**, underlined links and reduced motion.

## What was checked

- **The plug-in tester:** accessibility passed. Starboard runs it before the plug-in is added, every time.
- **Its page** is a list. Each row has a title, a state in words (**Ready**, **Working**, **Done**, **Left out**) with a shape beside the colour, and a sentence of detail. Nothing depends on colour alone.
- **Progress** is a sentence on its own row, such as "Making your library: 120 of 836 books". It is words, not a moving bar.
- **Its buttons** have names that say what they do. **Make the library** asks first in Starboard's own dialog, which starts on **Cancel** and closes with Escape.
- **Its logo**, two books with a plus sign, has the text description "Calibre library maker logo" where it is shown without its name.
- **Starboard's own parts** are checked with axe, a keyboard walk and the reading order in each Starboard release. Read [How Starboard is tested](../../accessibility/how-starboard-is-tested.md).

## Find out more

- [Accessibility in Starboard](../../accessibility/overview.md)
- [Problems](../calibre-library/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
