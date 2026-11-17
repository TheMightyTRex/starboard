"""Connect a cloud service (DASH-452): the checks on everything entered or pasted, the two ways to sign in (the link with
the address pasted back, and the phone with the device flow) against a stand-in sign-in service, the time limits, the
clean-up when the slide-out closes, and Save. Test connection on Copies off this computer is at the end. No real cloud
account is used; the real rclone runs are in tools/try-cloud-connect.py."""
import json
import os
import tempfile
import time
import unittest
from unittest import mock

from starboard import backup_copies, cloud_connect as cc
from tests.oauth_stand_in import StandIn


def unpadded(blob):
    import base64
    return base64.b64decode(blob + "=" * (-len(blob) % 4)).decode()


def wait_for(fn, limit=8.0):
    until = time.time() + limit
    while time.time() < until:
        if fn():
            return True
        time.sleep(0.05)
    return False


class FakeRunner:
    """Stands in for the helper container: plays rclone authorize's part through the same files."""

    def __init__(self, link="https://www.dropbox.com/oauth2/authorize?client_id=x&state=Abc123_state-XYZ&redirect_uri=http%3A%2F%2Flocalhost%3A53682%2F"):
        self.link, self.started, self.removed, self.scripts = link, [], [], []
        self.short_answer = (0, "")

    def authorize(self, sess):
        self.started.append(sess["id"])
        sess["cid"] = "fake-" + sess["id"]
        with open(os.path.join(sess["work"], "link"), "w") as f:
            f.write(self.link + "\n")

    def finish(self, sess, token=None):
        """What rclone does when the answer reaches its listener: says the token and ends."""
        with open(os.path.join(sess["work"], "out"), "w") as f:
            if token:
                f.write("NOTICE: Got code\nPaste the following into your remote machine --->\n" + json.dumps(token) + "\n<---End paste\n")
            else:
                f.write("ERROR: Failed to get token: oauth2: cannot fetch token: 400\n")
        with open(os.path.join(sess["work"], "done"), "w") as f:
            f.write("0")

    def short(self, sess, script, work):
        self.scripts.append(script)
        if "config create" in script:
            with open(os.path.join(work, "rclone.conf"), "w") as f:
                f.write(f"[{cc.REMOTE}]\ntype = webdav\nurl = https://cloud.example/\nvendor = nextcloud\nuser = alex\npass = OBSCURED\n")
        return self.short_answer

    def remove(self, cid):
        self.removed.append(cid)


