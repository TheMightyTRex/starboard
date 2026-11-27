"""The page shell: the shared header, side menu, phone menu and Display panel of every page in web/.

The pages hold only an empty pair of shell markers; static_file() in server.py fills them with shell(page) when a
page is first served, and keeps the result in memory. Before, tools/apply_shell.py wrote the same 34 KB into each of
the 96 pages (95% of all the pages' bytes); what reaches the browser is the same.

Edit the menus here. tools/apply_shell.py adds the markers to a new page and checks every page has help.
Each page is its own HTML file, so every page and sub-page has a real address you can link to.
Three levels, named as in the design system (docs/DESIGN-SYSTEM.md): the side menu (the logo with Starboard
underneath, Search (a link to the Search page; phones keep the search field in the menu and the header button) and the
five sections), the level 1 menu (header row 1, starting with the server name: a
section's pages) and the level 2 menu (header row 2: a page's own tabs, only when it has them). On phones the
side menu is hidden and the menu drawer holds the sections with their level 1 pages.
"""

import functools
import os
import re

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
MARKERS = re.compile(r"<!-- shell:start[^>]*-->\n?(.*?)<!-- shell:end -->", re.S)
START = "<!-- shell:start (filled in by starboard/shell.py; edit the menus there) -->"


@functools.cache
def _icons():
    """Icons come from web/icons/sprite.svg: the shared library's Lucide set plus Starboard's own (tools/lucide_icons.py)."""
    with open(os.path.join(WEB, "icons", "sprite.svg"), encoding="utf-8") as f:
        return dict(re.findall(r'<symbol id="i-([^"]+)"[^>]*>(.*?)</symbol>', f.read(), re.S))


