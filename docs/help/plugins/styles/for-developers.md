# Styles: For developers
<!-- Mirrored from the starboard-plugins repository by tools/sync-plugin-help.py: change it there. -->

How Styles is built, for anyone who wants to change it or make one like it. It is MIT, by TheMightyTRexUK, and works with plug-in API `>=1.14 <2.0`.

## Its files

- [`starboard-plugin.json`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/styles/starboard-plugin.json)
- [`install.py`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/styles/install.py)
- [`logo.svg`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/styles/logo.svg)
- [`CHANGELOG.md`](https://github.com/TheMightyTRex/starboard-plugins/blob/main/styles/CHANGELOG.md)

## How it works

- It has no container (`"containers": []`) and asks only for `appearance:styles`. Starboard reads the `styles` list in its manifest and writes the CSS itself.
- Each style has an `id`, a `name`, a `description`, a corner `radius`, a `font`, a `shadow`, and a `light` and a `dark` set of colours, such as `bg`, `surface`, `text`, `accent` and `focus`.
- Starboard checks every colour pair against WCAG 2.2: 4.5:1 for text, and 3:1 for edges and the focus ring. A style that fails cannot be added.
- The six newest styles use the style settings from plug-in API 1.2 for cards, buttons, borders, tabs, the header, the side menu and chips.

## Change it

1. Edit `starboard-plugin.json`.
2. Test it: run `python3 -m starboard.plugin_tester path/to/styles` from Starboard's folder, or go to **Settings**, then **Plug-ins**, then **Test a plug-in**.

## Find out more

- [The plug-in collection's developer pages](https://themightytrex.github.io/starboard-plugins/help/developers/plug-in-api.html)
- [Plug-in manifest reference](../../developers/plugin-manifest-reference.md)
- [Plug-in API reference](../../developers/plugin-api-reference.md)

<!-- footer: download rights -->

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download.
Examples are open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

**Need help?** Ask on the [Starboard Discord support server](https://discord.gg/xN9bf2H4vv).

<!-- /footer -->