class Base(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.run = FakeRunner()
        self.p = [mock.patch.object(cc, "RUN", self.run)]
        for p in self.p:
            p.start()

    def tearDown(self):
        cc.cancel()
        for p in self.p:
            p.stop()


class Services(unittest.TestCase):
    def test_the_list_is_in_the_agreed_order(self):
        self.assertEqual([s["id"] for s in cc.services()], ["drive", "onedrive", "dropbox", "b2", "s3", "webdav", "sftp", "own"])

    def test_phone_is_offered_only_with_starboard_own_sign_in(self):
        with mock.patch.dict(os.environ, {"STARBOARD_GOOGLE_CLIENT_ID": "", "STARBOARD_MICROSOFT_CLIENT_ID": ""}):
            self.assertFalse(any(s["phone"] for s in cc.offered()))
        with mock.patch.dict(os.environ, {"STARBOARD_GOOGLE_CLIENT_ID": "g.apps.example", "STARBOARD_MICROSOFT_CLIENT_ID": "m-id"}):
            self.assertEqual([s["id"] for s in cc.offered() if s["phone"]], ["drive", "onedrive"])
        with mock.patch.dict(os.environ, {"STARBOARD_GOOGLE_CLIENT_ID": "g"}):
            self.assertFalse(next(s for s in cc.offered() if s["id"] == "dropbox")["phone"])  # Dropbox has no device flow


class PastedAddress(unittest.TestCase):
    sess = {"auth_state": "Abc123_state-XYZ"}

    def ok(self, text):
        return cc.check_answer(self.sess, text)

    def bad(self, text, kind=ValueError):
        with self.assertRaises(kind):
            cc.check_answer(self.sess, text)

    def test_the_address_the_sign_in_ends_on(self):
        self.assertEqual(self.ok("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=4/0AbCd-e_f"),
                         "http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=4%2F0AbCd-e_f")
        self.assertTrue(self.ok("http://localhost:53682/?code=xyz&state=Abc123_state-XYZ&scope=drive.file").startswith("http://127.0.0.1:53682/?"))
        self.assertTrue(self.ok("  localhost:53682/?code=xyz&state=Abc123_state-XYZ  "))  # a phone hides http://

    def test_only_the_state_and_code_are_handed_on(self):
        out = self.ok("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=abc&next=http%3A%2F%2Fevil.example")
        self.assertNotIn("evil", out)

    def test_other_places_are_refused(self):
        for text in ("http://evil.example:53682/?state=Abc123_state-XYZ&code=a", "http://127.0.0.1.evil.example:53682/?state=Abc123_state-XYZ&code=a",
                     "http://127.0.0.1@evil.example:53682/?state=Abc123_state-XYZ&code=a", "https://127.0.0.1:53682/?state=Abc123_state-XYZ&code=a",
                     "http://127.0.0.1:8095/?state=Abc123_state-XYZ&code=a", "http://127.0.0.1/?state=Abc123_state-XYZ&code=a",
                     "http://127.0.0.1:53682/auth?state=Abc123_state-XYZ&code=a", "http://user@127.0.0.1:53682/?state=Abc123_state-XYZ&code=a",
                     "javascript:alert(1)", "file:///etc/passwd", "http://[::1]:53682/?state=Abc123_state-XYZ&code=a",
                     "http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=a#x", "http://127.0.0.1:99999/?state=Abc123_state-XYZ&code=a"):
            self.bad(text)

    def test_the_state_must_be_this_sign_in(self):
        self.bad("http://127.0.0.1:53682/?state=OtherState123&code=abc")
        self.bad("http://127.0.0.1:53682/?code=abc")
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&state=Abc123_state-XYZ&code=abc")

    def test_a_code_is_needed_and_must_look_like_one(self):
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ")
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=")
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=a%22b")
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=" + "a" * 3000)

    def test_spaces_quotes_and_line_breaks_are_refused(self):
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=a b")
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=a\nb")
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&code='a'")

    def test_a_refusal_at_the_service_says_so(self):
        self.bad("http://127.0.0.1:53682/?state=Abc123_state-XYZ&error=access_denied", cc.CloudError)


class Fields(unittest.TestCase):
    def test_each_keys_service(self):
        self.assertEqual(cc.check_fields("b2", {"account": "0012ab", "key": "K001xyz/+="}), {"account": "0012ab", "key": "K001xyz/+="})
        self.assertEqual(cc.check_fields("s3", {"access_key_id": "AKIA1", "secret_access_key": "s"}), {"access_key_id": "AKIA1", "secret_access_key": "s"})
        got = cc.check_fields("webdav", {"url": "https://cloud.example/remote.php/dav/files/alex/", "vendor": "nextcloud", "user": "alex", "pass": " a pass "})
        self.assertEqual(got["pass"], " a pass ")  # kept as entered
        self.assertEqual(cc.check_fields("sftp", {"host": "nas.home", "user": "alex", "pass": "p"})["port"], "22")

    def test_what_is_refused_names_the_field(self):
        cases = [("b2", {"account": "", "key": "k"}, "account"), ("b2", {"account": "a b", "key": "k"}, "account"),
                 ("s3", {"endpoint": "javascript:alert(1)", "access_key_id": "a", "secret_access_key": "s"}, "endpoint"),
                 ("s3", {"endpoint": "https://alex:pw@s3.example", "access_key_id": "a", "secret_access_key": "s"}, "endpoint"),
                 ("s3", {"region": "EU West", "access_key_id": "a", "secret_access_key": "s"}, "region"),
                 ("webdav", {"url": "https://cloud.example/ x", "vendor": "nextcloud", "user": "a", "pass": "p"}, "url"),
                 ("webdav", {"url": "https://cloud.example/", "vendor": "box", "user": "a", "pass": "p"}, "vendor"),
                 ("webdav", {"url": "https://cloud.example/", "vendor": "other", "user": "a", "pass": "p\nq"}, "pass"),
                 ("sftp", {"host": "nas;rm -rf", "user": "a", "pass": "p"}, "host"),
                 ("sftp", {"host": "nas", "port": "70000", "user": "a", "pass": "p"}, "port")]
        for sid, given, field in cases:
            with self.assertRaises(ValueError, msg=(sid, given)) as e:
                cc.check_fields(sid, given)
            self.assertEqual(str(e.exception).split("|")[0], field)

    def test_folders(self):
        self.assertEqual(cc.check_folder(" /starboard-backups/ "), "starboard-backups")
        self.assertEqual(cc.check_folder("my-bucket/Starboard copies"), "my-bucket/Starboard copies")
        for bad in ("", "..", "a/../b", "a\\b", "a:b", "a\nb", "/".join(["a"] * 11), "x" * 101, "a*b"):
            with self.assertRaises(ValueError, msg=bad):
                cc.check_folder(bad)

    def test_a_pasted_remote(self):
        remote, conf = cc.check_pasted_config("mine:backups", "[mine]\ntype = webdav\nurl = https://cloud.example/")
        self.assertEqual(remote, "mine:backups")
        with self.assertRaises(ValueError):
            cc.check_pasted_config("mine:backups", "[other]\ntype = webdav")


class Token(unittest.TestCase):
    def test_a_device_answer_becomes_rclone_token(self):
        tok = json.loads(cc._rclone_token({"access_token": "a", "refresh_token": "r", "expires_in": 60, "token_type": "Bearer"}))
        self.assertEqual(set(tok), {"access_token", "token_type", "refresh_token", "expiry"})
        self.assertTrue(tok["expiry"].endswith("Z"))

    def test_a_line_break_never_reaches_the_config(self):
        with self.assertRaises(ValueError):
            cc._section([("type", "dropbox"), ("token", "{}\n[evil]\ntype = local")])


class BrowserSignIn(Base):
    def test_link_then_pasted_address_then_signed_in(self):
        s = cc.start(self.data, "dropbox", "browser")
        self.assertEqual(s["way"], "browser")
        sess = cc._session
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "link"))
        now = cc.current()
        self.assertTrue(now["link"].startswith("https://www.dropbox.com/oauth2/authorize"))
        self.assertLessEqual(now["seconds_left"], cc.SIGNIN_LIMIT)
        cc.answer(s["id"], "http://localhost:53682/?code=dbx-code&state=Abc123_state-XYZ")
        with open(os.path.join(sess["work"], "answer")) as f:
            self.assertEqual(f.read(), "http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=dbx-code")
        self.assertEqual(cc.current()["state"], "checking")
        work = sess["work"]
        self.run.finish(sess, {"access_token": "at", "token_type": "Bearer", "refresh_token": "rt", "expiry": "2026-11-16T12:00:00Z"})
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "signed-in"))
        self.assertIn("type = dropbox\ntoken = {", sess["config"])
        self.assertNotIn("config", json.dumps(cc.current()))
        self.assertNotIn("at", [v for v in cc.current().values() if isinstance(v, str)])
        self.assertFalse(os.path.exists(work))           # the sign-in's files went
        self.assertEqual(self.run.removed, ["fake-" + s["id"]])  # and its helper

    def test_the_script_finds_either_address_rclone_says(self):
        import re as _re
        pattern = _re.search(r"grep -oE '([^']+)'", cc.authorize_script({"service": "dropbox"})).group(1).replace("[.]", "\\.").replace("[?]", "\\?")
        for said in ("http://localhost:53682/auth?state=Ab-c_1", "http://127.0.0.1:53682/auth?state=Ab-c_1"):
            self.assertTrue(_re.search(pattern, "NOTICE: go to the following link: " + said), said)

    def test_the_script_changes_folder_before_rclone_goes_to_the_background(self):
        script = cc.authorize_script({"service": "dropbox"})
        self.assertTrue(script.startswith("cd /c || exit 1; "))
        self.assertNotIn("&& (", script.split("rclone authorize")[0])

    def test_google_drive_asks_for_its_own_files_only(self):
        cc.start(self.data, "drive", "browser")
        self.assertIn('"scope": "drive.file"', unpadded(cc.authorize_script(cc._session).split("rclone authorize drive ")[1].split()[0]))

    def test_a_link_somewhere_else_is_never_shown(self):
        self.run.link = "https://evil.example/oauth2/authorize?state=Abc123_state-XYZ"
        cc.start(self.data, "dropbox", "browser")
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "failed"))
        self.assertNotIn("link", cc.current())

    def test_a_wrong_address_keeps_waiting_and_a_refusal_ends_it(self):
        s = cc.start(self.data, "dropbox", "browser")
        wait_for(lambda: cc.current()["state"] == "link")
        with self.assertRaises(ValueError):
            cc.answer(s["id"], "http://127.0.0.1:53682/?state=SomeoneElse1&code=x")
        self.assertEqual(cc.current()["state"], "link")
        with self.assertRaises(cc.CloudError):
            cc.answer(s["id"], "http://127.0.0.1:53682/?state=Abc123_state-XYZ&error=access_denied")
        self.assertEqual(cc.current()["state"], "failed")

    def test_closing_part_way_removes_the_helper_and_its_files(self):
        s = cc.start(self.data, "dropbox", "browser")
        work = cc._session["work"]
        wait_for(lambda: cc.current()["state"] == "link")
        cc.cancel()
        self.assertEqual(cc.current(), {"state": "none"})
        self.assertEqual(self.run.removed, ["fake-" + s["id"]])
        self.assertFalse(os.path.exists(work))
        with self.assertRaises(cc.CloudError):
            cc.answer(s["id"], "http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=x")

    def test_the_time_limit(self):
        with mock.patch.object(cc, "SIGNIN_LIMIT", 1):
            s = cc.start(self.data, "dropbox", "browser")
            time.sleep(1.2)
            self.assertEqual(cc.current()["state"], "expired")
            self.assertIn("Try again", cc.current()["error"])
            self.assertEqual(self.run.removed, ["fake-" + s["id"]])

    def test_a_new_sign_in_ends_the_last(self):
        a = cc.start(self.data, "dropbox", "browser")
        cc.start(self.data, "onedrive", "browser")
        self.assertIn("fake-" + a["id"], self.run.removed)

    def test_rclone_newer_form_of_the_token(self):
        # rclone 1.5x and later print a base64 blob of {"token": "<the token as JSON>"} between the markers.
        import base64
        tok = json.dumps({"access_token": "at", "token_type": "Bearer", "refresh_token": "rt", "expiry": "2026-11-16T12:00:00Z"})
        blob = base64.urlsafe_b64encode(json.dumps({"token": tok}).encode()).decode().rstrip("=")
        self.assertEqual(json.loads(cc.token_from_rclone(f"Paste the following into your remote machine --->\n{blob}\n<---End paste\n"))["access_token"], "at")
        self.assertEqual(json.loads(cc.token_from_rclone(f"--->\n{tok}\n<---End paste"))["refresh_token"], "rt")
        self.assertIsNone(cc.token_from_rclone("NOTICE: Waiting for code..."))

    def test_rclone_saying_no_token(self):
        cc.start(self.data, "dropbox", "browser")
        sess = cc._session
        wait_for(lambda: cc.current()["state"] == "link")
        cc.answer(sess["id"], "http://127.0.0.1:53682/?state=Abc123_state-XYZ&code=x")
        self.run.finish(sess, None)
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "failed"))
        self.assertIn("Start again", cc.current()["error"])