# The menu: side menu sections -> level 1 pages -> level 2 pages.
# Section: (key, label, icon, [level 1 item]). Level 1 item: (label, icon, [(page, level 2 label, icon)]).
# A level 1 item opens its first page; it has a level 2 menu only when it has more than one page.
MENU = [
    ("home", "Home", "house", [
        ("Dashboard", "layout-dashboard", [("dashboard.html", "Dashboard", "layout-dashboard")]),
    ]),
    ("library", "Library", "library", [
        ("TV", "tv", [("library-tv.html", "My library", "library"), ("library-tv-networks.html", "Networks", "layers")]),
        ("Films", "film", [("library-films.html", "My library", "library"), ("library-films-collections.html", "Collections", "layers")]),
        ("Music", "music", [("library-music.html", "My library", "library")]),
        ("Radio", "radio", [("library-radio.html", "My library", "library"), ("library-radio-stations.html", "Stations", "radio")]),
        ("Books", "book-open", [("library-books.html", "My library", "library"), ("library-books-series.html", "Series", "layers"),
                                ("library-books-authors.html", "Authors", "users")]),
        ("Audiobooks", "headphones", [("library-audiobooks.html", "My library", "library"),
                                      ("library-audiobooks-series.html", "Series", "layers"),
                                      ("library-audiobooks-authors.html", "Authors", "users"),
                                      ("library-audiobooks-narrators.html", "Narrators", "mic")]),  # DASH-261
    ]),
    ("discover", "Discover", "compass", [
        # Search the sites directly (DASH-213): a page people come back to, so its own page under Search.
        ("Search", "search", [("search.html", "Search", "search"), ("search-sites.html", "Search the sites", "globe")]),
        # One item for each area, each with its own feeds (owner, 12 November 2026). Trending is in Films and TV now.
        ("Films", "film", [("discover-films.html", "Films", "film")]),
        ("TV", "tv", [("discover-tv.html", "TV", "tv")]),
        ("Music", "music", [("discover-music.html", "Music", "music")]),
        ("Radio", "radio", [("discover-radio.html", "Radio", "radio")]),
        ("Books", "book-open", [("discover-books.html", "Books", "book-open")]),
        ("Audiobooks", "headphones", [("discover-audiobooks.html", "Audiobooks", "headphones")]),
        ("Coming up", "calendar-days", [("upcoming.html", "Coming up", "calendar-days")]),
        ("On demand history", "history", [("discover-ondemand.html", "On demand history", "history")]),
    ]),
    ("activity", "Activity", "activity", [
        ("Downloads", "download", [("downloads.html", "Queue", "download"), ("downloads-finished.html", "Recently finished", "history"),
                                   ("downloads-direct.html", "From a link", "link")]),
        # A level 2 item for each media type, with Missing and Below the quality wanted as tabs (12 November 2026)
        ("Wanted", "list-checks", [("wanted-films.html", "Films", "film"), ("wanted-tv.html", "TV", "tv"),
                                   ("wanted-music.html", "Music", "music"), ("wanted-books.html", "Books", "book-open"),
                                   ("wanted-audiobooks.html", "Audiobooks", "headphones")]),
        ("Requests", "inbox", [("downloads-requests.html", "Requests", "inbox"), ("downloads-issues.html", "Issues", "circle-alert")]),
        ("History", "history", [("history.html", "History", "history"), ("history-apps.html", "Across apps", "layout-grid")]),
    ]),
    ("system", "System", "server", [
        ("Overview", "layout-dashboard", [("system.html", "Overview", "layout-dashboard"), ("system-monitor.html", "Monitor", "gauge"),
                                                                                   ("system-busy.html", "Busy now", "activity")]),
        ("Apps", "layout-grid", [("index.html", "Apps", "layout-grid"), ("apps-services.html", "Other services", "server-cog"),
                                 ("apps-updates.html", "Updates", "circle-arrow-up"), ("install-apps.html", "Install apps", "download")]),
        ("Storage", "hard-drive", [("system-storage.html", "Storage", "hard-drive"), ("system-pool.html", "Pool", "layers"),
                                   ("system-disks.html", "Disk health", "heart-pulse")]),
        ("Network", "network", [("system-network.html", "Network", "network")]),
        ("Clean up", "trash-2", [("system-cleanup.html", "What is left over", "trash-2"), ("system-holding.html", "Holding folder", "archive")]),
        ("Logs", "scroll-text", [("system-logs.html", "Logs", "scroll-text")]),
    ]),
    ("settings", "Settings", "settings", [
        # Level 2 (owner, 13 November 2026: "The general sub menu should be on menu 2"; DASH-389).
        ("General", "sliders-horizontal", [("settings-general.html", "General", "tags"),
                                           ("settings-general-appearance.html", "Appearance", "sun"),
                                           ("settings-general-lists.html", "Lists", "list"),
                                           ("settings-general-hours.html", "Hours", "clock"),
                                           # Owner, 26 November 2026 (DASH-584): Alerts and Performance are part of General now.
                                           # Their old addresses move here (MOVED_PAGES in server.py).
                                           ("settings-general-alerts.html", "Alerts", "bell"),
                                           ("settings-general-performance.html", "Performance", "gauge"),
                                           # Owner, 26 November 2026 (DASH-595): Backup and restore (it was System, Backup, then
                                           # General) and Logs and feedback are one tab. The names are short so every tab keeps its
                                           # name at 1280 pixels wide. The old addresses move here (MOVED_PAGES in server.py).
                                           ("settings-general-backup.html", "Backup/Logs", "archive-restore")]),
        ("Apps", "app-window", [("settings.html", "Manage apps", "app-window"), ("settings-install.html", "Your install", "layers"),
                                ("settings-reelix.html", "Reelix", "film"),
                                ("settings-jellyfin.html", "Jellyfin", "tv"), ("settings-audiobookshelf.html", "Audiobookshelf", "headphones"),
                                ("settings-tdarr.html", "Tdarr", "cpu"), ("settings-dispatcharr.html", "Dispatcharr", "radio")]),
        # Level 2 (owner, 13 November 2026: "VPN, Usenet and Download hours should be on menu 2"; DASH-390).
        ("Downloads", "download", [("settings-downloads.html", "VPN", "lock"), ("settings-downloads-usenet.html", "Usenet", "server"),
                                   ("settings-downloads-hours.html", "Download hours", "clock")]),
        # Level 2 (owner, 13 November 2026: "All should have those on Menu 2"; DASH-391), as General and Downloads.
        ("Radio", "radio", [("settings-radio.html", "Sources", "radio"), ("settings-radio-link.html", "Add a show from a link", "link"),
                            ("settings-radio-library.html", "Your podcast library", "library"), ("settings-radio-logos.html", "Station logos", "layout-grid")]),
        ("Security", "shield-check", [("settings-security.html", "Who can open the dashboard", "network"),
                                      ("settings-security-password.html", "Password", "key-round"),
                                      ("settings-security-signin.html", "Sign-in methods", "shield-check"),
                                      ("settings-security-keys.html", "API keys", "lock"),
                                      ("settings-security-sessions.html", "Sign out everywhere", "log-out")]),
        # Owner, 26 November 2026 (DASH-589, single sign-on stage 1): the people who use the apps and their passwords in each.
        ("People", "users", [("settings-people.html", "People", "users")]),
        # Level 2: Manage, Catalogue, then one tab per added plug-in, which common.js adds from /api/session (DASH-318).
        ("Plug-ins", "puzzle", [("settings-plugins.html", "Manage", "list-checks"),
                                ("settings-plugins-catalogue.html", "Catalogue", "layout-grid")]),
        ("Updates", "circle-arrow-up", [("settings-updates.html", "Updates", "circle-arrow-up"),
                                         ("settings-updates-plugins.html", "Plug-ins", "puzzle"),
                                         ("settings-releases.html", "Releases", "scroll-text"),
                                         ("settings-restore.html", "Restore", "archive-restore")]),
    ]),
]
HOME = "index.html"  # the logo opens it

