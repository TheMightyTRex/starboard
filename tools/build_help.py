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
<script>{prefs_js}</script>
</head>
<body>
<a class="skip-link" href="#main">Skip to main content</a>
<header class="site-header site-header--no-rail">
  <div class="site-header__bar help-bar">
    <button class="icon-btn help-menu-btn" type="button" aria-expanded="false" aria-controls="help-nav">{icon_menu}<span class="label">Menu</span></button>
    <a class="site-header__brand" href="{root}index.html" aria-label="Starboard help centre home">{logo}<span aria-hidden="true">Starboard help centre</span></a>
    <form class="help-search" role="search" action="{root}search.html">
      <label class="visually-hidden" for="help-q">Search the help</label>
      <input class="input" type="search" id="help-q" name="q" placeholder="Search the help" autocomplete="off" value="{query}">
      <button class="btn" type="submit">Search</button>
    </form>
    <button class="icon-btn" type="button" data-opens="help-display" aria-haspopup="dialog" aria-expanded="false">{icon_display}<span class="label">Display</span></button>
  </div>
</header>
<div class="help-layout{layout_class}">
<nav class="help-nav" id="help-nav" aria-label="Help centre">
  <button class="btn btn--quiet help-nav__hide" type="button" aria-expanded="true" aria-controls="help-nav-groups">{icon_hide}<span>Hide the menu</span></button>
  <div id="help-nav-groups" class="help-nav__groups">
{nav}
  </div>
</nav>
<button class="btn btn--quiet help-nav__show" type="button" aria-expanded="false" aria-controls="help-nav-groups" hidden>{icon_show}<span>Show the menu</span></button>
<main id="main" tabindex="-1" class="help-page">
{crumbs}
{toc_inline}
<article class="prose">
{kind}{body}
</article>
{edit}
</main>
{toc}
</div>
<footer class="site-footer help-footer">
  <p><a href="{root}index.html">Help centre</a> · <a href="{repo}">Starboard on GitHub</a> · <a href="{repo}/issues">Report a problem with this help</a></p>
</footer>
<div class="side-panel-layer" id="help-display" hidden>
  <div class="side-panel-backdrop"></div>
  <aside class="side-panel" role="dialog" aria-modal="true" aria-labelledby="help-display-h">
    <div class="panel-header"><h2 class="panel-header__title" id="help-display-h">Display and accessibility</h2><button class="icon-btn" type="button" data-closes aria-label="Close display and accessibility">{icon_x}</button></div>
    <form class="side-panel__body form-stack" id="help-display-form">
      <fieldset><legend>Theme</legend><div class="segmented"><label><input type="radio" name="theme" value="system"><span>Match device</span></label><label><input type="radio" name="theme" value="light"><span>Light</span></label><label><input type="radio" name="theme" value="dark"><span>Dark</span></label></div></fieldset>
      <fieldset><legend>Text size</legend><div class="segmented"><label><input type="radio" name="text" value="100"><span>100%</span></label><label><input type="radio" name="text" value="125"><span>125%</span></label><label><input type="radio" name="text" value="150"><span>150%</span></label><label><input type="radio" name="text" value="175"><span>175%</span></label></div></fieldset>
      <fieldset><legend>Reduce motion</legend><div class="segmented"><label><input type="radio" name="motion" value="device"><span>Match device</span></label><label><input type="radio" name="motion" value="on"><span>On</span></label><label><input type="radio" name="motion" value="off"><span>Off</span></label></div></fieldset>
      <label class="switch" for="help-pref-contrast"><span>High contrast</span><input type="checkbox" role="switch" id="help-pref-contrast" name="contrast"></label>
      <label class="switch" for="help-pref-underline"><span>Underline links</span><input type="checkbox" role="switch" id="help-pref-underline" name="underline"></label>
      <label class="switch" for="help-pref-spacing"><span>Wider text spacing</span><input type="checkbox" role="switch" id="help-pref-spacing" name="spacing"></label>
      <p class="small muted">Choices apply at once and are kept in this browser.</p>
    </form>
    <div class="side-panel__foot"><button class="btn btn--primary" type="button" data-closes>Done</button><button class="btn" type="button" id="help-display-reset">Reset</button></div>
  </aside>