class PhoneSignIn(Base):
    def setUp(self):
        super().setUp()
        self.svc = StandIn().start()
        b = self.svc.base
        hook = {"device": {sid: {"code": b + "/device/code", "token": b + "/token", "pages": ("127.0.0.1",)} for sid in ("drive", "onedrive")},
                "graph": b + "/me/drive", "hosts": ("127.0.0.1",)}
        self.p += [mock.patch.object(cc, "TEST_HOOK", hook),
                   mock.patch.dict(os.environ, {"STARBOARD_GOOGLE_CLIENT_ID": "standin.apps.example", "STARBOARD_GOOGLE_CLIENT_SECRET": "x",
                                                "STARBOARD_MICROSOFT_CLIENT_ID": "standin-ms"})]
        for p in self.p[1:]:
            p.start()

    def tearDown(self):
        super().tearDown()
        self.svc.stop()

    def test_waits_by_itself_until_approved(self):
        s = cc.start(self.data, "drive", "phone")
        self.assertEqual(s["state"], "phone")
        self.assertRegex(s["user_code"], r"^\d{4}-\d{4}$")
        self.assertEqual(s["page"], self.svc.base + "/device")
        self.assertGreater(s["qr"]["size"], 20)
        self.assertTrue(s["qr"]["path"].startswith("M"))
        time.sleep(1.5)
        self.assertEqual(cc.current()["state"], "phone")  # nothing yet: authorization_pending
        self.svc.approve(s["user_code"])
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "signed-in", 10))
        conf = cc._session["config"]
        self.assertIn("client_id = standin.apps.example", conf)  # refreshing needs Starboard's own sign-in
        self.assertIn("scope = drive.file", conf)
        polls = [r for r in self.svc.requests if r[1] == "/token"]
        self.assertTrue(all(r[2]["client_secret"] == "x" for r in polls))

    def test_onedrive_finds_its_drive(self):
        s = cc.start(self.data, "onedrive", "phone")
        self.svc.approve(s["user_code"])
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "signed-in", 10))
        self.assertIn("drive_id = b!standin-drive\ndrive_type = personal", cc._session["config"])
        self.assertEqual(cc.current()["account"], "Alex")

    def test_a_refusal_on_the_phone(self):
        self.svc.mode = "deny"
        cc.start(self.data, "drive", "phone")
        for d in self.svc.devices.values():
            d["denied"] = True
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "failed", 10))
        self.assertIn("did not allow", cc.current()["error"])

    def test_the_code_running_out_at_the_service(self):
        self.svc.mode = "expire"
        cc.start(self.data, "drive", "phone")
        self.assertTrue(wait_for(lambda: cc.current()["state"] == "expired", 10))
        self.assertIn("Try again", cc.current()["error"])

    def test_starboard_own_time_limit(self):
        with mock.patch.object(cc, "PHONE_LIMIT", 2):
            s = cc.start(self.data, "onedrive", "phone")
            self.assertLessEqual(s["seconds_left"], 2)
            self.assertTrue(wait_for(lambda: cc.current()["state"] == "expired", 8))

    def test_closing_stops_the_waiting(self):
        s = cc.start(self.data, "drive", "phone")
        cc.cancel()
        self.svc.approve(s["user_code"])
        time.sleep(2.5)
        self.assertEqual(cc.current(), {"state": "none"})

    def test_slow_down_waits_longer(self):
        calls = []

        def http(url, form=None, headers=None):
            calls.append(url)
            if url.endswith("/device/code"):
                return 200, {"device_code": "d", "user_code": "ABCD-EFGH", "verification_uri": self.svc.base + "/device", "interval": 2, "expires_in": 60}
            return 400, {"error": "slow_down"}
        with mock.patch.object(cc, "HTTP", http):
            cc.start(self.data, "drive", "phone")
            time.sleep(2.3)
            self.assertEqual(cc._session["interval"], 7)

    def test_a_page_somewhere_else_is_never_shown(self):
        def http(url, form=None, headers=None):
            return 200, {"device_code": "d", "user_code": "ABCD-EFGH", "verification_uri": "https://evil.example/device"}
        with mock.patch.object(cc, "HTTP", http), self.assertRaises(cc.CloudError):
            cc.start(self.data, "drive", "phone")
        self.assertEqual(cc.current(), {"state": "none"})

    def test_phone_is_refused_for_dropbox(self):
        with self.assertRaises(cc.CloudError):
            cc.start(self.data, "dropbox", "phone")


