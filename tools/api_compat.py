"""Compatibility checks for the public API and the plug-in API (DASH-603). Nothing here runs at Starboard's start-up.

    python3 tools/api_compat.py --check      # fail when the API lost or changed something without the deprecation steps
    python3 tools/api_compat.py --freeze     # rewrite tests/compat/surface-baseline.json (after a deliberate, announced change)
    python3 tools/api_compat.py --frozen     # run every frozen older plug-in manifest against this Starboard
    python3 tools/api_compat.py --rehearse permission:library:holding   # who would break if this were removed
    python3 tools/api_compat.py --usage DATA_FOLDER   # who still uses what is going, from the counter and the installed manifests

The baseline lists what a plug-in or an outside tool may rely on: routes (with scope, right, answer fields, required
inputs), permissions, key scopes, manifest fields, container fields, card, setting and event names. Adding is always
fine. Taking away, or making stricter, fails unless tests/compat/deprecations.json lists it, its notice has run
out and the API's major version has moved (or the entry says security: true, which allows it at once).
"""
import datetime as dt
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from starboard import api_v1, plugin_tester, plugins  # noqa: E402

BASE = os.path.join(ROOT, "tests", "compat", "surface-baseline.json")
DEPRECATIONS = os.path.join(ROOT, "tests", "compat", "deprecations.json")
FROZEN = os.path.join(ROOT, "tests", "compat", "frozen")


def _props(spec, schema, depth=0, prefix=""):
    """Names of the fields an answer carries, to two levels, with an array's item fields under name[]."""
    out = set()
    if not isinstance(schema, dict) or depth > 2:
        return out
    ref = schema.get("$ref")
    if ref:
        schema = spec["components"]["schemas"].get(ref.split("/")[-1], {})
    for k, v in (schema.get("properties") or {}).items():
        out.add(prefix + k)
        out |= _props(spec, v, depth + 1, prefix + k + ".")
    if isinstance(schema.get("items"), dict):
        out |= _props(spec, schema["items"], depth + 1, prefix + "[].")
    return out


