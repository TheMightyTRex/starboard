"""The plug-ins help mirror (DASH-426): tools/sync-plugin-help.py mends each page's links for Starboard's help centre,
and check-help.py fails when Starboard's plug-in API is newer than the developers' pages describe."""
import importlib.util
import pathlib
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent.parent / "tools"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, TOOLS / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sync = load("sync_plugin_help", "sync-plugin-help.py")
check = load("check_help", "check-help.py")


class Mend(unittest.TestCase):
    out = sync.OUT / "direct-play"

    def mend(self, md, src="help/plugins/direct-play/install.md"):
        return sync.mend(md, src, self.out)

    def test_overview_of_a_plugin(self):
        self.assertEqual(self.mend("[x](../../../direct-play/README.md)"), "[x](../direct-play/README.md)")
        self.assertEqual(self.mend("[x](../../../tdarr/README.md#set-it-up)"), "[x](../tdarr/README.md#set-it-up)")

    def test_a_plugins_own_page(self):
        self.assertEqual(self.mend("[x](settings.md)"), "[x](../direct-play/settings.md)")
        self.assertEqual(self.mend("[x](../tdarr/problems.md)"), "[x](../tdarr/problems.md)")

    def test_collection_article_goes_to_its_site(self):
        self.assertEqual(self.mend("[x](../../developers/plug-in-api.md)"),
                         "[x](https://themightytrex.github.io/starboard-plugins/help/developers/plug-in-api.html)")

    def test_other_files_go_to_github(self):
        self.assertEqual(self.mend("[x](../../../direct-play/app.py)"),
                         "[x](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/app.py)")
        self.assertEqual(self.mend("[x](CHANGELOG.md)", "direct-play/README.md"),
                         "[x](https://github.com/TheMightyTRex/starboard-plugins/blob/main/direct-play/CHANGELOG.md)")

    def test_starboard_help_becomes_a_link_between_articles(self):
        md = "[x](https://themightytrex.github.io/starboard/help/topics/add-a-plugin.html#if-it-does-not-work)"
        self.assertEqual(self.mend(md), "[x](../../topics/add-a-plugin.md#if-it-does-not-work)")

    def test_web_addresses_and_images_stay(self):
        for md in ("[x](https://example.org/a)", "[x](#on-this-page)", "![a picture](logo.svg)"):
            self.assertEqual(self.mend(md), md)


class PluginApiPages(unittest.TestCase):
    def test_pages_name_the_api_they_describe(self):
        self.assertEqual(check.plugin_api_pages(), [])

    def test_an_older_page_fails(self):
        with tempfile.TemporaryDirectory() as d:
            help_dir = pathlib.Path(d) / "docs" / "help"
            (help_dir / "developers").mkdir(parents=True)
            (pathlib.Path(d) / "starboard").mkdir()
            (pathlib.Path(d) / "starboard" / "plugins.py").write_text('API_VERSION = "1.15.0"\n')
            (help_dir / "developers" / "ai-prompts-for-developers.md").write_text("<!-- plugin-api: 1.14 -->\n")
            (help_dir / "llms.txt").write_text("no line\n")
            old = check.HELP
            check.HELP = help_dir
            try:
                problems = check.plugin_api_pages()
            finally:
                check.HELP = old
        self.assertEqual(len(problems), 2)
        self.assertIn("describes plug-in API 1.14, but Starboard has 1.15", problems[0])
        self.assertIn("no <!-- plugin-api", problems[1])


if __name__ == "__main__":
    unittest.main()