# Pages that belong to a plug-in (owner, 12 November 2026: "All plug-in menu items should only show when installed").
# Their menu items are written hidden, with the plug-in's id; common.js shows them when /api/session lists it as added.
PLUGIN_PAGES = {"discover-ondemand.html": "on-demand"}


def plugin_attr(page):
    pid = PLUGIN_PAGES.get(page)
    return f' data-plugin="{pid}" hidden' if pid else ""

# Help for each page, from the Help button in the header: the help centre article for what the page does, or the
# help index's section when no one article covers the page. Page: (path in docs/help, what the help is about). Every
# page with the header must be here (check_help_links in tools/apply_shell.py). Change them here, in one place.
HELP_BASE = "https://themightytrex.github.io/starboard/help/"  # the help centre's pages (the design system's help centre builder (tools/help_centre))


def help_page(path):
    """topics/x.md#part (in the help folder) -> topics/x.html#part on the help centre; README.md is its index page."""
    file, _, anchor = path.partition("#")
    page = file[:-len("README.md")] + "index.html" if file.endswith("README.md") else file[:-3] + ".html"
    return page + ("#" + anchor if anchor else "")
EVERYDAY = ("README.md#everyday-use", "everyday use")
HELP = {
    **{page: ("topics/browse-your-library.md", "browsing your library") for page in (
        "library-tv.html", "library-tv-networks.html", "library-films.html", "library-films-collections.html",
        "library-music.html", "library-radio.html", "library-radio-stations.html", "library-books.html",
        "library-books-series.html", "library-books-authors.html", "library-audiobooks.html",
        "library-audiobooks-series.html", "library-audiobooks-authors.html", "library-audiobooks-narrators.html",
        "library-film.html", "library-tv-show.html",
        "library-artist.html", "library-radio-show.html", "library-book.html", "library-audiobook.html")},
    "search.html": ("topics/search-and-add.md", "searching for and adding films, series, music and books"),
    "search-sites.html": ("topics/search-and-add.md", "searching the sites directly"),
    **{f"discover-{a}.html": ("topics/search-and-add.md", "discovering and adding films, series, music, radio and books")
       for a in ("films", "tv", "music", "radio", "books", "audiobooks")},
    "upcoming.html": ("topics/coming-up.md", "finding out what is coming up"),
    "discover-ondemand.html": ("topics/search-and-add.md", "searching for and adding films, series, music and books"),
    "downloads.html": ("topics/manage-downloads.md", "pausing, resuming and removing downloads"),
    "downloads-finished.html": ("topics/manage-downloads.md", "pausing, resuming and removing downloads"),
    "wanted-films.html": ("topics/get-what-is-missing.md", "finding and getting what is missing"),
    "wanted-tv.html": ("topics/get-what-is-missing.md", "finding and getting what is missing"),
    "wanted-music.html": ("topics/get-what-is-missing.md", "finding and getting what is missing"),
    "wanted-books.html": ("topics/get-what-is-missing.md", "finding and getting what is missing"),
    "wanted-audiobooks.html": ("topics/get-what-is-missing.md", "finding and getting what is missing"),
    "downloads-requests.html": ("topics/approve-requests.md", "approving or declining requests"),
    "downloads-issues.html": ("topics/approve-requests.md", "issues people report"),
    "downloads-direct.html": ("topics/manage-downloads.md#download-from-a-youtube-or-spotify-link", "downloading from YouTube and Spotify"),
    "history.html": EVERYDAY,
    "history-apps.html": ("topics/check-what-happened-across-your-apps.md", "checking what was added, failed and upgraded across your apps"),
    "system.html": ("README.md#your-server", "your server"),
    "system-monitor.html": ("topics/monitor-apps.md", "finding out what each app is using"),
    "settings-people.html": ("topics/add-the-people-who-use-your-apps.md", "adding the people who use your apps"),
    "system-busy.html": ("topics/find-out-what-is-using-the-processor.md", "finding out what is using the processor"),
    "index.html": ("README.md#apps", "apps"),
    "apps-services.html": ("topics/add-a-background-service.md", "adding a background service"),
    "apps-updates.html": ("topics/update-your-apps.md", "updating your apps"),
    "install-apps.html": ("topics/install-apps.md", "installing apps with Starboard"),
    "system-storage.html": ("topics/check-storage.md", "checking free space and what is using it"),
    "system-pool.html": ("basics/what-is-a-drive-pool.md", "the disk pool"),
    "system-disks.html": ("topics/check-disk-health.md", "checking your disks' health"),
    "system-network.html": ("topics/open-from-another-device.md", "opening Starboard from another device"),
    "settings-general-backup.html": ("topics/back-up-settings.md", "backups, logs and feedback"),
    "system-logs.html": ("topics/read-the-log.md", "reading the log and reporting a problem"),
    "system-cleanup.html": ("topics/remove-starboard.md", "removing what Starboard leaves behind"),
    "system-holding.html": ("topics/remove-starboard.md", "removing what Starboard leaves behind"),
    "settings-general.html": ("topics/organise-categories.md", "organising apps into categories"),
    "settings-general-appearance.html": ("topics/display-and-accessibility.md", "the display, colours and accessibility"),
    "settings-general-lists.html": ("topics/coming-up.md", "what Coming up and the lists show"),
    "settings-general-hours.html": ("topics/set-download-hours.md", "setting download hours"),
    "settings.html": ("topics/change-or-remove-an-app.md", "changing or removing an app"),
    "settings-install.html": ("topics/change-your-install.md", "changing your install"),
    "settings-reelix.html": ("topics/change-reelix-settings.md", "changing Reelix's settings"),
    "settings-jellyfin.html": ("topics/choose-your-media-server.md", "your media server"),  # the active media server's tab (Jellyfin, Plex or Emby)
    "settings-audiobookshelf.html": ("README.md#jellyfin-and-audiobookshelf", "Jellyfin and Audiobookshelf"),
    "settings-tdarr.html": ("README.md#jellyfin-and-audiobookshelf", "Jellyfin and Audiobookshelf"),
    "settings-dispatcharr.html": ("topics/set-up-live-tv.md", "setting up Live TV"),
    "settings-general-alerts.html": ("topics/activate-alerts.md", "activating alerts"),
    "settings-general-performance.html": ("topics/make-starboard-lighter.md", "making Starboard use less of your server"),
    "settings-security.html": ("topics/choose-who-can-open-starboard.md", "choosing who can open Starboard"),
    "settings-security-password.html": ("topics/change-your-password.md", "changing your password"),
    "settings-security-signin.html": ("topics/set-up-a-two-step-code.md", "setting up a two-step code"),
    "settings-security-keys.html": ("topics/use-starboards-api.md", "API keys for Starboard's API"),
    "settings-security-sessions.html": ("topics/sign-out-everywhere.md", "signing out everywhere"),
    "settings-downloads.html": ("topics/change-your-install.md", "your install and its VPN"),
    "settings-downloads-usenet.html": ("topics/choose-a-usenet-provider.md", "your Usenet provider"),
    "settings-downloads-hours.html": ("topics/set-download-hours.md", "setting download hours"),
    "settings-plugins.html": ("topics/add-a-plugin.md", "plug-ins"),
    "settings-radio.html": ("topics/follow-radio-shows.md", "following radio shows and where they come from"),
    "settings-radio-link.html": ("topics/follow-radio-shows.md#find-and-follow-a-show", "following a show"),
    "settings-radio-library.html": ("topics/follow-radio-shows.md#bring-in-shows-you-already-have", "shows you already have"),
    "settings-radio-logos.html": ("topics/add-a-plugin.md", "station logos"),
    "settings-plugins-catalogue.html": ("topics/add-a-plugin.md", "adding a plug-in"),
    "settings-plugin.html": ("topics/add-a-plugin.md", "a plug-in's settings"),
    "dashboard.html": ("topics/use-the-dashboard.md", "your dashboard"),
    "settings-updates.html": ("topics/update-starboard.md", "updating Starboard"),
    "settings-releases.html": ("topics/update-starboard.md", "updating Starboard"),
    "settings-updates-plugins.html": ("topics/update-a-plugin.md", "updating plug-ins"),
    "settings-restore.html": ("topics/restore-a-saved-copy.md", "restoring a saved copy of your settings"),
    "setup-guide.html": ("guides/set-up-your-dashboard.md", "setting up your dashboard"),
    "upgrade.html": ("topics/update-starboard.md", "updating Starboard"),
    "copy-settings.html": ("topics/copy-app-settings.md", "copying settings from one app to another"),
    "bring-in.html": ("topics/bring-in-media-you-already-have.md", "bringing in media you already have"),
}


