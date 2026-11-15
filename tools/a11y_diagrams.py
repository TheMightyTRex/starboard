#!/usr/bin/env python3
"""Draws the accessibility help diagrams (DASH-435) as plain SVG: docs/help/images/a11y-*.svg.

Each one has a title and a description for screen readers, its own background, and colours that follow the reader's
light or dark setting (a style block with prefers-color-scheme), so it reads well on either. Nothing is told by colour
alone: every box has words, and arrows have labels. The articles say the same things in text as well.
Run: python3 tools/a11y_diagrams.py"""
import html
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/help/images"
FONT = "Atkinson Hyperlegible Next, Atkinson Hyperlegible, Verdana, sans-serif"
STYLE = """<style>
.bg{fill:#ffffff}.ink{fill:#1d2238}.mut{fill:#4a5068}.box{fill:#eef2fb;stroke:#7d86a8;stroke-width:2}
.hi{fill:#ffffff;stroke:#0b5f5a;stroke-width:3}.acc{fill:#0b5f5a}.line{stroke:#4a5068;stroke-width:2.5;fill:none}
.head{fill:#dfe6f5;stroke:#7d86a8;stroke-width:2}.warn{fill:#fff4dc;stroke:#8a5a00;stroke-width:2}
.out{fill:#f4f4f6;stroke:#7d86a8;stroke-width:2;stroke-dasharray:7 5}.tick{fill:#0b5f5a}
@media (prefers-color-scheme: dark){
.bg{fill:#101827}.ink{fill:#f3f4f6}.mut{fill:#b8c1d3}.box{fill:#1b2537;stroke:#8390a8}
.hi{fill:#101827;stroke:#5ed3c6}.acc{fill:#5ed3c6}.line{stroke:#b8c1d3}.head{fill:#232f42;stroke:#8390a8}
.warn{fill:#3a2c09;stroke:#f6cf6b}.out{fill:#161e2c;stroke:#8390a8}.tick{fill:#5ed3c6}}
</style>"""
ARROW = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
         '<path d="M0,0 L10,5 L0,10 z" class="ink"/></marker></defs>')


def esc(s):
    return html.escape(s, quote=False)


def svg(w, h, body, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-labelledby="t d"><title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>{STYLE}{ARROW}'
            f'<rect class="bg" width="{w}" height="{h}"/><g font-family="{FONT}">{body}</g></svg>\n')


