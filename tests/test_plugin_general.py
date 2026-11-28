"""Plug-ins, 19 November 2026 (owner): "When you install a plugin - it should automatically turn on. Keep the option in
state"; the Address Jellyfin uses to reach the TV channel "is this not populated automatically?"; a channel's name
was refused as "must be a URL"; and "rename State to General" with a card each for State, Versions, Jobs, What it
may do and Remove."""
import pathlib
import unittest
from unittest import mock

from starboard import plugins, plugins_admin as pa
from tests.test_app_plugins import app_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class HomeAddress(unittest.TestCase):
    def test_a_published_container_is_told_its_home_address(self):
        text = plugins.compose(app_manifest(), "/p", "/m", None, extra={"ports": {"app": 3001}, "home_ip": "192.168.1.20"})
        app, db = text.split("  plugin-stats-app-db:")
        self.assertIn('STARBOARD_HOME_ADDRESS: "http://192.168.1.20:3001"', app)
        self.assertNotIn("STARBOARD_HOME_ADDRESS", db)  # not published: no address on the home network

    def test_no_address_without_a_home_ip_or_a_port(self):
        self.assertNotIn("STARBOARD_HOME_ADDRESS", plugins.compose(app_manifest(), "/p", "/m", None, extra={"ports": {"app": 3001}}))
        self.assertNotIn("STARBOARD_HOME_ADDRESS", plugins.compose(app_manifest(), "/p", "/m", None, extra={"home_ip": "192.168.1.20"}))

    def test_home_ip_is_never_a_loopback_address(self):
        self.assertFalse(pa.home_ip().startswith("127."))


class ActivateAfterInstall(unittest.TestCase):
    def test_it_activates_when_nothing_needs_setting_up(self):
        with mock.patch("starboard.plugin_life.can_enable"), mock.patch.object(pa, "enable") as on:
            self.assertEqual(pa.activate_after_install("/d", "tv-station", services={"a": 1}), "")
        on.assert_called_once_with("/d", "tv-station", services={"a": 1})

    def test_one_that_needs_setting_up_stays_as_it_is_and_says_why(self):
        with mock.patch("starboard.plugin_life.can_enable", side_effect=ValueError("Enter its address first")), \
                mock.patch.object(pa, "enable") as on:
            self.assertEqual(pa.activate_after_install("/d", "test-plugin"), "Enter its address first")
        on.assert_not_called()

    def test_a_start_that_fails_never_undoes_the_install(self):
        with mock.patch("starboard.plugin_life.can_enable"), mock.patch.object(pa, "enable", side_effect=RuntimeError("no image")):
            said = pa.activate_after_install("/d", "test-plugin")
        self.assertIn("did not start: no image", said)
        self.assertIn("Select Turn on on its page", said)

    def test_an_app_to_bring_in_waits_so_bring_in_can_copy_it(self):
        with mock.patch("starboard.plugin_life.can_enable"), mock.patch.object(pa, "enable") as on, \
                mock.patch.object(pa, "_read", return_value={"adopt": {"app": "tdarr", "name": "Tdarr"}}), \
                mock.patch("starboard.containers.docker", return_value={"Id": "x"}):
            said = pa.activate_after_install("/d", "tdarr")
        on.assert_not_called()
        self.assertIn("Bring in the Tdarr you already have first, then select Turn on", said)

    def test_a_new_app_with_nothing_to_bring_in_starts(self):
        from starboard import containers
        with mock.patch("starboard.plugin_life.can_enable"), mock.patch.object(pa, "enable") as on, \
                mock.patch.object(pa, "_read", return_value={"adopt": {"app": "tdarr", "name": "Tdarr"}}), \
                mock.patch("starboard.containers.docker", side_effect=containers.DockerError("no such container")):
            self.assertEqual(pa.activate_after_install("/d", "tdarr"), "")
        on.assert_called_once()

    def test_every_install_route_activates(self):
        server = (ROOT / "starboard" / "server.py").read_text(encoding="utf-8")
        self.assertEqual(server.count("pa.activate_after_install("), 3)  # address or catalogue, built in, zip


class PlainTextBoxes(unittest.TestCase):
    def test_add_and_row_fields_take_plain_text(self):
        js = (ROOT / "web" / "js" / "plugins.js").read_text(encoding="utf-8")
        self.assertIn('type: "text", placeholder: data.add.placeholder', js)
        self.assertIn('id: `${base}-url`, type: "text"', js)


class General(unittest.TestCase):
    def test_general_holds_the_five_cards_and_plug_in_pages_have_tabs_from_two(self):
        js = (ROOT / "web" / "js" / "plugins.js").read_text(encoding="utf-8")
        self.assertIn('groupSection(`pl-${p.id}-general`, "General", stateSec, slot, versions, jobs, may, remove)', js)
        self.assertIn('data-topic-min="2"', (ROOT / "web" / "settings-plugin.html").read_text(encoding="utf-8"))