# Every page: (section key, level 1 index).
PAGES = {}
for key, _, _, items in MENU:
    for n, (_, _, pages) in enumerate(items):
        for page, _, _ in pages:
            PAGES[page] = (key, n)
# Pages with no tab of their own show the page they open from as current: the guides open from Settings,
# General, and Copy settings from Manage apps.
TAB_OF = {"setup-guide.html": "settings-general.html", "settings-plugin.html": "settings-plugins.html", "upgrade.html": "settings-general.html", "copy-settings.html": "settings.html",
          # An item's page shows its Library tab as current.
          "library-film.html": "library-films.html", "library-tv-show.html": "library-tv.html", "library-artist.html": "library-music.html",
          "library-radio-show.html": "library-radio.html", "library-book.html": "library-books.html",
          "library-audiobook.html": "library-audiobooks.html",
          "bring-in.html": "library-films.html"}  # Bring in media (DASH-455): opened from Library and Still to set up
for page, parent in TAB_OF.items():
    PAGES[page] = PAGES[parent]


def icon(name, size=18):
    icons = _icons()
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{icons[name]}</svg>')


def tab(href, label, icon_name, current):
    here = (' aria-current="page"' if current else "") + plugin_attr(href)
    return f'<a href="/{href}"{here}>{icon(icon_name)}<span class="menu-tabs__label">{label}</span></a>'


