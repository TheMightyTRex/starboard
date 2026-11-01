#!/usr/bin/env python3
"""Writes the shared header, phone menu and Display panel into every page in web/, between the shell markers.

Edit the menus here, then run: python3 tools/apply_shell.py
Each page is its own HTML file, so every page and sub-page has a real address you can link to.
The header follows Storyarr's components: square tabs with icons for the main menu, the same tabs for a
section's sub-menu in a second header row, and on phones a menu drawer that holds both.
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lucide_icons import ICONS  # noqa: E402

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"

# Main menu: (key, first page, label, icon)
MAIN = [
    ("apps", "index.html", "Apps", "layout-grid"),
    ("search", "search.html", "Search", "search"),
    ("downloads", "downloads.html", "Downloads", "download"),
    ("upcoming", "upcoming.html", "Coming up", "calendar"),
    ("system", "system.html", "System", "activity"),
    ("settings", "settings.html", "Settings", "settings"),
]

# Sub-menus: main key -> [(page, label, icon)]. They use the same tabs as the main menu.
SUB = {
    "apps": [
        ("index.html", "Apps", "layout-grid"),
        ("apps-updates.html", "Updates", "circle-arrow-up"),
        ("apps-services.html", "Other services", "server-cog"),
    ],
    "system": [
        ("system.html", "Overview", "layout-dashboard"),
        ("system-storage.html", "Storage", "hard-drive"),
        ("system-disks.html", "Disk health", "heart-pulse"),
        ("system-monitor.html", "Monitor", "gauge"),
        ("system-network.html", "Network", "network"),
    ],
    "settings": [
        ("settings.html", "Apps", "app-window"),
        ("settings-general.html", "General", "sliders-horizontal"),
        ("settings-security.html", "Security", "shield-check"),
        ("settings-updates.html", "Updates", "refresh-cw"),
    ],
}

# Every page and the main menu item it belongs to.
PAGES = {page: key for key, page, _, _ in MAIN}
for key, items in SUB.items():
    for page, _, _ in items:
        PAGES[page] = key


def icon(name, size=18):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>')


def tab(href, label, icon_name, current):
    here = ' aria-current="page"' if current else ""
    return f'<a href="/{href}"{here}>{icon(icon_name)}<span class="menu-tabs__label">{label}</span></a>'


def search_form(id_):
    return (f'<form class="search-bar" action="/search.html" role="search">'
            f'<label class="visually-hidden" for="{id_}">Search your apps</label>'
            f'<input class="input" id="{id_}" name="q" type="search" placeholder="Search films, series, music, books"></form>')


def shell(current):
    section = PAGES[current]
    main_tabs = "\n        ".join(tab(page, label, ic, key == section) for key, page, label, ic in MAIN)
    sub = ""
    if section in SUB:
        label = next(label for key, _, label, _ in MAIN if key == section)
        sub_tabs = "\n      ".join(tab(page, l, ic, page == current) for page, l, ic in SUB[section])
        sub = f'''
  <div class="sub-menu">
    <nav class="menu-tabs" aria-label="{label}">
      {sub_tabs}
    </nav>
  </div>'''

    phone_sections = []
    for key, page, label, ic in MAIN:
        is_current = key == section
        mark = " data-current" if is_current else ""
        if key in SUB:
            links = "\n            ".join(
                f'<li><a href="/{p}"{" aria-current=\"page\"" if p == current else ""}>{l}</a></li>' for p, l, _ in SUB[key])
            phone_sections.append(f'''<div class="phone-menu-section"{mark}>
          <button type="button" class="phone-menu-section-button" aria-expanded="{"true" if is_current else "false"}" aria-controls="phone-sub-{key}">{icon(ic, 20)}<span>{label}</span><span class="phone-menu-chevron">{icon("chevron-right", 18)}</span></button>
          <ul id="phone-sub-{key}"{"" if is_current else " hidden"}>
            {links}
          </ul>
        </div>''')
        else:
            here = ' aria-current="page"' if page == current else ""
            phone_sections.append(f'''<div class="phone-menu-section"{mark}>
          <a class="phone-menu-section-button" href="/{page}"{here}>{icon(ic, 20)}<span>{label}</span></a>
        </div>''')
    phone_sections = "\n        ".join(phone_sections)

    return f'''<a class="skip-link" href="#main">Skip to main content</a>
<header class="site-header">
  <div class="site-header__bar">
    <button type="button" class="icon-btn phone-menu-button" data-phone-menu-open aria-haspopup="dialog" aria-expanded="false" aria-controls="phone-menu">{icon("menu", 20)}<span class="visually-hidden">Menu</span></button>
    <a class="brand" href="/index.html">
      <svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect x="3" y="3" width="12" height="12" fill="var(--color-logo-tile)"/><rect x="3" y="17" width="12" height="12" fill="var(--color-logo-tile)"/><rect x="17" y="17" width="12" height="12" fill="var(--color-logo-tile)"/><path d="M23 3.5l1.9 4.4 4.7.4-3.6 3.1 1.1 4.6-4.1-2.5-4.1 2.5 1.1-4.6-3.6-3.1 4.7-.4Z" fill="var(--color-logo-star)"/></svg>
      <span class="brand__name" data-site-name>Starboard</span>
    </a>
    <nav class="main-nav menu-tabs" id="main-nav" aria-label="Main">
        {main_tabs}
    </nav>
    <div class="header-search">{search_form("header-search-input")}</div>
    <div class="header-actions">
      <button type="button" class="icon-btn display-btn" data-display-toggle aria-haspopup="dialog" aria-expanded="false">{icon("sun", 20)}<span class="display-btn__label">Display</span></button>
    </div>
  </div>{sub}
</header>
<dialog class="phone-menu" id="phone-menu" aria-label="Menu">
  <div class="side-panel-header">
    <span class="phone-menu-brand"><svg viewBox="0 0 32 32" width="24" height="24" aria-hidden="true" focusable="false"><rect x="3" y="3" width="12" height="12" fill="var(--color-logo-tile)"/><rect x="3" y="17" width="12" height="12" fill="var(--color-logo-tile)"/><rect x="17" y="17" width="12" height="12" fill="var(--color-logo-tile)"/><path d="M23 3.5l1.9 4.4 4.7.4-3.6 3.1 1.1 4.6-4.1-2.5-4.1 2.5 1.1-4.6-3.6-3.1 4.7-.4Z" fill="var(--color-logo-star)"/></svg><span data-site-name>Starboard</span></span>
    <button type="button" class="icon-btn" data-phone-menu-close aria-label="Close menu">{icon("x", 20)}</button>
  </div>
  <div class="phone-menu-search">{search_form("phone-search-input")}</div>
  <nav class="phone-menu-sections" aria-label="Main">
        {phone_sections}
  </nav>
  <div class="phone-menu-footer">
    <span class="version-label" data-version></span>
    <button type="button" class="btn btn-quiet" data-sign-out>{icon("log-out", 18)}<span>Sign out</span></button>
  </div>
</dialog>
<dialog id="display-panel" aria-labelledby="display-panel-title">
  <form method="dialog">
    <div class="dialog__head">
      <h2 id="display-panel-title">Display and accessibility</h2>
      <button type="button" class="icon-btn" data-dialog-close aria-label="Close display and accessibility">{icon("x", 20)}</button>
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
        <p class="hint">Applies to this browser only. Set the default for everyone in Settings, General.</p>
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
    for page in PAGES:
        path = WEB / page
        text = path.read_text(encoding="utf-8")
        if "shell:start" not in text:
            raise SystemExit(f"{page} has no shell markers")
        block = f"<!-- shell:start (written by tools/apply_shell.py; edit the menus there) -->\n{shell(page)}\n<!-- shell:end -->"
        path.write_text(pattern.sub(lambda _: block, text, count=1), encoding="utf-8")
        print(f"updated {page}")


if __name__ == "__main__":
    main()
