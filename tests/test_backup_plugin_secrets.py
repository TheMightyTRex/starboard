"""A downloaded settings file never holds a plug-in's keys or secrets (DASH-603, audit F3)."""
import json
import tempfile
import unittest
from unittest import mock

from starboard import backup, plugins_admin as pa
from tests.test_plugins import ON_DEMAND

WITH_SECRET = {**ON_DEMAND, "settings": list(ON_DEMAND.get("settings") or []) + [
    {"key": "token", "label": "Its token", "type": "secret"}, {"key": "address2", "label": "Name", "type": "text"}]}


class Secrets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/{pid}")
        p.start()
        self.addCleanup(p.stop)
        pa.install(self.tmp.name, WITH_SECRET, "/srv/media")
        pa.save_settings(self.tmp.name, "on-demand", {"token": "S3CRET-VALUE", "address2": "plain"})

    def test_the_file_has_no_secret_and_no_key(self):
        out = backup.plugin_settings(self.tmp.name)["on-demand"]
        text = json.dumps(out)
        self.assertNotIn("S3CRET-VALUE", text)
        self.assertNotIn("sb_read_", text)
        self.assertEqual(out["settings"].get("address2"), "plain")
        self.assertEqual(out["secrets_left_out"], ["token"])
        self.assertNotIn("key_id", out["state"])

    def test_restoring_keeps_the_secret_the_plug_in_has(self):
        saved = backup.plugin_settings(self.tmp.name)
        pa.save_settings(self.tmp.name, "on-demand", {"address2": "changed"})
        self.assertEqual(backup.restore_plugin_settings(self.tmp.name, saved), [])
        values = pa._read(pa.folder(self.tmp.name, "on-demand") + "/settings.json", {})
        self.assertEqual((values["token"], values["address2"]), ("S3CRET-VALUE", "plain"))


if __name__ == "__main__":
    unittest.main()
