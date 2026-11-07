#!/usr/bin/env python3
"""Puts the same footer on every help centre page and at the bottom of the README: download only what you have the
right to. The wording follows the installer's Usenet note (USENET_RIGHTS in starboard/terminal_setup.py and
web/js/common.js), widened from Usenet to every download app. Run it after adding a page; tools/check-help.py fails
when a page has no footer or an old one.

    python3 tools/help_footer.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
START = "<!-- footer: download rights -->"
END = "<!-- /footer -->"
FOOTER = f"""{START}

---

**Download only what you have the right to.** Use the download apps only for files you have the right to download,
such as open-source software, works in the public domain and your own backups. Downloading films, series, music or
books without the copyright holder's permission is against the law in the UK and most other countries. Starboard
does not host or provide any files, and you are responsible for what you download.

{END}
"""


def pages():
    """Every help centre page except the writing rules, and the README."""
    help_dir = ROOT / "docs" / "help"
    out = [p for p in sorted(help_dir.rglob("*.md")) if p.name != "HOW-THIS-HELP-IS-WRITTEN.md"]
    return out + [ROOT / "README.md"]


def with_footer(md):
    """`md` ending with the footer, replacing an earlier copy of it."""
    md = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", md, flags=re.S).rstrip() + "\n"
    return md + "\n" + FOOTER


def main():
    changed = 0
    for path in pages():
        md = path.read_text(encoding="utf-8")
        new = with_footer(md)
        if new != md:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"{changed} of {len(pages())} pages given the footer")


if __name__ == "__main__":
    main()
