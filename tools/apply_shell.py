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

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"

# Icons come from web/icons/sprite.svg: the shared library's Lucide set plus Starboard's own (tools/lucide_icons.py).
ICONS = dict(re.findall(r'<symbol id="i-([^"]+)"[^>]*>(.*?)</symbol>', (WEB / "icons" / "sprite.svg").read_text(encoding="utf-8"), re.S))

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
    "downloads": [
        ("downloads.html", "Queue", "download"),
        ("downloads-requests.html", "Requests", "inbox"),
    ],
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
        ("system-backup.html", "Backup and restore", "archive-restore"),
    ],
    "settings": [
        ("settings.html", "Manage apps", "app-window"),
        ("settings-general.html", "General", "sliders-horizontal"),
        ("settings-alerts.html", "Alerts", "bell"),
        ("settings-jellyfin.html", "Jellyfin", "tv"),
        ("settings-performance.html", "Performance", "gauge"),
        ("settings-security.html", "Security", "shield-check"),
        ("settings-updates.html", "About and updates", "info"),
    ],
}

# Every page and the main menu item it belongs to.
PAGES = {page: key for key, page, _, _ in MAIN}
for key, items in SUB.items():
    for page, _, _ in items:
        PAGES[page] = key
# Pages that belong to a section but have no tab of their own (opened from a button).
PAGES.update({"setup-guide.html": "settings", "upgrade.html": "settings", "install-apps.html": "settings"})


def icon(name, size=18):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>')


def tab(href, label, icon_name, current):
    here = ' aria-current="page"' if current else ""
    return f'<a href="/{href}"{here}>{icon(icon_name)}<span class="menu-tabs__label">{label}</span></a>'


def search_form(id_, cls):
    return (f'<form class="{cls}" action="/search.html" role="search">'
            f'<label class="visually-hidden" for="{id_}">Search films, series, music and books</label>'
            f'<input class="input" id="{id_}" name="q" type="search" placeholder="Search films, series, music and books">'
            f'<button type="submit" class="visually-hidden">Search</button></form>')


LOGO = ('<svg viewBox="0 0 32 32" width="{s}" height="{s}" aria-hidden="true" focusable="false"><rect x="3" y="3" width="12" height="12" fill="var(--color-logo-tile)"/>'
        '<rect x="3" y="17" width="12" height="12" fill="var(--color-logo-tile)"/><rect x="17" y="17" width="12" height="12" fill="var(--color-logo-tile)"/>'
        '<path d="M23 3.5l1.9 4.4 4.7.4-3.6 3.1 1.1 4.6-4.1-2.5-4.1 2.5 1.1-4.6-3.6-3.1 4.7-.4Z" fill="var(--color-logo-star)"/></svg>')


