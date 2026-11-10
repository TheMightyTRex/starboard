# Styles, a Starboard plug-in

Eight styles for Starboard, chosen from current interface trends and checked for accessibility in light and dark.

| Style | Look |
|---|---|
| Midnight | Dark first and dense, with calm blue accents |
| Frost | Soft frosted tints and gentle shadows, with solid panels for reading |
| Bold | Neo-brutalist: hard edges, thick shadows and a yellow highlight |
| Bento | Rounded boxes in soft pastels |
| Paper | Calm and minimal, on warm paper with a serif |
| Forest | Earthy greens and natural tones |
| Retro | Square corners, a monospace font and amber, like old terminals |
| Vivid | Bright pink and purple |

## Install

1. Run `python3 install.py` and give your Starboard's address. Your browser opens Settings, Plug-ins with
   Styles ready to add.
2. Read what it may do (add styles to Display, nothing else), type your Starboard password and select **Add**.
3. Select **Activate**, then open **Display** and choose a style.

No installer? In Settings, Plug-ins, choose this folder's `starboard-plugin.json` under **Or its manifest file**.

## What it can and cannot change

It changes colours, corner shapes, the font (from fonts already on your device) and shadows. It runs nothing: no
container, no code and no network access. Starboard writes the CSS itself after checking contrast (WCAG 2.2:
4.5:1 for text, 3:1 for edges and the focus ring). High contrast, text size, spacing, underlined links and reduced
motion in Display always win over a style.

## Change it

Edit `starboard-plugin.json`, then test it: `python3 -m starboard.plugin_tester path/to/styles` from Starboard's
folder, or Settings, Plug-ins, **Test a plug-in**. A style that fails contrast cannot be added.

Licence: MIT. Author: TheMightyTRexUK.
