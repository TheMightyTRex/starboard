#!/usr/bin/env python3
"""Writes the shared header, side menu, phone menu and Display panel into every page in web/, between the shell markers.

Edit the menus here, then run: python3 tools/apply_shell.py
Each page is its own HTML file, so every page and sub-page has a real address you can link to.
Three levels, named as in the design system (docs/DESIGN-SYSTEM.md): the side menu (the logo with Starboard
underneath, Search and the five sections), the level 1 menu (header row 1, starting with the server name: a
section's pages) and the level 2 menu (header row 2: a page's own tabs, only when it has them). On phones the
side menu is hidden and the menu drawer holds the sections with their level 1 pages.
"""

import pathlib
import re
import sys

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"

# Icons come from web/icons/sprite.svg: the shared library's Lucide set plus Starboard's own (tools/lucide_icons.py).
ICONS = dict(re.findall(r'<symbol id="i-([^"]+)"[^>]*>(.*?)</symbol>', (WEB / "icons" / "sprite.svg").read_text(encoding="utf-8"), re.S))

# The menu: side menu sections -> level 1 pages -> level 2 pages.
# Section: (key, label, icon, [level 1 item]). Level 1 item: (label, icon, [(page, level 2 label, icon)]).
# A level 1 item opens its first page; it has a level 2 menu only when it has more than one page.
MENU = [
    ("library", "Library", "library", [
        ("TV", "tv", [("library-tv.html", "My library", "library"), ("library-tv-series.html", "Series", "layers")]),
        ("Films", "film", [("library-films.html", "My library", "library"), ("library-films-collections.html", "Collections", "layers")]),
        ("Radio", "radio", [("library-radio.html", "My library", "library"), ("library-radio-series.html", "Series", "layers"),
                            ("library-radio-stations.html", "Stations", "radio")]),
        ("Books", "book-open", [("library-books.html", "My library", "library"), ("library-books-series.html", "Series", "layers"),
                                ("library-books-authors.html", "Authors", "users")]),
        ("Audiobooks", "headphones", [("library-audiobooks.html", "My library", "library"),
                                      ("library-audiobooks-series.html", "Series", "layers"),
                                      ("library-audiobooks-authors.html", "Authors", "users")]),
    ]),
    ("discover", "Discover", "compass", [
        ("Search", "search", [("search.html", "Search", "search")]),
        ("Trending", "sparkles", [("discover-trending.html", "Trending", "sparkles")]),
        ("Coming up", "calendar-days", [("upcoming.html", "Coming up", "calendar-days")]),
    ]),
    ("activity", "Activity", "activity", [
        ("Downloads", "download", [("downloads.html", "Queue", "download"), ("downloads-finished.html", "Recently finished", "history")]),
        ("Wanted", "list-checks", [("wanted.html", "Missing", "list-checks"), ("wanted-quality.html", "Below the quality wanted", "gauge")]),
        ("Requests", "inbox", [("downloads-requests.html", "Requests", "inbox")]),
        ("History", "history", [("history.html", "History", "history")]),
    ]),
    ("system", "System", "server", [
        ("Overview", "layout-dashboard", [("system.html", "Overview", "layout-dashboard"), ("system-monitor.html", "Monitor", "gauge")]),
        ("Apps", "layout-grid", [("index.html", "Apps", "layout-grid"), ("apps-services.html", "Other services", "server-cog"),
                                 ("apps-updates.html", "Updates", "circle-arrow-up"), ("install-apps.html", "Install apps", "download")]),
        ("Storage", "hard-drive", [("system-storage.html", "Storage", "hard-drive"), ("system-pool.html", "Pool", "layers"),
                                   ("system-disks.html", "Disk health", "heart-pulse")]),
        ("Network", "network", [("system-network.html", "Network", "network")]),
        ("Backup", "archive-restore", [("system-backup.html", "Backup and restore", "archive-restore")]),
        ("Logs", "scroll-text", [("system-logs.html", "Logs", "scroll-text")]),
    ]),
    ("settings", "Settings", "settings", [
        ("General", "sliders-horizontal", [("settings-general.html", "General", "sliders-horizontal")]),
        ("Apps", "app-window", [("settings.html", "Manage apps", "app-window"), ("settings-reelix.html", "Reelix", "film"),
                                ("settings-jellyfin.html", "Jellyfin", "tv"), ("settings-audiobookshelf.html", "Audiobookshelf", "headphones")]),
        ("Alerts", "bell", [("settings-alerts.html", "Alerts", "bell")]),
        ("Performance", "gauge", [("settings-performance.html", "Performance", "gauge")]),
        ("Security", "shield-check", [("settings-security.html", "Security", "shield-check")]),
        ("Updates", "circle-arrow-up", [("settings-updates.html", "About and updates", "info")]),
    ]),
]
HOME = "index.html"  # the logo opens it

