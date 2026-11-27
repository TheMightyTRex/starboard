#!/usr/bin/env python3
"""The done gate: every check a change needs before anyone says it is done (tools/done-check.sh runs this).

Run it once, on the final tip, through the shared heavy-run wrapper:

    /mnt/pool/build-cache/heavy-run-wt2 tools/done-check.sh

It runs each step in order, keeps going after a failure so one run reports everything (FAIL_FAST=1 stops at the first
new failure), prints a short table (step, result, seconds, log) and ends with DONE-CHECK PASSED or
DONE-CHECK FAILED: <steps>. The same table is written to done-check-out/summary.md for the pull request, and each
step's full output to done-check-out/logs/.

Known failures already on main do not hide new ones. tools/done-check-baseline.json lists them by name and count for
each step; a step whose only failures are listed there ends as "known on main" and does not fail the gate. Anything
not listed, or listed with a smaller count, is new and fails. Fix a known item and remove it from the file in the same
change; never add an item to hide a failure the change caused.

Environment:
  BASE=origin/main    what the change is compared with
  ONLY=a,b            run only these steps (a partial run, labelled as one in the summary)
  SKIP=a,b            leave these steps out (also labelled as partial)
  FAIL_FAST=1         stop at the first new failure
  CHANGED_ONLY=1      with a shared script or style file changed, check the fixed sample of pages, not every page
  FULL=1              run the accessibility steps on every page whatever changed
  DONE_CHECK_OUT=DIR  where the summary and logs go (default done-check-out in the repository)
Ports for the example servers follow A11Y_PORT and JOURNEYS_PORT, as the scripts they call do.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "done-check-baseline.json"
LIBRARY = pathlib.Path(os.environ.get("STARBOARD_DESIGN_SYSTEM") or os.path.expanduser("~/src/design-system"))
OUT = pathlib.Path(os.environ.get("DONE_CHECK_OUT") or ROOT / "done-check-out")
BASE = os.environ.get("BASE", "origin/main")


# ---------------------------------------------------------------------------------------------------------------------
# Reading what a step printed. Each parser returns ({name: count} of what failed, [notes to print]).

def parse_unit(log, ctx):
    found = {}
    for _kind, _, where in re.findall(r"^(FAIL|ERROR): (\S+) \(([\w.]+)\)", log, re.M):
        found[where] = found.get(where, 0) + 1
    ran = re.search(r"^Ran (\d+) tests", log, re.M)
    return found, [f"{ran.group(1)} tests ran"] if ran else []


def parse_checks(log, ctx):
    """tools/checks.sh prints PASS or FAIL for each tool, then the tool's findings indented. Count them by file."""
    found, tool = {}, None
    for line in log.splitlines():
        m = re.match(r"^(PASS|FAIL) (.+)$", line)
        if m:
            tool = m.group(2) if m.group(1) == "FAIL" else None
            continue
        if tool is None or not line.startswith("     "):
            continue
        body = line.strip()
        f = re.match(r"-->\s+(\S+?):\d+:\d+", body) or re.match(r"(?:\./)?(\S+?):\d+(?::\d+)?[:\s]", body)
        if f:
            key = f"{tool}|{f.group(1)}"
            found[key] = found.get(key, 0) + 1
    for m in re.finditer(r"^FAIL (.+)$", log, re.M):  # a tool failed in a way this reader does not know: still a failure
        if not any(k.startswith(m.group(1) + "|") for k in found):
            found[f"{m.group(1)}|(output not recognised)"] = 1
    return found, []


def parse_words(log, ctx):
    found = {}
    for path in re.findall(r'^(\S+?):\d+: "', log, re.M):
        found[path] = found.get(path, 0) + 1
    return found, []


def parse_help(log, ctx):
    found = {}
    for line in log.splitlines():
        m = re.match(r"^(?:docs/help/)?(\S+\.md)(?::\d+)?: (.+)$", line)
        if m:
            found[f"{m.group(1)}: {m.group(2)}"] = 1
        m = re.match(r"^(\d+) topics have fewer than 3 screenshots", line)
        if m:
            found["topics have fewer than 3 screenshots"] = int(m.group(1))
    return found, []


