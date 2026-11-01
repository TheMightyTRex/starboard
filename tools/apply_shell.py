#!/usr/bin/env python3
"""Writes the shared header and Display panel into every page in web/, between the shell markers.

Edit the menu here, then run: python3 tools/apply_shell.py
Each page is its own HTML file, so every page has a real address you can link to.
"""

import pathlib
import re

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"

ICONS = {
    "apps": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "downloads": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 20h16"/>',
    "upcoming": '<rect x="3" y="5" width="18" height="16"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "system": '<rect x="3" y="4" width="18" height="12"/><path d="M8 20h8M12 16v4"/><path d="m7 12 3-3 2 2 4-4"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    "display": '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
}

PAGES = [
    ("index.html", "apps", "Apps"),
    ("search.html", "search", "Search"),
    ("downloads.html", "downloads", "Downloads"),
    ("upcoming.html", "upcoming", "Coming up"),
    ("system.html", "system", "System"),
    ("settings.html", "settings", "Settings"),
]


def icon(name, size=20):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>')


def shell(current):
    links = []
    for href, key, label in PAGES:
        here = ' aria-current="page"' if href == current else ""
        links.append(f'        <li><a href="/{href}"{here}>{icon(key)}<span>{label}</span></a></li>')
    links = "\n".join(links)
    return f'''<a class="skip-link" href="#main">Skip to main content</a>
<header class="site-header">
  <div class="site-header__bar">
    <a class="brand" href="/index.html">
      <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect width="32" height="32" fill="var(--color-accent)"/><path d="M16 6l2.6 6.4 6.9.5-5.3 4.4 1.7 6.7L16 20.3 10.1 24l1.7-6.7-5.3-4.4 6.9-.5Z" fill="var(--color-accent-text)"/></svg>
      <span class="brand__name" data-site-name>Starboard</span>
    </a>
    <nav class="main-nav" id="main-nav" aria-label="Main">
      <form class="nav-search search-bar" action="/search.html" role="search">
        <label class="visually-hidden" for="nav-search-input">Search your apps</label>
        <input class="input" id="nav-search-input" name="q" type="search" placeholder="Search films, series, music, books">
      </form>
      <ul>
{links}
      </ul>
    </nav>
    <form class="header-search" action="/search.html" role="search">
      <label class="visually-hidden" for="header-search-input">Search your apps</label>
      <input class="input" id="header-search-input" name="q" type="search" placeholder="Search films, series, music, books">
    </form>
    <div class="header-actions">
      <button type="button" class="icon-btn display-btn" data-display-toggle aria-haspopup="dialog" aria-expanded="false">{icon("display")}<span class="display-btn__label">Display</span></button>
      <button type="button" class="icon-btn menu-btn" data-menu-toggle aria-expanded="false" aria-controls="main-nav">{icon("menu")}<span>Menu</span></button>
    </div>
  </div>
</header>
<dialog id="display-panel" aria-labelledby="display-panel-title">
  <form method="dialog">
    <div class="dialog__head">
      <h2 id="display-panel-title">Display and accessibility</h2>
      <button type="button" class="icon-btn" data-dialog-close aria-label="Close display and accessibility">{icon("close")}</button>
    </div>
    <div class="dialog__body">
      <fieldset><legend>Theme</legend>
        <div class="seg">
          <label><input type="radio" name="theme" value="system"><span>Match device</span></label>
          <label><input type="radio" name="theme" value="light"><span>Light</span></label>
          <label><input type="radio" name="theme" value="dark"><span>Dark</span></label>
        </div>
      </fieldset>
      <fieldset><legend>Text size</legend>
        <div class="seg">
          <label><input type="radio" name="text" value="100"><span>100%</span></label>
          <label><input type="radio" name="text" value="125"><span>125%</span></label>
          <label><input type="radio" name="text" value="150"><span>150%</span></label>
          <label><input type="radio" name="text" value="175"><span>175%</span></label>
        </div>
      </fieldset>
      <fieldset><legend>Reduce motion</legend>
        <div class="seg">
          <label><input type="radio" name="motion" value="device"><span>Match device</span></label>
          <label><input type="radio" name="motion" value="on"><span>On</span></label>
          <label><input type="radio" name="motion" value="off"><span>Off</span></label>
        </div>
      </fieldset>
      <label class="switch-row" for="pref-contrast"><span>High contrast</span><input type="checkbox" id="pref-contrast" name="contrast"></label>
      <label class="switch-row" for="pref-underline"><span>Underline links</span><input type="checkbox" id="pref-underline" name="underline"></label>
      <label class="switch-row" for="pref-spacing"><span>Wider text spacing</span><input type="checkbox" id="pref-spacing" name="spacing"></label>
      <fieldset><legend>Design</legend>
        <p class="hint">Applies to this browser only. Set the default for everyone in Settings.</p>
        <div class="design-options" data-design-options></div>
      </fieldset>
    </div>
    <div class="dialog__foot">
      <button type="submit" class="btn btn-primary">Done</button>
      <button type="button" class="btn" data-display-reset>Reset</button>
    </div>
  </form>
</dialog>
<div id="announcer" class="visually-hidden" aria-live="polite"></div>'''


def main():
    pattern = re.compile(r"<!-- shell:start.*?-->.*?<!-- shell:end -->", re.S)
    for href, _, _ in PAGES:
        path = WEB / href
        text = path.read_text(encoding="utf-8")
        block = f"<!-- shell:start (written by tools/apply_shell.py; edit the menu there) -->\n{shell(href)}\n<!-- shell:end -->"
        new = pattern.sub(lambda _: block, text, count=1)
        if "shell:start" not in text:
            raise SystemExit(f"{href} has no shell markers")
        path.write_text(new, encoding="utf-8")
        print(f"updated {href}")


if __name__ == "__main__":
    main()
