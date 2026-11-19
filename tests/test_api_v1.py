"""The public API, version 1 (DASH-274): contract tests against starboard/openapi.json, keys and their rules.
DASH-281: run on every change; a change that breaks one is fixed, or becomes a new API version."""
import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from unittest import mock

from starboard import api_v1, auth
from starboard.server import make_server


SAMPLES = {"id": "123", "name": "livetv"}


RUN_ID = "0123456789ab"  # the update run made in setUpClass (API 1.2.0)


def sample(path, app_id="abc"):
    """A described path with a made-up value in each {name}; {id} of an app is the app's id when given."""
    if path.startswith("/api/v1/updates/runs/"):
        return path.replace("{id}", RUN_ID)
    return re.sub(r"\{(\w+)\}", lambda m: app_id if m.group(1) == "id" and app_id != "abc" else SAMPLES.get(m.group(1), "abc"), path)


def _resolve(spec, schema):
    while "$ref" in schema:
        node = spec
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        schema = node
    return schema


def check(spec, schema, value, where="answer"):
    """A small JSON Schema check: types, required properties, enums, array items. Enough for the contract."""
    schema = _resolve(spec, schema)
    kinds = schema.get("type")
    if kinds:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        py = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}
        assert any(isinstance(value, py[k]) and not (k in ("integer", "number") and isinstance(value, bool)) for k in kinds), \
            f"{where}: {type(value).__name__} is not {kinds}"
    if "enum" in schema:
        assert value in schema["enum"], f"{where}: {value!r} not in {schema['enum']}"
    if isinstance(value, dict):
        for name in schema.get("required", []):
            assert name in value, f"{where}: {name} is missing"
        for name, sub in (schema.get("properties") or {}).items():
            if name in value:
                check(spec, sub, value[name], f"{where}.{name}")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value[:20]):
            check(spec, schema["items"], v, f"{where}[{i}]")


