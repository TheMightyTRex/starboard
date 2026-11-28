#!/usr/bin/env python3
"""Fails a page that has an "On this page" list of jump links, because separate topics are page topics (tabs).

Owner decision, 28 November 2026 (docs/LIBRARY.md, Page topics: tabs, not a jump list). An "On this page" list is
only for one long single-topic document: a help article, release notes, a guide in this library. Each file that
may keep one is named in tools/on-this-page-allowed.txt with its reason: a pattern for the path, a tab, the reason.

It looks for the list in a page's markup and in the scripts and templates that write markup: the words "On this
page" as a heading or an accessible name, or the page-links class. Prose that only mentions the words is left alone.

Run: python3 tools/check_on_this_page.py [files or folders]. With none, it checks the whole repository. It prints
each hit as path:line and exits 1 when there is one. Copy this file and the allowed list into an app to use it there;
the app's own allowed list should be empty or name only documents."""
import fnmatch
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", "vendor", "out", "done-check-out"}
SUFFIXES = {".html", ".js", ".py", ".mjs"}
# "On this page" as a heading or a name (not "Topics on this page", the tablist's own name), or the old list's class.
HIT = re.compile(r"""(>\s*On this page\s*<|aria-label=["']On this page["']|["']On this page["']\s*,\s*\[?\s*\(|class=["'][^"']*\bpage-links\b)""")


def allowed(path):
    here = pathlib.Path(__file__).resolve().parent / "on-this-page-allowed.txt"
    rules = []
    if here.exists():
        for line in here.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                pattern, _, reason = line.partition("\t")
                if not reason.strip():
                    print(f"on-this-page-allowed.txt: {pattern!r} has no reason")
                    sys.exit(1)
                rules.append(pattern.strip())
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    return any(fnmatch.fnmatch(rel, r) for r in rules)


def files(args):
    if not args:
        args = [str(root)]
    for a in args:
        p = pathlib.Path(a).resolve()
        if p.is_file():
            yield p
        else:
            for f in sorted(p.rglob("*")):
                if f.suffix in SUFFIXES and f.is_file() and not (SKIP_DIRS & set(f.relative_to(p).parts)):
                    yield f


def main():
    bad = 0
    for f in files(sys.argv[1:]):
        if f.name == pathlib.Path(__file__).name or allowed(f):
            continue
        for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if HIT.search(line):
                bad += 1
                print(f"{f.relative_to(root) if f.is_relative_to(root) else f}:{n}: an On this page list. Make the topics tabs (docs/LIBRARY.md, Page topics: tabs, not a jump list), or name this file in tools/on-this-page-allowed.txt with the reason it is one document.")
    if bad:
        print(f"{bad} place(s) with an On this page list")
        return 1
    print("No On this page lists outside the documents named in tools/on-this-page-allowed.txt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