def shell(current):
    section = PAGES[current]
    main_tabs = "\n        ".join(tab(page, label, ic, key == section) for key, page, label, ic in MAIN)
    sub = ""
    if section in SUB:
        label = next(label for key, _, label, _ in MAIN if key == section)
        sub_tabs = "\n      ".join(tab(page, l, ic, page == current) for page, l, ic in SUB[section])
        sub = f'''
  <div class="site-header__tabs">
    <nav class="menu-tabs" aria-label="{label}">
      {sub_tabs}
    </nav>
  </div>'''

    # Phone menu: the main menu with icons, then each section's pages as plain links.
    phone_sections = []
    for key, page, label, ic in MAIN:
        mark = " data-current" if key == section else ""
        if key in SUB:
            links = "\n            ".join(
                f'<li><a href="/{p}"{" aria-current=\"page\"" if p == current else ""}>{l}</a></li>' for p, l, _ in SUB[key])
            open_ = key == section
            phone_sections.append(f'''<div class="phone-menu__section"{mark}>
          <button type="button" aria-expanded="{"true" if open_ else "false"}" aria-controls="phone-sub-{key}">{icon(ic, 20)}<span>{label}</span>{icon("chevron-right", 18).replace('aria-hidden', 'class="phone-menu__chevron" aria-hidden')}</button>
          <ul id="phone-sub-{key}"{"" if open_ else " hidden"}>
            {links}
          </ul>
        </div>''')
        else:
            here = ' aria-current="page"' if page == current else ""
            phone_sections.append(f'''<div class="phone-menu__section"{mark}>
          <a href="/{page}"{here}>{icon(ic, 20)}<span>{label}</span></a>
        </div>''')
    phone_sections = "\n        ".join(phone_sections)

    return f'''<a class="skip-link" href="#main">Skip to main content</a>
<header class="site-header site-header--no-rail">
  <div class="site-header__bar">
    <button type="button" class="icon-btn phone-menu-button" data-phone-menu-open aria-expanded="false" aria-controls="phone-menu">{icon("menu", 20)}<span class="visually-hidden">Menu</span></button>
    <a class="site-header__brand" href="/index.html">{LOGO.format(s=28)}<span data-site-name>Starboard</span></a>
    <nav class="menu-tabs" id="main-nav" aria-label="Main">
        {main_tabs}
    </nav>
    {search_form("header-search-input", "site-header__search search-field")}
    <div class="site-header__actions">
      <button type="button" class="icon-btn" data-display-toggle aria-haspopup="dialog" aria-expanded="false">{icon("sun", 20)}<span class="label">Display</span></button>
    </div>
  </div>{sub}
</header>
<div class="side-panel-layer" id="phone-menu" hidden>
  <div class="side-panel-backdrop"></div>
  <nav class="phone-menu" aria-label="Menu">
    <div class="panel-header">
      <span class="panel-header__brand">{LOGO.format(s=24)}<span data-site-name>Starboard</span></span>
      <button type="button" class="icon-btn" data-closes aria-label="Close menu">{icon("x", 20)}</button>
    </div>
    {search_form("phone-search-input", "phone-menu__search search-field")}
    <div class="phone-menu__sections">
        {phone_sections}
    </div>
    <div class="phone-menu__foot">
      <span class="version-label" data-version></span>
      <button type="button" class="btn btn--quiet" data-sign-out>{icon("log-out", 18)}<span>Sign out</span></button>
    </div>
  </nav>
</div>
<dialog class="dialog" id="display-panel" aria-labelledby="display-panel-title">
  <form method="dialog">
    <div class="panel-header">
      <h2 class="panel-header__title" id="display-panel-title">Display and accessibility</h2>
      <button type="button" class="icon-btn" data-dialog-close aria-label="Close display and accessibility">{icon("x", 20)}</button>
    </div>
    <div class="dialog__body">
      <fieldset><legend>Theme</legend>
        <div class="segmented">
          <label><input type="radio" name="theme" value="system"><span>Match device</span></label>
          <label><input type="radio" name="theme" value="light"><span>Light</span></label>
          <label><input type="radio" name="theme" value="dark"><span>Dark</span></label>
        </div>
      </fieldset>
      <fieldset><legend>Text size</legend>
        <div class="segmented">
          <label><input type="radio" name="text" value="100"><span>100%</span></label>
          <label><input type="radio" name="text" value="125"><span>125%</span></label>
          <label><input type="radio" name="text" value="150"><span>150%</span></label>
          <label><input type="radio" name="text" value="175"><span>175%</span></label>
        </div>
      </fieldset>
      <fieldset><legend>Reduce motion</legend>
        <div class="segmented">
          <label><input type="radio" name="motion" value="device"><span>Match device</span></label>
          <label><input type="radio" name="motion" value="on"><span>On</span></label>
          <label><input type="radio" name="motion" value="off"><span>Off</span></label>
        </div>
      </fieldset>
      <label class="switch" for="pref-contrast"><span>High contrast</span><input type="checkbox" role="switch" id="pref-contrast" name="contrast"></label>
      <label class="switch" for="pref-underline"><span>Underline links</span><input type="checkbox" role="switch" id="pref-underline" name="underline"></label>
      <label class="switch" for="pref-spacing"><span>Wider text spacing</span><input type="checkbox" role="switch" id="pref-spacing" name="spacing"></label>
      <fieldset><legend>Design</legend>
        <p class="hint">Applies to this browser only. Set the default for everyone in Settings, General.</p>
        <div class="option-cards" data-design-options></div>
      </fieldset>
    </div>
    <div class="dialog__foot">
      <button type="submit" class="btn btn--primary">Done</button>
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