def search_form(id_, cls, form_id=""):
    form_id = f' id="{form_id}"' if form_id else ""
    return (f'<form class="{cls}"{form_id} action="/search.html" role="search">'
            f'<label class="visually-hidden" for="{id_}">Search films, series, music and books</label>'
            f'<input class="input" id="{id_}" name="q" type="search" placeholder="Search films, series, music and books">'
            f'<button type="submit" class="search-field__btn">{icon("search", 18)}<span class="visually-hidden">Search</span></button></form>')


# The Screen logo (DASH-73): a screen with four tiles and a star.
LOGO = ('<svg viewBox="0 0 32 32" width="{s}" height="{s}" aria-hidden="true" focusable="false">'
        '<path fill-rule="evenodd" fill="var(--color-logo-tile)" d="M1.5 6h26v19.5h-26z M3.8 8.3v14.9h21.4V8.3z"/>'
        '<path fill="var(--color-logo-tile)" d="M9.5 26.6h10v2.2h-10z"/>'
        '<path fill="var(--color-logo-tile)" d="M6.2 10.6h7.6v5.2H6.2z M15.2 10.6h7.6v5.2h-7.6z M6.2 17.4h7.6v3.9H6.2z M15.2 17.4h7.6v3.9h-7.6z"/>'
        '<path fill="var(--color-logo-star)" d="M25.2 0.2L26.8 4.9L31.8 5.0L27.8 8.0L29.3 12.8L25.2 10.0L21.1 12.8L22.6 8.0L18.6 5.0L23.6 4.9Z"/></svg>')


