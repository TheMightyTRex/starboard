"""Plug-in API 1.15 and batch 0.19's plug-in group: plug-ins from a zip file with a container built from its
Dockerfile (DASH-414, with its security tests: zip handling, build limits, what the Dockerfile may do), the Apps
entry of an app plug-in going with it (DASH-427), Jellyfin libraries a plug-in fills (DASH-430), and Jellyfin's
metadata outside its settings folder (DASH-431)."""
import copy
import io
import json
import os
import stat
import tempfile
import unittest
import zipfile
from unittest import mock

from starboard import app_setup, jellyfin_metadata, plugin_libraries, plugin_zip, plugins, stack
from starboard import plugins_admin as pa
from tests.test_plugins import ON_DEMAND

DOCKERFILE = ("# The On demand helper\nFROM python:3.12-alpine\nRUN apk upgrade --no-cache && \\\n    apk add --no-cache ffmpeg\n"
              "WORKDIR /app\nCOPY ondemand /app/ondemand\nENV PYTHONUNBUFFERED=1\nUSER 1000:1000\nCMD [\"python3\", \"-m\", \"ondemand\"]\n")


def built(version="0.9.2"):
    m = copy.deepcopy(ON_DEMAND)
    m["version"] = version
    m["containers"][0] = {**m["containers"][0], "image": f"local/on-demand:{version}", "build": True}
    return m


def make_zip(path, files, links=(), modes=None):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = ((modes or {}).get(name, 0o100644)) << 16
            z.writestr(info, data)
        for name, target in links:
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, target)
    return path


