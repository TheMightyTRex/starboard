"""A custom card for any service's JSON (DASH-555): the fields chosen from an answer, the status rules, the address checks
(home network only unless allowed, no redirect, one lookup, a deadline, a size limit), the key kept like the other
secrets, asking only when shown and kept for the refresh time, and the routes."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import auth, backup, json_cards, oidc
from starboard.config import Config
from starboard.json_cards import CardError

ANSWER = {"data": {"queue": {"total": 7, "state": "Idle", "paused": False}, "items": [{"name": "Dune"}, {"name": "Arrival"}],
                   "api_token": "super-secret-value", "ratio": 1.5, "empty": None}}


class Service(BaseHTTPRequestHandler):
    seen = []
    mode = "ok"

    def log_message(self, *a):
        pass

    def do_GET(self):
        type(self).seen.append({"path": self.path, "key": self.headers.get("X-Api-Key"), "auth": self.headers.get("Authorization"),
                                "host": self.headers.get("Host")})
        mode = type(self).mode
        if mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/elsewhere")
            self.end_headers()
            return
        if mode in ("401", "500"):
            self.send_response(int(mode))
            self.end_headers()
            return
        body = {"huge": "x" * (json_cards.READ_LIMIT + 10)} if mode == "huge" else ANSWER
        raw = b"not json at all" if mode == "text" else json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve():
    Service.seen, Service.mode = [], "ok"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Service)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Fields(unittest.TestCase):
    def test_paths_reach_names_and_list_entries(self):
        self.assertEqual(json_cards.pick(ANSWER, json_cards.parse_path("data.queue.total")), (True, 7))
        self.assertEqual(json_cards.pick(ANSWER, json_cards.parse_path("data.items.1.name")), (True, "Arrival"))
        self.assertEqual(json_cards.pick(ANSWER, json_cards.parse_path("data.items[0].name")), (True, "Dune"))
        self.assertEqual(json_cards.pick(ANSWER, json_cards.parse_path("data.nothing"))[0], False)
        self.assertEqual(json_cards.pick(ANSWER, json_cards.parse_path("data.items.9"))[0], False)
        for bad in ("", "  ", "a" * 201, "a.b\x00"):
            with self.assertRaises(ValueError):
                json_cards.parse_path(bad)

    def test_values_are_shown_in_words(self):
        self.assertEqual(json_cards.display(1234567), ("1,234,567", "number"))
        self.assertEqual(json_cards.display(1.5), ("1.5", "number"))
        self.assertEqual(json_cards.display(2.0), ("2", "number"))
        self.assertEqual(json_cards.display(True), ("Yes", "bool"))
        self.assertEqual(json_cards.display(None), ("Empty", "empty"))
        self.assertEqual(json_cards.display([1]), ("1 entry", "list"))
        self.assertEqual(json_cards.display([1, 2]), ("2 entries", "list"))
        self.assertEqual(json_cards.display("a\nb\x07c"), ("a b c", "text"))
        self.assertEqual(len(json_cards.display("x" * 500)[0]), 120)

    def test_rules_say_ok_or_the_level_chosen(self):
        rule = lambda op, value, bad="problem": {"op": op, "value": value, "bad": bad}  # noqa: E731
        self.assertEqual(json_cards.judge(rule("above", "5"), 7), "ok")
        self.assertEqual(json_cards.judge(rule("above", "5"), 5), "problem")
        self.assertEqual(json_cards.judge(rule("below", "5", "warning"), 5), "warning")
        self.assertEqual(json_cards.judge(rule("below", "5"), "3"), "ok")  # a number sent as text
        self.assertEqual(json_cards.judge(rule("above", "5"), "many"), "problem")  # not a number: not good
        self.assertEqual(json_cards.judge(rule("above", "5"), [1]), "problem")
        self.assertEqual(json_cards.judge(rule("equals", "idle"), "Idle"), "ok")
        self.assertEqual(json_cards.judge(rule("equals", "7"), 7.0), "ok")
        self.assertEqual(json_cards.judge(rule("not_equals", "error"), "ok"), "ok")
        self.assertEqual(json_cards.judge(rule("contains", "run"), "Running fine"), "ok")
        self.assertEqual(json_cards.judge(rule("not_contains", "fail"), "1 failed"), "problem")
        self.assertEqual(json_cards.judge(rule("equals", "true"), True), "ok")
        self.assertEqual(json_cards.judge(rule("equals", "no"), False), "ok")
        self.assertIsNone(json_cards.judge(None, 3))

    def test_the_card_takes_the_worst_state_and_none_without_rules(self):
        fields = [{"path": "data.queue.total", "label": "Waiting", "unit": "items", "rule": {"op": "below", "value": "5", "bad": "warning"}},
                  {"path": "data.queue.state", "label": "State", "unit": "", "rule": {"op": "equals", "value": "Idle", "bad": "problem"}},
                  {"path": "data.gone", "label": "Gone", "unit": "", "rule": None},
                  {"path": "data.items", "label": "Titles", "unit": "x", "rule": None}]
        rows = json_cards.rows_of(ANSWER, fields)
        self.assertEqual([(r["label"], r["value"], r["unit"], r["state"]) for r in rows],
                         [("Waiting", "7", "items", "warning"), ("State", "Idle", "", "ok"), ("Gone", "Not in the answer", "", "warning"),
                          ("Titles", "2 entries", "", None)])  # a unit is only for numbers and words
        self.assertEqual(json_cards.overall(rows), "warning")
        self.assertIsNone(json_cards.overall([{"state": None}]))

    def test_the_choices_list_the_fields_and_hide_what_looks_like_a_secret(self):
        found, more = json_cards.leaves(ANSWER)
        by = {f["path"]: f for f in found}
        self.assertEqual(by["data.queue.total"]["sample"], "7")
        self.assertEqual(by["data.items"]["sample"], "2 entries")
        self.assertEqual(by["data.items.0.name"]["sample"], "Dune")
        self.assertNotIn("super-secret-value", json.dumps(found))
        self.assertIn("Hidden", by["data.api_token"]["sample"])
        self.assertFalse(more)
        many, more = json_cards.leaves({f"k{i}": i for i in range(50)} | {"x": {f"j{i}": i for i in range(50)}}, limit=70)
        self.assertEqual(len(many), 70)
        self.assertTrue(more)


class Addresses(unittest.TestCase):
    def resolve(self, ip):
        return lambda host, port, *a, **k: [(2, 1, 6, "", (ip, port))]

    def test_the_home_network_is_what_is_asked_by_default(self):
        for ok in ("127.0.0.1", "10.1.2.3", "172.16.0.9", "172.31.255.1", "192.168.1.20", "100.64.0.5", "::1", "fd12:3456::1", "::ffff:192.168.1.5"):
            self.assertTrue(json_cards.on_home_network(ok), ok)
        for no in ("93.184.216.34", "172.32.0.1", "100.128.0.1", "2606:4700::1111", "8.8.8.8"):
            self.assertFalse(json_cards.on_home_network(no), no)
        json_cards.check_address("http://192.168.1.20:8080/api/status", False)
        json_cards.check_address("http://nas.home/api", False, self.resolve("192.168.1.9"))
        with self.assertRaises(CardError) as e:
            json_cards.check_address("https://api.example.com/x", False, self.resolve("93.184.216.34"))
        self.assertIn("not on your home network", e.exception.text)
        with self.assertRaises(CardError):
            json_cards.check_address("http://8.8.8.8/x", False)

    def test_others_need_the_owner_to_allow_them_and_even_then_not_every_address(self):
        json_cards.check_address("https://api.example.com/x", True, self.resolve("93.184.216.34"))
        for bad in ("http://169.254.169.254/latest", "http://[fe80::1]/x", "http://224.0.0.1/x", "http://0.0.0.0/x", "http://metadata.google.internal/x"):
            with self.assertRaises(CardError, msg=bad):
                json_cards.check_address(bad, True)

    def test_only_an_address_a_request_can_hold(self):
        for bad in ("", "ftp://192.168.1.2/x", "192.168.1.2/x", "http://user:pw@192.168.1.2/x", "http://192.168.1.2/a b", "http://192.168.1.2/x#frag",
                    "http://192.168.1.2:99999/x", "javascript:alert(1)"):
            with self.assertRaises(CardError, msg=bad):
                json_cards.check_address(bad, False)

    def test_a_name_that_later_answers_with_another_address_is_not_called(self):  # DNS rebinding
        real = oidc.socket.getaddrinfo
        with mock.patch.object(json_cards, "check_address", lambda *a, **k: None), \
                mock.patch.object(oidc.socket, "getaddrinfo", lambda host, port, *a, **k: real("93.184.216.34", port, *a, **k)):
            with self.assertRaises(CardError) as e:
                json_cards.fetch("http://rebind.test:9/x")
        self.assertIn("not on your home network", e.exception.text)
        with mock.patch.object(json_cards, "check_address", lambda *a, **k: None), \
                mock.patch.object(oidc.socket, "getaddrinfo", lambda host, port, *a, **k: real("169.254.169.254", port, *a, **k)):
            with self.assertRaises(CardError):
                json_cards.fetch("http://rebind.test:9/x", allow_outside=True)


class Asking(unittest.TestCase):
    def setUp(self):
        self.server = serve()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/status?x=1"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_the_answer_is_read_with_the_key_in_the_header_chosen(self):
        doc = json_cards.fetch(self.url, "k-123")
        self.assertEqual(doc["data"]["queue"]["total"], 7)
        json_cards.fetch(self.url, "t-456", "bearer")
        json_cards.fetch(self.url)
        self.assertEqual([(s["key"], s["auth"]) for s in Service.seen], [("k-123", None), (None, "Bearer t-456"), (None, None)])
        self.assertEqual(Service.seen[0]["path"], "/api/status?x=1")

    def test_a_redirect_is_never_followed(self):
        Service.mode = "redirect"
        with self.assertRaises(CardError) as e:
            json_cards.fetch(self.url, "k")
        self.assertIn("never followed", e.exception.text)
        self.assertEqual(len(Service.seen), 1)  # nothing was asked at the other address

    def test_errors_too_much_and_not_json_say_so_and_never_hold_the_key(self):
        for mode, words in (("401", "refused the request"), ("500", "error (500)"), ("huge", "too much"), ("text", "did not answer in JSON")):
            Service.mode = mode
            with self.assertRaises(CardError) as e:
                json_cards.fetch(self.url, "sekret-key")
            self.assertIn(words, e.exception.text)
            self.assertNotIn("sekret-key", e.exception.text)

    def test_a_service_that_never_answers_is_given_up_on(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)  # accepts the connection (the backlog) and never says a word
        try:
            with mock.patch.object(json_cards, "DEADLINE", 1):
                began = __import__("time").monotonic()
                with self.assertRaises(CardError):
                    json_cards.fetch(f"http://127.0.0.1:{s.getsockname()[1]}/x")
                self.assertLess(__import__("time").monotonic() - began, 5)
        finally:
            s.close()

    def test_a_key_is_not_sent_in_the_open_beyond_the_home_network(self):
        with mock.patch.object(json_cards, "on_home_network", lambda ip: False):
            with self.assertRaises(CardError) as e:
                json_cards.fetch(self.url, "k", allow_outside=True)
            self.assertIn("Use https://", e.exception.text)
            self.assertEqual(Service.seen, [])  # not even a request
            self.assertEqual(json_cards.fetch(self.url, "", allow_outside=True)["data"]["queue"]["total"], 7)  # no key: fine


class Saved(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(self.tmp.name)
        self.server = serve()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api"
        json_cards.forget()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def card(self, **more):
        return {"name": "Queue", "url": self.url, "key": "k-1", "key_style": "x-api-key", "refresh": 60,
                "fields": [{"path": "data.queue.total", "label": "Waiting", "unit": "items", "rule": {"op": "below", "value": "10", "bad": "warning"}}], **more}

    def test_saving_keeps_the_key_out_of_what_the_page_gets(self):
        card = json_cards.save_card(self.cfg, self.card())
        self.assertTrue(card["has_key"])
        self.assertNotIn("key", card)
        self.assertNotIn("k-1", json.dumps(json_cards.listing(self.cfg)))
        self.assertNotIn("k-1", json.dumps(self.cfg.public()))
        self.assertEqual(self.cfg.data["json_cards"]["cards"][0]["key"], "k-1")
        mode = os.stat(os.path.join(self.tmp.name, "config.json")).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_a_blank_key_keeps_the_saved_one_but_never_hands_it_to_another_server(self):
        card = json_cards.save_card(self.cfg, self.card())
        json_cards.save_card(self.cfg, self.card(id=card["id"], key="", name="Queue 2"))
        self.assertEqual(self.cfg.data["json_cards"]["cards"][0]["key"], "k-1")
        with self.assertRaises(CardError) as e:
            json_cards.save_card(self.cfg, self.card(id=card["id"], key="", url="http://127.0.0.1:9/other"))
        self.assertIn("different server", e.exception.text)
        json_cards.save_card(self.cfg, self.card(id=card["id"], key="", url="http://127.0.0.1:9/other", clear_key=True))
        self.assertEqual(self.cfg.data["json_cards"]["cards"][0]["key"], "")

    def test_checks_on_what_is_saved(self):
        for bad in ({"name": ""}, {"url": ""}, {"url": "http://8.8.8.8/x"}, {"fields": []}, {"refresh": 5}, {"key_style": "cookie"},
                    {"fields": [{"path": "a"}, {"path": "a"}]},
                    {"fields": [{"path": "a", "rule": {"op": "above", "value": "lots"}}]},
                    {"fields": [{"path": "a", "rule": {"op": "weird", "value": "1"}}]},
                    {"fields": [{"path": "a", "rule": {"op": "equals", "value": ""}}]},
                    {"fields": [{"path": "a%d" % i} for i in range(json_cards.MAX_FIELDS + 1)]}):
            with self.assertRaises(CardError, msg=str(bad)[:60]):
                json_cards.save_card(self.cfg, self.card(**bad))
        self.assertEqual(self.cfg.data["json_cards"]["cards"], [])
        for i in range(json_cards.MAX_CARDS):
            json_cards.save_card(self.cfg, self.card(name=f"c{i}"))
        with self.assertRaises(CardError):
            json_cards.save_card(self.cfg, self.card())
        with self.assertRaises(CardError):
            json_cards.save_card(self.cfg, self.card(id="jc00000000"))

    def test_an_address_outside_waits_for_the_owner_to_allow_it(self):
        with mock.patch.object(json_cards.oidc.socket, "getaddrinfo", lambda h, p, *a, **k: [(2, 1, 6, "", ("93.184.216.34", p))]), \
                mock.patch("starboard.outside.socket.getaddrinfo", lambda h, p, *a, **k: [(2, 1, 6, "", ("93.184.216.34", p))]):
            with self.assertRaises(CardError):
                json_cards.save_card(self.cfg, self.card(url="https://api.example.com/x"))
            json_cards.set_allow_outside(self.cfg, True)
            json_cards.save_card(self.cfg, self.card(url="https://api.example.com/x"))
            json_cards.set_allow_outside(self.cfg, False)
            json_cards.forget()  # saved before, but no longer allowed: it is not asked
            self.assertIn("not on your home network", json_cards.answer(self.cfg, self.cfg.data["json_cards"]["cards"][0]["id"])["problem"])

    def test_removing_a_card_takes_it_off_the_dashboard(self):
        card = json_cards.save_card(self.cfg, self.card())
        self.cfg.data["dashboard"] = {"layout": "glance", "cards": [{"id": "vpn", "size": "small"}, {"id": f"json:{card['id']}", "size": "half"}]}
        json_cards.delete_card(self.cfg, card["id"])
        self.assertEqual(self.cfg.data["dashboard"]["cards"], [{"id": "vpn", "size": "small"}])
        self.assertEqual(self.cfg.data["json_cards"]["cards"], [])
        with self.assertRaises(CardError):
            json_cards.delete_card(self.cfg, card["id"])

    def test_it_asks_only_when_shown_and_keeps_the_answer_for_the_refresh_time(self):
        card = json_cards.save_card(self.cfg, self.card(refresh=300))
        json_cards.listing(self.cfg)
        self.assertEqual(Service.seen, [])  # the list asks nothing
        first = json_cards.answer(self.cfg, card["id"], now=1000.0)
        self.assertEqual((first["state"], first["items"][0]["value"], first["items"][0]["state"], first["cached"]), ("ok", "7", "ok", False))
        self.assertEqual(Service.seen[0]["key"], "k-1")
        self.assertTrue(json_cards.answer(self.cfg, card["id"], now=1000.0 + 299)["cached"])
        self.assertEqual(len(Service.seen), 1)
        self.assertFalse(json_cards.answer(self.cfg, card["id"], now=1000.0 + 301)["cached"])
        self.assertEqual(len(Service.seen), 2)
        self.assertEqual(json_cards.listing(self.cfg)["cards"][0]["last"]["state"], "ok")  # remembered, with nothing asked
        self.assertEqual(len(Service.seen), 2)
        self.assertNotIn("data", json.dumps(json_cards._cache))  # only the chosen fields are kept, never the whole answer

    def test_ask_now_asks_again_but_not_in_a_burst_and_a_failure_is_not_hammered(self):
        card = json_cards.save_card(self.cfg, self.card(refresh=3600))
        json_cards.answer(self.cfg, card["id"], now=100.0)
        self.assertTrue(json_cards.answer(self.cfg, card["id"], fresh=True, now=102.0)["cached"])
        self.assertFalse(json_cards.answer(self.cfg, card["id"], fresh=True, now=106.0)["cached"])
        Service.mode = "500"
        bad = json_cards.answer(self.cfg, card["id"], fresh=True, now=200.0)
        self.assertEqual((bad["state"], bad["items"]), ("problem", []))
        self.assertIn("error (500)", bad["problem"])
        n = len(Service.seen)
        self.assertTrue(json_cards.answer(self.cfg, card["id"], now=220.0)["cached"])
        self.assertEqual(len(Service.seen), n)
        Service.mode = "ok"
        self.assertEqual(json_cards.answer(self.cfg, card["id"], now=235.0)["state"], "ok")  # asked again after 30 seconds

    def test_many_people_looking_at_once_make_one_request(self):
        card = json_cards.save_card(self.cfg, self.card())
        out = []
        threads = [threading.Thread(target=lambda: out.append(json_cards.answer(self.cfg, card["id"]))) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(out), 8)
        self.assertEqual(len(Service.seen), 1)

    def test_the_fields_to_choose_come_from_one_request_with_the_saved_key(self):
        card = json_cards.save_card(self.cfg, self.card())
        got = json_cards.probe(self.cfg, {"url": self.url, "id": card["id"]})
        self.assertIn("data.queue.total", [f["path"] for f in got["fields"]])
        self.assertEqual(Service.seen[-1]["key"], "k-1")
        json_cards.probe(self.cfg, {"url": self.url, "id": card["id"], "key": "typed"})
        self.assertEqual(Service.seen[-1]["key"], "typed")
        json_cards.probe(self.cfg, {"url": f"http://localhost:{self.server.server_address[1]}/x", "id": card["id"]})  # another name: not the same server
        self.assertIsNone(Service.seen[-1]["key"])

    def test_the_backup_carries_the_cards_with_their_keys_and_checks_them_on_restore(self):
        card = json_cards.save_card(self.cfg, self.card())
        out = backup.export(self.cfg, "0.0.0", self.tmp.name)
        self.assertEqual(out["settings"]["json_cards"]["cards"][0]["key"], "k-1")
        with tempfile.TemporaryDirectory() as other:
            two = Config(other)
            out["settings"]["json_cards"]["cards"].append({"id": "../../x", "name": "Bad", "url": "ftp://x", "fields": [{"path": "a"}]})
            out["settings"]["json_cards"]["cards"].append({"id": "jc00000001", "name": "Odd", "url": "http://10.0.0.2/x", "fields": []})
            backup.restore(two, out)
            self.assertEqual([c["id"] for c in two.data["json_cards"]["cards"]], [card["id"]])
            self.assertEqual(two.data["json_cards"]["cards"][0]["key"], "k-1")
        self.assertEqual(json_cards.clean_all("nonsense"), {"allow_outside": False, "cards": []})


class Routes(unittest.TestCase):
    def setUp(self):
        from starboard import terminal_setup
        from starboard.server import make_server
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        self.tmp = tempfile.TemporaryDirectory()
        self.service = serve()
        self.server, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = terminal_setup.Api(self.server.server_address[1])
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": "correct horse battery"})
        self.url = f"http://127.0.0.1:{self.service.server_address[1]}/api"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.service.shutdown()
        self.service.server_close()
        self.tmp.cleanup()

    def test_the_whole_way_through(self):
        from starboard.terminal_setup import Api, Problem
        self.assertEqual(self.api.call("GET", "/api/json-cards")["cards"], [])
        probe = self.api.call("POST", "/api/json-cards/probe", {"url": self.url, "key": "k-9"})
        self.assertIn("data.queue.total", [f["path"] for f in probe["fields"]])
        made = self.api.call("POST", "/api/json-cards", {"name": "Queue", "url": self.url, "key": "k-9", "refresh": 60,
                                                          "fields": [{"path": "data.queue.total", "label": "Waiting"}]})
        cid = made["card"]["id"]
        self.assertNotIn("k-9", json.dumps(made))
        self.assertEqual(self.api.call("GET", f"/api/json-cards/{cid}/answer")["items"][0]["value"], "7")
        self.api.call("PUT", "/api/config/general", {"dashboard": {"layout": "glance", "cards": [{"id": f"json:{cid}", "size": "half"}]}})
        with self.assertRaises(Problem):
            self.api.call("POST", "/api/json-cards", {"name": "Bad", "url": "http://8.8.8.8/x", "fields": [{"path": "a"}]})
        self.assertTrue(self.api.call("POST", "/api/json-cards/allow-outside", {"allow": True})["allow_outside"])
        self.api.call("POST", "/api/json-cards/delete", {"id": cid})
        self.assertEqual(self.api.call("GET", "/api/config")["dashboard"]["cards"], [])
        with self.assertRaises(Problem):
            self.api.call("GET", f"/api/json-cards/{cid}/answer")
        self.assertNotIn("k-9", json.dumps(self.api.call("GET", "/api/config")))
        signed_out = Api(self.server.server_address[1])
        with self.assertRaises(Problem):
            signed_out.call("GET", "/api/json-cards")
        with self.assertRaises(Problem):
            signed_out.call("POST", "/api/json-cards/probe", {"url": self.url})


if __name__ == "__main__":
    unittest.main()
