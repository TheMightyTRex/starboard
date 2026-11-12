"""Plug-in API 1.5 (DASH-307): a setting's group, and choices with words."""
import copy
import tempfile
import unittest
from unittest import mock

from starboard import plugins, plugins_admin as pa
from tests.test_plugins import ON_DEMAND


def manifest():
    m = copy.deepcopy(ON_DEMAND)
    m["settings"] = [
        {"key": "lang", "label": "Audio language", "type": "choice", "group": "Picture and sound", "default": "eng",
         "choices": [{"value": "eng", "label": "English"}, {"value": "fre", "label": "French"}]},
        {"key": "quality", "label": "Picture quality", "type": "choice", "choices": ["4K", "1080p"], "default": "1080p"},
    ]
    return m


class Groups(unittest.TestCase):
    def test_group_and_labelled_choices_pass(self):
        self.assertEqual([p for p in plugins.check(manifest()) if "settings" in p], [])

    def test_bad_group_and_choices_are_refused(self):
        m = manifest()
        m["settings"][0]["group"] = "x" * 41
        m["settings"][1]["choices"] = [{"value": "4K"}]
        problems = " ".join(plugins.check(m))
        self.assertIn("group must be text of up to 40 characters", problems)
        self.assertIn("choices must be a list", problems)

    def test_choices_give_value_and_words(self):
        s = manifest()["settings"]
        self.assertEqual(plugins.choices(s[0]), [("eng", "English"), ("fre", "French")])
        self.assertEqual(plugins.choices(s[1]), [("4K", "4K"), ("1080p", "1080p")])

    def test_page_gets_groups_and_saving_checks_values(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(pa, "host_path", return_value="/srv/p"), mock.patch.object(pa, "_compose_run", return_value=(True, "")):
            pa.install(d, manifest(), "/srv/media")
            shown = {s["key"]: s for s in pa.public_settings(d, "on-demand")}
            self.assertEqual(shown["lang"]["group"], "Picture and sound")
            self.assertEqual(shown["lang"]["choices"][1], {"value": "fre", "label": "French"})
            self.assertEqual(shown["quality"]["choices"][0], {"value": "4K", "label": "4K"})
            pa.save_settings(d, "on-demand", {"lang": "fre"})
            with self.assertRaisesRegex(ValueError, "choose one from the list"):
                pa.save_settings(d, "on-demand", {"lang": "French"})


if __name__ == "__main__":
    unittest.main()
