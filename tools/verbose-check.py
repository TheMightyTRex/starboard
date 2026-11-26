#!/usr/bin/env python3
"""Scores text for verbosity against guides/CONTENT-DESIGN.md rule 2.12 and its neighbours (26 November 2026).

It reads Markdown, HTML, JSON manifests, and the strings in JavaScript and Python, then counts:
  long sentences (over 25 words), long paragraphs (over 4 sentences), filler phrases, passive-voice hints,
  repeated sentences (inside a file and across the files of one repository), headings that restate the page
  title, and pages over the word target for their type (TARGETS below).

It only measures. It never changes a file, and it exits 0 unless --fail is given (the CI check warns first).

    python3 verbose-check.py audit  NAME=PATH [NAME=PATH ...] [--json out.json]   audit whole repositories
    python3 verbose-check.py files  FILE [FILE ...]                             score single files
    python3 verbose-check.py ci     [--base origin/main] [--root .] [--fail]    warn on the lines a change adds (GitHub annotations)
    python3 verbose-check.py stats  NAME=PATH ...                               word-count distribution per type

A genuine exception goes in tools/verbose-allowed.txt in the repository, one per line: the file, a tab, a regular
expression for the sentence, a tab, and the reason (the same layout as words-allowed.txt).
"""
import ast, collections, html, json, pathlib, re, subprocess, sys
from html.parser import HTMLParser

MAX_SENTENCE = 25
MAX_PARAGRAPH_SENTENCES = 4

# Target: average sentence 15 to 20 words (Plain English Campaign), none over 25 (our rule 2.12). Target words of prose per page, by type (set from the 26 November 2026 audit; see the audit report, section 4).
TARGETS = {
    "help-topic-how-to": 450, "help-topic-reference": 500, "help-topic-troubleshooting": 350, "help-topic-overview": 250,
    "help-topic": 400, "help-guide": 400, "help-basics": 500, "help-developers": 700, "help-comparison": 600,
    "help-accessibility": 450, "plugin-help": 350, "readme": 900, "docs": 900, "release-notes": 300,
    "changelog": 300,
}

FILLERS = [
    r"in order to", r"in order for", r"please note( that)?", r"it is important to( note| remember)?", r"it is worth (noting|mentioning)",
    r"it should be noted", r"note that", r"keep in mind( that)?", r"needless to say", r"simply", r"just", r"very", r"really",
    r"basically", r"actually", r"essentially", r"obviously", r"quite", r"fairly", r"rather than simply",
    r"you can then", r"you will then", r"you may then", r"and then", r"at this point", r"at the moment", r"at this time",
    r"in the event (that|of)", r"due to the fact that", r"because of the fact that", r"a (number|variety|range) of", r"various",
    r"is able to", r"are able to", r"be able to", r"allows? you to", r"enables? you to", r"lets? you", r"gives? you the (ability|option) to",
    r"make sure (that )?", r"ensure that", r"with (regard|respect) to", r"in relation to", r"prior to", r"subsequent to",
    r"utili[sz]e[sd]?", r"leverag\w+", r"as follows", r"the following", r"once you have", r"if you (would )?(like|want|wish) to",
    r"you (may|might) (wish|want|like) to", r"feel free to", r"in addition( to)?", r"additionally", r"furthermore", r"moreover",
    r"as well as", r"in the future", r"going forward", r"seamless\w*", r"robust", r"powerful", r"easily", r"effortless\w*",
    r"enhanced?", r"a lot of", r"in general", r"for the most part", r"as a result of", r"on the other hand", r"that said",
    r"whether or not", r"each and every", r"first and foremost", r"at all times", r"as needed", r"if necessary", r"if needed",
    r"there (is|are) (a|an|some|no)? ?\w* ?(that|which|who)", r"the fact that", r"in this (page|topic|article|section|guide)",
    r"this (page|topic|article|section|guide) (explains|describes|shows|covers|tells you)", r"you will (need|want) to",
    r"you (need|have) to", r"is used to", r"are used to", r"can be used to", r"so that you can", r"in the same way",
]
FILLER_RE = re.compile(r"(?<![\w-])(" + "|".join(FILLERS) + r")(?![\w-])", re.I)
# A passive hint: a form of "to be" then a past participle. Only a hint: "is set to" and "is shown" trigger it too.
PASSIVE_RE = re.compile(r"\b(is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?(\w+ed|shown|made|done|kept|set|given|found|run|built|held|sent|"
                        r"put|read|written|stored|taken|chosen|seen|known|used|shown|left|lost|hidden|began|begun|drawn|split)\b(?!\s+(?:to|on|at|in)\b\s*$)", re.I)
