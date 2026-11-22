"""The developer help stays in step with the code (DASH-150, DASH-275): every field the plug-in check accepts, and every
property of the manifest's JSON Schema, is named in the manifest reference; and every route in the API description has
its section in the API reference (tools/make_api_reference.py makes that page, so it checks itself)."""
import json
import pathlib
import re
import unittest

from starboard import plugins

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEV = ROOT / "docs" / "help" / "developers"


def schema_keys(node, out):
    """Every property name in the schema, wherever it is."""
    if isinstance(node, dict):
        for k, v in node.get("properties", {}).items():
            out.add(k)
            schema_keys(v, out)
        for k, v in node.items():
            if k != "properties":
                schema_keys(v, out)
    elif isinstance(node, list):
        for v in node:
            schema_keys(v, out)
    return out


class ManifestReference(unittest.TestCase):
    def setUp(self):
        self.doc = (DEV / "plugin-manifest-reference.md").read_text()

    def named(self, key):
        # in a code span, alone or inside an example such as `{"path": "/update/before", "time_limit_seconds": 60}`
        return re.search(r"`[^`\n]*\b" + re.escape(key) + r"\b[^`\n]*`", self.doc) is not None

    def test_every_field_the_check_accepts_is_in_the_reference(self):
        for name in ("TOP", "CONTAINER", "CARD", "ACTION", "SETTING", "JOB", "CHANGE", "JELLYFIN_LIBRARY"):
            for key in getattr(plugins, name):
                self.assertTrue(self.named(key), f"{name}: {key} is not in plugin-manifest-reference.md")

    def test_every_schema_property_is_in_the_reference(self):
        schema = json.loads((ROOT / "starboard" / "plugin-manifest.schema.json").read_text())
        for key in sorted(schema_keys(schema, set())):
            self.assertTrue(self.named(key), f"schema property {key} is not in plugin-manifest-reference.md")

    def test_the_pages_name_the_current_plug_in_api(self):
        have = re.search(r'^API_VERSION = "(\d+\.\d+)', (ROOT / "starboard" / "plugins.py").read_text(), re.M).group(1)
        self.assertIn(f"plug-in API {have}", self.doc)


class ApiReference(unittest.TestCase):
    def test_every_route_has_its_section(self):
        spec = json.loads((ROOT / "starboard" / "openapi.json").read_text())
        page = (DEV / "api-reference.md").read_text()
        for path, ops in spec["paths"].items():
            for method in ops:
                if method in ("get", "post", "put", "patch", "delete"):
                    self.assertIn(f"### {method.upper()} {path}", page, f"{method} {path}")


if __name__ == "__main__":
    unittest.main()
