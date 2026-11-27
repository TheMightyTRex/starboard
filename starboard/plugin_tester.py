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


# The plug-in API version each manifest field first came in (from the API changelog): a plug-in that uses one needs at least this.
FIELD_SINCE = {"setup_required": "1.4", "notices": "1.4", "events": "1.4", "jobs": "1.4", "changes": "1.10", "adopt": "1.13",
               "logo": "1.14", "update": "1.14", "jellyfin_libraries": "1.15", "requires": "1.19", "first_sign_in": "1.20",
               "starboard_tested": "1.22", "capabilities": "1.22", "needs_plugins": "1.21", "switch": "1.21"}


def _version(text):
    try:
        return tuple(int(x) for x in str(text).split(".")[:2])
    except ValueError:
        return None


def _api_checks(m):
    """The plug-in's statement of the API it needs (DASH-603): a top end, a lower end that is high enough for what it uses, and what it
    was tested with. Warnings only: Starboard never refuses a plug-in for these."""
    out = []

    def add(sev, what, fix):
        out.append({"severity": sev, "where": "starboard_api", "what": what, "fix": fix, "area": "compatibility"})
    spec = str(m.get("starboard_api") or "")
    clauses = spec.split()
    lows = [c.lstrip(">=") for c in clauses if c.startswith((">=", ">")) or c[:1].isdigit()]
    highs = [c for c in clauses if c.startswith("<")]
    if spec and not highs:
        add("warning", "starboard_api has no top end, so it promises to work with every future version",
            "End it at the next major version, such as >=1.14 <2.0")
    elif any(_version(c.lstrip("<=")) and _version(c.lstrip("<=")) > (2, 0) for c in highs):
        add("warning", "starboard_api reaches past the next major version, where parts of the API may be removed", "End it at <2.0")
    low = _version(lows[0]) if lows else None
    if low:
        need = max(((_version(v), k) for k, v in FIELD_SINCE.items() if k in m), default=None)
        if need and need[0] and need[0] > low:
            add("warning", f"starboard_api starts at {'.'.join(map(str, low))}, but {need[1]} came in at {'.'.join(map(str, need[0]))}",
                f"Start it at >={need[0][0]}.{need[0][1]}, so an older Starboard does not try to run it")
    tested = _version(m.get("starboard_tested"))
    if tested and isinstance(m.get("starboard_tested"), str):
        from . import plugins
        now = _version(plugins.API_VERSION)
        if tested > now:
            add("info", f"starboard_tested {m['starboard_tested']} is newer than this Starboard's API", "Test with this version too")
    from . import plugin_capabilities
    uses = (m.get("capabilities") or {}).get("uses") if isinstance(m.get("capabilities"), dict) else None
    for n in plugin_capabilities.missing(uses):
        add("info", f"It uses {n}, which this Starboard does not have", "Check GET /api/v1/ for capabilities and work without it")
    from . import deprecations
    for w in deprecations.for_manifest(m):  # a part of the manifest that is going, with the day it stops
        add("error" if w["removed"] else "warning", deprecations.warning_sentence(w), "Use what replaces it, and name the new version in starboard_api")
    if "starboard_tested" not in m and "starboard_api" in m:
        add("info", "It does not say which API version it was tested with", "Add starboard_tested, such as 1.22")
    return out


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
        add("warning", "description", "An em dash can be read oddly by some screen readers", "Use a full stop or a comma instead")
    # The writing rules of the design system's CONTENT-DESIGN.md (17 November 2026): the words people read in a
    # label, hint or confirm text, each with the house replacement as the fix.
    for where, text in _shown_texts(m):
        for rx, what, fix in WORD_RULES:
            if rx.search(text):
                add("warning", where, what, fix)
        if text == "Title Case":
            add("warning", where, "The label is in Title Case", "Write it in sentence case: only the first word and names take a capital")
        elif EM_DASH in text:
            add("warning", where, "An em dash can be read oddly by some screen readers", "Use a full stop or a comma instead")
    return out