def parse_verbose(log, ctx):
    found = {}
    for path in re.findall(r"::warning file=([^,]+),line=\d+,title=(?:Sentence over|Paragraph over)", log):
        found[path] = found.get(path, 0) + 1
    other = len(re.findall(r"^::warning ", log, re.M)) - sum(found.values())
    return found, [f"{other} other suggestions on added lines (not failures)"] if other > 0 else []


def parse_ds(log, ctx):
    """Which file differs depends on the library's commit, so it is named in the log and counted once here (DASH-609)."""
    found = {}
    if any(path.startswith(str(ROOT)) for path in re.findall(r"^differs\s+(\S+)", log, re.M)):
        found["a copy of a design system file differs from the library"] = 1
    found.update(parse_unit(log, ctx)[0])
    return found, []


def parse_named_lines(log, ctx):
    """Journeys and keyboard tasks: 'FAIL ID what: detail'."""
    found = {}
    for line in re.findall(r"^FAIL (.+)$", log, re.M):
        name = line.split(": ")[0][:140]
        found[name] = found.get(name, 0) + 1
    ran = re.search(r"== (\d+) passed, (\d+) failed", log)
    return found, [f"{ran.group(1)} passed"] if ran else []


def parse_layout(log, ctx):
    found = {}
    for key in re.findall(r"^FAIL (\S+) \(", log, re.M):
        found[key] = 1
    return found, []


def parse_axe(log, ctx):
    return findings_from_json(ctx["json"], lambda f: f"{f['page']}|{f['area']}|{f['rule']}"), []


def parse_order(log, ctx):
    return findings_from_json(ctx["json"], lambda f: f"{f['page']}|{f['rule']}"), []


def findings_from_json(path, key):
    found = {}
    try:
        data = json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return {"(the result file was not written)": 1}
    for f in data:
        k = key(f)
        found[k] = found.get(k, 0) + int(f.get("count", 1))
    return found


def parse_api(log, ctx):
    found = {}
    for plugin, check in re.findall(r"^  (\S+) (\S+(?: \S+)?): FAILED", log, re.M):  # the example plug-ins' smoke test
        found[f"smoke {plugin} {check}"] = found.get(f"smoke {plugin} {check}", 0) + 1
    notes = []
    if re.search(r"^Not run: ", log, re.M):
        notes.append("plug-in smoke test not run (needs Docker and starboard-plugins)")
    elif "Example plug-ins smoke test" in log:
        notes.append("plug-in smoke test ran")
    return found, notes


def parse_none(log, ctx):
    return {}, []


# ---------------------------------------------------------------------------------------------------------------------
# What the change touches decides which accessibility steps run.

