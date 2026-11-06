"""Reelix or Reelix with YouTube and Spotify downloads: the set-ups' choice, and switching either way later (stack)."""
import os
import tempfile
import unittest

from starboard import stack

LITE = stack.REELIX_IMAGE
OFFICIAL, FORK = stack.REELIX_FULL_IMAGES


def registry(public, versions=None):
    """A stand-in for containers.remote: images in `public` answer, others fail as a private package does."""
    def remote(ref):
        if ref not in public:
            raise OSError("401 authentication required")
        return {"digest": "sha256:x", "version": (versions or {}).get(ref, "")}
    return remote


class EditionTest(unittest.TestCase):
    def setUp(self):
        stack._pullable.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.choice = {"apps": ["reelix", "qbittorrent"], "config_dir": "/srv/config", "data_dir": "/srv/media"}

    def tearDown(self):
        self.tmp.cleanup()
        stack._pullable.clear()

    def write(self, edition="lite", check=None):
        import starboard.stack as s
        real = s.reelix_image
        s.reelix_image = lambda e, c=None: real(e, check)
        try:
            built = stack.build({**self.choice, "reelix_edition": edition})
        finally:
            s.reelix_image = real
        stack.write(self.tmp.name, built)
        return built

    def test_lite_is_the_default_and_needs_no_registry(self):
        built = stack.build(self.choice)
        self.assertIn(f"image: {LITE}", built["compose"])

    def test_the_official_image_comes_first(self):
        self.assertEqual(stack.reelix_image("full", registry({OFFICIAL, FORK})), OFFICIAL)

    def test_the_forks_copy_when_the_official_one_is_private(self):
        self.assertEqual(stack.reelix_image("full", registry({FORK})), FORK)

    def test_full_cannot_be_chosen_when_neither_can_be_downloaded(self):
        with self.assertRaises(ValueError) as e:
            stack.reelix_image("full", registry(set()))
        self.assertIn("Choose Reelix for now", str(e.exception))
        editions = {e["key"]: e for e in stack.reelix_editions(registry(set()))}
        self.assertTrue(editions["lite"]["available"] and editions["lite"]["recommended"])
        self.assertFalse(editions["full"]["available"])

    def test_upgrade_then_downgrade_keeps_the_settings_folder(self):
        check = registry({FORK, LITE}, {FORK: "0.8.6", LITE: "0.8.6"})
        self.write("lite", check)
        self.assertEqual(stack.edition_of(stack.reelix_in_stack(self.tmp.name)), "lite")
        old, new = stack.switch_reelix(self.tmp.name, "full", check)
        self.assertEqual((old, new), (LITE, FORK))
        with open(os.path.join(stack.folder(self.tmp.name), "compose.yaml")) as f:
            text = f.read()
        self.assertIn(f"image: {FORK}", text)
        self.assertIn("${CONFIG_DIR}/reelix:/config", text)  # the same settings, so nothing is set up again
        self.assertEqual(stack.edition_of(stack.reelix_in_stack(self.tmp.name)), "full")
        self.assertTrue(any(n.startswith("compose.yaml.before-") for n in os.listdir(stack.folder(self.tmp.name))))
        stack.switch_reelix(self.tmp.name, "lite", check)
        self.assertEqual(stack.reelix_in_stack(self.tmp.name), LITE)

    def test_no_downgrade_to_an_older_version(self):
        self.write("full", registry({FORK}))
        behind = registry({FORK, LITE}, {FORK: "0.9.0", LITE: "0.8.6"})
        with self.assertRaises(ValueError) as e:
            stack.switch_reelix(self.tmp.name, "lite", behind)
        self.assertIn("cannot go back", str(e.exception))
        self.assertEqual(stack.reelix_in_stack(self.tmp.name), FORK)  # nothing changed

    def test_switching_to_the_same_version_says_so(self):
        self.write("lite")
        with self.assertRaises(ValueError):
            stack.switch_reelix(self.tmp.name, "lite")

    def test_a_stack_without_reelix_cannot_switch(self):
        self.choice["apps"] = ["qbittorrent"]
        self.write()
        self.assertIsNone(stack.reelix_in_stack(self.tmp.name))
        with self.assertRaises(ValueError):
            stack.switch_reelix(self.tmp.name, "full", registry({FORK}))


if __name__ == "__main__":
    unittest.main()
