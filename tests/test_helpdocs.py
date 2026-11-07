"""In-page help in a slide-out: articles from the help centre come over as safe data (helpdocs.py)."""

import pathlib
import re
import unittest

from starboard import helpdocs

ARTICLE = """<html><head><title>x</title><script>bad()</script></head><body>
<nav><a href="../index.html">Home</a></nav>
<main><article class="prose">
<p class="prose__kind">How-to</p>
<h1 id="t">Choose a Usenet provider</h1>
<p>Read <a href="../basics/what-is-usenet.html">What Usenet is</a> or <a href="#steps">the steps</a>.</p>
<p onclick="steal()">Bad <a href="javascript:alert(1)">link</a> and <a href="http://plain.example">plain</a>.</p>
<script>alert(1)</script><style>p{}</style>
<h2 id="steps">Steps</h2>
<ol><li>Go to <strong>Settings</strong>.<br>Then <code>this</code>.</li></ol>
<figure><img src="../images/a.png" alt="The Settings page"><figcaption>Settings</figcaption></figure>
<img src="http://elsewhere.example/x.png" alt="x">
<pre class="mermaid">flowchart LR</pre>
<div class="callout"><p>Inside a div</p><svg><text>drawn</text></svg></div>
</article></main><footer>Footer</footer></body></html>"""

BASE = helpdocs.HELP_CENTRE + "topics/choose-a-usenet-provider.html"


def flat(nodes):
    out = []
    for n in nodes:
        if isinstance(n, str):
            out.append(n)
        else:
            out.append(n)
            out.extend(flat(n[2]))
    return out


class HelpDocsTest(unittest.TestCase):
    def setUp(self):
        helpdocs._cache.clear()
        self.data = helpdocs.parse(ARTICLE, BASE)
        self.all = flat(self.data["body"])
        self.tags = [n for n in self.all if not isinstance(n, str)]
        self.text = "".join(n for n in self.all if isinstance(n, str))

    def test_only_paths_like_docs_help_are_fetched(self):
        for bad in ["", "topics/../x.md", "https://evil.example/x.md", "topics/x.html", "other/x.md", "topics/X.md", "topics/x.md?a"]:
            with self.assertRaises(helpdocs.HelpError, msg=bad):
                helpdocs.page_url(bad)
        self.assertEqual(helpdocs.page_url("basics/what-is-usenet.md"), helpdocs.HELP_CENTRE + "basics/what-is-usenet.html")

    def test_the_title_comes_from_the_heading_and_is_left_out_of_the_body(self):
        self.assertEqual(self.data["title"], "Choose a Usenet provider")
        self.assertNotIn("h1", [t[0] for t in self.tags])
        self.assertNotIn("How-to", self.text)

    def test_only_safe_tags_and_attributes_are_kept(self):
        for tag, attrs, _ in self.tags:
            self.assertIn(tag, helpdocs.TAGS)
            self.assertLessEqual(set(attrs), set(helpdocs.TAGS[tag]))
        self.assertNotIn("bad()", self.text)
        self.assertNotIn("alert", self.text)
        self.assertNotIn("p{}", self.text)
        self.assertNotIn("drawn", self.text)
        self.assertNotIn("flowchart", self.text)
        self.assertNotIn("Footer", self.text)
        self.assertNotIn("Home", self.text)
        self.assertIn("Inside a div", self.text)

    def test_links_are_made_whole_and_unsafe_ones_lose_their_address(self):
        links = [t[1].get("href") for t in self.tags if t[0] == "a"]
        self.assertEqual(links, [helpdocs.HELP_CENTRE + "basics/what-is-usenet.html", "#steps", None, None])

    def test_pictures_only_from_the_help_centre(self):
        srcs = [t[1].get("src") for t in self.tags if t[0] == "img"]
        self.assertEqual(srcs, [helpdocs.HELP_CENTRE + "images/a.png", None])

    def test_articles_are_kept_for_a_while_and_failures_say_what_to_do(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return ARTICLE
        helpdocs.article("topics/choose-a-usenet-provider.md", fetch)
        helpdocs.article("topics/choose-a-usenet-provider.md", fetch)
        self.assertEqual(len(calls), 1)
        def broken(url):
            raise OSError("offline")
        with self.assertRaisesRegex(helpdocs.HelpError, "help centre"):
            helpdocs.article("topics/other.md", broken)

    def test_every_in_page_help_opens_a_slide_out(self):
        web = pathlib.Path(__file__).resolve().parent.parent / "web"
        for f in (web / "js").glob("*.js"):
            s = f.read_text(encoding="utf-8")
            if f.name != "common.js":  # helpCentreLink(), the one link that opens the help centre in a new tab
                self.assertFalse(re.search(r'class: "help-link", href', s), f"{f.name}: in-page help must use helpButton()")
            for summary in re.findall(r'el\("summary", \{ text: "([^"]+)"', s):
                self.assertFalse(summary.startswith(("How ", "Which ", "What is")), f"{f.name}: help '{summary}' is a fold-out")
        for f in web.glob("*.html"):
            for a in re.findall(r"<a [^>]*data-help-link>.*?</a>", f.read_text(encoding="utf-8"), re.S):
                self.assertIn("M15 3h6v6", a, f"{f.name}: the header Help needs the new-tab help icon")


if __name__ == "__main__":
    unittest.main()
