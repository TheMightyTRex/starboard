"""DASH-547 and DASH-548: a LinuxServer.io build tag is offered the newest build of its own branch (never another
branch), the last look at the apps survives a restart, and a rate-limited registry gets one more try and then a plain
answer. Registry answers are recorded, nothing is asked of the internet and no container is touched."""
import io
import json
import os
import subprocess
import tempfile
import time
import unittest
import urllib.error
from unittest import mock

from starboard import containers, stack

QB = "lscr.io/linuxserver/qbittorrent"
V1 = "libtorrentv1-5.3.0_v1.2.20-ls138"


def label(version):
    return {"config": {"Labels": {"build_version": f"Linuxserver.io version:- {version} Build-date:- 2026-11-20T10:00:00+00:00"}}}


class Registry:
    """What lscr.io answered on 23 November 2026, in the shapes that matter: an index per tag, an amd64 manifest, its
    config. `tags` are the branch tags and their newest build; anything else asked for is a 404."""

    def __init__(self, tags, listed=None):
        self.tags = tags  # tag -> version label of that tag's image
        self.listed = listed
        self.asked = []

    def __call__(self, reg, repo, path, accept=None):
        self.asked.append(path)
        if path.startswith("tags/list"):
            return {}, json.dumps({"tags": self.listed or []}).encode()
        kind, _, name = path.partition("/")
        if kind == "manifests" and name in self.tags:
            return {"Docker-Content-Digest": "sha256:" + name}, json.dumps(
                {"manifests": [{"digest": "sha256:amd-" + name, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                                "platform": {"architecture": "amd64", "os": "linux"}}]}).encode()
        if kind == "manifests" and name.startswith("sha256:amd-") and name[11:] in self.tags:
            return {}, json.dumps({"config": {"digest": "sha256:cfg-" + name[11:]}}).encode()
        if kind == "manifests" and name in self.builds():
            return {"Docker-Content-Digest": "sha256:" + name}, json.dumps({"config": {}}).encode()
        if kind == "blobs" and name.startswith("sha256:cfg-"):
            return {}, json.dumps(label(self.tags[name[11:]])).encode()
        raise urllib.error.HTTPError(path, 404, "Not Found", {}, io.BytesIO())

    def builds(self):
        """The build tags that exist: each branch's newest, as <branch>-<version>."""
        return {(f"{t}-{v}" if t != "latest" else v) for t, v in self.tags.items()}


LSIO = {"libtorrentv1": "5.3.0_v1.2.20-ls144", "latest": "5.3.0_v2.1.2-ls488"}


