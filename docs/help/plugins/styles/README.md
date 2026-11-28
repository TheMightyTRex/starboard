# Styles, a Starboard plug-in
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

22 styles for Starboard, chosen from current interface trends and checked for accessibility in light and dark.

| Style | What it is like |
|---|---|
| Mica | Starboard's own design since 18 November 2026: calm greys, small corners, drop shadows and frosted menus |
| Midnight | Dark first and dense, with calm blue accents |
| Frost | Soft frosted tints and gentle shadows, with solid panels for reading |
| Bold | Neo-brutalist: hard edges, thick shadows and a yellow highlight |
| Bento | Rounded boxes in soft pastels |
| Paper | Calm and minimal, on warm paper with a serif |
| Forest | Earthy greens and natural tones |
| Retro | Square corners, a monospace font and amber, like old terminals |
| Vivid | Bright pink and purple |
| Aurora | Deep night blue with violet and teal glows, rounded and calm |
| Nordic | Scandinavian calm: soft greys, birch white and fjord blue |
| Sunset | Warm coral and plum on soft peach |
| Graphite | Precise monochrome greys with one electric lime accent |
| Editorial | Magazine style: serif headings and a deep red rule |
| Winter | Pine and berry over a frosty page, with snow dots, glows and glass |
| Large and clear | Strong contrast, heavy headings and wide focus rings, for reading with low vision |
| Studio | A quiet product style: hairline borders, one indigo accent, outlined buttons |
| Expressive | Tonal colour blocks, big round shapes and pill buttons |
| Swiss | White, black and red on a grid, heavy rules and capital labels |
| Neon | Synthwave glows on a faint grid, with a gradient button |
| Clay | Puffy, matte soft-3D panels in calm pastels |
| Classic | Starboard's design before Mica: teal on cool blue-grey, square corners and flat cards |

Mica is Starboard's own style since 18 November 2026, so Classic keeps the design from before it. Mica and the five from Studio to Clay change every part of Starboard: cards, buttons, tabs, the header, the side menu and chips (Starboard's plug-in
API 1.2).

## Install

Needs Starboard with plug-in API 1.14 or later. An older Starboard keeps version 1.3.0.

1. Run `python3 install.py` and give your Starboard's address. Your browser opens Settings, Plug-ins, Catalogue
   with Styles ready to add.
2. Select **Install**, read what it may do (add styles to Display, nothing else), enter your Starboard password
   and select **Install Styles**.
3. Select **Turn on** on its tab, then open **Display** and choose a style.

Or find Styles in Settings, Plug-ins, Catalogue. No installer? There, choose this folder's `starboard-plugin.json` under **Or its manifest file**.

## What it can and cannot change

It changes colours, corner shapes, the fonts (from fonts already on your device), shadows, the page's gradient, a light texture and glass panels. It runs nothing: no
container, no code and no network access. Starboard writes the CSS itself after checking contrast (WCAG 2.2:
4.5:1 for text, 3:1 for edges and the focus ring). High contrast, text size, spacing, underlined links and reduced
motion in Display always win over a style.

## Change it

Edit `starboard-plugin.json`, then test it: `python3 -m starboard.plugin_tester path/to/styles` from Starboard's
folder, or Settings, Plug-ins, **Test a plug-in**. A style that fails contrast cannot be added.

Licence: MIT. Author: TheMightyTRexUK.

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
