"""Connect an AI tool (DASH-627): the wizard's server side, named narrow keys and the new audit lines."""
import http.client
import json
import os
import re
import tempfile
import threading
import unittest

from starboard import ai_tools, api_v1, auth, mcp
from starboard.server import make_server

PASSWORD = "correct horse battery"


class AiToolsTest(unittest.TestCase):
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
        _, _, headers = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": PASSWORD})
        cls.cookie = [v.split(";")[0] for k, v in headers if k.lower() == "set-cookie" and v.startswith("starboard_session=")][0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    @classmethod
    def call(cls, method, path, body=None, cookie=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=15)
        h = {"Content-Type": "application/json", "X-Starboard": "1", **(headers or {})}
        if cookie:
            h["Cookie"] = cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read()
        out = (r.status, json.loads(raw or b"{}") if raw[:1] in (b"{", b"[") else {"raw": raw.decode("utf-8", "replace")}, r.getheaders())
        conn.close()
        return out

    def api(self, method, path, body=None, cookie=True):
        self.app.limits.clear("127.0.0.1")
        return self.call(method, path, body, self.cookie if cookie is True else cookie)[:2]

    def setUp(self):
        self.app.config.data["mcp_enabled"] = False
        api_v1._buckets.clear()

    def audit(self, what=None):
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            lines = [json.loads(line) for line in f]
        return [e for e in lines if what is None or e["what"] == what]

    def connect(self, **over):
        body = {"name": "Claude Desktop on the laptop", "scopes": ["apps", "downloads"], "expires_days": "90", "client": "claude-desktop", "password": PASSWORD, **over}
        return self.api("POST", "/api/ai-tools/connect", body)

    # The page's data -----------------------------------------------------------------------------------------------

    def test_it_needs_the_owner_signed_in(self):
        for method, path in (("GET", "/api/ai-tools"), ("POST", "/api/ai-tools/connect")):
            self.assertEqual(self.api(method, path, {}, cookie=False)[0], 401, path)

    def test_the_overview_has_the_words_the_wizard_shows(self):
        status, d = self.api("GET", "/api/ai-tools")
        self.assertEqual(status, 200)
        self.assertFalse(d["enabled"])
        self.assertEqual({s["id"] for s in d["scopes"]}, set(api_v1.ALL_SCOPES))  # a new scope cannot be added without words for it
        self.assertEqual({s["id"] for s in d["scopes"] if s["default"]}, {"apps", "downloads", "media", "system"})
        self.assertEqual([c["id"] for c in d["clients"]], ["claude-desktop", "claude-code", "other-mcp", "openai-compatible"])
        self.assertEqual([e["id"] for e in d["ends"]], ["30", "90", "365", "never"])
        self.assertEqual({t["name"] for t in d["tools"]}, {t[0] for t in mcp.TOOLS})
        self.assertIn("Tailscale Serve", json.dumps(d["tailscale"]))

    def test_every_tool_scope_has_plain_words(self):
        for tool in mcp.TOOLS:
            self.assertIn(tool[3], ai_tools.SCOPE_WORDS, tool[0])

    def test_tailscale_says_serve_and_never_funnel(self):
        text = " ".join(ai_tools.TAILSCALE["steps"])
        self.assertIn("tailscale serve --bg 8095", text)
        self.assertRegex(text, r"Never run tailscale funnel")
        self.assertNotRegex(text, r"tailscale funnel (--bg|on|\d)")  # the only funnel command it gives is one that checks it is off
        self.assertIn("never open port 8095 on your router", text.lower())

    def test_the_client_setup_fills_in_and_is_valid(self):
        for c in ai_tools.CLIENTS:
            for snip in c["snippets"]:
                self.assertIn("{{address}}", snip["text"], c["id"])
                text = snip["text"].replace("{{address}}", "https://server.tail1234.ts.net/api/v1/mcp").replace("{{key}}", "sb_read_abc123_KEY")
                self.assertNotIn("{{", text)
                if snip["language"] == "json":
                    got = json.loads(text)
                    self.assertEqual(got["mcpServers"]["starboard"]["args"][2], "https://server.tail1234.ts.net/api/v1/mcp")
            blob = json.dumps(c)
            for banned in (" See ", " see ", " Look ", " look ", "Activate", "activate", "click ", "Click "):
                self.assertNotIn(banned, blob, c["id"])
            self.assertNotIn("—", blob)

    def test_claude_code_asks_for_the_key_without_showing_it(self):
        snip = next(c for c in ai_tools.CLIENTS if c["id"] == "claude-code")["snippets"][0]["text"]
        self.assertIn("read -rs STARBOARD_KEY", snip)
        self.assertNotIn("{{key}}", snip)  # the key is never written into the line that is saved in history

    # Connecting ------------------------------------------------------------------------------------------------------

    def test_connect_turns_it_on_and_makes_a_named_read_only_key(self):
        status, d = self.connect()
        self.assertEqual(status, 200, d)
        self.assertTrue(self.app.config.data["mcp_enabled"])
        self.assertTrue(d["turned_on_now"])
        self.assertRegex(d["key"], r"^sb_read_[0-9a-f]{6}_[A-Za-z0-9_-]{43}$")
        self.assertEqual((d["item"]["name"], d["item"]["right"], d["item"]["scopes"]), ("Claude Desktop on the laptop", "read", ["apps", "downloads"]))
        self.assertEqual(d["can"], ["Your apps", "Downloads"])
        self.assertTrue(d["item"]["expires_at"])
        self.assertIn("Change anything", " ".join(d["cannot"]))
        # the key works for the tools its scopes cover, and only those
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        conn.request("POST", mcp.PATH, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}), {"Authorization": f"Bearer {d['key']}", "Content-Type": "application/json"})
        names = [t["name"] for t in json.loads(conn.getresponse().read())["result"]["tools"]]
        conn.close()
        self.assertEqual(set(names), {t[0] for t in mcp.TOOLS if t[3] in ("apps", "downloads")})

    def test_the_key_is_stored_only_as_a_hash_and_never_shown_again(self):
        _, d = self.connect(name="Hash check")
        with open(os.path.join(self.tmp.name, api_v1.KEYS_FILE)) as f:
            raw = f.read()
        self.assertNotIn(d["key"], raw)
        self.assertNotIn(d["key"][-30:], raw)
        self.assertIn(api_v1._digest(d["key"]), raw)
        self.assertEqual(oct(os.stat(os.path.join(self.tmp.name, api_v1.KEYS_FILE)).st_mode & 0o777), "0o600")
        _, listing = self.api("GET", "/api/ai-tools")
        _, keys = self.api("GET", "/api/keys")
        for text in (json.dumps(listing), json.dumps(keys)):
            self.assertNotIn(d["key"][-30:], text)
            self.assertNotIn(api_v1._digest(d["key"]), text)

    def test_the_wrong_password_changes_nothing(self):
        before = len(api_v1.list_keys(self.tmp.name))
        status, d = self.connect(password="wrong password here")
        self.assertEqual(status, 401)
        self.assertFalse(self.app.config.data["mcp_enabled"])
        self.assertEqual(len(api_v1.list_keys(self.tmp.name)), before)

    def test_a_bad_answer_changes_nothing(self):
        before = len(api_v1.list_keys(self.tmp.name))
        for over in ({"scopes": []}, {"scopes": ["apps", "root"]}, {"scopes": "apps"}, {"expires_days": "forever"}, {"client": "something-else"}, {"name": "   "}):
            status, d = self.connect(**over)
            self.assertEqual(status, 400, (over, d))
            self.assertFalse(self.app.config.data["mcp_enabled"], over)  # a failed key does not leave it turned on
        self.assertEqual(len(api_v1.list_keys(self.tmp.name)), before)

    def test_it_never_makes_a_key_that_may_manage(self):
        status, d = self.connect(right="manage")  # the right is not an input at all
        self.assertEqual(d["item"]["right"], "read")

    def test_a_key_made_here_is_listed_with_its_kind_and_can_be_revoked(self):
        _, d = self.connect(name="Listed", client="claude-code", expires_days="never")
        _, listing = self.api("GET", "/api/ai-tools")
        mine = next(k for k in listing["keys"] if k["id"] == d["item"]["id"])
        self.assertEqual((mine["client"], mine["right"], mine["expires_at"], mine["can"]), ("claude-code", "read", None, ["Your apps", "Downloads"]))
        self.assertNotIn("hash", mine)
        status, _ = self.api("DELETE", f"/api/keys/{d['item']['id']}")
        self.assertEqual(status, 200)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        conn.request("POST", mcp.PATH, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}), {"Authorization": f"Bearer {d['key']}", "Content-Type": "application/json"})
        self.assertEqual(conn.getresponse().status, 401)
        conn.close()

    def test_the_expiry_choices(self):
        for choice, days in (("30", 30), ("90", 90), ("365", 365)):
            _, d = self.connect(name=f"Ends {choice}", expires_days=choice)
            self.assertTrue(d["item"]["expires_at"], choice)
        _, d = self.connect(name="Never", expires_days="never")
        self.assertIsNone(d["item"]["expires_at"])

    # Audit lines -------------------------------------------------------------------------------------------------

    def test_the_audit_log_has_made_used_revoked_and_turned_on(self):
        _, d = self.connect(name="Audit trail", scopes=["apps"])
        made = [e for e in self.audit("key_created") if e["name"] == "Audit trail"][0]
        self.assertEqual((made["right"], made["scopes"], made["via"]), ("read", ["apps"], "ai-tools"))
        self.assertTrue(self.audit("mcp_turned_on"))
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        conn.request("POST", mcp.PATH, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "app_health", "arguments": {}}}),
                     {"Authorization": f"Bearer {d['key']}", "Content-Type": "application/json"})
        conn.getresponse().read()
        conn.close()
        used = [e for e in self.audit("key_used") if e["name"] == "Audit trail"]
        self.assertEqual(len(used), 1)
        self.assertTrue(used[0]["first"])
        call = [e for e in self.audit("mcp_call") if e["key_name"] == "Audit trail"][0]
        self.assertEqual((call["tool"], call["outcome"]), ("app_health", "done"))
        self.api("DELETE", f"/api/keys/{d['item']['id']}")
        self.assertEqual([e["name"] for e in self.audit("key_revoked") if e["key_id"] == d["item"]["id"]], ["Audit trail"])
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            text = f.read()
        self.assertNotIn(d["key"], text)
        self.assertNotIn(d["key"][-30:], text)

    def test_turning_it_off_in_settings_is_in_the_audit_log(self):
        self.app.config.data["mcp_enabled"] = True
        self.api("PUT", "/api/config/general", {"mcp_enabled": False})
        self.assertEqual(self.audit("mcp_turned_off")[-1]["via"], "settings")

    def test_recent_activity_is_in_plain_words_and_leaves_plug_ins_out(self):
        _, d = self.connect(name="Plain words", scopes=["apps"])
        api_v1.create_key(self.tmp.name, "Plug-in: Something", "read", ["apps"], 90)
        _, listing = self.api("GET", "/api/ai-tools")
        text = json.dumps(listing["activity"])
        self.assertIn("Plain words", text)
        self.assertIn("Key made. It may read: Your apps.", text)
        self.assertNotIn("Plug-in: Something", text)
        for row in listing["activity"]:
            self.assertEqual(set(row), {"time", "who", "what"})
            self.assertNotRegex(row["what"], r"mcp_|key_")

    def test_a_plug_in_key_does_not_write_key_used(self):
        key, item = api_v1.create_key(self.tmp.name, "Plug-in: Quiet", "read", ["apps"], 90)
        api_v1._used.clear()
        api_v1.note_use(self.tmp.name, api_v1.find_key(self.tmp.name, f"Bearer {key}"))
        self.assertFalse([e for e in self.audit("key_used") if e["name"] == "Plug-in: Quiet"])

    def test_key_used_is_written_after_a_quiet_spell_not_each_request(self):
        key, item = api_v1.create_key(self.tmp.name, "Quiet spell", "read", ["apps"], 90)
        for _ in range(3):
            api_v1._used.clear()
            api_v1.note_use(self.tmp.name, api_v1.find_key(self.tmp.name, f"Bearer {key}"))
        self.assertEqual(len([e for e in self.audit("key_used") if e["name"] == "Quiet spell"]), 1)
        keys = api_v1._load(self.tmp.name)
        for k in keys:
            if k["id"] == item["id"]:
                k["last_used_at"] = "2020-01-01T00:00:00Z"
        api_v1._save(self.tmp.name, keys)
        api_v1._used.clear()
        api_v1.note_use(self.tmp.name, api_v1.find_key(self.tmp.name, f"Bearer {key}"))
        lines = [e for e in self.audit("key_used") if e["name"] == "Quiet spell"]
        self.assertEqual([e["first"] for e in lines], [True, False])

    def test_no_audit_field_ever_holds_the_key(self):
        _, d = self.connect(name="Leak check")
        for e in self.audit():
            self.assertNotIn(d["key"], json.dumps(e))
            self.assertFalse([f for f in e if re.search(r"(?i)token|secret|password|authorization", f)])


