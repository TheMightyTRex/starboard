# Audio description: Accessibility
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard draws everything Audio description shows in Starboard: its settings, buttons, cards and messages, with the same parts as the rest of Starboard. They follow your **Display** choices: text size, spacing, theme, **High contrast**, underlined links and reduced motion.

## What was checked

- **The plug-in tester:** accessibility passed, checking settings, cards and actions. Starboard runs it before the plug-in is added, every time.
- **Its logo** has a text description, "A loudspeaker with sound waves", for where it is shown without its name.
- **Its cards** say their status in words with an icon, never by colour alone. A screen reader hears the card's heading, then its status and when it last changed. Nothing on a card interrupts a screen reader when it refreshes.
- **What it is for:** it helps blind and partially sighted people find films and series with a described sound track, and keep that track in Jellyfin.
- **Its words:** a test checks that what people read on its pages and cards, and its README, has no em dashes or contractions.
- **Its links** each say where they go, such as "Search AudioVault for" and the title, and open in a new tab.
- **Long lists** on **Search AudioVault** and **Search YouDescribe** open by first letter when Films or Series has more than 80 titles, so no page is too long to move through.
- **Not checked:** the sites and phone apps it links to, such as AudioVault, YouDescribe, MovieReading and Earcatch. They are not part of Starboard.
- **Starboard's own parts** (settings, buttons, dialogs and cards) are checked with axe, a keyboard walk and the reading order in each Starboard release. Read [How Starboard is tested](../../accessibility/how-starboard-is-tested.md).

## Find out more

- [Accessibility in Starboard](../../accessibility/overview.md)
- [Problems](../audio-description/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

<!-- /footer -->
