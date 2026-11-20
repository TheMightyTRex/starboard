#!/usr/bin/env python3
"""Puts the empty shell markers into every page in the menu, and checks that each page has a help link.

The shared header, side menu, phone menu and Display panel are in starboard/shell.py: edit the menus there. The
server fills the markers in when it first serves a page (static_file() in starboard/server.py), so the pages do not
each carry 34 KB of the same menus. Run after adding a page to the menu: python3 tools/apply_shell.py
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from starboard.shell import HELP, MENU, PAGES, START, TAB_OF, block, help_page, shell  # noqa: E402,F401  (used by build_demo.py and the tests)

WEB = ROOT / "web"
EMPTY = f"{START}\n<!-- shell:end -->"


def check_help_links(root):
    """Every help link points at a file that exists in docs/help, and every page in the menu has one."""
    missing = [page for page in PAGES if page not in HELP]
    broken = [path for path, _ in HELP.values() if not (root / "docs/help" / path.split("#")[0]).is_file()]
    if missing or broken:
        raise SystemExit(f"Help links: pages with none {missing}, articles not found {sorted(set(broken))}")


def main():
    check_help_links(WEB.parent)
    pattern = re.compile(r"<!-- shell:start.*?-->.*?<!-- shell:end -->", re.S)
    for page in PAGES:
        path = WEB / page
        text = path.read_text(encoding="utf-8")
        if "shell:start" not in text:
            raise SystemExit(f"{page} has no shell markers")
        # The side menu needs room on the left: with-rail joins the page's own classes on <body>.
        text = re.sub(r'<body(?: class="([^"]*)")?>', lambda m: m.group(0) if "with-rail" in (m.group(1) or "").split()
                      else f'<body class="{((m.group(1) or "") + " with-rail").strip()}">', text, count=1)
        # Only the markers: the server fills them in (starboard/shell.py), so the pages do not each carry the shell.
        path.write_text(pattern.sub(lambda _: EMPTY, text, count=1), encoding="utf-8")
        print(f"updated {page}")


if __name__ == "__main__":
    main()
