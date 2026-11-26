[Help centre](../README.md) · Everyday use · how-to
<!-- help: a11y / change -->

# Change text size, theme and other display settings

The **Display and accessibility** panel changes Starboard's colours, text and movement for you. You can choose light
or dark, bigger text, higher contrast, less movement, underlined links, wider spacing, the design of the Apps page and
styles from plug-ins. Each choice applies at once, stays in the browser you use, and you undo it the same way.

![Where Display is in the header, and a table of what each setting in the Display and accessibility panel changes](../images/a11y-display-map.svg)

The diagram shows the Display button as the last item in the header, and each setting with its choices and what it
changes. The same information is in **The choices**.

## Steps

1. Select **Display** in the header of any page. It is the last item in the header, on every page, including
   Sign in and the set-up. A slide-out opens, called **Display and accessibility**, with focus on its **Close**
   button.
   ![The Apps page with example data, with Display at the end of the header (step 1) outlined](../images/display-and-accessibility-1-button.png)
2. Make any of the choices in **The choices**. Each one applies at once, and the page behind the panel changes
   straight away.
3. Select **Done**, or press Escape. Focus goes back to **Display**.
   ![The Display and accessibility slide-out open over the Apps page, with Theme (step 2) and Done (step 3) outlined](../images/display-and-accessibility-2-panel.png)

To go back to the standard settings, select **Reset** at the end of the panel. Reset puts every choice in the panel
back to its default, including the design and the style, and says "Display settings reset" to screen readers.

## The choices

| Setting | Choices | What it changes | More |
|---|---|---|---|
| **Theme** | **Match device**, **Light** (default), **Dark** | Dark text on a light page, or light text on a dark page. | [Light, dark and high contrast](../accessibility/light-dark-and-high-contrast.md) |
| **Text size** | **100%** (default), **125%**, **150%**, **175%** | All of Starboard's text, with the page laid out again to fit. | [Text size and spacing](../accessibility/text-size-and-spacing.md) |
| **Reduce motion** | **Match device** (default), **On**, **Off** | Slide-outs, messages and lists appear without sliding, shimmering or loading by themselves. | [Reduce motion](../accessibility/reduce-motion.md) |
| **High contrast** | Activated or deactivated (default) | Near-black or white text, solid borders, no shadows and a bolder focus colour. | [Light, dark and high contrast](../accessibility/light-dark-and-high-contrast.md) |
| **Underline links** | Activated or deactivated (default) | Every link is underlined, not shown by colour alone. | [Underline links](../accessibility/underline-links.md) |
| **Wider text spacing** | Activated or deactivated (default) | More space between lines, letters and words. | [Text size and spacing](../accessibility/text-size-and-spacing.md) |
| **Remove drop shadows** | Activated or deactivated | Cards, covers, menus, slide-outs and dialogs lose their shadow and keep their border. For everyone on this server. | [Remove drop shadows](#remove-drop-shadows) |
| **Style** | Only with a style plug-in | Colours and shape from a plug-in, checked for contrast. | [Choose a style from a plug-in](#choose-a-style-from-a-plug-in) |
| **Design** | Five designs, or the dashboard's default | How the Apps page is laid out in this browser. | [Choose a design for the Apps page](choose-a-design.md) |

### Make the same choices in Settings

The same choices, apart from the design and the style, are also in **Settings**, then **General**, then
**Appearance**, under **Accessibility**. They are the same settings: a change in one place shows in the other.
There, each change says **Saved** beside the control, and focus stays where it was.

![Settings, General, Appearance, with its Accessibility part outlined: the same theme, text size, motion, contrast, link and spacing choices as Display](../images/display-and-accessibility-3-appearance.png)

## Remove drop shadows

Drop shadows cost a little processor on every scroll, so removing them helps small and older computers. Removing
them leaves every border where it is, so nothing loses its edge, and nothing else changes.

Unlike the other choices, this one is for everyone on this server, not only the browser you use, and Starboard saves it at once.
The set-up asks about it, straight after **How much it does**, in the browser and in the terminal:

- **Reelix Lite** starts with the shadows **removed**, because Lite is for smaller computers.
- Any other install starts with the shadows **kept**.
- Your own choice is never changed. If you later switch between Reelix Lite and the full Reelix in **Settings**,
  your choice stays. Only a setting you never answered follows the install.
- A Starboard that you installed before this setting existed keeps its shadows. The first visit after the update
  says so once.

1. Select **Display** in the header.
2. Activate **Remove drop shadows**. To bring them back, deactivate it. It also shows in **Settings**, **General**,
   **Appearance**, under **Accessibility**.

![The Display and accessibility slide-out with Remove drop shadows (step 2) outlined, and the note about processor use under it](../images/display-and-accessibility-4-shadows-switch.png)

With the shadows kept, each cover and card stands off the page:

![The Films library with example covers and Remove drop shadows off: each cover and card has its shadow, one cover outlined](../images/display-and-accessibility-5-shadows-kept.png)

With them removed, the same covers keep their borders and sit flat:

![The same Films library with Remove drop shadows on: the covers and cards keep their borders and have no shadow, one cover outlined](../images/display-and-accessibility-6-shadows-removed.png)

High contrast already has no shadows.

## Choose a style from a plug-in

A style changes Starboard's colours and shape. Styles come from plug-ins. Starboard checks each one for
accessibility before you can choose it, and every colour pair must meet WCAG 2.2 AA, in light and in dark. **Style**
shows in the Display panel only when an active plug-in has styles. Read [Add a plug-in](add-a-plugin.md).

1. Select **Display** in the header.
2. Under **Style**, choose a style. **Starboard's own style** is the standard style.
3. Select **Done**.

To go back to Starboard's own style, select **Reset style** under the list. **High contrast**, text size, wider
spacing, underlined links and reduced motion always win over a style.

## Things to note

- **Kept in this browser:** your browser keeps these settings, including the design and the style. They are
  not on the server and not with your sign-in. Each phone, computer and browser has its own. Set them again on each
  one you use.
- A private or incognito window may forget them when it closes. Clearing your browser's data for Starboard also
  clears them.
- **Settings for everyone on the server:** two related settings are kept on the server instead. The accent
  colour is in **Settings**, then **General**, then **Appearance**. **Load more as you scroll** is in
  **Settings**, then **General**, then **Pages and lists**, under **Long lists**.
- **Match device** uses the light, dark and motion settings of your phone or computer, so Starboard changes when
  they do.
- Starboard is built to WCAG 2.2 AA (Web Content Accessibility Guidelines), with large controls. Its typeface,
  Atkinson Hyperlegible Next, is designed for readers with low vision, so there is no separate
  font setting.

## If it does not work

- **A setting goes back after closing the window:** the browser is in private mode, or blocks Starboard from
  keeping data. Use a normal window, or allow Starboard to keep data in your browser's settings.
- **The settings are different on another device:** they are kept per browser. Set them again there.
- **No Style in the panel:** no active plug-in has styles. Read [Add a plug-in](add-a-plugin.md).

## Find out more

- [Accessibility in Starboard](../accessibility/overview.md)
- [Use only a keyboard](../accessibility/use-only-a-keyboard.md)
- [Limits and known gaps](../accessibility/limits-and-known-gaps.md)
- [Choose a design for the Apps page](choose-a-design.md)
- [Add a plug-in](add-a-plugin.md)
- [Open Starboard from a phone or another computer](open-from-another-device.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
