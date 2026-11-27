#!/usr/bin/env python3
"""Fails when a wizard or multi-step flow has no keyboard task (owner, 27 November 2026).

    python3 tools/check-wizard-coverage.py

tools/a11y/wizards.json lists every flow, the files that draw it and the keyboard tasks that cover it. This checks that:
  1. every browser flow names at least one task, and each task id is a quoted id used by a check, walk or panel task in tools/a11y/tasks.mjs or wizards.mjs;
  2. every terminal flow (browser false) names the tests that cover it, and they exist;
  3. every file named in a flow exists;
  4. every script in web/js that draws a wizard (it calls wizardFrame or taskJob, or has "wizard" in its name) is named
     by a flow, so a new wizard cannot be added without its row.
Exit code 0 when all hold, 1 with each problem on its own line otherwise."""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASK_FILES = [ROOT / "tools/a11y/tasks.mjs", ROOT / "tools/a11y/wizards.mjs"]


def problems(root=ROOT, task_files=None):
    task_files = task_files or [root / "tools/a11y/tasks.mjs", root / "tools/a11y/wizards.mjs"]
    registry = json.loads((root / "tools/a11y/wizards.json").read_text())
    text = "\n".join(f.read_text() for f in task_files if f.exists())
    found = []
    named = set()
    for flow in registry["flows"]:
        fid = flow.get("id", "?")
        named.update(flow.get("files", []))
        for f in flow.get("files", []):
            if not (root / f).exists():
                found.append(f"{fid}: the file {f} does not exist")
        if flow.get("browser", True):
            if not flow.get("tasks"):
                found.append(f"{fid}: no keyboard task (add one to tools/a11y/wizards.mjs and list its id)")
            for task in flow.get("tasks", []):
                if not re.search(r'["\'`]' + re.escape(task) + r'["\'`]', text):
                    found.append(f"{fid}: no check for task {task} in tasks.mjs or wizards.mjs")
        else:
            if not flow.get("covered_by"):
                found.append(f"{fid}: a terminal flow needs covered_by, the tests that cover it")
            for t in flow.get("covered_by", []):
                if not (root / t).exists():
                    found.append(f"{fid}: the test {t} does not exist")
    for script in sorted((root / "web/js").glob("*.js")):
        rel = f"web/js/{script.name}"
        body = script.read_text(errors="replace")
        if re.search(r"\b(wizardFrame|taskJob)\(", body) or "wizard" in script.name:
            if rel not in named:
                found.append(f"{rel} draws a wizard but is in no flow of tools/a11y/wizards.json")
    return found


def main():
    found = problems()
    for line in found:
        print(line)
    registry = json.loads((ROOT / "tools/a11y/wizards.json").read_text())
    print(f"{len(registry['flows'])} flows, {len(found)} problems")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
