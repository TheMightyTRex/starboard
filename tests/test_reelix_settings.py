"""Keeps the set-ups in step with Reelix (plan section 4, DASH-154).

tests/reelix/wizard-settings.json lists every Reelix setting Starboard knows: each provider's fields from
/{kind}/schema and each settings route's fields. Each says what the set-ups do with it: "asked" (the step that asks
it), "default" (set without asking, and why) or "later" (left to Settings, Reelix).

Always, without Reelix:
- every entry is decided (no "undecided"), and Starboard's own sites list (reelix_sites.SUGGESTED) is in it;
- every field Starboard's set-up code sets (the "settings" dictionaries in reelix_setup.py and reelix_sites.py, read
  from the code itself) is in the list as asked or default, so the list and the set-ups cannot drift apart.

Against a real Reelix (STARBOARD_REELIX_LIVE=1, Docker, the throwaway container "starboard-settings-test" on port
STARBOARD_REELIX_PORT, 18809 unless set; or an existing throwaway one: STARBOARD_REELIX_URL and
STARBOARD_REELIX_PASSWORD): fails when Reelix has a setting the list does not, the list names one Reelix no longer has,
or a setting's kind of value or choices changed. The message names the setting, its kind and the route. The fix is to
decide asked, default or later (and to change the set-up step when asked):
    python3 tests/test_reelix_settings.py --write URL PASSWORD   (keeps every decision, adds new ones as undecided)
Run before every release, and weekly against Reelix's newest image.
"""
import ast
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from starboard import reelix_setup, reelix_sites  # noqa: E402

LIST = REPO / "tests" / "reelix" / "wizard-settings.json"
KINDS = ["indexers", "downloadclients", "mediaservers", "notifications", "importlists"]
USES = {"asked", "default", "later"}


def load():
    with open(LIST, encoding="utf-8") as f:
        return json.load(f)


def json_kind(v):
    return {bool: "bool", int: "number", float: "number", str: "text", list: "list", dict: "object", type(None): "empty"}[type(v)]


def tracked(kind, impl):
    """Indexers: the built-in kinds and the sites the set-ups offer; Reelix's other 500 or so sites are left to
    Settings, Reelix as a whole. Every implementation of the other kinds."""
    return kind != "indexers" or not impl.startswith("definition:") or impl in reelix_sites.SUGGESTED_IDS


def read_reelix(base, password):
    """What this Reelix has: {"providers": {kind: {impl: {field: {type, choices?}}}}, "settings": {route: {field: {type}}},
    "version": ...}."""
    s = reelix_setup.Session(base)
    s.call("POST", "/auth/login", {"username": "admin", "password": password, "remember_me": False})
    out = {"providers": {}, "settings": {}}
    for kind in KINDS:
        _, schemas = s.call("GET", f"/{kind}/schema", timeout=60)
        out["providers"][kind] = {}
        for e in schemas or []:
            sch = e.get("schema") or {}
            if not tracked(kind, sch.get("implementation", "")):
                continue
            fields = {}
            for f in sch.get("fields") or []:
                d = {"type": f.get("type")}
                if f.get("options"):
                    d["choices"] = sorted(str(o.get("value")) for o in f["options"])
                fields[f["name"]] = d
            out["providers"][kind][sch["implementation"]] = fields
    _, api = s.call("GET", "/openapi.json")
    routes = sorted(p[len("/api/v1"):] for p, ops in api["paths"].items()
                    if "get" in ops and "put" in ops and re.search(r"/settings$|^/api/v1/settings/[a-z]+$", p) and "{" not in p)
    for route in routes:
        try:
            _, values = s.call("GET", route)
        except reelix_setup.ReelixError:
            continue
        if isinstance(values, dict):
            out["settings"][route] = {k: {"type": json_kind(v)} for k, v in values.items()}
    _, status = s.call("GET", "/system/status")
    out["version"] = (status or {}).get("version")
    s.call("POST", "/auth/logout", ok=(200, 204))
    return out


def differences(listed, live):
    """Every difference, in words that name the setting, its kind and the route."""
    problems = []
    for section, route_of in (("providers", lambda k, i: f"/api/v1/{k}/schema, {i}"), ("settings", lambda r, _: f"/api/v1{r}")):
        for group in sorted(set(listed[section]) | set(live[section])):
            have, now = listed[section].get(group, {}), live[section].get(group)
            if now is None:
                problems.append(f"The list has {group}, which this Reelix no longer has ({section})")
                continue
            if section == "settings":
                have, now = {"": have}, {"": now}
            for impl in sorted(set(have) | set(now)):
                a, b = have.get(impl), now.get(impl)
                where = route_of(group, impl) if section == "providers" else route_of(group, None)
                if a is None:
                    problems.append(f"Reelix has {impl or group}, which the list does not have ({where}): decide asked, default or later")
                    continue
                if b is None:
                    problems.append(f"The list has {impl}, which Reelix no longer has ({where})")
                    continue
                for name in sorted(set(a) | set(b)):
                    if name not in a:
                        problems.append(f"New Reelix setting {name} ({b[name]['type']}) at {where}: decide asked, default or later")
                    elif name not in b:
                        problems.append(f"Reelix no longer has {name} ({a[name]['type']}) at {where}")
                    elif a[name]["type"] != b[name]["type"] or a[name].get("choices") != b[name].get("choices"):
                        problems.append(f"{name} at {where} changed from {a[name]['type']} {a[name].get('choices') or ''} "
                                        f"to {b[name]['type']} {b[name].get('choices') or ''}".replace("  ", " "))
    return problems