# Help for each section, from the Help button in the header. Placeholders while the new help centre is made and
# tested: today they open the matching part of the help index on GitHub. Change them here, in one place.
HELP_CENTRE = "https://github.com/TheMightyTRex/starboard/blob/main/docs/help/README.md"
HELP = {
    "library": HELP_CENTRE,
    "discover": f"{HELP_CENTRE}#everyday-use",
    "activity": f"{HELP_CENTRE}#everyday-use",
    "system": f"{HELP_CENTRE}#your-server",
    "settings": f"{HELP_CENTRE}#apps",
}

# Every page: (section key, level 1 index).
PAGES = {}
for key, _, _, items in MENU:
    for n, (_, _, pages) in enumerate(items):
        for page, _, _ in pages:
            PAGES[page] = (key, n)
# Pages with no tab of their own show the page they open from as current: the guides open from Settings,
# General, and Copy settings from Manage apps.
TAB_OF = {"setup-guide.html": "settings-general.html", "upgrade.html": "settings-general.html", "copy-settings.html": "settings.html"}
for page, parent in TAB_OF.items():
    PAGES[page] = PAGES[parent]


def icon(name, size=18):
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>')


def tab(href, label, icon_name, current):
    here = ' aria-current="page"' if current else ""
    return f'<a href="/{href}"{here}>{icon(icon_name)}<span class="menu-tabs__label">{label}</span></a>'


def search_form(id_, cls, form_id=""):
    form_id = f' id="{form_id}"' if form_id else ""
    return (f'<form class="{cls}"{form_id} action="/search.html" role="search">'
            f'<label class="visually-hidden" for="{id_}">Search films, series, music and books</label>'
            f'<input class="input" id="{id_}" name="q" type="search" placeholder="Search films, series, music and books">'
            f'<button type="submit" class="visually-hidden">Search</button></form>')


# The Screen logo (DASH-73): a screen with four tiles and a star.
LOGO = ('<svg viewBox="0 0 32 32" width="{s}" height="{s}" aria-hidden="true" focusable="false">'
        '<path fill-rule="evenodd" fill="var(--color-logo-tile)" d="M1.5 6h26v19.5h-26z M3.8 8.3v14.9h21.4V8.3z"/>'
        '<path fill="var(--color-logo-tile)" d="M9.5 26.6h10v2.2h-10z"/>'
        '<path fill="var(--color-logo-tile)" d="M6.2 10.6h7.6v5.2H6.2z M15.2 10.6h7.6v5.2h-7.6z M6.2 17.4h7.6v3.9H6.2z M15.2 17.4h7.6v3.9h-7.6z"/>'
        '<path fill="var(--color-logo-star)" d="M25.2 0.2L26.8 4.9L31.8 5.0L27.8 8.0L29.3 12.8L25.2 10.0L21.1 12.8L22.6 8.0L18.6 5.0L23.6 4.9Z"/></svg>')