PASSIVE_SKIP = re.compile(r"\b(is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?(need|needed|red|bed|speed|embed|seed|feed|proceed|exceed|"
                          r"succeed|indeed|hundred|sacred|naked|wicked|ragged|beloved|prefer|preferred|limited to|related to|"
                          r"supposed to|interested|concerned|tired|finished|connected|signed in|logged in|turned|based|located)\b", re.I)

# Plain English Campaign, "The A to Z of alternative words" (2024) and "How to write in plain English" (read 26 November 2026,
# plainenglish.co.uk, free guides). The list below is our own short selection of what applies to software text, written for this
# checker. It applies the guide and does not copy it. Where a word is an on-screen label or a Starboard term, the label wins.
REPLACE = {
    "additional": "extra, more", "advise": "tell", "ascertain": "find out", "assist": "help", "assistance": "help",
    "approximately": "about", "attempt": "try", "commence": "start", "terminate": "end, stop", "cease": "stop",
    "consequently": "so", "currently": "now (or leave out)", "demonstrate": "show", "determine": "decide, work out",
    "discontinue": "stop", "disseminate": "spread", "endeavour": "try", "ensure": "make sure", "facilitate": "help",
    "furnish": "give", "furthermore": "also", "generate": "make", "indicate": "show", "initially": "at first",
    "initiate": "start", "locate": "find", "modification": "change", "moreover": "also", "nevertheless": "but",
    "numerous": "many", "obtain": "get", "operate": "work, run", "optimum": "best", "permit": "let", "personnel": "staff",
    "prior to": "before", "proceed": "go on", "provide": "give", "purchase": "buy", "regarding": "about",
    "relating to": "about", "remainder": "the rest", "require": "need", "requirement": "need", "reside": "live",
    "retain": "keep", "subsequent": "later", "subsequently": "later", "sufficient": "enough", "thus": "so",
    "transmit": "send", "utilise": "use", "utilize": "use", "utilisation": "use", "whilst": "while", "whereas": "but",
    "with regard to": "about", "with respect to": "about", "in respect of": "for", "in excess of": "more than",
    "in the event of": "if", "in the event that": "if", "in accordance with": "under, in line with",
    "in conjunction with": "with", "in connection with": "about", "in relation to": "about", "in the absence of": "without",
    "in the course of": "while", "in addition to": "and, as well as", "in the near future": "soon", "as a consequence of": "because of",
    "on behalf of": "for", "owing to": "because of", "pursuant to": "under", "subject to": "depending on",
    "irrespective of": "despite", "notwithstanding": "even if, despite", "a large number of": "many", "the majority of": "most",
    "at the present time": "now", "at this point in time": "now", "despite the fact that": "although",
    "for the purpose of": "to", "with a view to": "to", "in the majority of instances": "mostly", "the question as to whether": "whether",
    "to the extent that": "if", "is in accordance with": "follows", "enable": "let, allow", "enables": "lets, allows",
    "alternative": "other, choice", "appropriate": "right, suitable", "apparent": "clear", "approximate": "about",
    "assemble": "put together", "beneficial": "helpful", "combine": "mix, join", "component": "part", "concerning": "about",
    "construct": "build", "corresponding": "matching", "designate": "name, set", "detrimental": "harmful", "deploy": "install, start",
    "discrete": "separate", "eliminate": "remove", "employ": "use", "establish": "set up, show", "evaluate": "check",
    "exclusively": "only", "execute": "run", "frequently": "often", "immediately": "at once, now", "implement": "do, build",
    "incorporate": "include", "inform": "tell", "insufficient": "not enough", "manner": "way", "minimal": "small",
    "notify": "tell", "objective": "aim", "perform": "do, run", "preferred": "chosen (when it means chosen)", "previous": "earlier, last",
    "primarily": "mainly", "principal": "main", "reconfigure": "change", "reduction": "cut", "referred to as": "called",
    "remain": "stay", "representative": "typical", "restriction": "limit", "solely": "only", "specified": "chosen, given",
    "substantial": "large", "supplementary": "extra", "therefore": "so", "ultimately": "in the end", "undertake": "do",
    "virtually": "almost", "visualise": "picture", "in order to": "to", "in order for": "for", "in order that": "so that",
    "is able to": "can", "are able to": "can", "be able to": "can", "make sure that": "make sure",
}
REPLACE_RE = re.compile(r"(?<![\w-])(" + "|".join(sorted((re.escape(k) for k in REPLACE), key=len, reverse=True)) + r")(?![\w-])", re.I)
LIGHT_VERBS = (r"(?:make|makes|made|making|take|takes|took|taking|give|gives|gave|have|has|had|having|perform|performs|carry out|carries out|"
               r"conduct|conducts|undertake|provide|provides)")
