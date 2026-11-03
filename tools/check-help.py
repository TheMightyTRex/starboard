#!/usr/bin/env python3
"""Checks the help centre (docs/help): every link goes somewhere, every article is in the index and has the
right layout for its tier, and the writing rules in HOW-THIS-HELP-IS-WRITTEN.md hold. Exits 1 on a problem.

    python3 tools/check-help.py
"""

import pathlib
import re
import sys

HELP = pathlib.Path(__file__).resolve().parent.parent / "docs" / "help"
TIERS = {"topics": ["## Find out more"], "guides": ["## Before you begin", "## The steps at a glance", "## What next"],
         "basics": ["## Find out more"]}
RULES = [
    (r"—", "an em dash"),
    (r"\b(can't|won't|don't|doesn't|isn't|aren't|didn't|wasn't|haven't|hasn't|shouldn't|wouldn't|couldn't|you're|you'll|"
     r"you've|we're|they're|it's|that's|there's|let's|I'm)\b", "a contraction"),
    (r"\b(click|clicking|clicked|tap|tapping)\b", "click or tap (use select)"),
    (r"\b(enable|enables|enabled|disable|disables|disabled|toggle|toggles)\b", "enable, disable or toggle (use turn on or off)"),
    (r"(?<!home )(?<!no )(?<!a )\bscreen\b(?! reader)(?! or keyboard)", "screen (use page)"),
    (r"\b(top right|top left|bottom right|bottom left|on the left|on the right|scroll down|scroll up)\b", "a position"),
    (r"!(?!\[)", "an exclamation mark"),
    (r"\b(click here|read more)\b", "a vague link"),
]


def text_only(md):
    """The words a reader reads: no code blocks, inline code, link targets or Mermaid."""
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"`[^`]*`", "", md)
    md = re.sub(r"\]\([^)]*\)", "]", md)
    return md


def main():
    problems = []
    files = sorted(p for p in HELP.rglob("*.md"))
    index = (HELP / "README.md").read_text()
    for path in files:
        rel = path.relative_to(HELP)
        md = path.read_text()
        if path.name == "HOW-THIS-HELP-IS-WRITTEN.md":
            continue  # the rules themselves, quoting what not to write
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", re.sub(r"```.*?```", "", md, flags=re.S)):
            if re.match(r"^[a-z]+:", target):
                continue
            if not (path.parent / target).resolve().exists():
                problems.append(f"{rel}: the link to {target} goes nowhere")
        tier = rel.parts[0] if len(rel.parts) > 1 else None
        if tier in TIERS:
            if str(rel) not in index:
                problems.append(f"{rel}: not listed in the index (README.md)")
            if not md.startswith("[Help centre](../README.md)"):
                problems.append(f"{rel}: does not start with the Help centre line")
            if len(re.findall(r"^# ", md, flags=re.M)) != 1:
                problems.append(f"{rel}: needs exactly one title")
            for heading in TIERS[tier]:
                if heading not in md:
                    problems.append(f"{rel}: has no '{heading[3:]}' section")
            if tier == "guides" and "```mermaid" not in md:
                problems.append(f"{rel}: a guide needs its steps as a Mermaid flowchart")
        words = text_only(md)
        for n, line in enumerate(words.splitlines(), 1):
            for pattern, what in RULES:
                if re.search(pattern, line, flags=re.I if "I'm" not in pattern else 0):
                    if what.startswith("enable") and re.search(r"\*\*Enable SSH\*\*", line):
                        continue  # Raspberry Pi Imager's own label, copied exactly
                    problems.append(f"{rel}: {what}: {line.strip()[:90]}")
    for target in re.findall(r"\]\(([^)#\s]+)\)", index):
        if not (HELP / target).exists():
            problems.append(f"README.md: the index lists {target}, which does not exist yet")
    for p in problems:
        print(p)
    print(f"{len(files)} articles checked, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