</div>
<div id="help-announcer" class="visually-hidden" aria-live="polite"></div>
<script>window.SharedComponentsSprite = "{root}assets/icons/sprite.svg";</script>
<script src="{root}assets/components.js"></script>
<script src="{root}assets/help.js"></script>
</body>
</html>
"""

# Display and accessibility: the same choices and classes as the app (web/js/common.js), applied before the page
# draws so it never flashes. Kept in this browser only.
PREFS_JS = ("try{var p=JSON.parse(localStorage.getItem('help-display')||'{}'),r=document.documentElement;"
            "if(p.theme&&p.theme!=='system')r.dataset.theme=p.theme;if(p.text&&p.text!=='100')r.classList.add('pref-text-'+p.text);"
            "if(p.contrast)r.classList.add('pref-contrast');if(p.motion==='on')r.classList.add('pref-motion');"
            "if(p.motion==='off')r.classList.add('pref-motion-off');if(p.underline)r.classList.add('pref-underline');"
            "if(p.spacing)r.classList.add('pref-spacing');if(localStorage.getItem('help-nav')==='hidden')r.classList.add('help-nav-hidden')}catch(e){}")


def icon(name, root, size=20):
    return (f'<svg class="i{" i-lg" if size >= 20 else ""}" width="{size}" height="{size}" aria-hidden="true" focusable="false">'
            f'<use href="{root}assets/icons/sprite.svg#i-{name}"/></svg>')


def nav_groups():
    """The left menu, from the help centre home's own lists: each heading with links becomes a group."""
    groups, current = [], None
    for line in (HELP / "README.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,3} (.+)", line)
        if m:
            current = {"title": re.split(r":", m.group(1))[0].strip(), "items": []}
            groups.append(current)
            continue
        m = re.match(r"^- \[([^\]]+)\]\(([^)#]+\.md)\)", line)
        if m and current is not None:
            current["items"].append((m.group(1), page_path(HELP / m.group(2)).as_posix()))
    return [g for g in groups if g["items"]]


def nav_html(groups, here, root):
    out = []
    for n, g in enumerate(groups):
        has = any(url == here for _, url in g["items"])
        items = "".join(f'<li><a href="{root}{url}"{" aria-current=\"page\"" if url == here else ""}>{html.escape(t)}</a></li>'
                        for t, url in g["items"])
        out.append(f'<div class="help-nav__group"><h2 class="help-nav__heading"><button type="button" aria-expanded="{"true" if has else "false"}" '
                   f'aria-controls="help-nav-{n}">{html.escape(g["title"])}</button></h2>'
                   f'<ul id="help-nav-{n}"{"" if has else " hidden"}>{items}</ul></div>')
    return "\n".join(out)


def toc_html(body):
    """The article's sections, for On this page: (the menu that follows the article, the one inside it on phones)."""
    heads = [(i, plain(t)) for i, t in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body, re.S)]
    if len(heads) < 2:
        return "", ""
    links = "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in heads)
    side = f'<nav class="help-toc" aria-labelledby="help-toc-h"><h2 class="help-toc__heading" id="help-toc-h">On this page</h2><ul>{links}</ul></nav>'
    inline = f'<details class="disclosure help-toc-inline"><summary>On this page</summary><div class="disclosure__body"><ul>{links}</ul></div></details>'
    return side, inline


def page(title, body, root, *, description="", crumbs="", kind="", edit="", canonical="", query="", nav="", toc=("", "")):
    return TEMPLATE.format(title=html.escape(title), description=html.escape(description[:200]), canonical=canonical,
                           root=root, logo=LOGO, crumbs=crumbs, kind=kind, body=body, edit=edit, repo=REPO, query=query,
                           prefs_js=PREFS_JS, nav=nav, toc=toc[0], toc_inline=toc[1],
                           layout_class="" if toc[0] else " help-layout--no-toc",
                           icon_menu=icon("menu", root), icon_display=icon("sun", root), icon_x=icon("x", root),
                           icon_hide=icon("chevron-left", root, 18), icon_show=icon("chevron-right", root, 18))


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
    shutil.copy(ROOT / "web" / "js" / "components.js", site / "assets" / "components.js")
    (site / "assets" / "icons").mkdir()
    shutil.copy(ROOT / "web" / "icons" / "sprite.svg", site / "assets" / "icons" / "sprite.svg")
    groups = nav_groups()
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
        # Mermaid flowcharts (the guides' steps) are drawn in the browser, as GitHub draws them.
        body, charts = re.subn(r'<pre><code class="language-mermaid">(.*?)</code></pre>', r'<pre class="mermaid">\1</pre>', body, flags=re.S)
        if charts:
            body += ('\n<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";'
                     'mermaid.initialize({startOnLoad: true, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default"});</script>')
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
                               canonical=SITE + rel_out.as_posix(), nav=nav_html(groups, rel_out.as_posix(), root),
                               toc=toc_html(body) if rel_out.name != "index.html" else ("", "")), encoding="utf-8")
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
                                           canonical=SITE + "search.html", nav=nav_html(groups, "search.html", "")), encoding="utf-8")
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