NOMINAL_RE = re.compile(
    r"\b" + LIGHT_VERBS + r" (?:a|an|the|some|any) (?:\w+ )?(selection|choice|decision|change|comparison|check|test|request|attempt|start|use|"
    r"discussion|review|assessment|investigation|adjustment|connection|configuration|replacement|deletion|installation|backup|restoration|"
    r"update|amendment|enquiry|inquiry|reference)\b"
    r"|\b(?:the|an?) (creation|removal|installation|selection|deletion|configuration|activation|deactivation|addition|provision|completion|"
    r"execution|implementation|introduction|investigation|arrangement|replacement|restoration|verification|detection|application|"
    r"utilisation|initiation|termination|modification|generation|adoption|assignment|allocation) of\b"
    r"|\bis (?:an?|the) (indication|reminder|example|reflection|representation) of\b"
    r"|\b(?:in|upon|on) (?:the )?(completion|receipt|selection|activation|installation|execution|deletion) of\b", re.I)
JARGON = ["daemon", "idempotent", "payload", "orchestrat\\w+", "namespace", "bind mount", "reverse proxy", "CIDR", "OAuth", "SSO", "TLS",
          "ingress", "egress", "heuristic", "latency", "throughput", "persistent volume", "sidecar", "webhook", "mutex", "regex",
          "serialis\\w+", "deserialis\\w+", "provision\\w*", "abstraction", "instantiate\\w*", "enumerat\\w+", "canonical", "atomic"]
JARGON_RE = re.compile(r"(?<![\w-])(" + "|".join(JARGON) + r")(?![\w-])", re.I)
CLAUSE_RE = re.compile(r"\b(and|but|which|that|because|so|while|although|though|when|if|unless|until|whereas|then)\b|[;:]", re.I)

ABBREV = re.compile(r"\b(e\.g|i\.e|etc|vs|approx|no|fig|inc|ltd|dr|mr|mrs|st)\.", re.I)
GENERIC_HEADS = {"overview", "introduction", "about this page", "about this topic", "about", "summary", "what this is", "background"}


# ---------------------------------------------------------------- text units

class Unit:
    """One run of text a person reads: a paragraph, a list item, a heading or a single interface string."""
    __slots__ = ("text", "line", "kind")

    def __init__(self, text, line, kind):
        self.text, self.line, self.kind = text, line, kind