# Each rule: what to find, what is wrong, and the house replacement.
WORD_RULES = [
    (re.compile(r"\b\w+n['’]t\b|\b(?:you|we|they|it|that|there|what|who|here|let|I)['’](?:s|re|ll|ve|d|m)\b", re.I),
     "A contraction", "Write it in full, such as do not or it is"),
    (re.compile(r"\b(?:see|sees|seen|seeing|look|looks|looked|looking)\b", re.I),
     "\"See\" or \"look\"", "Say what happens instead: show, read, check, find or search"),
    (re.compile(r"\b(?:click|clicks|clicked|clicking|tap|tapped)\b", re.I), "\"Click\" or \"tap\"", "Use select"),
    (re.compile(r"!"), "An exclamation mark", "End with a full stop"),
]
TITLE_CASE = re.compile(r"^(?:[A-Z][a-z]+ ){2,}[A-Z][a-z]+$")


def _shown_texts(m):
    """(where, text) for each label, hint and confirm text in settings and actions."""
    for kind in ("settings", "actions"):
        for i, s in enumerate(m.get(kind) or []):
            if not isinstance(s, dict):
                continue
            for key in ("label", "hint", "confirm"):
                if isinstance(s.get(key), str) and s[key]:
                    yield f"{kind}[{i}].{key}", s[key]
            if kind == "settings" and TITLE_CASE.match(str(s.get("label", ""))):
                yield f"{kind}[{i}].label", "Title Case"


def card_titles(card):
    return plugins.card_title_problems(card) if isinstance(card, dict) else []


