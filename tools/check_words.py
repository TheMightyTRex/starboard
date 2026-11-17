"""Stops banned words coming back into the text people read (the design system's CONTENT-DESIGN.md section 2 and
section 5, and HELP-WRITING.md section 9). tools/checks.sh runs it.

Checks the pages (web/*.html), the strings in the pages' scripts (web/js/*.js, but not snaglist.js, which is
Snaglist's own copy) and the help (docs/help, with
help-centre.json's own words left to tools/check-help.py). The plug-in help in docs/help/plugins is left out: it is
mirrored from the starboard-plugins repository, whose own check reads it at the source. Code (fenced blocks,
`inline code`, scripts, styles, comments) is left out, and so is a banned word quoted on its own ("click"), which
names the word rather than using it.

A genuine exception goes in tools/words-allowed.txt, one per line: the file, a tab, a regular expression for the
line, a tab, and the reason.

Run: python3 tools/check_words.py [files]. It prints each hit as path:line and exits 1 when there is one.
Adapted from the design system's tools/check_words.py (17 November 2026)."""
import html, pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent.parent

# Each banned word, with the rule it breaks.
BANNED = [
    (r"see|sees|seen|seeing", "2.6 no see or look"),
    (r"look|looks|looked|looking", "2.6 no see or look"),
    (r"click\w*|tap|taps|tapped|tapping", "2.5 select, not click"),
    (r"enabl(e|es|ed|ing)|disabl(e|es|ed|ing)|toggl(e|es|ed|ing)|turn(s|ed|ing)? (on|off)", "2.9 activate and deactivate"),
    (r"typed|typing|typ(e|es) (a|an|the|it|its|your|in|b|m|q|f|DELETE|\d+|one|them|that|this|something|here|ahead)"
     r"|typ(e|es)-to-\w+|as you type", "2.18 enter, not type"),
    (r"above|below", "2.7 no positional directions"),
    (r"please", "1 voice: no please"),
    (r"just|simply|simple|simplest|easy|easier|easily|advanced", "2.15 no difficulty words"),
    (r"drive|drives", "5 disk, not drive"),
]
PATTERN = re.compile(r"(?<![\w-])(" + "|".join(f"(?:{p})" for p, _ in BANNED) + r")(?![\w-])", re.I)
ON_COLON = re.compile(r"(?<![\w-])(On|Off):")
# A banned word quoted on its own names the word ("click", 'type'), so it is not a use of it.
QUOTED_ALONE = re.compile(r"[\"'“‘]\s*(" + "|".join(p for p, _ in BANNED) + r")\s*[\"'”’]", re.I)
# Third-party names that hold a banned word.
NAMES = re.compile(r"Google Drive|OneDrive|Drive pools? \(StableBit\)", re.I)


def rule_for(word):
    for p, rule in BANNED:
        if re.fullmatch(p, word, re.I):
            return rule
    return ""


def without_comments(line, in_comment):
    """The line with every HTML comment taken out, also one that began on an earlier line or goes on to a later one
    (CodeQL py/bad-tag-filter). Returns (text, whether a comment is still open at the end of the line)."""
    out, i = [], 0
    while i < len(line):
        if in_comment:
            end = line.find("-->", i)
            if end < 0:
                return "".join(out), True
            i, in_comment = end + 3, False
            out.append(" ")
        else:
            start = line.find("<!--", i)
            if start < 0:
                out.append(line[i:])
                break
            out.append(line[i:start])
            i, in_comment = start + 4, True
    return "".join(out), in_comment


def markdown_lines(text):
    fenced = in_comment = False
    for n, line in enumerate(text.splitlines(), 1):
        if not in_comment and line.lstrip().startswith("```"):
            # A ```flow block is a chart people read, so its words are checked; other code blocks are not.
            fenced = False if fenced else ("code" if not line.lstrip().startswith("```flow") else "flow")
            continue
        if fenced == "code":
            continue
        line, in_comment = without_comments(line, in_comment)
        line = re.sub(r"`[^`]*`", " ", line)
        line = re.sub(r"\]\([^)]*\)", "]", line)  # link targets
        yield n, line


SHOWN_ATTRS = ("aria-label", "title", "alt", "placeholder", "data-copied", "aria-description", "content")


def html_lines(text):
    # Blank out scripts, styles, comments and code, keeping the line count.
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"<(script|style)\b.*?</\1\s*>", blank, text, flags=re.S | re.I)  # also "</script >"
    text = re.sub(r"<!--.*?--!?>", blank, text, flags=re.S)  # a comment also ends at "--!>", as browsers read it
    text = re.sub(r"<code\b.*?</code>", blank, text, flags=re.S | re.I)
    text = re.sub(r"\{\{[^}]*\}\}", " ", text)
    for n, line in enumerate(text.splitlines(), 1):
        shown = []
        for tag in re.findall(r"<[^>]*>", line):
            for name, value in re.findall(r'([\w-]+)="([^"]*)"', tag):
                if name in SHOWN_ATTRS:
                    shown.append(value)
        line = re.sub(r"<[^>]*>", " ", line)
        yield n, html.unescape(line + " " + " ".join(shown))


def string_lines(text, comment):
    """Strings in a script, one line at a time: comment lines and trailing comments left out."""
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(comment) or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        strings = re.findall(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', line)
        # The code inside a template string (${look.name}, ${drives.length}) is not words people read.
        words = " | ".join(re.sub(r"\$\{[^}]*\}", " ", s) for group in strings for s in group if s and " " in s)
        if words:
            yield n, words


def lines_of(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        return markdown_lines(text)
    if path.suffix == ".html":
        return html_lines(text)
    if path.suffix == ".js":
        return string_lines(text, "//")
    if path.suffix == ".sh":
        return string_lines(text, "#")
    return []


def default_files():
    files = sorted((root / "web").glob("*.html"))
    # snaglist.js is a copy of Snaglist, whose own repository checks its words.
    files += sorted(p for p in (root / "web" / "js").glob("*.js") if p.name != "snaglist.js")
    files += sorted(p for p in (root / "docs" / "help").rglob("*.md") if "plugins" not in p.relative_to(root / "docs" / "help").parts[:1])
    return [f for f in files if f.exists()]


def allowed():
    rules = []
    allow_file = root / "tools" / "words-allowed.txt"
    for line in allow_file.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3 or not parts[2].strip():
            sys.exit(f"words-allowed.txt: each line needs a file, a pattern and a reason: {line}")
        rules.append((parts[0], re.compile(parts[1])))
    return rules


def main(argv):
    files = [pathlib.Path(a).resolve() for a in argv] or default_files()
    exceptions = allowed()
    hits = 0
    for path in files:
        rel = path.relative_to(root).as_posix()
        raw = path.read_text(encoding="utf-8").splitlines()
        for n, line in lines_of(path):
            text = NAMES.sub(" ", QUOTED_ALONE.sub(" ", line))
            found = [(m.group(1), rule_for(m.group(1))) for m in PATTERN.finditer(text)]
            found += [(m.group(0), "2.9 Active, not On:") for m in ON_COLON.finditer(text)]
            if not found:
                continue
            source = raw[n - 1] if n <= len(raw) else line
            if any(f == rel and p.search(source) for f, p in exceptions):
                continue
            hits += 1
            words = ", ".join(sorted({f'"{w}" ({r})' for w, r in found}))
            print(f"{rel}:{n}: {words}: {source.strip()[:140]}")
    if hits:
        print(f"\n{hits} lines with banned words. Fix each one, or add a genuine exception, with its reason, to "
              "tools/words-allowed.txt.")
        return 1
    print(f"Banned words: none in {len(files)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
