#!/usr/bin/env python3
"""Checks the help centre (docs/help): every link goes somewhere, every article is in the index and has the
right layout for its tier, and the writing rules of the design system's HELP-WRITING.md and CONTENT-DESIGN.md hold. Exits 1 on a problem.

    python3 tools/check-help.py
"""

import pathlib
import re
import sys

HELP = pathlib.Path(__file__).resolve().parent.parent / "docs" / "help"
SCREENSHOTS_PER_TOPIC = 3
TIERS = {"topics": ["## Find out more"], "guides": ["## Before you begin", "## The steps at a glance", "## What next"],
         "basics": ["## Find out more"], "developers": ["## Find out more"], "comparisons": ["## Find out more"],
         "accessibility": ["## Find out more"]}  # the Accessibility menu (DASH-435): tier one articles in their own folder
RULES = [
    (r"—", "an em dash"),
    (r"\b(can't|won't|don't|doesn't|isn't|aren't|didn't|wasn't|haven't|hasn't|shouldn't|wouldn't|couldn't|you're|you'll|"
     r"you've|we're|they're|it's|that's|there's|let's|I'm)\b", "a contraction"),
    (r"\b(click|clicking|clicked|tap|tapping)\b", "click or tap (use select)"),
    (r"\b(enable|enables|enabled|disable|disables|disabled|toggle|toggles)\b", "enable, disable or toggle (use activate or deactivate)"),
    (r"\b(turn|turns|turned|turning|switch|switches|switched) (it |them |this |that )?(on|off)\b|\bon or off\b", "turn on or off (use activate or deactivate)"),
    (r"(?<!home )(?<!no )(?<!a )(?<!on-)\bscreen\b(?! reader)(?! or keyboard)", "screen (use page)"),
    (r"\b(top right|top left|bottom right|bottom left|on the left|on the right|scroll down|scroll up)\b", "a position"),
    (r"(?<!\[)!(?!\[)", "an exclamation mark"),  # not GitHub's callouts, "> [!TIP]"
    (r"\b(click here|read more)\b", "a vague link"),
    # Starboard runs Reelix (DASH-161): help never sends people to Reelix's own settings. The TMDB key (Settings,
    # Metadata) is the one exception until the set-ups ask for it (DASH-178).
    (r"(?-i:\bDownload Clients\b)|\bReelix,? (\*\*)?Settings(\*\*)?,? (?!(\*\*)?Metadata)", "Reelix's own settings (use Settings, Reelix in Starboard)"),
]


def text_only(md):
    """The words a reader reads: no code blocks, inline code, link targets or Mermaid."""
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)  # markers such as the footer's, not read
    md = re.sub(r"`[^`]*`", "", md)
    md = re.sub(r"\]\([^)]*\)", "]", md)
    return md


def plugin_mirror():
    """The plug-ins help mirror (DASH-426, docs/help/plugins, from tools/sync-plugin-help.py): every plug-in in its
    catalogue has its Overview and seven pages, each marked as a copy. With STARBOARD_PLUGINS set to a starboard-plugins
    checkout, the copy must also match it."""
    out = []
    folder = HELP / "plugins"
    cat = folder / "catalogue.json"
    if not cat.exists():
        return ["docs/help/plugins: no catalogue.json; run tools/sync-plugin-help.py"]
    import json
    for p in json.loads(cat.read_text())["plugins"]:
        for name in ["README.md"] + [f"{k}.md" for k in ("install", "settings", "dashboard-card", "updates", "accessibility",
                                                          "problems", "for-developers")]:
            f = folder / p["id"] / name
            if not f.exists():
                out.append(f"plugins/{p['id']}/{name}: missing from the plug-ins help mirror; run tools/sync-plugin-help.py")
            elif "tools/sync-plugin-help.py" not in f.read_text():
                out.append(f"plugins/{p['id']}/{name}: not marked as a copy; change it in starboard-plugins and run tools/sync-plugin-help.py")
            elif re.search(r"still to be written|\bTODO\b|\bTBD\b", text_only(f.read_text())):
                out.append(f"plugins/{p['id']}/{name}: still a placeholder")
    import os
    import subprocess
    if os.environ.get("STARBOARD_PLUGINS"):
        r = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("sync-plugin-help.py")), os.environ["STARBOARD_PLUGINS"], "--check"],
                           capture_output=True, text=True)
        if r.returncode:
            out.append("docs/help/plugins: " + r.stdout.strip().splitlines()[-1])
    return out