class KeysTestAndSave(Base):
    def test_keys_folder_test_save(self):
        s = cc.start(self.data, "webdav", "browser")
        self.assertEqual(s["state"], "details")
        cc.details(s["id"], {"url": "https://cloud.example/", "vendor": "nextcloud", "user": "alex", "pass": "secret pass"})
        script = self.run.scripts[-1]
        self.assertIn("--obscure", script)
        self.assertNotIn("secret pass", script)  # read from a file in the helper, never on its command line
        self.assertEqual(cc.current()["state"], "signed-in")
        with self.assertRaises(cc.CloudError):
            cc.save(self.data, s["id"], 5)  # not tested yet
        self.run.short_answer = (0, "STEP-FOLDER\nSTEP-WRITE\nSTEP-READ\nSTEP-REMOVE\nFREE 1000000000\n")
        t = cc.test(s["id"], "starboard-backups")["test"]
        self.assertTrue(t["ok"])
        self.assertEqual([x["done"] for x in t["steps"]], [True] * 4)
        with self.assertRaises(ValueError):
            cc.save(self.data, s["id"], 0)
        new = cc.save(self.data, s["id"], 6)
        self.assertEqual((new["kind"], new["remote"], new["service"], new["keep"]), ("rclone", "starboard-cloud:starboard-backups", "webdav", 6))
        self.assertIn("[starboard-cloud]", backup_copies.secrets(self.data)["rclone_config"])
        pub = json.dumps(backup_copies.public(self.data))
        self.assertNotIn("OBSCURED", pub)
        self.assertTrue(backup_copies.public(self.data)["tested"]["ok"])
        self.assertEqual(cc.current(), {"state": "none"})
        self.assertEqual(oct(os.stat(os.path.join(self.data, backup_copies.SECRET)).st_mode & 0o777), "0o600")

    def test_a_test_that_stops_part_way(self):
        s = cc.start(self.data, "sftp", "browser")
        cc.details(s["id"], {"host": "nas.home", "user": "alex", "pass": "p"})
        self.run.short_answer = (1, "STEP-FOLDER\nERROR : couldn't connect SSH: ssh: handshake failed: ssh: unable to authenticate\n")
        t = cc.test(s["id"], "backups")["test"]
        self.assertFalse(t["ok"])
        self.assertEqual([x["done"] for x in t["steps"]], [True, False, False, False])
        self.assertIn("SFTP server did not accept", t["error"])

    def test_no_room_for_the_newest_backup(self):
        s = cc.start(self.data, "b2", "browser")
        cc.details(s["id"], {"account": "a", "key": "k"})
        self.run.short_answer = (0, "STEP-FOLDER\nSTEP-WRITE\nSTEP-READ\nSTEP-REMOVE\nFREE 1048576\n")
        with mock.patch.object(backup_copies, "newest_size", return_value=50 * 1024 ** 2):
            t = cc.test(s["id"], "bucket/starboard")["test"]
        self.assertFalse(t["ok"])
        self.assertIn("room for 1 MB", t["error"])

    def test_signin_problems_say_sign_in_again(self):
        self.assertTrue(cc.plain("Failed to create file system: couldn't fetch token: invalid_grant", signin="oauth").startswith("SIGNIN|"))
        self.assertFalse(cc.plain("401 Unauthorized", signin="keys").startswith("SIGNIN|"))