class LinuxServerBranch(unittest.TestCase):
    def offered(self, tag, tags=LSIO, listed=None):
        reg = Registry(tags, listed)
        with mock.patch.object(containers, "_registry", reg):
            return containers.newer_pinned(f"{QB}:{tag}"), reg

    def test_the_owners_tag_is_offered_the_newest_build_of_its_branch(self):
        target, reg = self.offered(V1)
        self.assertEqual(target, "libtorrentv1-5.3.0_v1.2.20-ls144")
        self.assertFalse([p for p in reg.asked if "latest" in p or "ls488" in p], "the v2 build was never asked about")

    def test_the_tag_list_is_not_needed_so_one_that_stops_short_is_harmless(self):
        junk = [f"version-{i}" for i in range(1000)]  # what n=1000 returned: none of the libtorrentv1 tags
        target, reg = self.offered(V1, listed=junk)
        self.assertEqual(target, "libtorrentv1-5.3.0_v1.2.20-ls144")
        self.assertFalse([p for p in reg.asked if p.startswith("tags/list")])

    def test_libtorrent_v2_is_never_offered_to_a_libtorrent_v1_install(self):
        self.assertNotIn("v2", self.offered(V1)[0])
        # the branch's own tag is gone or older: nothing is offered, and the newest tag is not a way round it
        self.assertIsNone(self.offered(V1, tags={"latest": "5.3.0_v2.1.2-ls488"})[0])
        self.assertIsNone(self.offered(V1, tags={"libtorrentv1": "5.3.0_v1.2.20-ls100", "latest": "5.3.0_v2.1.2-ls488"})[0])

    def test_already_on_the_newest_build_is_up_to_date(self):
        self.assertIsNone(self.offered("libtorrentv1-5.3.0_v1.2.20-ls144")[0])

    def test_a_newer_version_on_the_same_branch_beats_a_higher_build_number(self):
        tags = {"libtorrentv1": "5.3.1_v1.2.21-ls3"}
        self.assertEqual(self.offered("libtorrentv1-5.3.0_v1.2.20-ls900", tags)[0], "libtorrentv1-5.3.1_v1.2.21-ls3")

    def test_a_build_that_is_not_in_the_registry_is_not_offered(self):
        reg = Registry(LSIO)
        reg.builds = lambda: set()  # the branch tag says ls144 but that build tag is gone
        with mock.patch.object(containers, "_registry", reg):
            self.assertIsNone(containers.newer_pinned(f"{QB}:{V1}"))

    def test_an_image_without_branches_follows_latest(self):
        tags = {"latest": "v1.6.2-ls380"}
        with mock.patch.object(containers, "_registry", Registry(tags)):
            self.assertEqual(containers.newer_pinned("lscr.io/linuxserver/bazarr:v1.6.2-ls373"), "v1.6.2-ls380")
            self.assertIsNone(containers.newer_pinned("lscr.io/linuxserver/bazarr:v1.6.2-ls380"))

    def test_a_floating_tag_is_left_to_its_digest(self):
        for tag in ("libtorrentv1", "latest"):
            self.assertIsNone(self.offered(tag)[0])

    def test_a_plain_version_tag_still_works(self):
        tags = ["latest", "v0.4.8", "v0.5.8", "v0.6.0-dev.1"]
        reg = lambda *a, **k: ({}, json.dumps({"tags": tags}).encode())
        with mock.patch.object(containers, "_registry", reg):
            self.assertEqual(containers.newer_pinned("ghcr.io/example/app:v0.4.8"), "v0.5.8")
            self.assertIsNone(containers.newer_pinned("ghcr.io/example/app:v0.5.8"))

    def test_the_page_names_the_build_and_pulls_the_whole_tag(self):
        c = {"image": f"{QB}:{V1}", "version": "5.3.0_v1.2.20-ls138", "digests": [f"{QB}@sha256:" + V1]}
        reg = Registry(LSIO)
        # the installed tag is in the registry too (as it is for lscr.io), and its digest is the installed one
        reg.tags[V1] = "5.3.0_v1.2.20-ls138"
        with mock.patch.object(containers, "_registry", reg):
            out = containers._check_one(c)
        self.assertEqual((out["latest"], out["target_tag"], out["update"], out["pinned"], out["big_change"]),
                         ("5.3.0_v1.2.20-ls144", "libtorrentv1-5.3.0_v1.2.20-ls144", True, True, False))

    def test_shown_drops_only_a_branch(self):
        self.assertEqual(containers.shown("libtorrentv1-5.3.0_v1.2.20-ls144"), "5.3.0_v1.2.20-ls144")
        self.assertEqual(containers.shown("v26.3-ls273"), "v26.3-ls273")
        self.assertEqual(containers.shown("latest"), "latest")


