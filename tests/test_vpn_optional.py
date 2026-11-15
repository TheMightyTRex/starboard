"""Downloading without a VPN (DASH-440; owner, 15 November 2026: "Need to make the VPN account optional but with a
warning about not using it"). Both set-ups offer Continue without a VPN on the VPN step, with a warning; the apps are
then written without Gluetun, with qBittorrent on its own network and ports; Settings, Downloads, VPN adds a VPN
later or removes it; Downloads shows a quiet reminder that can be hidden for 90 days. Nothing here starts containers."""
import io
import json
import os
import pathlib
import re
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, download_repair, reelix_sites, server, stack, terminal_setup, vpn_ports
from starboard.server import make_server
from tests.test_terminal_setup import Answers

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORDS = "correct horse battery"
VPN = {"provider": "mullvad", "type": "wireguard", "wireguard_private_key": "made-up", "wireguard_addresses": "192.168.1.20/32"}
NOVPN = json.loads((ROOT / "web" / "setup-answers.json").read_text())["novpn"]


def basics(vpn):
    c = stack.install_choice("basics")
    apps = c["apps"] if vpn else [k for k in c["apps"] if k != "gluetun"]
    choice = {"apps": apps, "config_dir": "/srv/config", "data_dir": "/srv/media", "reelix_edition": "lite"}
    if vpn:
        choice["vpn"] = VPN
    return choice


def block(compose, name):
    m = re.search(rf"(?ms)^  {name}:\n(.*?)(?=^  \S|\Z)", compose)
    return m.group(1) if m else None


class ComposeWithoutGluetunTest(unittest.TestCase):
    def setUp(self):
        for p in (mock.patch("starboard.stack.can_download", return_value=True), mock.patch("starboard.stack._port_free", return_value=True)):
            p.start()
            self.addCleanup(p.stop)

    def test_basics_without_a_vpn_has_no_gluetun_and_qbittorrent_has_its_own_ports(self):
        built = stack.build(basics(False))
        compose = built["compose"]
        self.assertIsNone(block(compose, "gluetun"))
        self.assertNotIn("network_mode", compose)
        self.assertNotIn("NET_ADMIN", compose)
        qbit = block(compose, "qbittorrent")
        for port in ('"8080:8080"', '"6881:6881"', '"6881:6881/udp"'):
            self.assertIn(port, qbit)
        self.assertNotIn("depends_on", qbit)
        self.assertIn('"6789:6789"', block(compose, "nzbget"))  # NZBGet as before, on its own
        self.assertNotIn("VPN_SERVICE_PROVIDER", built["env"])
        self.assertNotIn("gluetun", block(compose, "reelix"))  # Reelix does not wait for a VPN

    def test_with_a_vpn_qbittorrent_is_behind_gluetun_as_before(self):
        compose = stack.build(basics(True))["compose"]
        self.assertIn('network_mode: "service:gluetun"', block(compose, "qbittorrent"))
        self.assertIn('"8080:8080"', block(compose, "gluetun"))

    def test_basics_without_a_vpn_is_still_basics(self):
        self.assertEqual(stack.which_install(basics(False)["apps"]), "basics")
        self.assertEqual(stack.which_install(basics(True)["apps"]), "basics")

    def test_reelix_reaches_the_download_apps_by_their_own_names(self):
        with tempfile.TemporaryDirectory() as d:
            choice = basics(False)
            built = stack.build(choice)
            stack.write(d, built)
            stack.note_reelix(d, choice, built)
            info = json.loads(pathlib.Path(stack.folder(d), "reelix-setup.json").read_text())
            self.assertEqual((info["qbittorrent_host"], info["usenet_host"], info["vpn"]), ("qbittorrent", "nzbget", False))
            wanted = download_repair.wanted(d)
            self.assertEqual(wanted["qbittorrent"]["host"], "qbittorrent")
            self.assertEqual(wanted["nzbget"]["host"], "nzbget")
            self.assertFalse(reelix_sites.vpn_available(d))


class ChoiceAndReminderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for p in (mock.patch("starboard.stack.can_download", return_value=True), mock.patch("starboard.stack._port_free", return_value=True)):
            p.start()
            self.addCleanup(p.stop)

    def test_the_reminder_shows_without_a_vpn_and_hides_for_90_days(self):
        stack.write(self.tmp.name, stack.build(basics(False)))
        stack.record_vpn_choice(self.tmp.name, False, "browser", now=1000)
        st = stack.vpn_state(self.tmp.name, now=2000)
        self.assertEqual((st["on"], st["reminder"], st["peers"]), (False, True, True))
        until = stack.hide_vpn_reminder(self.tmp.name, now=2000)
        self.assertEqual(until, 2000 + 90 * 86400)
        self.assertFalse(stack.vpn_state(self.tmp.name, now=3000)["reminder"])
        self.assertTrue(stack.vpn_state(self.tmp.name, now=until + 1)["reminder"])  # back after 90 days
        self.assertEqual(stack.vpn_choice(self.tmp.name)["from"], "browser")

    def test_no_reminder_with_a_vpn_or_without_torrents(self):
        stack.write(self.tmp.name, stack.build(basics(True)))
        self.assertFalse(stack.vpn_state(self.tmp.name)["reminder"])
        usenet_only = {**basics(False), "apps": ["nzbget", "jellyfin"]}
        stack.write(self.tmp.name, stack.build(usenet_only))
        self.assertFalse(stack.vpn_state(self.tmp.name)["reminder"])

    def test_another_install_keeps_going_without_a_vpn(self):
        stack.write(self.tmp.name, stack.build(basics(False)))
        plan = stack.plan_change(self.tmp.name, install="full")
        self.assertNotIn("gluetun", plan["choice"]["apps"])
        stack.build(plan["choice"])  # no VPN details asked for

    def test_adding_a_vpn_later_needs_its_details_and_moves_qbittorrent_behind_it(self):
        stack.write(self.tmp.name, stack.build(basics(False)))
        plan = stack.plan_vpn(self.tmp.name, True, {"provider": "mullvad", "type": "wireguard"})
        self.assertEqual(plan["add"], ["gluetun"])
        with self.assertRaisesRegex(ValueError, "WireGuard private key"):
            stack.build(plan["choice"])  # the same check as the set-ups
        plan = stack.plan_vpn(self.tmp.name, True, VPN)
        compose = stack.build(plan["choice"])["compose"]
        self.assertIn('network_mode: "service:gluetun"', block(compose, "qbittorrent"))
        self.assertIn('"8080:8080"', block(compose, "gluetun"))

    def test_removing_the_vpn_takes_gluetun_away(self):
        stack.write(self.tmp.name, stack.build(basics(True)))
        plan = stack.plan_vpn(self.tmp.name, False)
        self.assertEqual(plan["remove"], ["gluetun"])
        self.assertNotIn("vpn", plan["choice"])
        compose = stack.build(plan["choice"])["compose"]
        self.assertIn('"8080:8080"', block(compose, "qbittorrent"))
        self.assertNotIn("network_mode", compose)
        stack.write(self.tmp.name, stack.build(plan["choice"]))
        with self.assertRaisesRegex(ValueError, "no VPN"):
            stack.plan_vpn(self.tmp.name, False)

    def test_reelix_searches_and_flaresolverr_follow_the_vpn(self):
        stack.write(self.tmp.name, stack.build({**basics(False), "apps": basics(False)["apps"] + ["flaresolverr"]}))
        settings = {"proxy": dict(reelix_sites.PROXY), "flaresolverr_url": "http://gluetun:8191"}

        class Reelix:
            def call(self, method, path, body=None):
                if method == "PUT":
                    settings.clear()
                    settings.update(body)
                return 200, dict(settings)
        done = reelix_sites.follow_vpn(Reelix(), self.tmp.name, False)
        self.assertIsNone(settings["proxy"])
        self.assertEqual(settings["flaresolverr_url"], "http://flaresolverr:8191")
        self.assertIn("Reelix searches from this computer's own address", done)

    def test_qbittorrent_listens_on_its_own_port_again(self):
        cfg = mock.Mock(data={"services": [{"type": "qbittorrent", "api_key": "k", "enabled": True}]})
        sent = []
        with mock.patch("starboard.services.qbit", side_effect=lambda s, path, data=None: sent.append((path, data)) or {"listen_port": 51413}):
            said = vpn_ports.listen_at_home(cfg)
        self.assertIn("6881", said)
        self.assertEqual(json.loads(sent[-1][1]["json"])["listen_port"], 6881)