if __name__ == "__main__":
    unittest.main()


class AiToolsPageTest(unittest.TestCase):
    """The page's files fit together: the page, its script, the parts it loads, the menu, the help and the words."""
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def read(self, *path):
        with open(os.path.join(self.ROOT, *path), encoding="utf-8") as f:
            return f.read()

    def test_the_page_is_in_the_security_menu_and_has_its_help(self):
        from starboard import shell
        self.assertEqual(shell.PAGES["settings-security-ai.html"][0], shell.PAGES["settings-security-keys.html"][0])
        self.assertIn("settings-security-ai.html", shell.HELP)
        self.assertTrue(os.path.exists(os.path.join(self.ROOT, "docs", "help", shell.HELP["settings-security-ai.html"][0])))

    def test_the_page_loads_what_it_uses(self):
        html = self.read("web", "settings-security-ai.html")
        parts = json.loads(self.read("web", "parts-used.json"))["use"]
        for part in ("error-summary", "secret-field", "wizard-steps"):
            self.assertIn(part, parts)
            self.assertIn(f"/js/parts/{part}.js", html)
            self.assertTrue(os.path.exists(os.path.join(self.ROOT, "web", "js", "parts", f"{part}.js")), part)
        self.assertIn('id="ai-tools"', html)
        self.assertIn('["#ai-tools", "startAiTools"]', self.read("web", "js", "settings-core.js"))

    def test_the_wizard_is_the_shared_one_and_makes_no_wizard_of_its_own(self):
        js = self.read("web", "js", "settings-ai.js")
        self.assertIn('"data-wizard": "connect-ai-tool"', js)
        self.assertNotIn("wizardFrame", js)
        for act in ("next", "back", "skip", "finish"):
            self.assertIn(f'"data-wizard-act": "{act}"', js)
        self.assertEqual(js.count("wizard__check"), 1)

    def test_nothing_polls_and_the_key_is_not_kept(self):
        js = self.read("web", "js", "settings-ai.js")
        for bad in ("setInterval", "localStorage", "sessionStorage", "document.cookie"):
            self.assertNotIn(bad, js)
        self.assertNotRegex(js, r"setTimeout\([^)]*\b(r\.key|key)\b")

    def test_the_words_the_server_gives_follow_the_content_rules(self):
        blob = json.dumps([ai_tools.SCOPE_WORDS, ai_tools.ALWAYS_CANNOT, ai_tools.ENDS, [{k: v for k, v in c.items() if k != "snippets"} for c in ai_tools.CLIENTS], ai_tools.TAILSCALE])  # code in a snippet is not prose
        for bad in (r"\bsee\b", r"\blook", r"\bclick", r"\btap\b", r"\benable", r"\bdisable", r"activat", r"\babove\b", r"\bbelow\b", r"\bplease\b",
                    r"\bjust\b", r"\beasy\b", r"\bsimple\b", r"—", r"\b(can't|won't|don't|doesn't|isn't|it's|you're|let's)\b"):
            self.assertIsNone(re.search(bad, blob, re.I), bad)
