"""AI assistants over MCP (DASH-464, API 1.7.0): POST /api/v1/mcp. JSON-RPC handling, keys and scopes, the off
switch, the rate limit, the audit log and each tool's answer against its own outputSchema."""
import http.client
import json
import os
import tempfile
import threading
import time
import unittest

from starboard import api_v1, auth, config, mcp
from starboard.server import make_server


class McpTest(unittest.TestCase):
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
        cls.app.config.upsert_service({"name": "Made-up Sonarr", "type": "sonarr", "url": "http://127.0.0.1:9", "api_key": "made-up-secret-key"})
        cls.key, cls.item = api_v1.create_key(cls.tmp.name, "AI assistant", "read", [], 90)
        cls.downloads_key, _ = api_v1.create_key(cls.tmp.name, "Downloads only", "read", ["downloads"], 90)
        cls.manager, _ = api_v1.create_key(cls.tmp.name, "Manager", "manage", [], 90)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def setUp(self):
        self.app.config.data["mcp_enabled"] = True
        api_v1._buckets.clear()

    def post(self, body, key=None, headers=None, method="POST", raw=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
             **({"Authorization": f"Bearer {key or self.key}"} if key is not False else {}), **(headers or {})}
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        conn.request(method, mcp.PATH, body=data, headers=h)
        r = conn.getresponse()
        out = r.read()
        conn.close()
        return r, (json.loads(out) if out and "json" in (r.getheader("Content-Type") or "") else None)

    def rpc(self, method, params=None, key=None, rid=1):
        msg = {"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params is not None else {})}
        r, body = self.post(msg, key=key)
        self.assertEqual(r.status, 200, body)
        self.assertEqual((body["jsonrpc"], body["id"]), ("2.0", rid))
        return body

    def call(self, name, arguments=None, key=None):
        return self.rpc("tools/call", {"name": name, "arguments": arguments or {}}, key=key)

    # The off switch ------------------------------------------------------------------------------------------------

    def test_off_until_activated(self):
        self.assertFalse(config.DEFAULTS["mcp_enabled"])
        self.assertEqual(config.GENERAL_RIGHTS["mcp_enabled"], "never")  # no API key can turn it on
        self.app.config.data["mcp_enabled"] = False
        r, body = self.post({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual((r.status, r.getheader("Content-Type"), body["code"]), (403, "application/problem+json", "mcp_off"))
        self.assertNotIn("tools", json.dumps(body))
        self.app.config.data["mcp_enabled"] = True
        self.assertIn("result", self.rpc("initialize"))

    def test_the_switch_is_a_general_setting_and_listed_as_access(self):
        self.app.config.update_general({"mcp_enabled": False})
        self.assertFalse(self.app.config.public()["mcp_enabled"])
        from starboard import access
        row = next(a for a in access.summary(self.app) if a["key"] == "mcp")
        self.assertFalse(row["on"])
        self.app.config.update_general({"mcp_enabled": True})
        self.assertTrue(next(a for a in access.summary(self.app) if a["key"] == "mcp")["on"])

    # Keys -----------------------------------------------------------------------------------------------------------

    def test_a_key_is_needed_and_refused_keys_are_audited(self):
        r, body = self.post({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, key=False)
        self.assertEqual((r.status, body["code"]), (401, "key_needed"))
        self.assertIn("Bearer", r.getheader("WWW-Authenticate"))
        r, _ = self.post({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, key=self.key[:-3] + "abc")
        self.assertEqual(r.status, 401)
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            self.assertIn('"path": "/api/v1/mcp"', f.read())

    def test_only_a_read_key(self):
        r, body = self.post({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, key=self.manager)
        self.assertEqual((r.status, body["code"]), (403, "read_key_needed"))

    def test_post_only(self):
        for method in ("GET", "DELETE", "PUT"):
            r, body = self.post(None, method=method)
            self.assertEqual((r.status, body["code"], r.getheader("Allow")), (405, "method_not_allowed", "POST"), method)

    def test_another_sites_page_and_name_are_refused(self):
        r, body = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"Origin": "http://attacker.example"})
        self.assertEqual((r.status, body["code"]), (403, "origin_refused"))
        r, body = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual((r.status, body["result"]), (200, {}))
        r, _ = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"Host": "attacker.example"})
        self.assertEqual(r.status, 421)  # host_allowed, as for every request

    def test_the_rate_limit_is_the_keys(self):
        api_v1._buckets[self.item["id"]] = (0, time.monotonic())
        r, body = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"})
        self.assertEqual((r.status, body["code"]), (429, "rate_limited"))
        self.assertTrue(r.getheader("Retry-After"))

    # JSON-RPC -------------------------------------------------------------------------------------------------------

    def test_initialize(self):
        out = self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})["result"]
        self.assertEqual(out["protocolVersion"], "2025-03-26")
        self.assertEqual(out["capabilities"], {"tools": {"listChanged": False}})
        self.assertEqual(out["serverInfo"]["name"], "starboard")
        self.assertTrue(out["instructions"])
        self.assertEqual(self.rpc("initialize", {"protocolVersion": "1999-01-01"})["result"]["protocolVersion"], mcp.PROTOCOL_VERSIONS[0])

    def test_notifications_and_client_answers_get_202(self):
        for msg in ({"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}},
                    {"jsonrpc": "2.0", "id": 5, "result": {}}):
            r, body = self.post(msg)
            self.assertEqual((r.status, body), (202, None), msg)

    def test_bad_messages(self):
        r, body = self.post(None, raw=b"{not json")
        self.assertEqual((r.status, body["error"]["code"], body["id"]), (400, mcp.PARSE_ERROR, None))
        r, body = self.post([{"jsonrpc": "2.0", "id": 1, "method": "ping"}])
        self.assertEqual((r.status, body["error"]["code"]), (400, mcp.INVALID_REQUEST))
        r, body = self.post({"id": 1, "method": "ping"})
        self.assertEqual((r.status, body["error"]["code"]), (400, mcp.INVALID_REQUEST))
        r, body = self.post({"jsonrpc": "2.0", "id": None, "method": "ping"})
        self.assertEqual((r.status, body["error"]["code"]), (400, mcp.INVALID_REQUEST))
        r, body = self.post({"jsonrpc": "2.0", "id": True, "method": "ping"})
        self.assertEqual((r.status, body["error"]["code"]), (400, mcp.INVALID_REQUEST))
        self.assertEqual(self.rpc("resources/list")["error"]["code"], mcp.METHOD_NOT_FOUND)
        self.assertEqual(self.rpc("tools/list", params=[1])["error"]["code"], mcp.INVALID_PARAMS)
        self.assertEqual(self.rpc("ping", rid="text-id")["id"], "text-id")

    def test_a_protocol_version_it_does_not_speak(self):
        r, body = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"MCP-Protocol-Version": "2099-01-01"})
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))
        r, _ = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers={"MCP-Protocol-Version": "2025-06-18"})
        self.assertEqual(r.status, 200)

    def test_a_large_message_is_refused(self):
        r, body = self.post(None, raw=b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"x":"' + b"a" * (70 * 1024) + b'"}}')
        self.assertEqual((r.status, body["code"]), (413, "too_large"))

    # Tools ----------------------------------------------------------------------------------------------------------

    def test_tools_list_follows_the_keys_scopes(self):
        tools = self.rpc("tools/list")["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], [t[0] for t in mcp.TOOLS])
        for t in tools:
            self.assertEqual(set(t), {"name", "title", "description", "inputSchema", "outputSchema", "annotations"})
            self.assertTrue(t["annotations"]["readOnlyHint"])  # nothing changes anything in this version
            self.assertFalse(t["annotations"]["destructiveHint"])
            self.assertEqual((t["inputSchema"]["type"], t["outputSchema"]["type"]), ("object", "object"))
        names = [t["name"] for t in self.rpc("tools/list", key=self.downloads_key)["result"]["tools"]]
        self.assertEqual(names, ["downloads_in_progress", "download_problems"])

    def test_a_tool_outside_the_keys_scopes_is_unknown(self):
        out = self.call("disk_space", key=self.downloads_key)
        self.assertEqual(out["error"]["code"], mcp.INVALID_PARAMS)
        self.assertEqual(self.call("made_up")["error"]["code"], mcp.INVALID_PARAMS)
        self.assertIn("result", self.call("downloads_in_progress", key=self.downloads_key))

    def test_arguments_are_checked(self):
        for name, args in (("search_library", {}), ("search_library", {"query": ""}), ("search_library", {"query": "x" * 121}),
                           ("recently_added", {"limit": 0}), ("recently_added", {"limit": 51}), ("recently_added", {"limit": "5"}),
                           ("recently_added", {"limit": True}), ("coming_up", {"month": "November"}), ("requests", {"pending_only": "yes"}),
                           ("disk_space", {"made_up": 1})):
            out = self.call(name, args)
            self.assertEqual(out.get("error", {}).get("code"), mcp.INVALID_PARAMS, (name, args, out))
        self.assertEqual(self.rpc("tools/call", {"name": "disk_space", "arguments": [1]})["error"]["code"], mcp.INVALID_PARAMS)

    def test_each_tool_answers_in_its_own_shape(self):
        args = {"search_library": {"query": "dune"}, "coming_up": {"month": "2026-11", "limit": 5}, "requests": {"pending_only": True}}
        for name, _title, _desc, _scope, schema, out_schema, _fn in mcp.TOOLS:
            out = self.call(name, args.get(name, {}))["result"]
            self.assertEqual(mcp.valid(schema, args.get(name, {})), "", name)
            if name == "search_library":  # the Library needs Reelix, which the tests do not have
                self.assertTrue(out["isError"])
                self.assertIn("Reelix", out["content"][0]["text"])
                continue
            self.assertFalse(out["isError"], (name, out))
            self.assertEqual(mcp.valid(out_schema, out["structuredContent"], name), "", name)
            self.assertEqual(json.loads(out["content"][0]["text"]), out["structuredContent"], name)
            self.assertNotIn("made-up-secret-key", json.dumps(out), name)

    def test_tools_read_the_same_as_the_api(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("GET", "/api/v1/system", headers={"Authorization": f"Bearer {self.key}"})
        system = json.loads(conn.getresponse().read())
        conn.close()
        self.assertEqual(self.call("disk_space")["result"]["structuredContent"]["disks"], system.get("disks") or [])

    def test_each_call_is_in_the_audit_log_without_its_arguments(self):
        self.call("recently_added", {"limit": 3})
        self.call("search_library", {"query": "a very private title"})
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            lines = [json.loads(line) for line in f if '"mcp_call"' in line]
        self.assertTrue(any(e["tool"] == "recently_added" and e["ok"] and e["key_id"] == self.item["id"] for e in lines))
        self.assertTrue(any(e["tool"] == "search_library" and not e["ok"] for e in lines))
        self.assertNotIn("private title", json.dumps(lines))

    def test_the_description_names_every_tool(self):
        spec = api_v1.spec()
        op = spec["paths"][mcp.PATH]["post"]
        for name, *_ in mcp.TOOLS:
            self.assertIn(name, op["description"])
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "help", "developers", "mcp-tools.md")) as f:
            page = f.read()
        for name, *_ in mcp.TOOLS:
            self.assertIn(f"`{name}`", page)


if __name__ == "__main__":
    unittest.main()