class ApiV1Test(unittest.TestCase):
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
        cls.key, cls.item = api_v1.create_key(cls.tmp.name, "Contract tests", "read", [], 90)
        cls.manager, _ = api_v1.create_key(cls.tmp.name, "Contract manager", "manage", [], 90)
        cls.logs_key, _ = api_v1.create_key(cls.tmp.name, "AI assistant", "read", ["apps", "logs", "updates"], 90)
        cls.spec = api_v1.spec()
        from starboard import update_runs  # one finished run, so /api/v1/updates/runs/{id} has something to give
        run = update_runs._new(cls.tmp.name, "plugin:made-up", "plugin", "Made-up", "update", "1.0.0", "1.1.0", "you",
                               [("install", "Installing the new version")])
        with update_runs._lock:
            update_runs._runs.pop(run["id"])
            run["id"] = RUN_ID
            update_runs._runs[RUN_ID] = run
        update_runs._end(cls.tmp.name, run, "updated", "Made-up is now 1.1.0")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def get(self, path, key=None, headers=None, method="GET"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = {**({"Authorization": f"Bearer {key or self.key}"} if key is not False else {}), **(headers or {})}
        conn.request(method, path, headers=h)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r, (json.loads(raw) if raw else None)

    def test_every_route_is_described_and_every_description_is_a_route(self):
        described = {p for p, ops in self.spec["paths"].items() if "get" in ops}
        patterns = [p for p, *_ in api_v1.routes()]
        for path in described:
            self.assertTrue(path == "/api/v1/openapi.json" or any(re.match(p, sample(path)) for p in patterns), f"{path} has no route")
        for p in patterns:
            self.assertTrue(any(re.match(p, sample(d)) for d in described), f"{p} is not in openapi.json")

    def test_the_description_and_reference_are_what_the_tools_write(self):  # DASH-281: the tool had drifted
        import subprocess
        import sys
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for tool in ("tools/make_openapi.py", "tools/make_api_reference.py"):
            r = subprocess.run([sys.executable, tool, "--check"], cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr or r.stdout)

    def test_the_description_has_the_api_version(self):  # DASH-357: it said 1.1.0 while the API said 1.0.0
        self.assertEqual(self.spec["info"]["version"], api_v1.API_VERSION)

    def test_each_route_says_the_scope_it_needs(self):  # DASH-357: x-scope, the same as the code checks
        for path, ops in self.spec["paths"].items():
            if path.endswith("openapi.json") or "get" not in ops:
                continue
            scope = next(sc for p, sc, *_ in api_v1.routes() if re.match(p, sample(path)))
            self.assertIn("x-scope", ops["get"], path)
            self.assertEqual(ops["get"]["x-scope"], scope, path)

    def test_each_answer_matches_its_description(self):
        app_id = self.app.config.data["services"][0]["id"]
        for path, ops in self.spec["paths"].items():
            if "get" not in ops or path == "/api/v1/events":
                continue
            query = "?q=dune" if path.endswith("/search") else ""
            key = self.logs_key if ops["get"].get("x-scope") in api_v1.EXPLICIT_SCOPES else None
            r, body = self.get(sample(path, app_id) + query, key=key)
            self.assertTrue(r.getheader("X-Request-Id"))
            if r.status == 409 and "409" in ops["get"]["responses"]:  # needs Reelix, which the tests do not have
                self.assertEqual(body["code"], "not_set_up", path)
                continue
            self.assertEqual(r.status, 200, f"{path}: {body}")
            check(self.spec, ops["get"]["responses"]["200"]["content"]["application/json"]["schema"], body, path)

    def test_no_secret_in_any_answer(self):
        for path, ops in self.spec["paths"].items():
            if "get" not in ops or path == "/api/v1/events":
                continue
            _, body = self.get(sample(path, self.app.config.data["services"][0]["id"]))
            text = json.dumps(body)
            self.assertNotIn("made-up-secret-key", text, path)
            self.assertNotIn(self.key, text, path)
            self.assertNotIn("hash", json.dumps(body.get("components", {}) if path.endswith("openapi.json") else body).lower().replace("hashes", ""), path)

    def test_keys_only_as_a_bearer_header(self):
        r, body = self.get("/api/v1/apps", key=False)
        self.assertEqual((r.status, r.getheader("Content-Type"), body["code"]), (401, "application/problem+json", "key_needed"))
        r, _ = self.get(f"/api/v1/apps?key={self.key}", key=False)
        self.assertEqual(r.status, 401)
        r, _ = self.get("/api/v1/apps", key=self.key[:-3] + "abc")
        self.assertEqual(r.status, 401)

    def test_etag_gives_304(self):
        r, _ = self.get("/api/v1/apps")
        tag = r.getheader("ETag")
        r2, body = self.get("/api/v1/apps", headers={"If-None-Match": tag})
        self.assertEqual((r2.status, body), (304, None))

    def test_paging_and_bad_values(self):
        for i in range(3):
            self.app.config.upsert_service({"name": f"Extra {i}", "type": "radarr", "url": f"http://127.0.0.1:{10 + i}"})
        r, body = self.get("/api/v1/apps?limit=2")
        self.assertEqual(len(body["items"]), 2)
        self.assertIn('rel="next"', r.getheader("Link"))
        _, more = self.get(f"/api/v1/apps?limit=2&cursor={body['next_cursor']}")
        self.assertNotEqual(more["items"][0]["id"], body["items"][0]["id"])
        r, body = self.get("/api/v1/apps?limit=500")
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))

    def test_writes_are_refused_for_now(self):
        r, body = self.get("/api/v1/apps", method="POST")
        self.assertEqual((r.status, body["code"]), (405, "method_not_allowed"))

    def test_a_scoped_key_sees_nothing_else(self):
        key, _ = api_v1.create_key(self.tmp.name, "Downloads only", "read", ["downloads"], None)
        self.assertEqual(self.get("/api/v1/downloads", key=key)[0].status, 200)
        r, body = self.get("/api/v1/apps", key=key)
        self.assertEqual((r.status, body["code"]), (404, "not_found"))

    def test_download_issues_with_the_downloads_scope(self):  # DASH-434, API 1.3.0
        key, _ = api_v1.create_key(self.tmp.name, "Issues reader", "read", ["downloads"], None)
        r, body = self.get("/api/v1/downloads/issues", key=key)
        self.assertEqual(r.status, 200, body)
        self.assertEqual((body["count"], body["items"]), (0, []))
        self.assertTrue(body["markdown"].startswith("# Download issues from Starboard"))
        self.assertEqual(len(body["errors"]), 1)  # the made-up Sonarr does not answer, and the export says so
        self.assertNotIn("made-up-secret-key", json.dumps(body))
        self.assertNotIn("127.0.0.1", json.dumps(body))
        other, _ = api_v1.create_key(self.tmp.name, "Apps only", "read", ["apps"], None)
        r, body = self.get("/api/v1/downloads/issues", key=other)
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        self.assertEqual(self.get("/api/v1/downloads/issues", method="POST")[0].status, 405)

    def test_a_plugin_key_without_scopes_reads_nothing(self):
        # No scopes means everything only for people's own keys; a plug-in reads exactly what was approved (P8).
        key, _ = api_v1.create_key(self.tmp.name, "Plug-in: Network only", "read", [], None)
        r, body = self.get("/api/v1/apps", key=key)
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        mine, _ = api_v1.create_key(self.tmp.name, "My script", "read", [], None)
        self.assertEqual(self.get("/api/v1/apps", key=mine)[0].status, 200)

    def test_rate_limit_answers_429_with_retry_after(self):
        key, item = api_v1.create_key(self.tmp.name, "Busy", "read", [], 1)
        api_v1._buckets[item["id"]] = (0, __import__("time").monotonic())
        r, body = self.get("/api/v1/", key=key)
        self.assertEqual((r.status, body["code"]), (429, "rate_limited"))
        self.assertTrue(r.getheader("Retry-After"))

    def test_revoked_and_expired_keys_stop_working(self):
        key, item = api_v1.create_key(self.tmp.name, "Short lived", "read", [], 1)
        self.assertEqual(self.get("/api/v1/me", key=key)[1]["name"], "Short lived")
        api_v1.revoke_key(self.tmp.name, item["id"])
        self.assertEqual(self.get("/api/v1/me", key=key)[0].status, 401)
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            lines = [json.loads(line)["what"] for line in f]
        self.assertIn("key_revoked", lines)
        with self.assertRaises(ValueError):
            api_v1.create_key(self.tmp.name, "Writer", "admin")

    # Version 1.1 (DASH-274): the manage right, writes, Idempotency-Key, events -----------------------------------

    def send_json(self, method, path, body=None, key=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        raw = json.dumps(body if body is not None else {}).encode()
        h = {"Authorization": f"Bearer {key or self.manager}", "Content-Type": "application/json", **(headers or {})}
        conn.request(method, path, body=raw, headers=h)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        return r, (json.loads(data) if data else None)

    def test_each_write_is_described_with_its_right(self):
        for path, ops in self.spec["paths"].items():
            for method, op in ops.items():
                if method == "get":
                    continue
                if path == "/api/v1/mcp":  # DASH-464: read keys only, each tool with its own scope (tests/test_mcp.py)
                    self.assertEqual((op.get("x-right"), op.get("x-scope")), ("read", None))
                    continue
                self.assertEqual(op.get("x-right"), "manage", f"{method} {path}")
                found = [a for a in api_v1.actions() if a[1] == method.upper() and re.match(a[0], sample(path))]
                self.assertTrue(found, f"{method} {path} has no route")
                self.assertEqual(op["x-scope"], found[0][2], path)
        for pattern, method, *_ in api_v1.actions():
            self.assertTrue(any(method.lower() in ops and re.match(pattern, sample(p)) for p, ops in self.spec["paths"].items()),
                            f"{method} {pattern} is not in openapi.json")

    def test_a_read_key_cannot_write(self):
        r, body = self.send_json("POST", "/api/v1/download-hours", {"action": "pause"}, key=self.key)
        self.assertEqual((r.status, body["code"]), (403, "right_needed"))

    def test_a_manage_key_writes_and_each_write_is_in_the_audit_log(self):
        r, body = self.send_json("POST", "/api/v1/download-hours", {"action": "sideways"})
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))
        r, body = self.send_json("POST", "/api/v1/download-hours", {"action": "pause"})
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))  # download hours are not active here
        self.assertIn("Activate download hours", body["title"])
        r, body = self.send_json("POST", "/api/v1/containers/check")
        self.assertEqual((r.status, body["available"]), (200, False))  # no Docker in the tests
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            writes = [json.loads(line) for line in f if '"api_write"' in line]
        self.assertTrue(any(w["path"] == "/api/v1/containers/check" and w["status"] == 200 for w in writes))
        self.assertTrue(all(self.manager not in json.dumps(w) for w in writes))

    def test_writes_check_scope_before_right_and_refuse_bad_bodies(self):
        key, _ = api_v1.create_key(self.tmp.name, "Downloads manager", "manage", ["downloads"], None)
        r, body = self.send_json("POST", "/api/v1/alerts/test", key=key)
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("POST", "/api/v1/download-hours", body=b"[1, 2]", headers={"Authorization": f"Bearer {key}"})
        r = conn.getresponse()
        self.assertEqual((r.status, json.loads(r.read())["code"]), (400, "bad_request"))
        conn.close()
        r, body = self.send_json("POST", "/api/v1/download-hours", {"action": "x" * 70000}, key=key)
        self.assertEqual((r.status, body["code"]), (413, "too_large"))

    def test_a_download_action_needs_a_download_app(self):
        app_id = self.app.config.data["services"][0]["id"]
        r, body = self.send_json("POST", "/api/v1/downloads/actions", {"app_id": "nope", "id": 1, "action": "remove"})
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        r, body = self.send_json("POST", "/api/v1/downloads/actions", {"app_id": app_id, "id": "x", "action": "remove"})
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))
        r, body = self.send_json("POST", "/api/v1/downloads/actions", {"app_id": app_id, "id": 1, "action": "delete-everything"})
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))

    def test_backup_copies_and_test_connection(self):
        """DASH-452 (API 1.6.0): where copies go, and Test connection by key; never a secret in either answer."""
        from starboard import backup_copies
        r, body = self.get("/api/v1/backup/copies")
        self.assertEqual((r.status, body["kind"]), (200, "off"))
        r, body = self.send_json("POST", "/api/v1/backup/copies/test")
        self.assertEqual((r.status, body["code"]), (409, "not_set_up"))
        backup_copies.save(self.tmp.name, {**backup_copies.settings(self.tmp.name), "kind": "smb", "smb": "//192.0.2.4/backups", "smb_user": "alex"},
                           {"smb_password": "share-secret-123", "rclone_config": ""})
        done = "STEP-FOLDER\nSTEP-WRITE\nSTEP-READ\nSTEP-REMOVE\nFREE 5000000000\nCOUNT 2\n"
        with mock.patch("starboard.containers.available", return_value=True), mock.patch.object(backup_copies, "_run", return_value=(0, done)), \
                mock.patch.object(backup_copies, "newest_size", return_value=None):
            r, body = self.send_json("POST", "/api/v1/backup/copies/test")
        self.assertEqual((r.status, body["ok"], body["tested"]["free"]), (200, True, 5000000000))
        self.assertNotIn("share-secret-123", json.dumps(body))
        r, body = self.get("/api/v1/backup/copies")
        self.assertEqual((body["kind"], body["where"], body["tested"]["ok"]), ("smb", "//192.0.2.4/backups", True))
        self.assertNotIn("share-secret-123", json.dumps(body))
        reader, _ = api_v1.create_key(self.tmp.name, "Reader", "read", [], None)
        r, body = self.send_json("POST", "/api/v1/backup/copies/test", key=reader)
        self.assertEqual(r.status, 403)
        other, _ = api_v1.create_key(self.tmp.name, "Downloads", "manage", ["downloads"], None)
        r, body = self.get("/api/v1/backup/copies", key=other)
        self.assertEqual(r.status, 404)  # without the system scope the route is not there for this key

    def test_the_library_needs_reelix(self):
        r, body = self.get("/api/v1/library")
        self.assertEqual((r.status, body["code"]), (409, "not_set_up"))
        r, body = self.send_json("POST", "/api/v1/library/refresh", {"tab": "films"})
        self.assertEqual((r.status, body["code"]), (409, "not_set_up"))

    def test_idempotency_key_gives_the_first_answer_again(self):
        first, body = self.send_json("POST", "/api/v1/containers/check", headers={"Idempotency-Key": "check-1"})
        again, body2 = self.send_json("POST", "/api/v1/containers/check", headers={"Idempotency-Key": "check-1"})
        self.assertEqual((first.status, again.status, body, again.getheader("Idempotent-Replayed")), (200, 200, body2, "true"))
        r, body = self.send_json("POST", "/api/v1/containers/check", headers={"Idempotency-Key": "bad key!"})
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))

    def test_bad_query_values(self):
        for path in ("/api/v1/calendar?month=2026-13", "/api/v1/system/history?hours=5", "/api/v1/library/search?q=",
                     "/api/v1/history?which=everything"):
            r, body = self.get(path)
            self.assertIn(r.status, (400, 409), path)

    def test_events_stream_with_scopes_and_resume(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/api/v1/events", headers={"Authorization": f"Bearer {self.key}"})
        r = conn.getresponse()
        self.assertEqual((r.status, r.getheader("Content-Type").split(";")[0]), (200, "text/event-stream"))
        self.assertEqual(r.fp.readline(), b"retry: 10000\n")
        r.fp.readline(), r.fp.readline()  # ": open" and the blank line
        api_v1.publish("app.down", {"app": "Made-up Sonarr", "type": "sonarr", "api_key": "made-up-secret-key"})
        lines = [r.fp.readline() for _ in range(3)]
        self.assertTrue(lines[0].startswith(b"id: "))
        self.assertEqual(lines[1], b"event: starboard.app.down\n")
        event = json.loads(lines[2][6:])
        self.assertEqual((event["type"], event["data"]["app"], event["specversion"]), ("starboard.app.down", "Made-up Sonarr", "1.0"))
        self.assertNotIn("made-up-secret-key", lines[2].decode())
        conn.close()
        # A key scoped to downloads does not hear app events; resuming from an id gives what came after it.
        key, _ = api_v1.create_key(self.tmp.name, "Downloads events", "read", ["downloads"], None)
        last = int(event["id"])
        api_v1.publish("app.up", {"app": "Made-up Sonarr"})
        api_v1.publish("download.finished", {"title": "A made-up film", "app": "Made-up Radarr"})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/api/v1/events", headers={"Authorization": f"Bearer {key}", "Last-Event-ID": str(last)})
        r = conn.getresponse()
        for _ in range(3):
            r.fp.readline()
        lines = [r.fp.readline() for _ in range(3)]
        self.assertEqual(lines[1], b"event: starboard.download.finished\n")
        conn.close()

    def test_logs_only_when_ticked_and_with_addresses_taken_out(self):  # DASH-76
        from starboard import logs
        logs.event("warning", "apps", "Sonarr at http://192.168.1.21:8989 said apikey=abcdef123456 for sam@starboard-pi.local")
        r, body = self.get("/api/v1/logs")  # a key with no scopes
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        r, body = self.get("/api/v1/logs?level=problems", key=self.logs_key)
        self.assertEqual(r.status, 200)
        text = json.dumps(body)
        for secret in ("192.168.1.21", "abcdef123456", "sam@starboard-pi.local"):
            self.assertNotIn(secret, text)
        r, body = self.get("/api/v1/logs?level=everything", key=self.logs_key)
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))

    # Version 1.4.0 (DASH-451): the log limits and Delete all logs, only with the logs scope ---------------------------

    def test_log_limits_only_when_ticked(self):
        r, body = self.get("/api/v1/logs/limits")  # a key with no scopes
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        r, body = self.get("/api/v1/logs/limits", key=self.logs_key)
        self.assertEqual((r.status, body["keep_days"], body["max_mb"]), (200, 30, 50))
        self.assertEqual(body["max_mb_choices"], [10, 25, 50, 100, 250, 500])
        self.assertFalse(body["apps"]["available"])  # no Docker in the tests
        r, body = self.send_json("POST", "/api/v1/logs/limits", {"keep_days": 14}, key=self.logs_key)  # read only
        self.assertEqual((r.status, body["code"]), (403, "right_needed"))
        r, body = self.send_json("POST", "/api/v1/logs/limits", {"keep_days": 14})  # a manage key with no scopes
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        r, body = self.send_json("POST", "/api/v1/logs/delete", {"confirm": True})
        self.assertEqual((r.status, body["code"]), (404, "not_found"))

    def test_a_manage_key_with_logs_changes_the_limits_and_deletes_all_logs(self):
        from starboard import logs
        key, _ = api_v1.create_key(self.tmp.name, "Log keeper", "manage", ["logs"], None)
        before = dict(self.app.config.data["logs"])
        self.addCleanup(lambda: self.app.config.data["logs"].update(before))
        for body in ({}, {"keep_days": 3}, {"max_mb": "lots"}, {"max_mb": 7}):
            r, out = self.send_json("POST", "/api/v1/logs/limits", body, key=key)
            self.assertEqual((r.status, out["code"]), (400, "bad_request"), body)
        r, out = self.send_json("POST", "/api/v1/logs/limits", {"keep_days": 14, "max_mb": 25}, key=key)
        self.assertEqual((r.status, out["keep_days"], out["max_mb"], out["removed"]), (200, 14, 25, 0))
        self.assertEqual(self.app.config.data["logs"]["max_mb"], 25)
        logs.event("warning", "apps", "Something to delete")
        for body in ({}, {"confirm": "yes"}):
            r, out = self.send_json("POST", "/api/v1/logs/delete", body, key=key)
            self.assertEqual((r.status, out["code"]), (400, "bad_request"), body)
        r, out = self.send_json("POST", "/api/v1/logs/delete", {"confirm": True}, key=key)
        self.assertEqual(r.status, 200)
        self.assertGreater(out["freed"], 0)
        self.assertEqual(out["summary"]["days"], 1)  # today's file, emptied, with the line saying who
        r, rows = self.get("/api/v1/logs", key=self.logs_key)
        self.assertRegex(rows["items"][0]["message"], r"^All logs deleted by the API key Log keeper: ")
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            writes = [json.loads(line) for line in f if '"api_write"' in line]
        self.assertEqual([w["path"] for w in writes], ["/api/v1/logs/delete"])  # emptied, then the delete itself

    # Version 1.2.0 (DASH-424): updates, only with the updates scope -------------------------------------------------

    def test_updates_only_when_ticked(self):
        r, body = self.get("/api/v1/updates")  # a key with no scopes
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        r, body = self.send_json("POST", "/api/v1/updates", {"target": "starboard"})  # a manage key with no scopes
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        r, body = self.get("/api/v1/updates", key=self.logs_key)
        self.assertEqual(r.status, 200)
        self.assertEqual(body["items"][0]["id"], "starboard")
        r, body = self.send_json("POST", "/api/v1/updates", {"target": "starboard"}, key=self.logs_key)  # read only
        self.assertEqual((r.status, body["code"]), (403, "right_needed"))

    def test_update_actions_say_why_not(self):
        key, _ = api_v1.create_key(self.tmp.name, "Updater", "manage", ["updates"], None)
        for body, status, code in (({"target": "everything"}, 400, "bad_request"), ({}, 400, "bad_request"),
                                   ({"target": "starboard"}, 409, "cannot_update"),  # no newer release is known here
                                   ({"target": "plugin:not-added"}, 404, "not_found"),
                                   ({"target": "reelix"}, 409, "cannot_update")):  # no Docker in the tests
            r, out = self.send_json("POST", "/api/v1/updates", body, key=key)
            self.assertEqual((r.status, out["code"]), (status, code), body)
        for target in ("starboard", "app:abc"):
            r, out = self.send_json("POST", "/api/v1/updates/rollback", {"target": target}, key=key)
            self.assertEqual((r.status, out["code"]), (409, "cannot_update"), target)
            self.assertIn("by itself", out["detail"])
        r, out = self.send_json("POST", "/api/v1/updates/rollback", {"target": "plugin:not-added"}, key=key,
                                headers={"Idempotency-Key": "rb-1"})
        again, out2 = self.send_json("POST", "/api/v1/updates/rollback", {"target": "plugin:not-added"}, key=key,
                                     headers={"Idempotency-Key": "rb-1"})
        self.assertEqual((r.status, again.status), (404, 404))
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            writes = [json.loads(line) for line in f if '"api_write"' in line]
        self.assertTrue(any(w["path"] == "/api/v1/updates" and w["status"] == 409 for w in writes))

    def test_a_run_reads_back_with_its_steps(self):
        r, body = self.get(f"/api/v1/updates/runs/{RUN_ID}", key=self.logs_key)
        self.assertEqual((r.status, body["state"], body["steps"][0]["state"]), (200, "updated", "done"))
        r, body = self.get("/api/v1/updates/runs/ffffffffffff", key=self.logs_key)
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        r, body = self.get("/api/v1/updates/runs", key=self.logs_key)
        self.assertEqual(body["items"][0]["id"], RUN_ID)

    def test_events_are_capped(self):
        old = api_v1._event_state["streams"]
        api_v1._event_state["streams"] = api_v1.MAX_STREAMS
        try:
            r, body = self.get("/api/v1/events")
            self.assertEqual((r.status, body["code"]), (503, "too_many_streams"))
        finally:
            api_v1._event_state["streams"] = old


if __name__ == "__main__":
    unittest.main()
