# Philips Hue: Accessibility
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

Starboard draws everything Philips Hue shows, with the same parts as the rest of Starboard. That covers its settings, its lists of lights, scenes and schedules, buttons, cards and messages. They follow your **Display** choices: text size, spacing, theme, **High contrast**, underlined links and reduced motion.

## How it is built to be used

- **Colour in words:** every light's colour is said by its name, such as "On at 80%, warm white", never by colour alone. Colours are chosen from a list of names, not a colour wheel.
- **Every control is Starboard's own:** switches, lists and buttons have their names. A screen reader hears "Brightness: Ceiling" or "Deactivate Under cupboard", not a bare control.
- **Each change is spoken:** Starboard's live region says what happened, such as "Ceiling is at 40%" or "Every light in Kitchen is off". The focus stays on the control you used. After **Change** on a schedule, the focus goes to the page heading.
- **Pairing waits for you:** the link button notice says the seconds left in words as well as a bar, and the page waits 90 seconds.
- **Schedules in words:** a schedule is one sentence, such as "Every weekday at 07:00, Kitchen to 80%", read out as written, with no time pickers. A mistake is said in words with what to change.
- **Not reachable** is said in words on each light, on the Rooms card and on the Lights on card.

## What was checked

- **The plug-in tester:** accessibility passed, checking settings, cards and actions. Starboard runs it before the plug-in is added, every time.
- **Its logo**, a light bulb, has the text description "Philips Hue logo" where it is shown without its name.
- **Its cards** say their status in words with an icon, never by colour alone. Nothing on a card interrupts a screen reader when it refreshes.
- **Its tabs in Starboard**, on 20 November 2026 against a made-up bridge. The checks were:
  - axe (WCAG 2.2 AA) in Light, Dark and High contrast on every tab, a room, a zone, a device type and the dashboard cards.
  - A Tab walk of each tab.
  - The headings in reading order.
  - Where the focus goes after each change.
- **What the check found** was in Starboard's own list parts, not in the plug-in, and goes to Starboard. The section tabs are smaller than 24 pixels for a touch. The heading **Activate or deactivate in bulk** comes two levels under the tab's heading. The list of schedules holds a part that is not a list item while **Change** is open.

## Find out more

- [Accessibility in Starboard](../../accessibility/overview.md)
- [Problems](../philips-hue/problems.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