def run(manifest, dev=False, builtin=False, logo_problem=""):
    """All issues for a manifest: [{severity, area, where, what, fix}], errors first. Never empty of accessibility
    checks: when a plug-in has nothing to check, it says what was checked. `logo_problem`: what was wrong with its
    logo file when Starboard read it (API 1.14), from beside its address or its folder."""
    issues = []
    if not isinstance(manifest, dict):
        return [{"severity": "error", "area": "manifest", "where": "manifest", "what": "Not a JSON object", "fix": "Check the file is starboard-plugin.json"}]
    style_errors = set()
    for i, st in enumerate(manifest.get("styles") or []):
        for issue in plugin_styles.check_style(st, f"styles[{i}]"):
            issues.append({**issue, "area": "accessibility"})
            style_errors.add(f"{issue['where']}: {issue['what']}")
    # A title for each card size (API 1.15, DASH-443): each one too long for one line is named, with its fix.
    for i, c in enumerate(manifest.get("cards") or []):
        for what, fix in card_titles(c):
            issues.append({"severity": "error", "area": "accessibility", "where": f"cards[{i}].titles", "what": what[:1].upper() + what[1:], "fix": fix})
            style_errors.add(f"cards[{i}]: {what}")
    for p in plugins.check(manifest, dev=dev, builtin=builtin):
        if p not in style_errors:  # style problems are listed once, with their fix
            where, _, what = p.partition(": ") if re.match(r"^[a-z_]+(\[\d+\])?(\.[a-z]+)?: ", p) else ("manifest", "", p)
            issues.append({"severity": "error", "area": "manifest", "where": where, "what": what or p, "fix": "Read the manifest reference in the help centre"})
    issues += _text_checks(manifest)
    for i, c in enumerate(manifest.get("containers") or []):
        if isinstance(c, dict):
            if dev and "@sha256:" not in str(c.get("image", "")):
                issues.append({"severity": "warning", "area": "security", "where": f"containers[{i}]", "what": "The image is not pinned by digest",
                               "fix": "Pin it as name@sha256:... before anyone else installs it"})
            if c.get("build") is True:  # API 1.15 (DASH-414)
                issues.append({"severity": "info", "area": "security", "where": f"containers[{i}]",
                               "what": "Its image is built from the Dockerfile in the plug-in's zip, so it installs only from a zip file",
                               "fix": "Share the zip (Settings, Plug-ins, Add a plug-in, Upload a zip file); an address or catalogue cannot install it"})
            if i and c.get("start") == "when_needed":  # DASH-357: only the container Starboard calls can be started again
                issues.append({"severity": "warning", "area": "quality", "where": f"containers[{i}]",
                               "what": "Only the first container can rest when idle, because Starboard only calls that one; this one runs always",
                               "fix": "Leave out start and idle_stop_minutes here, or make it the first container if Starboard alone calls it"})
            if c.get("network") == "lan":
                issues.append({"severity": "info", "area": "security", "where": f"containers[{i}]", "what": "It can reach your home network",
                               "fix": "Use the default network unless it needs other computers"})
    from . import plugin_cards
    for i, c in enumerate(manifest.get("cards") or []):
        if not isinstance(c, dict):
            continue
        if "example" not in c:
            issues.append({"severity": "warning", "area": "quality", "where": f"cards[{i}]", "what": "No example answer, so the card cannot be tested",
                           "fix": "Add example: what the card's path answers, such as {\"value\": 42}"})
        else:
            try:
                plugin_cards.clean(c.get("type"), c["example"], strict=True)
            except ValueError as e:
                issues.append({"severity": "error", "area": "manifest", "where": f"cards[{i}].example", "what": str(e),
                               "fix": "Make the path answer the shape for its type (help: What a plug-in can change, Dashboard cards)"})
    # The logo (API 1.14, DASH-428): the file's own checks, and a nudge towards one, so every card looks the same.
    if logo_problem:
        # A warning, not an error: a refused logo never stops a plug-in being added; Starboard shows its initials.
        severe = "warning" if manifest.get("logo") and "only when it is added from an address" not in logo_problem else "info"
        issues.append({"severity": severe, "area": "security" if severe == "warning" else "quality", "where": "logo", "what": logo_problem,
                       "fix": "A plain SVG (16 KB at most, with a viewBox, no scripts, styles, pictures or outside links) or a square "
                              "PNG of 32 to 256 pixels (32 KB at most), beside starboard-plugin.json"})
    elif "logo" not in manifest and (manifest.get("cards") or manifest.get("containers")):
        issues.append({"severity": "info", "area": "quality", "where": "logo", "what": "No logo, so Starboard shows its initials",
                       "fix": "Add logo: {\"file\": \"logo.svg\", \"alt\": \"What it shows\"}, a small SVG or PNG beside the manifest"})
    # Without a small title, a small card's heading is the plug-in's name (API 1.15, DASH-443): a nudge when it is
    # longer than one line there.
    name = str(manifest.get("name") or "")
    small = plugins.CARD_TITLE_MAX["small"]
    for i, c in enumerate(manifest.get("cards") or []):
        if isinstance(c, dict) and len(name) > small and not (isinstance(c.get("titles"), dict) and c["titles"].get("small")):
            issues.append({"severity": "info", "area": "quality", "where": f"cards[{i}]",
                           "what": f"On a small card the heading is the plug-in's name, {len(name)} characters, which takes more than one line",
                           "fix": f'Add titles with a small title of up to {small} characters, such as "titles": {{"small": "Short name"}}'})
    for i, c in enumerate(manifest.get("cards") or []):
        if isinstance(c, dict) and isinstance(c.get("example"), dict) and c["example"].get("status") is None and c.get("type") != "status":
            issues.append({"severity": "info", "area": "quality", "where": f"cards[{i}]",
                           "what": "No status in the example, so the card's band shows only when it last updated",
                           "fix": "Answer status (such as working, done or problem) when the plug-in works in the background"})
    # Updating safely (API 1.14, DASH-424): What is new before and after, and work that an update could cut short.
    listed = [c.get("version") for c in manifest.get("changes") or [] if isinstance(c, dict)]
    if listed and manifest.get("version") not in listed:
        issues.append({"severity": "warning", "area": "quality", "where": "changes",
                       "what": f"changes has nothing for this version, {manifest.get('version')}, so What is new cannot say what changed",
                       "fix": "Add this version to changes, newest first, before you publish it"})
    elif not listed and manifest.get("containers"):
        issues.append({"severity": "info", "area": "quality", "where": "changes", "what": "No changes, so What is new says its maker did not list them",
                       "fix": "Add changes: each version with what was added, changed or fixed, shown before and after an update"})
    upd = manifest.get("update") if isinstance(manifest.get("update"), dict) else {}
    if manifest.get("jobs") and manifest.get("containers") and not upd.get("before"):
        issues.append({"severity": "info", "area": "quality", "where": "update", "what": "It has jobs, but no before step, so an update can stop one part way",
                       "fix": "Add update.before: a path that finishes or pauses its work, answering {\"ok\": true} when it is ready"})
    if upd.get("migrations") and not manifest.get("changes"):
        issues.append({"severity": "info", "area": "quality", "where": "update.migrations", "what": "Settings move in this version, but changes does not say so",
                       "fix": "Say in changes what moved, so people know before they update"})
    if manifest.get("containers") and not manifest.get("health"):
        issues.append({"severity": "warning", "area": "quality", "where": "health", "what": "No health path, so Starboard cannot tell when it breaks",
                       "fix": "Add a cheap GET path that answers 200, such as /health"})
    for w in plugins.permission_words(manifest) if isinstance(manifest.get("permissions"), list) else []:
        if w["risk"] == "high":
            issues.append({"severity": "info", "area": "security", "where": "permissions", "what": f"High risk: {w['words']}",
                           "fix": "People are warned before adding it; ask only for what you use"})
    order = {"error": 0, "warning": 1, "info": 2}
    issues += _api_checks(manifest)
    issues.sort(key=lambda i: (order[i["severity"]], i["area"], i["where"]))
    return issues


