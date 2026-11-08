"""Makes a help picture's page from one terminal screen kept by the terminal check (tools/vm/drive.py writes every
screen to screens.html). Each line becomes its own element, so annotate.js can outline a line by its text, and
groups of lines can be outlined together. The page goes in tools/screenshots/terminal/ and help_shots.json names it
as "terminal/<name>.html"; tools/help-screenshots.sh then marks it up like any other page. 8 November 2026.

  python3 tools/screenshots/terminal_page.py SCREENS.html INDEX NAME [--group id:FIRST:LAST ...] [--swap old=new ...]

INDEX counts the screens from 0, as screens.html numbers them. A group wraps lines FIRST to LAST (from 0) in an
element with that id, for a "$#id" mark. A swap replaces text, so no test machine's address or code is shown:
addresses become documentation ones (192.0.2.x) and codes made-up ones.
"""

import argparse
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<style>
  html, body {{ margin: 0; background: #0d1020; }}
  body {{ padding: 28px 32px; }}
  .term {{ display: inline-block; background: #14182e; color: #e8eaf6; padding: 14px 20px; border-radius: 8px;
          font: 15px/1.3 "DejaVu Sans Mono", "Liberation Mono", monospace; white-space: pre; }}
  .l {{ min-height: 1.3em; }}
  .t {{ display: inline-block; }}
</style>
<div class="term">{lines}</div>
"""


def lines_of(screens, index):
    parts = re.split(r"<h2[^>]*>", screens)[1:]
    pre = re.search(r"<pre>(.*?)</pre>", parts[index], re.S).group(1)
    return pre.split("\n")


def line_html(line):
    """The line's leading spaces stay outside .t, so an outline hugs the words."""
    text = html.unescape(re.sub(r"<[^>]+>", "", line))
    lead = len(text) - len(text.lstrip(" "))
    if not text.strip():
        return '<div class="l"></div>'
    # Cut the first `lead` characters of text out of the (span-wrapped) line.
    out, left = "", lead
    for m in re.finditer(r'(<span[^>]*>)(.*?)(</span>)', line, re.S):
        open_, body, close = m.groups()
        raw = html.unescape(body)
        take = min(left, len(raw))
        left -= take
        rest = raw[take:]
        if rest:
            out += open_ + html.escape(rest) + close
    return f'<div class="l">{" " * lead}<span class="t">{out}</span></div>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("screens")
    ap.add_argument("index", type=int)
    ap.add_argument("name")
    ap.add_argument("--group", action="append", default=[])
    ap.add_argument("--swap", action="append", default=[])
    a = ap.parse_args()
    lines = lines_of(open(a.screens, encoding="utf-8").read(), a.index)
    for swap in a.swap:
        old, new = swap.split("=", 1)
        lines = [l.replace(html.escape(old), html.escape(new)) for l in lines]
    while lines and not re.sub(r"<[^>]+>", "", lines[-1]).strip():
        lines.pop()
    body = [line_html(l) for l in lines]
    for group in a.group:
        gid, first, last = group.split(":")
        first, last = int(first), int(last)
        body[first] = f'<div id="{gid}" style="display:inline-block;margin:8px 0;padding:2px 0">' + body[first]
        body[last] = body[last] + "</div>"
    os.makedirs(os.path.join(HERE, "terminal"), exist_ok=True)
    path = os.path.join(HERE, "terminal", a.name + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(PAGE.format(title=html.escape(a.name), lines="".join(body)))
    for n, l in enumerate(lines):
        print(f"{n:2d} {html.unescape(re.sub(r'<[^>]+>', '', l)).rstrip()}")
    print("Written", os.path.relpath(path))


if __name__ == "__main__":
    main()
