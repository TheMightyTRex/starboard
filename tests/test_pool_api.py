"""System, Storage, Pool through Starboard's API (DASH-87): Starboard asks, the helper answers, and nothing that
changes a drive goes through without the password."""
import http.client
import json
import os
import tempfile
import threading
import unittest

from starboard import auth
from starboard import pool_helper as ph
from starboard.server import make_server
from tests.test_pool_helper import Computer, standard

PASSWORD = "correct horse battery"


class PoolApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        resp, _ = cls.request(None, "POST", "/api/setup", {"token": cls.app.setup_token, "password": PASSWORD}, cookie="")
        cls.cookie = resp.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()
        os.environ.pop("STARBOARD_POOL_DIR", None)

    def setUp(self):
        self.c = Computer(standard())
        os.environ["STARBOARD_POOL_DIR"] = self.c.exchange
        ph.publish_status(self.c.host)
        self.app.limits.clear("127.0.0.1")

    def request(self, method, path, body=None, cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", type(self).port if self else PoolApiTest.port, timeout=10)
        h = {"Content-Type": "application/json", "X-Starboard": "1"}
        cookie = cookie if cookie is not None else type(self).cookie
        if cookie:
            h["Cookie"] = cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        resp = conn.getresponse()
        return resp, json.loads(resp.read() or b"{}")

    def ask(self, body):
        resp, data = self.request("POST", "/api/pool/ask", body)
        self.assertEqual(resp.status, 200, data)
        ph.serve(self.c.host)
        _, answer = self.request("GET", "/api/pool/answer?id=" + data["request"])
        return answer

    def test_the_pool_page_reads_the_helper(self):
        _, data = self.request("GET", "/api/pool")
        self.assertTrue(data["set_up"])
        self.assertEqual({d["name"] for d in data["drives"]}, {"sda", "sdb", "sdc", "sdd", "sde"})
        os.environ["STARBOARD_POOL_DIR"] = ""
        _, data = self.request("GET", "/api/pool")
        self.assertFalse(data["set_up"])

    def test_a_change_needs_the_password_and_the_serial(self):
        plan = self.ask({"kind": "add", "drive": "sdb", "as": "pool", "erase": True})
        self.assertTrue(plan["ok"], plan)
        pid = plan["result"]["id"]
        resp, data = self.request("POST", "/api/pool/apply", {"plan": pid, "password": "wrong password"})
        self.assertEqual(resp.status, 401)
        self.assertEqual(os.listdir(os.path.join(self.c.exchange, "requests")), [])
        resp, data = self.request("POST", "/api/pool/apply", {"plan": pid, "password": PASSWORD})
        self.assertEqual(resp.status, 200)
        ph.serve(self.c.host)
        _, answer = self.request("GET", "/api/pool/answer?id=" + data["request"])
        self.assertFalse(answer["ok"])
        self.assertIn("9KX1", answer["error"])
        resp, data = self.request("POST", "/api/pool/apply", {"plan": pid, "password": PASSWORD,
                                                              "confirm": {self.c.byid("sdb"): "9kx1"}})
        ph.serve(self.c.host)
        _, answer = self.request("GET", "/api/pool/answer?id=" + data["request"])
        self.assertTrue(answer["ok"], answer)
        _, state = self.request("GET", "/api/pool")
        self.assertEqual(state["job"]["state"], "done")
        self.assertEqual(next(d for d in state["drives"] if d["name"] == "sdb")["use"], "pool")

    def test_only_known_fields_reach_the_helper(self):
        for bad in ({"kind": "format"}, {"kind": "add", "drive": "sdb; rm -rf /", "as": "pool"},
                    {"kind": "add", "drive": "sdb", "as": "pool", "folders": ["../etc"]}):
            resp, _ = self.request("POST", "/api/pool/ask", bad)
            self.assertEqual(resp.status, 400, bad)
        self.assertEqual(os.listdir(os.path.join(self.c.exchange, "requests")), [])

    def test_signed_out_is_refused(self):
        resp, _ = self.request("GET", "/api/pool", cookie="")
        self.assertEqual(resp.status, 401)


if __name__ == "__main__":
    unittest.main()