class TerminalChoiceTest(unittest.TestCase):
    def term(self, typed):
        out = io.StringIO()
        return terminal_setup.Terminal(out=out, ask=Answers(typed), secret=Answers([]), fancy=False), out

    def state(self):
        return {"choice": {"apps": list(basics(True)["apps"]), "groups": ["downloads", "vpn", "watching"]},
                "names": [stack.APPS[k]["name"] for k in basics(True)["apps"]]}

    def test_the_vpn_is_the_suggested_answer(self):
        term, out = self.term([""])
        state = self.state()
        self.assertTrue(terminal_setup.ask_vpn_or_not(term, state))
        self.assertIn("gluetun", state["choice"]["apps"])
        self.assertIn(f"1. {NOVPN['use']}", out.getvalue())
        self.assertIn("Your choice [1]", "\n".join(term._ask.prompts))

    def test_without_a_vpn_shows_the_warning_and_cancel_is_the_default(self):
        term, out = self.term(["2", "", "2", "2"])  # without; Enter cancels; without again; I understand
        state = self.state()
        self.assertFalse(terminal_setup.ask_vpn_or_not(term, state))
        text = " ".join(out.getvalue().split())
        for line in NOVPN["warning"]:
            self.assertEqual(text.count(line), 2)  # shown each time it was chosen
        self.assertEqual(text.count(NOVPN["question"]), 2)  # Cancel asked again
        self.assertTrue(state["no_vpn"])
        self.assertNotIn("gluetun", state["choice"]["apps"])
        self.assertNotIn("vpn", state["choice"]["groups"])
        self.assertNotIn("Gluetun", state["names"])
        self.assertIn(f"1. {NOVPN['cancel']}", out.getvalue())

    def test_the_vpn_step_stays_in_the_count_and_can_add_it_back(self):
        term, _ = self.term(["2", "2"])
        state = self.state()
        terminal_setup.ask_vpn_or_not(term, state)
        state.update(start="new")
        self.assertIn("vpn", terminal_setup.job_steps(state))  # the step is still counted, so Back reaches it
        term, out = self.term([""])  # back on the step: Enter keeps "without"
        self.assertFalse(terminal_setup.ask_vpn_or_not(term, state))
        self.assertIn("Your choice [2]", "\n".join(term._ask.prompts))
        term, _ = self.term(["1"])  # the VPN after all
        self.assertTrue(terminal_setup.ask_vpn_or_not(term, state))
        self.assertIn("gluetun", state["choice"]["apps"])
        self.assertFalse(state["no_vpn"])

    def test_both_set_ups_use_the_same_words(self):
        js = (ROOT / "web" / "js" / "install.js").read_text()
        common = (ROOT / "web" / "js" / "common.js").read_text()
        for key in ("question", "use", "use_about", "without", "without_about"):
            self.assertIn(f"nw.{key}", js)
        for key in ("warning_title", "warning", "confirm", "cancel"):
            self.assertIn(f"w.{key}", common)
        self.assertIn('role: "alertdialog"', common)


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k, v in {"STARBOARD_HISTORY": "0", "STARBOARD_SCHEDULE": "0", "STARBOARD_WATCH": "0", "STARBOARD_JOBS": "0",
                     "STARBOARD_DOCKER": "/nonexistent/docker.sock"}.items():
            os.environ[k] = v
        for p in (mock.patch("starboard.server.discovery.search", return_value={"items": []}),
                  mock.patch("starboard.stack.can_download", return_value=True),
                  mock.patch("starboard.stack._port_free", return_value=True),
                  mock.patch("starboard.server.after_install_change")):  # nothing runs after: no containers here
            p.start()
            self.addCleanup(p.stop)
        self.server, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = terminal_setup.Api(self.server.server_address[1])
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": WORDS})
        stack._job.clear()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()
        stack._job.clear()

    def test_writing_without_a_vpn_records_the_choice(self):
        self.api.call("POST", "/api/stack/write", {**basics(False), "password": WORDS, "from": "terminal"})
        self.assertEqual(stack.vpn_choice(self.tmp.name)["vpn"], False)
        self.assertEqual(stack.vpn_choice(self.tmp.name)["from"], "terminal")
        st = self.api.call("GET", "/api/downloads/vpn-state")
        self.assertEqual((st["on"], st["reminder"]), (False, True))
        self.assertTrue(self.api.call("GET", "/api/downloads/settings")["vpn"]["state"]["reminder"])
        st = self.api.call("POST", "/api/downloads/vpn-reminder", {})
        self.assertFalse(st["reminder"])
        self.assertGreater(st["hidden_until"], 0)

    def test_add_a_vpn_later_then_remove_it(self):
        self.api.call("POST", "/api/stack/write", {**basics(False), "password": WORDS})
        with self.assertRaises(terminal_setup.Problem) as e:
            self.api.call("POST", "/api/downloads/vpn", {"password": WORDS, "vpn": {"provider": "mullvad", "type": "wireguard"}})
        self.assertIn("WireGuard private key", str(e.exception))
        self.assertNotIn("gluetun", stack.chosen_keys(self.tmp.name))  # nothing written
        r = self.api.call("POST", "/api/downloads/vpn", {"password": WORDS, "vpn": VPN})
        self.assertEqual((r["vpn"], r["add"]), (True, ["gluetun"]))
        self.assertIn("--start-apps", r["command"])  # no Docker access in tests
        self.assertIn("gluetun", stack.chosen_keys(self.tmp.name))
        self.assertTrue(stack.vpn_choice(self.tmp.name)["vpn"])
        self.assertEqual(server.after_install_change.call_args[0][2]["add"], ["gluetun"])
        # Removing needs the password and the warning understood
        with self.assertRaises(terminal_setup.Problem):
            self.api.call("POST", "/api/downloads/vpn/remove", {"password": WORDS})
        with self.assertRaises(terminal_setup.Problem):
            self.api.call("POST", "/api/downloads/vpn/remove", {"password": "wrong", "understood": True})
        self.assertIn("gluetun", stack.chosen_keys(self.tmp.name))
        r = self.api.call("POST", "/api/downloads/vpn/remove", {"password": WORDS, "understood": True})
        self.assertEqual((r["vpn"], r["remove"]), (False, ["gluetun"]))
        self.assertNotIn("gluetun", stack.chosen_keys(self.tmp.name))
        self.assertFalse(stack.vpn_choice(self.tmp.name)["vpn"])
        compose = (pathlib.Path(stack.folder(self.tmp.name)) / "compose.yaml").read_text()
        self.assertIn('"8080:8080"', block(compose, "qbittorrent"))
        self.assertNotIn("WIREGUARD_PRIVATE_KEY", (pathlib.Path(stack.folder(self.tmp.name)) / ".env").read_text())


if __name__ == "__main__":
    unittest.main()