class ComposeEdit(unittest.TestCase):
    """The file edit of an update, run with the shell on a throwaway project in a temp folder (never a container)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = os.path.join(self.tmp.name, "compose.yaml")
        self.old = f"{QB}:{V1}"
        self.new = f"{QB}:libtorrentv1-5.3.0_v1.2.20-ls144"
        with open(self.file, "w") as f:
            f.write(f"services:\n  qbittorrent:\n    image: {self.old}\n    ports: ['8080:8080']\n"
                    f"  other:\n    image: {self.old}0  # a different build\n")

    def run_steps(self, steps):
        subprocess.run(["sh", "-c", " && ".join(["set -e", *steps])], check=True)

    def text(self):
        with open(self.file) as f:
            return f.read()

    def test_the_tag_changes_with_a_copy_kept_and_going_back_restores_it(self):
        self.run_steps(containers.swap_image_steps([self.file], self.old, self.new, "qbittorrent", "libtorrentv1-5.3.0_v1.2.20-ls144", "T"))
        self.assertIn(f"image: {self.new}\n", self.text())
        self.assertIn(f"image: {self.old}0  # a different build", self.text())  # ls1380 style neighbours are not touched
        copies = [n for n in os.listdir(self.tmp.name) if ".bak-qbittorrent-" in n]
        self.assertEqual(len(copies), 1)
        with open(os.path.join(self.tmp.name, copies[0])) as f:
            self.assertIn(f"image: {self.old}\n", f.read())
        self.run_steps(containers.swap_image_steps([self.file], self.new, self.old))
        self.assertIn(f"image: {self.old}\n", self.text())
        self.assertNotIn("ls144", self.text())

    def test_a_trailing_comment_is_kept(self):
        with open(self.file, "w") as f:
            f.write(f"    image: {self.old} # the v1 build\n")
        self.run_steps(containers.swap_image_steps([self.file], self.old, self.new))
        self.assertEqual(self.text(), f"    image: {self.new} # the v1 build\n")

    def test_going_back_runs_the_helper_with_the_old_tag(self):
        before = {"image": self.old, "service": "qbittorrent", "name": "qbittorrent", "project": "stack",
                  "folder": self.tmp.name, "files": [self.file]}
        with mock.patch.object(containers, "_helper", return_value=(0, "")) as helper:
            containers.go_back_pinned(before, self.new)
        script = helper.call_args[0][1]
        self.assertIn("up -d qbittorrent", script)
        self.assertIn("ls144", script)
        self.assertNotIn(".bak-", script)

    def test_kept_json_names_the_new_tag(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "stack"))
            path = os.path.join(d, "stack", "kept.json")
            with open(path, "w") as f:
                json.dump({"qbittorrent": {"image": self.old, "ports": ["8080:8080"]}, "radarr": {"image": "x:1"}}, f)
            self.assertEqual(stack.keep_image(d, self.old, self.new), ["qbittorrent"])
            with open(path) as f:
                saved = json.load(f)
            self.assertEqual((saved["qbittorrent"]["image"], saved["qbittorrent"]["ports"], saved["radarr"]["image"]),
                             (self.new, ["8080:8080"], "x:1"))
            self.assertEqual(stack.keep_image(d, self.old, self.new), [])  # nothing left to change
            self.assertEqual(stack.keep_image(tempfile.gettempdir() + "/none-here", self.old, self.new), [])  # no file


class Remembered(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, containers.CHECK_FILE)
        self.before = dict(containers._state)
        self.addCleanup(lambda: (containers._state.clear(), containers._state.update(self.before), setattr(containers, "data_dir", None)))
        containers._state.update(check={}, checked_at=None, restored=False, loaded=False)
        containers.use_data_dir(self.tmp.name)

    def write(self, body):
        with open(self.path, "w") as f:
            f.write(body if isinstance(body, str) else json.dumps(body))

    def saved(self, **over):
        return {"version": 1, "checked_at": time.time() - 3600, "check": {"jellyfin": {"update": False, "latest": "12.4"}}, **over}

    def test_a_missing_file_is_not_checked_yet(self):
        self.assertIsNone(containers.last_check())
        with mock.patch.object(containers, "containers", return_value=[]):
            out = containers.apps([])
        self.assertEqual((out["checked_at"], out["restored"]), (None, False))

    def test_a_kept_look_comes_back_marked_as_from_before_the_restart(self):
        self.write(self.saved())
        with mock.patch.object(containers, "containers", return_value=[]):
            out = containers.apps([])
        self.assertTrue(out["restored"])
        self.assertAlmostEqual(out["checked_at"], time.time() - 3600, delta=5)
        self.assertEqual(containers.last_check()["restored"], True)
        self.assertEqual(containers._state["check"]["jellyfin"]["latest"], "12.4")

    def test_a_look_from_days_ago_is_kept_with_its_own_time(self):
        long_ago = time.time() - 9 * 86400
        self.write(self.saved(checked_at=long_ago))
        self.assertEqual(containers.last_check()["at"], long_ago)

    def test_a_file_that_is_broken_or_from_another_layout_is_ignored(self):
        for body in ("{not json", "[]", "", json.dumps({"checked_at": 5}), self.saved(version=2), self.saved(check=[1]),
                     self.saved(checked_at="yesterday"), self.saved(checked_at=time.time() + 86400), self.saved(checked_at=True),
                     {"checked_at": time.time(), "check": {}}):  # the last has no version: an older layout
            containers._state.update(check={}, checked_at=None, restored=False, loaded=False)
            self.write(body)
            self.assertIsNone(containers.last_check(), body)
            self.assertEqual(containers._state["check"], {})

    def test_what_is_looked_at_after_the_start_is_not_replaced_by_the_file(self):
        self.write(self.saved())
        containers._state.update(checked_at=123.0, check={"x": {}})
        self.assertEqual(containers.last_check(), {"at": 123.0, "restored": False})

    def test_a_check_writes_the_file_whole_and_a_later_start_reads_it(self):
        svc = [{"id": "jf", "name": "Jellyfin", "enabled": True}]
        c = {"name": "jellyfin", "image": "x/jf:latest", "version": "1", "digests": [], "folder": "", "files": [], "state": "running",
             "status": "Up", "created": "", "service": "jf", "project": "p"}
        with mock.patch.object(containers, "containers", return_value=[c]), mock.patch.object(containers, "match", return_value=c), \
                mock.patch.object(containers, "_check_one", return_value={"latest": "2", "update": True, "unknown": False}):
            out = containers.check(svc)
        self.assertFalse(out["restored"])
        self.assertEqual(os.listdir(self.tmp.name), [containers.CHECK_FILE])  # no half-written file left beside it
        self.assertEqual(oct(os.stat(self.path).st_mode & 0o777), "0o600")
        containers._state.update(check={}, checked_at=None, restored=False, loaded=False)  # a restart
        self.assertEqual(containers.last_check()["restored"], True)
        self.assertEqual(containers._state["check"]["jellyfin"]["latest"], "2")

    def test_a_folder_that_cannot_be_written_does_not_stop_the_check(self):
        containers.use_data_dir(os.path.join(self.tmp.name, "not", "there"))
        containers._state.update(checked_at=1.0, check={})
        containers._save()  # no error


def too_many(wait=None):
    headers = {"Retry-After": wait} if wait is not None else {}
    return urllib.error.HTTPError("https://lscr.io/v2/x", 429, "Too Many Requests", headers, io.BytesIO())


class Ok:
    headers = {"Docker-Content-Digest": "sha256:a"}

    def read(self, n=-1):
        return b"{}"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class RateLimited(unittest.TestCase):
    def ask(self, answers):
        sleeps = []
        with mock.patch("urllib.request.urlopen", side_effect=answers), mock.patch.object(containers, "_sleep", sleeps.append):
            try:
                return containers._registry("lscr.io", "linuxserver/nzbget", "manifests/latest"), sleeps
            except containers.RegistryBusy as e:
                return e, sleeps

    def test_one_more_try_after_the_pause_the_registry_asked_for(self):
        (headers, body), sleeps = self.ask([too_many("3"), Ok()])
        self.assertEqual((body, sleeps), (b"{}", [3.0]))

    def test_a_long_pause_is_cut_to_ten_seconds_and_a_missing_one_is_two(self):
        self.assertEqual(self.ask([too_many("120"), Ok()])[1], [10.0])
        self.assertEqual(self.ask([too_many(), Ok()])[1], [2.0])
        self.assertEqual(self.ask([too_many("soon"), Ok()])[1], [2.0])

    def test_twice_is_the_registry_is_busy_with_no_third_try(self):
        out, sleeps = self.ask([too_many("1"), too_many("1"), Ok()])
        self.assertIsInstance(out, containers.RegistryBusy)
        self.assertEqual((str(out), len(sleeps)), ("The registry is busy, try again", 1))

    def test_the_app_says_so_instead_of_being_left_unchecked(self):
        c = {"image": "lscr.io/linuxserver/nzbget:v26.3-ls273", "version": "", "digests": []}
        with mock.patch("urllib.request.urlopen", side_effect=[too_many("0")] * 2), mock.patch.object(containers, "_sleep", lambda s: None):
            out = containers._check_one(c)
        self.assertEqual((out["error"], out["unknown"], out["update"]), ("The registry is busy, try again", True, False))

    def test_a_busy_token_service_is_retried_too(self):
        challenge = urllib.error.HTTPError("u", 401, "x", {"WWW-Authenticate": 'Bearer realm="https://lscr.io/token",service="s"'}, io.BytesIO())
        token = mock.MagicMock()
        token.__enter__.return_value = io.BytesIO(b'{"token": "t"}')
        sleeps = []
        with mock.patch("urllib.request.urlopen", side_effect=[challenge, too_many("1"), challenge, token, Ok()]), mock.patch.object(containers, "_sleep", sleeps.append):
            containers._tokens.clear()
            _, body = containers._registry("lscr.io", "linuxserver/nzbget", "manifests/latest")
        self.assertEqual((body, sleeps), (b"{}", [1.0]))


if __name__ == "__main__":
    unittest.main()


class PinnedUpdateRun(unittest.TestCase):
    """update_runs on an app pinned to a LinuxServer.io tag: the new tag goes in kept.json when it is healthy, and the
    old tag goes back in the Compose file when it is not. Docker is replaced; the work runs at once, not in a thread."""

    OLD = f"{QB}:{V1}"
    NEW = "libtorrentv1-5.3.0_v1.2.20-ls144"

    def run_it(self, healthy):
        from starboard import update_runs
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "stack"))
            with open(os.path.join(d, "stack", "kept.json"), "w") as f:
                json.dump({"qbittorrent": {"image": self.OLD}}, f)
            app = mock.Mock(data_dir=d)
            app.config.data = {"services": [{"id": "qb", "name": "qBittorrent"}]}
            row = {"id": "qb", "name": "qBittorrent", "update": True, "latest": "5.3.0_v1.2.20-ls144", "target_tag": self.NEW, "pinned": True,
                   "container": {"name": "qbittorrent", "compose": True, "version": "5.3.0_v1.2.20-ls138"}}
            before = {"name": "qbittorrent", "image": self.OLD, "image_id": "sha256:old", "service": "qbittorrent", "project": "stack",
                      "folder": d, "files": [d + "/compose.yaml"]}
            with mock.patch.object(containers, "available", return_value=True), \
                    mock.patch.object(containers, "apps", return_value={"items": [row]}), \
                    mock.patch.object(containers, "containers", return_value=[before]), \
                    mock.patch.object(containers, "update"), mock.patch.object(containers, "forget_old"), \
                    mock.patch.object(containers, "job", return_value={"finished": True, "items": {"qbittorrent": {"phase": "done", "version": "x"}}}), \
                    mock.patch.object(containers, "go_back_pinned") as back, mock.patch.object(containers, "go_back") as plain, \
                    mock.patch.object(update_runs, "save_app_settings", return_value=("done", "")), \
                    mock.patch.object(update_runs, "_app_healthy", return_value=(healthy, "did not answer")), \
                    mock.patch.object(update_runs, "_go", lambda data_dir, run, work: work()), \
                    mock.patch.object(update_runs.api_v1, "audit"), mock.patch.object(update_runs.logs, "event"):
                run = update_runs._start_app(app, "app:qb", "you")
            with open(os.path.join(d, "stack", "kept.json")) as f:
                kept = json.load(f)["qbittorrent"]["image"]
        return run, kept, back, plain

    def test_healthy_writes_the_new_tag_to_kept_json(self):
        run, kept, back, plain = self.run_it(True)
        self.assertEqual((run["state"], kept), ("updated", f"{QB}:{self.NEW}"))
        back.assert_not_called()

    def test_unhealthy_goes_back_to_the_old_tag(self):
        run, kept, back, plain = self.run_it(False)
        self.assertEqual((run["state"], kept), ("went-back", self.OLD))
        back.assert_called_once()
        self.assertEqual(back.call_args[0][1], f"{QB}:{self.NEW}")
        plain.assert_not_called()
