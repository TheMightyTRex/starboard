#!/usr/bin/env python3
"""Check that every link into the help centre goes to an article that exists, and to a heading that exists.

It reads the help articles themselves, the release notes (CHANGELOG.md and docs/releases), the pages and scripts
in web/, the Python in starboard/ and tools/apply_shell.py. Anchors are made the way the help centre's builder and
GitHub make them: the heading's words in lower case, punctuation left out, spaces as hyphens. A link to a heading
that appears twice in one article is refused too, because GitHub and the help centre number the second one
differently.

    python3 tools/check-help-links.py            # problems only
    python3 tools/check-help-links.py --anchors  # also list every article's anchors
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELP = ROOT / "docs" / "help"
BLOB = re.compile(r"https://github\.com/TheMightyTRex/starboard/blob/main/docs/help/([^)\s\"'#>]+)(?:#([^)\s\"'>]*))?")
PAGES = re.compile(r"https://themightytrex\.github\.io/starboard/help/([^)\s\"'#>]*)(?:#([^)\s\"'>]*))?")


def slug(text):
    """A heading's anchor, as tools/help_centre/build.py and GitHub make it."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("`", "").replace("*", "")
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


def anchors(path):
    """(all anchors, anchors made twice) for one article."""
    md = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
    seen, twice = set(), set()
    for heading in re.findall(r"^#{1,6} +(.+?) *#*$", md, flags=re.M):
        s = slug(heading)
        (twice if s in seen else seen).add(s)
    seen |= set(re.findall(r'<a (?:id|name)="([^"]+)"', md))
    return seen, twice


def page_to_md(page):
    """A help centre page (topics/x.html, index.html, '') to its article."""
    page = page or "index.html"
    if page.endswith("/"):
        page += "index.html"
    if page.endswith("index.html"):
        return HELP / (page[:-len("index.html")] + "README.md")
    return HELP / re.sub(r"\.html$", ".md", page)


def main():
    cache = {}
    problems = []

    def check(where, target, anchor):
        if not target.is_file():
            problems.append(f"{where}: the link to {target.relative_to(ROOT)} goes nowhere")
            return
        if not anchor:
            return
        if target not in cache:
            cache[target] = anchors(target)
        have, twice = cache[target]
        if anchor not in have:
            problems.append(f"{where}: {target.relative_to(ROOT)} has no heading #{anchor}")
        elif anchor in twice:
            problems.append(f"{where}: {target.relative_to(ROOT)} has two headings #{anchor}, so the link is unclear")

    # Links inside the help.
    for path in sorted(HELP.rglob("*.md")):
        md = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        md = re.sub(r"`[^`\n]*`", "", md)
        rel = path.relative_to(ROOT)
        for n, line in enumerate(md.splitlines(), 1):
            for url in re.findall(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", line):
                if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
                    for m in list(BLOB.finditer(url)) + list(PAGES.finditer(url)):
                        target = HELP / m.group(1) if m.re is BLOB else page_to_md(m.group(1))
                        check(f"{rel}:{n}", target, m.group(2))
                    continue
                file, _, anchor = url.partition("#")
                target = (path.parent / file).resolve() if file else path
                if target.suffix != ".md" and not anchor:
                    if not target.exists():
                        problems.append(f"{rel}:{n}: the link to {file} goes nowhere")
                    continue
                if target.suffix == ".md" or not file:
                    check(f"{rel}:{n}", target, anchor)

    # Links from the release notes, the pages, the scripts and the code.
    others = [ROOT / "CHANGELOG.md", ROOT / "README.md", ROOT / "tools" / "apply_shell.py"]
    others += sorted((ROOT / "docs" / "releases").glob("*.md"))
    others += sorted((ROOT / "web").glob("*.html")) + sorted((ROOT / "web" / "js").glob("*.js"))
    others += sorted((ROOT / "starboard").glob("*.py")) + sorted((ROOT / "starboard").glob("*.sh"))
    others += sorted(ROOT.glob("*.sh")) + sorted((ROOT / "tools").glob("*.sh"))
    for path in others:
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for m in BLOB.finditer(line):
                check(f"{rel}:{n}", HELP / m.group(1), m.group(2))
            for m in PAGES.finditer(line):
                if "{" in m.group(0):
                    continue  # an address built in code, such as HELP_BASE + a page
                check(f"{rel}:{n}", page_to_md(m.group(1)), m.group(2))

    # The app's Help buttons (tools/apply_shell.py's HELP) and its help paths written as docs/help/... in code.
    shell = (ROOT / "tools" / "apply_shell.py").read_text()
    for path in set(re.findall(r'"((?:topics|guides|basics)/[\w-]+\.md(?:#[\w-]+)?|README\.md#[\w-]+)"', shell)):
        file, _, anchor = path.partition("#")
        check("tools/apply_shell.py (Help buttons)", HELP / file, anchor)
    for path in sorted((ROOT / "starboard").glob("*.py")) + sorted((ROOT / "web" / "js").glob("*.js")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for m in re.finditer(r"docs/help/((?:topics|guides|basics)/[\w-]+\.md)(?:#([\w-]+))?", line):
                check(f"{path.relative_to(ROOT)}:{n}", HELP / m.group(1), m.group(2))

    if "--anchors" in sys.argv:
        for path in sorted(HELP.rglob("*.md")):
            have, _ = anchors(path)
            print(f"{path.relative_to(HELP)}: {' '.join(sorted(have))}")
    for p in sorted(set(problems)):
        print(p)
    print(f"Help links: {len(set(problems))} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
