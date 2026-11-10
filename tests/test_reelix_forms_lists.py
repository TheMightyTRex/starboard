"""Settings, Reelix, Information: Language of details and Region are lists with plain names (owner, 10 November
2026), and an empty Region (Reelix's default) saves instead of failing 'not in the form it needs'."""
import unittest

from starboard import reelix_forms as rf


class FakeReelix:
    def __init__(self, current):
        self.current, self.put = current, None

    def call(self, method, path, body=None):
        if method == "PUT":
            self.put = body
            self.current = {**self.current, **body}
        return 200, self.current


class InformationListsTest(unittest.TestCase):
    def test_an_empty_region_saves(self):
        r = FakeReelix({"language": "en-US", "region": None})
        rf.save_form(r, "information", {"language": "en-GB", "region": ""})
        self.assertEqual((r.put["language"], r.put["region"]), ("en-GB", None))

    def test_the_lists_have_plain_names_and_keep_reelixs_own_value(self):
        f = rf.open_form(FakeReelix({"language": "eo", "region": None}), "information")
        lang, region = f["fields"][0], f["fields"][1]
        self.assertIn({"value": "en-GB", "label": "English (United Kingdom), en-GB"}, lang["choices"])
        self.assertEqual(lang["choices"][0]["label"], "eo (as Reelix has it now)")
        self.assertEqual((region["value"], region["choices"][0]["value"]), ("", ""))

    def test_anything_else_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Choose one of the choices"):
            rf.save_form(FakeReelix({"language": "en-US"}), "information", {"language": "xx-YY"})


if __name__ == "__main__":
    unittest.main()