def shell(current):
    key, at = PAGES[current]
    current = TAB_OF.get(current, current)
    section = next(s for s in MENU if s[0] == key)
    level1 = section[3]

    rail_links = "".join(f'<a href="/{items[0][2][0][0]}"{" aria-current=\"page\"" if k == key else ""}>{icon(ic, 24)}<span>{label}</span></a>'
                         for k, label, ic, items in MENU)
    level1_tabs = "\n        ".join(tab(pages[0][0], label, ic, n == at) for n, (label, ic, pages) in enumerate(level1))
    level2 = ""
    label, _, pages = level1[at]
    if len(pages) > 1:
        tabs = "\n      ".join(tab(page, l, ic, page == current) for page, l, ic in pages)
        level2 = f'''
  <div class="site-header__tabs">
    <nav class="menu-tabs" aria-label="{label}">
      {tabs}
    </nav>
  </div>'''

    # Phone menu: the five sections, each with its level 1 pages and their icons.
    phone_sections = []
    for k, s_label, ic, items in MENU:
        open_ = k == key
        links = "\n            ".join(
            f'<li><a href="/{pages[0][0]}"{" aria-current=\"page\"" if open_ and n == at else ""}>{icon(i2, 18)}<span>{l}</span></a></li>'
            for n, (l, i2, pages) in enumerate(items))
        phone_sections.append(f'''<div class="phone-menu__section"{" data-current" if open_ else ""}>
          <button type="button" aria-expanded="{"true" if open_ else "false"}" aria-controls="phone-sub-{k}">{icon(ic, 20)}<span>{s_label}</span>{icon("chevron-right", 18).replace('aria-hidden', 'class="phone-menu__chevron" aria-hidden')}</button>
          <ul id="phone-sub-{k}"{"" if open_ else " hidden"}>
            {links}
          </ul>
        </div>''')
    phone_sections = "\n        ".join(phone_sections)

    return f'''<a class="skip-link" href="#main">Skip to main content</a>
<nav class="rail" aria-label="Side menu">
  <a class="rail__brand" href="/{HOME}">{LOGO.format(s=32)}<span class="rail__name">Starboard</span></a>
  <button type="button" class="rail__search" data-search-open aria-controls="header-search" aria-expanded="false">{icon("search", 24)}<span>Search</span></button>
  {rail_links}
</nav>
<header class="site-header">
  <div class="site-header__bar">
    <button type="button" class="icon-btn phone-menu-button" data-phone-menu-open aria-expanded="false" aria-controls="phone-menu">{icon("menu", 20)}<span class="visually-hidden">Menu</span></button>
    <a class="site-header__brand" href="/{HOME}">{LOGO.format(s=28)}<span>Starboard</span></a>
    <span class="site-header__server" data-server-name hidden></span>
    <nav class="menu-tabs" id="main-nav" aria-label="{section[1]}">
        {level1_tabs}
    </nav>
    {search_form("header-search-input", "site-header__search search-field", "header-search")}
    <div class="site-header__actions">
      <button type="button" class="icon-btn site-header__search-btn" data-search-open aria-controls="header-search" aria-expanded="false">{icon("search", 20)}<span class="visually-hidden">Search</span></button>
      <a class="icon-btn" href="{HELP[key]}" target="_blank" rel="noopener noreferrer" data-help-link>{icon("circle-help", 20)}<span class="label">Help</span><span class="visually-hidden"> with {section[1]} (opens in a new tab)</span></a>
      <button type="button" class="icon-btn" data-display-toggle aria-haspopup="dialog" aria-expanded="false">{icon("sun", 20)}<span class="label">Display</span></button>
    </div>
  </div>{level2}
</header>
<div class="side-panel-layer" id="phone-menu" hidden>
  <div class="side-panel-backdrop"></div>
  <nav class="phone-menu" aria-label="Menu">
    <div class="panel-header">
      <span class="panel-header__brand">{LOGO.format(s=24)}<span>Starboard</span></span>
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
<!-- Display and accessibility: a slide-out (common.js builds it from this template when Display is pressed). -->
<template id="display-panel">
  <form class="form-stack" data-display-form>
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
  </form>
</template>
<div id="announcer" class="visually-hidden" aria-live="polite"></div>'''


def main():
    pattern = re.compile(r"<!-- shell:start.*?-->.*?<!-- shell:end -->", re.S)
    for page in PAGES:
        path = WEB / page
        text = path.read_text(encoding="utf-8")
        if "shell:start" not in text:
            raise SystemExit(f"{page} has no shell markers")
        # The side menu needs room on the left: with-rail joins the page's own classes on <body>.
        text = re.sub(r'<body(?: class="([^"]*)")?>', lambda m: m.group(0) if "with-rail" in (m.group(1) or "").split()
                      else f'<body class="{((m.group(1) or "") + " with-rail").strip()}">', text, count=1)
        block = f"<!-- shell:start (written by tools/apply_shell.py; edit the menus there) -->\n{shell(page)}\n<!-- shell:end -->"
        path.write_text(pattern.sub(lambda _: block, text, count=1), encoding="utf-8")
        print(f"updated {page}")


if __name__ == "__main__":
    main()