def changes():
    sys.path.insert(0, str(ROOT / "tools"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("changed_pages", ROOT / "tools" / "changed-pages.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    files = mod.changed_files(BASE)
    sample = bool(os.environ.get("CHANGED_ONLY"))
    pages, reasons, kinds, shared = mod.pages_for(files, sample)
    if os.environ.get("FULL"):
        pages, shared = mod.all_pages(), True
    return {"files": files, "pages": pages, "reasons": reasons, "kinds": kinds, "shared": shared,
            "all": shared and not sample or bool(os.environ.get("FULL")), "ok": True}


def page_arg(ch):
    """PAGES for the accessibility scripts: nothing means every page."""
    return "" if ch["all"] else ",".join(ch["pages"])


def a11y_run(ch, env_extra):
    pages = page_arg(ch)
    return {"cmds": [["bash", "tools/a11y.sh"]], "env": {"ORDER": "", "TASKS": "", "LAYOUT": "", **env_extra, "PAGES": pages}}


def docker_ready():
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def steps(ch):
    """The steps in order: (name, title, what to run or why to skip, parser). A skip reason is a string."""
    k = ch["kinds"]
    web = k["web"] or k["checks"]
    pages_ok = bool(ch["pages"]) or ch["all"]
    no_pages = "no page, script or style file in web/ changed"
    docker = docker_ready()
    nodocker = "Docker is not available here (the check cannot run, so it cannot pass)"
    clean_json = [ROOT / "tools/a11y/a11y.json", ROOT / "tools/a11y/order.json", ROOT / "tools/a11y/layout.json"]
    steps = [
        ("unit", "Unit tests", {"cmds": [[sys.executable, "tools/run-tests.py", "-j", "4"]]}, parse_unit),
        ("api", "API and plug-in checks", {"cmds": [["bash", "tools/check-api.sh"]]}, parse_api),
        ("journeys", "Journeys", {"cmds": [["bash", "tools/journeys.sh"]]} if docker else nodocker, parse_named_lines),
        ("axe", "Accessibility: axe, WCAG 2.2 AA",
         {**a11y_run(ch, {}), "json": ROOT / "tools/a11y/a11y.json", "clean": clean_json} if docker and web and pages_ok
         else (nodocker if not docker else no_pages), parse_axe),
        ("order", "Accessibility: reading and Tab order",
         {**a11y_run(ch, {"ORDER": "1"}), "json": ROOT / "tools/a11y/order.json", "clean": clean_json} if docker and web and pages_ok
         else (nodocker if not docker else no_pages), parse_order),
        ("tasks", "Accessibility: keyboard tasks",
         {"cmds": [["bash", "tools/a11y.sh"]], "env": {"TASKS": "1", "ORDER": "", "LAYOUT": ""}} if docker and (web or k["server"]) else
         (nodocker if not docker else "no page, script, style or server file changed"), parse_named_lines),
        ("layout", "Layout at large text, wide spacing and short windows",
         {"cmds": [["bash", "tools/a11y.sh"]], "env": {"LAYOUT": "1", "TASKS": "", "ORDER": "", "PAGES": "" if ch["all"] or not ch["pages"] else ",".join(ch["pages"])},
          "clean": clean_json} if docker and k["css"] else (nodocker if not docker and k["css"] else "no style file in web/css changed"), parse_layout),
        ("ds", "Design system copies",
         {"cmds": [[sys.executable, "-m", "unittest", "tests.test_parts_loaded", "tests.test_design_system_copies", "tests.test_reelix_parts_once"],
                   [sys.executable, str(LIBRARY / "tools/sync.py"), "--check"]], "env": {"STARBOARD_WEB": str(ROOT / "web")}}
         if (LIBRARY / "tools/sync.py").exists() else "the design system is not on this computer (STARBOARD_DESIGN_SYSTEM)", parse_ds),
    ]
    if (ROOT / "tools/check-wizard-coverage.py").exists():
        steps.append(("wizards", "Every wizard has a keyboard task", {"cmds": [[sys.executable, "tools/check-wizard-coverage.py"]]}, parse_none))
    steps += [
        ("words", "Banned words", {"cmds": [[sys.executable, "tools/check_words.py"]]}, parse_words),
        ("verbose", "Long sentences on the lines this change adds", {"cmds": [[sys.executable, "tools/verbose-check.py", "ci", "--base", BASE, "--fail"]]}, parse_verbose),
        ("help", "Help centre", {"cmds": [[sys.executable, "tools/check-help.py"]]}, parse_help),
        ("private", "No private details", {"cmds": [["bash", "tools/check-private.sh"]]}, parse_none),
        ("checks", "Code and writing checks (Ruff, Biome, Vale, typos, workflows)",
         {"cmds": [["bash", "tools/checks.sh"]]} if docker else nodocker, parse_checks),
    ]
    return steps


# ---------------------------------------------------------------------------------------------------------------------

def run_step(spec, log_path):
    env = {**os.environ, **{k: str(v) for k, v in spec.get("env", {}).items()}}
    for stale in spec.get("clean", []):
        stale.unlink(missing_ok=True)  # an old result file must never stand in for this run
    out, rc = [], 0
    for cmd in spec.get("cmds") or [spec["cmd"]]:
        done = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, errors="replace")
        out.append(f"$ {' '.join(cmd)}\n{done.stdout}{done.stderr}\n[exit {done.returncode}]\n")
        rc = rc or done.returncode
    text = "\n".join(out)
    log_path.write_text(text)
    return rc, text


def judge(name, rc, found, baseline):
    """pass, known (only what main already has) or fail, with the new and the known items."""
    known_map = baseline.get("steps", {}).get(name, {}).get("known", {})
    new = {k: n for k, n in found.items() if n > known_map.get(k, 0)}
    old = {k: min(n, known_map[k]) for k, n in found.items() if k in known_map and n > 0}
    if new:
        return "fail", new, old
    if rc != 0 and not found:
        return "fail", {"(exit code %d and no failure recognised: read the log)" % rc: 1}, {}
    return ("known" if old else "pass"), {}, old


def owed(name, found, baseline):
    """Findings the baseline says are owed at release (the help pictures wait until the release batch)."""
    patterns = baseline.get("steps", {}).get(name, {}).get("owed_at_release", [])
    mine = {k: found[k] for k in list(found) if any(re.search(p, k) for p in patterns)}
    for k in mine:
        del found[k]
    return mine


def git_line(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main():
    only = [s for s in os.environ.get("ONLY", "").split(",") if s]
    skip = [s for s in os.environ.get("SKIP", "").split(",") if s]
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    ch = changes()
    sha = git_line("rev-parse", "--short", "HEAD")
    dirty = bool(git_line("status", "--porcelain", "--untracked-files=no"))
    started = time.time()
    rows, failed_steps, notes_all = [], [], []
    for name, title, spec, parser in steps(ch):
        if (only and name not in only) or name in skip:
            continue
        t = time.time()
        if isinstance(spec, str):
            # A step that cannot run for want of Docker cannot pass; one with nothing to check is just left out.
            fails = spec.startswith("Docker")
            rows.append((name, title, "FAIL" if fails else "skipped", 0, "-", spec))
            if fails:
                failed_steps.append(name)
            print(f"{'FAIL' if fails else 'skip'}  {name}: {spec}", flush=True)
            continue
        log_path = OUT / "logs" / f"{name}.log"
        print(f"run   {name} ...", flush=True)
        rc, log = run_step(spec, log_path)
        ctx = {"json": spec.get("json")}
        found, notes = parser(log, ctx)
        found = {k: v for k, v in found.items() if v > 0}
        if name == "ds":
            rc = 0  # sync.py --check also reports the other repositories' copies; only the lines for this checkout count (parse_ds)
        late = owed(name, found, baseline)
        result, new, old = judge(name, rc, found, baseline)
        secs = round(time.time() - t)
        detail = []
        if new:
            detail += [f"NEW {k} ({n})" if n > 1 else f"NEW {k}" for k, n in list(new.items())[:12]]
            if len(new) > 12:
                detail.append(f"and {len(new) - 12} more new")
        if old:
            detail.append(f"known on main: {sum(old.values())} ({len(old)} item{'s' if len(old) != 1 else ''})")
        if late:
            detail.append(f"owed at release: {sum(late.values())}")
        detail += notes
        label = {"pass": "PASS", "known": "PASS (known on main)", "fail": "FAIL"}[result]
        rows.append((name, title, label, secs, str(log_path.relative_to(ROOT)) if log_path.is_relative_to(ROOT) else str(log_path), "; ".join(detail)))
        notes_all.append((name, new, old, late))
        if result == "fail":
            failed_steps.append(name)
            print(f"FAIL  {name} ({secs} s)", flush=True)
            if os.environ.get("FAIL_FAST"):
                break
        else:
            print(f"{label.lower()[:4]}  {name} ({secs} s)", flush=True)
    total = round(time.time() - started)
    partial = bool(only or skip)
    lines = [f"Done check on `{sha}`{' (uncommitted changes in the working tree: not the final tip)' if dirty else ''}, "
             f"against `{BASE}`, {time.strftime('%d %B %Y %H:%M')}, {total} s" + (f", partial run ({','.join(only) or 'skipping ' + ','.join(skip)})" if partial else ""),
             "", "| Step | Result | Seconds | Notes | Log |", "|---|---|---|---|---|"]
    for name, title, label, secs, log_path, detail in rows:
        lines.append(f"| {title} (`{name}`) | {label} | {secs} | {detail or '-'} | `{log_path}` |")
    lines += ["", f"Pages checked for accessibility: {'every page' if ch['all'] else (', '.join(ch['pages']) or 'none')}."]
    shown = [f"- {n}: {k}" for n, _, old, _ in notes_all for k in list(old)[:6]]
    if shown:
        lines += ["", "Known on main (listed in tools/done-check-baseline.json; not caused by this change):"] + shown
    verdict = "DONE-CHECK PASSED" if not failed_steps else "DONE-CHECK FAILED: " + ", ".join(failed_steps)
    if partial and not failed_steps:
        verdict += " (partial run: not enough to call the change done)"
    lines += ["", verdict]
    summary = "\n".join(lines) + "\n"
    (OUT / "summary.md").write_text(summary)
    print("\n" + summary)
    return 1 if failed_steps else 0


if __name__ == "__main__":
    sys.exit(main())