def report(manifest, dev=False, builtin=False, logo_problem=""):
    """{ok, errors, warnings, infos, issues, accessibility}: what pages and the command show."""
    issues = run(manifest, dev, builtin, logo_problem)
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
    previous = None
    if "--previous" in args:  # DASH-423: the update from the version before, and Roll back, on the settings alone
        i = args.index("--previous")
        previous = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    paths = [a for a in args if a != "--dev"]
    if len(paths) != 1 or previous == "":
        print("Usage: python3 -m starboard.plugin_tester [--dev] [--previous old/starboard-plugin.json] path/to/starboard-plugin.json (or its folder)")
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
    problem = ""
    logo = manifest.get("logo") if isinstance(manifest, dict) else None
    if isinstance(logo, dict) and isinstance(logo.get("file"), str):  # API 1.14: the file beside the manifest
        from . import plugin_logo
        try:
            if not plugin_logo.check_entry(logo):
                with open(os.path.join(os.path.dirname(path), logo["file"]), "rb") as f:
                    plugin_logo.clean(f.read(plugin_logo.PNG_MAX + 1), logo["file"])
        except (OSError, ValueError) as e:
            problem = str(e)
    r = report(manifest, dev, logo_problem=problem)
    for i in r["issues"]:
        print(f"{i['severity'].upper():8} {i['area']:13} {i['where']}: {i['what']}\n{'':23}Fix: {i['fix']}")
    print(f"\nAccessibility: {'passed' if r['accessibility']['passed'] else 'FAILED'} ({r['accessibility']['checked']})")
    print(f"{r['errors']} errors, {r['warnings']} warnings, {r['infos']} tips. {'Ready to add.' if r['ok'] else 'Fix the errors before adding it.'}")
    ok = r["ok"]
    if previous is not None:
        if os.path.isdir(previous):
            previous = os.path.join(previous, "starboard-plugin.json")
        try:
            with open(previous, encoding="utf-8") as f:
                old = json.load(f)
        except (OSError, ValueError) as e:
            print(f"Cannot read {previous}: {e}")
            return 2
        from . import plugin_update
        issues = plugin_update.rehearse(old, manifest)
        print(f"\nUpdate from {old.get('version')} to {manifest.get('version')}, and Roll back:")
        for sev, what, fix in issues:
            print(f"{sev.upper():8} update        {what}\n{'':23}Fix: {fix}")
        bad = [i for i in issues if i[0] == "error"]
        print("The update and Roll back keep the settings." if not bad else f"{len(bad)} errors in the update. Fix them before publishing.")
        ok = ok and not bad
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
