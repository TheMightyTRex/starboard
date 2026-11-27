#!/usr/bin/env python3
"""Which pages does a change touch? Used by tools/done-check.sh and the a11y pull request workflow.

    python3 tools/changed-pages.py [--base origin/main] [--sample] [--json]

Reads the files the change touches (committed, uncommitted and new, against the merge base with --base) and maps them
to the pages in web/:

  web/NAME.html                the page itself
  web/js/X.js, web/css/X.css   every page whose HTML loads that file (a file no page names directly counts as shared)
  web/*.json                   shared (the set-up steps and the cloud services are read by several pages)
  tools/a11y/*                 shared (the checks themselves changed, so every page is checked again)

A file loaded by more than half of the pages is shared. With a shared file the answer is every page, unless --sample
is given: then it is the small fixed sample the layout check uses (the header, the side menu and the commonest page
kinds), which keeps a pull request check light. Prints the pages as one comma separated line (what PAGES takes), or
with --json the pages, the reasons and which kinds of file changed.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
# The pages the checks leave out of "every page" (tools/a11y/order.mjs): they are tested by their own states.
LEFT_OUT = {"login.html", "setup.html", "offline.html", "wanted-moved.html"}
SAMPLE = ["index.html", "system.html", "settings-general-appearance.html", "settings-reelix.html", "discover-films.html",
          "library-films.html", "dashboard.html", "downloads.html"]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")


def changed_files(base):
    merge_base = (git("merge-base", "HEAD", base)[0] or base).strip()
    files = set(git("diff", "--name-only", merge_base)) | set(git("ls-files", "--others", "--exclude-standard"))
    return sorted(f for f in files if f)


def all_pages():
    return sorted(p.name for p in WEB.glob("*.html") if p.name not in LEFT_OUT)


def loaded_by():
    """For each script and style file, the pages that name it."""
    users = {}
    for page in sorted(WEB.glob("*.html")):
        text = page.read_text(encoding="utf-8", errors="replace")
        for ref in set(re.findall(r'(?:src|href)="/?((?:js|css)/[^"?#]+)', text)):
            users.setdefault(ref, set()).add(page.name)
    return users


def pages_for(files, sample=False):
    pages, reasons = set(), []
    shared = False
    users = loaded_by()
    every = all_pages()
    kinds = {"web": False, "css": False, "server": False, "checks": False}
    for f in files:
        if f.startswith("web/") and f.endswith(".html") and "/" not in f[4:]:
            kinds["web"] = True
            pages.add(f[4:])
            reasons.append(f"{f}: the page itself")
        elif f.startswith(("web/js/", "web/css/")):
            kinds["web"] = True
            kinds["css"] = kinds["css"] or f.startswith("web/css/")
            mine = users.get(f[4:], set())
            if not mine or len(mine) > len(every) / 2:
                shared = True
                reasons.append(f"{f}: shared (loaded by {len(mine) or 'no page named here, so every'} pages)")
            else:
                pages |= mine
                reasons.append(f"{f}: loaded by {len(mine)} page" + ("" if len(mine) == 1 else "s"))
        elif f.startswith("web/") and f.endswith(".json"):
            kinds["web"] = True
            shared = True
            reasons.append(f"{f}: read by several pages")
        elif f.startswith("tools/a11y/") or f == "tools/a11y.sh":
            kinds["checks"] = True
            shared = True
            reasons.append(f"{f}: the accessibility checks themselves changed")
        elif f.startswith("starboard/"):
            kinds["server"] = True
    if shared:
        pages = set(SAMPLE if sample else every) | (pages if sample else set())
    pages = sorted(p for p in pages if (WEB / p).exists())
    return pages, reasons, kinds, shared


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--sample", action="store_true", help="a shared file gives the fixed sample, not every page")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--files", nargs="*", help="use these changed files instead of asking git (for tests)")
    a = ap.parse_args()
    files = a.files if a.files is not None else changed_files(a.base)
    pages, reasons, kinds, shared = pages_for(files, a.sample)
    if a.json:
        print(json.dumps({"pages": pages, "reasons": reasons, "kinds": kinds, "shared": shared, "files": len(files)}, indent=1))
    else:
        print(",".join(pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