def text(x, y, s, size=15, weight=400, cls="ink", anchor="start", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" class="{cls}" text-anchor="{anchor}"{extra}>{esc(s)}</text>'


def wrap(s, chars):
    """Splits words into lines of at most `chars` characters (a safe width for the fallback fonts)."""
    lines, now = [], ""
    for word in s.split():
        if now and len(now) + 1 + len(word) > chars:
            lines.append(now)
            now = word
        else:
            now = f"{now} {word}".strip()
    if now:
        lines.append(now)
    return lines


def para(x, y, s, chars, size=15, gap=21, cls="ink", weight=400):
    return "".join(text(x, y + n * gap, line, size, weight, cls) for n, line in enumerate(wrap(s, chars)))


def rect(x, y, w, h, cls="box", rx=8):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>'


def line(x1, y1, x2, y2, arrow=True):
    return f'<path d="M{x1},{y1} L{x2},{y2}" class="line"{" marker-end=\"url(#a)\"" if arrow else ""}/>'


# 1. Where Display is, and what each setting changes ------------------------------------------------------------
SETTINGS = [
    ("Theme", "Match device, Light, Dark", "The colours: dark text on light, or light text on dark. Match device follows your phone or computer."),
    ("Text size", "100%, 125%, 150%, 175%", "All of Starboard's text, with the layout reflowing to fit. Controls grow with it."),
    ("Reduce motion", "Match device, On, Off", "Slide-outs and menus appear without sliding, the loading line fades, long lists wait for Show more."),
    ("High contrast", "Activated or deactivated", "Near-black or white text, solid borders and no shadows, and a bolder focus colour."),
    ("Underline links", "Activated or deactivated", "Every link is underlined, so it is not shown by colour alone."),
    ("Wider text spacing", "Activated or deactivated", "More space between lines (1.8), letters (0.12 em) and words (0.16 em)."),
    ("Style", "Only with a style plug-in", "Colours and corners from a plug-in, checked for contrast. Your choices above always win."),
    ("Design", "Five designs, or the default", "How the Apps page is laid out in this browser."),
    ("Done and Reset", "Buttons at the end", "Done closes the panel. Reset puts every choice back to the defaults."),
]


def display_map():
    w, h = 1100, 760
    b = [rect(20, 20, 1060, 58, "head", 10), text(44, 56, "Starboard", 18, 700),
         rect(210, 34, 420, 30, "box", 6), text(226, 55, "Search films, series, music and books", 14, 400, "mut"),
         text(860, 56, "Help", 15, 700), rect(950, 30, 112, 38, "hi", 8), text(1006, 55, "Display", 16, 700, anchor="middle"),
         text(40, 104, "The header of every page", 14, 400, "mut")]
    b.append(line(1006, 68, 1006, 116))
    b.append(text(990, 100, "Select Display", 14, 700, anchor="end"))
    top = 122
    b.append(rect(20, top, 1060, 600, "box", 10))
    b.append(rect(20, top, 1060, 46, "head", 10))
    b.append(text(40, top + 30, "Display and accessibility", 18, 700))
    b.append(text(1050, top + 30, "Close", 14, 700, anchor="end"))
    b.append(text(40, top + 72, "Setting", 14, 700, "mut") + text(250, top + 72, "Choices", 14, 700, "mut")
             + text(500, top + 72, "What it changes", 14, 700, "mut"))
    y = top + 100
    for name, choices, what in SETTINGS:
        b.append(f'<path d="M36,{y - 20} L1064,{y - 20}" class="line" stroke-width="1" opacity="0.35"/>')
        b.append(text(40, y + 4, name, 15, 700))
        b.append(para(250, y + 4, choices, 26, 14, 19, "mut"))
        b.append(para(500, y + 4, what, 64, 14, 19))
        y += 54
    b.append(text(40, h - 18, "Every choice applies at once and is kept in this browser only, for this phone or computer.", 15, 700))
    desc = ("The Display button is the last item in the header of every Starboard page. Selecting it opens the Display and "
            "accessibility panel. " + " ".join(f"{n}: {c}. {wt}" for n, c, wt in SETTINGS)
            + " Every choice applies at once and is kept in this browser only.")
    return svg(w, h, "".join(b), "Where Display is, and what each setting changes", desc)


# 2. How focus moves through a slide-out or dialog ---------------------------------------------------------------
FOCUS_STEPS = [
    ("1. You select a button", "Such as Display, Edit or Remove. Starboard remembers it as the opener."),
    ("2. Focus moves inside", "To the first field, to Close, or to Cancel when the choice would delete something."),
    ("3. Tab stays inside", "Tab and Shift and Tab move only between its controls. After the last, focus goes back to the first."),
    ("4. You close it", "With Escape, Close, Done or Cancel, or by finishing what it asks."),
    ("5. Focus goes back", "To the opener. If that has gone, to the same control drawn again, its row, the section's heading or the page's heading."),
]


def focus_flow():
    w, h = 1100, 440
    b = [text(20, 34, "How focus moves through a slide-out or a dialog", 19, 700)]
    bw, gap, y0, bh = 196, 20, 64, 250
    for n, (head, body) in enumerate(FOCUS_STEPS):
        x = 20 + n * (bw + gap)
        b.append(rect(x, y0, bw, bh, "hi" if n in (1, 2) else "box", 10))
        b.append(para(x + 14, y0 + 32, head, 19, 16, 21, "ink", 700))
        b.append(para(x + 14, y0 + 84, body, 21, 14, 20))
        if n < len(FOCUS_STEPS) - 1:
            b.append(line(x + bw + 2, y0 + bh / 2, x + bw + gap - 2, y0 + bh / 2))
    # The loop under step 3: Tab goes round inside.
    x3 = 20 + 2 * (bw + gap)
    b.append(f'<path d="M{x3 + bw - 30},{y0 + bh} C{x3 + bw - 30},{y0 + bh + 50} {x3 + 30},{y0 + bh + 50} {x3 + 30},{y0 + bh + 6}" '
             f'class="line" marker-end="url(#a)"/>')
    b.append(text(x3 + bw / 2, y0 + bh + 66, "Tab goes round inside", 14, 700, anchor="middle"))
    b.append(text(20, h - 14, "The page behind cannot be reached while it is open. Outlined boxes: focus is inside the slide-out or dialog.", 14, 400, "mut"))
    desc = ("Five steps. " + " ".join(f"{hd}: {bd}" for hd, bd in FOCUS_STEPS)
            + " The page behind cannot be reached while the slide-out or dialog is open.")
    return svg(w, h, "".join(b), "How focus moves through a slide-out or a dialog", desc)


# 3. Text size and wider spacing ----------------------------------------------------------------------------------
def text_and_spacing():
    w, h = 1100, 430
    b = [text(20, 34, "Text size: the same words at each setting", 19, 700)]
    y = 80
    for pct, px in (("100%", 16), ("125%", 20), ("150%", 24), ("175%", 28)):
        b.append(text(20, y, pct, 15, 700, "mut"))
        b.append(text(110, y, "Harbour Lights, film, 2023, in your library", px))
        y += px + 26
    b.append(f'<path d="M20,{y - 6} L1080,{y - 6}" class="line" stroke-width="1" opacity="0.4"/>')
    y += 30
    b.append(text(20, y, "Wider text spacing", 19, 700))
    y += 40
    b.append(text(20, y, "Deactivated", 15, 700, "mut"))
    b.append(text(170, y, "Starboard checks your apps every minute", 16))
    b.append(text(170, y + 24, "and tells you when one stops answering.", 16))
    b.append(text(600, y, "Activated", 15, 700, "mut"))
    b.append(text(720, y, "Starboard checks your apps", 16, extra=' letter-spacing="1.9" word-spacing="2.6"'))
    b.append(text(720, y + 29, "every minute and tells you", 16, extra=' letter-spacing="1.9" word-spacing="2.6"'))
    b.append(text(720, y + 58, "when one stops answering.", 16, extra=' letter-spacing="1.9" word-spacing="2.6"'))
    desc = ("Text size: the same line, Harbour Lights, film, 2023, in your library, shown at 100%, 125%, 150% and 175%, "
            "each larger than the last. Wider text spacing: a sentence with normal spacing beside the same sentence with "
            "more space between lines, letters and words, so it takes three lines instead of two.")
    return svg(w, h, "".join(b), "Text size and wider text spacing", desc)


# 4. How Starboard is tested --------------------------------------------------------------------------------------
def test_process(figures):
    w, h = 1100, 640
    b = [text(20, 34, "How Starboard is tested for accessibility", 19, 700)]

    def lane(y, height, title, note, cls="box"):
        return rect(20, y, 1060, height, cls, 12) + text(40, y + 30, title, 17, 700) + text(1060, y + 30, note, 14, 400, "mut", "end")

    b.append(lane(56, 250, "Every change, before it is merged", "tools/a11y.sh, run three ways"))
    cards = [
        ("Scan", f"axe-core {figures['axe_version']}, WCAG 2.2 AA, every page in Light, Dark and High contrast; structure, target size, reflow, forced colours, reduced motion", figures["scan"]),
        ("Reading order", "What a screen reader reads against what is seen, Tab order, landmarks and the h1 first, on every page", figures["order"]),
        ("Keyboard walk", "The main tasks with keys only: focus after each step, and what is said", figures["tasks"]),
        ("Colour contrast", "Every colour pair in the design system, in every theme and palette", figures["contrast"]),
    ]
    cw = 245
    for n, (head, body, result) in enumerate(cards):
        x = 40 + n * (cw + 12)
        b.append(rect(x, 100, cw, 190, "hi", 10))
        b.append(text(x + 14, 128, head, 16, 700))
        b.append(para(x + 14, 154, body, 28, 13, 18))
        b.append(text(x + 14, 274, result, 14, 700, "acc"))
    b.append(lane(326, 120, "Before every release", "as well as all of the above"))
    b.append(para(40, 384, "All the checks run again on the release, with the journeys (every page used as a person would) and "
                  "fresh screenshots that a person looks at.", 110, 15, 21))
    b.append(lane(466, 130, "Still needs a person", "not done yet", "warn"))
    b.append(para(40, 524, "Listening with a screen reader, such as Orca or NVDA, and testing with people who use assistive "
                  "technology. Tools find many problems, but not whether something makes sense when heard.", 110, 15, 21))
    b.append(text(20, h - 16, f"Results from the run on {figures['date']}.", 14, 400, "mut"))
    desc = ("Three bands. Every change, before it is merged: " + "; ".join(f"{hd}: {bd}. Latest result: {r}" for hd, bd, r in cards)
            + ". Before every release: all the checks run again with the journeys and fresh screenshots that a person looks at. "
            "Still needs a person, not done yet: listening with a screen reader such as Orca or NVDA, and testing with people "
            f"who use assistive technology. Results from the run on {figures['date']}.")
    return svg(w, h, "".join(b), "How Starboard is tested for accessibility", desc)


# 5. What Starboard controls --------------------------------------------------------------------------------------
COLUMNS = [
    ("Starboard's own pages", "hi", "Built and tested to WCAG 2.2 AA", [
        "Apps, Home, Library, Discover", "Activity, System, Settings", "Sign in and the set-up", "Display and accessibility"]),
    ("Made by others, drawn by Starboard", "box", "Checked, but written by someone else", [
        "Plug-in styles: contrast checked", "Plug-in cards and settings:", "labels checked, drawn by Starboard",
        "Words and pictures plug-ins send"]),
    ("Outside Starboard", "out", "Starboard cannot change or test these", [
        "Jellyfin, Audiobookshelf, players", "Reelix's own pages", "Other apps' own pages",
        "Your browser and screen reader"]),
]


def who_controls():
    w, h = 1100, 360
    b = [text(20, 34, "What Starboard controls, and what it does not", 19, 700)]
    cw = 340
    for n, (head, cls, sub, items) in enumerate(COLUMNS):
        x = 20 + n * (cw + 20)
        b.append(rect(x, 56, cw, 280, cls, 12))
        b.append(text(x + 18, 90, head, 17, 700))
        b.append(text(x + 18, 116, sub, 14, 400, "mut"))
        for k, item in enumerate(items):
            b.append(text(x + 18, 160 + k * 40, item, 15))
    desc = " ".join(f"{head}, {sub.lower()}: {', '.join(items)}." for head, _, sub, items in COLUMNS).replace(":,", ":")
    return svg(w, h, "".join(b), "What Starboard controls, and what it does not", desc)


# The latest results quoted in the help (topics/how-starboard-is-tested-for-accessibility.md), from the run named.
FIGURES = {
    "date": "14 November 2026",
    "axe_version": "4.14.0",
    "scan": "0 problems on 101 pages",
    "order": "0 problems",
    "tasks": "76 of 76 checks passed",
    "contrast": "560 pairs, 0 failures",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in (("a11y-display-map.svg", display_map()), ("a11y-focus-flow.svg", focus_flow()),
                       ("a11y-text-and-spacing.svg", text_and_spacing()), ("a11y-test-process.svg", test_process(FIGURES)),
                       ("a11y-who-controls.svg", who_controls())):
        (OUT / name).write_text(body)
        print(OUT / name)


if __name__ == "__main__":
    main()
