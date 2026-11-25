#!/usr/bin/env python3
"""Runs the unit tests in parallel: python3 tools/run-tests.py [-j N] [-v] [module ...]

Each test file runs in its own process (`python3 -m unittest tests.test_x`), a few at a time, the biggest files first.
Same tests as `python3 -m unittest discover -s tests`, which stays the plain way and the one the pull-request check uses;
this is the quick way on a computer with several processors (the whole suite is mostly waiting, so it takes about a
third of the time). A failing file prints its own full output. Exit code 0 only when every file passed.
"""
import argparse
import concurrent.futures
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")


def modules(wanted):
    names = sorted(f[:-3] for f in os.listdir(TESTS) if re.fullmatch(r"test_.*\.py", f))
    if wanted:
        names = [n for n in names if n in {w.replace("tests.", "").removesuffix(".py") for w in wanted}]
    return sorted(names, key=lambda n: -os.path.getsize(os.path.join(TESTS, n + ".py")))


def run_one(name):
    t = time.time()
    p = subprocess.run([sys.executable, "-m", "unittest", f"tests.{name}"], cwd=ROOT, capture_output=True, text=True)
    out = p.stdout + p.stderr
    m = re.search(r"^Ran (\d+) tests?", out, re.M)
    sk = re.search(r"skipped=(\d+)", out)
    return name, p.returncode, int(m.group(1)) if m else 0, int(sk.group(1)) if sk else 0, time.time() - t, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=max(2, min(8, (os.cpu_count() or 2))), help="files at once (default: processors, at most 8)")
    ap.add_argument("-v", action="store_true", help="print each file as it finishes")
    ap.add_argument("modules", nargs="*")
    a = ap.parse_args()
    names = modules(a.modules)
    start = time.time()
    ran = skipped = 0
    bad = []
    with concurrent.futures.ThreadPoolExecutor(a.j) as ex:
        for name, code, n, sk, took, out in ex.map(run_one, names):
            ran, skipped = ran + n, skipped + sk
            if a.v:
                print(f"{'ok  ' if code == 0 else 'FAIL'} {name} ({n} tests, {took:.1f} s)", flush=True)
            if code:
                bad.append(name)
                print(f"\n===== {name} =====\n{out}", flush=True)
    took = time.time() - start
    print(f"\nRan {ran} tests in {len(names)} files in {took:.1f}s with {a.j} at once" + (f" (skipped={skipped})" if skipped else ""))
    print("OK" if not bad else "FAILED: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