def merge(listed, live):
    """The live settings with the list's decisions kept; anything new is undecided."""
    out = {k: v for k, v in listed.items() if k not in ("providers", "settings")}
    out["tested_with"] = live.get("version") or listed.get("tested_with")
    for section in ("providers", "settings"):
        out[section] = {}
        for group, items in live[section].items():
            old = listed.get(section, {}).get(group, {})
            if section == "settings":
                out[section][group] = {n: {**d, **{k: v for k, v in old.get(n, {}).items() if k not in ("type", "choices")}}
                                       for n, d in items.items()}
                for d in out[section][group].values():
                    d.setdefault("use", "undecided")
                continue
            out[section][group] = {}
            for impl, fields in items.items():
                o = old.get(impl, {})
                out[section][group][impl] = {n: {**d, **{k: v for k, v in o.get(n, {}).items() if k not in ("type", "choices")}}
                                             for n, d in fields.items()}
                for d in out[section][group][impl].values():
                    d.setdefault("use", "undecided")
    return out


def code_sets():
    """Every (implementation, field) Starboard's set-up code puts in a provider's settings: the dictionaries next to
    "implementation" in reelix_setup.py and reelix_sites.py, and the variables those take their settings from."""
    found = set()
    for module in ("reelix_setup.py", "reelix_sites.py"):
        tree = ast.parse((REPO / "starboard" / module).read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = [k.value if isinstance(k, ast.Constant) else None for k in node.keys]
            if "implementation" not in keys or "settings" not in keys:
                continue
            impl = node.values[keys.index("implementation")]
            settings = node.values[keys.index("settings")]
            impls = [impl.value] if isinstance(impl, ast.Constant) else []
            names = [k.value for k in getattr(settings, "keys", []) if isinstance(k, ast.Constant)]
            for i in impls:
                found |= {(i, n) for n in names}
    # Variables built before the call: the media servers' and your own site's settings.
    for kind in reelix_sites.MEDIA_SERVERS:
        found |= {(kind, "url"), (kind, "api_key")}
    for kind in reelix_sites.OWN_KINDS:
        found |= {(kind, "base_url"), (kind, "api_key")}
    return found


class ListTest(unittest.TestCase):
    def setUp(self):
        self.listed = load()

    def entries(self):
        for kind, impls in self.listed["providers"].items():
            for impl, fields in impls.items():
                for name, d in fields.items():
                    yield f"{kind} {impl} {name}", d
        for route, fields in self.listed["settings"].items():
            for name, d in fields.items():
                yield f"{route} {name}", d

    def test_every_setting_is_decided(self):
        undecided = [where for where, d in self.entries() if d.get("use") not in USES]
        self.assertEqual(undecided, [], "Decide asked, default or later for each of these")
        for where, d in self.entries():
            if d["use"] == "asked":
                self.assertTrue(d.get("step"), f"{where} is asked: name the step that asks it")
            if d["use"] == "default":
                self.assertTrue(d.get("why"), f"{where} is set without asking: say why")

    def test_the_sites_the_set_ups_offer_are_in_the_list(self):
        for impl, name, _ in reelix_sites.SUGGESTED:
            self.assertIn(impl, self.listed["providers"]["indexers"], f"{name} is offered by the set-ups but not in the list")

    def test_what_the_set_up_code_sets_is_in_the_list(self):
        providers = {}
        for impls in self.listed["providers"].values():  # an implementation can be in two kinds (Jellyfin)
            for impl, fields in impls.items():
                providers.setdefault(impl, []).append(fields)
        for impl, name in sorted(code_sets()):
            self.assertIn(impl, providers, f"The set-up sets {impl}, which the list does not have")
            uses = [fields[name]["use"] for fields in providers[impl] if name in fields]
            self.assertTrue(uses, f"The set-up sets {name} on {impl}, which the list does not have")
            self.assertTrue(set(uses) & {"asked", "default"},
                            f"The set-up sets {name} on {impl}, so the list must say asked or default, not later")
        search = self.listed["settings"]["/settings/indexers"]
        for name in ("proxy", "allow_private_addresses", "flaresolverr_url"):
            self.assertEqual(search[name]["use"], "default", f"Searches through the VPN set {name}")


class DifferencesTest(unittest.TestCase):
    def test_new_gone_and_changed_settings_are_named_with_their_route(self):
        listed = {"providers": {"indexers": {"torznab": {"base_url": {"type": "url", "use": "asked", "step": "sites"},
                                                         "old": {"type": "text", "use": "later"},
                                                         "sort": {"type": "select", "choices": ["a"], "use": "later"}}}},
                  "settings": {"/settings/naming": {"rename": {"type": "bool", "use": "later"}}}}
        live = {"providers": {"indexers": {"torznab": {"base_url": {"type": "url"}, "pace": {"type": "select", "choices": ["light"]},
                                                       "sort": {"type": "select", "choices": ["a", "b"]}}}},
                "settings": {"/settings/naming": {"rename": {"type": "bool"}}, "/system/background-work": {"pace": {"type": "text"}}}}
        problems = differences(listed, live)
        self.assertTrue(any("New Reelix setting pace (select) at /api/v1/indexers/schema, torznab" in p for p in problems), problems)
        self.assertTrue(any("Reelix no longer has old (text)" in p for p in problems), problems)
        self.assertTrue(any("sort at /api/v1/indexers/schema, torznab changed" in p for p in problems), problems)
        self.assertTrue(any("/system/background-work" in p and "decide asked, default or later" in p for p in problems), problems)
        merged = merge(listed, live)
        self.assertEqual(merged["providers"]["indexers"]["torznab"]["base_url"]["use"], "asked")  # decisions kept
        self.assertEqual(merged["providers"]["indexers"]["torznab"]["pace"]["use"], "undecided")


@unittest.skipUnless(os.environ.get("STARBOARD_REELIX_LIVE") == "1" or os.environ.get("STARBOARD_REELIX_URL"),
                     "needs a throwaway Reelix: STARBOARD_REELIX_LIVE=1, or STARBOARD_REELIX_URL and STARBOARD_REELIX_PASSWORD")
class LiveTest(unittest.TestCase):
    NAME = "starboard-settings-test"

    @classmethod
    def setUpClass(cls):
        cls.base = os.environ.get("STARBOARD_REELIX_URL")
        cls.password = os.environ.get("STARBOARD_REELIX_PASSWORD", "")
        cls.started = False
        if cls.base:
            return
        port = os.environ.get("STARBOARD_REELIX_PORT", "18809")
        image = os.environ.get("STARBOARD_REELIX_IMAGE", load()["image"])
        subprocess.run(["docker", "rm", "-f", cls.NAME], capture_output=True)  # nosec B603 B607: our own throwaway container
        subprocess.run(["docker", "run", "-d", "--name", cls.NAME, "-p", f"127.0.0.1:{port}:7700", "--tmpfs", "/config",  # nosec
                        "-e", "REELIX_WEB_DIR=/tmp", image], check=True, capture_output=True)
        cls.started = True
        cls.base = f"http://127.0.0.1:{port}"
        reelix_setup.wait_until_up(cls.base, seconds=120)
        token = None
        for _ in range(30):
            logs = subprocess.run(["docker", "logs", cls.NAME], capture_output=True, text=True)  # nosec B603 B607
            m = re.findall(r"setup token: ([A-Za-z0-9_-]{8,})", logs.stdout + logs.stderr)
            if m:
                token = m[-1]
                break
            time.sleep(2)
        cls.password = secrets.token_urlsafe(16)
        reelix_setup.Session(cls.base).call("POST", "/setup", {"username": "admin", "password": cls.password, "setup_token": token})
        # Reelix downloads its list of sites at start: wait for it (up to 3 minutes).
        s = reelix_setup.Session(cls.base)
        s.call("POST", "/auth/login", {"username": "admin", "password": cls.password, "remember_me": False})
        for _ in range(90):
            _, status = s.call("GET", "/indexers/definitions/status")
            if (status or {}).get("loaded") and not status.get("syncing"):
                break
            time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        if cls.started:
            subprocess.run(["docker", "rm", "-f", cls.NAME], capture_output=True)  # nosec B603 B607

    def test_the_list_matches_this_reelix(self):
        live = read_reelix(self.base, self.password)
        problems = differences(load(), live)
        self.assertEqual(problems, [], f"Reelix {live.get('version')} and tests/reelix/wizard-settings.json differ")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--write":
        listed = load() if LIST.exists() else {"providers": {}, "settings": {}}
        merged = merge(listed, read_reelix(sys.argv[2], sys.argv[3]))
        LIST.parent.mkdir(exist_ok=True)
        LIST.write_text(json.dumps(merged, indent=1, sort_keys=False) + "\n")
        print(f"Written {LIST}. Decide every undecided entry.")
    else:
        unittest.main()
