"""The check the Run first window and ./install.sh --start-apps make before starting data/stack/compose.yaml
(starboard/compose_check.py): Starboard's own set-ups pass, anything that would give a container the computer does
not. 7 November 2026."""
import unittest

from starboard import compose_check, stack

ENV = {"CONFIG_DIR": "/srv/config", "DATA_DIR": "/srv/media"}


def svc(name, **extra):
    return {"image": stack.APPS[name]["image"], **extra}


class ComposeCheckTest(unittest.TestCase):
    def check(self, services, env=ENV):
        return compose_check.problems({"services": services}, env)

    def test_starboards_own_apps_pass(self):
        self.assertEqual(self.check({
            "dozzle": svc("dozzle", volumes=[{"type": "bind", "source": "/var/run/docker.sock", "target": "/var/run/docker.sock"}]),
            "gluetun": svc("gluetun", cap_add=["NET_ADMIN"], devices=[{"source": "/dev/net/tun", "target": "/dev/net/tun"}]),
            "jellyfin": svc("jellyfin", volumes=[{"type": "bind", "source": "/srv/config/jellyfin", "target": "/config"},
                                                 {"type": "bind", "source": "/srv/media", "target": "/data"}]),
        }), [])

    def test_a_newer_tag_of_a_catalogue_image_passes_and_another_image_does_not(self):
        self.assertEqual(self.check({"storyarr": {"image": "ghcr.io/themightytrex/storyarr:v9.9.9"}}), [])
        self.assertEqual(self.check({"jellyfin": {"image": "lscr.io/linuxserver/jellyfin@sha256:" + "0" * 64}}), [])
        self.assertTrue(self.check({"storyarr": {"image": "ghcr.io/someone-else/storyarr:v9.9.9"}}))
        self.assertTrue(self.check({"x": {"image": "localhost:5000/thing"}}))

    def test_the_docker_socket_is_refused_for_any_other_app(self):
        found = self.check({"jellyfin": svc("jellyfin", volumes=[{"type": "bind", "source": "/var/run/docker.sock"}])})
        self.assertIn("jellyfin: mounts /var/run/docker.sock, outside the settings and media folders", found)

    def test_system_folders_privileged_host_network_and_unknown_images_are_refused(self):
        found = "\n".join(self.check({
            "a": {"image": "example/miner:1"},
            "jellyfin": svc("jellyfin", privileged=True, network_mode="host", cap_add=["SYS_ADMIN"],
                            devices=["/dev/sda:/dev/sda"], volumes=["/etc:/host-etc"]),
        }))
        for words in ("example/miner:1 is not one Starboard installs", "runs privileged", "network_mode is host",
                      "asks for SYS_ADMIN", "uses the device /dev/sda", "mounts /etc"):
            self.assertIn(words, found)

    def test_a_folder_that_only_starts_with_the_media_folder_is_outside_it(self):
        found = self.check({"jellyfin": svc("jellyfin", volumes=[{"type": "bind", "source": "/srv/media-other"}])})
        self.assertTrue(found)

    def test_a_settings_folder_of_a_whole_home_is_refused(self):
        found = self.check({}, {"CONFIG_DIR": "/home/someone", "DATA_DIR": "/srv/media"})
        self.assertTrue(any(p.startswith("CONFIG_DIR") for p in found))


if __name__ == "__main__":
    unittest.main()
