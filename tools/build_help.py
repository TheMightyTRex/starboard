#!/usr/bin/env python3
"""Builds the help centre as web pages from docs/help, for GitHub Pages: one page for each article, with the
design system's styles (web/css), breadcrumbs, a search box on every page and a search page that works in the
browser with no server. The Markdown files stay the source: change them, and the pages are built again when the
change reaches main (.github/workflows/help.yml).

    python3 tools/build_help.py [--out _site]       then open _site/help/index.html

Needs the Python-Markdown package (pip install markdown==3.5.2). Pages go in <out>/help/<the same path>.html,
README.md becoming index.html; links between articles point at the pages, and links to other files in the
repository point at GitHub. 7 November 2026.
"""
import argparse
import html
import json
import pathlib
import re
import shutil

import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELP = ROOT / "docs" / "help"
REPO = "https://github.com/TheMightyTRex/starboard"
BLOB = f"{REPO}/blob/main/"
SITE = "https://themightytrex.github.io/starboard/help/"
LEAVE_OUT = {"HOW-THIS-HELP-IS-WRITTEN.md"}  # how the help is written: for writers, kept on GitHub
SECTIONS = {"guides": "Guides", "topics": "Topics", "basics": "Basics"}

LOGO = ('<svg class="help-logo" viewBox="0 0 32 32" width="28" height="28" aria-hidden="true" focusable="false">'
        '<rect x="3" y="3" width="12" height="12" fill="var(--color-logo-tile)"/>'
        '<rect x="3" y="17" width="12" height="12" fill="var(--color-logo-tile)"/>'
        '<rect x="17" y="17" width="12" height="12" fill="var(--color-logo-tile)"/>'
        '<path d="M23 3.5l1.9 4.4 4.7.4-3.6 3.1 1.1 4.6-4.1-2.5-4.1 2.5 1.1-4.6-3.6-3.1 4.7-.4Z" '
        'fill="var(--color-logo-star)"/></svg>')


def slug(value, separator="-"):
    """Heading ids as GitHub makes them, so links written for GitHub (#before-you-begin) still work."""
    value = re.sub(r"<[^>]+>", "", value).strip().lower()
    value = re.sub(r"[^\w\- ]", "", value)
    return value.replace(" ", separator)


def page_path(md):
    """docs/help/topics/x.md -> topics/x.html; README.md -> index.html."""
    rel = md.relative_to(HELP)
    return rel.with_name("index.html") if rel.name == "README.md" else rel.with_suffix(".html")


def fix_links(body, md):
    """Article links go to their pages; other repository files to GitHub; everything else is left alone."""
    here = md.parent

    def fix(m):
        attr, url = m.group(1), html.unescape(m.group(2))
        if re.match(r"^[a-z][a-z0-9+.-]*:|^#|^//", url, re.I):
            return m.group(0)
        path, _, anchor = url.partition("#")
        target = (here / path).resolve()
        try:
            rel_help = target.relative_to(HELP)
        except ValueError:
            try:
                return f'{attr}="{html.escape(BLOB + str(target.relative_to(ROOT)))}{"#" + anchor if anchor else ""}"'
            except ValueError:
                return m.group(0)
        if target.name in LEAVE_OUT:
            return f'{attr}="{html.escape(BLOB + str(target.relative_to(ROOT)))}{"#" + anchor if anchor else ""}"'
        if target.suffix == ".md":
            new = page_path(target)
            back = pathlib.Path(*[".."] * len(md.relative_to(HELP).parent.parts)) if md.relative_to(HELP).parent.parts else pathlib.Path(".")
            out = (back / new).as_posix()
        else:
            out = path  # an image or another file copied next to the pages
        return f'{attr}="{html.escape(out)}{"#" + anchor if anchor else ""}"'

    return re.sub(r'\b(href|src)="([^"]*)"', fix, body)


def crumbs_and_body(text):
    """The first line of an article is its trail, "[Help centre](../README.md) · Apps · how-to": that becomes the
    breadcrumbs. Returns (trail parts, kind, the rest)."""
    lines = text.splitlines()
    first = lines[0] if lines else ""
    if first.startswith("[Help centre]"):
        parts = [p.strip() for p in first.split("·")]
        kind = parts[-1] if len(parts) > 2 and parts[-1] in ("how-to", "reference", "troubleshooting", "concept", "guide") else ""
        middle = parts[1:-1] if kind else parts[1:]
        return middle, kind, "\n".join(lines[1:])
    return [], "", text


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