class TestConnection(unittest.TestCase):
    """Test connection on Copies off this computer: the result is kept for the place set up now."""

    def test_kept_and_shown_again(self):
        d = tempfile.mkdtemp()
        backup_copies.save(d, {**backup_copies.settings(d), "kind": "disk", "folder": "/mnt/usb/starboard"}, backup_copies.secrets(d))
        ok = "STEP-FOLDER\nSTEP-WRITE\nSTEP-READ\nSTEP-REMOVE\nFREE 999999999999\nCOUNT 3\n"
        with mock.patch("starboard.containers.available", return_value=True), mock.patch.object(backup_copies, "_run", return_value=(0, ok)), \
                mock.patch.object(backup_copies, "newest_size", return_value=10):
            got = backup_copies.test(d)
        self.assertTrue(got["ok"])
        self.assertEqual(got["count"], 3)
        self.assertEqual(backup_copies.public(d)["tested"]["where"], "/mnt/usb/starboard")
        backup_copies._say(d, state="done", said="Copied to /mnt/usb/starboard")
        # Another place: the old result is not shown for it, and the last copy line starts again.
        backup_copies.save(d, {**backup_copies.settings(d), "folder": "/mnt/usb2/starboard"}, backup_copies.secrets(d))
        self.assertIsNone(backup_copies.public(d)["tested"])
        self.assertEqual(backup_copies.status(d), {"state": "none"})

    def test_an_expired_cloud_sign_in(self):
        d = tempfile.mkdtemp()
        backup_copies.save(d, {**backup_copies.settings(d), "kind": "rclone", "remote": "starboard-cloud:b", "service": "drive"},
                           {"smb_password": "", "rclone_config": "[starboard-cloud]\ntype = drive\n"})
        said = "ERROR : Failed to create file system: couldn't fetch token: invalid_grant: maybe token expired? - try refreshing with \"rclone config reconnect\""
        with mock.patch("starboard.containers.available", return_value=True), mock.patch.object(backup_copies, "_run", return_value=(1, said)):
            got = backup_copies.test(d)
        self.assertFalse(got["ok"])
        self.assertTrue(got["error"].startswith("SIGNIN|"))

    def test_a_place_that_does_not_answer(self):
        d = tempfile.mkdtemp()
        backup_copies.save(d, {**backup_copies.settings(d), "kind": "smb", "smb": "//192.0.2.1/x"}, backup_copies.secrets(d))
        with mock.patch("starboard.containers.available", return_value=True), \
                mock.patch.object(backup_copies, "_run", side_effect=backup_copies.CopyError("The share //192.0.2.1/x did not answer")):
            got = backup_copies.test(d)
        self.assertFalse(got["ok"])
        self.assertIn("did not answer", got["error"])

    def test_the_test_file_is_never_in_a_backup(self):
        from starboard import full_backup
        self.assertIn(backup_copies.TESTED, full_backup.COPY_SKIP)


if __name__ == "__main__":
    unittest.main()
