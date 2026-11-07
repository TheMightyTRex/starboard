"""Help centre articles for the help slide-out (LIBRARY.md, Help links: in-page help opens in a slide-out).

The browser may only talk to Starboard (connect-src 'self'), so Starboard fetches the article from the help centre,
keeps the article's own text and a short list of safe tags, and hands it over as data. The page draws it with
el(), never as HTML. Only article paths that look like docs/help paths are fetched, always from the one help
centre address, and a few are kept in memory for an hour.
"""

import re
import threading
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

HELP_CENTRE = "https://themightytrex.github.io/starboard/help/"
PAGE = re.compile(r"^(?:topics|basics|guides)/[a-z0-9][a-z0-9-]{0,80}\.md$")
KEEP_SECONDS = 3600
KEEP_MAX = 40
MAX_BYTES = 1_000_000

# Tags kept, and the attributes each may keep. Everything else is dropped; its text is kept unless it is in SKIP.
TAGS = {
    "h2": ("id",), "h3": ("id",), "h4": ("id",), "p": (), "ul": (), "ol": (), "li": (), "strong": (), "em": (),
    "code": (), "pre": (), "kbd": (), "br": (), "blockquote": (), "a": ("href",), "img": ("src", "alt"),
    "figure": (), "figcaption": (), "table": (), "thead": (), "tbody": (), "tr": (), "th": (), "td": (),
}
SKIP = {"script", "style", "template", "iframe", "object", "svg", "button", "form", "nav", "h1"}
EMPTY = {"br", "img"}

_cache = {}
_lock = threading.Lock()


class HelpError(Exception):
    pass


def page_url(page):
    if not PAGE.match(page or ""):
        raise HelpError("That is not a help centre article.")
    return HELP_CENTRE + page[:-3] + ".html"


class _Article(HTMLParser):
    """Collects the children of <article class="prose"> as [tag, attrs, children] lists and strings."""

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.depth = 0       # nesting inside the article; 0 means outside it
        self.skip = 0        # nesting inside a dropped tag whose text is dropped too
        self.root = []
        self.stack = [self.root]
        self.kind = ""

    def _url(self, value, image=False):
        url = urllib.parse.urljoin(self.base, value.strip())
        if url.startswith(HELP_CENTRE) or (not image and url.startswith("https://")):
            return url
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.depth:
            if tag == "article" and "prose" in (a.get("class") or "").split():
                self.depth = 1
            return
        if tag not in EMPTY:
            self.depth += 1
        if self.skip or tag in SKIP:
            if tag not in EMPTY:
                self.skip += 1
            return
        if tag == "pre" and "mermaid" in (a.get("class") or ""):
            self.skip += 1          # a diagram drawn by the help centre's script: only the help centre can show it
            return
        if tag == "p" and "prose__kind" in (a.get("class") or ""):
            self.skip += 1          # the article's kind ("How-to") is not part of the help
            return
        if tag not in TAGS:
            if tag not in EMPTY:
                self.stack.append(self.stack[-1])   # unwrap: its children go to the parent
            return
        kept = {}
        for name in TAGS[tag]:
            value = a.get(name)
            if value is None:
                continue
            if name == "href":
                if value.startswith("#"):
                    kept[name] = value
                    continue
                value = self._url(value)
            elif name == "src":
                value = self._url(value, image=True)
            if value is not None:
                kept[name] = value[:2000]
        node = [tag, kept, []]
        self.stack[-1].append(node)
        if tag not in EMPTY:
            self.stack.append(node[2])

    def handle_startendtag(self, tag, attrs):
        if tag in EMPTY:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if not self.depth or tag in EMPTY:
            return
        self.depth -= 1
        if not self.depth:
            return
        if self.skip:
            self.skip -= 1
            return
        if len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data):
        if self.depth and not self.skip and data:
            self.stack[-1].append(data)


def _title(html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def parse(html, url):
    p = _Article(url)
    p.feed(html)
    return {"title": _title(html), "url": url, "body": p.root}


def article(page, fetch=None):
    """The article at docs/help path `page` ("topics/x.md") as {title, url, body}."""
    url = page_url(page)
    now = time.time()
    with _lock:
        hit = _cache.get(url)
        if hit and now - hit[0] < KEEP_SECONDS:
            return hit[1]
    try:
        html = (fetch or _fetch)(url)
    except Exception as e:  # noqa: BLE001 - any failure means the same thing to the reader
        raise HelpError("The help centre could not be reached. Read it in the help centre instead.") from e
    data = parse(html, url)
    if not data["body"]:
        raise HelpError("That article has no text yet. Read it in the help centre instead.")
    with _lock:
        if len(_cache) >= KEEP_MAX:
            _cache.pop(min(_cache, key=lambda k: _cache[k][0]))
        _cache[url] = (now, data)
    return data


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Starboard"})
    with urllib.request.urlopen(req, timeout=8) as r:  # the fixed help centre address, checked above  # nosec B310
        return r.read(MAX_BYTES).decode("utf-8", "replace")