class ZipHandling(unittest.TestCase):
    """Security tests: what a zip may hold, and what is refused before anything is shown."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def zip(self, files, **kw):
        return make_zip(os.path.join(self.tmp, f"z{len(os.listdir(self.tmp))}.zip"), files, **kw)

    def good(self):
        return {"starboard-plugin.json": json.dumps(built()), "Dockerfile": DOCKERFILE, "ondemand/__main__.py": "print(1)\n"}

    def test_a_good_zip_is_read_with_its_base_image(self):
        m, report = plugin_zip.read(self.zip(self.good()))
        self.assertEqual(m["id"], "on-demand")
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["dockerfile"]["from"], ["python:3.12-alpine"])
        self.assertEqual(report["files"], 3)
        self.assertEqual(plugins.check(m), [])

    def test_names_outside_the_zip_are_refused(self):
        for bad in ("../evil.sh", "a/../../evil", "/etc/passwd", "C:/x", "a\\b", "a//b", "./a"):
            files = {**self.good(), bad: "x"}
            with self.assertRaises(plugin_zip.ZipProblem, msg=bad):
                plugin_zip.read(self.zip(files))

    def test_links_and_special_files_are_refused(self):
        with self.assertRaisesRegex(plugin_zip.ZipProblem, "link"):
            plugin_zip.read(self.zip(self.good(), links=[("ondemand/passwd", "/etc/passwd")]))
        with self.assertRaisesRegex(plugin_zip.ZipProblem, "link or a special file"):
            plugin_zip.read(self.zip({**self.good(), "fifo": ""}, modes={"fifo": stat.S_IFIFO | 0o644}))

    def test_the_manifest_must_be_at_the_top(self):
        files = {"on-demand/starboard-plugin.json": json.dumps(built()), "on-demand/Dockerfile": DOCKERFILE}
        with self.assertRaisesRegex(plugin_zip.ZipProblem, "at the top of the zip, not in a folder"):
            plugin_zip.read(self.zip(files))

    def test_twice_the_same_name_is_refused(self):
        p = os.path.join(self.tmp, "dup.zip")
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("starboard-plugin.json", json.dumps(built()))
            z.writestr("Dockerfile", DOCKERFILE)
            z.writestr("DOCKERFILE", "FROM scratch\n")
        with self.assertRaisesRegex(plugin_zip.ZipProblem, "twice"):
            plugin_zip.read(p)

    def test_a_zip_bomb_stops_at_the_limit(self):
        p = os.path.join(self.tmp, "bomb.zip")
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("starboard-plugin.json", json.dumps(built()))
            z.writestr("Dockerfile", DOCKERFILE)
            z.writestr("zeros", b"\0" * (8 * 1024 * 1024))
        self.assertLess(os.path.getsize(p), 100 * 1024)
        with mock.patch.object(plugin_zip, "MAX_UNPACKED", 4 * 1024 * 1024):
            with self.assertRaisesRegex(plugin_zip.ZipProblem, "unpacks to more than"):
                plugin_zip.read(p)

    def test_too_big_too_many_encrypted_or_not_a_zip(self):
        with mock.patch.object(plugin_zip, "MAX_ZIP", 100):
            with self.assertRaisesRegex(plugin_zip.ZipProblem, "up to 50 MB"):
                plugin_zip.read(self.zip(self.good()))
        with mock.patch.object(plugin_zip, "MAX_FILES", 2):
            with self.assertRaisesRegex(plugin_zip.ZipProblem, "more than"):
                plugin_zip.read(self.zip(self.good()))
        p = os.path.join(self.tmp, "plain.txt")
        with open(p, "w") as f:
            f.write("hello")
        with self.assertRaisesRegex(plugin_zip.ZipProblem, "not a zip"):
            plugin_zip.read(p)
        enc = self.zip(self.good())
        with open(enc, "r+b") as f:  # the encrypted flag on the first entry's local and central headers
            data = bytearray(f.read())
            for sig in (b"PK\x03\x04", b"PK\x01\x02"):
                i = data.find(sig)
                off = i + (6 if sig == b"PK\x03\x04" else 8)
                data[off] |= 1
            f.seek(0)
            f.write(data)
        with self.assertRaises(plugin_zip.ZipProblem):
            plugin_zip.read(enc)

    def test_a_built_container_needs_a_dockerfile_and_its_own_tag(self):
        files = self.good()
        del files["Dockerfile"]
        _, report = plugin_zip.read(self.zip(files))
        self.assertIn("needs a Dockerfile", report["problems"][0])
        m = built()
        m["containers"][0]["image"] = "local/jellyfin:latest"  # never another plug-in's or app's image
        self.assertTrue(any("local/on-demand:0.9.2" in p for p in plugins.check(m)))
        m["containers"][0]["build"] = "yes"
        self.assertTrue(any("build is true" in p for p in plugins.check(m)))

    def test_upload_is_streamed_kept_private_and_tidied(self):
        data_dir = tempfile.mkdtemp()
        with open(self.zip(self.good()), "rb") as f:
            raw = f.read()
        token, m, _ = plugin_zip.receive(data_dir, len(raw), io.BytesIO(raw))
        path = plugin_zip.path_of(data_dir, token)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(m["version"], "0.9.2")
        for bad in ("../x", "a" * 32, ""):
            with self.assertRaises(LookupError):
                plugin_zip.path_of(data_dir, bad)
        with self.assertRaises(plugin_zip.ZipProblem):  # shorter than it said: nothing kept
            plugin_zip.receive(data_dir, len(raw) + 10, io.BytesIO(raw))
        with self.assertRaises(plugin_zip.ZipProblem):  # a bad zip is not kept either
            plugin_zip.receive(data_dir, 5, io.BytesIO(b"hello"))
        self.assertEqual(len(os.listdir(plugin_zip.uploads(data_dir))), 1)
        plugin_zip._tidy(data_dir, now=os.path.getmtime(path) + 7200)
        self.assertEqual(os.listdir(plugin_zip.uploads(data_dir)), [])

    def test_the_build_context_holds_only_the_files(self):
        p = self.zip({**self.good(), "run.sh": "#!/bin/sh\n"}, modes={"run.sh": 0o100755})
        buf = io.BytesIO()
        plugin_zip._context(p, buf)
        buf.seek(0)
        import tarfile
        with tarfile.open(fileobj=buf) as tar:
            members = {t.name: t for t in tar.getmembers()}
        self.assertEqual(set(members), {"starboard-plugin.json", "Dockerfile", "ondemand/__main__.py", "run.sh"})
        self.assertTrue(all(t.isfile() and t.uid == 0 and t.gid == 0 for t in members.values()))
        self.assertEqual(members["run.sh"].mode, 0o755)
        self.assertEqual(members["Dockerfile"].mode, 0o644)


class DockerfileRules(unittest.TestCase):
    """Security tests: what the Dockerfile in a zip may do."""

    def problems(self, text):
        return plugin_zip.check_dockerfile(text)[0]

    def test_on_demands_dockerfile_is_fine(self):
        self.assertEqual(plugin_zip.check_dockerfile(DOCKERFILE), ([], ["python:3.12-alpine"]))

    def test_what_is_refused(self):
        cases = {
            "# syntax=docker/dockerfile:1\nFROM alpine\n": "directive",
            "# escape=`\nFROM alpine\n": "directive",
            "FROM alpine\nRUN --mount=type=bind,source=/,target=/host cat /host/etc/shadow\n": "RUN --mount",
            "FROM alpine\nRUN --network=host wget x\n": "RUN --network",
            "FROM alpine\nRUN --security=insecure x\n": "RUN --security",
            "FROM alpine\nADD https://example.invalid/x.tar /x\n": "internet or git",
            "FROM alpine\nADD git@github.com:a/b.git /b\n": "internet or git",
            "FROM alpine\nCOPY --from=docker.io/library/busybox /bin/sh /sh\n": "earlier stage",
            "FROM alpine\nVOLUME /data\n": "VOLUME",
            "FROM alpine\nONBUILD RUN x\n": "ONBUILD",
            "FROM $BASE\n": "variable",
            "FROM local/jellystat:1.0\n": "built on this computer",
            "RUN echo hi\n": "must start with FROM",
            "FROM alpine\nFOO bar\n": "not an instruction",
            "FROM alpine\nCOPY --link a /a\n": "COPY --link",
            "FROM --network=host alpine\n": "only --platform",
        }
        for text, words in cases.items():
            got = self.problems(text)
            self.assertTrue(any(words in p for p in got), f"{text!r}: {got}")

    def test_stages_and_their_copies_are_allowed(self):
        text = "FROM golang:1.23 AS build\nRUN go build -o /x .\nFROM alpine:3.20\nCOPY --from=build /x /x\nCOPY --chown=1000:1000 a /a\n"
        self.assertEqual(plugin_zip.check_dockerfile(text), ([], ["golang:1.23", "alpine:3.20"]))
        self.assertEqual(self.problems("FROM scratch\nCOPY a /a\n"), [])
        self.assertEqual(self.problems("FROM alpine@sha256:" + "a" * 64 + "\n"), [])


class BuildLimits(unittest.TestCase):
    """Security tests: the build Docker is asked for, with its limits, and what happens when it goes wrong."""

    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.zip = make_zip(os.path.join(self.data, "p.zip"), {"starboard-plugin.json": json.dumps(built()), "Dockerfile": DOCKERFILE})

    def fake(self, lines, size=1000, status=200):
        sent = {}

        class Resp:
            def __init__(self):
                self.status, self.items = status, [json.dumps(x).encode() + b"\n" for x in lines]

            def read(self, n=-1):
                return b"refused"

            def readline(self, n=-1):
                return self.items.pop(0) if self.items else b""

        class Conn:
            def __init__(self, timeout):
                sent["timeout"] = timeout

            def request(self, method, path, body=None, headers=None):
                sent.update(method=method, path=path, headers=headers, tar=body.read())

            def getresponse(self):
                return Resp()

            def close(self):
                sent["closed"] = True

        docker = mock.Mock(return_value={"Size": size})
        return sent, Conn, docker

    def test_the_build_is_limited_and_tagged(self):
        import urllib.parse
        sent, conn, docker = self.fake([{"stream": "Step 1/8 : FROM python:3.12-alpine\n"}, {"stream": "Successfully built 1\n"}])
        with mock.patch("starboard.containers._UnixConnection", conn), mock.patch("starboard.containers.docker", docker):
            lines = plugin_zip.build(self.data, "on-demand", built(), self.zip)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(sent["path"]).query)
        self.assertEqual(q["t"], ["local/on-demand:0.9.2"])
        self.assertEqual(q["version"], ["1"])  # Docker's own builder, which keeps to the limits
        self.assertEqual(q["memory"], [str(2048 * 1024 * 1024)])
        self.assertEqual(q["memswap"], q["memory"])  # no swap beyond the memory
        self.assertEqual(q["cpuquota"], ["200000"])
        self.assertEqual(q["networkmode"], ["default"])  # never the host's network
        self.assertNotIn("buildargs", q)
        self.assertEqual(json.loads(q["labels"][0])["starboard.plugin"], "on-demand")
        self.assertTrue(sent["closed"])
        self.assertIn("Successfully built 1", lines)
        self.assertEqual([n for n in os.listdir(plugin_zip.uploads(self.data))], [])  # the context tar is not kept

    def test_a_failing_build_says_why(self):
        sent, conn, docker = self.fake([{"stream": "Step 2/8 : RUN false\n"}, {"error": "The command returned a non-zero code: 1"}])
        with mock.patch("starboard.containers._UnixConnection", conn), mock.patch("starboard.containers.docker", docker):
            with self.assertRaisesRegex(plugin_zip.BuildFailed, "non-zero code"):
                plugin_zip.build(self.data, "on-demand", built(), self.zip)

    def test_a_build_over_its_time_is_stopped(self):
        sent, conn, docker = self.fake([{"stream": "working\n"}] * 5)
        with mock.patch("starboard.containers._UnixConnection", conn), mock.patch("starboard.containers.docker", docker):
            with self.assertRaisesRegex(plugin_zip.BuildFailed, "took longer"):
                plugin_zip.build(self.data, "on-demand", built(), self.zip, deadline_seconds=-1)
        self.assertTrue(sent["closed"])  # closing the connection ends Docker's build

    def test_an_image_over_3_gb_is_removed_and_refused(self):
        sent, conn, docker = self.fake([{"stream": "done\n"}], size=4 * 1024 ** 3)
        with mock.patch("starboard.containers._UnixConnection", conn), mock.patch("starboard.containers.docker", docker):
            with self.assertRaisesRegex(plugin_zip.BuildFailed, "up to 3 GB"):
                plugin_zip.build(self.data, "on-demand", built(), self.zip)
        self.assertEqual(docker.call_args_list[-1][0][0], "DELETE")

    def test_the_warning_says_what_the_build_may_do(self):
        w = plugins.install_warning(built())
        self.assertTrue(any("builds its image, local/on-demand:0.9.2" in r and "2 GB" in r and "20 minutes" in r for r in w["runs"]))
        self.assertTrue(any("(built here from the zip)" in r for r in w["runs"]))


class ZipLife(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        os.makedirs(pa.root(self.data), exist_ok=True)

    def test_kept_zips_are_the_current_and_the_previous_only(self):
        where = pa.folder(self.data, "on-demand")
        os.makedirs(os.path.join(where, "previous"))
        pa._write(os.path.join(where, "manifest.json"), built("0.9.3"))
        pa._write(os.path.join(where, "previous", "manifest.json"), built("0.9.2"))
        for v in ("0.9.1", "0.9.2", "0.9.3"):
            p = os.path.join(self.data, f"{v}.zip")
            with open(p, "wb") as f:
                f.write(b"PK")
            plugin_zip.keep(self.data, "on-demand", v, p)
        self.assertEqual(sorted(os.listdir(os.path.join(where, "zips"))), ["0.9.2.zip", "0.9.3.zip"])
        aside = os.listdir(os.path.join(pa.root(self.data), ".removed", "on-demand-zips"))
        self.assertTrue(aside[0].endswith("0.9.1.zip"))  # moved aside, never deleted

    def test_a_missing_image_is_built_again_from_the_kept_zip(self):
        where = pa.folder(self.data, "on-demand")
        os.makedirs(os.path.join(where, "zips"))
        pa._write(os.path.join(where, "manifest.json"), built())
        with mock.patch("starboard.containers.available", return_value=True), \
                mock.patch.object(plugin_zip, "image_present", return_value=False):
            with self.assertRaisesRegex(ValueError, "zip is not kept"):
                plugin_zip.ensure_images(self.data, "on-demand")
            make_zip(os.path.join(where, "zips", "0.9.2.zip"), {"starboard-plugin.json": json.dumps(built()), "Dockerfile": DOCKERFILE})
            with mock.patch.object(plugin_zip, "build", return_value=[]) as b:
                self.assertTrue(plugin_zip.ensure_images(self.data, "on-demand"))
                b.assert_called_once()

    def test_an_address_or_catalogue_cannot_install_a_built_container(self):
        from starboard import update_runs
        app = mock.Mock(data_dir=self.data)
        with mock.patch.object(pa, "listing", return_value=[{"id": "on-demand", "name": "On demand", "version": "0.9.1"}]), \
                mock.patch.object(pa, "fetch_manifest", return_value=built()), \
                mock.patch("starboard.plugin_life.updates_known", return_value={}):
            with self.assertRaisesRegex(update_runs.Refused, "comes as a zip file"):
                update_runs._start_plugin(app, "on-demand", "you", "https://example.invalid/starboard-plugin.json")


LIB_MANIFEST = {**copy.deepcopy(ON_DEMAND), "permissions": ON_DEMAND["permissions"] + ["jellyfin:libraries"],
                "jellyfin_libraries": [{"name": "On demand Films", "type": "movies", "folder": "media/on-demand/films"},
                                       {"name": "On demand TV", "type": "tvshows", "folder": "media/on-demand/tv"}]}


class JellyfinLibraries(unittest.TestCase):
    def test_the_field_is_checked(self):
        self.assertEqual(plugins.check(LIB_MANIFEST), [])
        m = copy.deepcopy(LIB_MANIFEST)
        m["permissions"].remove("jellyfin:libraries")
        self.assertIn("jellyfin_libraries needs the permission jellyfin:libraries", plugins.check(m))
        for lib, words in (({"name": "X", "type": "films", "folder": "media/on-demand/x"}, "type must be"),
                           ({"name": "X", "type": "movies", "folder": "media/other/x"}, "mounts (media/other)"),
                           ({"name": "X", "type": "movies", "folder": "media/on-demand/../x"}, "inside one of its media folders"),
                           ({"name": "X", "type": "movies", "folder": "/etc"}, "inside one of its media folders"),
                           ({"name": "X", "type": "movies", "folder": "media/on-demand/x", "realtime_monitor": "no"}, "true or false"),
                           ({"name": "X", "type": "movies", "folder": "media/on-demand/x", "path": "/x"}, "unknown field path")):
            m = copy.deepcopy(LIB_MANIFEST)
            m["jellyfin_libraries"] = [lib]
            self.assertTrue(any(words in p for p in plugins.check(m)), f"{lib}: {plugins.check(m)}")

    def test_the_warning_names_them_and_monitoring(self):
        w = plugins.install_warning(LIB_MANIFEST)
        line = next(c for c in w["change"] if c.startswith("Jellyfin:"))
        self.assertIn("On demand Films and On demand TV", line)
        self.assertIn("Real-time monitoring is deactivated", line)
        self.assertIn("stay in Jellyfin", line)

    def setUp(self):
        self.data = tempfile.mkdtemp()
        where = pa.folder(self.data, "on-demand")
        os.makedirs(where)
        pa._write(os.path.join(where, "manifest.json"), LIB_MANIFEST)
        pa._write(os.path.join(where, "state.json"), {"state": "enabled"})
        self.services = [{"type": "jellyfin", "url": "http://127.0.0.1:8096", "api_key": "k", "name": "Jellyfin", "container": "jellyfin"}]

    def test_new_libraries_are_added_with_monitoring_off(self):
        calls = []

        def call(method, path, body):
            calls.append((method, path, body))
            return [{"Name": "Films", "Locations": ["/data/media/films"], "ItemId": "1", "LibraryOptions": {"EnableRealtimeMonitor": True}}] if method == "GET" else None
        inspect = lambda name: {"Mounts": [{"Source": "/srv/data/media", "Destination": "/data/media"}]}
        with mock.patch.object(pa, "media_host_dir", return_value="/srv/data/media"):
            done = plugin_libraries.ensure(self.data, "on-demand", self.services, call=call, inspect=inspect)
        posts = [c for c in calls if c[0] == "POST"]
        self.assertEqual(len(posts), 2)
        self.assertIn("name=On+demand+Films", posts[0][1])
        self.assertIn("collectionType=movies", posts[0][1])
        self.assertEqual(posts[0][2]["LibraryOptions"], {"EnableRealtimeMonitor": False, "PathInfos": [{"Path": "/data/media/on-demand/films"}]})
        self.assertEqual(len(done), 2)
        st = pa._read(os.path.join(pa.folder(self.data, "on-demand"), "state.json"))
        self.assertEqual([x["name"] for x in st["libraries"]["items"]], ["On demand Films", "On demand TV"])

    def test_monitoring_turned_back_on_is_put_back_and_others_left(self):
        calls = []
        have = [{"Name": "On demand Films", "Locations": ["/media/on-demand/films"], "ItemId": "a", "LibraryOptions": {"EnableRealtimeMonitor": True, "Other": 1}},
                {"Name": "On demand TV", "Locations": ["/media/on-demand/tv"], "ItemId": "b", "LibraryOptions": {"EnableRealtimeMonitor": False}},
                {"Name": "Films", "Locations": ["/media/films"], "ItemId": "c", "LibraryOptions": {"EnableRealtimeMonitor": True}}]

        def call(method, path, body):
            calls.append((method, path, body))
            return have if method == "GET" else None
        inspect = lambda name: {"Mounts": [{"Source": "/mnt/pool/media", "Destination": "/media"}]}  # a server set up by hand
        with mock.patch.object(pa, "media_host_dir", return_value="/mnt/pool/media"):
            plugin_libraries.ensure(self.data, "on-demand", self.services, call=call, inspect=inspect)
        posts = [c for c in calls if c[0] == "POST"]
        self.assertEqual(posts, [("POST", "/Library/VirtualFolders/LibraryOptions",
                                  {"Id": "a", "LibraryOptions": {"EnableRealtimeMonitor": False, "Other": 1}})])

    def test_without_jellyfin_it_says_so_and_never_stops_the_plug_in(self):
        self.assertEqual(plugin_libraries.ensure(self.data, "on-demand", []), [])
        st = pa._read(os.path.join(pa.folder(self.data, "on-demand"), "state.json"))
        self.assertIn("no key for Jellyfin", st["libraries"]["said"])

    def test_their_folders_are_made_before_it_starts(self):
        with mock.patch.object(pa, "media_host_dir", return_value="/srv/media"):
            script, media = pa._prepare_media(self.data, "on-demand")
        self.assertIn("mkdir -p '/srv/media/on-demand/films' && chown 1000:1000 '/srv/media/on-demand/films'", script)
        self.assertNotIn("chown -R", script)


class AppsLinks(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        where = pa.folder(self.data, "tdarr")
        os.makedirs(where)
        m = {"id": "tdarr", "name": "Tdarr", "containers": [{"name": "tdarr", "image": "x"}], "adopt": {"app": "tdarr", "name": "Tdarr"}}
        pa._write(os.path.join(where, "manifest.json"), m)
        pa._write(os.path.join(where, "state.json"), {"state": "enabled", "ports": {"tdarr": 8265}, "adopted": {"app": "tdarr"}})

    def test_its_own_its_port_and_the_adopted_app_go_and_nothing_else(self):
        services = [{"id": "tdarr", "name": "Tdarr", "type": "tdarr", "url": "http://127.0.0.1:8265", "container": "tdarr"},
                    {"id": "t2", "name": "Tdarr 2", "type": "link", "url": "http://127.0.0.1:9999", "container": "plugin-tdarr-tdarr"},
                    {"id": "jf", "name": "Jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096", "container": "jellyfin"},
                    {"id": "far", "name": "Other", "type": "link", "url": "http://192.168.1.9:8265", "container": ""}]
        self.assertEqual([s["id"] for s in pa.apps_links(self.data, "tdarr", services)], ["tdarr", "t2"])

    def test_uninstall_takes_them_off_apps(self):
        from starboard import config as config_mod
        cfg = config_mod.Config(self.data)
        cfg.upsert_service({"name": "Tdarr", "type": "tdarr", "url": "http://127.0.0.1:8265", "container": "tdarr"})
        cfg.upsert_service({"name": "Jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096"})
        with mock.patch.object(pa, "_compose_run", return_value=(True, "")):
            pa.uninstall(self.data, "tdarr", config=cfg)
        self.assertEqual([s["name"] for s in cfg.data["services"]], ["Jellyfin"])

    def test_tdarr_settings_say_it_is_not_installed(self):
        from starboard import tdarr
        with self.assertRaisesRegex(LookupError, "not installed"):
            tdarr.state(mock.Mock(data={"services": []}))
        with self.assertRaisesRegex(ValueError, "no key"):
            tdarr.state(mock.Mock(data={"services": [{"type": "tdarr"}]}))


class JellyfinMetadataPlace(unittest.TestCase):
    def choice(self, **extra):
        return {"apps": ["jellyfin"], "config_dir": "/srv/config", "data_dir": "/srv/data", "puid": 1000, "pgid": 1000, "tz": "Europe/London", **extra}

    def test_new_installs_give_jellyfin_metadata(self):
        compose = stack.build(self.choice())["compose"]
        self.assertTrue(stack.has_jellyfin_metadata(compose))
        self.assertIn('"${CONFIG_DIR}/jellyfin-metadata:/metadata"', compose)
        self.assertFalse(stack.has_jellyfin_metadata(stack.build(self.choice(jellyfin_metadata=False))["compose"]))

    def test_an_install_not_moved_stays_as_it_was_until_moved(self):
        old = stack.build(self.choice(jellyfin_metadata=False))["compose"]
        new = stack.build(self.choice())["compose"]
        self.assertFalse(stack.has_jellyfin_metadata(stack.metadata_as_before(old, new)))
        moved = stack.add_jellyfin_metadata(old)
        self.assertTrue(stack.has_jellyfin_metadata(moved))
        self.assertTrue(stack.has_jellyfin_metadata(stack.metadata_as_before(moved, new)))
        self.assertEqual(stack.add_jellyfin_metadata(moved), moved)
        with self.assertRaises(ValueError):
            stack.add_jellyfin_metadata("services:\n  reelix:\n    image: x\n")

    def test_the_set_up_sets_metadata_path_once(self):
        calls = []

        def fake(base, method, path, body=None, headers=None, opener=None):
            calls.append((method, path, body))
            return {"/System/Info/Public": {"StartupWizardCompleted": True}, "/Users/AuthenticateByName": {"AccessToken": "t"},
                    "/System/Configuration": {"MetadataPath": "", "Other": 1}, "/Auth/Keys": {"Items": [{"AppName": app_setup.KEY_NAME, "AccessToken": "k"}]}
                    }.get(path.split("?")[0], [] if method == "GET" else None)
        with mock.patch.object(app_setup, "_call", fake):
            _, done, _ = app_setup.jellyfin_first_run("http://x", "pw", [], metadata="/metadata")
        self.assertIn(("POST", "/System/Configuration", {"MetadataPath": "/metadata", "Other": 1}), calls)
        self.assertTrue(any("/metadata" in d for d in done))

    def test_the_move_refuses_when_starboard_does_not_run_jellyfin(self):
        data = tempfile.mkdtemp()
        with mock.patch("starboard.containers.available", return_value=True), \
                mock.patch.object(jellyfin_metadata, "_inspect", return_value={"Mounts": []}):
            st = jellyfin_metadata.status(data)
        self.assertFalse(st["can_move"])
        self.assertIn("not in Install apps", st["why"])

    def test_watches_are_counted_and_judged(self):
        helper = mock.Mock(return_value=(0, "2074 127879\n0\n"))
        with mock.patch("time.sleep"):
            got = jellyfin_metadata.check_watches("sbtest", helper, "/srv/stack", wait=0)
        self.assertTrue(got["ok"])
        self.assertIn("2,074", got["said"])
        helper = mock.Mock(return_value=(0, "126000 127879\n4\n"))
        with mock.patch("time.sleep"):
            self.assertFalse(jellyfin_metadata.check_watches("sbtest", helper, "/srv/stack", wait=0)["ok"])


if __name__ == "__main__":
    unittest.main()
