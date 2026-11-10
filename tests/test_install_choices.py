"""Basics, Full install and Everything, and the apps each app needs (stack.INSTALLS, stack.NEEDS, stack.with_needs).
The three installs come from the owner's install choices page (7 November 2026)."""
import unittest

from starboard import stack


def downloadable(_ref):
    return {"digest": "sha256:x", "version": ""}


def private(_ref):
    raise OSError("401")


class InstallChoicesTest(unittest.TestCase):
    def setUp(self):
        stack._pullable.clear()

    def tearDown(self):
        stack._pullable.clear()

    def test_basics_is_reelix_lite_with_what_the_owner_chose(self):
        c = stack.install_choice("basics", check=downloadable)
        self.assertEqual(c["reelix_edition"], "lite")
        self.assertFalse(c["disk_health"])
        self.assertEqual(sorted(c["apps"]), sorted(["reelix", "qbittorrent", "jellyfin", "audiobookshelf", "bazarr",
                                                    "gluetun", "nzbget"]))

    def test_full_is_the_full_reelix_with_more(self):
        c = stack.install_choice("full", check=downloadable)
        self.assertEqual(c["reelix_edition"], "full")
        self.assertTrue(c["disk_health"])
        for k in ("flaresolverr", "jellystat", "dozzle", "tdarr"):
            self.assertIn(k, c["apps"])
        for k in ("wizarr", "dispatcharr"):  # add-ons since 9 November 2026 (DASH-222, DASH-230)
            self.assertNotIn(k, c["apps"])
        self.assertNotIn("storyarr", c["apps"])
        self.assertNotIn("kapowarr", c["apps"])

    def test_graphics_chip_goes_to_jellyfin_and_comes_back(self):
        import os
        import tempfile
        c = {"apps": ["jellyfin"], "config_dir": "/srv/config", "data_dir": "/srv/media", "graphics": {"vendor": "intel", "gid": 993}}
        built = stack.build(c)
        self.assertIn('      - "/dev/dri:/dev/dri"', built["compose"])
        self.assertIn('    group_add:\n      - "${RENDER_GID}"', built["compose"])
        self.assertIn("RENDER_GID=993", built["env"])
        self.assertIn("GRAPHICS_VENDOR=intel", built["env"])
        self.assertNotIn("/dev/dri", stack.build({**c, "graphics": None})["compose"])
        with tempfile.TemporaryDirectory() as d:
            node, sys_root = os.path.join(d, "renderD128"), os.path.join(d, "sys")
            self.assertIsNone(stack.graphics_chip(node, sys_root=sys_root))
            open(node, "w").close()
            self.assertEqual(stack.graphics_chip(node, sys_root=sys_root)["vendor"], "other")
            os.makedirs(os.path.join(sys_root, "renderD128", "device"))
            with open(os.path.join(sys_root, "renderD128", "device", "vendor"), "w") as f:
                f.write("0x8086\n")
            self.assertEqual(stack.graphics_chip(node, sys_root=sys_root), {"vendor": "intel", "gid": os.stat(node).st_gid})

    def test_everything_is_every_app_offered(self):
        c = stack.install_choice("all", check=downloadable)
        self.assertEqual(sorted(c["apps"]), sorted(k for k in stack.offered() if k != "sabnzbd"))  # one Usenet app
        self.assertNotIn("radarr", c["apps"])  # Reelix replaces it

    def test_full_falls_back_to_lite_when_the_full_reelix_cannot_be_downloaded(self):
        c = stack.install_choice("full", check=private)
        self.assertEqual(c["reelix_edition"], "lite")
        self.assertIn("Reelix Lite", c["note"])

    def test_apps_already_running_are_left_out(self):
        c = stack.install_choice("basics", installed_keys={"jellyfin"}, check=downloadable)
        self.assertNotIn("jellyfin", c["apps"])

    def test_nzbget_is_the_usenet_app_and_sabnzbd_a_choice_in_full_and_everything(self):
        for key in ("full", "all"):
            c = stack.install_choice(key, check=downloadable, usenet="sabnzbd")
            self.assertIn("sabnzbd", c["apps"])
            self.assertNotIn("nzbget", c["apps"])
        basics = stack.install_choice("basics", check=downloadable, usenet="sabnzbd")
        self.assertEqual((basics["usenet"], "nzbget" in basics["apps"]), ("nzbget", True))  # no choice in Basics

    def test_made_up_passwords_are_kept_when_the_files_are_written_again(self):
        import tempfile
        d = tempfile.mkdtemp()
        choice = {"apps": ["nzbget", "storyarr"], "config_dir": "/srv/config", "data_dir": "/srv/media"}
        stack.write(d, stack.build(choice))
        first = stack.env_values(d)
        stack.write(d, stack.build(choice))
        again = stack.env_values(d)
        self.assertEqual(first["NZBGET_PASS"], again["NZBGET_PASS"])
        self.assertEqual(first["STORYARR_DB_PASSWORD"], again["STORYARR_DB_PASSWORD"])
        self.assertEqual(stack.nzbget_key(d), "starboard:" + first["NZBGET_PASS"])

    def test_an_install_is_recognised_from_its_apps_and_a_change_is_planned(self):
        import tempfile
        d = tempfile.mkdtemp()
        c = stack.install_choice("basics", check=downloadable)
        stack.write(d, stack.build({"apps": c["apps"], "config_dir": "/srv/config", "data_dir": "/srv/media",
                                    "vpn": {"provider": "mullvad", "type": "wireguard", "wireguard_private_key": "made-up",
                                            "wireguard_addresses": "192.168.1.20/32"}}))
        now = stack.current_choice(d)
        self.assertEqual(stack.which_install(now["apps"]), "basics")
        self.assertEqual(now["vpn"]["provider"], "mullvad")  # read back, so a rebuild keeps it
        up = stack.plan_change(d, install="full", check=downloadable)
        self.assertIn("tdarr", up["add"])
        self.assertEqual(up["remove"], [])
        self.assertEqual(up["choice"]["reelix_edition"], "full")
        swap = stack.plan_change(d, usenet="sabnzbd", check=downloadable)
        self.assertEqual((swap["add"], swap["remove"], swap["usenet"]), (["sabnzbd"], ["nzbget"], ("nzbget", "sabnzbd")))
        stack.write(d, stack.build(up["choice"]))
        down = stack.plan_change(d, install="basics", check=downloadable)
        self.assertIn("tdarr", down["remove"])
        self.assertEqual(down["choice"]["reelix_edition"], "lite")

    def test_needs_are_added(self):
        keys, added = stack.with_needs(["jellystat", "bazarr"])
        self.assertEqual(set(added), {"jellyfin", "reelix", "qbittorrent"})  # Reelix needs a download app
        self.assertIn("jellystat", keys)

    def test_one_of_is_satisfied_by_either(self):
        keys, added = stack.with_needs(["reelix", "sabnzbd"])
        self.assertEqual(added, [])
        self.assertNotIn("qbittorrent", keys)

    def test_build_adds_what_is_needed_and_databases_come_with_their_app(self):
        built = stack.build({"apps": ["wizarr", "jellystat"], "config_dir": "/srv/config", "data_dir": "/srv/media"})
        self.assertIn("container_name: jellyfin", built["compose"])
        self.assertIn("container_name: jellystat-db", built["compose"])

    def test_every_need_names_an_app(self):
        for app, needs in stack.NEEDS.items():
            self.assertIn(app, stack.APPS)
            for n in needs:
                for k in (n if isinstance(n, tuple) else (n,)):
                    self.assertIn(k, stack.APPS)

    def test_the_catalogue_lists_the_installs_and_needs(self):
        c = stack.catalogue(set())
        self.assertEqual([i["key"] for i in c["installs"]], ["basics", "full", "all"])
        self.assertTrue(c["installs"][0]["recommended"])
        self.assertEqual(c["needs"]["reelix"], [["qbittorrent", "nzbget", "sabnzbd"]])


if __name__ == "__main__":
    unittest.main()