def surface():
    spec = json.load(open(os.path.join(ROOT, "starboard", "openapi.json"), encoding="utf-8"))
    routes = {}
    for path, item in spec["paths"].items():
        for method, op in item.items():
            ok = (op.get("responses") or {}).get("200") or {}
            schema = ((ok.get("content") or {}).get("application/json") or {}).get("schema")
            params = [p for p in (op.get("parameters") or []) if isinstance(p, dict)]
            body = (((op.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema")
            routes[f"{method.upper()} {path}"] = {
                "scope": op.get("x-scope"), "right": op.get("x-right"),
                "answer": sorted(_props(spec, schema)) if schema else [],
                "required_in": sorted([p.get("name", "") for p in params if p.get("required")]
                                      + [f"body.{r}" for r in (body or {}).get("required", [])] if isinstance(body, dict) else
                                      [p.get("name", "") for p in params if p.get("required")])}
    return {
        "api_version": plugins.API_VERSION,
        "routes": routes,
        "permissions": {k: {"risk": v[1], "scope": v[2]} for k, v in plugins.PERMISSIONS.items()},
        "key_scopes": list(api_v1.ALL_SCOPES),
        "manifest_fields": sorted(plugins.TOP),
        "manifest_required": sorted(plugins.REQUIRED),
        "container_fields": sorted(plugins.CONTAINER),
        "card_types": list(plugins.CARD_TYPES),
        "setting_types": list(plugins.SETTING_TYPES),
        "events": {k: v[0] for k, v in plugins.EVENTS.items()},
        "change_types": list(plugins.CHANGE_TYPES),
    }


def compare(old, new):
    """(breaks, additions): plain sentences. A break is anything an older plug-in or tool could have relied on."""
    breaks, adds = [], []

    def sets(label, a, b):
        for x in sorted(set(a) - set(b)):
            breaks.append((f"{label}:{x}", f"{label} {x} was taken away"))
        for x in sorted(set(b) - set(a)):
            adds.append(f"{label} {x} was added")
    for name, order in (("manifest_fields", 0), ("container_fields", 0), ("card_types", 0), ("setting_types", 0), ("key_scopes", 0),
                        ("change_types", 0)):
        sets(name, old[name], new[name])
    sets("event", old["events"], new["events"])
    sets("permission", old["permissions"], new["permissions"])
    for x in sorted(set(new["manifest_required"]) - set(old["manifest_required"])):
        breaks.append((f"required_field:{x}", f"manifest field {x} became required, so older manifests are refused"))
    for p in sorted(set(old["permissions"]) & set(new["permissions"])):
        a, b = old["permissions"][p], new["permissions"][p]
        if a["scope"] != b["scope"]:
            breaks.append((f"permission:{p}", f"permission {p} now gives key scope {b['scope']}, not {a['scope']}"))
    for x in sorted(set(old["events"]) & set(new["events"])):
        if old["events"][x] != new["events"][x]:
            breaks.append((f"event:{x}", f"event {x} now needs {new['events'][x]}, not {old['events'][x]}"))
    sets("route", old["routes"], new["routes"])
    for r in sorted(set(old["routes"]) & set(new["routes"])):
        a, b = old["routes"][r], new["routes"][r]
        for f in sorted(set(a["answer"]) - set(b["answer"])):
            breaks.append((f"field:{r}:{f}", f"{r} no longer answers {f}"))
        for f in sorted(set(b["answer"]) - set(a["answer"])):
            adds.append(f"{r} answers a new field {f}")
        for k in ("scope", "right"):
            if a[k] != b[k]:
                breaks.append((f"{k}:{r}", f"{r} changed its {k} from {a[k]} to {b[k]}"))
        for f in sorted(set(b["required_in"]) - set(a["required_in"])):
            breaks.append((f"required:{r}:{f}", f"{r} now requires {f}"))
    return breaks, adds


def allowed(item, entries, today, api_major):
    """(True/False, why): a break is allowed only through the deprecation steps."""
    for e in entries:
        if e["item"] == item or item.startswith(e["item"] + ":"):
            if e.get("security"):
                return True, "security exception, noticed on " + e.get("announced", "?")
            if api_major < 2:
                return False, f"listed as deprecated, but removal waits for API 2.0 (not before {e['remove_not_before']})"
            if today < dt.date.fromisoformat(e["remove_not_before"]):
                return False, f"notice runs until {e['remove_not_before']}"
            return True, "notice has run out"
    return False, "not listed in tests/compat/deprecations.json"


def check(today=None):
    today = today or dt.date.today()
    old = json.load(open(BASE, encoding="utf-8"))
    new = surface()
    entries = json.load(open(DEPRECATIONS))["items"] if os.path.exists(DEPRECATIONS) else []
    major = int(plugins.API_VERSION.split(".")[0])
    breaks, adds = compare(old, new)
    bad = []
    for item, sentence in breaks:
        ok, why = allowed(item, entries, today, major)
        if not ok:
            bad.append(f"{sentence}: {why}")
    return bad, adds


def run_frozen():
    """Every frozen manifest must pass Starboard's own manifest check and the plug-in tester without errors."""
    rows = []
    for f in sorted(glob.glob(os.path.join(FROZEN, "*.json"))):
        m = json.load(open(f, encoding="utf-8"))
        problems = plugins.check(m, dev=True)  # dev: older versions named images by tag, as they were before the digest rule
        errors = [i for i in plugin_tester.run(m, dev=True) if i["severity"] == "error"]
        rows.append((os.path.basename(f), m.get("starboard_api"), problems, [e["what"] for e in errors]))
    return rows


def uses(m, item):
    kind, _, name = item.partition(":")
    cs = [c for c in m.get("containers") or [] if isinstance(c, dict)]
    if kind == "permission":
        return name in (m.get("permissions") or [])
    if kind == "manifest_fields":
        return name in m
    if kind == "card":
        return any(isinstance(c, dict) and c.get("type") == name for c in m.get("cards") or [])
    if kind == "setting":
        return any(isinstance(c, dict) and c.get("type") == name for c in m.get("settings") or [])
    if kind == "event":
        return name in (m.get("events") or [])
    if kind == "container_field":
        return any(name in c for c in cs)
    return False


def rehearse(item, newest_only=True):
    """Which manifests use `item`. Plain words for how each would appear to the owner."""
    seen, out = set(), []
    files = sorted(glob.glob(os.path.join(FROZEN, "*.json")))
    for f in files:
        m = json.load(open(f, encoding="utf-8"))
        out.append((m["id"], m["version"], uses(m, item), m.get("name")))
    latest = {}
    for pid, ver, hit, name in out:
        v = tuple(int(x) for x in ver.split("-")[0].split("."))
        if pid not in latest or v > latest[pid][0]:
            latest[pid] = (v, ver, hit, name)
    return [(pid, ver, name) for pid, (v, ver, hit, name) in sorted(latest.items()) if hit], len(latest)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--freeze":
        os.makedirs(os.path.dirname(BASE), exist_ok=True)
        json.dump(surface(), open(BASE, "w", encoding="utf-8"), indent=1, sort_keys=True)
        print("Wrote", BASE)
        return 0
    if argv[0] == "--check":
        bad, adds = check()
        for a in adds:
            print("added:", a)
        for b in bad:
            print("BREAK:", b)
        print(f"{len(bad)} breaking change(s) without the deprecation steps, {len(adds)} addition(s).")
        return 1 if bad else 0
    if argv[0] == "--frozen":
        rows = run_frozen()
        failed = [r for r in rows if r[2] or r[3]]
        for name, api, problems, errors in failed:
            print("FAILS:", name, api, problems or errors)
        print(f"{len(rows)} frozen manifests, {len(failed)} fail.")
        return 1 if failed else 0
    if argv[0] == "--rehearse" and len(argv) == 2:
        hit, total = rehearse(argv[1])
        print(f"If {argv[1]} were removed, {len(hit)} of {total} plug-ins (newest frozen version of each) would stop:")
        for pid, ver, name in hit:
            print(f"  {name} {ver}: Needs an update. It uses {argv[1].split(':', 1)[1]}, which this Starboard no longer has. "
                  "It stays installed and stopped; its settings and data are kept.")
        return 0
    if argv[0] == "--usage" and len(argv) == 2:  # who still uses what is going (DASH-603); argv[1] is Starboard's data folder
        from starboard import deprecations, plugins_admin
        print(f"{len(deprecations.items())} feature(s) going.")
        for r in deprecations.routes_in_use(argv[1]):
            print(f"  route {r['route']}: {r['calls']} call(s) from key {r['key']}, last {r['last']}")
        for p in plugins_admin.basics(argv[1]):
            m = plugins_admin._read_kept(os.path.join(plugins_admin.folder(argv[1], p["id"]), "manifest.json"), {})
            for w in deprecations.for_manifest(m):
                print(f"  plug-in {p['name']}: {deprecations.warning_sentence(w)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
