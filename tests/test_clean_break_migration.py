"""The 0.40.0 settings step (DASH-596): a 0.31.0 settings file moves to schema 5 once, after a copy is saved, and
nothing Starboard does not understand is removed."""
import json
import os
import shutil
import tempfile
import unittest

from starboard import backup, config


def settings_from_0_31_0():
    data = json.loads(json.dumps(config.DEFAULTS))
    data.update(schema=4, site_name="Made-up Media", a_key_from_a_plug_in_or_the_future={"keep": [1, 2, 3]},
                services=[{"id": "sonarr", "name": "Sonarr", "type": "sonarr", "url": "http://sonarr:8989", "api_key": "s" * 32, "group": "Downloads"},
                          {"id": "odd", "name": "Odd one", "type": "a-kind-from-somewhere-else", "url": "http://odd:80", "group": "Tools"}])
    data["auth"] = {"password_hash": "made-up-hash", "session_version": 3}
    return data


class CleanBreakSteps(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, data):
        with open(os.path.join(self.dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_rule_1_a_copy_is_saved_before_the_settings_change(self):
        before = settings_from_0_31_0()
        self.write(before)
        cfg = config.Config(self.dir)
        self.assertEqual(cfg.data["schema"], 5)
        copies = [c for c in backup.saved_copies(cfg) if c["reason"] == "Before an update changed the settings"]
        self.assertEqual(len(copies), 1)
        with open(os.path.join(self.dir, "backups", copies[0]["name"]), encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved.get("settings", saved).get("site_name"), "Made-up Media")  # read back, with the old schema
        self.assertIn(4, [saved.get("schema"), saved.get("settings", {}).get("schema")])

    def test_rule_2_the_step_runs_once(self):
        self.write(settings_from_0_31_0())
        config.Config(self.dir)
        again = config.Config(self.dir)
        self.assertEqual(again.data["schema"], 5)
        self.assertEqual(len([n for n in os.listdir(os.path.join(self.dir, "backups")) if n.startswith("config-")]), 1)  # no second copy: nothing to migrate
        with open(os.path.join(self.dir, "config.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["schema"], 5)

    def test_rule_3_nothing_it_does_not_understand_is_deleted(self):
        self.write(settings_from_0_31_0())
        data = config.Config(self.dir).data
        self.assertEqual(data["a_key_from_a_plug_in_or_the_future"], {"keep": [1, 2, 3]})
        self.assertEqual([(s["id"], s["type"]) for s in data["services"]], [("sonarr", "sonarr"), ("odd", "a-kind-from-somewhere-else")])
        self.assertEqual(data["auth"], {"password_hash": "made-up-hash", "session_version": 3})
        self.assertEqual(data["site_name"], "Made-up Media")
        with open(os.path.join(self.dir, "config.json"), encoding="utf-8") as f:  # and on disk
            on_disk = json.load(f)
        self.assertIn("a_key_from_a_plug_in_or_the_future", on_disk)
        self.assertEqual(len(on_disk["services"]), 2)

    def test_rule_3_a_restore_keeps_an_unknown_kind_as_a_plain_link(self):
        saved = {"format": backup.FORMAT, "version": "0.31.0", "schema": 4, "settings": {"site_name": "Restored"},
                 "services": settings_from_0_31_0()["services"]}
        cfg = config.Config(self.dir)
        self.assertEqual(backup.restore(cfg, saved), 2)
        self.assertEqual([(s["id"], s["type"]) for s in cfg.data["services"]], [("sonarr", "sonarr"), ("odd", "link")])
        self.assertEqual(cfg.data["schema"], 5)

    def test_a_backup_made_now_says_schema_5(self):
        self.assertEqual(backup.export(config.Config(self.dir), "0.40.0")["schema"], 5)


if __name__ == "__main__":
    unittest.main()