def shell(current):
    key, at = PAGES[current]
    help_path, help_about = HELP[current]
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
            f'<li{plugin_attr(pages[0][0])}><a href="/{pages[0][0]}"{" aria-current=\"page\"" if open_ and n == at else ""}>{icon(i2, 18)}<span>{l}</span></a></li>'
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
  {rail_links}
  <div class="rail__end">
    <button type="button" class="rail__feedback" data-feedback-open hidden>{icon("message-square-warning", 24)}<span>Feedback</span><span class="visually-hidden"> (send feedback)</span></button>
    <button type="button" class="rail__signout" data-sign-out>{icon("log-out", 24)}<span>Sign out</span></button>
    <a class="rail__version" href="/settings-updates.html" data-version-link><span class="update-dot" data-update-available hidden aria-hidden="true"></span><span data-version-short></span></a>
  </div>
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
      <a class="icon-btn" href="{HELP_BASE}{help_page(help_path)}" target="_blank" rel="noopener noreferrer" data-help-link>{icon("help-new-tab", 20)}<span class="label">Help</span><span class="visually-hidden"> with {help_about} (opens in a new tab)</span></a>
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
    <button type="button" class="phone-menu__feedback" data-feedback-open hidden>{icon("message-square-warning", 20)}<span>Send feedback</span></button>
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
        <p class="hint">Applies to this browser only. Set the default for everyone in Settings, General, Appearance.</p>
        <div class="option-cards" data-design-options></div>
      </fieldset>
  </form>
</template>
<div id="announcer" class="visually-hidden" aria-live="polite"></div>'''


def block(page):
    """The whole shell of a page, between its markers."""
    return f"{START}\n{shell(page)}\n<!-- shell:end -->"


def fill(page, text):
    """A page's HTML with its shell filled in; pages with no markers, or not in the menu, come back as they are."""
    m = MARKERS.search(text)
    if not m or page not in PAGES or m.group(1).strip():
        return text
    return text[:m.start()] + block(page) + text[m.end():]
