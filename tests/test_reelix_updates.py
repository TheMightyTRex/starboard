"""Automatic Reelix updates, with a way back (DASH-263)."""
import unittest
from unittest import mock

from starboard import reelix_updates

CFG = mock.Mock(data={"services": [{"id": "rx", "type": "link", "icon": "reelix", "url": "http://127.0.0.1:7700", "name": "Reelix"}]})
C = {"name": "reelix", "image_id": "sha256:old", "image": "ghcr.io/themightytrex/reelix:lite", "folder": "/srv/stack", "project": "media-stack",
     "files": ["/srv/stack/compose.yaml"]}


class AutoUpdate(unittest.TestCase):
    def patches(self, update, healthy):
        p = [mock.patch("starboard.containers.available", return_value=True),
             mock.patch("starboard.containers.containers", return_value=[C]),
             mock.patch("starboard.containers.check", return_value={"items": [{"id": "rx", "update": update}]}),
             mock.patch("starboard.containers.update"), mock.patch("starboard.containers.job", return_value={"finished": True}),
             mock.patch("starboard.containers._helper", return_value=(0, "")), mock.patch("starboard.containers.docker"),
             mock.patch("starboard.containers.forget_old"), mock.patch("starboard.stack.reelix_url", return_value="http://127.0.0.1:7700"),
             mock.patch.object(reelix_updates, "_healthy", return_value=healthy)]
        return [x.start() for x in p], p

    def tearDown(self):
        mock.patch.stopall()

    def test_up_to_date_does_nothing(self):
        (_, _, _, update, *_), _ = self.patches(False, True)
        self.assertEqual(reelix_updates.run(CFG, "/data"), "Reelix is up to date")
        update.assert_not_called()

    def test_healthy_keeps_the_new_one(self):
        m, _ = self.patches(True, True)
        self.assertIn("healthy", reelix_updates.run(CFG, "/data"))
        m[3].assert_called_once_with(CFG.data["services"], ["rx"], keep_old=True)
        self.assertIn("reelix-before-update.tgz", m[5].call_args_list[0][0][1])  # settings saved first
        m[7].assert_called_once_with("sha256:old")

    def test_not_healthy_goes_back(self):
        m, _ = self.patches(True, False)
        self.assertIn("went back", reelix_updates.run(CFG, "/data"))
        tag = m[6].call_args[0][1]
        self.assertTrue(tag.startswith("/images/sha256:old/tag?repo=ghcr.io/themightytrex/reelix&tag=lite"))
        self.assertIn("up -d reelix", m[5].call_args_list[-1][0][1])


if __name__ == "__main__":
    unittest.main()
