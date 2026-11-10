"""The plug-in tester (DASH-284): checks a plug-in and lists its issues, each with where it is, what is wrong and
how to fix it. Accessibility is always tested and can never be switched off: every style in light and dark, the
words people read (names, labels, hints), and card and setting text.

Run it on a manifest file or folder:  python3 -m starboard.plugin_tester path/to/starboard-plugin.json
Starboard runs the same tests on Settings, Plug-ins, Test a plug-in, and before any plug-in is added.
Severity: "error" stops a plug-in being added; "warning" should be fixed; "info" is a tip.
"""
import json
import os
import re
import sys

from . import plugin_styles, plugins

EM_DASH = "—"


def _text_checks(m):
    """Words people read: plain, short, labelled (accessibility for screen readers and everyone)."""
    out = []

    def add(sev, where, what, fix):
        out.append({"severity": sev, "where": where, "what": what, "fix": fix, "area": "accessibility"})

    for i, s in enumerate(m.get("settings") or []):
        if isinstance(s, dict):
            label = str(s.get("label", ""))
            if label and len(label) > 60:
                add("warning", f"settings[{i}]", "The label is long; screen readers read all of it for every field", "Keep labels under 60 characters and put detail in hint")
            if label.endswith(":") or label.isupper():
                add("warning", f"settings[{i}]", "Labels in capitals or ending in a colon read badly aloud", "Write the label in sentence case without a colon")
            if s.get("type") in ("switch", "choice") and not s.get("hint"):
                add("info", f"settings[{i}]", "No hint says what this changes", "Add a one-sentence hint")
    for i, c in enumerate(m.get("cards") or []):
        if isinstance(c, dict) and not (c.get("title") or c.get("label")):
            add("error", f"cards[{i}]", "The card has no title, so a screen reader cannot name it", "Give the card a title")
    for i, a in enumerate(m.get("actions") or []):
        if isinstance(a, dict) and str(a.get("label", "")).lower() in ("click here", "here", "go", "ok", "submit"):
            add("warning", f"actions[{i}]", "The button label does not say what it does", "Name the action, such as Update now")
    words = " ".join(str(m.get(k, "")) for k in ("name", "description"))
    if EM_DASH in words:
        add("info", "description", "An em dash can be read oddly by some screen readers", "Use a full stop or a comma instead")
    return out


def run(manifest, dev=False, builtin=False):
    """All issues for a manifest: [{severity, area, where, what, fix}], errors first. Never empty of accessibility
    checks: when a plug-in has nothing to check, it says what was checked."""
    issues = []
    if not isinstance(manifest, dict):
        return [{"severity": "error", "area": "manifest", "where": "manifest", "what": "Not a JSON object", "fix": "Check the file is starboard-plugin.json"}]
    style_errors = set()
    for i, st in enumerate(manifest.get("styles") or []):
        for issue in plugin_styles.check_style(st, f"styles[{i}]"):
            issues.append({**issue, "area": "accessibility"})
            style_errors.add(f"{issue['where']}: {issue['what']}")
    for p in plugins.check(manifest, dev=dev, builtin=builtin):
        if p not in style_errors:  # style problems are listed once, with their fix
            where, _, what = p.partition(": ") if re.match(r"^[a-z_]+(\[\d+\])?(\.[a-z]+)?: ", p) else ("manifest", "", p)
            issues.append({"severity": "error", "area": "manifest", "where": where, "what": what or p, "fix": "See the manifest reference in the help centre"})
    issues += _text_checks(manifest)
    for i, c in enumerate(manifest.get("containers") or []):
        if isinstance(c, dict):
            if dev and "@sha256:" not in str(c.get("image", "")):
                issues.append({"severity": "warning", "area": "security", "where": f"containers[{i}]", "what": "The image is not pinned by digest",
                               "fix": "Pin it as name@sha256:... before anyone else installs it"})
            if c.get("network") == "lan":
                issues.append({"severity": "info", "area": "security", "where": f"containers[{i}]", "what": "It can reach your home network",
                               "fix": "Use the default network unless it really needs other computers"})
    from . import plugin_cards
    for i, c in enumerate(manifest.get("cards") or []):
        if not isinstance(c, dict):
            continue
        if "example" not in c:
            issues.append({"severity": "warning", "area": "quality", "where": f"cards[{i}]", "what": "No example answer, so the card cannot be tested",
                           "fix": "Add example: what the card's path answers, such as {\"value\": 42}"})
        else:
            try:
                plugin_cards.clean(c.get("type"), c["example"])
            except ValueError as e:
                issues.append({"severity": "error", "area": "manifest", "where": f"cards[{i}].example", "what": str(e),
                               "fix": "Make the path answer the shape for its type (help: What a plug-in can change, Dashboard cards)"})
    if manifest.get("containers") and not manifest.get("health"):
        issues.append({"severity": "warning", "area": "quality", "where": "health", "what": "No health path, so Starboard cannot tell when it breaks",
                       "fix": "Add a cheap GET path that answers 200, such as /health"})
    for w in plugins.permission_words(manifest) if isinstance(manifest.get("permissions"), list) else []:
        if w["risk"] == "high":
            issues.append({"severity": "info", "area": "security", "where": "permissions", "what": f"High risk: {w['words']}",
                           "fix": "People are warned before adding it; ask only for what you use"})
    order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: (order[i["severity"]], i["area"], i["where"]))
    return issues


def report(manifest, dev=False, builtin=False):
    """{ok, errors, warnings, infos, issues, accessibility}: what pages and the command show."""
    issues = run(manifest, dev, builtin)
    styles = len(manifest.get("styles") or []) if isinstance(manifest, dict) else 0
    acc = [i for i in issues if i["area"] == "accessibility"]
    return {"ok": not any(i["severity"] == "error" for i in issues),
            "errors": sum(i["severity"] == "error" for i in issues), "warnings": sum(i["severity"] == "warning" for i in issues),
            "infos": sum(i["severity"] == "info" for i in issues), "issues": issues,
            "accessibility": {"checked": f"{styles} style{'s' if styles != 1 else ''} in light and dark, settings, cards and actions",
                              "passed": not any(i["severity"] == "error" for i in acc)}}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    dev = "--dev" in args
    paths = [a for a in args if a != "--dev"]
    if len(paths) != 1:
        print("Usage: python3 -m starboard.plugin_tester [--dev] path/to/starboard-plugin.json (or its folder)")
        return 2
    path = paths[0]
    if os.path.isdir(path):
        path = os.path.join(path, "starboard-plugin.json")
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError) as e:
        print(f"Cannot read {path}: {e}")
        return 2
    r = report(manifest, dev)
    for i in r["issues"]:
        print(f"{i['severity'].upper():8} {i['area']:13} {i['where']}: {i['what']}\n{'':23}Fix: {i['fix']}")
    print(f"\nAccessibility: {'passed' if r['accessibility']['passed'] else 'FAILED'} ({r['accessibility']['checked']})")
    print(f"{r['errors']} errors, {r['warnings']} warnings, {r['infos']} tips. {'Ready to add.' if r['ok'] else 'Fix the errors before adding it.'}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