def plugin_api_pages():
    """The pages that describe the plug-in API to AI tools and developers name the version they describe
    (<!-- plugin-api: 1.14 -->). When Starboard's plug-in API is newer, they fail until they are brought up to it."""
    out = []
    code = (HELP.parent.parent / "starboard" / "plugins.py").read_text()
    have = tuple(int(x) for x in re.search(r'^API_VERSION = "(\d+)\.(\d+)', code, re.M).groups())
    for rel in ("developers/ai-prompts-for-developers.md", "llms.txt"):
        m = re.search(r"<!--\s*plugin-api:\s*(\d+)\.(\d+)\s*-->", (HELP / rel).read_text())
        if not m:
            out.append(f"{rel}: no <!-- plugin-api: x.y --> line saying which plug-in API it describes")
        elif tuple(map(int, m.groups())) < have:
            out.append(f"{rel}: describes plug-in API {m.group(1)}.{m.group(2)}, but Starboard has {have[0]}.{have[1]}: "
                       "bring it up to date, then change the plugin-api line")
    return out


def main():
    problems = []
    import json
    config = json.loads((HELP.parent.parent / "help-centre.json").read_text())
    global GROUPS
    GROUPS = {(a["key"], g["key"]) for a in config.get("areas", []) for g in a.get("groups", [])}
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
            if tier == "guides" and "```mermaid" not in md and "```flow" not in md:
                problems.append(f"{rel}: a guide needs its steps as a flow chart")
            # The help centre standard (design system HELP-WRITING.md, section 11): every article names its area and
            # group from help-centre.json, and a troubleshooting topic starts with its flow chart.
            m = re.search(r"<!--\s*help:\s*([\w-]+)\s*/\s*([\w-]+)\s*-->", md)
            if not m:
                problems.append(f"{rel}: has no <!-- help: <area> / <group> --> line under its first line")
            elif (m.group(1), m.group(2)) not in GROUPS:
                problems.append(f"{rel}: {m.group(1)} / {m.group(2)} is not a group in help-centre.json")
            first = md.splitlines()[0]
            if first.rstrip().endswith("troubleshooting") and "```flow" not in md:
                problems.append(f"{rel}: a troubleshooting topic starts with a flow chart (a flow block)")
        words = text_only(md)
        for _n, line in enumerate(words.splitlines(), 1):
            for pattern, what in RULES:
                if re.search(pattern, line, flags=re.I if "I'm" not in pattern else 0):
                    if what.startswith("enable") and re.search(r"\*\*Enable SSH\*\*", line):
                        continue  # Raspberry Pi Imager's own label, copied exactly
                    problems.append(f"{rel}: {what}: {line.strip()[:90]}")
    # The download rights footer (tools/help_footer.py) on every page and the README, as it is written there.
    import importlib.util
    spec = importlib.util.spec_from_file_location("help_footer", pathlib.Path(__file__).with_name("help_footer.py"))
    footer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(footer)
    for path in footer.pages():
        if footer.FOOTER not in path.read_text():
            problems.append(f"{path.relative_to(HELP.parent.parent)}: no download rights footer, or an old one (run tools/help_footer.py)")
    problems += plugin_mirror() + plugin_api_pages()
    for target in re.findall(r"\]\(([^)#\s]+)\)", index):
        if not target.startswith("https://") and not (HELP / target).exists():  # a web address is not a page
            problems.append(f"README.md: the index lists {target}, which does not exist yet")
    for p in problems:
        print(p)
    # Every topic (tier one) has at least 3 marked-up screenshots (owner, 7 November 2026). Reported, not yet a
    # failure, until the backlog is done: then move it into problems.
    few = [str(f.relative_to(HELP)) for f in files if f.parent.name in ("topics", "accessibility")
           and len(re.findall(r"!\[[^\]]+\]\(", f.read_text())) < SCREENSHOTS_PER_TOPIC]
    if few:
        print(f"{len(few)} topics have fewer than {SCREENSHOTS_PER_TOPIC} screenshots (python3 tools/check-help.py --list-screenshots lists them)")
        if "--list-screenshots" in sys.argv:
            print("\n".join("  " + f for f in few))
    print(f"{len(files)} articles checked, {len(problems)} problems")
    # Every link into the help, from the help, the release notes, the pages and the code, reaches its heading.
    spec = importlib.util.spec_from_file_location("check_help_links", pathlib.Path(__file__).with_name("check-help-links.py"))
    links = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(links)
    return 1 if links.main() or problems else 0


if __name__ == "__main__":
    sys.exit(main())