TEMPLATE = """<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Starboard help centre</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="{root}assets/css/tokens.css">
<link rel="stylesheet" href="{root}assets/css/components.css">
<link rel="stylesheet" href="{root}assets/css/help.css">
<script>try{{var t=localStorage.getItem("help-theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<a class="skip-link" href="#main">Skip to main content</a>
<header class="site-header site-header--no-rail">
  <div class="site-header__bar help-bar">
    <a class="site-header__brand" href="{root}index.html">{logo}<span>Starboard help centre</span></a>
    <form class="help-search" role="search" action="{root}search.html">
      <label class="visually-hidden" for="help-q">Search the help</label>
      <input class="input" type="search" id="help-q" name="q" placeholder="Search the help" autocomplete="off" value="{query}">
      <button class="btn" type="submit">Search</button>
    </form>
    <button class="btn btn--quiet help-theme" type="button" aria-pressed="false" hidden>Dark theme</button>
  </div>
</header>
<main id="main" tabindex="-1" class="page page--narrow help-page">
{crumbs}
<article class="prose">
{kind}{body}
</article>
{edit}
</main>
<footer class="site-footer help-footer">
  <p><a href="{root}index.html">Help centre</a> · <a href="{repo}">Starboard on GitHub</a> · <a href="{repo}/issues">Report a problem with this help</a></p>
</footer>
<script src="{root}assets/help.js"></script>
</body>
</html>
"""


def page(title, body, root, *, description="", crumbs="", kind="", edit="", canonical="", query=""):
    return TEMPLATE.format(title=html.escape(title), description=html.escape(description[:200]), canonical=canonical,
                           root=root, logo=LOGO, crumbs=crumbs, kind=kind, body=body, edit=edit, repo=REPO, query=query)


def build(out):
    site = out / "help"
    if site.exists():
        shutil.rmtree(site)
    (site / "assets" / "css").mkdir(parents=True)
    (site / "assets" / "fonts").mkdir()
    for name in ("tokens.css", "components.css"):
        shutil.copy(ROOT / "web" / "css" / name, site / "assets" / "css" / name)
    for f in (ROOT / "web" / "fonts").iterdir():
        shutil.copy(f, site / "assets" / "fonts" / f.name)
    shutil.copy(pathlib.Path(__file__).with_name("help_site.css"), site / "assets" / "css" / "help.css")
    shutil.copy(pathlib.Path(__file__).with_name("help_site.js"), site / "assets" / "help.js")
    if (HELP / "images").is_dir():
        shutil.copytree(HELP / "images", site / "images")

    index = []
    pages = sorted(p for p in HELP.rglob("*.md") if p.name not in LEAVE_OUT)
    for md in pages:
        rel_out = page_path(md)
        depth = len(rel_out.parent.parts)
        root = "../" * depth
        text = md.read_text(encoding="utf-8")
        trail, kind, rest = crumbs_and_body(text)
        conv = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"],
                                 extension_configs={"toc": {"slugify": slug}}, output_format="html")
        body = fix_links(conv.convert(rest), md)
        title_m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S)
        title = plain(title_m.group(1)) if title_m else "Starboard help centre"
        first_p = re.search(r"<p>(.*?)</p>", body, re.S)
        description = plain(first_p.group(1)) if first_p else ""
        section = SECTIONS.get(rel_out.parts[0], "") if len(rel_out.parts) > 1 else ""
        items = [f'<li><a href="{root}index.html">Help centre</a></li>']
        if section:
            items.append(f"<li>{html.escape(section)}</li>")
        items += [f"<li>{html.escape(t)}</li>" for t in trail if t and t != section]
        items.append(f'<li aria-current="page">{html.escape(title)}</li>')
        crumbs = f'<nav class="breadcrumbs" aria-label="Breadcrumb"><ol>{"".join(items)}</ol></nav>' if rel_out.name != "index.html" or depth else ""
        kind_html = f'<p class="prose__kind">{html.escape(kind.capitalize())}</p>\n' if kind else ""
        edit = (f'<p class="help-source small muted"><a href="{BLOB}{md.relative_to(ROOT).as_posix()}">'
                f"This page on GitHub</a>, where the help is written.</p>")
        target = site / rel_out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page(title, body, root, description=description, crumbs=crumbs, kind=kind_html, edit=edit,
                               canonical=SITE + rel_out.as_posix()), encoding="utf-8")
        headings = [plain(h) for h in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", body, re.S)]
        words = plain(re.sub(r"<h1[^>]*>.*?</h1>", "", body, flags=re.S))
        words = words.split("Download only what you have the right to")[0]  # the footer on every page
        index.append({"url": rel_out.as_posix(), "title": title, "section": section or (trail[0] if trail else ""),
                      "kind": kind, "summary": description[:220], "headings": headings, "text": words[:6000]})

    (site / "search-index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    search_body = ('<h1>Search the help</h1>\n<p id="help-results-count" class="muted" role="status" aria-live="polite">'
                   'Type what you want to do, such as "add a drive" or "forgotten password".</p>\n'
                   '<ol id="help-results" class="help-results"></ol>\n'
                   '<noscript><p>Search needs JavaScript. Every article is listed on the <a href="index.html">help centre '
                   'home</a>.</p></noscript>')
    (site / "search.html").write_text(page("Search the help", search_body, "", description="Search the Starboard help centre.",
                                           canonical=SITE + "search.html"), encoding="utf-8")
    # The site's own front door goes to the help centre.
    (out / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Starboard help centre</title>'
                                    '<meta http-equiv="refresh" content="0; url=help/index.html">'
                                    '<a href="help/index.html">Starboard help centre</a>\n', encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return len(pages)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="_site")
    a = ap.parse_args()
    n = build(pathlib.Path(a.out).resolve())
    print(f"{n} help pages in {a.out}/help, with search")


if __name__ == "__main__":
    main()
