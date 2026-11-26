"""Plex and Emby installable from Starboard beside Jellyfin (DASH-566, owner, 26 November 2026): own ports and folders, the
media folder read only, a cap on memory and processors, not part of Basics or Full install, and a guided step each."""
import os
import re
import unittest
from unittest import mock

from starboard import setup_left, stack

CHOICE = {"apps": ["jellyfin", "plex", "emby"], "config_dir": "/srv/cfg", "data_dir": "/srv/data", "puid": 1000, "pgid": 1000, "tz": "Etc/UTC"}


def service(compose, name):
    """One service's lines of the Compose file."""
    return re.split(r"\n  (?=[a-z-]+:\n)", compose.split(f"\n  {name}:\n", 1)[1], maxsplit=1)[0]


class Install(unittest.TestCase):
    def build(self, **over):
        with mock.patch.object(stack, "_port_free", return_value=True):
            return stack.build({**CHOICE, **over})

    def test_each_has_its_own_port_and_folders_and_the_media_folder_read_only(self):
        c = self.build()["compose"]
        jelly, plex, emby = (service(c, n) for n in ("jellyfin", "plex", "emby"))
        self.assertIn('"8096:8096"', jelly)
        self.assertIn('"32400:32400"', plex)
        self.assertIn('"8097:8096"', emby)  # Jellyfin has 8096 on this computer
        self.assertIn('"${CONFIG_DIR}/plex:/config"', plex)
        self.assertIn('"${CONFIG_DIR}/emby:/config"', emby)
        for one in (plex, emby):
            self.assertIn('"${DATA_DIR}/media:/data/media:ro"', one)
            self.assertNotIn("${DATA_DIR}:", one)  # never the whole data folder, with downloads in it

    def test_a_cap_on_memory_and_processors_that_this_computer_can_meet(self):
        c = self.build()["compose"]
        for name in ("plex", "emby"):
            one = service(c, name)
            self.assertIn("mem_limit: 2g", one)
            cpus = int(re.search(r"cpus: (\d+)", one).group(1))
            self.assertTrue(1 <= cpus <= (os.cpu_count() or 1) and cpus <= 4)
        with mock.patch("os.cpu_count", return_value=2):
            self.assertIn("cpus: 2", service(self.build()["compose"], "plex"))
        self.assertNotIn("mem_limit", service(c, "jellyfin"))  # only what asked for a cap has one

    def test_a_port_that_is_taken_moves_on_and_is_said(self):
        with mock.patch.object(stack, "_port_free", side_effect=lambda p: p != 32400):
            b = stack.build(CHOICE)
        self.assertIn('"32401:32400"', service(b["compose"], "plex"))
        self.assertTrue(any("Plex uses port 32401" in m for m in b["moved"]))

    def test_the_claim_is_left_blank_for_the_person_and_nothing_is_made_up(self):
        b = self.build()
        self.assertIn('PLEX_CLAIM: "${PLEX_CLAIM:-}"', b["compose"])
        self.assertNotIn("PLEX_CLAIM", b["env"])

    def test_neither_is_ticked_by_default_nor_in_basics_or_full_install(self):
        for key in ("plex", "emby"):
            self.assertIs(stack.APPS[key].get("default"), False)
            self.assertNotIn(key, stack.INSTALLS["basics"]["apps"])
            self.assertNotIn(key, stack.INSTALLS["full"]["apps"])
            self.assertIn(key, stack.offered())
            self.assertIn("watching", stack.APPS[key]["groups"])

    def test_each_has_a_guided_step_that_says_what_starboard_cannot_do(self):
        steps = {k: (t, why) for k, t, why in setup_left.GUIDED}
        self.assertIn("Plex account", steps["plex"][1])
        self.assertIn("cannot make or enter it for you", steps["plex"][1])
        self.assertIn("first-run steps", steps["emby"][1])

    def test_discovery_adds_them_to_manage_apps_as_their_own_types(self):
        from starboard import discovery
        self.assertEqual((discovery.CATALOGUE["plex"][1], discovery.CATALOGUE["emby"][1]), ("plex", "emby"))
        self.assertTrue({"plex", "emby"} <= set(discovery.CATALOGUE))


if __name__ == "__main__":
    unittest.main()
