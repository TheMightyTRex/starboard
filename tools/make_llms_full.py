#!/usr/bin/env python3
"""Writes docs/help/llms-full.txt: the developer pages in one plain text file, for AI tools that read one file
(DASH-275, rule D8 in the developer best practice). It is made from the pages, so it cannot differ from them.

    python3 tools/make_llms_full.py            write it
    python3 tools/make_llms_full.py --check    fail when it is out of date (bash tools/check-api.sh runs this)
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELP = ROOT / "docs" / "help"
OUT = HELP / "llms-full.txt"
# In the order a developer reads them: the API first, then the plug-ins.
PAGES = [
    "developers/api-quickstart.md", "developers/api-authentication.md", "developers/mcp-tools.md",
    "developers/api-reference.md", "../api/errors.md", "developers/api-changelog.md",
    "developers/make-a-plugin.md", "developers/plugin-manifest-reference.md", "developers/plugin-api-reference.md",
    "developers/test-and-publish-a-plugin.md", "developers/update-a-plugin-safely.md",
    "developers/compatibility-promise.md",
]
HEAD = """# Starboard: the developer pages in one file

> Starboard is a lightweight home-server dashboard and installer, with an API at /api/v1 and plug-ins that run in
> locked-down containers. This file holds the developer pages in full, for tools that read one file. The index, with a
> line for each page, is llms.txt. Made by tools/make_llms_full.py from docs/help; do not change it by hand.
"""


def body(path):
    text = (HELP / path).read_text()
    text = re.sub(r"<!-- footer: download rights -->.*?<!-- /footer -->", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = [l for l in text.split("\n") if not l.startswith("[Help centre](")]
    text = "\n".join(lines)
    # a relative link keeps its words; the page it names is in this file or in the index
    text = re.sub(r"\]\((?!https?:)[^)]*\)", "]", text)
    text = re.sub(r"!\[[^\]]*\]\][^\n]*", "", text) if False else text
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def build():
    parts = [HEAD]
    for rel in PAGES:
        parts.append(f"\n---\n\nSource: {pathlib.PurePosixPath('docs/help', rel)}\n\n" + body(rel))
    return "".join(parts)


def main():
    text = build()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print("docs/help/llms-full.txt is out of date: run python3 tools/make_llms_full.py")
            return 1
        print("docs/help/llms-full.txt is up to date")
        return 0
    OUT.write_text(text)
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(text):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
