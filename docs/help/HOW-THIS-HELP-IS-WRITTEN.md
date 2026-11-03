# How this help is written

Starboard's help follows the shared guides in the design system, which Starboard and Storyarr both use:

- [Help writing guide](https://github.com/TheMightyTRex/design-system/blob/main/docs/HELP-WRITING.md): the three
  tiers (topics, guides and the basics), the layout of each, the rules for help, screenshots, and how to get an AI
  to write instructions.
- [Content design guide](https://github.com/TheMightyTRex/design-system/blob/main/docs/CONTENT-DESIGN.md): voice,
  words and punctuation for everything on screen and in the help. For example, settings are activated and
  deactivated, never turned on or off.

## Only in Starboard

- **Folders:** `topics/` (tier 1), `guides/` (tier 2) and `basics/` (tier 3). Every article is listed in the
  [help centre home](README.md), and the footer of every Starboard page links to it.
- **The first line** of every article is `[Help centre](../README.md) · <Area>`, followed by the kind for a topic
  (how-to, reference or troubleshooting).
- **Guides** show their steps as a Mermaid flowchart, which GitHub draws.
- **Made-up examples:** use `192.168.1.20` or `192.168.1.21` for addresses, `starboard-pi` for a Raspberry Pi,
  and names such as Sam and Alex. `tools/check-private.sh` allows exactly these, and refuses any other home
  network address.
- **Check before committing:** `python3 tools/check-help.py` checks every link, the layout of each tier and the
  writing rules that a machine can check.
