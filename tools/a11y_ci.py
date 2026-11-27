#!/usr/bin/env python3
"""Reads the two result files tools/a11y.sh wrote (a11y.json for axe, order.json for reading order) and fails on what is
new, as tools/done-check.sh does: findings listed in tools/done-check-baseline.json are known on main and do not fail.
Prints each new finding as a GitHub annotation. Used by .github/workflows/a11y.yml (the check "a11y (changed pages)")."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import done_check as gate  # noqa: E402


def main(results=ROOT / "tools" / "a11y"):
    baseline = gate.json.loads(gate.BASELINE.read_text()) if gate.BASELINE.exists() else {}
    failed = False
    for step, parser, name in (("axe", gate.parse_axe, "a11y.json"), ("order", gate.parse_order, "order.json")):
        found, _ = parser("", {"json": results / name})
        result, new, old = gate.judge(step, 0, found, baseline)
        print(f"{step}: {result}; {sum(old.values())} known on main")
        for key, n in new.items():
            print(f"::error title=Accessibility ({step})::{key} ({n})")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