def clean_md(s):
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", "", s)           # a picture's alt text is checked by ALT-TEXT.md, not here
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"`[^`]*`", "code", s)
    s = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def md_units(text):
    """Units from Markdown. Code blocks, tables, comments, front lines, the trail line and link targets are left out."""
    # The download rights footer is shared legal wording, written once in tools/help_footer.py: left out of the counts.
    text = re.sub(r"<!-- footer:.*?<!-- /footer -->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    units, para, para_line, in_code = [], [], 0, False

    def flush():
        nonlocal para, para_line
        if para:
            t = clean_md(" ".join(para))
            if t:
                units.append(Unit(t, para_line, "para"))
        para, para_line = [], 0

    for n, raw in enumerate(text.split("\n"), 1):
        line = raw.rstrip()
        if re.match(r"\s*(```|~~~)", line):
            flush(); in_code = not in_code; continue
        if in_code:
            continue
        if not line.strip():
            flush(); continue
        if line.lstrip().startswith("|") or re.match(r"\s*[-=]{3,}\s*$", line) or line.startswith("[Help centre]") or line.startswith("<"):
            flush(); continue
        m = re.match(r"(#{1,6})\s+(.*)", line)
        if m:
            flush(); units.append(Unit(clean_md(m.group(2)), n, "h" + str(len(m.group(1))))); continue
        m = re.match(r"\s*(?:[-*+]|\d+[.)])\s+(.*)", line)
        if m:
            flush(); para, para_line = [m.group(1)], n
            units.append(Unit("", n, "mark")); units.pop()  # (list items are one unit each, ended by the next marker or blank line)
            # an item continues on indented lines: collect them as part of this paragraph
            units.append(Unit("", n, "item-open"))
            continue
        if line.lstrip().startswith(">"):
            line = re.sub(r"^\s*>\s?(\[![A-Z]+\])?", "", line)
        if not para:
            para_line = n
        para.append(line.strip())
        # close a list item when the next line is a marker (handled above by flush) or blank (handled above)
    flush()
    # Mark list items: units that follow an "item-open" sentinel
    out, item = [], False
    for u in units:
        if u.kind == "item-open":
            item = True; continue
        if item and u.kind == "para":
            u.kind = "item"
        item = False
        out.append(u)
    return out


class _Html(HTMLParser):
    SKIP = {"script", "style", "pre", "code", "svg", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.units, self.skip, self.buf = [], 0, []
        self.title = ""
        self._title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag == "title":
            self._title = True
        d = dict(attrs)
        for a in ("title", "aria-label", "placeholder"):
            v = d.get(a)
            if v and len(v.split()) >= 3 and not v.startswith(("{", "$")):
                self.units.append(Unit(v.strip(), self.getpos()[0], "ui"))

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "title":
            self._title = False

    def handle_data(self, data):
        if self._title:
            self.title += data
        if self.skip:
            return
        t = re.sub(r"\s+", " ", data).strip()
        if len(t.split()) >= 3 and not t.startswith(("{{", "{%")):
            self.units.append(Unit(t, self.getpos()[0], "ui"))


def html_units(text):
    p = _Html()
    try:
        p.feed(text)
    except Exception:
        pass
    return p.units


STR_JS = re.compile(r"""(?P<q>["'`])(?P<s>(?:\\.|(?!(?P=q))[^\\\n])*)(?P=q)""")


def looks_like_text(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
    words = s.split()
    if len(words) < 4 or not re.match(r"[A-Z][a-z]", s):
        return None
    if re.search(r"[{};=]|=>|\(\)|\$\{|\bfunction\b|https?://|\.(js|css|html|png|svg)\b|\\n", s) and not s.endswith("."):
        return None
    alpha = sum(1 for w in words if re.fullmatch(r"[A-Za-z’'.,:;!?()\-]+", w))
    if alpha / len(words) < 0.7:
        return None
    return re.sub(r"\s+", " ", s)


def js_units(text):
    out = []
    for m in STR_JS.finditer(text):
        t = looks_like_text(m.group("s"))
        if t:
            out.append(Unit(t, text.count("\n", 0, m.start()) + 1, "ui"))
    return out


def py_units(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            b = node.body[0]
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
                doc_ids.add(id(b.value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_ids:
            t = looks_like_text(node.value)
            if t and not re.search(r"\b(SELECT|INSERT|CREATE TABLE|docker|systemctl)\b", t):
                out.append(Unit(t, node.lineno, "ui"))
    return out


TEXT_KEYS = {"description", "hint", "label", "help", "note", "notes", "summary", "text", "message", "title", "body", "intro",
             "empty", "placeholder", "summary", "does", "for", "needs", "shows", "pitch", "unclear", "tagline", "about", "why", "detail", "details", "caption"}


def json_units(text, minwords=3):
    try:
        data = json.loads(text)
    except Exception:
        return []
    out = []

    def walk(v, key=""):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)
        elif isinstance(v, str) and key in TEXT_KEYS and len(v.split()) >= minwords and not v.startswith(("http", "/")):
            out.append(Unit(clean_md(v), 0, "field"))
    walk(data)
    return out


# ---------------------------------------------------------------- analysis

def sentences(t):
    t = ABBREV.sub(lambda m: m.group(0).replace(".", "\u2024"), t)
    t = re.sub(r"(\d)\.(\d)", "\\1\u2024\\2", t)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", t)
    return [p.replace("\u2024", ".").strip() for p in parts if p.strip()]


def syllables(w):
    w = w.lower()
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def wc(s):
    return len(re.findall(r"[\w][\w’'./:-]*", s))


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


class Result:
    def __init__(self, rel, ptype, units):
        self.rel, self.type = rel, ptype
        self.words = 0
        self.sent = 0
        self.long_sent = []          # (words, line, text)
        self.long_para = []          # (sentences, line, text)
        self.filler = collections.Counter()
        self.passive = 0
        self.passive_ex = []
        self.dup = 0
        self.heading_restate = []
        self.over = 0
        self.title = ""
        self.sentence_norms = []
        self.replace = collections.Counter()
        self.nominal = 0
        self.nominal_ex = []
        self.stacked = []
        self.jargon = collections.Counter()
        self.syll = 0
        self.semis = 0
        self.analyse(units)

    def analyse(self, units):
        heads = [u for u in units if u.kind.startswith("h")]
        h1 = next((u.text for u in heads if u.kind == "h1"), "")
        self.title = h1
        tset = set(norm(h1).split())
        for u in units:
            if u.kind.startswith("h"):
                self.words += wc(u.text)
                if u.kind in ("h2", "h3"):
                    n = norm(u.text)
                    ws = set(n.split())
                    if n in GENERIC_HEADS or (h1 and ws and len(tset) >= 2 and len(ws & tset) / len(ws) >= 0.8 and len(ws) >= 2):
                        self.heading_restate.append((u.line, u.text))
                continue
            ss = sentences(u.text)
            self.words += wc(u.text)
            for s in ss:
                n = wc(s)
                self.sent += 1
                if n > MAX_SENTENCE:
                    self.long_sent.append((n, u.line, s))
                for m in FILLER_RE.finditer(s):
                    self.filler[m.group(0).lower().strip()] += 1
                if PASSIVE_RE.search(s) and not PASSIVE_SKIP.search(s):
                    self.passive += 1
                    if len(self.passive_ex) < 3:
                        self.passive_ex.append((u.line, s))
                if n >= 7:
                    self.sentence_norms.append(norm(s))
                for m in REPLACE_RE.finditer(s):
                    self.replace[m.group(0).lower()] += 1
                for m in NOMINAL_RE.finditer(s):
                    self.nominal += 1
                    if len(self.nominal_ex) < 3:
                        self.nominal_ex.append((u.line, m.group(0)))
                clauses = len(CLAUSE_RE.findall(s)) + s.count(",")
                if n >= 15 and clauses >= 5:
                    self.stacked.append((n, u.line, s))
                self.semis += s.count(";")
                for m in JARGON_RE.finditer(s):
                    self.jargon[m.group(0).lower()] += 1
                self.syll += sum(syllables(w) for w in re.findall(r"[A-Za-z]+", s))
            if len(ss) > MAX_PARAGRAPH_SENTENCES and u.kind in ("para", "item"):
                self.long_para.append((len(ss), u.line, u.text))
        seen = collections.Counter(self.sentence_norms)
        self.dup = sum(c - 1 for c in seen.values() if c > 1)
        tgt = TARGETS.get(self.type)
        if tgt and self.words > tgt:
            self.over = self.words - tgt

    @property
    def filler_n(self):
        return sum(self.filler.values())

    @property
    def replace_n(self):
        return sum(self.replace.values())

    @property
    def fre(self):
        return flesch(self.words, self.sent, self.syll)[0]

    @property
    def grade(self):
        return flesch(self.words, self.sent, self.syll)[1]

    @property
    def points(self):
        tgt = TARGETS.get(self.type, 0)
        over = (self.over / max(tgt, 20) * 5) if tgt else 0
        return round(2 * len(self.long_sent) + 2 * len(self.long_para) + self.filler_n + 0.5 * self.passive
                     + self.dup + 2 * len(self.heading_restate) + 0.5 * self.replace_n + self.nominal + len(self.stacked)
                     + 0.5 * self.semis + over, 1)

    def row(self):
        return dict(file=self.rel, type=self.type, words=self.words, sentences=self.sent, long_sentences=len(self.long_sent),
                    long_paragraphs=len(self.long_para), filler=self.filler_n, passive=self.passive, replace=self.replace_n,
                    nominal=self.nominal, stacked=len(self.stacked), semicolons=self.semis, fre=self.fre, grade=self.grade,
                    top_replace=self.replace.most_common(3), jargon=sum(self.jargon.values()), repeats=self.dup,
                    heading_restates=len(self.heading_restate), over_target=self.over, points=self.points,
                    top_filler=self.filler.most_common(3), longest=max([x[0] for x in self.long_sent], default=0))


# ---------------------------------------------------------------- classification

def help_kind(text):
    m = re.match(r"\[Help centre\][^\n]*·\s*([a-z -]+)\s*$", text.split("\n", 1)[0].strip())
    return m.group(1).strip().replace(" ", "-") if m else ""


def classify(rel, text=""):
    """The page type for a path, or None to leave the file out."""
    p = rel
    parts = p.split("/")
    ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
    name = parts[-1]
    if any(x in parts for x in ("node_modules", ".git", "images", "screenshots", "dist", "vendor", "fonts", "licences", "__pycache__")):
        return None
    if name in ("llms.txt", "llms-full.txt", "THIRD-PARTY.md", "LICENSE", "LICENSE-DOCS.md", "package-lock.json"):
        return None
    if re.search(r"(^|/)(tests?|test-plans)/", p) or name.endswith((".min.js", ".min.css")) or re.search(r"\.(bak|log)$", name):
        return None
    if ext == "md":
        if name == "CHANGELOG.md":
            return "changelog"
        if len(parts) >= 3 and parts[:2] == ["docs", "releases"]:
            return "release-notes"
        if parts[0] == "docs" and len(parts) >= 3 and parts[1] == "help" and parts[2] in ("topics", "guides", "basics", "developers", "comparisons", "accessibility"):
            tier = parts[2]
            if tier == "topics":
                k = help_kind(text)
                return "help-topic-" + k if ("help-topic-" + k) in TARGETS else "help-topic"
            return {"guides": "help-guide", "basics": "help-basics", "developers": "help-developers",
                    "comparisons": "help-comparison", "accessibility": "help-accessibility"}[tier]
        if parts[:3] == ["docs", "help", "plugins"]:
            return None  # a mirror of starboard-plugins/help/plugins, counted once, in that repository
        if "help" in parts and "plugins" in parts:
            return "plugin-help"
        if parts[0] == "help":
            k = help_kind(text)
            if parts[1] == "plugins":
                return "plugin-help"
            return {"start": "help-guide", "use": "help-topic", "fix": "help-topic-troubleshooting", "developers": "help-developers",
                    "accessibility": "help-accessibility"}.get(parts[1], "help-topic") if len(parts) > 2 else "docs"
        if name.lower().startswith("readme") and len(parts) <= 2:
            return "readme"
        if re.match(r"(SECURITY|CONTRIBUTING|CODE_OF_CONDUCT|REVIEWING)\.md", name):
            return "docs"
        return "docs"
    if ext == "html":
        return "ui-html"
    if ext == "js" and "web/js" in p or name == "snaglist.js":
        return "ui-js"
    if ext == "py" and (parts[0] == "starboard" or re.match(r"[^/]+/(app|install|sbplugin|run)\.py$", p) or parts[0] in ("ondemand", "_shared")):
        return "ui-py"
    if name == "starboard-plugin.json" or name in ("catalogue.json", "help-centre.json", "plugin-manifest.schema.json") or (ext == "json" and ("listings" in parts or parts[:2] == ["data", "storefront"])):
        return "manifest"
    return None


def units_for(ptype, rel, text):
    if ptype == "manifest":
        return json_units(text)
    ext = rel.rsplit(".", 1)[-1].lower()
    if ext == "md":
        return md_units(text)
    if ext == "html":
        return html_units(text)
    if ext == "js":
        return js_units(text)
    if ext == "py":
        return py_units(text)
    return []


def changelog_sections(text):
    """The Unreleased section and the newest released one count as current; older sections are history (left alone)."""
    heads = [m.start() for m in re.finditer(r"^## ", text, flags=re.M)]
    cut = heads[2] if len(heads) > 2 else len(text)
    return text[:cut], text[cut:]


def load_allowed(root):
    f = root / "tools" / "verbose-allowed.txt"
    out = []
    if f.exists():
        for ln in f.read_text().splitlines():
            if ln and not ln.startswith("#"):
                a = ln.split("\t")
                if len(a) >= 2:
                    out.append((a[0], re.compile(a[1])))
    return out


def only_lines(units, lines):
    """Keeps the units that start on, or run into, one of the added lines (a unit runs up to the next unit)."""
    keep = []
    for i, u in enumerate(units):
        if not u.line:
            keep.append(u)
            continue
        nxt = next((v.line for v in units[i + 1:] if v.line and v.line > u.line), None)
        end = (nxt - 1) if nxt else u.line + u.text.count("\n")
        if any(u.line <= n <= max(end, u.line) for n in lines):
            keep.append(u)
    return keep


def scan_file(root, path, allowed=(), lines=None):
    rel = str(path.relative_to(root))
    try:
        text = path.read_text(errors="replace")
    except Exception:
        return None
    ptype = classify(rel, text)
    if not ptype:
        return None
    if ptype == "changelog":
        text, _ = changelog_sections(text)
    units = units_for(ptype, rel, text)
    if allowed:
        units = [u for u in units if not any(f == rel and r.search(u.text) for f, r in allowed)]
    if lines is not None:
        units = only_lines(units, lines)
    r = Result(rel, ptype, units)
    if lines is not None:
        r.over = 0  # a word target is for a whole page, so a change that adds lines is never held to it
    return r


def tracked_files(root):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
        return [root / f for f in out if f]
    except Exception:
        return [p for p in root.rglob("*") if p.is_file()]


def audit_repo(name, root):
    root = pathlib.Path(root)
    allowed = load_allowed(root)
    results = []
    for p in tracked_files(root):
        if p.is_file() and p.stat().st_size < 3_000_000:
            r = scan_file(root, p, allowed)
            if r and r.words:
                results.append(r)
    # repeated sentences across files of one repository
    where = collections.defaultdict(set)
    for r in results:
        for n in set(r.sentence_norms):
            where[n].add(r.rel)
    cross = collections.Counter()
    for n, files in where.items():
        if len(files) > 1:
            for f in files:
                cross[f] += 1
    for r in results:
        r.cross = cross.get(r.rel, 0)
        r.dup += r.cross
    return results


# ---------------------------------------------------------------- reports

def summarise(results):
    by = collections.defaultdict(list)
    for r in results:
        by[r.type].append(r)
    rows = []
    for t, rs in sorted(by.items()):
        w = sum(r.words for r in rs)
        rows.append(dict(type=t, files=len(rs), words=w, sentences=sum(r.sent for r in rs),
                         long_sentences=sum(len(r.long_sent) for r in rs), long_paragraphs=sum(len(r.long_para) for r in rs),
                         filler=sum(r.filler_n for r in rs), passive=sum(r.passive for r in rs), repeats=sum(r.dup for r in rs),
                         heading_restates=sum(len(r.heading_restate) for r in rs), over_target=sum(1 for r in rs if r.over),
                         over_words=sum(r.over for r in rs), points=round(sum(r.points for r in rs)),
                         replace=sum(r.replace_n for r in rs), nominal=sum(r.nominal for r in rs), stacked=sum(len(r.stacked) for r in rs),
                         semicolons=sum(r.semis for r in rs), avg_sentence=round(w / max(1, sum(r.sent for r in rs)), 1),
                         fre=flesch(w, sum(r.sent for r in rs), sum(r.syll for r in rs))[0],
                         grade=flesch(w, sum(r.sent for r in rs), sum(r.syll for r in rs))[1]))
    return rows


def flesch(words, sents, syll):
    """Flesch reading ease and Flesch-Kincaid grade, a guide only: product names and file names push both the wrong way."""
    if not words or not sents:
        return 0.0, 0.0
    wps, spw = words / sents, syll / words
    return round(206.835 - 1.015 * wps - 84.6 * spw, 1), round(0.39 * wps + 11.8 * spw - 15.59, 1)


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(len(vals) * p))] if vals else 0


def print_files(results):
    for r in results:
        print(f"{r.rel}  [{r.type}]  words {r.words}, sentences {r.sent}, long {len(r.long_sent)}, long paragraphs {len(r.long_para)}, "
              f"filler {r.filler_n}, passive {r.passive}, repeats {r.dup}, heading restates {len(r.heading_restate)}, "
              f"plain-word swaps {r.replace_n}, hidden verbs {r.nominal}, stacked {len(r.stacked)}, over target {r.over}, "
              f"avg sentence {r.words / max(1, r.sent):.1f}, reading ease {r.fre}, grade {r.grade}, points {r.points}")


def cmd_audit(args):
    jsn = None
    if "--json" in args:
        i = args.index("--json"); jsn = args[i + 1]; del args[i:i + 2]
    allres = {}
    for a in args:
        name, path = a.split("=", 1)
        allres[name] = audit_repo(name, path)
    if jsn:
        data = {}
        for name, rs in allres.items():
            data[name] = dict(summary=summarise(rs), files=[r.row() for r in rs],
                              examples={r.rel: dict(long=[(n, l, s) for n, l, s in sorted(r.long_sent, reverse=True)[:3]],
                                                    para=[(n, l, t[:400]) for n, l, t in r.long_para[:2]],
                                                    passive=r.passive_ex, restates=r.heading_restate[:3]) for r in rs if r.points >= 6})
        pathlib.Path(jsn).write_text(json.dumps(data, indent=1))
    for name, rs in allres.items():
        print(f"== {name}: {len(rs)} files, {sum(r.words for r in rs)} words")
        for row in summarise(rs):
            print("  ", row)


def cmd_files(args):
    allr = []
    for a in args:
        p = pathlib.Path(a).resolve()
        root = next((q for q in [p] + list(p.parents) if (q / ".git").exists()), p.parent)
        r = scan_file(root, p, load_allowed(root))
        if r:
            allr.append(r)
    print_files(allr)
    for r in allr:
        for n, l, s in r.long_sent:
            print(f"  long ({n} words) {r.rel}:{l}: {s[:160]}")
        for n, l, t in r.long_para:
            print(f"  long paragraph ({n} sentences) {r.rel}:{l}: {t[:100]}")
        for l, h in r.heading_restate:
            print(f"  heading restates the title {r.rel}:{l}: {h}")
        if r.filler:
            print(f"  filler {r.rel}: {dict(r.filler)}")
        if r.replace:
            print(f"  plainer words {r.rel}: " + ", ".join(f"{k} -> {REPLACE[k]}" for k in list(r.replace)[:8] if k in REPLACE))
        for l, t in r.passive_ex:
            print(f"  passive {r.rel}:{l}: {t[:140]}")
        for l, t in r.nominal_ex:
            print(f"  hidden verb {r.rel}:{l}: {t}")
        for n, l, t in r.stacked[:3]:
            print(f"  stacked clauses ({n} words) {r.rel}:{l}: {t[:140]}")


def added_lines(root, base, f):
    """The line numbers a change adds to file f, from git diff -U0 (None when the whole file is new)."""
    out = subprocess.run(["git", "-C", str(root), "diff", "-U0", "--diff-filter=AM", base + "...HEAD", "--", f],
                         capture_output=True, text=True).stdout
    if "\nnew file mode" in "\n" + out:
        return None
    lines = set()
    for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", out, flags=re.M):
        start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        lines.update(range(start, start + count))
    return lines


def cmd_ci(args):
    """Warns about the lines a pull request adds (not the whole file). Prints GitHub annotations. Exits 0 always,
    unless --fail is given: then 1 for a sentence over 25 words or a paragraph over 4 sentences on an added line.
    --fail is not switched on in any workflow: it waits until a repository has fewer than 100 long sentences
    (python3 verbose-check.py audit NAME=PATH shows the number)."""
    base, root = "origin/main", pathlib.Path(".")
    if "--base" in args:
        base = args[args.index("--base") + 1]
    if "--root" in args:
        root = pathlib.Path(args[args.index("--root") + 1])
    root = root.resolve()
    out = subprocess.run(["git", "-C", str(root), "diff", "--name-only", "--diff-filter=AM", base + "...HEAD"], capture_output=True, text=True).stdout.split("\n")
    allowed = load_allowed(root)
    worst = 0
    for f in out:
        p = root / f
        if f and p.is_file():
            r = scan_file(root, p, allowed, added_lines(root, base, f))
            if not r:
                continue
            for n, l, s in r.long_sent:
                print(f"::warning file={r.rel},line={l or 1},title=Sentence over {MAX_SENTENCE} words::{n} words: {s[:120]}")
            for n, l, t in r.long_para:
                print(f"::warning file={r.rel},line={l or 1},title=Paragraph over {MAX_PARAGRAPH_SENTENCES} sentences::{n} sentences")
            for l, h in r.heading_restate:
                print(f"::warning file={r.rel},line={l or 1},title=Heading restates the title::{h}")
            if r.passive >= 2:
                print(f"::warning file={r.rel},line={r.passive_ex[0][0] or 1},title=Passive voice::{r.passive} added sentences hint at passive voice. Name who does the action.")
            if r.replace_n >= 2:
                print(f"::warning file={r.rel},title=Plainer words::" + ", ".join(f"{k} -> {REPLACE[k]}" for k in list(r.replace)[:6] if k in REPLACE))
            for l, h in r.nominal_ex[:3]:
                print(f"::warning file={r.rel},line={l or 1},title=Hidden verb::{h}")
            if r.filler_n >= 3:
                print(f"::warning file={r.rel},title=Filler phrases::{dict(r.filler)}")
            worst = max(worst, 1 if (r.long_sent or r.long_para) else 0)
    if "--fail" in args:
        sys.exit(worst)


def cmd_stats(args):
    for a in args:
        name, path = a.split("=", 1)
        rs = audit_repo(name, path)
        by = collections.defaultdict(list)
        for r in rs:
            by[r.type].append(r.words)
        print(f"== {name}")
        for t, v in sorted(by.items()):
            print(f"  {t:28} n={len(v):4} p50={pct(v, .5):5} p75={pct(v, .75):5} p90={pct(v, .9):5} max={max(v):5}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("audit", "files", "ci", "stats"):
        print(__doc__); sys.exit(2)
    {"audit": cmd_audit, "files": cmd_files, "ci": cmd_ci, "stats": cmd_stats}[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
